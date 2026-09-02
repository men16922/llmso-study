#!/usr/bin/env bash
set -euo pipefail

# F1a-2 — 같은 KV 예산 스윕을 "예산이 노는 워크로드"와 "예산이 걸리는 워크로드"
#         양쪽에서 동시에 잰다.
#
# F1a-1(decode c=16)은 곡선이 평평했다. 이유는 계산하면 바로 나온다 —
# decode 요청 하나는 프롬프트 약 40토큰 + 출력 512토큰이라 KV 수요가 약 550토큰이고,
# c=16이면 8,800토큰이다. util 0.55에서도 KV는 109,001토큰이므로 12배가 남는다.
# 예산이 놀고 있으면 예산을 늘려도 처리량은 안 움직인다. 그것도 결과지만,
# 좌표계로 쓰려면 기울기가 있는 구간이 반드시 하나는 필요하다.
#
# 그래서 수요를 예산 가까이 끌어올린 두 번째 워크로드를 같은 배포에서 이어 잰다.
#   ① prefill        — 프롬프트가 약 2,400토큰
#   ② c=64           — 64 x 2,400 = 약 154,000토큰
#   ③ --unique-prefix— 요청 프롬프트가 같으면 prefix cache가 전부 합쳐버려
#                      KV 수요가 1/64로 준다. 그걸 막아야 예산이 실제로 걸린다.
#
# ★ util 0.90은 이 랩톱에서 기동 자체가 안 된다 — 자유 메모리가 10.79 GiB인데
#   0.90이 요구하는 것도 10.79 GiB다(results/f1a-mem90-FAILED.txt).
#   윈도우 데스크톱이 이미 1.2 GiB를 쥐고 있어서다. 그래서 상단은 0.85가 천장이고,
#   대신 0.45를 밑으로 붙여 곡선의 폭을 넓혔다.
#
# 배포 한 번에 두 워크로드를 다 태우는 이유: 롤아웃이 1회 70~90초라 스윕에서
# 제일 비싼 부분이고, 같은 파드에서 재면 두 워크로드의 KV 예산이 정확히 같다.

cd "$(dirname "$0")"
source redeploy.sh

DECODE_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios decode --concurrency 16 --requests-per-level 32
  --warmup 2 --ttft-slo 2 --e2e-slo 30
)
PREFILL_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios prefill --concurrency 64 --requests-per-level 64
  --warmup 2 --unique-prefix --ttft-slo 2 --e2e-slo 30
)

for util in 0.45 0.55 0.65 0.75 0.85; do
  tag="mem${util#0.}"
  echo "=== F1a2 $tag (util=$util) $(date -u +%H:%M:%S) UTC ==="

  if ! redeploy GPU_MEMORY_UTILIZATION="$util" EXTRA_ARGS=''; then
    echo "!! $tag 기동 실패 — 건너뜁니다" >&2
    continue
  fi

  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 | tee "results/f1a2-${tag}-startup.txt"

  # ① 예산이 노는 쪽
  python3 benchmark.py "${DECODE_ARGS[@]}" --output "results/f1a2-${tag}-decode.json"

  # ② 예산이 걸리는 쪽. running/waiting/사용률은 게이지라 부하가 끝난 뒤에 찍으면
  #    전부 0이다 — 부하 "중에" 0.5초 간격으로 샘플링해야 걸린 증거가 남는다.
  ( while :; do
      curl -fsS http://127.0.0.1:8000/metrics 2>/dev/null \
        | grep -E '^vllm:(num_requests_running|num_requests_waiting|kv_cache_usage_perc) ' \
        | sed "s/^/$(date -u +%H:%M:%S) /"
      sleep 0.5
    done > "results/f1a2-${tag}-samples.txt" ) &
  sampler=$!

  python3 benchmark.py "${PREFILL_ARGS[@]}" --output "results/f1a2-${tag}-prefill.json"

  kill "$sampler" 2>/dev/null || true

  # 누적 카운터는 끝나고 한 번 찍으면 된다.
  curl -fsS http://127.0.0.1:8000/metrics \
    | grep -E '^vllm:(num_preemptions_total|prefix_cache_hits_total|prefix_cache_queries_total|prompt_tokens_total|generation_tokens_total) ' \
    > "results/f1a2-${tag}-metrics.txt" || true
done

echo "=== F1a2 done $(date -u +%H:%M:%S) UTC ==="
