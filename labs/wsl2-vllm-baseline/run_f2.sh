#!/usr/bin/env bash
set -euo pipefail

# F2 — 3계층 프로파일링. 과녁은 F1c가 정한다.
#
# CH9은 Nsight 딥다이브에서 "양자화 전후 GEMM 커널 실행시간이 거의 같았다"고 적었다.
# 그 관측이 이 랩톱에서도 성립하는지를 커널 시간으로 직접 확인한다.
#
# 계층: ① 서버 지표 → ② PyTorch Profiler(연산자·커널) → ③ 문제 커널 1개
# Nsight Systems는 컨테이너 안에 nsys 바이너리가 있어야 하므로 ⓪에서 먼저 확인하고,
# 없으면 ②까지로 축소한다(설계의 중단 기준).
#
# ★ v0.23.0에서 VLLM_TORCH_PROFILER_DIR은 없어졌다. 첫 시도에서 서버가
#   "Unknown vLLM environment variable"을 찍고 /start_profile이 404를 냈다.
#   프로파일러 설정이 --profiler-config.* CLI 플래그로 옮겨갔기 때문이다
#   (vllm/config/profiler.py의 ProfilerConfig).
#
# 트레이스는 PVC 위(허깅페이스 캐시 마운트)에 떨어뜨려 파드가 죽어도 남긴다.
# 크기 관리는 iteration 옵션으로 한다 — with_stack을 끄고(기본이 켜짐, 트레이스가
# 몇 배로 커진다), 앞 20 iteration을 버리고, 100 iteration만 담는다.

cd "$(dirname "$0")"
source redeploy.sh

PROF_DIR=/root/.cache/huggingface/profiles
NS=llm-serving-lab

PROF_ARGS="--profiler-config.profiler=torch"
PROF_ARGS="$PROF_ARGS --profiler-config.torch_profiler_dir=$PROF_DIR"
PROF_ARGS="$PROF_ARGS --profiler-config.torch_profiler_with_stack=false"
PROF_ARGS="$PROF_ARGS --profiler-config.ignore_frontend=true"
PROF_ARGS="$PROF_ARGS --profiler-config.delay_iterations=20"
PROF_ARGS="$PROF_ARGS --profiler-config.max_iterations=100"

profile_arm() {  # profile_arm <tag> <extra_args>
  local tag="$1" extra="$2"
  echo "=== F2 $tag $(date -u +%H:%M:%S) UTC ==="

  redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS="$extra $PROF_ARGS"

  kubectl -n "$NS" logs deploy/vllm-baseline \
    | grep -E 'Available KV cache memory|GPU KV cache size|Maximum concurrency' \
    | tail -3 | tee "results/f2-${tag}-startup.txt"

  # 프로파일러를 켜기 전에 한 번 태워 컴파일·CUDA graph 캡처를 트레이스 밖으로 뺀다.
  python3 benchmark.py --base-url http://127.0.0.1:8000 --scenarios decode \
    --concurrency 4 --requests-per-level 4 --warmup 1 --output /tmp/f2-warm.json >/dev/null 2>&1 || true

  # 프로파일 구간은 짧게 잡는다. decode 512토큰짜리를 그대로 트레이싱하면 스텝마다
  # 커널 수백 개가 쌓여 트레이스가 기가바이트로 간다. short(64토큰)로도 디코드
  # 스텝의 커널 구성은 같으므로 연산자별 평균을 뽑는 데 충분하다.
  curl -fsS -X POST http://127.0.0.1:8000/start_profile
  python3 benchmark.py --base-url http://127.0.0.1:8000 \
    --scenarios short --concurrency 8 --requests-per-level 16 --warmup 0 \
    --output "results/f2-${tag}-load.json"
  curl -fsS -X POST http://127.0.0.1:8000/stop_profile

  # 트레이스는 비동기로 떨어진다. 파일이 안정될 때까지 기다린다.
  local pod prev=0 cur=0 i
  pod="$(kubectl -n "$NS" get pod -l app=vllm-baseline -o jsonpath='{.items[0].metadata.name}')"
  for ((i = 0; i < 60; i++)); do
    sleep 3
    cur="$(kubectl -n "$NS" exec "$pod" -- sh -c "du -sb $PROF_DIR 2>/dev/null | cut -f1" || echo 0)"
    [ "$cur" != "0" ] && [ "$cur" = "$prev" ] && break
    prev="$cur"
  done

  kubectl -n "$NS" exec "$pod" -- sh -c "ls -la $PROF_DIR" | tee "results/f2-${tag}-trace-ls.txt"
  mkdir -p "results/f2-traces/$tag"
  kubectl -n "$NS" exec "$pod" -- sh -c "cd $PROF_DIR && tar cf - ." \
    | tar xf - -C "results/f2-traces/$tag"
  kubectl -n "$NS" exec "$pod" -- sh -c "rm -rf $PROF_DIR/*" || true
}

kubectl -n "$NS" get pod -l app=vllm-baseline -o name >/dev/null

profile_arm bf16 ''
profile_arm quant '--quantization fp8'

# 프로파일러를 원복한다. 켜 둔 채로 두면 다음 실험의 저울이 달라진다.
redeploy GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''

echo "=== F2 done $(date -u +%H:%M:%S) UTC ==="
