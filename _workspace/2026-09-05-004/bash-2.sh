cd labs/wsl2-vllm-baseline
source redeploy.sh

# 모델과 입력·출력 조건을 고정한 상태에서 BF16 기준 구성으로 재배포
redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=4096 \
  GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''

# 새로 측정할 때의 예시. 100은 이 예시의 요청 수이며 원실험 값이 아니다.
python3 benchmark.py --scenarios decode --concurrency 16 \
  --requests-per-level 100 --output results/recheck-bf16-1.json

# FP8 기본 구성. 재배포 성공과 기동 로그를 확인한 뒤 같은 부하를 실행
redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=4096 \
  GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS='--quantization fp8'
python3 benchmark.py --scenarios decode --concurrency 16 \
  --requests-per-level 100 --output results/recheck-fp8-1.json
