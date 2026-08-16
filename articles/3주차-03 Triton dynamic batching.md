# 3주차-03 Triton dynamic batching — C2

> **시리즈** — [허브](./KV%20cache%EC%99%80%20%EC%84%9C%EB%B9%99%20%EA%B3%84%EC%B8%B5%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH5%C2%B7CH6%29.md) · [00 준비·측정 규칙](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) · [01 Ray Serve 계층](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) · [02 KV cache 상한](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) · [03 Triton](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)

> **이 편이 답하는 것**: **dynamic batching은 언제 쓰나?** 그리고 왜 LLM에는 안 맞나.

1주차 예습 노트의 질문입니다: *"continuous batching이 static보다 항상 낫다면, **dynamic batching은 언제 쓰나?** (힌트: **LLM이 아닌 모델**)"*

**교재 CH6 「Dynamic Batching in Online Inference」 절의 실측판**입니다. 교재는 dynamic batching을 **max batch size + max delay time** 두 파라미터로 정의하고, 이렇게 결론냅니다:

> **하지만 LLM에서는 이것만으로도 부족합니다!** … LLM은 request마다 output 길이가 달라 batch 내부의 sequence가 서로 다른 시점에 끝난다.

**★ vLLM에는 dynamic batching 모드가 없습니다.** 그래서 이 절은 vLLM으로 실측할 수 없고, **Triton이 그 두 노브를 실제로 가진 도구**입니다. 여기가 이 실습의 존재 이유입니다.

원설계는 [`2주차-03`의 C2 절](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)에 있습니다.

---

## ⚠️ 교재의 Triton과 이 실습의 Triton은 다른 이야기입니다

**글에 반드시 명시할 구분**입니다.

| | 교재 CH3의 Triton | 이 실습의 Triton |
|---|---|---|
| 무엇을 보여주나 | **멀티모델 서빙 백엔드 위임** — `TritonWorker`가 HTTP로 load/infer/unload를 Triton에 넘김 | **dynamic batching** 두 노브의 효과 |
| 대응 챕터 | CH3 (시스템 설계) | **CH6** (최적화 — 배칭 전략) |
| 모델 | `densenet_onnx` | `mobilenet_v2` (배치 축을 열어 재-export) |

즉 **배칭 축은 이 시리즈가 CH6에 붙여 확장한 것**입니다. 이 구분을 적어야 "교재 요약"이 아니라 "교재 위에 얹은 실험"이 됩니다.

## 가설

1. `max_queue_delay`를 키우면 **평균 배치 크기와 처리량이 오르고, p95 지연이 나빠진다.** 기다림을 팔아 처리량을 사는 것.
2. **동시성이 낮으면 delay는 순손실이다.** 기다려도 묶을 요청이 없으니 지연만 늘어난다 → dynamic의 효과는 **도착률에 의존**한다. ★ 질문의 답이 여기
3. **이 방식이 LLM에 안 맞는 이유**는 배치를 통째로 묶어 통째로 내보내기 때문이다. mobilenet은 모든 요청의 연산량이 정확히 같아 성립하지만, LLM은 출력 길이가 제각각이라 배치가 **가장 긴 요청에 인질로 잡힌다.**

---

## C2-0. 준비 — GPU 확보 ★

[01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md)·[02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)를 **완전히 끝내고** 내린 뒤에 시작합니다.

```bash
kubectl delete -f /tmp/rayservice-sweep.yaml 2>/dev/null
kubectl delete -f labs/rayserve-on-k8s/rayservice-qwen.yaml 2>/dev/null
helm uninstall kuberay-operator -n kuberay 2>/dev/null
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0

kubectl -n llm-serving-lab get pod       # 전부 사라졌는지
nvidia-smi                                # ★ VRAM 반환 확인 — 02에서 배운 것

cd ~/llm-model-inference/ch03/multi_model_serving
docker images | grep tritonserver         # 00의 0-3에서 풀어둔 이미지
```

## C2-1. 배치 축이 열린 모델 만들기 ★ 이게 진짜 장벽입니다

저장소(그리고 교재 CH3 실습)에 들어 있는 `densenet_onnx`로는 **dynamic batching을 켤 수 없습니다.** `config.pbtxt`를 보면 이유가 나옵니다.

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

> **이 한 줄이 실험 전체를 가능하게 합니다. 글에 꼭 남기세요** — *"배칭을 지원하려면 모델이 먼저 배치를 받아들여야 한다"* 는, 서빙 계층만 봐서는 안 보이는 제약입니다. 교재 실습을 그대로 따라갔다면 여기서 막혔을 것이고, **막히는 지점 자체가 배울 거리**입니다. `--verify`가 export 결과의 첫 차원이 실제로 심볼(dynamic)인지 확인해 줍니다.

## C2-2. config 생성기 — `make_config.py`

`max_batch_size > 0`이면 `dims`에서 **배치 차원을 빼고** 씁니다(Triton이 앞에 붙임).

```bash
python3 "$LAB/make_config.py" off  > model_dir/mobilenet_v2/config.pbtxt   # 대조군
python3 "$LAB/make_config.py" 5000 > model_dir/mobilenet_v2/config.pbtxt   # 5ms 대기
```

> ⚠️ **대조군은 `max_batch_size: 0`이 아니라 `off`입니다.** `0`으로 두면 Triton이 입력 텐서 모양을 다르게 해석해 **모델 시그니처까지 달라지고**, 비교가 깨집니다. `dynamic_batching` **블록만 빼야** 모델은 그대로 두고 배칭만 끈 올바른 대조군이 됩니다. `test_control_group_keeps_the_same_model_signature`가 `off` 출력이 `5000` 출력의 접두사임을 검증합니다.

## C2-3. Triton 기동

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

> 포트 매핑(8009/8010/8011)은 교재 CH3 실습 기록과 같습니다. Triton 컨테이너 내부는 HTTP 8000 / gRPC 8001 / Metrics 8002입니다.

## C2-4. 평균 배치 크기 재기 ★ 이 실험의 핵심 지표

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

> ⚠️ **반드시 차분해야 합니다.** Triton 카운터는 서버 기동 이후 누적이라 그냥 나누면 이전 실험까지 섞입니다. `queue_duration`이 요청당 몇 ms인지가 `max_queue_delay`가 실제로 얼마나 쓰였는지를 알려줍니다.

## C2-5. 스윕 — `sweep.sh`

```bash
cd ~/llm-model-inference/ch03/multi_model_serving
bash "$LAB/sweep.sh"            # 기본: off 0 1000 5000 20000
```

delay마다 ① config 생성 ② unload/load ③ **서버에 적용된 값 되읽기** ④ 부하 ⑤ 카운터 차분을 돕니다. 결과는 `results/c2-delay-*.json`과 `results/c2-batch-stats.txt`에 쌓입니다.

> unload/load로 config가 반영되지 않으면 컨테이너를 재시작하세요(`docker restart triton`). 매번 20~30초가 더 듭니다.

---

## 관측 — 채울 표

### ① delay 축 (동시성 8 고정)

| `max_queue_delay` | 평균 배치 크기 | 처리량 (inf/s) | p50 (ms) | p95 (ms) | 큐 대기 (ms/req) |
|---|---|---|---|---|---|
| (dynamic 끔) | 1.00 | | | | |
| 0 μs | | | | | |
| 1,000 μs (1ms) | | | | | |
| 5,000 μs (5ms) | | | | | |
| 20,000 μs (20ms) *(잘라내기 4순위)* | | | | | |

### ② 도착률 의존성 ★ 질문의 답이 여기 있습니다

같은 delay(5ms)를 **동시성만 바꿔가며**:

| 동시성 | 평균 배치 크기 | 처리량 (inf/s) | p95 (ms) | dynamic 끔 대비 p95 |
|---|---|---|---|---|
| 1 | | | | |
| 8 | | | | |
| 32 | | | | |

---

## 판단 기준

- ✅ **가설 1**: delay ↑ → 평균 배치 크기 ↑, 처리량 ↑, p95 ↑. **세 값이 같이 움직여야** 합니다
- ✅ **가설 2 ★ 이게 질문의 답입니다**: **동시성 1에서는 평균 배치 크기가 1.00에 머물고 p95만 delay만큼 늘어납니다.** 기다렸는데 아무도 안 온 것 — 순손실입니다. 그래서 dynamic batching의 delay는 **예상 도착률에 맞춰 정해야** 하고, 트래픽이 들쭉날쭉하면 그 자체가 약점이 됩니다
- 💡 **`delay=0`인데 평균 배치 크기가 1보다 크면**: 기다리지 않아도 **이미 큐에 쌓여 있던 것**만으로 묶인 것입니다. 부하가 충분히 높으면 delay 없이도 dynamic이 동작한다는 뜻이고, 뒤집으면 delay는 **부하가 낮을 때를 위한 장치**입니다
- ⚠️ **평균 배치 크기가 계속 1.00이면**: config가 반영되지 않았습니다. `curl localhost:8009/v2/models/mobilenet_v2/config`로 실제 값을 확인하세요
- ⚠️ **`load`가 실패하면**: `dims`에 배치 차원을 넣었거나(빼야 함) ONNX의 배치 축이 안 열린 것입니다. `docker logs triton`에 이유가 나옵니다

## 보너스 — 모델 스와핑 *(여유가 있으면)*

`manager.py:11`의 `max_models: int = 2`가 LRU 캐시 상한입니다. Triton의 explicit 모드 load/unload와 붙여 **모델 3개를 번갈아 요청하면 매번 스와핑이 일어나는** 상황을 만들 수 있습니다. 스와핑 지연을 재면 *"GPU에 안 올라간 모델은 첫 요청이 비싸다"* 가 숫자로 나옵니다 — **5주차 multi-LoRA의 복선**입니다.

이건 교재 CH3의 원래 Triton 주제(멀티모델 백엔드 위임)와 맞닿는 부분이기도 합니다.

---

## 종합 — 배칭 4종을 한 표에

이 편이 끝나면 예습 노트 §1의 표에서 **dynamic 칸**이 채워집니다.

| 방식 | 어디서 쟀나 | 대기 전략 | 처리량 | 지연 | 언제 쓰나 |
|---|---|---|---|---|---|
| 배칭 없음 | *(C1 미수행)* | — | — | — | 디버깅·초저지연 단일 요청 |
| static | *(C1 미수행)* | 배치가 **찰 때까지** | — | — | 오프라인 배치 작업 |
| **dynamic** | **C2 Triton** | **시간 상한까지** | | | **요청당 연산량이 균일한 모델** (CV·임베딩) |
| **continuous** | B1·B2 vLLM (2주차) | 기다리지 않음, **슬롯 단위로 교체** | 2,627 tok/s | | **출력 길이가 제각각인 LLM** |

> ⚠️ **없음·static 칸은 빈칸으로 두고 글에 범위를 명시하세요.** C1(교재 서버)은 미수행입니다. 채운 척하지 않는 것이 중요합니다.

마지막 열의 대비가 이 시리즈가 답하려던 것입니다. **dynamic은 "요청들이 같은 시간 걸린다"를 전제로** 배치를 통째로 묶었다 통째로 내보냅니다. mobilenet에서는 성립합니다(이 편). LLM에서는 배치가 가장 긴 요청에 인질로 잡힙니다. **continuous batching은 그 전제를 버려서 문제를 푼 것**이고, 2주차의 23배가 그 대가로 얻은 것입니다.

## 정리

```bash
docker rm -f triton
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=1   # k3s 기준선 복구
```

## 기록 체크리스트

- [ ] `export_mobilenet_onnx.py --verify` 출력 (배치 축이 심볼인지)
- [ ] 적용된 `config.pbtxt` (off / 5000 각각)
- [ ] `results/c2-delay-*.json` × 5
- [ ] `results/c2-batch-stats.txt` (평균 배치 크기 · 큐 대기)
- [ ] 도착률 의존성 표 (동시성 1/8/32)
- [ ] Triton 이미지 실제 크기 (00의 0-3 확인 항목)
