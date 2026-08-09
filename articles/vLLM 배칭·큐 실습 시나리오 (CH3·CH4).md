# 배치 슬롯을 넘어서면 무슨 일이 일어나는가 — WSL2 로컬 K8s에서 vLLM 배칭·큐 실습

> **이 문서는 실습 시나리오입니다.** 순서대로 실행하고 표의 빈칸을 채우면, 그대로 2주차 과제 글의 뼈대가 됩니다.
> 측정이 끝난 뒤 "관측" 절의 빈칸을 채우고 "해석"을 쓰면 완성입니다.

---

## 이 실습이 답하려는 질문

교재 CH3·CH4의 핵심 주장을 **내 GPU에서 재현**하는 것이 목적입니다.

| # | 질문 | 교재 |
|---|---|---|
| B1 | 동시 요청을 계속 늘리면 처리량은 계속 오르는가? **어디서 멈추는가?** | CH3 배칭 |
| B2 | 그 순간 서버 안에서는 무슨 일이 일어나는가? | CH3 큐·동시성 |
| B3 | 동시에 처리 가능한 요청 수의 **상한은 무엇이 정하는가?** | 1주차 숙제 · CH3 |
| B4 | 서버가 재는 지연과 사용자가 겪는 지연은 얼마나 다른가? | CH4 추론시간 vs 종단간 |
| B5 | 내 기존 측정은 왜 전 구간 goodput 100%였는가? | CH4 벤치마킹 팁 |

**선행 관측이 하나 있습니다.** 1주차 Cloud Run 실습(`google/gemma-4-31B-it`, `MAX_NUM_SEQS=8`)에서 이런 결과가 나왔습니다.

| 동시성 | TTFT p50 | 처리량 | goodput |
|---|---|---|---|
| 8 | 0.475s | 289.5 tok/s | 100% |
| 16 | 3.688s | 294.6 tok/s | 50% |

동시성 2배에 **처리량 +1.8%, TTFT 7.8배**. 꺾인 지점이 `max_num_seqs`의 정확히 2배였습니다. 이번 실습의 가설은 **"이 현상이 하드웨어와 모델을 바꿔도 슬롯 수를 따라 재현된다"** 입니다.

---

## 사전 조건

| 항목 | 값 |
|---|---|
| 호스트 | Windows 11 + WSL2 (Ubuntu), RTX 4080 Laptop 12GB |
| 클러스터 | K3s, namespace `llm-serving-lab` |
| 서빙 | `vllm/vllm-openai:v0.23.0`, Deployment `vllm-baseline` |
| 모델 | `Qwen/Qwen2.5-1.5B-Instruct` (`qwen2.5-1.5b`) — PVC에 캐시됨 |
| 관측 | kube-prometheus-stack + DCGM Exporter, ServiceMonitor `vllm-baseline` (15s) |
| 벤치마크 | `labs/wsl2-vllm-baseline/benchmark.py` |

**총 소요 1.5~2시간** (B1 30분 · B2 15분 · B3 20분 · B4 10분 · B5 20분 + 준비/정리)

---

## 0. 준비

### 0-1. WSL 세션 붙잡기 ★ 안 하면 실습 중 파드가 죽습니다

WSL이 유휴 상태에서 systemd에 poweroff를 요청해 k3s가 내려갑니다. **별도 창을 하나 열어 그대로 둡니다.**

```powershell
# Windows PowerShell — 실습 내내 이 창을 닫지 않는다
wsl -d Ubuntu -u root -- sleep infinity
```

### 0-2. 상태 확인

```bash
kubectl -n llm-serving-lab get pod,svc
kubectl -n llm-serving-lab logs deploy/vllm-baseline --tail=5
kubectl get servicemonitor -n monitoring vllm-baseline
```

포트포워딩 3개를 각각 백그라운드로 띄웁니다. (NodePort는 Windows에서 안 열립니다 — 실제 리스닝 소켓이 필요합니다)

```bash
kubectl -n llm-serving-lab port-forward --address 0.0.0.0 svc/vllm-baseline 8000:8000 &
kubectl -n monitoring port-forward --address 0.0.0.0 svc/kube-prometheus-stack-prometheus 30001:9090 &
kubectl -n monitoring port-forward --address 0.0.0.0 svc/kube-prometheus-stack-grafana 30002:80 &
```

### 0-3. 메트릭 이름 확인 ★ 버전마다 다릅니다

**추측하지 말고 실제로 뽑아보세요.** 아래 이름들이 이 시나리오 전체의 전제입니다.

```bash
curl -s localhost:8000/metrics | grep -oE '^vllm:[a-z_]+' | sort -u
```

기대하는 이름과 쓰임:

| 메트릭 | 쓰는 곳 |
|---|---|
| `vllm:num_requests_running` | B2 — 배치에 들어간 요청 수 |
| `vllm:num_requests_waiting` | B2 — 큐 대기 |
| `vllm:gpu_cache_usage_perc` | B3 — KV cache 사용률 |
| `vllm:e2e_request_latency_seconds_bucket` | B4 — 서버 측 종단간 |
| `vllm:time_to_first_token_seconds_bucket` | B4 — 서버 측 TTFT |
| `vllm:time_per_output_token_seconds_bucket` | (보너스) ITL |
| `vllm:prefix_cache_queries_total` / `_hits_total` | B5 — prefix cache 적중률 |

> **이름이 다르면 그 자체가 기록거리입니다.** v0.23.0 기준 실제 목록을 글에 남기면 재현하는 사람에게 도움이 됩니다. 없는 메트릭이 있으면 해당 실험을 조정하고 "이 버전에는 없었다"고 적습니다.

### 0-4. 매니페스트 적용

`k8s/vllm-baseline.yaml`은 **이미 파라미터화되어 있습니다.** 세 값이 env로 빠져 있어 `kubectl set env`만으로 롤아웃할 수 있습니다.

```yaml
              --max-model-len "$MAX_MODEL_LEN"
              --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
              --max-num-seqs "$MAX_NUM_SEQS"
```

| 변수 | 기본값 | 쓰는 실험 |
|---|---|---|
| `MAX_NUM_SEQS` | 16 | B1 · B2 · B3 |
| `MAX_MODEL_LEN` | 4096 | B3 |
| `GPU_MEMORY_UTILIZATION` | 0.85 | B3 (보너스) |

`strategy: Recreate`라 이전 파드가 먼저 내려가므로 GPU 경합이 없습니다.

```bash
kubectl apply -f labs/wsl2-vllm-baseline/k8s/vllm-baseline.yaml
kubectl -n llm-serving-lab rollout status deploy/vllm-baseline --timeout=10m
```

### 0-5. 스모크 테스트

```bash
cd labs/wsl2-vllm-baseline
python3 benchmark.py --concurrency 1,4 --requests-per-level 2 --output results/smoke.json
```

성공하면 다음으로 갑니다.

---

## B1. 배치 슬롯과 붕괴점 ★ 이 실습의 본체

### 목적

처리량이 포화하는 지점과 TTFT가 무너지는 지점이 **`max-num-seqs`에 의해 결정되는지** 확인합니다.

### 가설

1. 처리량은 동시성이 `max-num-seqs`에 도달할 때까지 거의 선형으로 오르고, **그 이후로는 평평해진다.**
2. 슬롯을 넘어선 동시성은 전부 **대기 시간으로만 전환**된다 → TTFT 급증.
3. `max-num-seqs=1`은 사실상 배칭을 끈 상태다 → 처리량이 동시성과 무관하게 낮게 유지된다.

### 실행

슬롯 값 4개에 대해 같은 스윕을 돌립니다.

```bash
cd labs/wsl2-vllm-baseline

for SLOTS in 1 4 16 64; do
  kubectl -n llm-serving-lab set env deploy/vllm-baseline MAX_NUM_SEQS=$SLOTS
  kubectl -n llm-serving-lab rollout status deploy/vllm-baseline --timeout=10m

  # 포트포워딩은 파드가 바뀌면 끊깁니다 — 다시 띄웁니다
  pkill -f "port-forward.*vllm-baseline" ; sleep 2
  kubectl -n llm-serving-lab port-forward svc/vllm-baseline 8000:8000 &
  sleep 5

  python3 benchmark.py \
    --scenarios short \
    --concurrency 1,2,4,8,16,32,64 \
    --requests-per-level 100 \
    --ttft-slo 0.5 --e2e-slo 10 \
    --output results/b1-slots-$SLOTS-short.json
done
```

`decode` 시나리오는 요청당 4~7초라 전 구간을 돌리면 너무 깁니다. **포인트를 줄여** 별도로 한 번 더 돌립니다.

```bash
for SLOTS in 1 16 64; do
  kubectl -n llm-serving-lab set env deploy/vllm-baseline MAX_NUM_SEQS=$SLOTS
  kubectl -n llm-serving-lab rollout status deploy/vllm-baseline --timeout=10m
  pkill -f "port-forward.*vllm-baseline" ; sleep 2
  kubectl -n llm-serving-lab port-forward svc/vllm-baseline 8000:8000 & sleep 5

  python3 benchmark.py --scenarios decode \
    --concurrency 1,8,32 --requests-per-level 30 \
    --ttft-slo 0.5 --e2e-slo 30 \
    --output results/b1-slots-$SLOTS-decode.json
done
```

### 관측 — 채울 표

**`short` 시나리오, 처리량 (tok/s)**

| 동시성 | slots=1 | slots=4 | slots=16 | slots=64 |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 4 | | | | |
| 8 | | | | |
| 16 | | | | |
| 32 | | | | |
| 64 | | | | |

**TTFT p95 (s)** — 같은 형식으로 하나 더

**goodput (%)** — 같은 형식으로 하나 더

### 판단 기준

- ✅ **가설대로면**: `slots=4` 열의 처리량이 동시성 4~8 사이에서 평평해지고, `slots=64` 열은 훨씬 뒤에서 꺾입니다. 꺾이는 위치가 열마다 오른쪽으로 이동해야 합니다.
- ⚠️ **모든 열이 똑같이 나오면**: 슬롯 변경이 실제로 반영되지 않은 것입니다. 파드 로그에서 `max_num_seqs` 값을 확인하세요.
  ```bash
  kubectl -n llm-serving-lab logs deploy/vllm-baseline | grep -i "max_num_seqs\|max num seqs"
  ```
- ⚠️ **`slots=64`가 뜨지 않거나 값이 줄어들면**: KV cache 메모리가 부족해 vLLM이 스스로 낮춘 것입니다. **이건 실패가 아니라 B3의 답입니다** — 로그를 그대로 기록하세요.

---

## B2. 큐가 보이는 그림 ★ 글의 대표 이미지

### 목적

B1에서 숫자로 본 붕괴를 **서버 내부 상태로** 확인합니다. 클라이언트 지연이 왜 늘어나는지가 여기서 드러납니다.

### 실행

슬롯을 16으로 되돌리고, **슬롯을 확실히 넘는 부하**를 길게 겁니다.

```bash
kubectl -n llm-serving-lab set env deploy/vllm-baseline MAX_NUM_SEQS=16
kubectl -n llm-serving-lab rollout status deploy/vllm-baseline --timeout=10m
pkill -f "port-forward.*vllm-baseline" ; sleep 2
kubectl -n llm-serving-lab port-forward svc/vllm-baseline 8000:8000 & sleep 5

# 시작 시각을 적어둔다 (그래프 구간을 찾기 위해)
date -u +"%H:%M:%S UTC"

python3 benchmark.py --scenarios decode \
  --concurrency 4,16,64 --requests-per-level 200 \
  --ttft-slo 0.5 --e2e-slo 30 \
  --output results/b2-queue.json

date -u +"%H:%M:%S UTC"
```

### 관측 — Prometheus에서 세 개를 같은 시간축에

`http://localhost:30001` → Graph 탭에 순서대로 넣습니다.

```promql
# ① 배치에 실제로 들어간 요청 수 — max-num-seqs에서 평평해져야 함
vllm:num_requests_running

# ② 큐에서 기다리는 요청 수 — ①이 천장에 닿는 순간부터 치솟아야 함
vllm:num_requests_waiting

# ③ 서버 측 TTFT p95 — ②가 오르는 시점에 같이 꺾여야 함
histogram_quantile(0.95, sum(rate(vllm:time_to_first_token_seconds_bucket[1m])) by (le))
```

Grafana(`http://localhost:30002`)에 세 개를 한 패널에 겹쳐 놓으면 **CH3의 배칭과 큐가 한 화면에 설명됩니다.** 이 스크린샷이 글의 핵심 그림입니다.

### 기록할 것

| 항목 | 값 |
|---|---|
| `num_requests_running`의 최댓값 (= 실질 슬롯 수) | |
| `num_requests_waiting`이 0을 벗어난 동시성 | |
| 그 시점의 클라이언트 TTFT p95 | |
| 그 시점의 처리량 변화 | |

### 판단 기준

- ✅ `running`이 16에서 평평해지고 `waiting`이 그때부터 쌓이면 성공입니다.
- ⚠️ `waiting`이 계속 0이면 부하가 부족한 것입니다. 동시성이나 요청 수를 늘리세요.
- 💡 `running`의 최댓값이 설정한 16보다 **작으면** KV cache가 먼저 한계입니다 → B3로 이어집니다.

---

## B3. 동시 요청 수의 상한은 무엇이 정하는가

> 1주차 예습 노트에 남겨둔 숙제입니다: *"KV cache는 요청마다 쌓이는데, 동시 요청 수의 상한은 무엇이 정하나?"*

### 목적

슬롯 수(`max-num-seqs`)를 아무리 키워도 **KV cache 메모리가 먼저 상한을 정한다**는 것을 확인합니다.

### 실행

컨텍스트 길이를 4배로 늘려 요청당 KV cache 사용량을 키웁니다.

```bash
kubectl -n llm-serving-lab set env deploy/vllm-baseline MAX_NUM_SEQS=64 MAX_MODEL_LEN=16384
kubectl -n llm-serving-lab rollout status deploy/vllm-baseline --timeout=10m

# 기동 로그에서 vLLM이 계산한 KV cache 블록 수와 실제 동시성 상한을 확인
kubectl -n llm-serving-lab logs deploy/vllm-baseline | grep -iE "kv cache|gpu blocks|maximum concurrency"
```

부하를 걸며 KV cache 사용률을 봅니다.

```promql
vllm:gpu_cache_usage_perc
```

### 관측 — 채울 표

| `max-model-len` | `max-num-seqs` 설정 | 로그가 보고한 실질 동시성 | KV cache 사용률 최대 | 처리량 |
|---|---|---|---|---|
| 4096 | 16 | | | |
| 4096 | 64 | | | |
| 16384 | 64 | | | |

7B-AWQ 모델로 한 줄 더 채우면 **모델 크기가 KV cache 여유를 어떻게 잡아먹는지**까지 보입니다.

### 판단 기준

- ✅ `max-model-len`을 키우면 같은 슬롯 설정에서도 실질 동시성이 줄어야 합니다.
- 💡 vLLM 기동 로그에 `Maximum concurrency for N tokens per request: X.XXx` 같은 줄이 나오면 **그게 정답을 직접 알려주는 것**입니다. 그대로 인용하세요.

---

## B4. 서버가 재는 지연 vs 사용자가 겪는 지연

> CH4: *"추론 시간은 빠른데 종단간이 느리다면, 모델 성능 최적화가 아니라 인프라를 봐야 한다."*

### 목적

같은 요청에 대해 **서버 측 지연과 클라이언트 측 지연의 차이**를 재고, 그 차이가 동시성에 따라 어떻게 벌어지는지 봅니다. 차이의 정체는 큐 대기 + 네트워크(+ port-forward 경유)입니다.

### 실행

B1·B2에서 이미 만든 부하를 재활용합니다. 각 구간의 시각을 알고 있으면 새로 돌릴 필요가 없습니다.

```promql
# 서버 측 종단간 p95
histogram_quantile(0.95, sum(rate(vllm:e2e_request_latency_seconds_bucket[1m])) by (le))
```

이 값을 `benchmark.py` 결과의 `e2e_p95_s`와 비교합니다.

### 관측 — 채울 표

| 동시성 | 서버 측 e2e p95 (Prometheus) | 클라이언트 e2e p95 (benchmark) | 차이 | 차이 비율 |
|---|---|---|---|---|
| 4 | | | | |
| 16 | | | | |
| 64 | | | | |

### 판단 기준

- ✅ 동시성이 오를수록 **차이가 커지면** 큐 대기가 클라이언트 쪽에만 잡힌다는 뜻입니다.
- 💡 차이가 거의 없으면 병목이 서버 안에 있다는 뜻입니다. 그것도 결론입니다.

---

## B5. 내 기존 측정은 왜 전부 goodput 100%였는가

> CH4: *"엉터리 입력에 대고 벤치마크 성능을 극대화하면, 프로덕션 성능은 기대와 달라진다."*

### 목적

기존 기준선 측정(`results/baseline.json`)이 **전 구간 goodput 100%**였던 이유를 스스로 해부합니다. 원인 후보가 셋입니다.

| 후보 | 왜 문제인가 | 확인 방법 |
|---|---|---|
| ① SLO가 느슨함 | TTFT 2s / E2E 30s인데 실측이 0.1s / 7s | 같은 데이터에 SLO만 조여 재계산 |
| ② 동시성이 슬롯을 안 넘음 | 슬롯 16인데 동시성도 16까지만 | B1이 이미 답함 |
| ③ 프롬프트가 하나로 고정 | prefix caching이 TTFT를 부풀림 | 아래 실험 |

### ③ 확인 — `--unique-prefix`

`benchmark.py`의 `SCENARIOS`는 시나리오마다 프롬프트가 **하나로 고정**되어 있어, 모든 요청이 같은 입력이면 두 번째 요청부터 prefill이 캐시로 해결됩니다. TTFT가 실제보다 좋게 나옵니다.

1주차 Cloud Run 스크립트에 있던 장치(`uncached_user_messages()` — 프롬프트 앞에 UUID를 붙여 고유화)를 **`--unique-prefix` 플래그로 옮겨 두었습니다.** 기본값은 끔이라 기존 측정과 호환됩니다.

```bash
# 켜고 끄고 각각 측정
python3 benchmark.py --scenarios prefill --concurrency 8 --requests-per-level 100 \
  --output results/b5-cached.json
python3 benchmark.py --scenarios prefill --concurrency 8 --requests-per-level 100 \
  --unique-prefix --output results/b5-unique.json
```

적중률은 서버 쪽에서도 확인합니다.

```promql
rate(vllm:prefix_cache_hits_total[1m]) / rate(vllm:prefix_cache_queries_total[1m])
```

### ① 확인 — 백분위 안정성

같은 조건에서 요청 수만 바꿔 p95가 얼마나 흔들리는지 봅니다. **8개 샘플의 p95는 사실상 최댓값**입니다.

```bash
for N in 8 30 100 300; do
  python3 benchmark.py --scenarios short --concurrency 8 --requests-per-level $N \
    --output results/b5-n$N.json
done
```

### 관측 — 채울 표

| 실험 | TTFT p50 | TTFT p95 | 캐시 적중률 | 해석 |
|---|---|---|---|---|
| 프롬프트 고정 | | | | |
| 프롬프트 고유화 | | | | |

| 요청 수 | TTFT p95 | 반복 시 편차 |
|---|---|---|
| 8 | | |
| 30 | | |
| 100 | | |
| 300 | | |

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

---

## 정리

```bash
# 실습용 설정 원복
kubectl -n llm-serving-lab set env deploy/vllm-baseline MAX_NUM_SEQS=16 MAX_MODEL_LEN=4096
kubectl -n llm-serving-lab rollout status deploy/vllm-baseline

# 포트포워딩 종료
pkill -f "kubectl.*port-forward"

# GPU를 놓아주려면 (로컬이라 과금은 없지만 VRAM 회수)
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0
```

---

## 트러블슈팅

| 증상 | 원인 | 대응 |
|---|---|---|
| 실습 중 파드가 전부 `Completed`/`Error` | WSL 유휴 → systemd poweroff | 0-1의 `sleep infinity` 창 확인 |
| `port-forward` 연결 끊김 | 롤아웃으로 파드가 바뀜 | 재배포마다 다시 띄우기 (스크립트에 포함됨) |
| Windows에서 `localhost:30001` 접속 안 됨 | NodePort는 WSL localhost 릴레이가 인식 못 함 | `port-forward` 사용 |
| 롤아웃이 `rollout status`에서 멈춤 | 모델 로딩 중 | `logs -f`로 진행 확인, `startupProbe`가 최대 20분 허용 |
| `slots=64`에서 OOM 또는 기동 실패 | KV cache 부족 | 실패가 아니라 **B3의 결과**. 로그 기록 후 값 낮추기 |
| 처리량이 슬롯과 무관하게 동일 | env 반영 안 됨 | `logs | grep max_num_seqs`로 확인 |

---

## 글로 옮길 때의 뼈대

1. **문제 제기** — 1주차 Cloud Run에서 c=16에 goodput이 50%로 떨어졌다. 왜?
2. **B1** — 슬롯 수를 바꿔가며 붕괴점이 따라 움직이는지 확인 (표 3개)
3. **B2** — 서버 내부에서 무슨 일이 일어나는지 (Grafana 그림 1장) ★
4. **B3** — 그런데 슬롯을 키워도 안 되는 지점이 있다 (KV cache)
5. **B4** — 서버가 재는 지연과 사용자가 겪는 지연은 다르다
6. **B5** — 내 첫 측정이 틀렸던 이유 3가지
7. **한계와 다음** — 6주차·7주차로 넘길 것들

---

## 참고

- 1주차 실습: [`Run inference of Gemma 4 model on Cloud Run.md`](./Run%20inference%20of%20Gemma%204%20model%20on%20Cloud%20Run.md) — A1~A4 실험 설계와 선행 관측
- 환경 구축: [`WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기.md`](./WSL2%EB%A5%BC%20%EB%A1%9C%EC%BB%AC%20GPU%20Kubernetes%20%EA%B0%9C%EB%B0%9C%20%ED%99%98%EA%B2%BD%EC%9C%BC%EB%A1%9C%20%EC%82%AC%EC%9A%A9%ED%95%98%EA%B8%B0.md)
- 기준선 측정: [`labs/wsl2-vllm-baseline/`](../labs/wsl2-vllm-baseline/README.md)
- 2주차 예습 노트: [`knowledge/06-week2-prep.md`](../knowledge/06-week2-prep.md)
