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
# ★ 어텐션이 GEMM보다 먼저 와야 한다. Flash Attention 커널은 이름의 템플릿 인자에
#   `cutlass::bfloat16_t` 같은 타입이 들어가서, GEMM을 먼저 검사하면 통째로 GEMM으로
#   빨려 들어간다(실제로 첫 집계에서 13.56ms가 잘못 묶였다).
BUCKETS = [
    ("어텐션·KV 캐시", ("flash_fwd", "flash_bwd", "paged_attention", "attention",
                    "fmha", "mla", "reshape_and_cache", "concat_and_cache")),
    ("GEMM (선형 계층)", ("cutlass", "gemm", "gemv", "scaled_mm", "sm90", "sm80", "ampere", "cublas", "nvjet")),
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
    ap.add_argument(
        "--normalize",
        help="이 문자열이 든 커널의 호출 수로 나눠 비교한다 (예: flash_fwd_splitkv_kernel). "
             "두 트레이스가 담은 스텝 수가 다르면 총합 비교는 부호까지 거꾸로 읽힌다",
    )
    args = ap.parse_args()

    labels = (args.labels.split(",") if args.labels
              else [os.path.basename(p.rstrip("/\\")) for p in args.paths])

    summaries = [summarize(p) for p in args.paths]

    # ★ 정규화가 없으면 이 비교는 거짓말을 한다. 프로파일 구간의 길이는 트레이스마다
    #   다르다(실측에서 BF16 56스텝 vs FP8 96스텝). 총합만 놓고 보면 FP8이 GEMM에
    #   시간을 22% "더" 쓴 것처럼 보이지만, 스텝당으로 나누면 29% 덜 쓴다.
    #   그래서 어텐션 커널 호출 수처럼 스텝 수에 비례하는 값으로 나눈다.
    units = []
    for (_, by_name, _, _) in summaries:
        n = sum(cnt for name, (_, cnt) in by_name.items() if args.normalize and args.normalize in name)
        units.append(n if n else 1)
    if args.normalize and any(u == 1 for u in units):
        print(f"!! '{args.normalize}'에 걸리는 커널이 없는 트레이스가 있습니다 — 정규화 없이 비교합니다",
              file=sys.stderr)
        units = [1] * len(units)

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
    ua, ub = units
    if args.normalize:
        print(f"  단위: '{args.normalize}' 호출 1회당 (BF16 {ua:,}회 / FP8 {ub:,}회로 나눔)")
        unit = "us"
        scale_a, scale_b = ua, ub
    else:
        print("  단위: 트레이스 총합 (정규화 없음 — 구간 길이가 다르면 오해를 부른다)")
        unit = "ms"
        scale_a = scale_b = 1000.0

    print(f"  {'역할':<18} {labels[0]:>12} {labels[1]:>12} {'차이':>10}")
    for label in sorted(set(ba) | set(bb), key=lambda k: -(ba.get(k, [0])[0])):
        a = ba.get(label, [0.0, 0])[0] / scale_a
        b = bb.get(label, [0.0, 0])[0] / scale_b
        diff = f"{100 * (b / a - 1):+.1f}%" if a else "—"
        print(f"  {label:<18} {a:>9.2f} {unit} {b:>9.2f} {unit} {diff:>10}")
    a, b = ta / scale_a, tb / scale_b
    print(f"  {'합계':<18} {a:>9.2f} {unit} {b:>9.2f} {unit} {100 * (b / a - 1):>+9.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
