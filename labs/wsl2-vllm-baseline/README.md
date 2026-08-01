# WSL2·K3s vLLM 서빙 기준선 실험

[`gpu-setup-docker-k8s-lab-report-wsl2.md`](../../knowledge/subpages/gpu-setup-docker-k8s-lab-report-wsl2.md)에서 확인한 GPU 인프라 위에 실제 모델 서버를 올리고, 입력·출력 길이와 동시성에 따른 성능 변화를 측정합니다.

사람이 따라갈 실행 순서와 결과 기록 양식은 [`WSL2·K3s vLLM GPU 서빙 기준선 런북`](../../knowledge/subpages/vllm-gpu-serving-baseline-runbook-wsl2.md)에 있습니다. 이 디렉터리는 런북에서 호출하는 스크립트와 Kubernetes 매니페스트의 원본입니다.

이 실험의 목적은 최고 성능을 만드는 것이 아닙니다. 같은 모델과 설정으로 반복할 수 있는 기준선을 남겨 이후 배칭·양자화·prefix caching·EKS 결과와 비교하는 것이 목적입니다.

## 측정 범위

| 시나리오 | 입력·출력 | 확인할 병목 |
|---|---|---|
| `short` | 짧은 입력·64토큰 출력 | 기본 지연과 호출 오버헤드 |
| `prefill` | 긴 입력·64토큰 출력 | 긴 프롬프트가 TTFT에 미치는 영향 |
| `decode` | 짧은 입력·512토큰 출력 | decode 처리량과 메모리 대역폭 영향 |
| 동시성 `1,4,8,16` | 시나리오별 반복 | 배칭 이득과 goodput 하락 지점 |

측정기는 스트리밍 응답의 첫 내용 토큰 도착 시간을 TTFT로 기록합니다. goodput은 **TTFT와 E2E SLO를 모두 만족한 요청 비율**입니다. 기본 SLO는 TTFT 2초, E2E 30초이며 명령행 옵션으로 변경할 수 있습니다.

## 환경 전제

- Windows 11 + WSL2 + NVIDIA GPU
- K3s와 `RuntimeClass/nvidia`
- `nvidia.com/gpu: 1`이 allocatable 자원으로 등록된 상태
- `monitoring` namespace에 kube-prometheus-stack 설치
- 모델 최초 다운로드를 위한 네트워크와 PVC 20Gi

현재 저장소를 편집한 Darwin arm64·CPU kind 환경에는 NVIDIA GPU가 없습니다. 이 환경에서는 Python 측정기와 Kubernetes·Prometheus 구문만 검증했으며, 실제 TTFT·처리량 수치는 WSL2 RTX 환경에서 실행해야 합니다.

```bash
kubectl get runtimeclass nvidia
kubectl get node -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}{"\n"}'
```

두 번째 명령의 결과가 `1`이 아니면 모델 서버를 적용하지 말고 GPU 환경부터 복구합니다.

## 1. 모델 서버 배포

기본값은 12GB VRAM에서 기준선을 먼저 얻기 위한 `Qwen/Qwen2.5-1.5B-Instruct`입니다. vLLM 이미지는 `v0.23.0`으로 고정했습니다.

```bash
kubectl apply -f labs/wsl2-vllm-baseline/k8s/vllm-baseline.yaml
kubectl rollout status deployment/vllm-baseline \
  -n llm-serving-lab --timeout=20m
kubectl logs -n llm-serving-lab deployment/vllm-baseline -f
```

첫 실행은 이미지와 모델을 내려받으므로 오래 걸릴 수 있습니다. 서버가 준비되면 별도 터미널에서 포트를 엽니다.

```bash
kubectl port-forward -n llm-serving-lab svc/vllm-baseline 8000:8000
```

NodePort 대신 `port-forward`를 쓰는 이유는 WSL2 localhost 릴레이가 iptables DNAT만으로 구성된 NodePort를 인식하지 못한 실측 결과 때문입니다.

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/v1/models
```

## 2. 기준선 측정

빠른 확인은 시나리오당 동시성 단계별 요청 2개만 실행합니다.

```bash
python3 labs/wsl2-vllm-baseline/benchmark.py \
  --concurrency 1,4 \
  --requests-per-level 2 \
  --output labs/wsl2-vllm-baseline/results/smoke.json
```

기준선은 각 단계에서 최소 8개 요청을 실행합니다. 동시성 16에서는 요청 수가 자동으로 16개까지 늘어납니다.

```bash
python3 labs/wsl2-vllm-baseline/benchmark.py \
  --concurrency 1,4,8,16 \
  --requests-per-level 8 \
  --ttft-slo 2 \
  --e2e-slo 30 \
  --output labs/wsl2-vllm-baseline/results/baseline.json
```

결과 JSON에는 집계값과 요청별 원시 측정값이 함께 저장됩니다. `exact_usage_requests`가 성공 요청 수보다 작으면 서버가 스트리밍 usage를 주지 않아 출력 토큰 수 일부를 공백 기준으로 추정했다는 뜻입니다.

## 3. GPU·서버 메트릭 함께 보기

매니페스트의 `ServiceMonitor`는 vLLM `/metrics`를 15초마다 수집합니다. 벤치마크를 실행하는 동안 다음 PromQL을 나란히 확인합니다.

```promql
DCGM_FI_DEV_GPU_UTIL
DCGM_FI_DEV_FB_USED
DCGM_FI_DEV_POWER_USAGE
rate(vllm:request_success_total[1m])
histogram_quantile(0.95, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[5m])))
```

vLLM 버전에 따라 메트릭 이름이 바뀌면 `/metrics`에서 `vllm:` 접두사를 먼저 확인하고 쿼리를 조정합니다.

```bash
curl -fsS http://localhost:8000/metrics | grep '^vllm:' | head -30
```

## 4. 관측성 공백 감지

기존 `GpuXidError`는 `DCGM_FI_DEV_XID_ERRORS` 시계열 자체가 없으면 발화하지 않습니다. 다음 규칙은 핵심·XID·Tensor Core 메트릭의 부재를 별도 상태로 알립니다.

```bash
kubectl apply -f labs/wsl2-vllm-baseline/k8s/gpu-telemetry-gap-rule.yaml
kubectl get prometheusrule gpu-telemetry-gap-rules -n monitoring
```

WSL2에서는 `GpuXidTelemetryMissing`과 `GpuProfilingTelemetryMissing`이 예상 결과입니다. 핵심 메트릭인 GPU 온도까지 없다면 `GpuCoreTelemetryMissing`이 발생하며 DCGM Exporter 수집 경로를 먼저 복구해야 합니다.

## 5. 7B AWQ 확장 실험

1.5B 기준선이 끝난 뒤 동일한 파라미터로 7B AWQ를 비교합니다. 12GB에서는 모델 가중치 외에 KV cache와 CUDA 그래프 공간이 필요하므로 4096 컨텍스트부터 시작합니다.

```bash
kubectl set env deployment/vllm-baseline -n llm-serving-lab \
  MODEL_ID=Qwen/Qwen2.5-7B-Instruct-AWQ \
  SERVED_MODEL_NAME=qwen2.5-7b-awq
kubectl rollout status deployment/vllm-baseline \
  -n llm-serving-lab --timeout=20m
```

OOM이 발생하면 `--gpu-memory-utilization`을 올리기보다 `--max-model-len`과 `--max-num-seqs`를 먼저 낮추고, 실패한 설정도 결과에 남깁니다. 모델을 바꾼 결과는 기준선 JSON과 섞지 말고 별도 파일로 저장합니다.

## 6. 종료와 정리

```bash
kubectl delete -f labs/wsl2-vllm-baseline/k8s/gpu-telemetry-gap-rule.yaml
kubectl delete namespace llm-serving-lab
```

namespace를 삭제하면 PVC의 모델 캐시도 함께 삭제됩니다. 다시 측정할 계획이면 namespace 대신 Deployment만 삭제해 캐시를 보존합니다.

## 검증 상태

- `benchmark.py` Python 구문 검사 통과
- mock OpenAI 스트리밍 서버 기반 단위 테스트 통과
- Kubernetes 리소스 5종 client-side dry-run 통과
- Prometheus 3.13.1 `promtool check rules` 통과: 3개 규칙
- 실제 NVIDIA GPU·vLLM 결과: WSL2 RTX 환경에서 실행 필요

## 참고

- [vLLM 공식 Docker 가이드](https://docs.vllm.ai/en/latest/deployment/docker/)
- [vLLM 공식 Kubernetes 가이드](https://docs.vllm.ai/en/latest/deployment/k8s/)
- [Qwen2.5-1.5B-Instruct 모델 카드](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [Qwen2.5-7B-Instruct-AWQ 모델 카드](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ)
- [Prometheus `absent_over_time`](https://prometheus.io/docs/prometheus/latest/querying/functions/#absent_over_time)
