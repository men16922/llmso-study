#!/usr/bin/env python3
"""Triton의 Prometheus 메트릭에서 **평균 배치 크기**를 계산한다.

C2의 핵심 지표다. dynamic batching이 실제로 요청을 묶었는지를 "그런 것 같다"가
아니라 숫자로 증명한다.

    평균 배치 크기 = nv_inference_request_success / nv_inference_exec_count
                    (처리한 요청 수)            ÷ (모델을 실행한 횟수)

배칭이 꺼져 있으면 요청 하나당 실행 하나이므로 정확히 1.00이 나온다.
5ms를 기다려 6개씩 묶였다면 6.00 근처가 된다.

측정 구간의 값만 보려면 **부하 전후로 스냅샷을 찍어 차분**해야 한다. Triton의
카운터는 서버 기동 이후 누적이라 그냥 나누면 이전 실험까지 섞인다.

    python3 triton_metrics.py snapshot > before.txt
    #  ... 부하 ...
    python3 triton_metrics.py snapshot > after.txt
    python3 triton_metrics.py delta before.txt after.txt --model mobilenet_v2
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_METRICS_URL = "http://localhost:8011/metrics"

# 이 실험이 보는 카운터 4종.
COUNTERS = (
    "nv_inference_request_success",      # 성공한 요청 수
    "nv_inference_exec_count",           # 모델을 실행한 횟수 (배치 단위)
    "nv_inference_queue_duration_us",    # 큐에서 기다린 누적 시간
    "nv_inference_compute_infer_duration_us",  # 실제 연산 누적 시간
)

# 예: nv_inference_exec_count{model="mobilenet_v2",version="1"} 42
SAMPLE_RE = re.compile(r'^(?P<name>[a-zA-Z_:][\w:]*)\{(?P<labels>[^}]*)\}\s+(?P<value>[^\s]+)')


def parse_metrics(text: str, model: str | None = None) -> dict[str, float]:
    """Prometheus 텍스트에서 COUNTERS 값을 뽑는다. model을 주면 그 모델만 추린다."""
    values: dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = SAMPLE_RE.match(line)
        if not match:
            continue
        name = match.group("name")
        if name not in COUNTERS:
            continue
        if model and f'model="{model}"' not in match.group("labels"):
            continue
        try:
            values[name] = values.get(name, 0.0) + float(match.group("value"))
        except ValueError:
            continue
    return values


def fetch_metrics(url: str = DEFAULT_METRICS_URL, timeout_s: float = 5) -> str:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return response.read().decode("utf-8", errors="replace")


def delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    """구간 차분. 서버 재시작 등으로 카운터가 줄면 0으로 막는다."""
    return {
        name: max(0.0, after.get(name, 0.0) - before.get(name, 0.0))
        for name in COUNTERS
    }


def batch_stats(interval: dict[str, float]) -> dict[str, Any]:
    """차분값에서 평균 배치 크기와 요청당 큐 대기·연산 시간을 계산한다."""
    requests = interval.get("nv_inference_request_success", 0.0)
    executions = interval.get("nv_inference_exec_count", 0.0)
    queue_us = interval.get("nv_inference_queue_duration_us", 0.0)
    compute_us = interval.get("nv_inference_compute_infer_duration_us", 0.0)
    return {
        "requests": int(requests),
        "executions": int(executions),
        # 실행이 0이면 나눌 수 없다 (부하가 안 걸린 구간).
        "avg_batch_size": (requests / executions) if executions else None,
        "queue_ms_per_request": (queue_us / 1000 / requests) if requests else None,
        "compute_ms_per_request": (compute_us / 1000 / requests) if requests else None,
    }


def render(stats: dict[str, Any], label: str = "") -> str:
    def fmt(value: Any, digits: int) -> str:
        return "-" if value is None else f"{value:.{digits}f}"

    head = f"[{label}] " if label else ""
    return (
        f"{head}요청 {stats['requests']} / 실행 {stats['executions']}"
        f" → 평균 배치 크기 {fmt(stats['avg_batch_size'], 2)}"
        f" | 큐 대기 {fmt(stats['queue_ms_per_request'], 3)} ms/req"
        f" | 연산 {fmt(stats['compute_ms_per_request'], 3)} ms/req"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="현재 메트릭을 그대로 출력 (파일로 저장용)")
    snap.add_argument("--url", default=DEFAULT_METRICS_URL)

    diff = sub.add_parser("delta", help="두 스냅샷의 차분에서 평균 배치 크기 계산")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--model", default="mobilenet_v2")
    diff.add_argument("--label", default="")

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        try:
            sys.stdout.write(fetch_metrics(args.url))
        except Exception as exc:
            print(f"메트릭을 가져오지 못했습니다({args.url}): {exc}", file=sys.stderr)
            return 1
        return 0

    for path in (args.before, args.after):
        if not path.exists():
            print(f"파일이 없습니다: {path}", file=sys.stderr)
            return 1
    before = parse_metrics(args.before.read_text(encoding="utf-8"), args.model)
    after = parse_metrics(args.after.read_text(encoding="utf-8"), args.model)
    stats = batch_stats(delta(before, after))
    print(render(stats, args.label))
    if stats["avg_batch_size"] is None:
        print("⚠️ 이 구간에 실행이 없습니다 — 부하가 안 걸렸거나 모델명이 틀렸습니다.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
