#!/usr/bin/env bash
set -euo pipefail

# F1c — 양자화가 지는 구간이 있는가.
#
# W8A8은 메모리 바운드에서 이득이지만 compute-bound 구간에서는 역양자화가
# 순비용이다. 4주차 E1과 같은 격자(prefill·decode × c=1,4,16,64)를 그대로 써서
# 부호가 뒤집히는 점을 찾는다. 격자를 같게 두는 이유는 4주차 추측 디코딩 결과와
# 나란히 놓고 읽기 위해서다.

cd "$(dirname "$0")"
source redeploy.sh

BENCH_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios prefill,decode
  --concurrency 1,4,16,64
  --requests-per-level 24
  --warmup 2
  --ttft-slo 2
  --e2e-slo 30
)

snap_startup() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 | tee "results/f1c-$1-startup.txt"
}

echo "=== F1c bf16 $(date -u +%H:%M:%S) UTC ==="
redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''
snap_startup bf16
for run in 1 2; do
  python3 benchmark.py "${BENCH_ARGS[@]}" --output "results/f1c-bf16-r${run}.json"
done

echo "=== F1c quant $(date -u +%H:%M:%S) UTC ==="
redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS='--quantization fp8'
snap_startup quant
for run in 1 2; do
  python3 benchmark.py "${BENCH_ARGS[@]}" --output "results/f1c-quant-r${run}.json"
done

echo "=== F1c done $(date -u +%H:%M:%S) UTC ==="
