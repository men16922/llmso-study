# 배치 슬롯을 넘어서면 무슨 일이 일어나는가 — WSL2 로컬 K8s에서 vLLM 배칭·큐 실습

> **이 문서는 실습 시나리오입니다.** 순서대로 실행하고 표의 빈칸을 채우면, 그대로 2주차 과제 글의 뼈대가 됩니다.
> 측정이 끝난 뒤 "관측" 절의 빈칸을 채우고 "해석"을 쓰면 완성입니다.

**이번 편은 B1 · B2 · C1 세 실험입니다.** B3~B5는 분량상 [다음 편으로 미룹니다](#다음-편으로-미루는-것) — 설계는 이 문서 뒤쪽에 그대로 보존해 두었습니다.

---

## 이 실습이 답하려는 질문

교재 CH3·CH4의 핵심 주장을 **내 GPU에서 재현**하는 것이 목적입니다.

| # | 질문 | 교재 대응 |
|---|---|---|
| **B1** | 동시 요청을 계속 늘리면 처리량은 계속 오르는가? **어디서 멈추는가?** | CH3 배칭 |
| **B2** | 그 순간 서버 안에서는 무슨 일이 일어나는가? | CH3 큐·동시성 |
| **C1** | 그 배칭을 **직접 짜면** 어디까지 가고, vLLM과 무엇이 다른가? | CH3 시스템 설계 (교재 코드) |

> **챕터 대응에 대한 주의.** 교재 CH3는 "배칭"을 **시스템 설계** 층위에서, CH6는 같은 주제를 **최적화** 층위(continuous batching·chunked prefill·prefix caching)에서 다룹니다. B1·B2는 두 층위에 걸쳐 있고, C1이 CH3 쪽에 정확히 대응합니다. 다음 편의 B3(KV cache 상한)는 엄밀히는 **CH5** 주제입니다.

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
| **C1 추가** | 교재 저장소 `orca3/llm-model-inference` (WSL2 안에 클론), `ch03/single_model_llm_serving` |

### 소요 시간

| 단계 | 실측 예상 |
|---|---|
| 0. 준비 | 20분 |
| B1 | **60~80분** (롤아웃 3회 × 모델 로딩 포함) |
| B2 | 20분 |
| C1 | 100~120분 (설치 40 + 어댑터 40 + 측정 40, 설치는 B1과 병행 가능) |

**총 3~4시간.** 한 자리에 다 하지 말고 **B1·B2 세션 / C1 세션**으로 나누세요. B1·B2만으로도 글 한 편의 뼈대가 서므로, 먼저 그 안전판을 확보한 뒤 C1에 들어갑니다.

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
curl -s localhost:8000/metrics | grep -oE '^vllm:[a-z_]+' | sort -u | tee results/metrics-v0.23.0.txt
```

기대하는 이름과 쓰임 — **빈 결과가 나오면 오른쪽 대안을 먼저 확인하세요.** vLLM V1 엔진 이후 이름이 바뀐 것들이 있습니다.

| 쓰는 곳 | 1순위 이름 | 확인할 대안 |
|---|---|---|
| B2 — 배치에 들어간 요청 수 | `vllm:num_requests_running` | — |
| B2 — 큐 대기 | `vllm:num_requests_waiting` | — |
| B2 — 서버 측 TTFT | `vllm:time_to_first_token_seconds_bucket` | — |
| (다음 편 B3) KV cache 사용률 | `vllm:gpu_cache_usage_perc` | **`vllm:kv_cache_usage_perc`** |
| (다음 편 B4) 서버 측 종단간 | `vllm:e2e_request_latency_seconds_bucket` | — |
| (다음 편 B5) prefix cache 적중률 | `vllm:prefix_cache_queries_total` / `_hits_total` | **`vllm:gpu_prefix_cache_queries_total`** / `_hits_total` |

> **이름이 다르면 그 자체가 기록거리입니다.** v0.23.0 기준 실제 목록을 파일로 남겨 글에 붙이면 재현하는 사람에게 그대로 도움이 됩니다.

### 0-4. 매니페스트 적용

`k8s/vllm-baseline.yaml`은 **이미 파라미터화되어 있습니다.** 세 값이 env로 빠져 있어 `kubectl set env`만으로 롤아웃할 수 있습니다.

```yaml
              --max-model-len "$MAX_MODEL_LEN"
              --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
              --max-num-seqs "$MAX_NUM_SEQS"
```

| 변수 | 기본값 | 쓰는 실험 |
|---|---|---|
| `MAX_NUM_SEQS` | 16 | B1 · B2 |
| `MAX_MODEL_LEN` | 4096 | (다음 편 B3) |
| `GPU_MEMORY_UTILIZATION` | 0.85 | (다음 편 B3) |

`strategy: Recreate`라 이전 파드가 먼저 내려가므로 GPU 경합이 없습니다.

```bash
kubectl apply -f labs/wsl2-vllm-baseline/k8s/vllm-baseline.yaml
kubectl -n llm-serving-lab rollout status deploy/vllm-baseline --timeout=10m
```

### 0-5. 재배포 헬퍼 ★ B1 루프가 이걸 씁니다

슬롯을 바꿀 때마다 ① env 설정 ② 롤아웃 대기 ③ 포트포워딩 재기동 ④ **실제 응답할 때까지 대기**가 필요합니다. `sleep 5`로 때우면 파드가 준비되기 전에 벤치마크가 시작돼 조용히 실패합니다.

```bash
# labs/wsl2-vllm-baseline/redeploy.sh
#!/usr/bin/env bash
set -euo pipefail
NS=llm-serving-lab

redeploy() {   # redeploy MAX_NUM_SEQS=16 [MAX_MODEL_LEN=4096 ...]
  kubectl -n "$NS" set env deploy/vllm-baseline "$@"
  if ! kubectl -n "$NS" rollout status deploy/vllm-baseline --timeout=10m; then
    echo "!! 롤아웃 실패: $* — 이 구성은 건너뜁니다" >&2
    kubectl -n "$NS" logs deploy/vllm-baseline --tail=40 >&2 || true
    return 1
  fi
  pkill -f "port-forward.*vllm-baseline" || true
  sleep 2
  kubectl -n "$NS" port-forward --address 0.0.0.0 svc/vllm-baseline 8000:8000 &
  for _ in $(seq 60); do            # 최대 60초, 실제 응답을 확인
    curl -sf localhost:8000/v1/models >/dev/null && return 0
    sleep 1
  done
  echo "!! 포트포워딩 후 /v1/models 응답 없음" >&2
  return 1
}
```

**롤아웃 실패를 반드시 잡아야 하는 이유**: B1의 `slots=64`는 KV cache 부족으로 기동에 실패할 수 있습니다. 그건 실패가 아니라 관측 결과인데, 스크립트가 그냥 넘어가면 죽은 엔드포인트에 대고 벤치마크를 돌려 **쓰레기 데이터**를 만듭니다.

### 0-6. 스모크 테스트

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

슬롯 값 **3개**로 스윕합니다. (원래 4개였으나 `slots=4`는 1과 16 사이의 중간값일 뿐이고, 롤아웃 1회 = 모델 로딩 포함 3~5분이라 비용 대비 얻는 게 적습니다. 시간이 남으면 마지막에 추가하세요.)

```bash
cd labs/wsl2-vllm-baseline
source redeploy.sh

for SLOTS in 1 16 64; do
  redeploy MAX_NUM_SEQS=$SLOTS || continue      # 기동 실패는 건너뛴다
  echo "=== slots=$SLOTS short 시작 $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt

  python3 benchmark.py \
    --scenarios short \
    --concurrency 1,2,4,8,16,32,64 \
    --requests-per-level 100 \
    --unique-prefix \
    --ttft-slo 0.5 --e2e-slo 10 \
    --output results/b1-slots-$SLOTS-short.json

  echo "=== slots=$SLOTS short 종료 $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt
done
```

> **`--unique-prefix`를 켜는 이유**: 모든 요청이 같은 프롬프트면 두 번째 요청부터 prefill이 prefix cache로 해결되어 TTFT가 실제보다 좋게 나옵니다. **배칭을 재는 실험에서는 이 효과를 제거해야** 슬롯 효과만 남습니다. (이 플래그의 존재 이유 자체는 다음 편 B5의 주제입니다.)

`decode` 시나리오는 요청당 4~7초라 전 구간을 돌리면 너무 깁니다. **포인트를 줄여** 별도로 한 번 더 돌립니다.

```bash
for SLOTS in 1 16 64; do
  redeploy MAX_NUM_SEQS=$SLOTS || continue
  echo "=== slots=$SLOTS decode 시작 $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt

  python3 benchmark.py --scenarios decode \
    --concurrency 1,8,32 --requests-per-level 30 \
    --unique-prefix \
    --ttft-slo 0.5 --e2e-slo 30 \
    --output results/b1-slots-$SLOTS-decode.json

  echo "=== slots=$SLOTS decode 종료 $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt
done
```

**`results/b1-timeline.txt`를 반드시 남기세요.** 다음 편 B4가 Prometheus에서 이 구간을 되짚어야 하는데, 시각 기록이 없으면 데이터가 있어도 못 씁니다.

### 관측 — 채울 표

**`short` 시나리오, 처리량 (tok/s)**

| 동시성 | slots=1 | slots=16 | slots=64 |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 4 | | | |
| 8 | | | |
| 16 | | | |
| 32 | | | |
| 64 | | | |

**TTFT p95 (s)** — 같은 형식으로 하나 더

**goodput (%)** — 같은 형식으로 하나 더

### 관측 — 파레토 곡선 ★ 추가 측정 없이 얻는 그림

위 표 세 개는 같은 데이터의 세 단면입니다. **처리량(x축) vs TTFT p95(y축)** 산점도로 다시 그리면, 교재 CH3의 *cost-optimized vs latency-optimized design*이 한 장에 나옵니다.

- 점 하나 = (슬롯 값, 동시성) 조합 하나
- `--ttft-slo 0.5` 선을 가로로 긋는다 → 그 아래가 **SLO 충족 영역**
- 그 영역 안에서 **가장 오른쪽 점**이 이 GPU의 실질 최대 처리량

"처리량을 얼마까지 살 수 있고, 그 값이 지연으로 얼마인가"가 곡선 하나로 답해집니다. **추가 측정은 0회**입니다.

### 판단 기준

- ✅ **가설대로면**: `slots=1` 열은 동시성과 거의 무관하게 평평하고, `slots=16` 열은 동시성 16 부근에서, `slots=64` 열은 훨씬 뒤에서 꺾입니다. 꺾이는 위치가 열마다 오른쪽으로 이동해야 합니다.
- ⚠️ **모든 열이 똑같이 나오면**: 슬롯 변경이 실제로 반영되지 않은 것입니다. 파드 로그에서 확인하세요.
  ```bash
  kubectl -n llm-serving-lab logs deploy/vllm-baseline | grep -i "max_num_seqs\|max num seqs"
  ```
- ⚠️ **`slots=64`가 뜨지 않거나 값이 줄어들면**: KV cache 메모리가 부족해 vLLM이 스스로 낮춘 것입니다. **이건 실패가 아니라 다음 편 B3의 답입니다** — `redeploy`가 찍어준 로그를 그대로 기록하세요.

---

## B2. 큐가 보이는 그림 ★ 글의 대표 이미지

### 목적

B1에서 숫자로 본 붕괴를 **서버 내부 상태로** 확인합니다. 클라이언트 지연이 왜 늘어나는지가 여기서 드러납니다.

### 실행

슬롯을 16으로 되돌리고, **슬롯을 확실히 넘는 부하**를 길게 겁니다.

```bash
redeploy MAX_NUM_SEQS=16

echo "=== B2 시작 $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt

python3 benchmark.py --scenarios decode \
  --concurrency 4,16,64 --requests-per-level 200 \
  --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 30 \
  --output results/b2-queue.json

echo "=== B2 종료 $(date -u +%H:%M:%S) UTC ===" | tee -a results/b1-timeline.txt
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
- 💡 `running`의 최댓값이 설정한 16보다 **작으면** KV cache가 먼저 한계입니다 → 다음 편 B3의 소재.

---

## C1. 그 배칭을 직접 짜면 — 교재 코드로 하는 대조 실험 ★ CH3의 본체

> 여기까지는 vLLM을 **블랙박스로 두고 밖에서** 부하를 걸었습니다. CH3가 실제로 가르치는 것은 **그 안을 직접 짜보는 것**입니다.

### 왜 이 실험이 성립하는가

교재 저장소의 `ch03/single_model_llm_serving`에는 **배칭 네 방식이 한 서버 안에** 들어 있습니다. 같은 모델(`facebook/opt-125m`), 같은 프로세스, 같은 GPU — 통제가 완벽합니다.

| 엔드포인트 | 구현 위치 | 배칭 성격 |
|---|---|---|
| `/basic_generate` | `llm.py` `basic_generate()` — WorkloadManager를 우회, 1건씩 | **배칭 없음** |
| `/generate` | `llm.py` `generate()` — `while not _is_batch_finished` | **static** |
| `/generate_stream` | `llm.py` `requests_processing_loop()` — 슬롯 비는 대로 채움 | **naive continuous** |
| `/generate_vllm` | 인프로세스 vLLM | **진짜 continuous** |

그리고 `workload_manager.py:23`의 `self.batch_size = 4`가 **B1의 `max-num-seqs`와 정확히 같은 축**입니다. B1 스윕을 자작 서버에 그대로 재현할 수 있습니다.

### 가설

1. `basic_generate` < `generate`(static) < `generate_stream`(continuous) 순으로 처리량이 오른다.
2. static → continuous 전환만으로도 **동시성이 높을수록 격차가 커진다.**
3. continuous로 바꿔도 vLLM과는 여전히 격차가 남는다. 그 격차의 정체는 **배칭 방식이 아니라** PagedAttention·토큰 단위 스케줄링·커널 최적화다.

### C1-0. 준비

```bash
# 0) k3s의 vLLM이 VRAM을 쥐고 있으면 교재 서버가 못 뜬다 ★ 필수
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0
nvidia-smi   # VRAM이 비었는지 확인

# 1) 교재 저장소
git clone https://github.com/orca3/llm-model-inference.git
cd llm-model-inference/ch03/single_model_llm_serving

# 2) 환경 — vllm 0.9.0.1 + torch 2.7.0 핀. 8~10GB, 30~40분
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

> ⚠️ `LLMEngine.__init__`이 기동 시점에 `VLLM(model="facebook/opt-125m")`를 **인프로세스로** 띄웁니다(기본 `gpu_memory_utilization=0.9`). k3s 파드를 내리지 않으면 여기서 OOM으로 죽습니다.
> 💡 이 설치는 시간이 걸리므로 **B1을 돌리는 동안 다른 창에서 병행**하세요. 단, 설치만 하고 서버 기동은 B1이 끝난 뒤에.

### C1-1. 공정성 정렬 ★ 이걸 안 하면 비교가 무의미합니다

**세 엔드포인트의 출력 토큰 수가 서로 다릅니다.** 코드를 읽어보면:

| 위치 | 현재 값 | 영향 |
|---|---|---|
| `llm/llm.py:17` | `self.max_tokens = 20` | `/generate_stream`, `/generate_vllm` |
| `llm/model_worker.py:48` | `max_new_tokens=50` | `/basic_generate`, `/generate` |

`/generate`만 50토큰을 만들고 나머지는 20토큰입니다. **이 상태로 처리량을 비교하면 2.5배 왜곡**됩니다. 하나로 맞추세요.

```bash
sed -i 's/max_new_tokens=50/max_new_tokens=20/' llm/model_worker.py
grep -n "max_new_tokens" llm/model_worker.py    # 확인
```

> 이 불일치를 발견한 것 자체가 글감입니다 — **"교재 코드를 벤치마크에 쓰려면 먼저 통제 변수를 맞춰야 한다"**는 게 CH4 벤치마킹 절의 "한 번에 하나씩만 바꿀 것"과 정확히 같은 이야기입니다.

### C1-2. 벤치마크 어댑터

`benchmark.py`는 OpenAI 호환 스키마(`/v1/chat/completions`, `data: {"choices":[{"delta":...}]}`)를 전제합니다. 교재 서버는 스키마가 다릅니다.

| 엔드포인트 | 요청 | 응답 |
|---|---|---|
| `/generate` | `{"prompts": ["..."]}` | `{"generated_texts": [...]}` (비스트리밍) |
| `/generate_stream` | `{"prompt": "..."}` | SSE `data: {"token": " a", "sequence_id": "..."}` |
| `/generate_vllm` | `{"prompts": ["..."]}` | `{"generated_texts": [...]}` (비스트리밍) |

`benchmark.py`에 `--api book` 모드를 추가해 **요청 본문 생성과 SSE 파싱만 분기**하고, 백분위·goodput·요약 로직(`summarize_group`, `percentile`)은 그대로 재사용합니다. 손댈 곳은 `run_request()` 하나입니다.

주의할 점 둘:

- **비스트리밍 엔드포인트는 TTFT가 정의되지 않습니다.** `/generate`와 `/generate_vllm`은 **E2E와 처리량만** 비교하세요. TTFT 칸은 `-`로 두는 게 정직합니다. *(static batching에는 스트리밍이 없다 — 그 자체가 결과입니다.)*
- **`usage`가 없으므로** `estimate_tokens()`(공백 분리)로 떨어집니다. 세 엔드포인트가 모두 같은 방식으로 세므로 **상대 비교는 유효**하지만, 절대값을 vLLM 서버의 tok/s와 직접 비교하지는 마세요.

### C1-3. 실행

```bash
python main.py     # 기동에 수 분 (opt-125m 로딩 + vLLM 초기화)
```

배치 크기 축을 바꿔가며 세 엔드포인트를 각각 측정합니다. `batch_size`는 상수이므로 **재기동이 필요**합니다.

```bash
cd ~/llm-model-inference/ch03/single_model_llm_serving
BENCH=~/"Hands-On LLM Serving and Optimization Study"/labs/wsl2-vllm-baseline/benchmark.py

for BS in 1 4 16; do
  sed -i "s/self.batch_size = .*/self.batch_size = $BS  # Process up to N sequences at a time/" llm/workload_manager.py
  # 서버 재기동
  pkill -f "python main.py" || true; sleep 3
  python main.py > /tmp/book-server-$BS.log 2>&1 &
  until curl -sf -X POST localhost:8000/basic_generate \
        -H 'Content-Type: application/json' -d '{"prompt":"hi"}' >/dev/null; do sleep 3; done

  for EP in basic_generate generate generate_stream generate_vllm; do
    python3 "$BENCH" --api book --endpoint /$EP \
      --scenarios short --concurrency 1,2,4,8,16,32 \
      --requests-per-level 50 \
      --output results/c1-bs$BS-$EP.json
  done
done
```

> `/generate_vllm`은 `batch_size`와 무관합니다(vLLM이 자체 스케줄링). **세 번 다 같은 값이 나와야 정상**이고, 안 나오면 측정 노이즈의 크기를 알려주는 지표가 됩니다 — 공짜로 얻는 재현성 점검입니다.

### 관측 — 채울 표

**처리량 (tok/s), `batch_size=4` 기준**

| 동시성 | basic (배칭 없음) | generate (static) | generate_stream (continuous) | generate_vllm |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 4 | | | | |
| 8 | | | | |
| 16 | | | | |
| 32 | | | | |

**E2E p95 (s)** — 같은 형식으로 하나 더

**`batch_size` 축** — continuous 엔드포인트만

| 동시성 | bs=1 | bs=4 | bs=16 |
|---|---|---|---|
| 8 | | | |
| 16 | | | |
| 32 | | | |

### 판단 기준

- ✅ **가설 1·2대로면**: 동시성 1에서는 네 열이 비슷하고, 동시성이 오를수록 벌어집니다. `basic`은 완전히 평평(직렬 처리)해야 합니다.
- ✅ **가설 3**: `generate_vllm` 열이 압도적으로 높을 것입니다. 중요한 건 승패가 아니라 **`generate_stream`까지 오는 데 얼마를 벌었고, 거기서 vLLM까지 얼마가 남았는가**입니다. 전자는 스케줄링 설계의 몫, 후자는 커널·메모리 관리의 몫입니다.
- ⚠️ **`/generate`가 동시 요청에서 이상한 값을 내면** — 코드상 예견되는 문제입니다. `ModelExecutor.execute_batch()`는 `task_queue.put()` 직후 `result_queue.get()`을 하는데, **동시 호출자 둘이 서로의 결과를 받아갈 수 있습니다**(`model_executor.py:33-46`). 응답이 뒤바뀌거나 예외가 나면 그걸 그대로 기록하세요 — **"교재 예제는 단일 요청 데모이지 동시성 안전하지 않다"**는 것도 CH3 시스템 설계의 결론 중 하나입니다.
- ⚠️ **`bs=16`이 `bs=4`보다 나쁘면**: `ModelWorker.generate()`가 배치 전체를 `padding=True`로 묶어 한 번에 돌리므로, 길이가 다른 요청이 섞이면 **패딩 낭비**가 커집니다. vLLM이 토큰 단위로 배칭하는 이유가 바로 이것입니다.

### 정리

```bash
deactivate
pkill -f "python main.py"
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=1   # k3s 복구
```

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
| **NVIDIA Triton, 멀티모델 서빙** (LRU 모델 캐시, on-demand 로딩) | CH3 후반 · `ch03/multi_model_serving` | 다루지 않음 — LLM 서빙 맥락과 거리가 있어 제외 |
| **에이전틱 시스템, RAG, CAG** | CH4 전반 · `ch04/KnowledgeAgent` | 다루지 않음 — 별도 편에서 로컬 vLLM 백엔드로 재구성 예정 |
| **클라우드 벤더 / build-or-buy** | CH4 후반 · `ch04/{bedrock,jumpstart,dlc}` | 다루지 않음 — 계정·비용 발생, 6주차와 중복 |
| **엔터프라이즈 서빙 아키텍처** | CH4 | 다루지 않음 |

---

## 글로 옮길 때의 뼈대

1. **문제 제기** — 1주차 Cloud Run에서 c=16에 goodput이 50%로 떨어졌다. 왜?
2. **B1** — 슬롯 수를 바꿔가며 붕괴점이 따라 움직이는지 확인 (표 3개 + 파레토 곡선)
3. **B2** — 서버 내부에서 무슨 일이 일어나는지 (Grafana 그림 1장) ★
4. **C1** — 그럼 그 배칭을 직접 짜면? 교재 코드로 배칭 없음 → static → continuous → vLLM (표 3개) ★
5. **종합** — 스케줄링 설계가 버는 것과, 거기서 vLLM까지 남는 격차의 정체
6. **한계와 다음** — 다루지 않은 CH3·CH4 + 6·7주차로 넘길 것들

---

## 트러블슈팅

| 증상 | 원인 | 대응 |
|---|---|---|
| 실습 중 파드가 전부 `Completed`/`Error` | WSL 유휴 → systemd poweroff | 0-1의 `sleep infinity` 창 확인 |
| `port-forward` 연결 끊김 | 롤아웃으로 파드가 바뀜 | 0-5의 `redeploy`가 처리 |
| Windows에서 `localhost:30001` 접속 안 됨 | NodePort는 WSL localhost 릴레이가 인식 못 함 | `port-forward` 사용 |
| 롤아웃이 `rollout status`에서 멈춤 | 모델 로딩 중 | `logs -f`로 진행 확인, `startupProbe`가 최대 20분 허용 |
| `slots=64`에서 OOM 또는 기동 실패 | KV cache 부족 | 실패가 아니라 **다음 편 B3의 결과**. 로그 기록 후 건너뛰기 |
| 처리량이 슬롯과 무관하게 동일 | env 반영 안 됨 | `logs \| grep max_num_seqs`로 확인 |
| **C1** 교재 서버가 기동 중 OOM | k3s 파드가 VRAM 점유 | `kubectl scale deploy/vllm-baseline --replicas=0` |
| **C1** `/generate`가 동시 요청에 뒤섞인 응답 | `execute_batch`의 큐 경합 | 버그가 아니라 **관측 결과**. 그대로 기록 |
| **C1** `pip install vllm==0.9.0.1` 실패 | CUDA·torch 버전 충돌 | 새 venv에서 `requirements.txt` 순서 그대로 설치 |

---

## 다음 편으로 미루는 것

아래 셋은 설계가 끝나 있으므로 다음 편에서 그대로 실행하면 됩니다. **B1·B2의 결과 파일과 `results/b1-timeline.txt`가 그대로 입력**이 됩니다.

### B3. 동시 요청 수의 상한은 무엇이 정하는가 *(엄밀히는 CH5 주제)*

> 1주차 예습 노트의 숙제: *"KV cache는 요청마다 쌓이는데, 동시 요청 수의 상한은 무엇이 정하나?"*

슬롯 수를 아무리 키워도 **KV cache 메모리가 먼저 상한을 정한다**는 것을 확인합니다.

```bash
redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=16384
kubectl -n llm-serving-lab logs deploy/vllm-baseline | grep -iE "kv cache|gpu blocks|maximum concurrency"
```

**측정 전에 손계산을 먼저 적어두세요.** 예측과 실측을 대조하는 게 이 실험의 값어치입니다.

```
토큰당 KV = 2(K,V) × 층수 × KV헤드수 × head_dim × 2 bytes
KV 예산  = 12GB × gpu_memory_utilization − 가중치 − 활성화
실질 동시성 ≈ KV 예산 ÷ (토큰당 KV × max-model-len)
```

Qwen2.5-1.5B의 층수·KV 헤드 수·head_dim은 **모델 `config.json`에서 직접 확인**하세요. 기동 로그의 `Maximum concurrency for N tokens per request: X.XXx`가 정답을 직접 알려주므로, 손계산과 나란히 놓으면 글이 됩니다.

| `max-model-len` | `max-num-seqs` | 손계산 예측 | 로그가 보고한 실질 동시성 | KV cache 사용률 최대 | 처리량 |
|---|---|---|---|---|---|
| 4096 | 16 | | | | |
| 4096 | 64 | | | | |
| 16384 | 64 | | | | |
| 4096 (`GPU_MEMORY_UTILIZATION=0.6`) | 64 | | | | |

### B4. 서버가 재는 지연 vs 사용자가 겪는 지연 *(CH4 성능 측정)*

> CH4: *"추론 시간은 빠른데 종단간이 느리다면, 모델 성능 최적화가 아니라 인프라를 봐야 한다."*

B2 구간(`results/b1-timeline.txt`의 시각)을 Prometheus에서 되짚어 `benchmark.py`의 `e2e_p95_s`와 비교합니다.

```promql
histogram_quantile(0.95, sum(rate(vllm:e2e_request_latency_seconds_bucket[1m])) by (le))
```

> ⚠️ **먼저 확인할 것.** vLLM의 `e2e_request_latency_seconds`는 요청이 **엔진에 도착한 시점**부터 재므로 **큐 대기를 이미 포함**할 가능성이 큽니다. 그렇다면 서버–클라이언트 차이는 큐가 아니라 HTTP + port-forward + 클라이언트 asyncio 스케줄링입니다. 즉 *"차이가 커지면 큐 대기가 클라이언트에만 잡힌다"*는 해석은 **성립하지 않을 수 있습니다.** 0-3에서 메트릭을 뽑을 때 이 정의부터 확정하거나, 정의가 더 명확한 `time_to_first_token` 비교로 바꾸세요.

| 동시성 | 서버 측 e2e p95 | 클라이언트 e2e p95 | 차이 | 차이 비율 |
|---|---|---|---|---|
| 4 | | | | |
| 16 | | | | |
| 64 | | | | |

### B5. 내 기존 측정은 왜 전부 goodput 100%였는가 *(CH4 벤치마킹 · ③은 CH6 prefix caching)*

기존 기준선(`results/baseline.json`)이 전 구간 goodput 100%였던 이유를 해부합니다.

| 후보 | 왜 문제인가 | 확인 방법 |
|---|---|---|
| ① SLO가 느슨함 | TTFT 2s / E2E 30s인데 실측이 0.1s / 7s | 같은 데이터에 SLO만 조여 재계산 |
| ② 동시성이 슬롯을 안 넘음 | 슬롯 16인데 동시성도 16까지만 | **B1이 이미 답함** |
| ③ 프롬프트가 하나로 고정 | prefix caching이 TTFT를 부풀림 | `--unique-prefix` 켜고 끄고 비교 |

```bash
python3 benchmark.py --scenarios prefill --concurrency 8 --requests-per-level 100 \
  --output results/b5-cached.json
python3 benchmark.py --scenarios prefill --concurrency 8 --requests-per-level 100 \
  --unique-prefix --output results/b5-unique.json

for N in 8 30 100 300; do    # 백분위 안정성 — 8개 샘플의 p95는 사실상 최댓값
  python3 benchmark.py --scenarios short --concurrency 8 --requests-per-level $N \
    --output results/b5-n$N.json
done
```

---

## 참고

- 1주차 실습: [`Run inference of Gemma 4 model on Cloud Run.md`](./Run%20inference%20of%20Gemma%204%20model%20on%20Cloud%20Run.md) — A1~A4 실험 설계와 선행 관측
- 환경 구축: [`WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기.md`](./WSL2%EB%A5%BC%20%EB%A1%9C%EC%BB%AC%20GPU%20Kubernetes%20%EA%B0%9C%EB%B0%9C%20%ED%99%98%EA%B2%BD%EC%9C%BC%EB%A1%9C%20%EC%82%AC%EC%9A%A9%ED%95%98%EA%B8%B0.md)
- 기준선 측정: [`labs/wsl2-vllm-baseline/`](../labs/wsl2-vllm-baseline/README.md)
- 2주차 예습 노트: [`knowledge/06-week2-prep.md`](../knowledge/06-week2-prep.md)
- 교재 공식 코드: `orca3/llm-model-inference` — CH3 `ch03/single_model_llm_serving`(C1이 쓰는 것) · `ch03/multi_model_serving`, CH4 `ch04/KnowledgeAgent` · `ch04/{bedrock,jumpstart,dlc,dlc_customization}`
