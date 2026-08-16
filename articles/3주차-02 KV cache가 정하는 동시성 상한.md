# 3주차-02 KV cache가 정하는 동시성 상한 — B3

> **시리즈** — [허브](./KV%20cache%EC%99%80%20%EC%84%9C%EB%B9%99%20%EA%B3%84%EC%B8%B5%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH5%C2%B7CH6%29.md) · [00 준비·측정 규칙](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) · [01 Ray Serve 계층](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) · [02 KV cache 상한](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) · [03 Triton](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)

> **이 편이 답하는 것**: 슬롯을 계속 키우면 되는가? **동시 요청 수의 상한은 무엇이 정하는가.**

**교재 CH5 「Estimating KV Cache Size」 + 공식 도전과제 2**입니다 — *"`max batch size`, `max model length`, `max number of tokens` 기본값 확인 및 변경 후 서빙 성능 측정 비교"*.

1주차 예습 노트에 남겨둔 질문이 **2주 만에** 여기서 닫힙니다:

> *"KV cache는 요청마다 쌓이는데, **동시 요청 수의 상한**은 무엇이 정하나?"*

**★ [01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md)의 RayService 환경을 그대로 재사용합니다.** 01을 먼저 끝내세요.

---

## 왜 Ray Serve 위에서 하는가

`rayservice-qwen.yaml`의 `serveConfigV2 → engine_kwargs`에 도전과제 2가 요구하는 세 노브가 그대로 노출돼 있습니다.

```yaml
engine_kwargs:
  max_model_len: 4096            # ← max model length
  gpu_memory_utilization: 0.85
  max_num_seqs: 16               # ← max batch size
  # max_num_batched_tokens: ...  # ← max number of tokens (후반부에서 추가)
```

그리고 **RayService는 `serveConfigV2` 변경을 zero-downtime으로 갈아끼웁니다.** 2주차에 `kubectl set env`로 재배포하며 겪은 사고 — **13일 전 구버전 배포가 떠 있어 변경이 무시된 것** — 가 구조적으로 없습니다. 스윕이 깨끗합니다.

### ⚠️ 시작 전 두 가지

1. **[01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md)의 C3-3(계층 오버헤드)을 먼저 끝낼 것.** `engine_kwargs`를 건드리면 통제 변수가 깨져 01의 비교가 무의미해집니다.
2. **`rayservice-qwen.yaml`을 직접 고쳐 커밋하지 말 것.** `ManifestTest`가 네 값을 지키고 있어 `make check`가 깨집니다. 스윕은 **복사본**으로 하세요.

```bash
cp labs/rayserve-on-k8s/rayservice-qwen.yaml /tmp/rayservice-sweep.yaml
# /tmp/rayservice-sweep.yaml 의 engine_kwargs 만 편집해서 apply
```

---

## B3-1. 손계산 먼저 ★ 로그를 보기 전에 적어두세요

로그가 정답을 직접 알려주므로, **보고 나서 계산하면 검증이 아니라 사후 맞추기**가 됩니다.

### 교재 CH5의 공식

```
토큰당 KV = 2(K,V) × 층 수 × 어텐션 헤드 수 × head_dim × 정밀도(바이트)
```

교재 예시는 Llama-2-7b(MHA):

```
2 × 32 × 32 × 128 × 2 = 524,288 바이트 = 0.5 MB/token
```

### ★ 그런데 이 공식은 MHA 전제입니다

교재도 못 박아 둡니다 — *"기본적인 멀티헤드 어텐션(MHA) 형태를 사용하는 Llama-2-7b를 사용하겠습니다"*, 그리고 *"이후 장에서 MQA, GQA, MLA 등 KV 캐시를 축소하고 압축하는 다른 아이디어들을 소개할 예정"* 이라고요.

**그 "이후 장"이 바로 이번 주 CH6**(「Scaling Attention and Kernel Optimization」)입니다. 그리고 **우리 모델 Qwen2.5-1.5B는 GQA**입니다. 그대로 넣으면 안 맞습니다.

```bash
# config.json에서 직접 확인 ★ 추측하지 말 것
POD=$(kubectl -n llm-serving-lab get pod -l ray.io/node-type=worker -o name | head -1)
kubectl -n llm-serving-lab exec "$POD" -- \
  python -c "
from transformers import AutoConfig
c = AutoConfig.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct')
print('num_hidden_layers   :', c.num_hidden_layers)
print('num_attention_heads :', c.num_attention_heads)
print('num_key_value_heads :', c.num_key_value_heads)   # ★ GQA면 위와 다르다
print('hidden_size         :', c.hidden_size)
print('torch_dtype         :', c.torch_dtype)
"
```

**두 공식으로 각각 계산해서 표에 나란히 적으세요.**

| | 공식 | 토큰당 KV |
|---|---|---|
| 교재 그대로 (MHA 가정) | `2 × L × num_attention_heads × head_dim × 2` | |
| GQA 반영 | `2 × L × **num_key_value_heads** × head_dim × 2` | |

### 동시성 예측

```
KV 예산 ≈ (VRAM 총량 × gpu_memory_utilization) − 가중치 − 활성화
실질 동시성 ≈ KV 예산 ÷ (토큰당 KV × max_model_len)
```

- VRAM 총량: 12,282 MiB (RTX 4080 Laptop)
- 가중치: 1.5B × 2바이트(BF16) ≈ 3.0 GB
- 활성화: 대략 1 GB 잡고 시작 (교재도 *"이론적 최대치를 온전히 다 쓸 수 없다"* 고 경고)

> 교재의 경험칙: **모델 크기의 약 2배 GPU 메모리를 확보하는 것을 시작점으로 권장.** 우리는 1.5B(3GB) 모델에 12GB이니 4배 — 여유가 있는 편입니다. 그래서 슬롯을 키울 여지가 있었던 것입니다.

---

## B3-2. `engine_kwargs` 스윕 ★ 도전과제 2 본체

네 조합을 돕니다. 각각 **다른 변수**를 건드립니다.

| # | `max_model_len` | `max_num_seqs` | `util` | 무엇을 보는가 |
|---|---|---|---|---|
| 1 | 4096 | 16 | 0.85 | 기준점 — **[01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) 결과 재사용, 새로 안 돌려도 됨** |
| 2 | 4096 | 64 | 0.85 | 슬롯 4배 — 메모리가 받쳐주나? |
| 3 | 16384 | 64 | 0.85 | **컨텍스트 4배 → 동시성이 1/4로 깎이는가** ★ 핵심 |
| 4 | 4096 | 64 | 0.60 | GPU 예산을 줄이면 상한도 그만큼 내려가는가 *(잘라내기 3순위)* |

각 롤아웃마다:

```bash
CFG="len16384-seqs64-util085"      # 조합에 맞게

# 1) /tmp/rayservice-sweep.yaml의 engine_kwargs 수정 후
kubectl apply -f /tmp/rayservice-sweep.yaml
kubectl -n llm-serving-lab get rayservice vllm-service -w    # 전환 대기 5~15분

# 2) ★ 기동 로그를 반드시 파일로 (00의 0-5)
POD=$(kubectl -n llm-serving-lab get pod -l ray.io/node-type=worker -o name | head -1)
kubectl -n llm-serving-lab logs "$POD" \
  | grep -iE "kv cache|gpu blocks|maximum concurrency" \
  | tee "results/b3-startup-${CFG}.txt"

# 3) 처리량 측정
cd labs/wsl2-vllm-baseline
python3 benchmark.py --scenarios short --concurrency 1,8,16,32,64 \
  --requests-per-level 100 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 --output "results/b3-${CFG}.json"

# 4) KV cache 사용률 최대 (메트릭 이름 주의 — 00의 0-4)
curl -s localhost:8000/metrics | grep vllm:kv_cache_usage_perc
```

### 관측 — 채울 표 ★ 이 편의 결론

| `max_model_len` | `max_num_seqs` | `util` | 손계산 (MHA) | 손계산 (GQA) | **로그의 `Maximum concurrency`** | KV 사용률 최대 | 처리량 (c=64) |
|---|---|---|---|---|---|---|---|
| 4096 | 16 | 0.85 | | | | | |
| 4096 | 64 | 0.85 | | | | | |
| 16384 | 64 | 0.85 | | | | | |
| 4096 | 64 | 0.60 | | | | | |

---

## B3-3. 미해결 관측 규명 ★ 글감으로 가장 좋은 부분

2주차에 이런 관측이 있었고 **원인 미확인**으로 남아 있습니다:

> 같은 `slots=64` 설정인데 어떤 롤아웃은 `Maximum concurrency` **59.50x**, 어떤 롤아웃은 **28.77x**.

28.77은 59.50의 **거의 정확히 절반**입니다. 손계산 기준선이 생기면 판정할 수 있습니다.

**확인 절차**:

```bash
# 롤아웃 직전/직후 VRAM을 각각 찍는다
nvidia-smi --query-gpu=memory.used,memory.total --format=csv | tee -a results/b3-vram-timeline.txt
```

| 가설 | 예측 | 확인법 |
|---|---|---|
| **직전 파드의 VRAM 미반환** (유력) | 새 파드 기동 시점의 `memory.used`가 0이 아님 → KV 예산이 그만큼 줄어듦 | 위 타임라인 |
| 활성화 메모리 추정 변동 | 같은 설정에서 재현되지 않음 | 같은 설정을 2회 롤아웃 |
| 측정 착오 | 로그를 다시 보면 설정이 실제로 달랐음 | 저장한 기동 로그 대조 |

> **운영 관점에서 이게 왜 무서운가**: 파드는 정상으로 뜨고 헬스체크도 통과하는데 **실질 수용량만 조용히 절반**이 됩니다. 부하가 올라가야 큐가 밀리면서 드러납니다. "롤아웃할 때마다 서비스 용량이 달라지는데 대시보드는 초록색" — CH5가 말하는 종류의 함정입니다. **글의 「운영 관점 · 안정성」에 그대로 들어갑니다.**

---

## B3-4. 도전과제 3 — chunked prefill *(잘라내기 1순위)*

여유가 있을 때만. 같은 `engine_kwargs`에 노브를 추가합니다.

```yaml
engine_kwargs:
  max_num_batched_tokens: 2048      # ← 청크 크기 역할
  # enable_chunked_prefill: true    # ← 버전에 따라 불필요
```

교재 CH6: *"별도의 '청크 크기' 전용 파라미터는 따로 없고, `--max-num-batched-tokens` 값 자체가 청크 크기를 결정합니다."*

### ⚠️ 먼저 확인할 것

**vLLM v0.23.0의 V1 엔진은 chunked prefill이 기본 ON일 가능성이 큽니다.** OFF로 내리는 방법이 없으면 "ON/OFF 비교"는 성립하지 않습니다.

```bash
POD=$(kubectl -n llm-serving-lab get pod -l ray.io/node-type=worker -o name | head -1)
kubectl -n llm-serving-lab logs "$POD" | grep -i "chunked"
```

- **OFF가 가능하면**: ON/OFF 비교 + `max_num_batched_tokens` 튜닝
- **OFF가 불가능하면**: **`max_num_batched_tokens` 튜닝 축만** 남기고 **그 사실 자체를 글에 적으세요** — "교재가 ON/OFF 비교를 제안하지만 이 버전에서는 기본값이 ON이라 성립하지 않았다"는 것도 관측 결과입니다

### 측정

**긴 프롬프트 시나리오라야 효과가 보입니다** (chunked prefill은 긴 prefill이 decode를 막는 것을 푸는 기법).

| `max_num_batched_tokens` | TTFT p95 | ITL p50 | 처리량 | 비고 |
|---|---|---|---|---|
| (기본값) | | | | 기본값을 먼저 확인해 기록 |
| 512 | | | | |
| 2048 | | | | |
| 8192 | | | | |

**기대**: 청크가 작을수록 긴 prefill이 잘게 쪼개져 **decode 요청의 ITL이 좋아지고 TTFT는 나빠진다.** 교재가 말한 *"TTFT와 ITL의 균형"* 이 이것입니다.

---

## 판단 기준

- ✅ **손계산(GQA)과 로그가 ±15% 안에 들어오면** 공식을 이해한 것입니다. MHA 공식은 크게 빗나가야 정상이고, **그 빗나감이 이 편의 결론**입니다
- ✅ **`max_model_len` 4096 → 16384에서 `Maximum concurrency`가 대략 1/4**이면 "컨텍스트 길이와 동시성이 같은 예산을 두고 경쟁한다"가 확인된 것입니다
- ✅ **`util` 0.85 → 0.60에서 상한이 비례 이상으로 줄면** 가중치가 고정 비용이기 때문입니다 (예산은 `총량×util − 가중치`라 util이 줄면 분자가 더 크게 깎임)
- ⚠️ **슬롯 64인데 `Maximum concurrency`가 그보다 작으면** — 슬롯 수가 아니라 **KV가 실질 상한**입니다. 이게 바로 이 편의 제목이 말하는 것
- ⚠️ **기동에 실패하면** 실패가 아니라 **결과입니다.** 로그를 기록하고 표에 "기동 실패"로 적으세요

## 기록 체크리스트

- [ ] `config.json` 값 4종 (층수 · 어텐션 헤드 · **KV 헤드** · head_dim)
- [ ] 손계산 2종 (MHA 공식 / GQA 공식) — **로그 보기 전에 적은 것**
- [ ] `results/b3-startup-*.txt` × 4 (기동 로그) ★ 가장 중요
- [ ] `results/b3-*.json` × 4 (처리량)
- [ ] `results/b3-vram-timeline.txt` (VRAM 반환 추적)
- [ ] KV cache 사용률 최대치 (`vllm:kv_cache_usage_perc`)
- [ ] (도전과제 3) chunked prefill 기본값 · OFF 가능 여부

## 다음 — [03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)으로

여기까지 끝나면 **GPU를 반납**합니다. [00의 0-2](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md)의 배타성 표를 따르세요.

```bash
kubectl delete -f /tmp/rayservice-sweep.yaml
helm uninstall kuberay-operator -n kuberay
nvidia-smi          # ★ 반환 확인 — 이 편에서 배운 것을 여기 적용
```
