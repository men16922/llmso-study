# EKS·Trainium 워크샵 Lab 3~6

독자용 아티클은 [6주차 과제](../../articles/6주차%20과제.md), 설치·권한·배포의 상세 이력은 [실행 기록](./execution-record.md)에 있습니다. `results/2026-09-12/`는 실제 워크샵 결과입니다. `benchmark-during-setup.json`은 설치와 겹친 예비 측정이므로 성능 비교에는 `benchmark-final.json`을 사용합니다. 개인 키·HF 토큰·Grafana 비밀번호는 포함하지 않습니다.

## 전제

워크샵 접속용 EC2의 `sudo -i` 셸, 기존 EKS context, 정상 vLLM Pod·Service가 필요합니다. 이번 모델의 API ID는 `tinyLlama/TinyLlama-1.1B-Chat-v1.0`, Service는 `default/vllm-service:8080`입니다. 아래 명령은 파일을 EC2로 전송한 뒤 해당 디렉터리에서 실행합니다. 클러스터와 Pod 이름은 실제 값을 확인합니다.

## Lab 3·4 설치

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx --version 4.15.1 \
  -n ingress-nginx --create-namespace --wait --timeout 5m
kubectl apply -f vllm-ingress-simple.yaml
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap vllm-dashboard -n monitoring \
  --from-file=vllm.json=grafana-dashboard.json --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install prometheus prometheus \
  --repo https://prometheus-community.github.io/helm-charts --version 29.28.1 \
  -n monitoring -f prometheus-values.yaml --wait --timeout 5m
helm upgrade --install grafana grafana \
  --repo https://grafana.github.io/helm-charts --version 10.5.15 \
  -n monitoring -f grafana-values.yaml --wait --timeout 5m
```

Grafana dashboard UID는 `week6-vllm`입니다. chart가 생성한 admin Secret을 로그인에 사용합니다. 서비스는 ClusterIP로 유지하며 별도 셸에서 `kubectl port-forward -n monitoring svc/grafana 13000:80 --address 127.0.0.1`을 실행합니다. Prometheus는 `svc/prometheus-server 19090:80`입니다. 로컬 SSH 터널도 localhost에만 바인딩합니다.

```bash
ssh -N -i /path/to/key.pem \
  -L 127.0.0.1:13000:127.0.0.1:13000 \
  -L 127.0.0.1:19090:127.0.0.1:19090 ubuntu@EC2_IP
```

CloudWatch는 추가 실습에서 Agent 설치와 제한된 로그 전송 정책을 적용한 뒤 Pod CPU·메모리 datapoint까지 확인했습니다. `cloudwatch/`의 manifest는 AWS 공식 예제를 내려받아 클러스터 이름과 이미지 버전을 고정한 실제 적용본입니다. 노드 역할에 붙인 정책은 `performance-log-policy.json`이며 특정 performance 로그 그룹만 허용합니다. 다른 계정에서는 계정·역할·클러스터 이름을 먼저 맞춰야 합니다.

```bash
kubectl create namespace amazon-cloudwatch --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f cloudwatch/cwagent-serviceaccount.yaml
kubectl apply -f cloudwatch/cwagent-configmap.yaml
kubectl apply -f cloudwatch/cwagent-daemonset.yaml
# 권한이 있는 참가자 AWS CLI 세션에서 실행: NODE_ROLE은 확인한 노드 역할 이름
aws iam put-role-policy --role-name "$NODE_ROLE" \
  --policy-name Week6ContainerInsightsPerformanceOnly \
  --policy-document file://cloudwatch/performance-log-policy.json --region us-west-2
aws cloudwatch put-dashboard --dashboard-name week6-vllm-monitoring \
  --dashboard-body file://cloudwatch-dashboard.json --region us-west-2
python3 verify_cloudwatch.py > cloudwatch-datapoints.json
```

AWS 자격 증명은 해당 프로세스 환경에서만 사용하고 파일에 저장하지 않습니다. `pod_cpu_usage_total`은 이 구성에서 게시된 metric이 아닌 performance 로그 필드입니다. CPU·메모리 utilization의 datapoint로 수집 성공을 판단합니다.

## Lab 5 부하 시험

[기존 검증된 벤치마크](../wsl2-vllm-baseline/benchmark.py)를 재사용했습니다. 아래 `benchmark.py`는 해당 파일입니다. 테스트 Pod에는 tar가 없으므로 파일은 stdin으로 전송합니다.

```bash
kubectl apply -f performance-runner.yaml
kubectl wait -n performance-testing --for=condition=Ready pod/performance-test-runner --timeout=120s
kubectl exec -i -n performance-testing performance-test-runner -- sh -c 'cat > /tmp/benchmark.py' < benchmark.py
kubectl exec -n performance-testing performance-test-runner -- python /tmp/benchmark.py \
  --base-url http://ingress-nginx-controller.ingress-nginx.svc.cluster.local \
  --scenarios short --concurrency 1,2,4,8 --requests-per-level 30 --warmup 3 \
  --output /tmp/benchmark-final.json
kubectl exec -n performance-testing performance-test-runner -- cat /tmp/benchmark-final.json > benchmark-final.json
kubectl exec -i -n performance-testing performance-test-runner -- python - < collect_metrics.py > prometheus.json
```

llmperf는 공식 저장소의 `f1d6bed47e4501b0e371082b41601b59ab55269f` 커밋을 Python 3.10 테스트 Pod에 내려받아 `pip install -e .`로 설치했습니다. 해당 소스 디렉터리에서 다음 명령을 실행합니다. 설치와 성능 측정은 겹치지 않게 합니다.

```bash
export OPENAI_API_KEY=EMPTY
export OPENAI_API_BASE=http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/v1
python token_benchmark_ray.py \
  --model tinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --mean-input-tokens 256 --stddev-input-tokens 50 \
  --mean-output-tokens 100 --stddev-output-tokens 20 \
  --max-num-completed-requests 50 --timeout 600 --num-concurrent-requests 5 \
  --results-dir /tmp/llmperf-results --llm-api openai \
  --additional-sampling-params '{"temperature":0.7}'
```

## Lab 6 HPA

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.8.1/components.yaml
kubectl top nodes
kubectl apply -f vllm-hpa.yaml
python3 observe_hpa.py --seconds 420 > hpa-timeline.jsonl
```

관측기를 실행한 동안 다른 EC2 셸에서 Running Pod의 실제 이름으로 `kubectl exec -i POD -c vllm-server -- python3 - --seconds 180 --workers 8 < cpu_stress.py > hpa-stress.jsonl`을 실행합니다. CPU 부하 시험이며 LLM 트래픽 시험과 구분합니다. 자식 프로세스마다 종료 시각이 있고 생성한 프로세스만 정리합니다. `cpu_stress.py`는 300초·8개 이하로 제한합니다.

부하 종료 뒤 HPA·Deployment가 1개로 돌아오는지, Pending이 없어지는지, `verify_http.py`가 다시 통과하는지 확인합니다. 단일 노드의 가속기 1개로는 추가 vLLM Pod가 실행되지 않습니다. HPA 최대값을 3으로 지정하는 것이 노드 증설을 수행하지는 않습니다.

## 추가 실험과 결과 회수

`run_output_matrix.py`는 64·256 출력 상한 × 동시 요청 4·8을 각각 32건씩 3회 반복합니다. `run_sustained.py`는 256토큰·동시 요청 8개로 320건을 보냅니다. 두 스크립트는 `/tmp/benchmark.py`와 함께 테스트 Pod에서 실행합니다. 원본은 `results/2026-09-12-extra/`에 있습니다.

```bash
kubectl exec -i -n performance-testing performance-test-runner -- sh -c 'cat > /tmp/run_output_matrix.py' < run_output_matrix.py
kubectl exec -i -n performance-testing performance-test-runner -- sh -c 'cat > /tmp/run_sustained.py' < run_sustained.py
kubectl exec -n performance-testing performance-test-runner -- python /tmp/run_output_matrix.py
kubectl exec -n performance-testing performance-test-runner -- python /tmp/run_sustained.py
kubectl exec -n performance-testing performance-test-runner -- cat /tmp/sustained.json > sustained.json
kubectl exec -i -n performance-testing performance-test-runner -- python - < collect_history.py > prometheus-history.json
kubectl exec -n performance-testing performance-test-runner -- python -c 'import glob,json; print(json.dumps({p:json.load(open(p)) for p in sorted(glob.glob("/tmp/output-matrix/*.json"))}))' > output-matrix-results.json
```

`collect_history.py`는 실행 시점 이전 30분을 10초 간격으로 조회합니다. 지속 시험 직후 회수해야 해당 구간이 포함됩니다. 파일 리다이렉션은 `sudo -i`로 진입한 root 셸 안에서 실행합니다. 추가 kubectl 관측기는 root 소유 디렉터리에 ubuntu가 쓰려다 실패했으며, 연속 시계열 근거는 회수한 Prometheus 결과입니다.

추가 부하 종료 후 `verify_http.py`로 내부 Ingress 응답을 다시 확인했고 테스트 Pod를 삭제했습니다. 클러스터·모니터링·HPA·로그·인라인 IAM 정책은 유지했습니다. 전체 삭제는 수행하지 않았으며, 나중에 정리할 때는 시험 결과 보존 후 워크샵의 종료 절차를 따릅니다.

## 아티클 후속 검증

출력 256토큰·동시 요청 4개의 지속 부하를 추가했습니다. 같은 준비 절차에서 `python /tmp/run_sustained.py --concurrency 4 --output /tmp/sustained-c4.json`을 실행하면 됩니다. 기본값은 기존 8개 시험과 같으며 측정 요청 320건, warmup 2건입니다.

`results/2026-09-12-extra/sustained-c4.json`은 2026-09-12 20:00:49~20:03:55 KST의 실측이며 `sustained-comparison.json`은 앞선 8개 시험과의 비교입니다. 320/320 성공, 451.52 tok/s, TTFT p95 0.174초, 지연 목표 충족률 100%였습니다. 일정한 도착률에서 요청을 제한한 정책 실험은 아닙니다. C4 시계열은 `prometheus-history-c4.json`입니다.

`plot_article.py`는 기존 3회 반복 집계 JSON에서 `articles/figures/week6-throughput-ttft.png`와 SVG를 만듭니다. 로컬 matplotlib와 AppleGothic·NanumGothic·Noto Sans CJK KR 중 하나가 필요합니다. 관측 화면을 가공한 그림이 아니라 JSON을 시각화한 비교 그래프입니다.

## Neuron 가속기 동시 관측

[관측 결과](./results/2026-09-12-neuron/summary.json)는 동시 요청 4/8을 각 320건 추가 실행하며 NeuronCore·디바이스 메모리를 같은 시간대에 수집한 결과입니다. 총 640/640 성공. 실제 Grafana 화면은 [가속기 동시 관측](../../articles/screenshots/week6-neuron-c4-c8.png)입니다.

- `observe_neuron.py`: 기존 vLLM 컨테이너 안에서 설치된 공식 Neuron monitor와 Prometheus exporter를 실행합니다. 기본 900초, 최대 1,200초로 제한하고 `/tmp/week6-neuron-observation/stop` 파일을 만들면 종료합니다. 원본은 같은 디렉터리의 `raw.jsonl`입니다.
- Prometheus에는 현재 vLLM Pod IP의 `9109` 포트를 가리키는 `week6-neuron-live` job을 5초 주기로 추가합니다. 기존 `scrape_configs` 배열 안에 넣고 설정 검증과 `up=1` 확인 후 부하를 시작합니다. 인터넷에 공개하는 Service는 만들지 않습니다.
- `grafana-neuron-dashboard.json`: 공식 `neuroncore_utilization_ratio`·`neuron_runtime_memory_used_bytes`와 기존 vLLM·CPU·HPA 지표를 그립니다. 완료한 구간으로 시간이 고정돼 있으므로 다시 측정할 때는 시간 범위를 바꿉니다.
- 테스트 Pod의 `/tmp`에 `benchmark.py`, `run_sustained.py`, `run_neuron_load.py`를 넣고 `python /tmp/run_neuron_load.py`를 실행합니다. 결과는 `/tmp/week6-neuron-load/`에 생성됩니다. `collect_neuron_history.py`는 클러스터 내부에서 최근 30분을 조회합니다.
- `summarize_neuron.py`: `results/2026-09-12-neuron/`의 회수된 원본을 집계합니다. 시작 +30초~종료 −15초를 관측 구간으로 사용하며, 누락된 관측을 0으로 바꾸지 않습니다.

회수 후 stop 파일로 관측기를 종료하고, 추가한 scrape job과 테스트 Pod를 정리합니다. `verify_http.py`로 일반·스트리밍 API를 재확인합니다. 이번 실행의 실제 종료 확인은 [정리 상태](./results/2026-09-12-neuron/cleanup.json)에 있습니다.
