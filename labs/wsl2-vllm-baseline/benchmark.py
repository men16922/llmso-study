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


# 교재(orca3/llm-model-inference) ch03/single_model_llm_serving 서버의 엔드포인트.
# OpenAI 호환이 아니라 스키마가 각기 다르므로 여기에 선언해 두고 분기한다.
#
#   streaming      — SSE(`data: {"token": ...}`)로 받는가. False면 TTFT를 잴 수 없다.
#   list_input     — 요청 본문이 {"prompts": [...]}인가 {"prompt": "..."}인가.
#   result_key     — 비스트리밍 응답에서 생성 텍스트를 꺼낼 키.
#   echoes_prompt  — 응답에 프롬프트가 그대로 포함되는가 (아래 주석 참조).
#   batching       — 이 엔드포인트가 대표하는 배칭 방식 (결과 해석용 라벨).
BOOK_ENDPOINTS = {
    "/basic_generate": {
        "streaming": False, "list_input": False, "result_key": "generated_text",
        "echoes_prompt": True, "batching": "none",
    },
    "/generate": {
        "streaming": False, "list_input": True, "result_key": "generated_texts",
        "echoes_prompt": True, "batching": "static",
    },
    "/generate_stream": {
        "streaming": True, "list_input": False, "result_key": None,
        "echoes_prompt": False, "batching": "continuous-naive",
    },
    "/generate_vllm": {
        "streaming": False, "list_input": True, "result_key": "generated_texts",
        "echoes_prompt": False, "batching": "continuous-vllm",
    },
}

# `echoes_prompt`가 필요한 이유:
#   ModelWorker.generate()는 batch_decode(outputs)를 그대로 반환하는데, outputs는
#   [프롬프트 토큰 + 생성 토큰] 전체다. 즉 /basic_generate·/generate의 응답에는
#   프롬프트가 그대로 붙어 나온다. 그대로 세면 처리량이 프롬프트 길이만큼 부풀려져
#   /generate_vllm(생성분만 반환)과의 비교가 무의미해진다.
#   그래서 이 엔드포인트들은 프롬프트 몫을 빼고 센다.


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
    # ITL(inter-token latency) = 첫 토큰 이후 토큰 하나당 평균 간격.
    # 스터디 공통 벤치마크 규칙의 핵심 지표(TPOT)에 해당한다. ITL 10ms = 사용자당 100 TPS.
    # 스트리밍이 아니면 잴 수 없으므로 None이다.
    itl_s: float | None = None

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


def compute_itl(
    first_token_at: float | None, last_token_at: float | None, token_events: int
) -> float | None:
    """첫 토큰 이후 토큰 하나당 평균 간격(초).

    토큰 이벤트가 2개 미만이면 간격 자체가 없으므로 None을 돌려준다.
    usage 기반 토큰 수가 아니라 **실제로 받은 스트림 이벤트 수**로 나눈다 —
    시간 간격을 만든 것은 이벤트이지 서버가 세어 준 토큰이 아니기 때문이다.
    """
    if first_token_at is None or last_token_at is None or token_events < 2:
        return None
    return (last_token_at - first_token_at) / (token_events - 1)


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
    api_key: str | None = None,
    model: str = "",
    scenario_name: str,
    concurrency: int,
    request_id: int,
    timeout_s: float,
    unique_prefix: bool = False,
    api: str = "openai",
    endpoint: str | None = None,
    prompts_per_request: int = 1,
) -> RequestResult:
    """API 방식에 따라 실제 요청 함수로 분기한다.

    api="openai" — vLLM 등 OpenAI 호환 서버의 /v1/chat/completions (기본값)
    api="book"   — 교재 ch03 서버. endpoint로 BOOK_ENDPOINTS 중 하나를 지정한다.
    """
    if api == "book":
        return run_book_request(
            base_url=base_url,
            endpoint=endpoint or "/generate_stream",
            scenario_name=scenario_name,
            concurrency=concurrency,
            request_id=request_id,
            timeout_s=timeout_s,
            unique_prefix=unique_prefix,
            prompts_per_request=prompts_per_request,
        )
    return run_openai_request(
        base_url=base_url,
        api_key=api_key,
        model=model,
        scenario_name=scenario_name,
        concurrency=concurrency,
        request_id=request_id,
        timeout_s=timeout_s,
        unique_prefix=unique_prefix,
    )


def run_book_request(
    *,
    base_url: str,
    endpoint: str,
    scenario_name: str,
    concurrency: int,
    request_id: int,
    timeout_s: float,
    unique_prefix: bool = False,
    prompts_per_request: int = 1,
) -> RequestResult:
    """교재 ch03 서버에 요청 하나를 보낸다.

    OpenAI 경로와 달리 usage가 없으므로 출력 토큰 수는 estimate_tokens()로 센다.
    네 엔드포인트가 모두 같은 방식으로 세므로 **상대 비교는 유효**하지만, vLLM
    서버의 tok/s와 절대값을 직접 비교하면 안 된다.

    ★ prompts_per_request — 교재 서버의 배칭 축은 "동시 요청 수"가 아니다.
      `/generate`는 요청 하나에 담긴 프롬프트들을 WorkloadManager의 batch_size(=4)
      단위로 묶는다. 그리고 main.py의 핸들러가 `async def` 안에서 동기 호출을 하므로
      uvicorn 이벤트 루프가 막혀 **요청 간 배칭은 구조적으로 일어나지 않는다.**
      따라서 배칭을 재려면 한 요청에 프롬프트를 여러 개 실어야 한다.
    """
    if endpoint not in BOOK_ENDPOINTS:
        raise ValueError(f"알 수 없는 교재 엔드포인트: {endpoint}")
    if prompts_per_request < 1:
        raise ValueError("prompts_per_request는 1 이상이어야 합니다.")
    spec = BOOK_ENDPOINTS[endpoint]
    prompts = [
        build_prompt(scenario_name, unique_prefix) for _ in range(prompts_per_request)
    ]
    prompt = prompts[0]
    if spec["list_input"]:
        body: dict[str, Any] = {"prompts": prompts}
    else:
        # 단일 프롬프트만 받는 엔드포인트는 여러 개를 실을 수 없다.
        body = {"prompt": prompt}
    request = urllib.request.Request(
        api_url(base_url, endpoint),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    first_token_at: float | None = None
    last_token_at: float | None = None
    parts: list[str] = []
    status = 0

    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            status = response.status
            if spec["streaming"]:
                # 교재 서버는 [DONE] 센티널 없이 스트림을 그냥 닫는다.
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    token = json.loads(line[5:].strip()).get("token")
                    if token:
                        last_token_at = time.perf_counter()
                        if first_token_at is None:
                            first_token_at = last_token_at
                        parts.append(str(token))
            else:
                payload = json.load(response)
                value = payload.get(spec["result_key"])
                # 리스트 응답이면 **전부** 센다. 요청 하나에 프롬프트 N개를 실었으면
                # 생성분도 N개이고, 처리량은 그 합이어야 한다.
                items = value if isinstance(value, list) else [value]
                parts.extend(str(item or "") for item in items)
        ended = time.perf_counter()
        text = "".join(parts)
        if spec["streaming"]:
            # parts가 토큰 조각이므로 이어 붙인 뒤 세야 한다 (조각 단위로 세면
            # subword가 각각 한 단어로 잡혀 과대계상된다).
            output_tokens = estimate_tokens(text)
        else:
            # parts가 응답 하나씩이므로 **개별로 세서 더한다.** 이어 붙여서 세면
            # 앞 응답의 마지막 단어와 다음 응답의 첫 단어가 붙어 하나로 세어진다.
            output_tokens = sum(estimate_tokens(part) for part in parts)
            if spec["echoes_prompt"]:
                # 응답 하나마다 프롬프트가 한 벌씩 붙어 나온다.
                output_tokens = max(
                    0, output_tokens - estimate_tokens(prompt) * len(parts)
                )
        ok = 200 <= status < 300 and bool(text.strip())
        return RequestResult(
            scenario=scenario_name,
            concurrency=concurrency,
            request_id=request_id,
            ok=ok,
            status=status,
            # 비스트리밍 엔드포인트는 TTFT가 정의되지 않는다 — None으로 남긴다.
            ttft_s=(first_token_at - started) if first_token_at else None,
            e2e_s=ended - started,
            output_tokens=output_tokens,
            tokens_exact=False,
            error=None if ok else "응답에서 생성 텍스트를 받지 못했습니다.",
            itl_s=compute_itl(first_token_at, last_token_at, len(parts)),
        )
    except urllib.error.HTTPError as exc:
        ended = time.perf_counter()
        detail = exc.read(500).decode("utf-8", errors="replace")
        return RequestResult(
            scenario_name, concurrency, request_id, False, exc.code,
            None, ended - started, 0, False, detail,
        )
    except Exception as exc:  # 네트워크·타임아웃을 결과 파일에 남긴다.
        ended = time.perf_counter()
        return RequestResult(
            scenario_name, concurrency, request_id, False, status,
            None, ended - started, 0, False, f"{type(exc).__name__}: {exc}",
        )


def run_openai_request(
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
    last_token_at: float | None = None
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
                        last_token_at = time.perf_counter()
                        if first_token_at is None:
                            first_token_at = last_token_at
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
            itl_s=compute_itl(first_token_at, last_token_at, len(output_parts)),
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
    itls = [result.itl_s for result in successful if result.itl_s is not None]
    e2es = [result.e2e_s for result in successful]
    # 비스트리밍 엔드포인트(교재 /generate 등)는 TTFT가 정의되지 않는다. 그런 결과를
    # 전부 SLO 위반으로 세면 goodput이 0%로 나와 비교가 무의미해지므로, TTFT가 없으면
    # E2E SLO만으로 판정한다. OpenAI 경로의 성공 결과는 항상 TTFT를 가지므로 영향 없다.
    good = [
        result
        for result in successful
        if (result.ttft_s is None or result.ttft_s <= ttft_slo_s)
        and result.e2e_s <= e2e_slo_s
    ]
    itl_p50 = percentile(itls, 0.50)
    total_tokens = sum(result.output_tokens for result in successful)
    return {
        "scenario": results[0].scenario,
        "concurrency": results[0].concurrency,
        "requests": len(results),
        "successes": len(successful),
        "failures": len(results) - len(successful),
        "ttft_p50_s": percentile(ttfts, 0.50),
        "ttft_p95_s": percentile(ttfts, 0.95),
        "itl_p50_s": itl_p50,
        "itl_p95_s": percentile(itls, 0.95),
        # ITL 10ms = 사용자당 100 TPS. 스터디 규칙의 "perceived TPS"가 이것이다.
        "perceived_tps": (1 / itl_p50) if itl_p50 else None,
        "e2e_p50_s": percentile(e2es, 0.50),
        "e2e_p95_s": percentile(e2es, 0.95),
        "e2e_mean_s": statistics.fmean(e2es) if e2es else None,
        "output_tokens": total_tokens,
        "output_tok_per_s": total_tokens / wall_s if wall_s > 0 else None,
        "goodput_pct": len(good) / len(results) * 100 if results else 0,
        "exact_usage_requests": sum(result.tokens_exact for result in successful),
        "ttft_measured": bool(ttfts),
        "wall_s": wall_s,
    }


def run_group(
    *,
    base_url: str,
    api_key: str | None = None,
    model: str = "",
    scenario_name: str,
    concurrency: int,
    request_count: int,
    timeout_s: float,
    unique_prefix: bool = False,
    api: str = "openai",
    endpoint: str | None = None,
    prompts_per_request: int = 1,
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
                api=api,
                endpoint=endpoint,
                prompts_per_request=prompts_per_request,
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
        "--api",
        choices=("openai", "book"),
        default="openai",
        help="openai=vLLM 등 호환 서버(기본), book=교재 ch03 single_model_llm_serving",
    )
    parser.add_argument(
        "--endpoint",
        choices=tuple(BOOK_ENDPOINTS),
        help=f"--api book에서 쓸 엔드포인트 (기본 /generate_stream). "
             f"선택지: {', '.join(BOOK_ENDPOINTS)}",
    )
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
        "--prompts-per-request",
        type=int,
        default=1,
        help="--api book 전용. 요청 하나에 실을 프롬프트 수 — 교재 서버의 실제 배칭 축",
    )
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

    endpoint = args.endpoint
    if args.api == "book":
        # 교재 서버에는 /v1/models가 없다. 모델명은 기록용 라벨로만 쓴다.
        endpoint = endpoint or "/generate_stream"
        model = args.model or f"book{endpoint}"
    else:
        if endpoint:
            print("--endpoint는 --api book에서만 씁니다.", file=sys.stderr)
            return 2
        try:
            model = args.model or discover_model(
                args.base_url, args.api_key, args.timeout
            )
        except Exception as exc:
            print(f"모델 서버 확인 실패: {exc}", file=sys.stderr)
            return 1

    print(f"api={args.api} model={model} base_url={args.base_url}"
          + (f" endpoint={endpoint}" if endpoint else ""))
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
                api=args.api,
                endpoint=endpoint,
                prompts_per_request=args.prompts_per_request,
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
                api=args.api,
                endpoint=endpoint,
                prompts_per_request=args.prompts_per_request,
            )
            all_results.extend(results)
            summaries.append(
                summarize_group(results, wall_s, args.ttft_slo, args.e2e_slo)
            )

    payload = {
        "meta": {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "base_url": args.base_url,
            "api": args.api,
            "endpoint": endpoint,
            "batching": BOOK_ENDPOINTS[endpoint]["batching"] if endpoint else None,
            "model": model,
            "scenarios": scenario_names,
            "concurrency": args.concurrency,
            "requests_per_level": args.requests_per_level,
            "warmup": args.warmup,
            "ttft_slo_s": args.ttft_slo,
            "e2e_slo_s": args.e2e_slo,
            "unique_prefix": args.unique_prefix,
            "prompts_per_request": args.prompts_per_request,
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
