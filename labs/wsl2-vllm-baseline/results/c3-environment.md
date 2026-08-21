# 3주차 환경 기록 — C3 (Ray Serve) / B3 / C2

측정 시작 2026-08-21 22:52 KST · 하드웨어는 2주차와 동일

## 하드웨어 · 커널

| 항목 | 값 |
|---|---|
| GPU | NVIDIA GeForce RTX 4080 Laptop GPU, 12,282 MiB |
| 드라이버 | 581.57 (WSL 내부 NVIDIA-SMI 580.102.01) |
| CUDA (드라이버 보고) | 13.0 |
| 커널 | 6.18.33.1-microsoft-standard-WSL2 |
| k3s | v1.36.2+k3s1 |

## ★ 통제 변수 — vLLM 버전이 갈린다

**이번 주 측정의 가장 중요한 사실입니다.** 01편이 "다르면 이건 비교가 아니다"라고 못박은 바로 그 지점이 실제로 갈렸습니다.

| 구성 | 이미지 | vLLM |
|---|---|---|
| B1 (2주차 기준선, 직접 vLLM) | `vllm/vllm-openai:v0.23.0` | **0.23.0** |
| C3 (Ray Serve) | `rayproject/ray-llm:2.44.1-py311-cu124` | **0.7.2** |

마이너 버전이 16개 벌어집니다. **B1과 C3를 그냥 빼면 "Ray Serve 계층의 가격"이 아니라 "계층 + 엔진 버전 차이"의 합**이 나옵니다.

→ 그래서 **같은 ray-llm 이미지로 Ray 없이 vLLM만 띄운 세 번째 구성**을 추가했습니다. 남는 변수가 Ray Serve 계층 하나로 좁혀집니다.

| # | 구성 | 이미지 | vLLM | 무엇이 분리되는가 |
|---|---|---|---|---|
| A | 직접 vLLM (B1, 2주차) | `vllm-openai:v0.23.0` | 0.23.0 | (기존 기준선) |
| B | 직접 vLLM (신규) | `ray-llm:2.44.1` | 0.7.2 | **A와의 차 = 엔진 버전의 가격** |
| C | Ray Serve | `ray-llm:2.44.1` | 0.7.2 | **B와의 차 = 계층의 순수 가격** |

## Ray 스택 (C3 워커 파드 내부 실측)

| 항목 | 값 |
|---|---|
| Ray | 2.44.1 |
| vLLM | 0.7.2 |
| PyTorch | 2.5.1+cu124 |
| transformers | 4.49.0 |
| KubeRay operator | 1.4.2 (helm) |

## 이미지 크기 — 계획의 추정치 정정

| 이미지 | 계획서 추정 | **실측** |
|---|---|---|
| `rayproject/ray-llm:2.44.1-py311-cu124` | ~10GB | **11.9 GiB 다운로드** (280초, 평균 43.4 MiB/s) |
| `nvcr.io/nvidia/tritonserver:24.12-py3` | 9.63GB ↔ ~17GB (문서 간 불일치) | **디스크 27.4GB** |

**Triton 이미지 크기 불일치가 풀렸습니다.** 노션 CH3 기록의 *"9.63GB(디스크 27.4GB)"* 가 맞고, 계획서의 `~17GB`가 틀린 값이었습니다. 9.63GB는 **압축된 다운로드 크기**, 27.4GB는 **압축 푼 디스크 크기**입니다. `docker images`가 보고하는 값은 후자입니다.

## ★ 관측성 — Ray Serve로 감싸면 vLLM 메트릭이 통째로 사라진다

2주차 측정의 서버 측 교차검증(큐 궤적·KV 사용률·goodput)은 전부 `:8000/metrics`의 `vllm:*` 메트릭에 의존했습니다. **Ray Serve 아래에서는 그게 없습니다.**

| 엔드포인트 | 구성 C (Ray Serve) | 구성 B (같은 엔진, Ray 없음) |
|---|---|---|
| `:8000/metrics` | **404** | **200** (3,114 B) |
| `vllm:*` 이름 수 | **0개** | **15개** |
| 대신 나오는 것 | 워커/헤드 `:8080`에 `ray_*` 184개 (`ray_serve_deployment_processing_latency_ms` 등) | — |

**같은 vLLM 0.7.2인데 계층 유무로 갈립니다** → 버전 탓이 아니라 **계층 탓**입니다. `num_requests_running` / `num_requests_waiting` / KV 사용률 같은 **엔진 내부 지표를 잃고**, 대신 배포·레플리카 단위의 Ray Serve 지표를 얻습니다. 입도가 다릅니다.

목록: `results/metrics-rayserve.txt`(194) · `results/metrics-direct-v072.txt`(15)

> 덤으로 3주차-00의 0-4가 지적한 **메트릭 이름 변경**도 확인됐습니다 — 0.7.2는 `vllm:gpu_cache_usage_perc`, 0.23.0은 `vllm:kv_cache_usage_perc`입니다. 이름이 버전 사이에서 바뀐 것이 맞습니다.

## 구성 B를 띄울 때 걸린 것 — HF 캐시 PVC 권한

2주차의 `huggingface-cache` PVC를 그대로 붙였더니 죽었습니다.

```
PermissionError: [Errno 13] Permission denied: '/root/.cache/huggingface/token'
```

`vllm/vllm-openai` 이미지는 **root**로 돌아 `/root/.cache`에 썼지만, `rayproject/ray-llm`은 **uid 1000(`ray`)** 으로 돕니다. 캐시를 공유하려면 권한을 맞춰야 하는데, 모델이 3GB라 **새로 받는 편이 쌉니다**(2~3분). PVC를 떼고 컨테이너 기본 캐시를 쓰게 했습니다.

## 모델 · 엔진 설정 (세 구성 공통)

| 항목 | 값 |
|---|---|
| 모델 | `Qwen/Qwen2.5-1.5B-Instruct` |
| served name | `qwen2.5-1.5b` |
| `max_model_len` | 4096 |
| `gpu_memory_utilization` | 0.85 |
| `max_num_seqs` | 16 |
| dtype | auto |

## 고친 저장소 결함

### `accelerator_type: null`이 Serve 앱 배포를 통째로 막는다 ★ 2026-08-21

`rayservice-qwen.yaml`의 `accelerator_type: null` 한 줄 때문에 Serve 앱이 배포되지 않았습니다. RayService 자체는 `Running`으로 보이고 파드도 둘 다 뜨지만, **`NUM SERVE ENDPOINTS`가 영영 비어 있고** `serviceStatus`도 채워지지 않습니다.

```
pydantic_core._pydantic_core.ValidationError: 2 validation errors for LLMServingArgs
llm_configs.0.LLMConfig.accelerator_type
  Value error, Unsupported accelerator type: None
```

- **증상이 조용합니다.** `kubectl get pod`은 정상이고 `kubectl get rayservice`는 그냥 빈 칸이라, 원인이 파드 이벤트나 operator 로그가 아니라 **Serve 대시보드 API**(`:8265/api/serve/applications/`)에만 남습니다.
- 원인: `null`은 "값 없음"이 아니라 "None이라는 값"으로 검증기에 전달됩니다. **필드를 통째로 생략**해야 합니다.
- 공식 예제가 이 자리에 `A10G` 같은 구체 값을 넣기 때문에, GPU 종류를 고정하고 싶지 않을 때 `null`로 적기 쉬운 함정입니다.
- 이 매니페스트는 작성 후 **실제로 배포된 적이 없어** 결함이 잠복해 있었습니다. `ManifestTest`는 네 값(모델·`max_model_len`·`util`·`max_num_seqs`)만 지키므로 이 줄을 잡지 못합니다.

**진단 명령** (파드 이벤트로는 안 보입니다):

```bash
HEAD=$(kubectl -n llm-serving-lab get pod -l ray.io/node-type=head -o name | head -1)
kubectl -n llm-serving-lab exec "$HEAD" -- \
  python -c "import json,urllib.request; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8265/api/serve/applications/').read()), indent=1)[:3000])"
```
