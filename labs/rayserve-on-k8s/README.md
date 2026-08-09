# C3 랩 — Ray Serve on K8s (KubeRay)

CH4 도전과제(`로컬 PC에 kind(k8s)로 RayService 배포`)를 **배칭 축에 붙여서** 수행한다.
kind 대신 이미 있는 K3s를 쓴다.

실습 시나리오는 [`articles/2주차-03 dynamic batching과 그 위의 계층.md`](../../articles/2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)의 **C3** 절이다. 시리즈 목차는 [허브](../../articles/vLLM%20%EB%B0%B0%EC%B9%AD%C2%B7%ED%81%90%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH3%C2%B7CH4%29.md).

## 왜 따라하기가 아닌가 — 접점 두 개

도전과제를 그냥 수행하면 "배포해봤다"로 끝난다. 이 랩은 앞선 실험과 **직접 비교되는 두 축**으로 붙인다.

| 접점 | 비교 대상 | 답하는 질문 |
|---|---|---|
| **① 계층 오버헤드** | B1(직접 vLLM) ↔ C3(Ray Serve로 감싼 vLLM) | 오케스트레이션 계층은 얼마를 먹는가 |
| **② 같은 개념, 다른 노출** | C2(Triton `dynamic_batching`) ↔ C3(`@serve.batch`) | dynamic batching은 프레임워크가 정하는가, 워크로드가 정하는가 |

②의 대응 관계가 이 랩의 핵심 근거다.

| Triton | Ray Serve |
|---|---|
| `max_batch_size: 8` | `@serve.batch(max_batch_size=8)` |
| `max_queue_delay_microseconds: 5000` | `@serve.batch(batch_wait_timeout_s=0.005)` |
| `dynamic_batching` 블록 없음 (대조군) | `@serve.batch` 데코레이터 없음 (대조군) |

**같은 모델(mobilenet_v2), 같은 두 노브, 다른 프레임워크.** C2에서 그린 곡선을 여기서 다시 그린다.

## ①이 성립하려면 — 통제 변수

공식 가이드는 `Qwen2.5-7B-Instruct-AWQ`를 쓰지만, **B1과 다른 모델을 쓰면 오버헤드를 분리할 수 없다.**
그래서 `rayservice-qwen.yaml`은 B1의 `vllm-baseline.yaml`과 값을 맞춰 두었다.

| 항목 | 값 | 왜 |
|---|---|---|
| 모델 | `Qwen/Qwen2.5-1.5B-Instruct` | B1과 동일 |
| `max_model_len` | 4096 | B1과 동일 |
| `gpu_memory_utilization` | 0.85 | B1과 동일 |
| `max_num_seqs` | 16 | B1과 동일 |

`test_rayserve_lab.py`의 `ManifestTest`가 이 네 값이 어긋나지 않았는지 지킨다. 하나라도 바뀌면 테스트가 깨진다.

공식 예제 대비 조정한 나머지: GPU 4→1, `max_replicas` 4→1, 헤드는 GPU를 잡지 않음(`num-gpus: "0"`),
워커에 `runtimeClassName: nvidia`(WSL2 K3s 필수), 메모리를 WSL2 할당(23Gi)에 맞춰 축소.

## 파일

| 파일 | 역할 | 오프라인 테스트 |
|---|---|---|
| `rayservice-qwen.yaml` | RayService 매니페스트 — B1과 동일 조건 | ✅ (`ManifestTest`) |
| `mobilenet_serve.py` | `@serve.batch`로 mobilenet 서빙, env로 스윕 | ✅ (`BatchSettingsTest`) |
| `test_rayserve_lab.py` | 위 둘의 단위 테스트 (10건) | ✅ |

`make check`가 이 테스트를 돌린다. ray·torch 없이 통과한다 (`ManifestTest`는 `pyyaml`이 있으면 실행, 없으면 skip).

## 실행

### C3-1. KubeRay operator

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/ && helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.4.2 -n kuberay --create-namespace
kubectl -n kuberay get pod
```

### C3-2. RayService 배포 — GPU 확보 후

```bash
# ★ B1의 vllm-baseline과 GPU를 동시에 쓸 수 없다
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0

kubectl apply -f rayservice-qwen.yaml
kubectl -n llm-serving-lab get rayservice vllm-service -w   # READY까지 5~15분(모델 로딩)
```

### C3-3. 접점 ① — 계층 오버헤드 측정

**B1과 똑같은 명령**을 Ray Serve 엔드포인트에 던진다. OpenAI 호환이라 `--api openai` 그대로다.

```bash
kubectl -n llm-serving-lab port-forward --address 0.0.0.0 svc/vllm-service-serve 8000:8000 &

cd ../wsl2-vllm-baseline
python3 benchmark.py --scenarios short --concurrency 1,2,4,8,16,32,64 \
  --requests-per-level 100 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 \
  --output results/c3-rayserve-short.json
```

B1의 `slots=16` 결과와 나란히 놓는다.

```bash
python3 summarize_results.py \
  results/b1-slots-16-short.json results/c3-rayserve-short.json \
  --label-regex '(b1-slots-16|c3-rayserve)' --delta --metric output_tok_per_s
python3 summarize_results.py \
  results/b1-slots-16-short.json results/c3-rayserve-short.json \
  --label-regex '(b1-slots-16|c3-rayserve)' --delta --metric ttft_p95_s
```

`--delta`가 `차이`·`차이 %` 열을 붙인다. **그 차이가 오케스트레이션 계층의 가격**이다.

### C3-4. 접점 ② — `@serve.batch` 스윕

C2와 같은 지점(off/0/1ms/5ms/20ms)을 돈다.

```bash
for WAIT in off 0 0.001 0.005 0.02; do
  MAX_BATCH_SIZE=8 BATCH_WAIT_S=$WAIT serve run mobilenet_serve:app &
  sleep 20
  # 부하 → /stats에서 avg_batch_size 확인 (Triton의 exec_count 대신 직접 센다)
  curl -s localhost:8000/stats | python3 -m json.tool
  serve shutdown -y
done
```

`/stats`가 `avg_batch_size = requests_seen / batches_run`을 돌려준다 — **C2의
`nv_inference_request_success / nv_inference_exec_count`와 같은 정의**다.

### C3-5. 배포 계층 관찰 (도전과제 본래 목적)

```bash
kubectl -n llm-serving-lab port-forward svc/vllm-service-serve 8265:8265 &   # Ray Dashboard
kubectl -n llm-serving-lab describe rayservice vllm-service | tail -30
```

- RayService의 **zero-downtime 업그레이드** — serveConfigV2를 바꾸면 새 RayCluster를 띄우고 전환
- Ray Dashboard의 Serve 탭에서 **replica 수·큐 길이·실패율**
- `kubectl get raycluster`로 헤드/워커 파드 구조

## 정리

```bash
kubectl delete -f rayservice-qwen.yaml
helm uninstall kuberay-operator -n kuberay
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=1
```

## 예상되는 함정

| 증상 | 원인 | 대응 |
|---|---|---|
| 워커 파드 `Pending` | GPU를 `vllm-baseline`이 점유 | `scale deploy/vllm-baseline --replicas=0` |
| 워커가 GPU를 못 봄 | `runtimeClassName: nvidia` 누락 | 매니페스트에 이미 있음 — 다른 매니페스트를 쓴 건 아닌지 확인 |
| 헤드가 GPU를 잡아 워커가 못 뜸 | `num-gpus`가 헤드에도 잡힘 | 매니페스트는 헤드를 `"0"`으로 둔다 |
| OOM / 파드 Evicted | WSL2 23Gi에 head+worker가 안 맞음 | `requests` 합이 20Gi 이하인지 (`test_worker_memory_fits_wsl2_allocation`) |
| RayService가 계속 `Initializing` | 모델 다운로드 중 | `kubectl logs`로 진행 확인. PVC 캐시를 쓰면 빨라진다 |
