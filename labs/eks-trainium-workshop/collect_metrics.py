#!/usr/bin/env python3
"""클러스터 내부에서 Prometheus 실제 target과 주요 지표를 수집한다."""
import datetime as dt
import json
import urllib.parse
import urllib.request
BASE = 'http://prometheus-server.monitoring.svc.cluster.local'
def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.load(r)
queries = {
    'vllm_up': 'up{job="vllm-metrics"}',
    'generation_tokens': 'vllm:generation_tokens_total{job="vllm-metrics"}',
    'generation_rate': 'sum(rate(vllm:generation_tokens_total{job="vllm-metrics"}[1m]))',
    'running': 'vllm:num_requests_running{job="vllm-metrics"}',
    'waiting': 'vllm:num_requests_waiting{job="vllm-metrics"}',
    'cpu_cores': 'sum(rate(container_cpu_usage_seconds_total{namespace="default",container="vllm-server"}[1m]))',
    'desired': 'kube_deployment_spec_replicas{namespace="default",deployment="vllm-deployment"}',
    'available': 'kube_deployment_status_replicas_available{namespace="default",deployment="vllm-deployment"}',
}
print(json.dumps({'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'targets': get('/api/v1/targets'), 'queries': {k: get('/api/v1/query?' + urllib.parse.urlencode({'query': v})) for k,v in queries.items()}}, indent=2))
