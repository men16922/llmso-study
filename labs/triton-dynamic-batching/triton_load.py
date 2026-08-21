#!/usr/bin/env python3
"""Triton에 동시 요청을 걸어 처리량과 지연 백분위를 잰다 (C2용).

benchmark.py와 달리 대상이 LLM이 아니라 이미지 분류 모델이므로 TTFT·토큰 개념이
없다. 재는 것은 **초당 추론 수와 요청 지연**뿐이고, 배치가 실제로 몇 개씩 묶였는지는
triton_metrics.py가 서버 카운터에서 따로 뽑는다.

    python3 triton_load.py --concurrency 1,8,32 --requests 300

tritonclient는 이 모듈을 import할 때가 아니라 실제 요청을 보낼 때 필요하다
(게이트가 오프라인으로 순수 로직만 테스트할 수 있게 지연 import한다).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

DEFAULT_URL = "localhost:8009"
DEFAULT_MODEL = "mobilenet_v2"
_local = threading.local()


def percentile(values: list[float], quantile: float) -> float | None:
    """benchmark.py와 같은 선형보간 방식 — 두 랩의 숫자를 같은 기준으로 읽기 위해."""
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * quantile
    lower, upper = math.floor(rank), math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize(latencies: list[float], wall_s: float, concurrency: int,
              failures: int = 0) -> dict[str, Any]:
    """지연 목록과 벽시계 시간에서 요약 통계를 만든다."""
    count = len(latencies)
    return {
        "concurrency": concurrency,
        "requests": count + failures,
        "failures": failures,
        "wall_s": wall_s,
        "inf_per_s": (count / wall_s) if wall_s > 0 else None,
        "p50_ms": (lambda v: None if v is None else v * 1000)(percentile(latencies, 0.50)),
        "p95_ms": (lambda v: None if v is None else v * 1000)(percentile(latencies, 0.95)),
        "mean_ms": statistics.fmean(latencies) * 1000 if latencies else None,
    }


def make_client(url: str):
    """스레드마다 클라이언트를 하나씩 둔다.

    요청마다 새로 만들면 접속 비용이 지연에 섞여 dynamic batching 효과를 가린다.
    """
    import tritonclient.http as httpclient  # 지연 import — 테스트는 여기까지 안 온다

    if not hasattr(_local, "client"):
        _local.client = httpclient.InferenceServerClient(url=url)
    return _local.client


def infer_once(url: str, model: str, image) -> float:
    import tritonclient.http as httpclient

    tensor = httpclient.InferInput("input", image.shape, "FP32")
    tensor.set_data_from_numpy(image)
    started = time.perf_counter()
    make_client(url).infer(
        model, inputs=[tensor], outputs=[httpclient.InferRequestedOutput("output")]
    )
    return time.perf_counter() - started


def run_level(task: Callable[[], float], concurrency: int, requests: int,
              warmup: int = 20) -> dict[str, Any]:
    """동시성 하나를 측정한다. task는 요청 하나를 보내고 지연(초)을 돌려주는 함수."""
    latencies: list[float] = []
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(concurrency) as executor:
        for future in [executor.submit(task) for _ in range(warmup)]:
            try:
                future.result()
            except Exception:  # warmup 실패는 무시한다
                pass
        started = time.perf_counter()
        futures = [executor.submit(task) for _ in range(requests)]
        for future in futures:
            try:
                latencies.append(future.result())
            except Exception:
                failures += 1
        wall_s = time.perf_counter() - started
    return summarize(latencies, wall_s, concurrency, failures)


def parse_concurrency(value: str) -> list[int]:
    values = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not values or any(item < 1 for item in values):
        raise argparse.ArgumentTypeError("동시성은 1 이상의 쉼표 구분 정수여야 합니다.")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--concurrency", type=parse_concurrency, default=[1, 8, 32])
    parser.add_argument("--requests", type=int, default=300)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--label", default="", help="결과에 붙일 이름 (예: delay=5000)")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        import numpy as np
    except ImportError:
        print("numpy가 필요합니다: pip install numpy tritonclient[http]", file=sys.stderr)
        return 1

    # 내용은 중요하지 않다 — 모든 요청의 연산량이 정확히 같다는 점이 중요하다.
    # (그래서 dynamic batching이 성립한다. LLM에서 깨지는 것이 바로 이 전제다.)
    # ★ 배치 차원(맨 앞의 1)을 반드시 포함해야 한다.
    # config.pbtxt의 `dims: [3, 224, 224]`는 **샘플 하나의** 모양이고,
    # Triton이 max_batch_size를 보고 배치 축을 앞에 붙인다. 하지만 클라이언트가
    # 보내는 텐서는 그 배치 축까지 포함한 (N, 3, 224, 224)여야 한다.
    # (3, 224, 224)로 보내면 서버가 전부 거부한다 — config는 멀쩡한데 요청만 실패해
    # 원인을 찾기 어렵다. 2026-08-21 실측에서 300건 전량 실패로 드러났다.
    image = np.random.rand(1, 3, 224, 224).astype(np.float32)

    summaries = []
    for concurrency in args.concurrency:
        summary = run_level(
            lambda: infer_once(args.url, args.model, image),
            concurrency, args.requests, args.warmup,
        )
        summary["label"] = args.label
        summaries.append(summary)
        print(
            f"c={summary['concurrency']:<3} "
            f"{summary['inf_per_s'] or 0:8.1f} inf/s  "
            f"p50 {summary['p50_ms'] or 0:7.2f} ms  "
            f"p95 {summary['p95_ms'] or 0:7.2f} ms  "
            f"실패 {summary['failures']}"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {"meta": {"url": args.url, "model": args.model, "label": args.label},
                 "summaries": summaries},
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        print(f"result={args.output}")
    return 0 if all(s["failures"] == 0 for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
