# WSL2·K3s vLLM GPU 서빙 기준선 런북

> **상태:** 실행 준비 완료 · 실제 GPU 측정 대기<br>
> **대상 환경:** Windows 11 + WSL2 + NVIDIA GPU + K3s<br>
> **실행 자산:** [`labs/wsl2-vllm-baseline/`](../../labs/wsl2-vllm-baseline/)<br>
> **선행 기록:** [`WSL2 GPU 인프라 실측 보고서`](./gpu-setup-docker-k8s-lab-report-wsl2.md)

이 문서는 GPU 인프라를 다시 설명하지 않습니다. 앞선 실습에서 확인한 K3s GPU 환경에 실제 vLLM 서버를 올리고, **TTFT·E2E 지연·출력 처리량·goodput**을 같은 조건으로 반복 측정하기 위한 실행 기록지입니다.

첫 목표는 최고 성능이 아닙니다. `Qwen2.5-1.5B-Instruct`와 고정된 설정으로 기준선을 하나 만든 뒤, 7B AWQ·동시성·캐싱·EKS 결과를 같은 표에서 비교할 수 있게 만드는 것이 핵심입니다.

## 한눈에 보는 실행 순서

| 순서 | 할 일 | 완료 조건 |
|---|---|---|
| 1 | GPU·RuntimeClass·Prometheus 사전 점검 | GPU allocatable 값이 `1`, Prometheus Pod가 `Running` |
| 2 | vLLM 1.5B 배포 | Deployment rollout 완료, `/health` 응답 성공 |
| 3 | 스모크 테스트 | 모든 요청 성공, JSON 결과 생성 |
| 4 | 기준선 측정 | 동시성 `1,4,8,16` 결과와 GPU 메트릭 확보 |
| 5 | 관측성 공백 확인 | 핵심·XID·프로파일링 메트릭의 유무를 명시 |
| 6 | 7B AWQ 비교 | 동일 조건의 별도 JSON 생성 또는 실패 조건 기록 |
| 7 | 결과 정리 | 아래 결과표와 결론 작성 |

<details>
<summary><strong>0. 실험 원칙과 측정 기준</strong></summary>

	### 무엇을 측정하나

	| 지표 | 이 실험에서의 의미 |
	|---|---|
	| TTFT | 요청 시작부터 스트리밍 첫 내용 토큰이 도착할 때까지의 시간 |
	| E2E | 요청 시작부터 스트림 종료까지 걸린 전체 시간 |
	| Output tok/s | 한 동시성 구간에서 성공한 출력 토큰 수를 실제 벽시계 시간으로 나눈 값 |
	| Goodput | TTFT 2초와 E2E 30초를 모두 만족한 요청의 비율 |

	`short`는 기본 호출 지연, `prefill`은 긴 입력이 TTFT에 주는 영향, `decode`는 긴 출력의 처리량을 봅니다. 각 시나리오를 동시성 `1,4,8,16`에서 반복합니다.

	### 비교할 때 고정할 것

	- 모델 ID와 양자화 방식
	- vLLM 이미지 버전
	- `max-model-len`, `gpu-memory-utilization`, `max-num-seqs`
	- 요청 시나리오와 동시성
	- 전원 모드, GPU 전력 상한, 실험 당시 온도

	이 중 하나라도 바뀌면 같은 기준선으로 취급하지 않고 별도 결과로 남깁니다.

</details>

<details>
<summary><strong>1. 실행 전 점검</strong></summary>

	### 저장소 루트와 환경 확인

	다음 명령은 저장소 루트에서 실행합니다.

	```bash
	pwd
	nvidia-smi
	kubectl get node -o wide
	kubectl get runtimeclass nvidia
	kubectl get node \
	  -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}{"\n"}'
	kubectl get pods -n monitoring
	```

	마지막에서 두 번째 명령이 `1`을 반환하지 않으면 배포를 진행하지 않습니다. 먼저 [`WSL2 GPU 실행 가이드`](./gpu-setup-windows-wsl2.md)의 K3s·Device Plugin 구간을 복구합니다.

	### 실험 시작값 기록

	```bash
	nvidia-smi --query-gpu=name,driver_version,memory.total,power.limit,temperature.gpu \
	  --format=csv
	kubectl version
	```

	드라이버, GPU 메모리, 전력 상한은 결과 해석에 영향을 주므로 출력값을 결과표에 옮겨 적습니다.

</details>

<details>
<summary><strong>2. vLLM 배포와 준비 확인</strong></summary>

	### 1.5B 기준 모델 배포

	```bash
	kubectl apply \
	  -f labs/wsl2-vllm-baseline/k8s/vllm-baseline.yaml
	kubectl rollout status deployment/vllm-baseline \
	  -n llm-serving-lab --timeout=20m
	```

	기본 모델은 `Qwen/Qwen2.5-1.5B-Instruct`, vLLM 이미지는 `v0.23.0`입니다. 최초 실행은 이미지와 모델을 내려받기 때문에 시간이 더 걸릴 수 있습니다.

	### 준비가 끝나지 않을 때

	```bash
	kubectl get pods -n llm-serving-lab -o wide
	kubectl describe pod -n llm-serving-lab -l app=vllm-baseline
	kubectl logs -n llm-serving-lab deployment/vllm-baseline --tail=200
	```

	`Pending`이면 GPU 할당과 PVC를, `CrashLoopBackOff`이면 OOM·모델 로딩·CUDA 오류를 먼저 확인합니다.

	### 로컬 포트 열기

	별도 터미널에서 다음 명령을 계속 실행해 둡니다.

	```bash
	kubectl port-forward -n llm-serving-lab svc/vllm-baseline 8000:8000
	```

	```bash
	curl -fsS http://localhost:8000/health
	curl -fsS http://localhost:8000/v1/models
	```

</details>

<details>
<summary><strong>3. 스모크 테스트</strong></summary>

	기준선 전체를 돌리기 전에 요청 수를 줄여 API·스트리밍·결과 저장만 확인합니다.

	```bash
	python3 labs/wsl2-vllm-baseline/benchmark.py \
	  --concurrency 1,4 \
	  --requests-per-level 2 \
	  --output labs/wsl2-vllm-baseline/results/smoke.json
	```

	완료 조건은 다음 세 가지입니다.

	- 모든 구간에서 `fail`이 `0`
	- TTFT와 E2E가 `-`가 아닌 숫자로 출력
	- `labs/wsl2-vllm-baseline/results/smoke.json` 생성

	실패 요청은 JSON의 `requests[].error`에 남습니다. 스모크 테스트가 실패하면 기준선 측정으로 넘어가지 않습니다.

</details>

<details>
<summary><strong>4. 1.5B 기준선 측정</strong></summary>

	```bash
	python3 labs/wsl2-vllm-baseline/benchmark.py \
	  --concurrency 1,4,8,16 \
	  --requests-per-level 8 \
	  --ttft-slo 2 \
	  --e2e-slo 30 \
	  --output labs/wsl2-vllm-baseline/results/baseline-1.5b.json
	```

	동시성 16에서는 요청 수도 최소 16개로 자동 조정됩니다. 결과 JSON에는 집계값과 요청별 원시값이 함께 저장됩니다.

	### 측정 중 함께 볼 메트릭

	```promql
	DCGM_FI_DEV_GPU_UTIL
	DCGM_FI_DEV_FB_USED
	DCGM_FI_DEV_POWER_USAGE
	rate(vllm:request_success_total[1m])
	histogram_quantile(0.95, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[5m])))
	```

	동시성이 올라갈수록 출력 처리량이 늘더라도 TTFT p95와 goodput이 급격히 나빠질 수 있습니다. 가장 높은 tok/s 하나보다 **goodput을 유지하는 최대 동시성**을 먼저 찾습니다.

</details>

<details>
<summary><strong>5. GPU 관측성 공백 확인</strong></summary>

	```bash
	kubectl apply \
	  -f labs/wsl2-vllm-baseline/k8s/gpu-telemetry-gap-rule.yaml
	kubectl get prometheusrule gpu-telemetry-gap-rules -n monitoring
	```

	이 규칙은 GPU 고장 자체가 아니라 **필요한 시계열이 없는 상태**를 구분합니다.

	| 경보 | 해석 |
	|---|---|
	| `GpuCoreTelemetryMissing` | 온도 등 기본 DCGM 수집 경로부터 끊김. 먼저 복구 필요 |
	| `GpuXidTelemetryMissing` | 기본 메트릭은 있지만 XID 오류 시계열 없음 |
	| `GpuProfilingTelemetryMissing` | 기본 메트릭은 있지만 Tensor Core 프로파일링 시계열 없음 |

	WSL2에서 뒤의 두 경보는 환경 한계의 기록이 될 수 있습니다. 경보를 억지로 없애기보다 “어떤 메트릭까지 관측할 수 있었는가”를 결과에 명시합니다.

</details>

<details>
<summary><strong>6. 7B AWQ 비교 실험</strong></summary>

	1.5B 기준선이 완성된 뒤에만 진행합니다.

	```bash
	kubectl set env deployment/vllm-baseline -n llm-serving-lab \
	  MODEL_ID=Qwen/Qwen2.5-7B-Instruct-AWQ \
	  SERVED_MODEL_NAME=qwen2.5-7b-awq
	kubectl rollout status deployment/vllm-baseline \
	  -n llm-serving-lab --timeout=20m
	```

	```bash
	python3 labs/wsl2-vllm-baseline/benchmark.py \
	  --concurrency 1,4,8,16 \
	  --requests-per-level 8 \
	  --ttft-slo 2 \
	  --e2e-slo 30 \
	  --output labs/wsl2-vllm-baseline/results/baseline-7b-awq.json
	```

	12GB VRAM에서 OOM이 나면 그 자체가 결과입니다. 실패한 모델·컨텍스트 길이·동시성·오류 메시지를 먼저 기록한 뒤 `max-model-len`과 `max-num-seqs`를 낮춥니다. 설정을 바꾼 결과는 기존 JSON에 덮어쓰지 않습니다.

</details>

<details>
<summary><strong>7. 결과 기록 양식</strong></summary>

	### 실행 환경

	| 항목 | 기록 |
	|---|---|
	| 측정 일시 | |
	| GPU / VRAM | |
	| 드라이버 / CUDA | |
	| GPU 전력 상한 | |
	| K3s / Kubernetes | |
	| vLLM 이미지 | `vllm/vllm-openai:v0.23.0` |
	| 모델 | |
	| `max-model-len` / `max-num-seqs` | `4096` / `16` |

	### 핵심 결과

	JSON의 시나리오별 집계값을 옮겨 적습니다.

	| 모델 | 시나리오 | 동시성 | TTFT p50/p95 | E2E p50/p95 | Output tok/s | Goodput | 실패 |
	|---|---|---:|---:|---:|---:|---:|---:|
	| 1.5B | short | 1 | | | | | |
	| 1.5B | short | 4 | | | | | |
	| 1.5B | short | 8 | | | | | |
	| 1.5B | short | 16 | | | | | |
	| 1.5B | prefill | 1/4/8/16 | | | | | |
	| 1.5B | decode | 1/4/8/16 | | | | | |
	| 7B AWQ | short/prefill/decode | 1/4/8/16 | | | | | |

	### 결론에 답할 질문

	1. goodput을 유지한 최대 동시성은 얼마였나?
	2. 긴 입력은 TTFT를 얼마나 늘렸나?
	3. 긴 출력에서 GPU 사용률과 출력 tok/s가 함께 올랐나?
	4. 7B AWQ는 1.5B보다 어떤 비용과 품질 선택지를 만들었나?
	5. WSL2에서 빠진 GPU 메트릭은 무엇이며, EKS에서는 확인할 수 있나?

</details>

<details>
<summary><strong>8. 종료와 재실행</strong></summary>

	### 모델 캐시를 남길 때

	```bash
	kubectl delete deployment vllm-baseline -n llm-serving-lab
	```

	### 모델 캐시까지 모두 지울 때

	```bash
	kubectl delete \
	  -f labs/wsl2-vllm-baseline/k8s/gpu-telemetry-gap-rule.yaml
	kubectl delete namespace llm-serving-lab
	```

	namespace를 지우면 PVC의 Hugging Face 모델 캐시도 함께 삭제됩니다. 재측정할 계획이면 Deployment만 삭제합니다.

</details>

---

## 이번 실행의 완료 기준

- `smoke.json`, `baseline-1.5b.json` 생성
- 모든 실패 요청의 원인 기록
- TTFT p95·출력 tok/s·goodput과 GPU 사용률을 함께 비교
- DCGM 핵심·XID·프로파일링 메트릭의 수집 여부 기록
- 결과표를 채우고 “goodput을 유지한 최대 동시성” 한 줄 결론 작성
- 가능하면 7B AWQ 결과를 별도 JSON으로 확보하고, 불가능하면 OOM 조건 기록

완성한 로컬 기준선은 [`Gemma 4 Cloud Run GPU 실습`](../../articles/Run%20inference%20of%20Gemma%204%20model%20on%20Cloud%20Run.md)의 A1~A4와 비교합니다. 모델 크기와 GPU가 다르므로 절대 수치의 승패보다 **동시성 증가에 따른 곡선과 병목이 나타나는 지점**을 비교합니다.

## 참고

- [vLLM 공식 Docker 가이드](https://docs.vllm.ai/en/latest/deployment/docker/)
- [vLLM 공식 Kubernetes 가이드](https://docs.vllm.ai/en/latest/deployment/k8s/)
- [vLLM 메트릭 문서](https://docs.vllm.ai/en/stable/design/metrics/)
- [Qwen2.5-1.5B-Instruct 모델 카드](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [Qwen2.5-7B-Instruct-AWQ 모델 카드](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ)
- [Prometheus `absent_over_time`](https://prometheus.io/docs/prometheus/latest/querying/functions/#absent_over_time)
