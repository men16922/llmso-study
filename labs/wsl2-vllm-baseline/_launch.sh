#!/usr/bin/env bash
# Start-Process로 띄우기 위한 얇은 래퍼. 인자 하나(스테이지 이름)만 받는다.
# 왜 필요한가 — WSL 세션에 붙은 셸에서 nohup으로 띄우면 호출이 끝날 때 같이 죽는다.
# 독립 Windows 프로세스(Start-Process)가 세션을 잡고 있어야 측정이 끝까지 간다.
cd /mnt/c/Users/82104/Desktop/Study/llmso-study/labs/wsl2-vllm-baseline
exec "./run_$1.sh" > "/tmp/$1.log" 2>&1
