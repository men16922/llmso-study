#!/usr/bin/env python3
"""Summarize synchronized observations; never interpret missing metrics as zero."""
import datetime as dt
import json
from pathlib import Path
import statistics

root=Path(__file__).parent/'results/2026-09-12-neuron'
phases=json.loads((root/'phases.json').read_text())
raw=[json.loads(l) for l in (root/'raw.jsonl').read_text().splitlines() if l.strip()]
history=json.loads((root/'prometheus-history.json').read_text())
def stamp(s):return dt.datetime.fromisoformat(s).timestamp()
def stats(values):
    if not values:raise ValueError('Missing observations')
    return {'samples':len(values),'min':min(values),'max':max(values),'mean':statistics.mean(values)}
result={'method':'one run per concurrency, max output 256, 320 requests, warmup 2; telemetry window phase start +30s to phase end -15s','conditions':{}}
for p in phases:
    assert p['returncode']==0
    start,end=stamp(p['start'])+30,stamp(p['end'])-15
    obs=[x for x in raw if start<=stamp(x['received_at'])<=end]
    cores={};memory=[];errors=[];completed=[]
    for x in obs:
        apps=x['data']['neuron_runtime_data']
        assert len(apps)==1, 'Review per-runtime attribution before aggregating'
        for app in apps:
            report=app['report']
            for group in ['neuroncore_counters','memory_used','execution_stats']:
                if report[group].get('error'):errors.append(report[group]['error'])
            if app.get('error'):errors.append(app['error'])
            for c,v in report['neuroncore_counters']['neuroncores_in_use'].items():
                cores.setdefault(c,[]).append(v['neuroncore_utilization'])
            memory.append(report['memory_used']['neuron_runtime_used_bytes']['neuron_device'])
            errors.extend([f'{k}={v}' for k,v in report['execution_stats']['error_summary'].items() if v])
            completed.append(report['execution_stats']['execution_summary']['completed'])
    bench=json.loads((root/f'c{p["concurrency"]}.json').read_text())
    assert len(bench['summaries'])==1
    summary=bench['summaries'][0]
    assert summary['requests']==summary['successes']==320
    prom={}
    for name,data in history['queries'].items():
        prom[name]=[]
        for series in data['response']['data']['result']:
            vals=[float(v) for t,v in series['values'] if start<=t<=end]
            if vals:prom[name].append({'labels':series['metric'],'stats':stats(vals)})
    for name in ['neuron_up','running','waiting','cpu_cores','hpa_desired','available']:
        assert prom[name], name
    result['conditions'][str(p['concurrency'])]={'phase':p,'window_start':dt.datetime.fromtimestamp(start,dt.timezone.utc).isoformat(),'window_end':dt.datetime.fromtimestamp(end,dt.timezone.utc).isoformat(),'benchmark':summary,'neuron_core_percent':{c:stats(v) for c,v in cores.items()},'runtime_device_memory_bytes':stats(memory),'monitor_errors':errors,'execution_completed_per_sample':stats(completed),'prometheus':prom}
result['raw_records']=len(raw)
result['hardware']=raw[-1]['data']['neuron_hardware_info']
(root/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
for c,d in result['conditions'].items():
    print(c,json.dumps({k:d[k] for k in ['benchmark','neuron_core_percent','runtime_device_memory_bytes','monitor_errors']},ensure_ascii=False))
