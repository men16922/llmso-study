#!/usr/bin/env bash
# F5 구간이 끝난 직후 Prometheus 대시보드 4장을 굽는다.
# 범위는 "지금부터 뒤로 25분" — F5 세 구간(약 14분)을 모두 덮는다.
set -euo pipefail
cd "$(dirname "$0")"
P="PYTHONIOENCODING=utf-8 python prom_shot.py"
R="--range 25m"

# ① 예산은 놀고 있다 → 조이면 찬다. 이 글의 headline.
eval $P dash-01-kv-usage.png $R --height 900 \
  "'sum(vllm:kv_cache_usage_perc)'"

# ② 같은 부하, 처리량만 오른다 (A vs B). 동시 실행 요청 수는 그대로여야 한다.
eval $P dash-02-throughput.png $R --height 1750 \
  "'sum(rate(vllm:generation_tokens_total[1m]))'" \
  "'sum(vllm:num_requests_running)'"

# ③ 예산이 걸리는 순간 — 대기 요청과 선점.
eval $P dash-03-binding.png $R --height 1750 \
  "'sum(vllm:num_requests_waiting)'" \
  "'sum(vllm:num_preemptions_total)'"

# ④ GPU 쪽에서 본 같은 구간.
eval $P dash-04-gpu.png $R --height 1750 \
  "'DCGM_FI_DEV_FB_USED{gpu=\"0\"}'" \
  "'DCGM_FI_DEV_GPU_UTIL{gpu=\"0\"}'"
