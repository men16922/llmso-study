#!/usr/bin/env bash
# C2 스윕 — max_queue_delay만 바꿔가며 dynamic batching 효과를 잰다.
#
#   cd ~/llm-model-inference/ch03/multi_model_serving
#   bash /path/to/labs/triton-dynamic-batching/sweep.sh
#
# 전제:
#   ① mobilenet_v2가 배치 축 열린 ONNX로 model_dir/mobilenet_v2/1/model.onnx 에 있다
#      (export_mobilenet_onnx.py)
#   ② Triton이 --model-control-mode=explicit 으로 떠 있다 (8009/8010/8011)
#
# explicit 모드라 **컨테이너 재시작 없이** unload/load만으로 config를 다시 읽는다.

set -uo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${MODEL:-mobilenet_v2}"
HTTP="${HTTP:-localhost:8009}"
METRICS="${METRICS:-http://localhost:8011/metrics}"
CONFIG="${CONFIG:-model_dir/$MODEL/config.pbtxt}"
CONCURRENCY="${CONCURRENCY:-1,8,32}"
REQUESTS="${REQUESTS:-300}"
OUT="${OUT:-results}"

DELAYS=("${@:-off 0 1000 5000 20000}")
read -ra DELAYS <<< "${DELAYS[*]}"

mkdir -p "$OUT"

reload_model() {
  curl -s -X POST "$HTTP/v2/repository/models/$MODEL/unload" >/dev/null
  curl -s -X POST "$HTTP/v2/repository/models/$MODEL/load"   >/dev/null
  # 실제로 준비됐는지 확인 — sleep으로 때우면 첫 요청이 실패한다.
  local i
  for ((i = 0; i < 30; i++)); do
    if curl -sf "$HTTP/v2/models/$MODEL/ready" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

for DELAY in "${DELAYS[@]}"; do
  echo ""
  echo "===================== delay=$DELAY ====================="

  python3 "$LAB_DIR/make_config.py" "$DELAY" --model "$MODEL" > "$CONFIG" || {
    echo "!! config 생성 실패: $DELAY" >&2; continue; }

  if ! reload_model; then
    echo "!! 모델 로드 실패 (delay=$DELAY) — Triton 로그를 확인하세요:" >&2
    echo "   docker logs triton | tail -40" >&2
    continue
  fi

  # 적용된 config를 서버에서 되읽어 확인한다. 파일만 고치고 반영이 안 된 경우를 여기서 잡는다.
  APPLIED=$(curl -s "$HTTP/v2/models/$MODEL/config" \
    | python3 -c 'import json,sys; c=json.load(sys.stdin); d=c.get("dynamic_batching"); print("off" if not d else d.get("max_queue_delay_microseconds", 0))' 2>/dev/null)
  echo "   서버에 적용된 값: $APPLIED (요청한 값: $DELAY)"

  python3 "$LAB_DIR/triton_metrics.py" snapshot --url "$METRICS" > "$OUT/before-$DELAY.txt"

  python3 "$LAB_DIR/triton_load.py" \
    --url "$HTTP" --model "$MODEL" \
    --concurrency "$CONCURRENCY" --requests "$REQUESTS" \
    --label "delay=$DELAY" --output "$OUT/c2-delay-$DELAY.json"

  python3 "$LAB_DIR/triton_metrics.py" snapshot --url "$METRICS" > "$OUT/after-$DELAY.txt"
  python3 "$LAB_DIR/triton_metrics.py" delta \
    "$OUT/before-$DELAY.txt" "$OUT/after-$DELAY.txt" \
    --model "$MODEL" --label "delay=$DELAY" | tee -a "$OUT/c2-batch-stats.txt"
done

echo ""
echo "===================== 요약 ====================="
cat "$OUT/c2-batch-stats.txt"
