#!/usr/bin/env bash
# vLLM 배포의 서빙 파라미터를 바꾸고, 실제로 응답할 때까지 기다린다.
#
#   source redeploy.sh
#   redeploy MAX_NUM_SEQS=16
#   redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=16384
#
# 왜 헬퍼가 필요한가 — 슬롯을 바꿀 때마다 네 가지가 필요하다.
#   ① env 설정  ② 롤아웃 대기  ③ 포트포워딩 재기동  ④ 실제 응답 확인
# ④를 `sleep 5`로 때우면 파드가 준비되기 전에 벤치마크가 시작돼 조용히 실패한다.
# 그리고 ②의 실패를 잡지 않으면(예: slots=64가 KV cache 부족으로 기동 실패),
# 죽은 엔드포인트에 대고 벤치마크를 돌려 쓰레기 데이터를 만든다.

NS="${NS:-llm-serving-lab}"
DEPLOY="${DEPLOY:-vllm-baseline}"
PORT="${PORT:-8000}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-10m}"
READY_TIMEOUT_S="${READY_TIMEOUT_S:-60}"

redeploy() {
  if [ $# -eq 0 ]; then
    echo "usage: redeploy KEY=VALUE [KEY=VALUE ...]" >&2
    return 2
  fi

  echo ">> set env: $*"
  kubectl -n "$NS" set env "deploy/$DEPLOY" "$@" || return 1

  if ! kubectl -n "$NS" rollout status "deploy/$DEPLOY" --timeout="$ROLLOUT_TIMEOUT"; then
    echo "!! 롤아웃 실패: $* — 이 구성은 건너뜁니다" >&2
    echo "!! 마지막 로그 40줄:" >&2
    kubectl -n "$NS" logs "deploy/$DEPLOY" --tail=40 >&2 || true
    return 1
  fi

  # 파드가 바뀌면 기존 포트포워딩은 끊긴다.
  pkill -f "port-forward.*$DEPLOY" >/dev/null 2>&1 || true
  sleep 2
  kubectl -n "$NS" port-forward --address 0.0.0.0 "svc/$DEPLOY" "$PORT:$PORT" \
    >/dev/null 2>&1 &

  local i
  for ((i = 0; i < READY_TIMEOUT_S; i++)); do
    if curl -sf "localhost:$PORT/v1/models" >/dev/null 2>&1; then
      echo ">> ready ($* / ${i}s)"
      return 0
    fi
    sleep 1
  done

  echo "!! 포트포워딩 후 ${READY_TIMEOUT_S}초 동안 /v1/models 응답 없음" >&2
  return 1
}

# 슬롯 값이 실제로 반영됐는지 파드 로그에서 확인한다.
# 모든 열이 똑같이 나오면 가장 먼저 의심할 것.
confirm_slots() {
  kubectl -n "$NS" logs "deploy/$DEPLOY" 2>/dev/null \
    | grep -iE "max_num_seqs|max num seqs|maximum concurrency" | tail -5
}

# 실행 구간의 시각을 남긴다. 다음 편 B4가 Prometheus에서 이 구간을 되짚는다.
mark() {
  echo "=== $* $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt
}
