#!/usr/bin/env bash
set -euo pipefail

# F5 — 대시보드 증거용 부하.
#
# 앞선 F1~F2의 결론은 벤치마크 클라이언트와 0.4초 간격 지표 수집으로 냈다.
# 그런데 Prometheus는 15초에 한 번 긁는다. 각 측정이 10~20초짜리 버스트라
# 되짚어 보면 스크랩 사이로 빠져나가 있다 — 실제로 F1d의 KV 사용률 피크 0.998을
# Prometheus는 0.078까지밖에 못 봤다.
#
# 그래서 같은 대비를 **한 구간에 3분씩** 다시 걸어 대시보드에 남긴다.
# 숫자를 새로 만드는 게 아니라, 이미 낸 결론을 모니터링 스택에서도 보이게 하는 것이다.
#
#   A) BF16 util 0.85 · decode  — 예산이 놀고 있는 상태
#   B) FP8  util 0.85 · decode  — 같은 부하, 처리량만 오른다
#   C) BF16 util 0.33 · prefill — 예산이 실제로 걸리는 상태(선점 발생)
#
# 구간 시각을 results/f5-timeline.txt에 남긴다. 그래프 범위를 그걸로 맞춘다.

cd "$(dirname "$0")"
source redeploy.sh

TL=results/f5-timeline.txt
: > "$TL"
note() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)  $*" | tee -a "$TL"; }

phase() {  # phase <이름> <util> <extra_args> <시나리오> <동시성> <요청수>
  local name="$1" util="$2" extra="$3" scen="$4" conc="$5" reqs="$6"
  note "=== $name 준비 (util=$util  EXTRA_ARGS='$extra') ==="
  redeploy GPU_MEMORY_UTILIZATION="$util" EXTRA_ARGS="$extra"

  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 | tee "results/f5-${name}-startup.txt"

  # 스크랩이 확실히 한 번 지나가도록 부하 전에 20초 비운다. 그래야 그래프에서
  # 구간 경계가 보인다.
  sleep 20
  note "$name 부하 시작"
  python3 benchmark.py --base-url http://127.0.0.1:8000 \
    --scenarios "$scen" --concurrency "$conc" --requests-per-level "$reqs" \
    --warmup 2 --ttft-slo 2 --e2e-slo 60 \
    --output "results/f5-${name}.json" ${7:-}
  note "$name 부하 끝"
  sleep 20
}

phase A-bf16-idle-budget  0.85 ''                    decode  16 480
phase B-fp8-idle-budget   0.85 '--quantization fp8'  decode  16 480
phase C-bf16-bound-budget 0.33 ''                    prefill 64 640 --unique-prefix

note "=== F5 done ==="

# 저울을 기준선으로 돌려놓는다.
redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''
