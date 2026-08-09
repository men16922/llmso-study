#!/usr/bin/env python3
"""OpenAI 호환 스트리밍 API의 TTFT, E2E, 처리량, goodput을 측정한다."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


SCENARIOS = {
    "short": {
        "description": "짧은 입력·짧은 출력",
        "prompt": "GPU 한 장에서 LLM을 서빙할 때 먼저 확인할 지표를 한 문장으로 설명해 주세요.",
        "max_tokens": 64,
    },
    "prefill": {
        "description": "긴 입력·짧은 출력",
        "prompt": (
            "다음 문맥을 읽고 핵심 병목을 한 문장으로 답하세요.\n\n"
            + (
                "LLM 추론의 prefill 단계는 입력 토큰을 병렬 처리해 KV cache를 만들고, "
                "decode 단계는 저장된 KV cache를 읽으며 토큰을 하나씩 생성한다. "
                "긴 입력은 prefill 연산량을 늘리고 동시 요청은 KV cache 메모리 사용량을 늘린다. "
            )
            * 24
        ),
        "max_tokens": 64,
    },
    "decode": {
        "description": "짧은 입력·긴 출력",
        "prompt": "GPU 기반 LLM 서빙에서 prefill, decode, KV cache, batching의 관계를 예시와 함께 자세히 설명해 주세요.",
        "max_tokens": 512,
    },
}


@dataclasses.dataclass
class RequestResult:
    scenario: str
    concurrency: int
    request_id: int
    ok: bool
    status: int
    ttft_s: float | None
    e2e_s: float
    output_tokens: int
    tokens_exact: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * quantile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def auth_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def discover_model(base_url: str, api_key: str | None, timeout_s: float) -> str:
    request = urllib.request.Request(
        api_url(base_url, "/v1/models"), headers=auth_headers(api_key)
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        payload = json.load(response)
    models = payload.get("data", [])
    if not models or not models[0].get("id"):
        raise RuntimeError("/v1/models 응답에서 모델 ID를 찾지 못했습니다.")
    return str(models[0]["id"])


def estimate_tokens(text: str) -> int:
    """usage가 없는 호환 서버를 위한 보수적 대체값이다."""
    return max(0, len(text.strip().split()))


def build_prompt(scenario_name: str, unique_prefix: bool) -> str:
    """시나리오 프롬프트를 만든다.

    unique_prefix=True면 앞에 요청마다 다른 식별자를 붙여 prefix cache 적중을 막는다.
    모든 요청이 같은 프롬프트면 두 번째 요청부터 prefill이 캐시로 해결되어 TTFT가
    실제보다 좋게 나온다 — 배칭·동시성을 재는 실험에서는 이 효과를 제거해야 한다.
    """
    prompt = SCENARIOS[scenario_name]["prompt"]
    if not unique_prefix:
        return prompt
    return f"request-id={uuid.uuid4().hex}\n{prompt}"


def run_request(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    scenario_name: str,
    concurrency: int,
    request_id: int,
    timeout_s: float,
    unique_prefix: bool = False,
) -> RequestResult:
    scenario = SCENARIOS[scenario_name]
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": build_prompt(scenario_name, unique_prefix)}
        ],
        "max_tokens": scenario["max_tokens"],
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = urllib.request.Request(
        api_url(base_url, "/v1/chat/completions"),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=auth_headers(api_key),
        method="POST",
    )
    started = time.perf_counter()
    first_token_at: float | None = None
    output_parts: list[str] = []
    output_tokens: int | None = None
    status = 0

    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            status = response.status
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                event = json.loads(data)
                usage = event.get("usage")
                if usage and usage.get("completion_tokens") is not None:
                    output_tokens = int(usage["completion_tokens"])
                for choice in event.get("choices", []):
                    content = choice.get("delta", {}).get("content")
                    if content:
                        if first_token_at is None:
                            first_token_at = time.perf_counter()
                        output_parts.append(str(content))
        ended = time.perf_counter()
        exact = output_tokens is not None
        if output_tokens is None:
            output_tokens = estimate_tokens("".join(output_parts))
        return RequestResult(
            scenario=scenario_name,
            concurrency=concurrency,
            request_id=request_id,
            ok=200 <= status < 300 and first_token_at is not None,
            status=status,
            ttft_s=(first_token_at - started) if first_token_at else None,
            e2e_s=ended - started,
            output_tokens=output_tokens,
            tokens_exact=exact,
            error=None if first_token_at else "스트림에서 출력 토큰을 받지 못했습니다.",
        )
    except urllib.error.HTTPError as exc:
        ended = time.perf_counter()
        detail = exc.read(500).decode("utf-8", errors="replace")
        return RequestResult(
            scenario_name,
            concurrency,
            request_id,
            False,
            exc.code,
            None,
            ended - started,
            0,
            False,
            detail,
        )
    except Exception as exc:  # 네트워크·타임아웃을 결과 파일에 남긴다.
        ended = time.perf_counter()
        return RequestResult(
            scenario_name,
            concurrency,
            request_id,
            False,
            status,
            None,
            ended - started,
            0,
            False,
            f"{type(exc).__name__}: {exc}",
        )


def summarize_group(
    results: list[RequestResult],
    wall_s: float,
    ttft_slo_s: float,
    e2e_slo_s: float,
) -> dict[str, Any]:
    successful = [result for result in results if result.ok]
    ttfts = [result.ttft_s for result in successful if result.ttft_s is not None]
    e2es = [result.e2e_s for result in successful]
    good = [
        result
        for result in successful
        if result.ttft_s is not None
        and result.ttft_s <= ttft_slo_s
        and result.e2e_s <= e2e_slo_s
    ]
    total_tokens = sum(result.output_tokens for result in successful)
    return {
        "scenario": results[0].scenario,
        "concurrency": results[0].concurrency,
        "requests": len(results),
        "successes": len(successful),
        "failures": len(results) - len(successful),
        "ttft_p50_s": percentile(ttfts, 0.50),
        "ttft_p95_s": percentile(ttfts, 0.95),
        "e2e_p50_s": percentile(e2es, 0.50),
        "e2e_p95_s": percentile(e2es, 0.95),
        "e2e_mean_s": statistics.fmean(e2es) if e2es else None,
        "output_tokens": total_tokens,
        "output_tok_per_s": total_tokens / wall_s if wall_s > 0 else None,
        "goodput_pct": len(good) / len(results) * 100 if results else 0,
        "exact_usage_requests": sum(result.tokens_exact for result in successful),
        "wall_s": wall_s,
    }


def run_group(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    scenario_name: str,
    concurrency: int,
    request_count: int,
    timeout_s: float,
    unique_prefix: bool = False,
) -> tuple[list[RequestResult], float]:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                run_request,
                base_url=base_url,
                api_key=api_key,
                model=model,
                scenario_name=scenario_name,
                concurrency=concurrency,
                request_id=request_id,
                timeout_s=timeout_s,
                unique_prefix=unique_prefix,
            )
            for request_id in range(request_count)
        ]
        results = [future.result() for future in futures]
    return results, time.perf_counter() - started


def parse_concurrency(value: str) -> list[int]:
    values = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not values or any(item < 1 for item in values):
        raise argparse.ArgumentTypeError("동시성은 1 이상의 쉼표 구분 정수여야 합니다.")
    return values


def fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def print_summary(summaries: list[dict[str, Any]]) -> None:
    print(
        "scenario concurrency ok/total ttft_p50 ttft_p95 "
        "e2e_p95 tok/s goodput"
    )
    for item in summaries:
        print(
            f"{item['scenario']:8} {item['concurrency']:>11} "
            f"{item['successes']:>2}/{item['requests']:<5} "
            f"{fmt(item['ttft_p50_s']):>8} {fmt(item['ttft_p95_s']):>8} "
            f"{fmt(item['e2e_p95_s']):>7} "
            f"{fmt(item['output_tok_per_s']):>5} "
            f"{item['goodput_pct']:>6.1f}%"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--model", help="생략하면 /v1/models의 첫 모델을 사용")
    parser.add_argument(
        "--scenarios",
        default="short,prefill,decode",
        help="short,prefill,decode 중 쉼표 구분",
    )
    parser.add_argument("--concurrency", type=parse_concurrency, default=[1, 4, 8, 16])
    parser.add_argument("--requests-per-level", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--ttft-slo", type=float, default=2.0)
    parser.add_argument("--e2e-slo", type=float, default=30.0)
    parser.add_argument(
        "--unique-prefix",
        action="store_true",
        help="요청마다 프롬프트 앞에 고유 식별자를 붙여 prefix cache 적중을 막는다",
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scenario_names = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    unknown = [name for name in scenario_names if name not in SCENARIOS]
    if unknown:
        print(f"알 수 없는 시나리오: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if args.requests_per_level < 1 or args.warmup < 0:
        print("요청 수는 1 이상, warmup은 0 이상이어야 합니다.", file=sys.stderr)
        return 2

    try:
        model = args.model or discover_model(args.base_url, args.api_key, args.timeout)
    except Exception as exc:
        print(f"모델 서버 확인 실패: {exc}", file=sys.stderr)
        return 1

    print(f"model={model} base_url={args.base_url}")
    all_results: list[RequestResult] = []
    summaries: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        for warmup_id in range(args.warmup):
            warmup = run_request(
                base_url=args.base_url,
                api_key=args.api_key,
                model=model,
                scenario_name=scenario_name,
                concurrency=1,
                request_id=-(warmup_id + 1),
                timeout_s=args.timeout,
                unique_prefix=args.unique_prefix,
            )
            if not warmup.ok:
                print(f"{scenario_name} warmup 실패: {warmup.error}", file=sys.stderr)
                return 1

        for concurrency in args.concurrency:
            count = max(args.requests_per_level, concurrency)
            results, wall_s = run_group(
                base_url=args.base_url,
                api_key=args.api_key,
                model=model,
                scenario_name=scenario_name,
                concurrency=concurrency,
                request_count=count,
                timeout_s=args.timeout,
                unique_prefix=args.unique_prefix,
            )
            all_results.extend(results)
            summaries.append(
                summarize_group(results, wall_s, args.ttft_slo, args.e2e_slo)
            )

    payload = {
        "meta": {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "base_url": args.base_url,
            "model": model,
            "scenarios": scenario_names,
            "concurrency": args.concurrency,
            "requests_per_level": args.requests_per_level,
            "warmup": args.warmup,
            "ttft_slo_s": args.ttft_slo,
            "e2e_slo_s": args.e2e_slo,
            "unique_prefix": args.unique_prefix,
            "goodput_definition": "TTFT와 E2E SLO를 모두 만족한 요청 비율",
        },
        "summaries": summaries,
        "requests": [result.as_dict() for result in all_results],
    }
    print_summary(summaries)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"result={args.output}")
    return 0 if all(result.ok for result in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
