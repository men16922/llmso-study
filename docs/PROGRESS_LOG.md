# Progress Log

Last Updated: 2026-08-23

## 2026-08-23 — 3주차 마감 통과. **4주차(CH7·CH8) 착수 — 실습 시나리오 5편 + 설계**

- **Status**: 게이트 green — 문서 3종 + labs **91건**. 인덱스 **1084 nodes / 92 docs**. 커밋 `dd8fc04` 푸시 완료(origin PRIVATE 확인 후).
- **3주차 종료**: 노션 재발행 + 과제 링크 공유 완료. **마감 08-23 09:00 통과** — 3주 연속 제출.
- ★ **4주차 축을 교재에서 찾았다.** 만들어 붙인 게 아니라 `Ch7.md:12`의 첫 질문이 그대로 축이다 — *"compute-bound vs memory-bound가 이 장 전체를 관통하는 단일 기준"*. 네 기법이 전부 조건부로만 이득이고 조건이 하나다. 그 조건이 코드 어디에 있는지는 `Ch8.md:9`가 답한다(`num_computed_tokens`). **CH7(측정)과 CH8(설명)이 한 글에 들어가는 이유가 여기서 나왔다.**
- **Changed**
  - `articles/조건부 최적화 실습 시나리오 (CH7·CH8).md` + `4주차-00`~`-04` 신규 6편(총 1,083줄). E1 추측 디코딩 / E2 chunked prefill / E3 prefix caching / E4 스케줄러 소스 해부.
  - `docs/plans/2026-08-23-week4-conditional-optimization.md` 신규.
  - `knowledge/07-aws-gpu-quota.md` 신규 — 절차·비용·정리 목록. `README.md`·`04-kickoff-checklist.md`에서 연결.
  - `docs/{AGENT_BRIEF,STATUS,NEXT_PLAN}.md` — 3주차 완료 반영, Priority 0을 4주차로 교체.
- ★ **`benchmark.py`를 읽고 설계 두 곳을 정정했다** (추측으로 계획을 세웠다가 뒤집힌 자리)
  - **E3은 도구 수정이 필요 없다.** `prefill` 시나리오의 프롬프트가 같은 문단을 **24회 반복**한 긴 문맥이고(`benchmark.py:30`), 2주차에 만든 `--unique-prefix`(`:160`)가 UUID를 붙여 **일부러 적중을 막는다**. 서버 캐시 ON/OFF와 곱하면 2×2가 그대로 나온다. 계획에 있던 `[auto]` 선행 작업을 지웠다.
  - **E2는 반대로 함정이 있었다.** 시나리오가 **순차 실행**이라(`run_scenario`가 시나리오마다 별도 executor) `--scenarios prefill,decode`로는 안 섞인다. 간섭을 재려는 실험인데 간섭이 안 생긴다. **두 프로세스 동시 실행**이 코드 수정 없는 유일한 방법이라 런북에 스크립트로 넣었다.
- **런북에 박은 함정 방지 셋**
  1. **E1에 워크로드 축 추가** — ngram은 출력이 입력을 되풀이할 때만 맞는다. `decode`만 재고 *"ngram은 효과 없다"* 고 쓰면 워크로드를 안 맞춘 것이지 기법이 나쁜 게 아니다. `decode`(반복 없음) × `prefill`(긴 문맥) 두 워크로드로 **조건이 동시성만이 아님**을 보인다.
  2. **E1-1 KV 예산 표를 먼저 채우게 했다.** draft 팔은 0.5B가 VRAM을 먹어 KV가 준다. 이 표 없이는 "추측 디코딩 탓"과 "KV가 좁아진 탓"을 구별할 수 없다.
  3. **기동 로그 + `spec_decode_*` 메트릭 두 곳 교차 확인**, 둘 다 비면 측정 금지. 3주차 `accelerator_type: null`과 같은 조용한 실패를 막는 자리.
- **AWS GPU 쿼터 — CLI로 조회해 실태를 확인했다**
  - `us-east-1`·`ap-northeast-2` 둘 다 `Running On-Demand G and VT instances = 0.0`, **신청 이력 없음**. 지금은 GPU 인스턴스를 아예 못 띄운다. 6주차(09-06) EKS가 여기 걸려 있다.
  - 목표 인스턴스(`g6e.2xlarge`·`g6.12xlarge`·`g5.xlarge`)는 세 리전 모두에 있음을 `describe-instance-type-offerings`로 확인 → 선택 기준은 가용성이 아니라 워크숍 리전. **us-east-1 / 값 32**로 확정.
  - **콘솔로 신청해야 한다** — `request-service-quota-increase`에는 사유 필드가 없고 GPU 쿼터는 사유가 승인 속도를 가른다.
- **범위 확정**: 랩톱 GPU 1장(RTX 4080 12GB)만. 외부 GPU 없음. 비용은 따져봤으나(단일 GPU 실습 약 $6, TP=4 약 $19) **이번 주 A~D는 AWS를 써도 얻는 게 없다**는 판단.
- **Verified**: `make check` green(문서 3종 + labs 91건, 이 맥에서는 `check-labs`도 됨) · `make index-md` 1084 nodes/92 docs · `git ls-files study/` 비어 있음(원문 커밋 밖) · 인덱스의 `study/` 문자열 2건은 경로 인용이지 발췌 아님 · `gh repo view` PRIVATE.
- **Blockers**: 없음. **AWS 쿼터 신청은 사용자가 콘솔에서 직접** 해야 함.
- **Next**: ① `df -h`로 3주차 잔해 이미지 정리(Triton 27.4GB + ray-llm 11.9GB) → ② `vllm --help`로 플래그·메트릭 이름 확인 → ③ **E1(추측 디코딩)**, 08-25(화) 예정.

## 2026-08-23 — 3주차 **서빙 계층 3종 가격표 완성**. 글 전면 재구성

- **Status**: 측정 완료 · 원고 재작성 완료 · 윤문/발행 진행 중. 커밋 `c35ae8d`.
- ★ **글의 주제를 바꿨다.** 이전 원고는 "병목 추적기"였는데, 실험 결과의 나열로 읽혀 목적이 서지 않았다. 사용자 지시로 **"설정 축 vs 구조 축 — 서빙 최적점을 어떤 순서로 찾는가"** 로 재구성했다. 기존 재료(계층 비용·KV 스윕·Triton dynamic batching)는 그 뼈대에 배치하거나 부록으로 내렸다.
- ★ **계층 표본을 1개에서 3개로 늘렸다.** Ray Serve만으로는 "계층은 비싸다"밖에 말할 수 없었다. Triton·KServe를 같은 저울에 올리자 **"계층마다 가격이 다르고, 가르는 기준은 요청 경로에 서 있는지"** 라는 설명이 나왔다.
- **각 계층마다 짝을 만들었다.** 계층들이 품은 vLLM이 전부 다르다(0.7.2 / 0.5.5 / 0.20.0). 계층 비용은 **같은 이미지에서 계층만 뺀 구성**과 비교해서만 쟀다. 짝이 맞았다는 확인은 기동 로그의 KV 예산이 해 줬다 — Triton 짝 `GPU blocks 15,326`, KServe 짝 `247,024 tokens / 60.31x` 일치.
- **Changed**
  - `articles/서빙 최적화, 설정부터 만지면 안 되는 이유.md` 신규(571줄). 이전 원고 `슬롯을 4배로...`를 대체.
  - `articles/figures/fig-c3-layer-cost.svg` 신규 — 세 계층의 가격 곡선. `tools/make_figures.py`에 `fig_cost()` 추가(짝 대비 %라 엔진 버전 혼입이 상쇄된다).
  - `labs/kserve-on-k8s/` 신규 — `isvc-qwen.yaml` + 짝 구성 `vllm-v0200-direct.yaml`.
  - `labs/triton-vllm-backend/` 신규 — vLLM 백엔드 모델 저장소.
  - `benchmark.py` — `--no-stream-options` 추가.
  - 측정 원본 — `c3-triton-vllm-seqs64.json` · `c3-kserve-vllm-seqs64.json` · `b-direct-v055-*` · `b-direct-v0200-*` · `metrics-{triton-vllm,kserve,direct-v055,direct-v0200}.txt`.
- **핵심 관측 (c=64, max_num_seqs=64)**
  - **KServe −2.2% / goodput 100% / `vllm:*` 66개 보존.** RawDeployment는 컨트롤 플레인이라 요청 경로에서 빠진다.
  - **Triton −12.6% / goodput 100%.** 동시성과 무관하게 평평(−3.5~−12.6%) — 요청당 고정비를 내는 프록시의 모양.
  - **Ray Serve −70.0% / goodput 19%.** 동시성에 따라 비용이 커진다 — 고정비가 아니라 처리 능력의 상한.
  - **설정 축은 구조가 정한 천장 안에서만 움직였다.** Ray Serve 위에서 설정 4종을 흔들어도 822~964 tok/s(±17%). 같은 슬롯 변경이 계층 없는 구성에서는 +139%.
- **막힌 곳 (진입 비용으로 기록)**
  - KServe 0.20.0을 k3s에 올리기까지 다섯 곳에서 막혔다 — 네임스페이스 미생성 · 기본 Serverless 모드 · 번들 런타임이 `python`을 부르는데 이미지엔 `python3`만 있음 · HF 캐시 심볼릭 링크가 subPath 마운트로 끊김 · `runtimeClassName: nvidia` 누락. 전부 매니페스트 주석에 남겼다.
  - **GPU 1장에서는 롤링 업데이트가 스스로 안 풀린다.** 새 파드가 GPU를 기다리는데 옛 파드가 쥐고 있어 교착. 옛 ReplicaSet을 0으로 내려야 진행된다.
  - ⚠️ **디스크가 꽉 차 WSL이 I/O 오류로 멈췄다.** Triton vLLM 이미지(36.3GB) 다운로드가 C: 잔여 공간을 소진시켰고, ext4.vhdx가 더 못 늘어나 k3s까지 죽었다. 이미지 정리 후 복구. **36GB급 이미지를 받기 전에 `df`로 여유를 먼저 확인할 것.**
- **측정 방법 보강**
  - Triton 24.12 프론트엔드가 `stream_options`를 거부해 `usage`를 못 받는다. 대체 계수를 **단어 분리 → 스트림 이벤트 수**로 바꿨다. 한국어에서 단어 분리는 **55% 과소 계수**라 서버 간 비교가 통째로 깨진다. 토크나이저 대조로 46 대 47토큰(오차 2%) 확인, 같은 서버 두 계수법 비교로 c≤32에서 1.3% 안 확인.
  - **c=64는 재현 측정에서 10% 가까이 흔들린다**(c≤32는 1.3% 안). 10%대 차이는 잡음과 구별하지 않기로 했다.

## 2026-08-22 — 3주차 **측정 3종 전부 완료 + 글 작성 완료**. 남은 것은 노션 발행·링크 공유

- **Status**: 게이트 green — 문서 3종 + labs **91건**. 마크다운 인덱스 975 nodes / 81 docs. 커밋 `42a3446`·`cf95673`·`b44f061`.
- **08-16 → 08-21 닷새 공백 뒤 한 세션에 몰아서 수행.** 계획 일정(08-17 C3 / 08-18 B3 / 08-19~20 C2)이 통째로 밀렸으나, 측정이 계획 추정보다 훨씬 빨라(벤치마크 1회 약 4분, 롤아웃 20~60초) 셋 다 들어갔다. **2주차처럼 범위를 줄이지는 않았다.**
- ★ **통제 변수가 깨져 있는 것을 발견해 실험 설계를 바꿨다.** `ray-llm:2.44.1`이 품은 vLLM은 **0.7.2**인데 2주차 B1 기준선은 **0.23.0**. 그냥 빼면 "계층 + 엔진 16개 마이너 버전"의 합이 나온다. **같은 ray-llm 이미지로 Ray 없이 vLLM만 띄운 구성 B**를 추가해 변수를 계층 하나로 좁혔다(추가 다운로드 0, 약 15분).
- **Changed**
  - `articles/슬롯을 4배로 늘렸는데 처리량이 그대로였다.md` 신규 — 8단계 템플릿. 세 실험을 "처리량 천장을 정하는 게 무엇인가" 한 줄기로 묶음.
  - `articles/figures/fig-c3-layer-{throughput,ttft}.svg` 신규. `tools/make_figures.py`에 3주차 계열 추가.
  - `labs/rayserve-on-k8s/vllm-v072-direct.yaml` 신규(구성 B).
  - 측정 원본 — `results/`에 `c3-*`(5) · `b3-*`(4) · `b-direct-v072-*`(3) · `metrics-{rayserve,direct-v072}.txt`, `labs/triton-dynamic-batching/results/`에 C2 16종.
  - 분석 문서 3종 — `c3-environment.md` · `c3-layer-cost.md` · `b3-kv-handcalc.md`.
- **핵심 관측**
  - **계층의 순수 가격 −32.6%**(c=16). 순진하게 B1과 빼면 −39.3%로 **7%p 과대계상**된다. 그리고 **고정 오버헤드가 아니다** — 포화 전 ~11%, 포화 후 ~31%. 경계는 엔진이 천장을 치는 동시성 16.
  - TTFT는 c=1에서 **+48ms**가 프록시 한 겹의 실비.
  - **도전과제 2의 답**: 세 노브가 `Maximum concurrency`를 14.28x~64.02x(4.5배)로 흔드는데 **처리량은 ±17%**. 저 값은 "모든 요청이 컨텍스트를 꽉 채울 때"의 입장 제한이라 짧은 프롬프트 부하에서는 물리지 않는다.
  - **CH5 공식 검증** — MHA 전제 공식은 GQA인 Qwen2.5-1.5B에서 **6배** 어긋난다(168 vs 28 KiB/token). KV 헤드(2)로 고치면 **네 설정 전부** 기동 로그와 소수점 둘째 자리까지 일치.
  - **C2**: 대조군 평균 배치 정확히 1.00. 같은 `20ms` 설정이 **동시성 1에서 37.5 inf/s(대조군의 1/9), 동시성 32에서 1,371 inf/s(2.3배)**. dynamic batching의 이득은 도착률의 함수.
  - **관측성 손실** — Ray Serve 아래에서 `:8000/metrics`가 404이고 `vllm:*`가 **0개**(구성 B는 15개). 같은 엔진이므로 **계층 탓**. 2주차의 서버 측 교차검증이 이 환경에서는 불가능하다.
- **2주차 미해결 관측 일부 규명** — `Maximum concurrency` 변동의 메커니즘을 잡았다. `max_num_seqs`를 키우면 **활성화 피크가 커져 KV 예산을 갉아먹는다**(0.26→0.48 GiB, KV 7.00→6.79 GiB). KV 예산은 정적 공식이 아니라 **기동 시 프로파일링 결과**. 다만 이번 변동은 3%라 2주차의 2배(59.50↔28.77)는 여전히 미확인.
- **고친 결함 3건**
  1. `rayservice-qwen.yaml`의 **`accelerator_type: null`** — Ray 2.44.1 `LLMConfig` 검증이 거부해 Serve 앱 배포가 통째로 실패. 파드는 정상으로 보이고 `NUM SERVE ENDPOINTS`만 비어 증상이 조용하다. 원인은 Serve 대시보드 API에만 남는다. **필드를 생략해야 한다.** 매니페스트가 작성 후 실제 배포된 적이 없어 잠복해 있었다.
  2. `triton_load.py`가 입력을 **`(3,224,224)`** 로 만들어 300건 전량 실패. `config.pbtxt`의 `dims`는 샘플 단위지만 클라이언트 텐서는 `(N,3,224,224)`여야 한다. 오프라인 테스트 19건은 mock이라 못 잡는 자리.
  3. `make_figures.py`의 `fig_log`가 라벨 분리용 `rank`를 계산해두고 **쓰지 않아** 끝점이 가까우면 라벨이 겹쳤다(9.3px). 최소 간격 15px 강제. 2주차 그림은 산출물 변화 없음.
- **환경 메모**
  - Triton 이미지 크기 불일치 해소 — **9.63GB는 다운로드, 27.4GB가 디스크**. 계획서의 `~17GB`가 틀린 값.
  - WSL `python3`(3.14)에 pip이 없어 numpy·tritonclient·torch를 넣을 수 없다. **C2 스윕은 Triton 컨테이너 안에서, ONNX export는 k3s에 받아둔 ray-llm 이미지 파드로** 돌렸다(추가 다운로드 0).
  - 2주차 `huggingface-cache` PVC는 재사용 불가 — `vllm-openai`는 root, `ray-llm`은 uid 1000(`ray`)이라 `PermissionError`.
  - **백그라운드 태스크 강제 종료는 이번 세션에서 겪지 않았다.** WSL 안에서 `setsid`로 분리한 프로세스(keeper·이미지 풀·벤치마크)는 별도 `wsl.exe` 호출을 넘어 살아남았다.
  - Windows에서 `PYTHONIOENCODING=utf-8 py -3`로 게이트·테스트가 전부 돈다 (`Makefile`의 `PY` 항목 실마리).
- **Verified**: `check_docs.py` green · `--only md` 975 nodes/81 docs · `pytest` 91 passed · 그림 2종 headless Chrome 렌더로 눈 확인 · 롤아웃마다 `/v1/models`와 기동 로그 양쪽으로 반영 확인.
- **윤문·발행** (같은 날) — humanize-korean heavy 경로(진단→겨냥 윤문→finalize). 진단이 *논증 자체는 사람 글*로 보고 지배 패턴을 4개로 좁힘. 볼드 62→38 · 대구 17→7 · 연결어미 뒤 쉼표 24→1 · 대시 15→9. **수치 831개·헤딩 48개 전원 보존**(자체 게이트), 변경률 0.51%, finalize fidelity 위반 0건.
  - ⚠️ `verify_gates.py`의 P3 golden FAIL 1건은 **오탐**. 이 글에 각주가 없다 — `1)` 패턴은 `(c=1)`·`(§5-1)`뿐. finalizer도 독립 확인.
  - **노션 발행 완료** — https://app.notion.com/p/3c44c2420ac48157aaebe78f971e05c9. 표 21개 변환, 그림 2장 업로드, 발행 후 fetch로 전 수치 대조 확인.
- **Blockers**: 없음. **과제 링크 공유만 남음** (마감 08-23 09:00, 사용자가 직접 공유).
- **Next**: 링크 공유 → 4주차 예습 노트.

## 2026-08-16 — 2주차 마감 통과. **3주차 방향 확정 + 실습 문서 5편 작성**

- **Status**: 게이트 green (문서 3종). 마크다운 인덱스 910 nodes / 76 docs. 측정은 아직 없음(문서 작업만).
- **2주차 종료**: 글 2편 노션 발행 + 링크 공유 완료 (마감 08-16 09:00 통과).
- **`study/` 복귀** — 체크아웃에 `Ch1~Ch6.md` + `LLM기초.md`(9,592줄)가 다시 생겼습니다. 이번 세션의 판단 근거가 대부분 여기서 나왔습니다. 인덱스·git 양쪽에서 제외된 것을 재확인(`grep '"study/'` 0건, `.gitignore:25`).
- **3주차 방향 확정 — 이월한 C3(Ray Serve) + C2(Triton)로 수행**
  - 근거를 노션 원문에서 확보: **Ray Serve는 CH4 공식 도전과제**(`Ch4.md:1381`), **Triton dynamic batching은 CH6 본문**(`Ch6.md:140` — vLLM엔 dynamic batching 모드가 없어 이 절은 vLLM으로 실측 불가), 과제 규칙도 *"혹은 LLM 관련 내용(혹은 도전과제)"* 로 열려 있음(`Ch6.md:1039`).
  - **공식 도전과제 4개를 `Ch6.md:1047`에서 발견** — 그중 2번(`max batch size`·`max model length`·`max number of tokens` 변경 비교)이 이월해둔 B3와 같은 실험.
  - ★ **`rayservice-qwen.yaml`의 `serveConfigV2 → engine_kwargs`에 그 세 노브가 그대로 노출**돼 있어, 도전과제 2를 C3 환경 위에서 수행하기로. RayService는 변경을 zero-downtime으로 갈아끼우므로 2주차의 `kubectl set env` 사고(구버전이 떠 있어 무시)가 구조적으로 없음.
- **Changed**
  - `articles/` **5편 신규**(990줄) — 허브 `KV cache와 서빙 계층 실습 시나리오 (CH5·CH6)` + `3주차-00`(준비·측정 규칙) / `-01`(C3) / `-02`(B3) / `-03`(C2). **문서 번호 = 실행 순서**로 배치(안전판 우선).
  - `docs/plans/2026-08-16-week3-triton-rayserve.md` 신규 — 상세 설계·잘라내기 순서·일정.
  - `docs/NEXT_PLAN.md` 172줄 → 89줄(예산 120). 상세는 plans로 분리, 여기엔 체크리스트만.
  - `2주차-03`과 2주차 허브에 3주차 시리즈 포인터 추가(원설계는 그대로 두고 실행 런북만 분리).
- **Verified**
  - `python3 scripts/check_docs.py` → `✓ links / ✓ index / ✓ tools` (신규 문서의 한글 URL 인코딩 링크 포함).
  - `build_pageindex.py --only md` → 910 nodes / 76 docs.
  - `study/`가 인덱스에 유입되지 않음(0건), `git check-ignore`로 무시 확인.
  - ⚠️ **labs 테스트는 안 돌렸습니다** — 이 머신 `make check-labs` 미동작(WSL python3.14에 pip 없음). 이번 변경은 문서뿐이라 영향 없음.
- **고친 인식 오류 2건** (원문 대조로 정정)
  1. *"Triton은 CH3라 CH5 주차와 어긋난다"* → **CH6에 「Dynamic Batching in Online Inference」 절이 통째로 있음.** 오히려 이번 주 주제.
  2. 교재 CH5의 KV 공식은 `2 × 층수 × **어텐션 헤드 수** × head_dim × 정밀도`로 **MHA 전제**. Qwen2.5-1.5B는 GQA라 그대로 쓰면 안 맞음 — 교재가 *"이후 장에서 MQA·GQA·MLA 소개"* 라 예고한 그 장이 **이번 주 CH6**. 이 어긋남을 3주차 글의 핵심 절로 배치.
- **Blockers**: 없음. 측정 미시작.
- **Next**: 이미지 풀 → C3 배포·계층 오버헤드(08-17) → `engine_kwargs` 스윕(08-18) → C2(08-19~20) → 글(08-21~22). 마감 **08-23 09:00**.

## 2026-08-15 (2) — 2주차 과제 완성. **글 2편 시리즈로 노션 발행**

- **Status**: 게이트 green (문서 3종). 커밋 `82d8ec2`~`d84f787` 9건, 미푸시.
- **제출 형태 확정**: 2주차 과제를 **2편 시리즈**로 낸다. ① `WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기`(미제출이던 환경 구축 글) ② `Continuous Batching이 처리량을 높이는 방식`. 두 글이 양방향으로 이어지도록 1편 끝에 「다음 편」, 2편 앞에 「이 글의 배경」을 넣었다.
- **Changed**
  - **본문 전면 재작성** — 사용자가 노션에서 다시 쓴 판이 개념·용어 면에서 더 정확해 그것을 뼈대로 삼았다. 특히 `Maximum concurrency`가 hard limit이 아니라 `max-model-len` 기준 **추정치**라는 점, `max-num-seqs`가 iteration당 최대 sequence 수라는 점, SLO 충족률과 vLLM `request_goodput(req/s)`의 구분을 반영. 대신 그 판에서 빠져 있던 **그래프 3장·증빙 캡처 3장·전체 데이터 표·ITL·파레토·지연 공식·재현 절차를 복원**하되 분량 큰 것은 접기로 넣었다. 용어표(0절)와 「이 글의 배경」 신규.
  - **윤문** — `/humanize` standard 경로(진단→윤문). 이전 윤문의 과윤문 흔적(같은 문장 5-4·5-7 중복, `궤적 그대로다`→`같다`)을 되돌리고, 문장 통째 볼드 27건·"A가 아니라 B" 대구 20+→7 정리. 이후 남은 구어·단정 표현 29건을 추가로 통일.
  - **도구 2종 신규** — `tools/make_figures.py`(결과 JSON → SVG, 표준 라이브러리만), `tools/md_to_notion.py`(파이프 표→노션 XML, 토글 헤딩, 인용 `<br>` 병합, 경로 치환).
  - **노션 발행** — 이미지 6장 업로드 후 2편 전체 반영, 1편에 다음 편 링크 추가.
- **Verified**
  - `check_docs.py` green (목차 앵커 14개 포함). 마크다운 인덱스 818 nodes / 69 docs.
  - 윤문 게이트를 직접 작성해 판정 — 변경률 1.90%, **수치 295개 전원 동일**, 헤딩 텍스트 동일. 플러그인 2.1.0에 `verify_gates.py`가 없어 대체했다.
  - 그래프 3종을 headless Chrome으로 렌더해 **눈으로 확인** — 라벨 충돌·넘침 없음. 색은 검증기로 light/dark 색각 분리도 통과 확인.
  - 노션 페이지 fetch로 이미지 6장이 S3 URL로 해석된 것과 토글 동작 확인.
- **고친 결함**
  - 부록 재현 스크립트의 `for` 루프 밖으로 decode가 빠지고 `done`이 두 개이던 버그(직전 세션에서 유입).
  - 노션 렌더 결함 — 번호 목록이 중간 표 때문에 4·5·6 → 1·2·3으로 리셋. 명시 번호 문단으로 교체.
  - 그래프·본문에 남아 있던 내부 실험 코드(`B1`/`B2`) 표기를 절 번호로 정리.
- **Blockers**: 없음. 제출 링크 공유만 남음(마감 2026-08-16 09:00).
- **Next**: 과제 링크 2개 공유 → 3주차(CH5·CH6) 예습 노트.

## 2026-08-15 — 2주차 세션 1(B1·B2) 실측 완료 + 과제 글 작성. **첫 실제 GPU 실행**

- **Status**: 게이트 green — 문서 3종 + labs **91건**(56+6+19+10). 미커밋.
- **범위 결정**: 08-09 이후 6일간 측정이 없었고 마감(08-16 09:00)까지 하루가 안 남아 **세션 1만 수행하고 C1·C2·C3는 통째 이월**. 근거는 시나리오 자체의 안전판(*"B1·B2만으로도 글 한 편이 선다"*).
- **Changed**
  - **B1·B2 전 구간 실측** (모델 `Qwen2.5-1.5B-Instruct`, vLLM v0.23.0, RTX 4080 Laptop 12GB). `short`·`decode` × slots 1/16/64 + B2 큐 부하. 결과 8종을 `labs/wsl2-vllm-baseline/results/`에 커밋.
  - `articles/Continuous Batching이 처리량을 높이는 방식.md` 신규 — 8단계 템플릿 전부 + 한계 6개 + 재현 부록.
  - `.gitattributes` 신규(`*.sh text eol=lf`), `articles/2주차-00`에 함정 3건을 트러블슈팅·본문으로 반영.
  - **증빙 보강** — 계획의 산출물 중 빠져 있던 *"concurrency 대비 latency·throughput 그래프"*를 채움. `tools/make_figures.py` 신규(표준 라이브러리만, matplotlib 미도입)가 SVG 3종 생성. 색은 검증된 카테고리 슬롯 1~3, light/dark 양쪽 색각 검증 통과. 렌더해서 눈으로 확인 후 라벨 충돌·넘침 3건 수정. 서버 측 원본을 `results/b2-prometheus.{json,txt}`로 내보내고 글에 5-9 「측정 증거」 절 추가.
- **Verified**
  - `python3 scripts/check_docs.py` → `✓ links / ✓ index / ✓ tools`. `--only md` 인덱스 갱신(802 nodes, 68 docs).
  - labs 테스트 4개 디렉터리 **91 passed**. 단 **이 머신에는 pytest·pip이 없어** Windows Python 3.12에 `pytest`·`pyyaml`을 설치해서 돌렸음(WSL python3.14는 pip 자체가 없음).
  - 클라이언트 측정과 서버 측 Prometheus가 **교차 검증됨** — `num_requests_running`이 16에서 천장, 초과분 48이 `num_requests_waiting`으로.
- **핵심 관측**
  - 슬롯만 1 → 64로 바꿔 **113 → 2,627 tok/s (23배)**, `decode`는 115 → 2,852 tok/s (24.8배).
  - **goodput이 조용히 무너진다** — B2 c=64에서 200/200 성공인데 goodput 8%. 부하 4배 올려 처리량 +0.3%, TTFT 139배.
  - **비용은 TTFT로만 청구** — 같은 구간 TTFT 14배, ITL 3%.
  - **지연 공식 잔차는 큐가 아니었다** — 큐 대기가 이미 TTFT에 포함돼 잔차는 고정 오버헤드(+0.05~0.10s)로 일정. p50 ITL로 곱하면 부호가 뒤집히는 구간이 생김.
- **고친 저장소 결함 3건** (전부 측정을 막던 것)
  1. `.sh`가 **CRLF로 체크아웃** → `source redeploy.sh`가 함수 정의에 실패하는데 조용히 성공한 척함. `sweep.sh`(C2)도 동일. → `.gitattributes`
  2. 클러스터에 **13일 전 구버전 배포**가 떠 있어 `kubectl set env`가 무시됨(args가 env 미참조). 준비 절차 `0-4`의 `kubectl apply`가 필수임을 확인.
  3. 시나리오 `0-3`의 메트릭 추출 정규식 `[a-z_]+`가 **숫자에서 잘려** `vllm:e2e_...`를 `vllm:e`로 만듦. → `[a-z0-9_]+`
- **Blockers**
  - **Grafana 스크린샷 미확보** — 사람이 찍어야 함. B2 구간(`02:15:47~02:21:49 UTC`) 데이터는 Prometheus에 남아 있어 **사후 조회 가능**하며, 글에는 수치·궤적으로 대체해 넣었음.
  - 이 환경에서 **백그라운드 태스크가 반복적으로 강제 종료**됨. keeper가 죽자 WSL 유휴 poweroff로 파드가 `Completed`/`Unknown`이 되어 측정이 한 번 중단됐음. 재개해서 전량 확보. 이후 포그라운드 실행으로 전환.
  - `study/`(노션 원문 사본)가 이 체크아웃에 **없음** — `AGENT_BRIEF`의 기술과 불일치.
- **Next**: 글 최종 검토 후 제출(마감 08-16 09:00). 3주차(CH5·CH6) 예습 노트. C1·C2·C3는 다음 편.

최근 증분 요약만 유지합니다 (최신 3~5건, ≤120줄). 오래된 항목은 `/tidy-docs`로 `docs/archive/progress-YYYY-MM.md`에 보관합니다.

최근 증분 요약만 유지합니다 (최신 3~5건, ≤120줄). 오래된 항목은 [`docs/archive/progress-2026-08.md`](./archive/progress-2026-08.md)에 있습니다.
