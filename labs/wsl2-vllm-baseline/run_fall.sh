#!/usr/bin/env bash
# 5주차 측정을 순서대로 돌린다. 하나가 실패해도 다음으로 넘어간다 —
# 이틀 밀린 상태라 밤새 한 번에 돌려야 하고, 앞 실험의 실패로 뒤가 통째로
# 날아가는 게 제일 나쁘다. 각 단계 로그는 /tmp/<단계>.log에 따로 남는다.
cd "$(dirname "$0")"

for stage in f1a2 f1b f1c f2; do
  echo "########## $stage 시작 $(date -u +%H:%M:%S) UTC ##########"
  if "./run_${stage}.sh" > "/tmp/${stage}.log" 2>&1; then
    echo "########## $stage 완료 $(date -u +%H:%M:%S) UTC ##########"
  else
    echo "########## $stage 실패(계속 진행) $(date -u +%H:%M:%S) UTC ##########"
    tail -20 "/tmp/${stage}.log"
  fi
done

echo "########## ALL DONE $(date -u +%H:%M:%S) UTC ##########"
