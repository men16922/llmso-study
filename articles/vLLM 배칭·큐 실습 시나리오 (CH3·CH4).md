# 배치 슬롯을 넘어서면 무슨 일이 일어나는가 — WSL2 로컬 K8s에서 vLLM 배칭·큐 실습

> **이 문서는 실습 시나리오입니다.** 순서대로 실행하고 표의 빈칸을 채우면, 그대로 2주차 과제 글의 뼈대가 됩니다.
> 측정이 끝난 뒤 "관측" 절의 빈칸을 채우고 "해석"을 쓰면 완성입니다.

**이번 편은 B1 · B2 · C1 · C2 · C3 다섯 실험입니다.** B3~B5는 분량상 [다음 편으로 미룹니다](#다음-편으로-미루는-것) — 설계는 이 문서 뒤쪽에 그대로 보존해 두었습니다.

> **분량 경고.** 다섯 실험은 **6.5~8시간·네 세션**입니다. 마감(2026-08-16 09:00)까지 일주일이니 하루 2시간씩이면 맞지만 여유가 없습니다. **B1·B2만으로도 글 한 편이 서므로 세션 1을 반드시 먼저 끝내세요.** 시간이 부족해지면 잘라내는 순서는 **C3-4 → C1의 `bs` 축 → C2의 20ms 지점** 입니다 (각각의 핵심 결론은 남습니다).

---

## 이 실습이 답하려는 질문

교재 CH3·CH4의 핵심 주장을 **내 GPU에서 재현**하는 것이 목적입니다.

| # | 질문 | 교재 대응 |
|---|---|---|
| **B1** | 동시 요청을 계속 늘리면 처리량은 계속 오르는가? **어디서 멈추는가?** | CH3 배칭 |
| **B2** | 그 순간 서버 안에서는 무슨 일이 일어나는가? | CH3 큐·동시성 |
| **C1** | 그 배칭을 **직접 짜면** 어디까지 가고, vLLM과 무엇이 다른가? | CH3 시스템 설계 (교재 코드) |
| **C2** | **dynamic batching은 언제 쓰나?** 그리고 왜 LLM에는 안 맞나 | CH3 Triton (교재 코드) |
| **C3** | 그 위에 **오케스트레이션 계층**을 얹으면 얼마를 내야 하나 | CH4 오픈소스 스택 · **도전과제** |

**네 실험이 합쳐서 배칭 4종을 전부 실측하고, C3가 그 위에 계층을 하나 더 얹습니다.** 예습 노트 §1의 표가 이 글에서 숫자로 채워집니다.

| 배칭 방식 | 어디서 재는가 |
|---|---|
| 배칭 없음 | C1 `/basic_generate` |
| **static** | C1 `/generate` |
| **dynamic** | **C2 Triton `dynamic_batching`** |
| **continuous** | B1·B2 (vLLM), C1 `/generate_stream`(자작)·`/generate_vllm` |

> **챕터 대응에 대한 주의.** 교재 CH3는 "배칭"을 **시스템 설계** 층위에서, CH6는 같은 주제를 **최적화** 층위(continuous batching·chunked prefill·prefix caching)에서 다룹니다. B1·B2는 두 층위에 걸쳐 있고, C1·C2가 CH3 쪽에 정확히 대응합니다. 다음 편의 B3(KV cache 상한)는 엄밀히는 **CH5** 주제입니다.

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
| **C2 추가** | Docker + `nvcr.io/nvidia/tritonserver:24.12-py3` (~17GB), `ch03/multi_model_serving` |

### 소요 시간

| 단계 | 실측 예상 |
|---|---|
| 0. 준비 | 20분 |
| B1 | **60~80분** (롤아웃 3회 × 모델 로딩 포함) |
| B2 | 20분 |
| C1 | 100~120분 (설치 40 + 측정 40 + 정리 20) |
| C2 | 60~70분 (ONNX export 20 + 측정 40) + **이미지 풀 30~40분은 백그라운드** |
| C3 | 120~150분 (KubeRay 설치 20 + RayService 기동 15 + 측정 60 + 관찰 20) |

**총 6.5~8시간.** 한 자리에 다 하지 말고 **네 세션**으로 나누세요.

| 세션 | 내용 | 왜 이 순서인가 |
|---|---|---|
| 1 | 0. 준비 → B1 → B2 | 이것만으로도 글의 뼈대가 섬 — **안전판 먼저** |
| 2 | C1 | 설치에서 시간이 새기 쉬움 |
| 3 | C2 | 앞의 결론(패딩 낭비)이 있어야 C2의 마무리가 선다 |
| 4 | C3 | B1·C2 결과가 있어야 비교 대상이 생긴다 (계층 오버헤드 · `@serve.batch` 대조) |

**세션 1을 시작할 때 아래 셋을 백그라운드로 걸어두세요.** 대기 시간이 사라집니다.

```bash
docker pull nvcr.io/nvidia/tritonserver:24.12-py3 &                 # C2용, ~17GB
docker pull rayproject/ray-llm:2.44.1-py311-cu124 &                 # C3용, ~10GB
# 다른 창에서 C1 venv 설치 (C1-0 참조) — 단, 서버 기동은 B1이 끝난 뒤
```

### GPU·포트가 하나뿐이라 생기는 제약 ★

| 실험 | 8000 포트 | GPU |
|---|---|---|
| B1·B2 | vLLM port-forward | `vllm-baseline` |
| C1 | 교재 서버 (인프로세스 vLLM) | 교재 서버 |
| C2 | (8009/8010/8011) | Triton 컨테이너 |
| C3 | Ray Serve port-forward | RayService 워커 |

**넷 중 하나만 GPU를 쥘 수 있습니다.** 세션을 넘어갈 때마다 앞의 것을 반드시 내리세요 — `kubectl scale deploy/vllm-baseline --replicas=0`, `pkill -f "python main.py"`, `docker rm -f triton`, `kubectl delete -f rayservice-qwen.yaml`. 안 내리면 다음 실험이 OOM으로 안 뜹니다.

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

### 0-5. 재배포 헬퍼 — [`labs/wsl2-vllm-baseline/redeploy.sh`](../labs/wsl2-vllm-baseline/README.md)

**이미 만들어져 있습니다.** 슬롯을 바꿀 때마다 ① env 설정 ② 롤아웃 대기 ③ 포트포워딩 재기동 ④ **실제 응답할 때까지 대기**가 필요한데, `sleep 5`로 때우면 파드가 준비되기 전에 벤치마크가 시작돼 조용히 실패합니다.

```bash
cd labs/wsl2-vllm-baseline
source redeploy.sh

redeploy MAX_NUM_SEQS=16          # env → 롤아웃 → 포트포워딩 → /v1/models 폴링(최대 60초)
confirm_slots                     # 파드 로그에서 실제 반영된 값 확인
mark "B1 slots=16 short 시작"     # results/b1-timeline.txt에 시각 기록
```

**롤아웃 실패를 반드시 잡아야 하는 이유**: B1의 `slots=64`는 KV cache 부족으로 기동에 실패할 수 있습니다. 그건 실패가 아니라 관측 결과인데, 스크립트가 그냥 넘어가면 죽은 엔드포인트에 대고 벤치마크를 돌려 **쓰레기 데이터**를 만듭니다. `redeploy`는 이 경우 로그 40줄을 찍고 `1`을 반환하므로, 호출부에서 `|| continue`로 건너뛸 수 있습니다.

### 0-6. 환경 기록 ★ 스터디 공통 규칙

스터디 벤치마크 규칙상 **모든 성능 수치는 아래를 함께 기록**해야 합니다. 측정 전에 한 번 찍어 글에 그대로 붙이세요.

```bash
cd labs/wsl2-vllm-baseline
{
  echo "## 환경";  date -u +"측정일 %Y-%m-%d %H:%M UTC"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
  echo "power.limit:"; nvidia-smi --query-gpu=power.limit --format=csv,noheader
  uname -r; python3 -V
  kubectl -n llm-serving-lab get deploy vllm-baseline \
    -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
  kubectl -n llm-serving-lab get deploy vllm-baseline \
    -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
  curl -s localhost:8000/v1/models | python3 -m json.tool
} | tee results/environment.md
```

| 기록 항목 | 어디서 |
|---|---|
| GPU · VRAM · Driver · **전력 상한** | `nvidia-smi` (랩탑은 TGP가 성능을 먼저 제한합니다) |
| OS · 커널 · Python | `uname -r`, `python3 -V` |
| serving engine 버전 | 컨테이너 이미지 태그 (`v0.23.0`) |
| 모델명 · dtype · tensor parallel | `/v1/models` + 파드 env |
| 입력·출력 토큰 길이 (ISL/OSL) | `benchmark.py`의 `SCENARIOS` — 결과 JSON `meta`에도 기록됨 |
| 동시 요청 수 · 총 요청 수 | 결과 JSON `meta.concurrency` / `requests_per_level` |

### 0-7. 반복 규칙 ★ 시간이 허락하는 만큼

스터디 규칙은 **최소 3회 반복 후 대표값**입니다. 다만 이번 실습은 전체 4.5~5.5시간이라 전 구간 3회는 현실적이지 않습니다. 타협안:

- **핵심 구간만 3회**: B1의 `slots=16`, 동시성 8·16·32 (붕괴점 주변). `--output`을 `-r1/-r2/-r3`로 나눠 저장
- 나머지는 1회 측정하되, **글에 "1회 측정"이라고 명시**
- 흔들림의 크기는 `--requests-per-level`을 키워 백분위를 안정시키는 것으로 대신합니다 (100 이상)

> 반복을 못 한 것 자체는 흠이 아닙니다. **안 했는데 한 것처럼 쓰는 것**이 문제입니다.

### 0-8. 스모크 테스트

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

**TTFT p95 (s)** · **goodput (%)** · **ITL p50 (s)** — 같은 형식으로 세 개 더

> **ITL(inter-token latency)** 은 첫 토큰 이후 토큰 하나당 평균 간격입니다. 스터디 공통 지표의 TPOT가 이것이고, `ITL 10ms = 사용자당 100 TPS`입니다. `benchmark.py`가 이미 재서 결과 JSON의 `itl_p50_s` / `perceived_tps`에 담습니다. **TTFT는 배칭에 민감하고 ITL은 상대적으로 둔감**한 것이 관전 포인트입니다 — 배치가 커져도 토큰 간격은 크게 안 변하는데 첫 토큰까지가 길어지는 구조.

### 표는 손으로 채우지 마세요 ★

결과 JSON에서 바로 마크다운 표가 나옵니다. 8개를 손으로 옮기면 반드시 어딘가 틀립니다.

```bash
cd labs/wsl2-vllm-baseline

# 표 3종(처리량·TTFT p95·goodput)을 한 번에
python3 summarize_results.py results/b1-slots-*-short.json \
  --label-regex 'slots-(\d+)' --label-format 'slots={}' --all

# ITL 표 하나 더
python3 summarize_results.py results/b1-slots-*-short.json \
  --label-regex 'slots-(\d+)' --label-format 'slots={}' --metric itl_p50_s
```

### B1-F. 지연 공식 검증 ★ 추가 측정 0회

교재 CH4가 지연 공식을 명시합니다.

```
E2E latency = TTFT + ITL × (N − 1)
```

그런데 교재는 **실제 E2E에는 "요청 대기(대량 요청 처리 시), 네트워크 지연, 라우팅 시간, 확장 오버헤드"가 더해진다**고도 말합니다. 즉 위 공식은 **모델 실행 시간만** 설명합니다. 그러면 남는 차이가 곧 **모델 밖에서 쓰인 시간**입니다.

```
잔차 = 측정된 E2E − (TTFT + ITL × (N−1))
     = 큐 대기 + 네트워크 + 라우팅
```

**B1 데이터에 이미 세 값이 다 들어 있습니다.** Prometheus도, 추가 측정도 필요 없습니다.

```bash
python3 summarize_results.py results/b1-slots-*-short.json \
  --label-regex 'slots-(\d+)' --label-format 'slots={}' --formula
```

| 판단 | 뜻 |
|---|---|
| ✅ **동시성이 오를수록 잔차가 커진다** | 슬롯을 넘어선 요청이 큐에서 기다린 시간. **B2 Grafana 그림의 클라이언트 측 증거** |
| ✅ 잔차가 동시성과 무관하게 일정 | 그건 큐가 아니라 고정 오버헤드(HTTP + port-forward) |
| ⚠️ 잔차가 음수 | ITL p50으로 곱했는데 실제 분포가 치우친 것. p50 대신 평균으로 다시 보거나, 출력 토큰 수(N) 추정이 틀린 것 |

> 이게 CH4의 *"E2E를 TTFT/ITL로 분해하라"*(모범 사례 3번)를 그대로 실행한 것입니다. 그리고 **B2에서 Grafana로 본 큐를 클라이언트 측정만으로 재확인**하는 셈이라, 두 관측이 서로를 검증합니다.

### 관측 — 파레토 곡선 ★ 추가 측정 없이 얻는 그림

위 표들은 같은 데이터의 여러 단면입니다. **처리량(x축) vs TTFT p95(y축)** 로 다시 접으면, 교재 CH3의 *cost-optimized vs latency-optimized design*이 한 장에 나옵니다.

```bash
python3 summarize_results.py results/b1-slots-*-short.json \
  --label-regex 'slots-(\d+)' --label-format 'slots={}' --pareto --ttft-slo 0.5
```

- 점 하나 = (슬롯 값, 동시성) 조합 하나
- `SLO` 열이 ✅인 행이 **충족 영역**, `파레토` 열의 ★가 **최적 경계**
- 마지막 줄이 "SLO를 지키면서 낼 수 있는 최대 처리량"을 직접 알려줍니다

"처리량을 얼마까지 살 수 있고, 그 값이 지연으로 얼마인가"가 표 하나로 답해집니다. **추가 측정은 0회**입니다.

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

### C1-2. 벤치마크 어댑터 — **이미 만들어져 있습니다**

`benchmark.py`에 `--api book` 모드가 들어가 있습니다. 요청 본문 생성과 SSE 파싱만 분기하고, 백분위·goodput·요약 로직은 그대로 재사용합니다.

```bash
python3 benchmark.py --api book --endpoint /generate_stream --base-url http://localhost:8000 ...
```

| 엔드포인트 | 요청 | 응답 | TTFT |
|---|---|---|---|
| `/basic_generate` | `{"prompt": "..."}` | `{"generated_text": "..."}` | ✗ |
| `/generate` | `{"prompts": ["..."]}` | `{"generated_texts": [...]}` | ✗ |
| `/generate_stream` | `{"prompt": "..."}` | SSE `data: {"token": " a", ...}` | ✅ |
| `/generate_vllm` | `{"prompts": ["..."]}` | `{"generated_texts": [...]}` | ✗ |

구현하며 코드에서 찾은 **함정 셋**이 이미 처리돼 있습니다. 결과를 해석할 때 알아둬야 합니다.

1. **`/generate`·`/basic_generate`는 프롬프트를 그대로 되돌려줍니다.** `ModelWorker.generate()`가 `batch_decode(outputs)`를 반환하는데 `outputs`는 `[프롬프트 토큰 + 생성 토큰]` 전체입니다. 그대로 세면 처리량이 프롬프트 길이만큼 부풀려져 `/generate_vllm`(생성분만 반환)과의 비교가 무의미해집니다. → 어댑터가 프롬프트 몫을 빼고 셉니다.
2. **비스트리밍 엔드포인트는 TTFT가 정의되지 않습니다.** TTFT 칸은 `-`입니다. 그런데 goodput 계산이 TTFT 없는 결과를 전부 SLO 위반으로 세면 0%가 나옵니다. → TTFT가 없으면 **E2E SLO만으로 판정**합니다. *(static batching에는 스트리밍이 없다 — 그 자체가 결과입니다.)*
3. **`usage`가 없어** 출력 토큰은 공백 분리로 셉니다. **네 엔드포인트가 모두 같은 방식**이라 상대 비교는 유효하지만, 절대값을 vLLM 서버(`--api openai`)의 tok/s와 직접 비교하면 안 됩니다.

> 세 함정은 `test_benchmark.py`의 `BookApiTest`가 검증합니다 (`make check`에 포함). 특히 `test_all_four_endpoints_count_the_same_way`가 네 엔드포인트의 토큰 계산이 어긋나지 않았음을 지킵니다.

### C1-3. 실행

```bash
python main.py     # 기동에 수 분 (opt-125m 로딩 + vLLM 초기화)
```

배치 크기 축을 바꿔가며 세 엔드포인트를 각각 측정합니다. `batch_size`는 상수이므로 **재기동이 필요**합니다.

```bash
cd ~/llm-model-inference/ch03/single_model_llm_serving
BENCH=~/"Hands-On LLM Serving and Optimization Study"/labs/wsl2-vllm-baseline/benchmark.py
mkdir -p results

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

### 관측 — 표 생성

라벨은 `meta.endpoint`에서 자동으로 붙습니다.

```bash
cd ~/"Hands-On LLM Serving and Optimization Study"/labs/wsl2-vllm-baseline
BOOK=~/llm-model-inference/ch03/single_model_llm_serving/results

# 배칭 4종 비교 (batch_size=4 기준) — 처리량·E2E p95
python3 summarize_results.py $BOOK/c1-bs4-*.json --metric output_tok_per_s
python3 summarize_results.py $BOOK/c1-bs4-*.json --metric e2e_p95_s

# batch_size 축 (continuous 엔드포인트만)
python3 summarize_results.py $BOOK/c1-bs*-generate_stream.json \
  --label-regex 'bs(\d+)' --label-format 'bs={}' --metric output_tok_per_s
```

**처리량 (tok/s), `batch_size=4` 기준** — 열 순서는 배칭이 정교해지는 순서입니다

| 동시성 | basic_generate (없음) | generate (static) | generate_stream (continuous) | generate_vllm (vLLM) |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 4 | | | | |
| 8 | | | | |
| 16 | | | | |
| 32 | | | | |

**E2E p95 (s)** — 같은 형식으로 하나 더

**`batch_size` 축** — `generate_stream`만

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
# k3s 복구는 C2까지 끝난 뒤에 — C2도 GPU를 쓴다
```

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

## 글로 옮길 때의 뼈대

7주 실행 계획의 **공개 글 8단계 템플릿**에 맞춘 구성입니다. 계획상 이번 주 글 제목은 `Continuous Batching이 처리량을 높이는 방식`이고, 핵심 질문은 *"Serving 시스템은 요청 증가를 어떻게 처리해야 하는가?"* 입니다.

| # | 템플릿 | 이 글에서 |
|---|---|---|
| 1 | **문제 정의** | 1주차 Cloud Run에서 c=16에 goodput이 50%로 떨어졌다. 왜? |
| 2 | **핵심 개념** | 배칭 4종을 요청 처리 흐름으로 설명 (용어 나열 금지) |
| 3 | **실습 환경** | `0-6`에서 뽑은 `results/environment.md` 그대로 |
| 4 | **실험 방법** | 고정 변수와 비교 변수 — B1은 슬롯, C1은 엔드포인트·batch_size, C2는 delay |
| 5 | **결과** | B1 표 4개 + 파레토 + 공식 검증 · B2 Grafana 그림 ★ · C1 표 3개 ★ · C2 표 2개 ★ · C3 표 3개 |
| 6 | **해석** | 배칭 4종 종합표. dynamic이 전제하는 "요청들이 같은 시간 걸린다"가 LLM에서 깨지고, continuous가 그 전제를 버려 문제를 푼 것. **C3가 그 결론을 프레임워크 밖에서 재확인** |
| 7 | **운영 관점** | 아래 별도 절 참조 — 비용·안정성·확장성·복잡도 |
| 8 | **다음 실험** | B3~B5(다음 편) + 6·7주차로 넘길 것 |

### 교재 CH4의 「성능 측정 모범 사례 9가지」 대조표

교재가 마지막 절에서 체크리스트 9개를 줍니다. 이 실습이 어디를 덮는지 미리 적어두면, 글의 6·7번 절을 쓸 때 그대로 근거가 됩니다.

| # | 교재의 모범 사례 | 이 실습에서 |
|---|---|---|
| 1 | 지연 vs 처리량 트레이드오프 파악 | ✅ **파레토 곡선** — 이 실습의 중심축 |
| 2 | 유스케이스별 "충분히 좋은" 목표 설정 | ✅ `--ttft-slo 0.5`가 그 선. SLO 충족 영역의 최대 처리량이 답 |
| 3 | **E2E를 TTFT/ITL로 분해** | ✅ **B1-F 지연 공식 검증** |
| 4 | 실제 트래픽 패턴 시뮬레이션 | △ `short`/`prefill`/`decode` 세 형태는 씀. **지터는 안 넣음** — 한계로 명시 |
| 5 | 실험의 일관성 — 한 번에 한 노브 | ✅ B1=슬롯만, C1=엔드포인트·batch_size, C2=delay만 |
| 6 | 하드웨어 활용률 모니터링 | ✅ DCGM + `0-6` 환경 기록. **전력 상한(TGP)까지** |
| 7 | 지표를 인위적으로 부풀리지 말 것 | ✅ `--unique-prefix`(prefix cache 차단) · 프롬프트 에코 보정 · 네 엔드포인트 동일 계수법 |
| 8 | 프로덕션 지속 모니터링 | ✗ 로컬 실습이라 해당 없음 |
| 9 | 테스트 스위트 주기적 재실행 | △ `make check` 71건이 도구의 회귀는 막음. **측정 자체의 반복은 `0-7` 타협안** |

**7번이 특히 이 글의 소재입니다.** 교재는 TPS를 부풀리는 두 가지 방법을 명시합니다 — ① **입력 길이를 줄이면** TTFT가 줄어 TPS가 높아 보인다 ② **배치를 키우거나 입출력 길이를 균일하게 만들면** GPU 유휴가 줄어 TPS가 개선된다.

> ②가 바로 **C2에서 재는 것**입니다. mobilenet은 모든 요청의 연산량이 정확히 같아서 ②의 극단이고, 그래서 dynamic batching이 그렇게 잘 먹힙니다. **LLM에서는 그 전제가 깨지므로 같은 방식이 안 통한다** — 이 글의 결론이 교재의 경고와 정확히 맞물립니다.

### 7번(운영 관점)에 쓸 것 — 측정에서 자연히 나옵니다

이 절을 빼먹기 쉬운데, 계획이 명시적으로 요구합니다. 다행히 실습 중에 재료가 다 나옵니다.

| 관점 | 이 실습에서 나온 재료 |
|---|---|
| **비용** | 파레토 곡선. SLO를 지키면서 낼 수 있는 최대 처리량 = GPU 한 장의 실질 수용량. "동시 사용자 N명당 GPU 몇 장"으로 환산 |
| **안정성** | `slots=64` 기동 실패(KV cache 부족), `/generate`의 동시 요청 응답 뒤섞임, 롤아웃 중 `startupProbe`가 최대 20분을 허용해야 했던 이유(모델 로딩) |
| **확장성** | 슬롯을 키워도 KV cache가 먼저 상한을 정한다(다음 편 B3의 예고). 레플리카 없이 GPU 1장에서 할 수 있는 것의 끝 |
| **복잡도** | 자작 배칭 루프 → vLLM으로 얻는 것 대비 잃는 것(설정 불투명성). Triton은 모델을 다시 export해야 했다는 진입 비용. **C3: Ray Serve가 얹는 계층의 가격이 숫자로** — 그 대신 얻는 것은 zero-downtime 롤아웃과 오토스케일링 |

> **health check·timeout·retry** 도 여기서 다루면 계획의 학습 항목이 채워집니다. 실습에서 실제로 부딪힌 것들입니다 — `startupProbe`를 20분으로 늘려야 모델 로딩을 견딘다, `redeploy`가 `/v1/models` 폴링으로 준비를 확인하지 않으면 벤치마크가 조용히 실패한다, `benchmark.py --timeout` 값이 decode 시나리오에서 부족하면 실패가 아니라 타임아웃으로 기록된다.

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
| **C2** 모델 `load`가 400/500 | `dims`에 배치 차원을 넣었거나 ONNX 배치 축이 고정 | `dims`에서 배치 차원 제거, `dynamic_axes`로 재-export. `docker logs triton` 확인 |
| **C2** 평균 배치 크기가 계속 1.00 | config 미반영 | `curl localhost:8009/v2/models/mobilenet_v2/config`로 실제 값 확인 → 안 되면 `docker restart triton` |
| **C2** `docker: permission denied` | WSL2에서 docker 그룹 미등록 | `sudo usermod -aG docker $USER` 후 셸 재시작 |
| **C2** 이미지 풀이 디스크 부족 | 17GB + 기존 이미지 | `docker system prune -a`, WSL2 가상디스크 여유 확인 |
| **C2** `--gpus all`에서 기동 실패 | WSL2 nvidia-container-toolkit 미설정 | 우선 `--gpus`를 빼고 CPU로 진행 — 절대값은 낮아지지만 **delay 축의 경향은 그대로** 나옴 |
| **C3** 워커 파드가 `Pending` | GPU를 앞 실험이 점유 | 앞 실험을 전부 내렸는지 확인 (사전 조건의 GPU 표) |
| **C3** 워커가 GPU를 못 봄 | `runtimeClassName: nvidia` 누락 | 제공 매니페스트에는 있음 — 공식 예제를 그대로 쓴 건 아닌지 확인 |
| **C3** head/worker가 메모리 부족 | WSL2 23Gi 할당 | `requests` 합이 20Gi 이하 (`test_worker_memory_fits_wsl2_allocation`이 지킴) |
| **C3** RayService가 계속 `Initializing` | 모델 다운로드 중 | `kubectl logs`로 진행 확인. B1의 PVC 캐시를 마운트하면 빨라짐 |
| **C3** 오버헤드가 음수 (Ray Serve가 더 빠름) | 통제 변수 위반 (이미지의 vLLM 버전 차이 등) | **vLLM 버전을 양쪽 다 기록**하고 글에 명시. 같은 버전이 아니면 비교가 아님 |

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

> ⚠️ **이 실험은 [B1-F(지연 공식 검증)](#b1-f-지연-공식-검증--추가-측정-0회)로 대부분 대체됐습니다.** 교재 CH4의 공식으로 클라이언트 측정만으로 같은 질문에 답할 수 있어서, Prometheus 대조는 "서버가 보는 값과 정말 일치하는가"를 교차 확인하는 보조 실험으로 남깁니다.

B2 구간(`results/b1-timeline.txt`의 시각)을 Prometheus에서 되짚어 `benchmark.py`의 `e2e_p95_s`와 비교합니다.

```promql
histogram_quantile(0.95, sum(rate(vllm:e2e_request_latency_seconds_bucket[1m])) by (le))
```

> ⚠️ **먼저 확인할 것.** vLLM의 `e2e_request_latency_seconds`는 요청이 **엔진에 도착한 시점**부터 재므로 **큐 대기를 이미 포함**할 가능성이 큽니다. 그렇다면 서버–클라이언트 차이는 큐가 아니라 HTTP + port-forward + 클라이언트 asyncio 스케줄링입니다. 0-3에서 메트릭을 뽑을 때 이 정의부터 확정하세요.

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
- 기준선 측정 · B1·B2·C1 도구: [`labs/wsl2-vllm-baseline/`](../labs/wsl2-vllm-baseline/README.md) — `benchmark.py`(`--api book` 포함) · `redeploy.sh` · `summarize_results.py`
- C2 도구: [`labs/triton-dynamic-batching/`](../labs/triton-dynamic-batching/README.md) — `export_mobilenet_onnx.py` · `make_config.py` · `triton_load.py` · `triton_metrics.py` · `sweep.sh`
- C3 도구: [`labs/rayserve-on-k8s/`](../labs/rayserve-on-k8s/README.md) — `rayservice-qwen.yaml`(B1과 동일 조건) · `mobilenet_serve.py`(`@serve.batch`)
- 2주차 예습 노트: [`knowledge/06-week2-prep.md`](../knowledge/06-week2-prep.md)
- 교재 공식 코드: `orca3/llm-model-inference` — CH3 `ch03/single_model_llm_serving`(C1) · `ch03/multi_model_serving`(C2), CH4 `ch04/KnowledgeAgent` · `ch04/{bedrock,jumpstart,dlc,dlc_customization}`
- Triton 모델 설정 문법(`max_batch_size`, `dynamic_batching`): [Model Configuration](https://github.com/triton-inference-server/server/blob/main/docs/user_guide/model_configuration.md)
