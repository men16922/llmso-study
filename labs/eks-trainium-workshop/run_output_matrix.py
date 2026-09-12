#!/usr/bin/env python3
"""동일 입력의 출력 상한 64/256 × 동시 요청 4/8을 3회 반복한다.

같은 디렉터리에 기존 wsl2-vllm-baseline/benchmark.py를 복사해 실행한다.
"""
import datetime as dt
import json
from pathlib import Path
import benchmark

base = 'http://ingress-nginx-controller.ingress-nginx.svc.cluster.local'
original = dict(benchmark.SCENARIOS['short'])
output = Path('/tmp/output-matrix')
output.mkdir(exist_ok=True)
for repeat in range(1, 4):
    # 순서에 따른 영향을 줄이되 완전한 무작위화라고 주장하지 않는다.
    caps = [64, 256] if repeat % 2 else [256, 64]
    concurrency = '4,8' if repeat % 2 else '8,4'
    for cap in caps:
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        benchmark.SCENARIOS['short'] = {**original, 'max_tokens': cap}
        path = output / f'output-{cap}-r{repeat}.json'
        code = benchmark.main(['--base-url',base,'--scenarios','short','--concurrency',concurrency,'--requests-per-level','32','--warmup','2','--output',str(path)])
        if path.exists():
            data = json.loads(path.read_text())
            data['experiment'] = {'repeat':repeat,'max_tokens':cap,'prompt':original['prompt'],'started_at':started,'ended_at':dt.datetime.now(dt.timezone.utc).isoformat(),'client_origin':'performance-test-runner on same EKS node','order':'caps and concurrency reversed on repeat 2','temperature':0,'synthetic_cpu_stress':False}
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        if code:
            raise SystemExit(code)
