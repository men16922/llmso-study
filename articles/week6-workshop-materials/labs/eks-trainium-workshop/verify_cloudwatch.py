#!/usr/bin/env python3
"""현재 AWS 프로세스 자격 증명으로 실제 Container Insights datapoint를 조회한다."""
import datetime as dt
import json
import subprocess
from pathlib import Path

region='us-west-2'
cluster='ai-infra-summit-test-cluster'
end=dt.datetime.now(dt.timezone.utc)
start=end-dt.timedelta(minutes=20)
def aws(*args):
    return json.loads(subprocess.check_output(['aws',*args,'--region',region,'--output','json'],text=True))
dims=['Name=ClusterName,Value='+cluster,'Name=Namespace,Value=default','Name=PodName,Value=vllm-deployment']
metrics={}
for name in ['pod_cpu_utilization','pod_memory_utilization','pod_cpu_usage_total']:
    metrics[name]=aws('cloudwatch','get-metric-statistics','--namespace','ContainerInsights','--metric-name',name,'--dimensions',*dims,'--start-time',start.isoformat(),'--end-time',end.isoformat(),'--period','60','--statistics','Average','Maximum')
result={'captured_at':end.isoformat(),'region':region,'cluster':cluster,'dimensions':dims,'metrics':metrics,'streams':aws('logs','describe-log-streams','--log-group-name','/aws/containerinsights/'+cluster+'/performance','--order-by','LastEventTime','--descending','--max-items','1')}
print(json.dumps(result,indent=2))
