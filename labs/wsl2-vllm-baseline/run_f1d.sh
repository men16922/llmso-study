#!/usr/bin/env bash
set -euo pipefail

# F1d — 평평한 선이 꺾이는 지점을 찾는다.
#
# F1a와 F1a2에서 KV 예산을 15.64x에서 59.50x까지(3.8배) 흔들었는데
# decode 처리량도 prefill 처리량도 움직이지 않았다. 예산이 병목이 아니었다는
# 뜻이지만, "바인딩되는 구간을 애초에 안 밟았다"는 반론이 가능하다.
# 그 반론을 닫으려면 예산을 더 조여서 꺾이는 점을 실제로 보여줘야 한다.
#
# 그래서 util을 0.45 아래로 더 내린다. BF16 가중치·활성화·CUDA graph가
# 약 3.69 GiB를 먼저 먹으므로 util 0.36이면 KV로 남는 건 0.6 GiB 남짓이다.
#
# ★ F1a2의 지표 수집은 비어 있었다. `^vllm:num_requests_running ` 처럼 이름 뒤에
#   공백을 요구했는데 실제 노출 형식은 `vllm:num_requests_running{engine="0",...} 16.0`
#   이라 라벨 블록에 막혔다. 여기서는 라벨을 포함해 잡는다.

cd "$(dirname "$0")"
source redeploy.sh

PREFILL_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios prefill --concurrency 64 --requests-per-level 64
  --warmup 2 --unique-prefix --ttft-slo 2 --e2e-slo 60
)

# ★ 리다이렉트는 while 루프가 아니라 서브셸에 붙여야 한다. `( while ...; done > 파일 ) &`
#   로 쓰면 서브셸 자신의 fd 1이 명령 치환 파이프를 계속 쥐고 있어 $( )가 EOF를 못 받고,
#   호출한 스크립트가 영원히 멈춘다 — 첫 실행에서 실제로 그렇게 멈췄다.
sample_start() {  # sample_start <파일>
  ( while :; do
      curl -fsS http://127.0.0.1:8000/metrics 2>/dev/null \
        | grep -E '^vllm:(num_requests_running|num_requests_waiting|kv_cache_usage_perc|num_preemptions_total)\{' \
        | sed "s/^/$(date -u +%H:%M:%S) /"
      sleep 0.4
    done ) > "$1" &
  echo $!
}

for util in 0.33 0.36 0.40 0.45 0.85; do
  tag="mem${util#0.}"
  echo "=== F1d $tag (util=$util) $(date -u +%H:%M:%S) UTC ==="

  if ! redeploy GPU_MEMORY_UTILIZATION="$util" EXTRA_ARGS=''; then
    echo "!! $tag 기동 실패 — 예산 하한을 넘었다" >&2
    kubectl -n llm-serving-lab logs deploy/vllm-baseline 2>/dev/null \
      | grep -iE 'ValueError|memory' | tail -3 > "results/f1d-${tag}-FAILED.txt" || true
    continue
  fi

  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 | tee "results/f1d-${tag}-startup.txt"

  sampler="$(sample_start "results/f1d-${tag}-samples.txt")"
  python3 benchmark.py "${PREFILL_ARGS[@]}" --output "results/f1d-${tag}-prefill.json"
  kill "$sampler" 2>/dev/null || true

  curl -fsS http://127.0.0.1:8000/metrics \
    | grep -E '^vllm:(num_preemptions_total|prefix_cache_hits_total|prefix_cache_queries_total|prompt_tokens_total|generation_tokens_total)\{' \
    > "results/f1d-${tag}-metrics.txt" || true
done

# 프리필 프롬프트가 정확히 몇 토큰인지 확정한다. 글에서 "요청당 KV 수요"를
# 계산할 때 이 값을 쓰는데, 벤치마크 결과 JSON에는 프롬프트 토큰이 안 남는다.
# 서버 누적 카운터의 차이로 잰다 — prefix cache가 합치지 못하게 --unique-prefix.
before="$(curl -fsS http://127.0.0.1:8000/metrics | grep -oE '^vllm:prompt_tokens_total\{[^}]*\} [0-9.]+' | grep -oE '[0-9.]+$')"
python3 benchmark.py --base-url http://127.0.0.1:8000 --scenarios prefill   --concurrency 1 --requests-per-level 4 --warmup 0 --unique-prefix   --output /tmp/f1d-probe.json >/dev/null
after="$(curl -fsS http://127.0.0.1:8000/metrics | grep -oE '^vllm:prompt_tokens_total\{[^}]*\} [0-9.]+' | grep -oE '[0-9.]+$')"
python3 -c "print(f'prefill 프롬프트 토큰/요청 = {(float('$after') - float('$before')) / 4:.0f}')"   | tee results/f1d-prompt-tokens.txt

echo "=== F1d done $(date -u +%H:%M:%S) UTC ==="
