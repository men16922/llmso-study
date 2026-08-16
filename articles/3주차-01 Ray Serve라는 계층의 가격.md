# 3주차-01 Ray Serve라는 계층의 가격 — C3

> **시리즈** — [허브](./KV%20cache%EC%99%80%20%EC%84%9C%EB%B9%99%20%EA%B3%84%EC%B8%B5%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH5%C2%B7CH6%29.md) · [00 준비·측정 규칙](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) · [01 Ray Serve 계층](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) · [02 KV cache 상한](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) · [03 Triton](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)

> **이 편이 답하는 것**: 직접 띄운 vLLM 위에 오케스트레이션 계층을 하나 얹으면 **얼마를 내야 하는가.**
> 그리고 그 대가로 무엇을 받는가.

**CH4 공식 도전과제**입니다 — *"로컬 PC에 kind(k8s)로 RayService 배포 테스트 해보기"*. kind 대신 이미 있는 **K3s**를 씁니다.

**★ 이 편이 안전판입니다.** 여기까지만 끝내도 글 한 편이 섭니다. 반드시 먼저 완료하세요.

원설계(가설의 배경, 노브 대응표)는 [`2주차-03`의 C3 절](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)에 있습니다. 이 문서는 **실행 런북**입니다.

---

## 따라하기로 끝내지 않는 법 — 접점 두 개

도전과제를 그냥 수행하면 "배포해봤다"로 끝납니다. 앞선 실험과 **직접 비교되는 두 축**으로 붙입니다.

| 접점 | 비교 | 답하는 질문 |
|---|---|---|
| **①** | B1(직접 vLLM) ↔ C3(Ray Serve로 감싼 vLLM) | **오케스트레이션 계층은 얼마를 먹는가** |
| **②** | C2(Triton `dynamic_batching`) ↔ C3(`@serve.batch`) | dynamic batching은 **프레임워크가 정하는가, 워크로드가 정하는가** |

②의 근거는 노브가 정확히 대응한다는 것입니다.

| Triton | Ray Serve |
|---|---|
| `max_batch_size: 8` | `@serve.batch(max_batch_size=8)` |
| `max_queue_delay_microseconds: 5000` | `@serve.batch(batch_wait_timeout_s=0.005)` |
| `dynamic_batching` 블록 없음 (대조군) | `@serve.batch` 데코레이터 없음 (대조군) |

> ②는 **잘라내기 2순위**입니다. 시간이 부족하면 이 대응표만 글에 남기고 측정은 생략하세요.

## 가설

1. Ray Serve로 감싸면 **TTFT가 늘고 처리량이 준다.** 그 차이가 계층의 가격이다.
2. 그 차이는 **동시성에 거의 무관한 고정 오버헤드**일 것이다 (HTTP 라우팅 한 겹). 동시성에 비례해 커진다면 그건 Ray Serve의 프록시가 병목이라는 뜻.
3. `@serve.batch` 곡선은 **[03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)의 Triton 곡선과 같은 모양**일 것이다. 다르다면 그건 구현 차이지 개념 차이가 아니다.

---

## C3-1. 통제 변수 ★ 이걸 놓치면 ①이 무의미합니다

공식 가이드는 `Qwen2.5-7B-Instruct-AWQ`를 쓰지만, **B1과 다른 모델이면 오버헤드를 분리할 수 없습니다.** [`labs/rayserve-on-k8s/rayservice-qwen.yaml`](../labs/rayserve-on-k8s/README.md)은 B1과 값을 맞춰 두었습니다.

| 항목 | 값 (= B1) |
|---|---|
| 모델 | `Qwen/Qwen2.5-1.5B-Instruct` |
| `max_model_len` | 4096 |
| `gpu_memory_utilization` | 0.85 |
| `max_num_seqs` | 16 |

> `test_rayserve_lab.py`의 `ManifestTest`가 이 네 값을 지킵니다. 하나라도 어긋나면 `make check`가 실패합니다 — 실수로 공식 예제 값을 붙여넣는 사고를 막습니다.

⚠️ **`vllm` 버전도 통제 변수입니다.** 이미지가 다르면 엔진 버전이 달라질 수 있습니다. [00의 0-6](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md)로 양쪽을 확인해 기록하세요. **다르면 이건 비교가 아닙니다** — 글에 반드시 명시하세요.

## C3-2. 배포

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/ && helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.4.2 -n kuberay --create-namespace
kubectl -n kuberay get pod

# ★ GPU 1장 — vllm-baseline과 동시에 못 쓴다
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0
nvidia-smi                                    # VRAM 반환 확인

kubectl apply -f labs/rayserve-on-k8s/rayservice-qwen.yaml
kubectl -n llm-serving-lab get rayservice vllm-service -w      # READY까지 5~15분
```

**READY가 되면 즉시 기동 로그를 저장하세요** ([00의 0-5](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md)). 이 값이 [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) 표의 첫 행이 됩니다.

```bash
POD=$(kubectl -n llm-serving-lab get pod -l ray.io/node-type=worker -o name | head -1)
kubectl -n llm-serving-lab logs "$POD" \
  | grep -iE "kv cache|gpu blocks|maximum concurrency" \
  | tee results/b3-startup-len4096-seqs16-util085.txt
```

## C3-3. 접점 ① — 계층 오버헤드 ★ 이 편의 핵심

**B1과 똑같은 명령**을 던집니다. Ray Serve LLM은 OpenAI 호환이라 `--api openai` 그대로입니다.

```bash
kubectl -n llm-serving-lab port-forward --address 0.0.0.0 svc/vllm-service-serve 8000:8000 &

cd labs/wsl2-vllm-baseline
python3 benchmark.py --scenarios short --concurrency 1,2,4,8,16,32,64 \
  --requests-per-level 100 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 --output results/c3-rayserve-short.json

# B1의 slots=16과 나란히 — --delta가 차이·차이% 열을 붙인다
python3 summarize_results.py \
  results/b1-slots-16-short.json results/c3-rayserve-short.json \
  --label-regex '(b1-slots-16|c3-rayserve)' --delta --metric output_tok_per_s
python3 summarize_results.py \
  results/b1-slots-16-short.json results/c3-rayserve-short.json \
  --label-regex '(b1-slots-16|c3-rayserve)' --delta --metric ttft_p95_s
```

### 관측 — 채울 표

**처리량 (tok/s)**

| 동시성 | 직접 vLLM (B1) | Ray Serve (C3) | 차이 | 차이 % |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 4 | | | | |
| 8 | | | | |
| 16 | | | | |
| 32 | | | | |
| 64 | | | | |

**TTFT p95 (s)** — 같은 형식으로 하나 더

| 동시성 | 직접 vLLM (B1) | Ray Serve (C3) | 차이 | 차이 % |
|---|---|---|---|---|
| 1 | | | | |
| 8 | | | | |
| 16 | | | | |
| 32 | | | | |
| 64 | | | | |

> ★ **처리량만 보지 마세요.** 2주차에서 goodput이 조용히 무너진 전례가 있습니다(200/200 성공인데 goodput 8%). **TTFT p95를 나란히** 놓아야 "계층의 가격"이 제대로 보입니다.

## C3-4. 접점 ② — `@serve.batch` 스윕 *(잘라내기 2순위)*

[03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)과 같은 지점(off / 0 / 1ms / 5ms / 20ms)을 돕니다.

```bash
cd labs/rayserve-on-k8s
for WAIT in off 0 0.001 0.005 0.02; do
  MAX_BATCH_SIZE=8 BATCH_WAIT_S=$WAIT serve run mobilenet_serve:app &
  sleep 20
  # 부하를 건 뒤
  curl -s localhost:8000/stats | python3 -m json.tool
  serve shutdown -y
done
```

`/stats`가 `avg_batch_size = requests_seen / batches_run`을 돌려줍니다 — **[03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)의 `nv_inference_request_success / nv_inference_exec_count`와 같은 정의**입니다.

| 대기 시간 | Triton 평균 배치 | Ray Serve 평균 배치 | Triton 처리량 | Ray Serve 처리량 |
|---|---|---|---|---|
| (배칭 끔) | 1.00 | 1.00 | | |
| 0 | | | | |
| 1ms | | | | |
| 5ms | | | | |
| 20ms | | | | |

## C3-5. 배포 계층 관찰 (도전과제 본래 목적)

```bash
kubectl -n llm-serving-lab port-forward svc/vllm-service-serve 8265:8265 &   # Ray Dashboard
kubectl get raycluster -n llm-serving-lab
kubectl -n llm-serving-lab describe rayservice vllm-service | tail -30
```

관찰할 것:

- ★ **zero-downtime 업그레이드** — `serveConfigV2`를 바꾸면 **새 RayCluster를 띄우고 전환**합니다. B1의 `kubectl set env` 재배포(파드가 죽었다 뜨는, `strategy: Recreate`)와 대비하면 계층이 주는 값어치가 드러납니다
  - 2주차에 **13일 전 구버전 배포가 떠 있어 `kubectl set env`가 무시된 사고**가 있었습니다. RayService에서는 이 사고가 구조적으로 안 생깁니다 — 그 대비가 「운영 관점 · 안정성」의 소재입니다
- Ray Dashboard의 Serve 탭에서 **replica 수 · 큐 길이 · 실패율**
- `kubectl get raycluster`로 헤드/워커 파드 구조

> **이 관찰이 [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)로 이어집니다.** zero-downtime 롤아웃이 된다는 것은 곧 `engine_kwargs` 스윕을 깨끗하게 돌릴 수 있다는 뜻입니다.

---

## 판단 기준

- ✅ **가설 1·2**: 차이가 있되 동시성에 거의 무관하면 **고정 오버헤드**입니다. **동시성에 비례해 커지면** Ray Serve 프록시가 병목이고, 그건 "계층을 얹으면 언제 손해인가"의 답입니다.
- ✅ **가설 3**: `@serve.batch` 곡선이 Triton 곡선과 같은 모양이면 — **dynamic batching은 프레임워크의 기능이 아니라 워크로드의 성질**이라는 뜻입니다. 시리즈 전체의 결론을 한 번 더 지지합니다.
- ⚠️ **오버헤드가 음수(Ray Serve가 더 빠름)** 라면 통제 변수를 의심하세요. `ManifestTest`가 지키는 네 값 외에 다른 게 달라진 것입니다 — 가장 유력한 것은 **이미지에 따른 vLLM 버전 차이**입니다. 그 경우 **양쪽 버전을 반드시 기록**하고, 글에서 "같은 조건 비교가 아니다"라고 명시하세요.
- ⚠️ **오버헤드가 20%를 넘으면** port-forward 경로를 의심하세요. B1과 C3가 같은 방식으로 노출됐는지 확인해야 합니다.

## 정리 — [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)로 넘어가기

**RayService를 내리지 마세요.** [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)가 이 환경을 그대로 재사용합니다.

[03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)으로 넘어갈 때만 전부 내립니다:

```bash
kubectl delete -f labs/rayserve-on-k8s/rayservice-qwen.yaml
helm uninstall kuberay-operator -n kuberay
nvidia-smi                                    # ★ VRAM 반환 확인
```

## 기록 체크리스트

- [ ] `results/c3-rayserve-short.json`
- [ ] `results/b3-startup-len4096-seqs16-util085.txt` (기동 로그)
- [ ] `--delta` 출력 2종 (처리량 · TTFT p95)
- [ ] Ray Serve 쪽 vLLM 버전 · KubeRay 버전
- [ ] Ray Dashboard Serve 탭 스크린샷 (replica·큐 길이)
- [ ] `serveConfigV2` 변경 시 롤아웃 관찰 기록 (zero-downtime 여부)
- [ ] Ray Serve의 `/metrics` 이름 목록 (`results/metrics-rayserve.txt`) — B1과 다르면 그 자체가 기록거리
