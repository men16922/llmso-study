#!/usr/bin/env python3
"""Compare C4/C8 with 256-token output while Neuron telemetry is collected."""
import datetime as dt
import json
from pathlib import Path
import subprocess
import time

out=Path('/tmp/week6-neuron-load')
out.mkdir(exist_ok=True)
phases=[]
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
for c in [4,8]:
    start=now()
    print(json.dumps({'stage':'start','concurrency':c,'at':start}),flush=True)
    result=out/f'c{c}.json'
    run=subprocess.run(['python','/tmp/run_sustained.py','--concurrency',str(c),'--output',str(result)],stdout=(out/f'c{c}.log').open('w'),stderr=subprocess.STDOUT)
    phases.append({'concurrency':c,'start':start,'end':now(),'returncode':run.returncode,'output':str(result)})
    (out/'phases.json').write_text(json.dumps(phases,indent=2)+'\n')
    print(json.dumps(phases[-1]),flush=True)
    if run.returncode:
        raise SystemExit(run.returncode)
    time.sleep(30)
print(json.dumps({'stage':'complete','at':now()}),flush=True)
