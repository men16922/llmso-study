#!/usr/bin/env python3
"""CPU 합성 부하 없이 긴 출력 요청 320건으로 HPA 반응을 관측한다."""
import argparse
import datetime as dt
import json
from pathlib import Path
import benchmark

parser = argparse.ArgumentParser()
parser.add_argument('--concurrency', type=int, choices=[4, 8], default=8)
parser.add_argument('--output', default='/tmp/sustained.json')
args = parser.parse_args()
benchmark.SCENARIOS['short']['max_tokens'] = 256
started = dt.datetime.now(dt.timezone.utc).isoformat()
code = benchmark.main(['--base-url','http://ingress-nginx-controller.ingress-nginx.svc.cluster.local','--scenarios','short','--concurrency',str(args.concurrency),'--requests-per-level','320','--warmup','2','--output',args.output])
p=Path(args.output)
if p.exists():
    data=json.loads(p.read_text())
    data['experiment']={'started_at':started,'ended_at':dt.datetime.now(dt.timezone.utc).isoformat(),'max_tokens':256,'prompt':benchmark.SCENARIOS['short']['prompt'],'synthetic_cpu_stress':False,'client_origin':'performance-test-runner on same EKS node'}
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(code)
