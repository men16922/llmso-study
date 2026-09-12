#!/usr/bin/env python3
"""Bounded observation using the installed AWS Neuron monitor and exporter.

Run inside the existing vLLM container. Does not modify its model or deployment.
Raw JSONL records carry receipt time; Prometheus scrapes the official exporter.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import select
import subprocess
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds', type=int, default=900)
    p.add_argument('--directory', default='/tmp/week6-neuron-observation')
    args = p.parse_args()
    if not 10 <= args.seconds <= 1200:
        p.error('seconds must be between 10 and 1200')
    out = Path(args.directory)
    out.mkdir(exist_ok=True)
    conf = {'period':'5s', 'neuron_runtimes':[{'tag_filter':'.*','metrics':[
        {'type':'neuroncore_counters'}, {'type':'memory_used'}, {'type':'execution_stats'}
    ]}], 'system_metrics':[]}
    (out/'monitor.json').write_text(json.dumps(conf))
    deadline = time.monotonic()+args.seconds
    with (out/'monitor.stderr').open('w') as err, (out/'exporter.log').open('w') as exportlog, (out/'raw.jsonl').open('w',buffering=1) as raw:
        exporter = subprocess.Popen(['python3','/opt/aws/neuron/bin/neuron-monitor-prometheus.py','--port','9109'],stdin=subprocess.PIPE,stdout=exportlog,stderr=exportlog,text=True)
        monitor = subprocess.Popen(['/opt/aws/neuron/bin/neuron-monitor','-c',str(out/'monitor.json')],stdout=subprocess.PIPE,stderr=err,text=True)
        try:
            while time.monotonic()<deadline and not (out/'stop').exists():
                if exporter.poll() is not None:
                    raise RuntimeError('Official exporter stopped; inspect exporter.log')
                ready,_,_=select.select([monitor.stdout],[],[],1)
                if not ready:
                    continue
                line=monitor.stdout.readline()
                if not line:
                    raise RuntimeError('Neuron monitor stopped')
                data=json.loads(line)
                raw.write(json.dumps({'received_at':dt.datetime.now(dt.timezone.utc).isoformat(),'data':data})+'\n')
                exporter.stdin.write(line)
                exporter.stdin.flush()
        finally:
            for child in (monitor,exporter):
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
    print(json.dumps({'completed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'directory':str(out)}))

if __name__=='__main__':
    main()
