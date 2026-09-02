#!/usr/bin/env bash
# Prometheus·Grafana를 Windows 쪽 브라우저에서 열 수 있게 포워딩한다.
#
# 왜 스크립트 파일이 필요한가 — `Start-Process wsl.exe -- kubectl port-forward ...`
# 처럼 명령을 직접 넘기면 호출한 PowerShell 세션이 끝날 때 같이 죽는다.
# 측정 스크립트와 같은 방식(`.sh` 파일을 독립 Windows 프로세스로 실행)이라야 남는다.
#
# `--address 0.0.0.0`은 쓰지 않는다. 127.0.0.1에만 묶어도 WSL2의 localhost
# 포워딩으로 Windows에서 닿는다. k3s NodePort(30001/30002)가 Windows에서 안 잡히는
# 이유는 kube-proxy가 iptables 규칙만 두고 실제 listening 소켓을 만들지 않아
# localhost 포워딩이 중계할 대상을 못 찾기 때문이다.

NS=monitoring

pf() {  # pf <서비스> <로컬포트> <원격포트>
  while :; do
    kubectl -n "$NS" port-forward "svc/$1" "$2:$3" >/dev/null 2>&1
    sleep 2   # 끊기면 다시 붙는다 (파드 재기동 등)
  done &
}

# 9090은 Windows 예약 포트 범위(9021~9120)에 들어가 Windows 쪽에서 바인딩이 막힌다.
# netsh interface ipv4 show excludedportrange protocol=tcp 로 확인했다.
pf kube-prometheus-stack-prometheus 9009 9090
pf kube-prometheus-stack-grafana    3000 80

echo "port-forward 시작: prometheus http://localhost:9009 · grafana http://localhost:3000"
wait
