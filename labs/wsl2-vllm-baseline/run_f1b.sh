#!/usr/bin/env bash
set -euo pipefail

# F1b — 양자화의 이득을 되돌려 놓는다 (제거 실험).
#
# 세 팔을 같은 저울에 올린다.
#   ① bf16        : BF16, util 0.85            (기준)
#   ② quant       : FP8,  util 0.85            (예산이 늘어난 상태)
#   ③ quant-frozen: FP8,  util을 조여 ①과 KV 예산을 맞춘 상태
#
# ③이 ①로 주저앉으면 이득은 전부 메모리였다는 뜻이고,
# ②에 가까우면 커널 이득이 실재한다는 뜻이다.
#
# ③의 util은 손으로 고르지 않는다 — ①의 Maximum concurrency를 목표로 놓고
# 선형 보정으로 최대 4회까지 재기동하며 ±5% 안에 넣는다. KV 예산은 정적 공식이
# 아니라 기동 시 프로파일링 결과라(3주차 관측) 계산만으로는 맞출 수 없다.

cd "$(dirname "$0")"
source redeploy.sh

BENCH_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios decode
  --concurrency 16
  --requests-per-level 32
  --warmup 2
  --ttft-slo 2
  --e2e-slo 30
)

# 기동 로그에서 Maximum concurrency 숫자만 꺼낸다 (예: 59.50x -> 59.50)
read_conc() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline 2>/dev/null \
    | grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' \
    | tail -1 | grep -oE '[0-9.]+x$' | tr -d 'x'
}

snap_startup() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 | tee "results/f1b-$1-startup.txt"
}

run_arm() {  # run_arm <tag>
  local tag="$1" run
  snap_startup "$tag"
  for run in 1 2 3; do
    python3 benchmark.py "${BENCH_ARGS[@]}" --output "results/f1b-${tag}-r${run}.json"
  done
}

# ---------- ① BF16 기준 ----------
echo "=== F1b bf16 $(date -u +%H:%M:%S) UTC ==="
redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''
BASE_CONC="$(read_conc)"
echo "bf16 Maximum concurrency = ${BASE_CONC}x"
echo "$BASE_CONC" > results/f1b-bf16-concurrency.txt
run_arm bf16

# ---------- ② FP8 기본 ----------
echo "=== F1b quant $(date -u +%H:%M:%S) UTC ==="
redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS='--quantization fp8'
QUANT_CONC="$(read_conc)"
echo "quant Maximum concurrency = ${QUANT_CONC}x"
run_arm quant

# ---------- ③ FP8 예산 동결 ----------
# 예산은 util에 거의 선형이다. 현재 (util=0.85, QUANT_CONC)에서 목표 BASE_CONC로
# 가는 util을 추정하고, 실측 후 남은 오차만큼 다시 보정한다.
util=0.85
applied_util=0.85
attempt=0
: > results/f1b-frozen-search.txt
while [ "$attempt" -lt 4 ]; do
  attempt=$((attempt + 1))
  cur="$(read_conc)"
  util=$(python3 - "$util" "$cur" "$BASE_CONC" <<'PY'
import sys
util, cur, target = (float(x) for x in sys.argv[1:4])
# KV 예산 = util * TOTAL - OVERHEAD 이므로 conc도 util에 선형이다.
# 두 점 (util, cur)과 (0, -overhead_conc)을 알 수 없으니, 기울기를 GPU 전체 대비로 근사한다.
# 실측 한 점에서 출발해 비례식으로 당기고, 다음 회차가 남은 오차를 먹는다.
TOTAL_CONC_PER_UTIL = cur / util if util else 0.0
step = (target - cur) / TOTAL_CONC_PER_UTIL if TOTAL_CONC_PER_UTIL else 0.0
print(f"{max(0.30, min(0.95, util + step)):.4f}")
PY
)
  echo "attempt ${attempt}: conc=${cur}x -> next util=${util}" | tee -a results/f1b-frozen-search.txt
  # 목표 ±5% 안에 들어왔으면 멈춘다
  if python3 -c "import sys;c=float('$cur');b=float('$BASE_CONC');sys.exit(0 if abs(c-b)/b<=0.05 else 1)"; then
    echo "frozen 성립: ${cur}x vs 기준 ${BASE_CONC}x (오차 5% 이내), util=${applied_util}"       | tee -a results/f1b-frozen-search.txt
    break
  fi
  redeploy GPU_MEMORY_UTILIZATION="$util" EXTRA_ARGS='--quantization fp8'
  applied_util="$util"
done

echo "$applied_util" > results/f1b-frozen-util.txt
echo "=== F1b quant-frozen (util=$applied_util) $(date -u +%H:%M:%S) UTC ==="
run_arm quant-frozen

echo "=== F1b done $(date -u +%H:%M:%S) UTC ==="
