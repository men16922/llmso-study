#!/usr/bin/env python3
"""접속용 EC2에서 HPA·Pod·CPU 상태를 15초 간격으로 JSONL 기록한다."""
import argparse
import datetime as dt
import json
import subprocess
import time

def command(*args, structured=True):
    r=subprocess.run(['kubectl',*args],capture_output=True,text=True,timeout=20)
    if r.returncode:
        return {'error':r.stderr.strip(),'returncode':r.returncode}
    return json.loads(r.stdout) if structured else r.stdout

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--seconds',type=int,default=420)
    a=p.parse_args()
    deadline=time.monotonic()+a.seconds
    while True:
        h=command('get','hpa','vllm-hpa','-o','json')
        d=command('get','deployment','vllm-deployment','-o','json')
        pods=command('get','pods','-l','app.kubernetes.io/name=vllm-server','-o','json')
        row={'at':dt.datetime.now(dt.timezone.utc).isoformat(),'hpa':h.get('status',h),'deployment':{'desired':d.get('spec',{}).get('replicas'),'status':d.get('status',{})},'pods':[{'name':x['metadata']['name'],'phase':x['status']['phase'],'conditions':x['status'].get('conditions',[])} for x in pods.get('items',[])],'cpu':command('top','pods','-l','app.kubernetes.io/name=vllm-server',structured=False)}
        print(json.dumps(row),flush=True)
        if time.monotonic()>=deadline:
            break
        time.sleep(min(15,max(0,deadline-time.monotonic())))
