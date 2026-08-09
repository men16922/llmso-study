# 2주차-03 dynamic batching과 그 위의 계층 — C2·C3

> **시리즈** — [허브](./vLLM%20%EB%B0%B0%EC%B9%AD%C2%B7%ED%81%90%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH3%C2%B7CH4%29.md) · [00 준비·측정 규칙](./2%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) · [01 배치 슬롯과 큐](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md) · [02 배칭을 직접 짜기](./2%EC%A3%BC%EC%B0%A8-02%20%EB%B0%B0%EC%B9%AD%EC%9D%84%20%EC%A7%81%EC%A0%91%20%EC%A7%9C%EA%B8%B0.md) · [03 dynamic batching과 계층](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)

> **이 편이 답하는 것**: 배칭 4종 중 남은 한 칸(dynamic)을 Triton으로 채우고,
> 그 위에 Ray Serve라는 오케스트레이션 계층을 얹으면 얼마를 내야 하는지 잽니다.

앞선 편의 결과가 입력입니다 — [01 배치 슬롯과 큐](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md)의 `slots=16` 결과와
[02 배칭을 직접 짜기](./2%EC%A3%BC%EC%B0%A8-02%20%EB%B0%B0%EC%B9%AD%EC%9D%84%20%EC%A7%81%EC%A0%91%20%EC%A7%9C%EA%B8%B0.md)의 패딩 낭비 관측이 있어야 이 편의 마무리가 섭니다.

---

## C2. dynamic batching은 언제 쓰나 — Triton으로 마지막 칸 채우기 ★

> 1주차 예습 노트에 남겨둔 질문입니다: *"continuous batching이 static보다 항상 낫다면, **dynamic batching은 언제 쓰나?** (힌트: **LLM이 아닌 모델**)"*

B1·B2·C1까지로 배칭 없음 / static / continuous는 다 쟀습니다. **dynamic만 비어 있습니다.** 그리고 그건 vLLM으로는 잴 수 없습니다 — vLLM에 dynamic batching 모드가 없으니까요. 교재 CH3가 Triton을 가져오는 자리가 정확히 여기입니다.

### 가설

1. `max_queue_delay`를 키우면 **평균 배치 크기와 처리량이 오르고, p95 지연이 나빠진다.** 기다림을 팔아 처리량을 사는 것.
2. **동시성이 낮으면 delay는 순손실이다.** 기다려도 묶을 요청이 없으니 지연만 늘어난다 → dynamic의 효과는 **도착률에 의존**한다.
3. **이 방식이 LLM에 안 맞는 이유**는 배치를 통째로 묶어 통째로 내보내기 때문이다. mobilenet은 모든 요청의 연산량이 정확히 같아 성립하지만, LLM은 출력 길이가 제각각이라 배치가 **가장 긴 요청에 인질로 잡힌다.** (C1에서 본 패딩 낭비가 그 증거)

### C2-0. 준비

```bash
# GPU 확보 — C1 서버와 k3s vLLM 둘 다 내려간 상태여야 한다
pkill -f "python main.py" || true
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0
nvidia-smi

cd ~/llm-model-inference/ch03/multi_model_serving
docker images | grep tritonserver     # 세션 1에서 풀어둔 이미지 확인
```

### C2-1. 배치 축이 열린 모델 만들기 ★ 이게 진짜 장벽입니다

저장소에 들어 있는 `densenet_onnx`로는 **dynamic batching을 켤 수 없습니다.** `config.pbtxt`를 보면 이유가 나옵니다.

```protobuf
max_batch_size : 0                       # ← 배칭 자체가 꺼져 있음
dims: [ 3, 224, 224 ]
reshape { shape: [ 1, 3, 224, 224 ] }    # ← 배치 차원 1을 억지로 끼워 넣는 중
```

이 ONNX는 **배치 축이 1로 고정**이라 `max_batch_size`를 켜면 모델이 거부합니다. `reshape`가 그 우회 흔적입니다.

`models.json`에 이미 있는 **`mobilenet_v2`를 배치 축이 열린 상태로 직접 export**합니다. 스크립트는 [`labs/triton-dynamic-batching/`](../labs/triton-dynamic-batching/README.md)에 **이미 만들어져 있습니다.**

```bash
LAB=~/"Hands-On LLM Serving and Optimization Study"/labs/triton-dynamic-batching
cd ~/llm-model-inference/ch03/multi_model_serving

python3 "$LAB/export_mobilenet_onnx.py" \
  --out model_dir/mobilenet_v2/1/model.onnx --verify
```

핵심은 이 한 줄입니다.

```python
dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}   # ★ 배치 축을 연다
```

> **이 한 줄이 실험 전체를 가능하게 합니다.** 글에 꼭 남기세요 — "배칭을 지원하려면 모델이 먼저 배치를 받아들여야 한다"는, 서빙 계층만 봐서는 안 보이는 제약입니다. `--verify`가 export 결과의 첫 차원이 실제로 심볼(dynamic)인지 확인해 줍니다.

### C2-2. config 생성기 — `make_config.py`

`max_batch_size > 0`이면 `dims`에서 **배치 차원을 빼고** 씁니다(Triton이 앞에 붙임).

```bash
python3 "$LAB/make_config.py" off  > model_dir/mobilenet_v2/config.pbtxt   # 대조군
python3 "$LAB/make_config.py" 5000 > model_dir/mobilenet_v2/config.pbtxt   # 5ms 대기
```

> **대조군은 `max_batch_size: 0`이 아니라 `off`입니다.** `0`으로 두면 Triton이 입력 텐서 모양을 다르게 해석해 **모델 시그니처까지 달라지고**, 비교가 깨집니다. `dynamic_batching` **블록만 빼야** 모델은 그대로 두고 배칭만 끈 올바른 대조군이 됩니다. `test_control_group_keeps_the_same_model_signature`가 `off` 출력이 `5000` 출력의 접두사임을 검증합니다.

### C2-3. Triton 기동

`--model-control-mode=explicit`이라 **컨테이너 재시작 없이 unload/load만으로 config를 다시 읽습니다.** 스윕이 빨라지는 이유입니다.

```bash
docker run -d --name triton --gpus all \
  -p8009:8000 -p8010:8001 -p8011:8002 \
  -v $(pwd)/model_dir:/models \
  nvcr.io/nvidia/tritonserver:24.12-py3 \
  tritonserver --model-repository=/models --model-control-mode=explicit

curl -s -X POST localhost:8009/v2/repository/models/mobilenet_v2/load
curl -s localhost:8009/v2/models/mobilenet_v2/config | python3 -m json.tool | head -30
```

마지막 줄로 **실제 적용된 config를 확인**하세요. 파일을 고쳤는데 반영이 안 된 경우를 여기서 잡습니다. (스윕 스크립트가 매 회 자동으로 확인합니다.)

### C2-4. 평균 배치 크기 재기 ★ 이 실험의 핵심 지표

Triton은 `:8011/metrics`에 Prometheus 메트릭을 냅니다. 그중 둘을 나누면 **실제 배치가 몇 개씩 묶였는지가 직접** 나옵니다.

```
평균 배치 크기 = nv_inference_request_success / nv_inference_exec_count
                (처리한 요청 수)             ÷ (모델을 실행한 횟수)
```

배칭이 꺼져 있으면 정확히 `1.00`, 5ms를 기다려 6개씩 묶였다면 `6.00` 근처. **"동작하는 것 같다"가 아니라 숫자로 증명되는 지점**입니다.

```bash
python3 "$LAB/triton_metrics.py" snapshot > before.txt
#  ... 부하 ...
python3 "$LAB/triton_metrics.py" snapshot > after.txt
python3 "$LAB/triton_metrics.py" delta before.txt after.txt --model mobilenet_v2
# → 요청 600 / 실행 100 → 평균 배치 크기 6.00 | 큐 대기 5.000 ms/req | 연산 2.000 ms/req
```

**반드시 차분해야 합니다.** Triton 카운터는 서버 기동 이후 누적이라 그냥 나누면 이전 실험까지 섞입니다. `queue_duration`이 요청당 몇 ms인지가 `max_queue_delay`가 실제로 얼마나 쓰였는지를 알려줍니다.

### C2-5. 스윕 — `sweep.sh`

```bash
cd ~/llm-model-inference/ch03/multi_model_serving
bash "$LAB/sweep.sh"            # 기본: off 0 1000 5000 20000
```

delay마다 ① config 생성 ② unload/load ③ **서버에 적용된 값 되읽기** ④ 부하 ⑤ 카운터 차분을 돕니다. 결과는 `results/c2-delay-*.json`과 `results/c2-batch-stats.txt`에 쌓입니다.

> unload/load로 config가 반영되지 않으면 컨테이너를 재시작하세요(`docker restart triton`). 매번 20~30초가 더 듭니다.

### 관측 — 채울 표

평균 배치 크기·큐 대기는 `results/c2-batch-stats.txt`에, 처리량·지연은 `results/c2-delay-*.json`에 있습니다.

**동시성 8 기준**

| `max_queue_delay` | 평균 배치 크기 | 처리량 (inf/s) | p50 (ms) | p95 (ms) | 큐 대기 (ms/req) |
|---|---|---|---|---|---|
| (dynamic 끔) | 1.00 | | | | |
| 0 μs | | | | | |
| 1,000 μs (1ms) | | | | | |
| 5,000 μs (5ms) | | | | | |
| 20,000 μs (20ms) | | | | | |

**도착률 의존성 ★ 질문의 답이 여기 있습니다** — 같은 delay(5ms)를 동시성만 바꿔가며

| 동시성 | 평균 배치 크기 | 처리량 (inf/s) | p95 (ms) | dynamic 끔 대비 p95 |
|---|---|---|---|---|
| 1 | | | | |
| 8 | | | | |
| 32 | | | | |

### 판단 기준

- ✅ **가설 1**: delay ↑ → 평균 배치 크기 ↑, 처리량 ↑, p95 ↑. 세 값이 같이 움직여야 합니다.
- ✅ **가설 2 ★ 이게 질문의 답입니다**: **동시성 1에서는 평균 배치 크기가 1.00에 머물고 p95만 delay만큼 늘어납니다.** 기다렸는데 아무도 안 온 것 — 순손실입니다. 그래서 dynamic batching의 delay는 **예상 도착률에 맞춰 정해야** 하고, 트래픽이 들쭉날쭉하면 그 자체가 약점이 됩니다.
- 💡 **`delay=0`인데 평균 배치 크기가 1보다 크면**: 기다리지 않아도 **이미 큐에 쌓여 있던 것**만으로 묶인 것입니다. 부하가 충분히 높으면 delay 없이도 dynamic이 동작한다는 뜻이고, 뒤집으면 delay는 **부하가 낮을 때를 위한 장치**입니다.
- ⚠️ **평균 배치 크기가 계속 1.00이면**: config가 반영되지 않았습니다. `curl localhost:8009/v2/models/mobilenet_v2/config`로 실제 값을 확인하세요.
- ⚠️ **`load`가 실패하면**: `dims`에 배치 차원을 넣었거나(빼야 함) ONNX의 배치 축이 안 열린 것입니다. `docker logs triton`에 이유가 나옵니다.

### 보너스 — 모델 스와핑 (여유가 있으면)

`manager.py:11`의 `max_models: int = 2`가 LRU 캐시 상한입니다. Triton의 explicit 모드 load/unload와 붙여 **모델 3개를 번갈아 요청하면 매번 스와핑이 일어나는** 상황을 만들 수 있습니다. 스와핑 지연을 재면 "GPU에 안 올라간 모델은 첫 요청이 비싸다"가 숫자로 나옵니다 — 5주차 multi-LoRA의 복선입니다.

### 정리

```bash
docker rm -f triton
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=1   # k3s 복구
```

---

---

## C3. 그 위에 계층을 하나 더 — Ray Serve on K8s ★ CH4 도전과제

> 노션 CH4의 도전과제입니다: *"로컬 PC에 kind(k8s)로 RayService 배포 테스트 해보기"*. kind 대신 **이미 있는 K3s**를 씁니다.

### 따라하기로 끝내지 않는 법 — 접점 두 개

배포만 하면 "해봤다"로 끝납니다. 앞선 실험과 **직접 비교되는 두 축**으로 붙입니다.

| 접점 | 비교 | 답하는 질문 |
|---|---|---|
| **①** | B1(직접 vLLM) ↔ C3(Ray Serve로 감싼 vLLM) | **오케스트레이션 계층은 얼마를 먹는가** |
| **②** | C2(Triton `dynamic_batching`) ↔ C3(`@serve.batch`) | dynamic batching은 **프레임워크가 정하는가, 워크로드가 정하는가** |

②의 근거는 노브가 정확히 대응한다는 것입니다.

| Triton | Ray Serve |
|---|---|
| `max_batch_size: 8` | `@serve.batch(max_batch_size=8)` |
| `max_queue_delay_microseconds: 5000` | `@serve.batch(batch_wait_timeout_s=0.005)` |
| `dynamic_batching` 블록 없음 | `@serve.batch` 데코레이터 없음 |

**같은 모델(mobilenet_v2), 같은 두 노브, 다른 프레임워크.** C2에서 그린 곡선을 여기서 다시 그립니다.

### 가설

1. Ray Serve로 감싸면 **TTFT가 늘고 처리량이 준다.** 그 차이가 계층의 가격이다.
2. 그 차이는 **동시성에 거의 무관한 고정 오버헤드**일 것이다 (HTTP 라우팅 한 겹). 동시성에 비례해 커진다면 그건 Ray Serve의 프록시가 병목이라는 뜻.
3. `@serve.batch` 곡선은 **C2의 Triton 곡선과 같은 모양**일 것이다. 다르다면 그건 구현 차이지 개념 차이가 아니다.

### C3-1. 통제 변수 ★ 이걸 놓치면 ①이 무의미합니다

공식 가이드는 `Qwen2.5-7B-Instruct-AWQ`를 쓰지만, **B1과 다른 모델이면 오버헤드를 분리할 수 없습니다.** [`labs/rayserve-on-k8s/rayservice-qwen.yaml`](../labs/rayserve-on-k8s/README.md)은 B1과 값을 맞춰 두었습니다.

| 항목 | 값 (= B1) |
|---|---|
| 모델 | `Qwen/Qwen2.5-1.5B-Instruct` |
| `max_model_len` | 4096 |
| `gpu_memory_utilization` | 0.85 |
| `max_num_seqs` | 16 |

> `test_rayserve_lab.py`의 `ManifestTest`가 이 네 값을 지킵니다. 하나라도 어긋나면 `make check`가 실패합니다 — 실수로 공식 예제 값을 붙여넣는 사고를 막습니다.

### C3-2. 배포

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/ && helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.4.2 -n kuberay --create-namespace

# ★ GPU 1장 — vllm-baseline과 동시에 못 쓴다
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0

kubectl apply -f labs/rayserve-on-k8s/rayservice-qwen.yaml
kubectl -n llm-serving-lab get rayservice vllm-service -w      # READY까지 5~15분
```

### C3-3. 접점 ① — 계층 오버헤드

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

**관측 — 채울 표**

| 동시성 | 직접 vLLM (tok/s) | Ray Serve (tok/s) | 차이 | 차이 % |
|---|---|---|---|---|
| 1 | | | | |
| 8 | | | | |
| 16 | | | | |
| 32 | | | | |
| 64 | | | | |

**TTFT p95 (s)** — 같은 형식으로 하나 더

### C3-4. 접점 ② — `@serve.batch` 스윕

C2와 같은 지점(off / 0 / 1ms / 5ms / 20ms)을 돕니다.

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

`/stats`가 `avg_batch_size = requests_seen / batches_run`을 돌려줍니다 — **C2의 `nv_inference_request_success / nv_inference_exec_count`와 같은 정의**입니다.

**관측 — C2와 나란히**

| 대기 시간 | Triton 평균 배치 | Ray Serve 평균 배치 | Triton 처리량 | Ray Serve 처리량 |
|---|---|---|---|---|
| (배칭 끔) | 1.00 | 1.00 | | |
| 0 | | | | |
| 1ms | | | | |
| 5ms | | | | |
| 20ms | | | | |

### C3-5. 배포 계층 관찰 (도전과제 본래 목적)

```bash
kubectl -n llm-serving-lab port-forward svc/vllm-service-serve 8265:8265 &   # Ray Dashboard
kubectl get raycluster -n llm-serving-lab
kubectl -n llm-serving-lab describe rayservice vllm-service | tail -30
```

- **zero-downtime 업그레이드** — `serveConfigV2`를 바꾸면 새 RayCluster를 띄우고 전환. `max_num_seqs`를 16→64로 바꿔 롤아웃을 관찰하면 B1의 `kubectl set env` 재배포(파드가 죽었다 뜨는)와 대비됩니다 ★
- Ray Dashboard의 Serve 탭에서 **replica 수·큐 길이·실패율**
- `kubectl get raycluster`로 헤드/워커 파드 구조

### 판단 기준

- ✅ **가설 1·2**: 차이가 있되 동시성에 거의 무관하면 고정 오버헤드입니다. **동시성에 비례해 커지면** Ray Serve 프록시가 병목이고, 그건 "계층을 얹으면 언제 손해인가"의 답입니다.
- ✅ **가설 3**: `@serve.batch` 곡선이 C2 Triton 곡선과 같은 모양이면 — **dynamic batching은 프레임워크의 기능이 아니라 워크로드의 성질**이라는 뜻입니다. 이 글 전체의 결론을 한 번 더 지지합니다.
- ⚠️ **오버헤드가 음수(Ray Serve가 더 빠름)** 라면 통제 변수를 의심하세요. `ManifestTest`가 지키는 네 값 외에 다른 게 달라진 것입니다 (예: 이미지 버전에 따른 vLLM 버전 차이). 그 경우 **vLLM 버전을 반드시 기록**하세요.

### 정리

```bash
kubectl delete -f labs/rayserve-on-k8s/rayservice-qwen.yaml
helm uninstall kuberay-operator -n kuberay
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=1
```

---

---

## 종합 — 배칭 4종을 한 표에

네 실험이 끝나면 예습 노트 §1의 표가 실측으로 채워집니다. **이게 글의 결론 절입니다.**

| 방식 | 어디서 쟀나 | 대기 전략 | 처리량 | 지연 | 언제 쓰나 |
|---|---|---|---|---|---|
| 배칭 없음 | C1 `/basic_generate` | — | | | 디버깅·초저지연 단일 요청 |
| static | C1 `/generate` | 배치가 **찰 때까지** | | | 오프라인 배치 작업 |
| dynamic | C2 Triton | **시간 상한까지** | | | **요청당 연산량이 균일한 모델** (CV·임베딩) |
| continuous | B1·B2 vLLM, C1 `/generate_stream` | 기다리지 않음, **슬롯 단위로 교체** | | | **출력 길이가 제각각인 LLM** |

마지막 열의 대비가 이 글이 답하려던 것입니다. dynamic은 **"요청들이 같은 시간 걸린다"를 전제로** 배치를 통째로 묶었다 통째로 내보냅니다. mobilenet에서는 성립합니다(C2). LLM에서는 배치가 가장 긴 요청에 인질로 잡히고, 그 대가가 C1에서 본 패딩 낭비입니다. **continuous batching은 그 전제를 버려서 문제를 푼 것**입니다.

---

---

## 이 환경에서 못 하는 것 (글의 "한계" 절)

정직하게 적어두면 6·7주차로 이어지는 다리가 됩니다.

| 못 하는 것 | 이유 | 어디서 다루나 |
|---|---|---|
| 오토스케일링, 멀티 레플리카, concurrency target | GPU 1장 | 6주차 EKS |
| 라우팅·로드밸런싱, KV cache-aware routing | 레플리카가 없음 | 7주차 llm-d |
| Prefill/Decode disaggregation | 노드·GPU 부족 | 7주차 llm-d |
| Tensor Core 활용률 | WSL2에 `DCGM_FI_PROF_*` 미노출 | (이 환경의 구조적 한계) |
| 콜드 스타트 중 GPU 확보 시간 | 로컬 GPU는 항상 붙어 있음 | 6주차 |

### 이 글이 다루지 않는 CH3·CH4 ★ 범위를 명시할 것

교재 CH3·CH4는 이 글보다 넓습니다. 제목이 약속하는 범위와 내용이 어긋나지 않도록 적어둡니다.

| 주제 | 교재 위치 | 이 글에서 |
|---|---|---|
| **멀티모델 서빙** (LRU 모델 캐시, on-demand 로딩, 스와핑 지연) | CH3 후반 · `ch03/multi_model_serving` | C2 보너스에서 맛만 봄 — 본격적으로는 다루지 않음 |
| **에이전틱 시스템, RAG, CAG** | CH4 전반 · `ch04/KnowledgeAgent` | 다루지 않음 — 별도 편에서 로컬 vLLM 백엔드로 재구성 예정 |
| **클라우드 벤더 / build-or-buy** | CH4 후반 · `ch04/{bedrock,jumpstart,dlc}` | 다루지 않음 — 계정·비용 발생, 6주차와 중복 |

> **Triton은 C2, 엔터프라이즈 오픈소스 스택은 C3에서 다룹니다.** 단, 이 글이 쓰는 것은 Triton의 **dynamic batching과 explicit 모델 관리**, Ray Serve의 **`@serve.batch`와 RayService 배포**뿐입니다. Triton의 앙상블·BLS, Ray의 Core/Data/Train 계층은 건드리지 않습니다.

---
