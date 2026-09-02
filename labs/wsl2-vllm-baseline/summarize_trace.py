#!/usr/bin/env python3
"""PyTorch Profiler 트레이스에서 GPU 커널 시간을 집계한다.

vLLM은 `VLLM_TORCH_PROFILER_DIR`이 설정돼 있을 때 `/start_profile`·`/stop_profile`을
열고, 멈출 때 Chrome trace(`*.pt.trace.json[.gz]`)를 그 디렉터리에 떨어뜨린다.
여기서 필요한 것은 하나다 — **어떤 커널이 GPU 시간을 얼마나 먹었는가.**

    python3 summarize_trace.py results/f2-traces/bf16 --top 12
    python3 summarize_trace.py results/f2-traces/bf16 results/f2-traces/quant --top 12

인자를 둘 주면 두 트레이스를 같은 분류로 나란히 놓고 차이를 낸다. 커널 이름은
정밀도가 바뀌면 통째로 달라지므로(예: cutlass 계열이 fp8 커널로 교체된다)
이름끼리 짝지어 봐야 소용이 없다. 그래서 **역할별로 묶어서** 비교한다.

표준 라이브러리만 쓴다 — 저장소의 다른 도구와 같은 원칙이다.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import defaultdict

# 커널 이름 → 역할. 앞에서부터 처음 걸리는 것으로 분류한다.
# 정밀도가 바뀌면 커널 이름이 통째로 달라지기 때문에, 이름이 아니라 역할로 묶어야
# BF16과 FP8을 같은 줄에 놓을 수 있다.
BUCKETS = [
    ("GEMM (선형 계층)", ("cutlass", "gemm", "scaled_mm", "sm90", "sm80", "ampere", "cublas", "nvjet")),
    ("어텐션", ("attention", "flash", "paged", "fmha", "mla")),
    ("정규화·활성화", ("rms_norm", "layernorm", "silu", "gelu", "act_and_mul")),
    ("양자화·스케일", ("quant", "scale", "fp8", "dequant")),
    ("임베딩·샘플링", ("embedding", "sampling", "topk", "softmax", "argmax", "gather")),
    ("복사·형변환", ("memcpy", "copy", "cast", "convert", "elementwise", "vectorized")),
    ("reduce·기타", ("reduce", "cat", "index", "fill", "triton")),
]


def bucket_of(name: str) -> str:
    low = name.lower()
    for label, keys in BUCKETS:
        if any(k in low for k in keys):
            return label
    return "분류 안 됨"


def load_events(path: str):
    """디렉터리면 안의 트레이스를 전부, 파일이면 그 하나를 읽는다."""
    files = []
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            files += [os.path.join(root, n) for n in names if ".trace.json" in n]
    else:
        files = [path]
    if not files:
        raise SystemExit(f"트레이스를 찾지 못했습니다: {path}")

    events = []
    for f in sorted(files):
        opener = gzip.open if f.endswith(".gz") else open
        with opener(f, "rt", encoding="utf-8") as fh:
            events += json.load(fh).get("traceEvents", [])
    return files, events


def kernel_time(events):
    """커널 이벤트만 골라 이름별 총 GPU 시간(us)과 호출 수를 낸다.

    `cat`이 'kernel'인 것만 센다. 'cuda_runtime'은 CPU 쪽 launch라 이중 계상이 되고,
    'gpu_memcpy'는 따로 남겨 둔다.
    """
    by_name = defaultdict(lambda: [0.0, 0])
    for e in events:
        cat = e.get("cat")
        if cat not in ("kernel", "gpu_memcpy", "gpu_memset"):
            continue
        dur = e.get("dur")
        if dur is None:
            continue
        slot = by_name[e.get("name", "?")]
        slot[0] += float(dur)
        slot[1] += 1
    return by_name


def summarize(path):
    files, events = load_events(path)
    by_name = kernel_time(events)
    by_bucket = defaultdict(lambda: [0.0, 0])
    for name, (dur, n) in by_name.items():
        slot = by_bucket[bucket_of(name)]
        slot[0] += dur
        slot[1] += n
    total = sum(d for d, _ in by_bucket.values())
    return files, by_name, by_bucket, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="트레이스 파일 또는 디렉터리 (1개 또는 2개)")
    ap.add_argument("--top", type=int, default=12, help="커널 이름별 상위 몇 개까지 보일지")
    ap.add_argument("--labels", help="쉼표로 구분한 계열 이름 (예: BF16,FP8)")
    args = ap.parse_args()

    labels = (args.labels.split(",") if args.labels
              else [os.path.basename(p.rstrip("/\\")) for p in args.paths])

    summaries = [summarize(p) for p in args.paths]

    for label, (files, by_name, _, total) in zip(labels, summaries):
        print(f"\n=== {label} — GPU 커널 시간 상위 {args.top} ===")
        print(f"  트레이스 {len(files)}개 · 총 커널 시간 {total / 1000:.1f} ms")
        rows = sorted(by_name.items(), key=lambda kv: -kv[1][0])[: args.top]
        for name, (dur, n) in rows:
            short = name if len(name) <= 58 else name[:55] + "..."
            print(f"  {dur / 1000:>9.2f} ms  {100 * dur / total:>5.1f}%  x{n:<6d} {short}")

    print("\n=== 역할별 ===")
    if len(summaries) == 1:
        _, _, by_bucket, total = summaries[0]
        for label, (dur, n) in sorted(by_bucket.items(), key=lambda kv: -kv[1][0]):
            print(f"  {dur / 1000:>9.2f} ms  {100 * dur / total:>5.1f}%  x{n:<7d} {label}")
        return 0

    (_, _, ba, ta), (_, _, bb, tb) = summaries[0], summaries[1]
    print(f"  {'역할':<18} {labels[0]:>12} {labels[1]:>12} {'차이':>10}")
    for label in sorted(set(ba) | set(bb), key=lambda k: -(ba.get(k, [0])[0])):
        a, b = ba.get(label, [0.0, 0])[0], bb.get(label, [0.0, 0])[0]
        diff = f"{100 * (b / a - 1):+.1f}%" if a else "—"
        print(f"  {label:<18} {a / 1000:>9.2f} ms {b / 1000:>9.2f} ms {diff:>10}")
    print(f"  {'합계':<18} {ta / 1000:>9.2f} ms {tb / 1000:>9.2f} ms "
          f"{100 * (tb / ta - 1):>+9.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
