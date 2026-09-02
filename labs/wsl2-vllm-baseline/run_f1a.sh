#!/usr/bin/env bash
set -euo pipefail

# F1a — KV 예산을 독립 변수로 놓는다.
#
# BF16 한 팔만 두고 GPU_MEMORY_UTILIZATION을 스윕해 KV 예산을 인위적으로 돌린다.
# 각 점에서 기동 로그의 `Maximum concurrency`(= KV 예산)와 decode c=16 처리량을
# 기록하면, 이후 모든 팔(양자화·예산동결·복제)을 얹어 읽을 좌표계 하나가 생긴다.
#
# 모델·이미지·max_num_seqs·max_model_len은 전부 고정이다. 움직이는 값은 util 하나.

cd "$(dirname "$0")"
source redeploy.sh

COMMON_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios decode
  --concurrency 16
  --requests-per-level 32
  --warmup 2
  --ttft-slo 2
  --e2e-slo 30
)

for util in 0.55 0.65 0.75 0.85 0.90; do
  tag="mem${util#0.}"   # 0.55 -> mem55
  echo "=== F1a $tag (util=$util) $(date -u +%H:%M:%S) UTC ==="

  if ! redeploy GPU_MEMORY_UTILIZATION="$util" EXTRA_ARGS=''; then
    echo "!! $tag 기동 실패 — 건너뜁니다" >&2
    continue
  fi

  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 \
    | tee "results/f1a-${tag}-startup.txt"

  python3 benchmark.py "${COMMON_ARGS[@]}" --output "results/f1a-${tag}.json"
done

echo "=== F1a done $(date -u +%H:%M:%S) UTC ==="
