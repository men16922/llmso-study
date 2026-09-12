#!/usr/bin/env python3
"""Collect actual Prometheus Neuron, vLLM and Kubernetes time series."""
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
end=time.time()
queries={
 'neuron_up':'up{job="week6-neuron-live"}',
 'neuron_utilization_percent':'100 * neuroncore_utilization_ratio{job="week6-neuron-live"}',
 'neuron_memory_bytes':'neuron_runtime_memory_used_bytes{job="week6-neuron-live"}',
 'generation_tokens_per_s':'sum(rate(vllm:generation_tokens_total{job="vllm-metrics"}[1m]))',
 'running':'vllm:num_requests_running{job="vllm-metrics"}',
 'waiting':'vllm:num_requests_waiting{job="vllm-metrics"}',
 'cpu_cores':'sum(rate(container_cpu_usage_seconds_total{namespace="default",container="vllm-server"}[1m]))',
 'hpa_desired':'kube_horizontalpodautoscaler_status_desired_replicas{namespace="default",horizontalpodautoscaler="vllm-hpa"}',
 'available':'kube_deployment_status_replicas_available{namespace="default",deployment="vllm-deployment"}'
}
results={}
for name,q in queries.items():
 url='http://prometheus-server.monitoring.svc.cluster.local/api/v1/query_range?'+urllib.parse.urlencode({'query':q,'start':end-1800,'end':end,'step':5})
 with urllib.request.urlopen(url,timeout=30) as r:
  data=json.load(r)
  if data.get('status')!='success':raise RuntimeError(data)
  results[name]={'query':q,'response':data}
print(json.dumps({'captured_at':dt.datetime.now(dt.timezone.utc).isoformat(),'start_epoch':end-1800,'end_epoch':end,'step_seconds':5,'queries':results},indent=2))
