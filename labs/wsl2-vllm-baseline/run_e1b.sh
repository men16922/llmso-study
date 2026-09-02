#!/usr/bin/env bash
set -euo pipefail

# E1 보강 실험: 추측 디코딩의 손익 전환 경계와 반복 변동 폭을 확인한다.
# 기존 E1과 같은 prefill 워크로드를 사용하되 각 지점을 64요청, 구성별 3회 측정한다.

cd "$(dirname "$0")"
source redeploy.sh

CONCURRENCY="1,16,24,32,48,64"
COMMON_ARGS=(
  --base-url http://127.0.0.1:8000
  --scenarios prefill
  --concurrency "$CONCURRENCY"
  --requests-per-level 64
  --warmup 2
  --ttft-slo 2
  --e2e-slo 30
)

kubectl apply -f k8s/vllm-baseline.yaml
kubectl rollout status deployment/vllm-baseline -n llm-serving-lab --timeout=20m

redeploy \
  MAX_MODEL_LEN=4096 \
  GPU_MEMORY_UTILIZATION=0.85 \
  MAX_NUM_SEQS=64 \
  EXTRA_ARGS=''
kubectl -n llm-serving-lab logs deploy/vllm-baseline \
  | grep -E 'GPU KV cache size|Maximum concurrency' \
  | tail -2 \
  | tee results/e1b-vanilla-startup.txt

for run in 1 2 3; do
  python3 benchmark.py "${COMMON_ARGS[@]}" \
    --output "results/e1b-vanilla-r${run}.json"
done

redeploy EXTRA_ARGS='--spec-method ngram --spec-tokens 5'
kubectl -n llm-serving-lab logs deploy/vllm-baseline \
  | grep -E 'GPU KV cache size|Maximum concurrency' \
  | tail -2 \
  | tee results/e1b-ngram-startup.txt

curl -fsS http://127.0.0.1:8000/metrics \
  | grep '^vllm:spec_decode' \
  > results/e1b-ngram-metrics-0.txt

for run in 1 2 3; do
  python3 benchmark.py "${COMMON_ARGS[@]}" \
    --output "results/e1b-ngram-r${run}.json"
  curl -fsS http://127.0.0.1:8000/metrics \
    | grep '^vllm:spec_decode' \
    > "results/e1b-ngram-metrics-${run}.txt"
done

