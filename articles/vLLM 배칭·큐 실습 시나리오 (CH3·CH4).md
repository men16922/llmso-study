# vLLM 배칭·큐 실습 시나리오 (CH3·CH4) — 허브

> **이 문서는 시리즈의 목차이자 종합입니다.** 실험 절차는 아래 네 문서에 나뉘어 있습니다.
> 원래 한 문서였으나 1,100줄을 넘어 쪼갰습니다.

> ▶ **다음 편**: [KV cache와 서빙 계층 실습 시나리오 (CH5·CH6)](./KV%20cache%EC%99%80%20%EC%84%9C%EB%B9%99%20%EA%B3%84%EC%B8%B5%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH5%C2%B7CH6%29.md)
> — 이 시리즈에서 이월한 **C2·C3에 B3(KV cache 상한)를 더한** 3주차 실습입니다.
> 실제로 수행한 것은 **B1·B2뿐**이고 C1·C2·C3는 시간 부족으로 이월됐습니다.

| # | 문서 | 내용 | 소요 |
|---|---|---|---|
| 00 | [실습 준비와 측정 규칙](./2%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) | 사전 조건 · 환경 기록 · 반복 규칙 · 트러블슈팅 | 20분 |
| 01 | [배치 슬롯과 큐](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md) | **B1** 슬롯 스윕 · 파레토 · 지연 공식 검증 / **B2** Grafana 큐 그림 | 80~100분 |
| 02 | [배칭을 직접 짜기](./2%EC%A3%BC%EC%B0%A8-02%20%EB%B0%B0%EC%B9%AD%EC%9D%84%20%EC%A7%81%EC%A0%91%20%EC%A7%9C%EA%B8%B0.md) | **C1** 교재 CH3 서버 — 프롬프트 축 · **이벤트 루프 블로킹** · 배칭 4단계 | 100~120분 |
| 03 | [dynamic batching과 그 위의 계층](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md) | **C2** Triton dynamic batching / **C3** RayService(CH4 도전과제) | 180~220분 |

**총 6.5~8시간·네 세션.** [01](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md)만으로도 글 한 편이 서므로 **반드시 먼저 끝내세요.**
시간이 부족해지면 잘라내는 순서는 **C3-4 → C1-C의 `bs` 축 → C2의 20ms 지점**입니다 (각각의 핵심 결론은 남습니다).

---

## 이 시리즈가 답하려는 질문

교재 CH3·CH4의 핵심 주장을 **내 GPU에서 재현**하는 것이 목적입니다.

| # | 질문 | 교재 대응 | 어디에 |
|---|---|---|---|
| **B1** | 동시 요청을 계속 늘리면 처리량은 계속 오르는가? **어디서 멈추는가?** | CH3 배칭 | [01](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md) |
| **B2** | 그 순간 서버 안에서는 무슨 일이 일어나는가? | CH3 큐·동시성 | [01](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md) |
| **C1** | 그 배칭을 **직접 짜면** 어디까지 가고, vLLM과 무엇이 다른가? | CH3 시스템 설계 (교재 코드) | [02](./2%EC%A3%BC%EC%B0%A8-02%20%EB%B0%B0%EC%B9%AD%EC%9D%84%20%EC%A7%81%EC%A0%91%20%EC%A7%9C%EA%B8%B0.md) |
| **C2** | **dynamic batching은 언제 쓰나?** 그리고 왜 LLM에는 안 맞나 | CH3 Triton (교재 코드) | [03](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md) |
| **C3** | 그 위에 **오케스트레이션 계층**을 얹으면 얼마를 내야 하나 | CH4 오픈소스 스택 · **도전과제** | [03](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md) |

**다섯 실험이 합쳐서 배칭 4종을 전부 실측하고, C3가 그 위에 계층을 하나 더 얹습니다.**
예습 노트 §1의 표가 이 시리즈에서 숫자로 채워집니다.

| 배칭 방식 | 어디서 재는가 |
|---|---|
| 배칭 없음 | C1 `/basic_generate` |
| **static** | C1 `/generate` |
| **dynamic** | **C2 Triton `dynamic_batching`** · C3 `@serve.batch` |
| **continuous** | B1·B2 (vLLM), C1 `/generate_stream`(자작)·`/generate_vllm` |

> **챕터 대응에 대한 주의.** 교재 CH3는 "배칭"을 **시스템 설계** 층위에서, CH6는 같은 주제를 **최적화** 층위(continuous batching·chunked prefill·prefix caching)에서 다룹니다. B1·B2는 두 층위에 걸쳐 있고, C1·C2가 CH3 쪽에 정확히 대응합니다. 다음 편의 B3(KV cache 상한)는 엄밀히는 **CH5** 주제입니다.

### 선행 관측 둘

**① 1주차 Cloud Run 실습** (`google/gemma-4-31B-it`, `MAX_NUM_SEQS=8`)

| 동시성 | TTFT p50 | 처리량 | goodput |
|---|---|---|---|
| 8 | 0.475s | 289.5 tok/s | 100% |
| 16 | 3.688s | 294.6 tok/s | 50% |

동시성 2배에 **처리량 +1.8%, TTFT 7.8배**. 꺾인 지점이 `max_num_seqs`의 정확히 2배였습니다.
→ [01](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md)의 가설: **"이 현상이 하드웨어와 모델을 바꿔도 슬롯 수를 따라 재현된다"**

**② 1주차 CH2 `LLM Batch Serving Basics`** (`Qwen/Qwen2.5-0.5B`, vLLM, 프롬프트 4개)

배치 처리 **1.3777s** vs 순차 처리 **2.4753s** — **2.2배**. 강의 노트가 4배가 안 되는 이유를 셋으로 설명하는데, 그중 하나가 검증 가능한 주장입니다.

> 이 예제가 GPU를 포화시킬 만큼 큰 배치(4개는 작음)가 아니라서, **배치 크기를 늘릴수록 상대적 이득은 더 커짐**

→ [02](./2%EC%A3%BC%EC%B0%A8-02%20%EB%B0%B0%EC%B9%AD%EC%9D%84%20%EC%A7%81%EC%A0%91%20%EC%A7%9C%EA%B8%B0.md)의 C1-A가 프롬프트를 1→16까지 스윕해 그 곡선을 그리고, **어디서 멈추는지(배치 포화점)** 를 찾습니다. 나머지 두 이유(**패딩**, 출력 길이 불균일)는 C1-C와 [03](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)의 결론으로 이어집니다.

---

## 종합 — 배칭 4종을 한 표에

다섯 실험이 끝나면 예습 노트 §1의 표가 실측으로 채워집니다. **이게 글의 결론 절입니다.**

| 방식 | 어디서 쟀나 | 대기 전략 | 처리량 | 지연 | 언제 쓰나 |
|---|---|---|---|---|---|
| 배칭 없음 | C1 `/basic_generate` | — | | | 디버깅·초저지연 단일 요청 |
| static | C1 `/generate` | 배치가 **찰 때까지** | | | 오프라인 배치 작업 |
| dynamic | C2 Triton · C3 `@serve.batch` | **시간 상한까지** | | | **요청당 연산량이 균일한 모델** (CV·임베딩) |
| continuous | B1·B2 vLLM, C1 `/generate_stream` | 기다리지 않음, **슬롯 단위로 교체** | | | **출력 길이가 제각각인 LLM** |

마지막 열의 대비가 이 시리즈가 답하려던 것입니다. dynamic은 **"요청들이 같은 시간 걸린다"를 전제로** 배치를 통째로 묶었다 통째로 내보냅니다. mobilenet에서는 성립합니다(C2·C3). LLM에서는 배치가 가장 긴 요청에 인질로 잡히고, 그 대가가 C1에서 본 패딩 낭비입니다. **continuous batching은 그 전제를 버려서 문제를 푼 것**입니다.

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
| 9 | 테스트 스위트 주기적 재실행 | △ `make check` 91건이 도구의 회귀는 막음. **측정 자체의 반복은 `0-7` 타협안** |

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

> ⚠️ **이 실험은 [01의 B1-F(지연 공식 검증)](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md)로 대부분 대체됐습니다.** 교재 CH4의 공식으로 클라이언트 측정만으로 같은 질문에 답할 수 있어서, Prometheus 대조는 "서버가 보는 값과 정말 일치하는가"를 교차 확인하는 보조 실험으로 남깁니다.

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
