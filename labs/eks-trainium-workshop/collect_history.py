#!/usr/bin/env python3
"""실제 추론 부하와 HPA의 Prometheus 시계열을 클러스터 내부에서 회수한다."""
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
end=time.time()
queries={
 'generation_tokens_per_s':'sum(rate(vllm:generation_tokens_total{job="vllm-metrics"}[1m]))',
 'running':'vllm:num_requests_running{job="vllm-metrics"}',
 'waiting':'vllm:num_requests_waiting{job="vllm-metrics"}',
 'cpu_cores':'sum(rate(container_cpu_usage_seconds_total{namespace="default",container="vllm-server"}[1m]))',
 'hpa_desired':'kube_horizontalpodautoscaler_status_desired_replicas{namespace="default",horizontalpodautoscaler="vllm-hpa"}',
 'available':'kube_deployment_status_replicas_available{namespace="default",deployment="vllm-deployment"}'
}
results={}
for name,q in queries.items():
 url='http://prometheus-server.monitoring.svc.cluster.local/api/v1/query_range?'+urllib.parse.urlencode({'query':q,'start':end-1800,'end':end,'step':10})
 with urllib.request.urlopen(url,timeout=30) as r:results[name]={'query':q,'response':json.load(r)}
print(json.dumps({'captured_at':dt.datetime.now(dt.timezone.utc).isoformat(),'start_epoch':end-1800,'end_epoch':end,'step_seconds':10,'queries':results},indent=2))
