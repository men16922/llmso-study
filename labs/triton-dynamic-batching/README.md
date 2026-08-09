# C2 랩 — Triton dynamic batching

배칭 4종 중 **dynamic**만 vLLM으로는 잴 수 없다. vLLM에 그 모드가 없기 때문이다.
이 랩은 NVIDIA Triton의 `dynamic_batching`으로 그 한 칸을 채운다.

실습 시나리오는 [`articles/2주차-03 dynamic batching과 그 위의 계층.md`](../../articles/2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)의 **C2** 절이다. 시리즈 목차는 [허브](../../articles/vLLM%20%EB%B0%B0%EC%B9%AD%C2%B7%ED%81%90%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH3%C2%B7CH4%29.md).

## 무엇을 재는가

| 축 | 값 |
|---|---|
| 바꾸는 것 | `max_queue_delay_microseconds` — off / 0 / 1ms / 5ms / 20ms |
| 재는 것 | **평균 배치 크기**, 처리량(inf/s), p50·p95 지연, 요청당 큐 대기 |
| 고정 | 모델(mobilenet_v2), 입력 크기, `max_batch_size: 8` |

핵심 지표는 **평균 배치 크기**다.

```
평균 배치 크기 = nv_inference_request_success / nv_inference_exec_count
                (처리한 요청 수)             ÷ (모델을 실행한 횟수)
```

배칭이 꺼져 있으면 정확히 `1.00`이고, 5ms를 기다려 6개씩 묶였다면 `6.00` 근처가 된다.
"동작하는 것 같다"가 아니라 숫자로 증명되는 지점이다.

## 파일

| 파일 | 역할 | 오프라인 테스트 |
|---|---|---|
| `export_mobilenet_onnx.py` | 배치 축이 **열린** ONNX를 만든다 ★ 전제 조건 | — (torch 필요) |
| `make_config.py` | `config.pbtxt` 생성 (대조군 포함) | ✅ |
| `triton_load.py` | 동시 요청 부하 + 지연 백분위 | ✅ (순수 로직) |
| `triton_metrics.py` | 서버 카운터 차분 → 평균 배치 크기 | ✅ |
| `sweep.sh` | 위 넷을 delay별로 엮는 스윕 | — |
| `test_triton_lab.py` | 위 로직의 단위 테스트 (19건, 오프라인) | ✅ |

`make check`가 `test_triton_lab.py`를 돌린다. tritonclient·torch 없이 통과한다.

## 왜 `densenet_onnx`를 안 쓰는가 ★

교재 저장소에 이미 들어 있는 `densenet_onnx`로는 **dynamic batching을 켤 수 없다.**

```protobuf
max_batch_size : 0                       # 배칭 자체가 꺼짐
dims: [ 3, 224, 224 ]
reshape { shape: [ 1, 3, 224, 224 ] }    # 배치 차원 1을 억지로 끼워 넣는 중
```

그 ONNX는 배치 축이 1로 고정이라 `max_batch_size`를 켜면 모델이 거부한다.
`reshape`가 그 우회 흔적이다. 그래서 `dynamic_axes`로 배치 축을 연 mobilenet_v2를
새로 만든다.

> **서빙 계층만 봐서는 안 보이는 제약이다.** 배칭을 지원하려면 모델이 먼저 배치를
> 받아들여야 한다. 이 한 줄이 실험 전체를 가능하게 한다.

## 대조군을 만드는 법 ★ 틀리기 쉬운 곳

`max_batch_size: 0`으로 두면 안 된다. Triton이 입력 텐서 모양을 다르게 해석해
**모델 시그니처까지 달라지고**, 그러면 비교가 깨진다.

`dynamic_batching` **블록만 빼야** 모델은 그대로 두고 배칭만 끈 올바른 대조군이 된다.
`make_config.py off`가 그것이고, `test_control_group_keeps_the_same_model_signature`가
`off` 출력이 `5000` 출력의 접두사임을 검증한다.

## 실행

```bash
# 0) GPU 확보 — k3s vLLM과 교재 C1 서버를 내린다
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0

# 1) 배치 축이 열린 모델 만들기
cd ~/llm-model-inference/ch03/multi_model_serving
python3 ~/study/labs/triton-dynamic-batching/export_mobilenet_onnx.py \
  --out model_dir/mobilenet_v2/1/model.onnx --verify

# 2) Triton 기동 (explicit 모드 — 재시작 없이 config 재적용)
python3 ~/study/labs/triton-dynamic-batching/make_config.py 5000 \
  > model_dir/mobilenet_v2/config.pbtxt
docker run -d --name triton --gpus all \
  -p8009:8000 -p8010:8001 -p8011:8002 \
  -v $(pwd)/model_dir:/models \
  nvcr.io/nvidia/tritonserver:24.12-py3 \
  tritonserver --model-repository=/models --model-control-mode=explicit

# 3) 스윕
bash ~/study/labs/triton-dynamic-batching/sweep.sh
```

`sweep.sh`는 delay마다 ① config 생성 ② unload/load ③ **서버에 적용된 값 되읽기**
④ 부하 ⑤ 카운터 차분을 돈다. ③이 있어서 "파일은 고쳤는데 반영이 안 된" 경우를 잡는다.

## 결과 읽는 법

- ✅ delay ↑ → 평균 배치 크기 ↑, 처리량 ↑, p95 ↑ (기다림을 팔아 처리량을 산다)
- ✅ **동시성 1에서는 평균 배치 크기가 1.00에 머물고 p95만 delay만큼 늘어난다** —
  기다렸는데 아무도 안 온 것. 이게 "dynamic은 언제 쓰나"의 답이다.
- 💡 `delay=0`인데 배치 크기가 1보다 크면, 기다리지 않아도 **이미 큐에 쌓여 있던 것**만으로
  묶인 것이다. delay는 부하가 낮을 때를 위한 장치라는 뜻.
- ⚠️ 계속 1.00이면 config 미반영. `curl localhost:8009/v2/models/mobilenet_v2/config` 확인.

## 정리

```bash
docker rm -f triton
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=1
```
