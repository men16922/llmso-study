#!/usr/bin/env python3
"""Cloud Run의 OpenAI 호환 vLLM API에서 A1~A4 서빙 실험을 수행한다."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import json
import math
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


MODEL_NAME = "google/gemma-4-31B-it"
SERVICE_NAME = "gemma-rtx-vllm-codelab"
REGION = "europe-west4"
EXPERIMENTS = ("smoke", "a1", "a2", "a3", "a4", "all")


@dataclasses.dataclass
class RequestResult:
    experiment: str
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


def parse_positive_ints(value: str) -> list[int]:
    try:
        values = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("쉼표로 구분한 정수를 입력하세요.") from exc
    if not values or any(item < 1 for item in values):
        raise argparse.ArgumentTypeError("값은 모두 1 이상이어야 합니다.")
    return values


def project_from_dotenv() -> str | None:
    """저장소 .env에서 프로젝트 ID 키만 읽는다. 다른 값은 로드하지 않는다."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in {"PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"}:
            return value.strip().strip("\"'") or None
    return None


def default_project() -> str | None:
    return (
        os.getenv("PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
        or project_from_dotenv()
    )


def run_gcloud(arguments: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["gcloud", *arguments], text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "output", None) or str(exc)
        raise RuntimeError(f"gcloud 실행 실패: {detail.strip()}") from exc


def identity_token() -> str:
    return run_gcloud(["auth", "print-identity-token"])


def service_url(project: str, region: str, service: str) -> str:
    return run_gcloud(
        [
            "run",
            "services",
            "describe",
            service,
            "--project",
            project,
            "--region",
            region,
            "--format=value(status.url)",
        ]
    )


def estimate_tokens(text: str) -> int:
    """usage가 없는 호환 서버의 대체값이며 결과에 추정치임을 표시한다."""
    return max(0, round(len(text) / 4))


def uncached_user_messages(prompt: str) -> list[dict[str, str]]:
    """A2 외 실험에서 자동 prefix caching이 비교를 섞지 않도록 첫 블록을 고유화한다."""
    return [{"role": "user", "content": f"request-id={uuid.uuid4().hex}\n{prompt}"}]


def make_streaming_request(
    *,
    url: str,
    token: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    experiment: str,
    scenario: str,
    concurrency: int,
    request_id: int,
    timeout_s: float,
    enable_thinking: bool,
) -> RequestResult:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
        "seed": 42,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
    }
    request = urllib.request.Request(
        f"{url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
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
                    delta = choice.get("delta", {})
                    for key in ("reasoning_content", "content"):
                        fragment = delta.get(key)
                        if fragment:
                            if first_token_at is None:
                                first_token_at = time.perf_counter()
                            output_parts.append(str(fragment))
        ended = time.perf_counter()
        exact = output_tokens is not None
        if output_tokens is None:
            output_tokens = estimate_tokens("".join(output_parts))
        return RequestResult(
            experiment=experiment,
            scenario=scenario,
            concurrency=concurrency,
            request_id=request_id,
            ok=200 <= status < 300 and first_token_at is not None,
            status=status,
            ttft_s=(first_token_at - started) if first_token_at else None,
            e2e_s=ended - started,
            output_tokens=output_tokens,
            tokens_exact=exact,
            error=None if first_token_at else "스트림에서 내용 토큰을 받지 못했습니다.",
        )
    except urllib.error.HTTPError as exc:
        ended = time.perf_counter()
        detail = exc.read(800).decode("utf-8", errors="replace")
        return RequestResult(
            experiment,
            scenario,
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
    except Exception as exc:
        ended = time.perf_counter()
        return RequestResult(
            experiment,
            scenario,
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


async def run_requests(
    *,
    url: str,
    token: str,
    model: str,
    messages_factory,
    max_tokens: int,
    experiment: str,
    scenario: str,
    concurrency: int,
    request_count: int,
    timeout_s: float,
    enable_thinking: bool,
) -> tuple[list[RequestResult], float]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(request_id: int) -> RequestResult:
        async with semaphore:
            return await asyncio.to_thread(
                make_streaming_request,
                url=url,
                token=token,
                model=model,
                messages=messages_factory(request_id),
                max_tokens=max_tokens,
                experiment=experiment,
                scenario=scenario,
                concurrency=concurrency,
                request_id=request_id,
                timeout_s=timeout_s,
                enable_thinking=enable_thinking,
            )

    started = time.perf_counter()
    results = await asyncio.gather(*(one(i) for i in range(request_count)))
    return list(results), time.perf_counter() - started


def summarize(
    results: list[RequestResult], wall_s: float, ttft_slo: float, e2e_slo: float
) -> dict[str, Any]:
    successful = [item for item in results if item.ok]
    ttfts = [item.ttft_s for item in successful if item.ttft_s is not None]
    e2es = [item.e2e_s for item in successful]
    good = [
        item
        for item in successful
        if item.ttft_s is not None
        and item.ttft_s <= ttft_slo
        and item.e2e_s <= e2e_slo
    ]
    total_tokens = sum(item.output_tokens for item in successful)
    return {
        "experiment": results[0].experiment,
        "scenario": results[0].scenario,
        "concurrency": results[0].concurrency,
        "requests": len(results),
        "successes": len(successful),
        "failures": len(results) - len(successful),
        "ttft_p50_s": percentile(ttfts, 0.50),
        "ttft_p95_s": percentile(ttfts, 0.95),
        "e2e_p50_s": percentile(e2es, 0.50),
        "e2e_p95_s": percentile(e2es, 0.95),
        "output_tokens": total_tokens,
        "output_tok_per_s": total_tokens / wall_s if wall_s > 0 else None,
        "goodput_pct": len(good) / len(results) * 100 if results else 0,
        "exact_usage_requests": sum(item.tokens_exact for item in successful),
        "wall_s": wall_s,
    }


def print_summary(item: dict[str, Any]) -> None:
    def display(value: float | None) -> str:
        return "-" if value is None else f"{value:.3f}"

    print(
        f"{item['experiment'].upper()} {item['scenario']} c={item['concurrency']} "
        f"ok={item['successes']}/{item['requests']} "
        f"TTFT p50/p95={display(item['ttft_p50_s'])}/{display(item['ttft_p95_s'])}s "
        f"E2E p95={display(item['e2e_p95_s'])}s "
        f"tok/s={display(item['output_tok_per_s'])} "
        f"goodput={item['goodput_pct']:.1f}%"
    )


async def run_group_and_record(
    records: dict[str, Any],
    *,
    args,
    token: str,
    url: str,
    experiment: str,
    scenario: str,
    concurrency: int,
    request_count: int,
    max_tokens: int,
    messages_factory,
) -> dict[str, Any]:
    results, wall_s = await run_requests(
        url=url,
        token=token,
        model=args.model,
        messages_factory=messages_factory,
        max_tokens=max_tokens,
        experiment=experiment,
        scenario=scenario,
        concurrency=concurrency,
        request_count=request_count,
        timeout_s=args.timeout,
        enable_thinking=args.enable_thinking,
    )
    summary = summarize(results, wall_s, args.ttft_slo, args.e2e_slo)
    records["summaries"].append(summary)
    records["requests"].extend(item.as_dict() for item in results)
    print_summary(summary)
    return summary


async def experiment_a1(records, args, token: str, url: str) -> None:
    prompt = (
        "Transformer와 self-attention의 구조를 LLM 서빙 관점에서 "
        "200단어 안팎으로 설명해 주세요."
    )
    for concurrency in args.concurrency:
        await run_group_and_record(
            records,
            args=args,
            token=token,
            url=url,
            experiment="a1",
            scenario="batching",
            concurrency=concurrency,
            request_count=max(args.requests_per_level, concurrency),
            max_tokens=256,
            messages_factory=lambda _i, prompt=prompt: uncached_user_messages(prompt),
        )


async def experiment_a2(records, args, token: str, url: str) -> None:
    common = (
        "당신은 LLM 서빙 인프라 전문가입니다. 다음 배경을 참고하세요. "
        + (
            "prefill은 입력을 처리해 KV cache를 만들고 decode는 토큰을 하나씩 생성합니다. "
            "PagedAttention은 KV cache를 블록 단위로 관리해 메모리 단편화를 줄입니다. "
        )
        * 80
    )
    hit_prefix = f"cache-group={'0' * 32}\n{common}"
    prime = make_streaming_request(
        url=url,
        token=token,
        model=args.model,
        messages=[
            {"role": "system", "content": hit_prefix},
            {"role": "user", "content": "핵심을 한 문장으로 요약해 주세요."},
        ],
        max_tokens=32,
        experiment="a2",
        scenario="cache-prime",
        concurrency=1,
        request_id=-1,
        timeout_s=args.timeout,
        enable_thinking=args.enable_thinking,
    )
    records["requests"].append(prime.as_dict())
    if not prime.ok:
        raise RuntimeError(f"A2 cache prime 실패: {prime.error}")

    hit_factory = lambda i: [
        {"role": "system", "content": hit_prefix},
        {"role": "user", "content": f"질문 {i}: PagedAttention의 장점을 설명해 주세요."},
    ]
    hit_summary = await run_group_and_record(
        records,
        args=args,
        token=token,
        url=url,
        experiment="a2",
        scenario="cache-hit",
        concurrency=1,
        request_count=args.prefix_repeats,
        max_tokens=128,
        messages_factory=hit_factory,
    )

    def miss_factory(i: int) -> list[dict[str, str]]:
        unique_prefix = f"cache-group={uuid.uuid4().hex}\n{common}"
        return [
            {"role": "system", "content": unique_prefix},
            {"role": "user", "content": "PagedAttention의 장점을 설명해 주세요."},
        ]

    miss_summary = await run_group_and_record(
        records,
        args=args,
        token=token,
        url=url,
        experiment="a2",
        scenario="cache-miss-control",
        concurrency=1,
        request_count=args.prefix_repeats,
        max_tokens=128,
        messages_factory=miss_factory,
    )
    hit_p50 = hit_summary["ttft_p50_s"]
    miss_p50 = miss_summary["ttft_p50_s"]
    reduction = None
    if hit_p50 is not None and miss_p50:
        reduction = (miss_p50 - hit_p50) / miss_p50 * 100
    records["derived"]["a2_prefix_cache"] = {
        "hit_ttft_p50_s": hit_p50,
        "miss_control_ttft_p50_s": miss_p50,
        "ttft_reduction_pct": reduction,
    }


async def experiment_a3(records, args, token: str, url: str) -> None:
    short_prompt = "prefill과 decode의 차이를 한 문장으로 설명해 주세요."
    long_prompt = (
        "다음 설명을 읽고 핵심 병목을 한 문장으로 답하세요.\n\n"
        + (
            "prefill은 입력 토큰을 병렬 처리해 KV cache를 만들고, decode는 저장된 "
            "KV cache를 읽으며 새 토큰을 순차 생성합니다. 입력 길이와 출력 길이는 "
            "서로 다른 병목을 만듭니다. "
        )
        * 80
    )
    scenarios = [
        ("short", short_prompt, 64),
        ("prefill", long_prompt, 64),
        ("decode", short_prompt, 512),
    ]
    for scenario, prompt, max_tokens in scenarios:
        for concurrency in args.a3_concurrency:
            await run_group_and_record(
                records,
                args=args,
                token=token,
                url=url,
                experiment="a3",
                scenario=scenario,
                concurrency=concurrency,
                request_count=max(args.a3_requests, concurrency),
                max_tokens=max_tokens,
                messages_factory=lambda _i, prompt=prompt: uncached_user_messages(prompt),
            )


async def experiment_a4(records, args, token: str, url: str) -> None:
    prompt = "GPU 한 장의 LLM 서버가 처리할 수 있는 요청량을 판단할 지표를 설명해 주세요."
    qualifying: list[int] = []
    for concurrency in args.concurrency:
        summary = await run_group_and_record(
            records,
            args=args,
            token=token,
            url=url,
            experiment="a4",
            scenario="goodput-capacity",
            concurrency=concurrency,
            request_count=max(args.requests_per_level, concurrency),
            max_tokens=128,
            messages_factory=lambda _i, prompt=prompt: uncached_user_messages(prompt),
        )
        if summary["goodput_pct"] >= args.goodput_target:
            qualifying.append(concurrency)
    records["derived"]["a4_capacity"] = {
        "goodput_target_pct": args.goodput_target,
        "max_concurrency_meeting_target": max(qualifying) if qualifying else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="생략하면 gcloud로 Cloud Run URL 조회")
    parser.add_argument("--project", default=default_project())
    parser.add_argument("--region", default=os.getenv("GOOGLE_CLOUD_REGION", REGION))
    parser.add_argument("--service", default=SERVICE_NAME)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--exp", choices=EXPERIMENTS, default="smoke")
    parser.add_argument("--concurrency", type=parse_positive_ints, default=[1, 2, 4, 8, 16])
    parser.add_argument("--requests-per-level", type=int, default=8)
    parser.add_argument("--a3-concurrency", type=parse_positive_ints, default=[1, 8])
    parser.add_argument("--a3-requests", type=int, default=4)
    parser.add_argument("--prefix-repeats", type=int, default=5)
    parser.add_argument("--ttft-slo", type=float, default=2.0)
    parser.add_argument("--e2e-slo", type=float, default=30.0)
    parser.add_argument("--goodput-target", type=float, default=95.0)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--skip-warmup", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


async def async_main(args) -> tuple[int, dict[str, Any]]:
    if not args.project:
        raise RuntimeError("GCP 프로젝트를 찾지 못했습니다. --project 또는 .env의 PROJECT_ID를 설정하세요.")
    if min(args.requests_per_level, args.a3_requests, args.prefix_repeats) < 1:
        raise RuntimeError("요청 수는 모두 1 이상이어야 합니다.")

    url = args.url or service_url(args.project, args.region, args.service)
    token = identity_token()
    records: dict[str, Any] = {
        "meta": {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "project": args.project,
            "region": args.region,
            "service": args.service,
            "url": url,
            "model": args.model,
            "experiment": args.exp,
            "ttft_definition": "요청 시작부터 첫 content 또는 reasoning_content 조각까지",
            "throughput_definition": "성공 요청의 completion_tokens 합계 / 벽시계 시간",
            "goodput_definition": "TTFT와 E2E SLO를 모두 만족한 요청 비율",
            "ttft_slo_s": args.ttft_slo,
            "e2e_slo_s": args.e2e_slo,
            "goodput_target_pct": args.goodput_target,
            "enable_thinking": args.enable_thinking,
        },
        "warmup": None,
        "derived": {},
        "summaries": [],
        "requests": [],
    }
    print(f"target={args.service} project={args.project} region={args.region}")

    if not args.skip_warmup:
        warmup = make_streaming_request(
            url=url,
            token=token,
            model=args.model,
            messages=[{"role": "user", "content": "한 단어로 준비 상태를 답하세요."}],
            max_tokens=8,
            experiment="warmup",
            scenario="cold-start-observation",
            concurrency=1,
            request_id=0,
            timeout_s=args.timeout,
            enable_thinking=False,
        )
        records["warmup"] = warmup.as_dict()
        print(
            f"warmup ok={warmup.ok} TTFT={warmup.ttft_s} E2E={warmup.e2e_s:.3f}s "
            "(배칭 곡선에서는 제외)"
        )
        if not warmup.ok:
            return 1, records

    if args.exp == "smoke":
        await run_group_and_record(
            records,
            args=args,
            token=token,
            url=url,
            experiment="smoke",
            scenario="short",
            concurrency=1,
            request_count=1,
            max_tokens=32,
            messages_factory=lambda _i: [
                {"role": "user", "content": "하늘이 파란 이유를 한 문장으로 답하세요."}
            ],
        )
    else:
        if args.exp in {"a1", "all"}:
            await experiment_a1(records, args, token, url)
        if args.exp in {"a2", "all"}:
            await experiment_a2(records, args, token, url)
        if args.exp in {"a3", "all"}:
            await experiment_a3(records, args, token, url)
        if args.exp in {"a4", "all"}:
            await experiment_a4(records, args, token, url)

    ok = all(item["ok"] for item in records["requests"])
    return (0 if ok else 1), records


def default_output() -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(__file__).resolve().parent / "results" / f"gemma4-{stamp}.json"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or default_output()
    try:
        exit_code, records = asyncio.run(async_main(args))
    except Exception as exc:
        print(f"실험 준비 실패: {exc}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"result={output}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
