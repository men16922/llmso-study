# Progress Log — 2026-08 아카이브

`docs/PROGRESS_LOG.md`가 컨텍스트 예산(120줄)을 넘어 옮겨둔 오래된 항목입니다. 최신 증분은 그쪽에 있습니다.

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

## 2026-08-09 (2) — 2주차 실습 도구 일체 완성, 시나리오를 B1·B2·C1·C2·C3로 확장

- **Status**: 게이트 green (`make check` = 문서 3종 + labs 테스트 **86건**, 오프라인·약 2초). 커밋·푸시 완료 (`6a01681`·`011379c`·`eae3406`).
- **Changed**
  - **근거 확보**: 교재 공식 저장소(`orca3/llm-model-inference`) ch03·ch04를 직접 읽고, 노션 CH4 원문(`study/`, gitignore)과 본인의 「7주 실행 계획」을 대조. 시나리오의 챕터 태그 오류 2건과 B4 판단 기준 오류를 정정.
  - **실습 도구 완성** — 노트북에서는 실행·기록만 하면 됨:
    - `benchmark.py --api book` (교재 ch03 서버 어댑터) + ITL/TPOT 지표
    - `summarize_results.py` — `--all` / `--pareto` / `--formula` / `--delta`
    - `redeploy.sh` — 롤아웃 실패 감지 · `/v1/models` 폴링 · 타임라인 기록
    - `labs/triton-dynamic-batching/` 5종 + `labs/rayserve-on-k8s/` 2종
  - **시나리오 확장**: C1(교재 자작 서버 배칭 4단계) · C2(Triton dynamic batching) · C3(RayService, CH4 도전과제) 추가. B3~B5는 다음 편으로 이월.
  - `study/`(멤버 전용 노션 원문)를 `.gitignore` + `MD_SKIP_DIRS` 양쪽에서 제외 — 인덱스가 커밋되므로 발췌가 들어가면 사실상 저장소 전재.
- **Verified**
  - `make check` exit 0. 51(wsl2) + 6(cloudrun) + 19(triton) + 10(rayserve) = 86건.
  - `summarize_results.py`를 합성 B1 데이터로 종단 실행 — 표 3종·파레토·공식 검증 모두 기대대로 출력.
  - 코드 읽기로 찾은 함정 3개가 테스트로 고정됨: 프롬프트 에코 보정 · TTFT 없는 엔드포인트의 goodput 판정 · 네 엔드포인트 동일 계수법.
  - `ManifestTest`가 C3의 통제 변수 4개(모델·max_model_len·gpu_memory_utilization·max_num_seqs)를 B1과 동일하게 감시.
  - **미검증**: 실제 GPU 실행은 한 번도 안 함(도구는 전부 mock·순수 로직 테스트). vLLM v0.23.0 메트릭 이름, Triton 이미지 동작, KubeRay 배포는 전부 노트북에서 확인 필요.
- **Blockers**: 없음. 단 `study/Ch3.md`가 0바이트 — 재복사 필요.
- **Next**: WSL2에서 세션 1(B1·B2) 실행. 시작 시 Triton·ray-llm 이미지 풀과 C1 venv 설치를 백그라운드로.

## 2026-08-09 — 하네스 설치 + 2주차 예습 노트 + CH3·CH4 실습 시나리오

- **Status**: 게이트 green (`make check` = 문서 3종 + labs 테스트 6건, 약 2초). 전부 미커밋.
- **Changed**
  - 하네스 설치: `harness-init.sh` 스캐폴딩 후 게이트를 이 저장소에 맞게 정의. `scripts/check_docs.py`(링크·인덱스 스키마·파이썬 문법) 신규 + `Makefile`(check / check-labs / index-md / overnight 타겟).
  - 권한 경계를 저장소 위험에 맞춰 조정 — 구독 사용량(`enrich_summaries`·`pageindex_claude`), 한국어 요약 파괴(`build_pageindex` 직접 실행), 비용(gcloud/aws/kubectl/docker/labs 벤치), 유출(push/gh/curl/MCP)을 deny.
  - `knowledge/06-week2-prep.md` 신규 (286줄) — PDF p.29~32·37~40·107~118·185~195·206~209를 직접 추출해 작성. 교재의 Triton·RAG·에이전틱은 이 PDF에 없어 "어긋날 수 있는 지점" 표로 명시.
  - `articles/vLLM 배칭·큐 실습 시나리오 (CH3·CH4).md` 신규 (471줄) — B1~B5 실험. 각 실험에 가설·명령·채울 표·판단 기준.
  - 랩 보강: `vllm-baseline.yaml`의 `MAX_NUM_SEQS`/`MAX_MODEL_LEN`/`GPU_MEMORY_UTILIZATION`을 env로 분리(→ `kubectl set env`로 스윕 가능), `benchmark.py`에 `--unique-prefix`(prefix cache 오염 차단) + 테스트 2건.
  - 아티클 이름 변경으로 끊긴 내부 링크 4곳 복구 (게이트가 검출).
- **Verified**
  - `make check` exit 0. `python3 -m pytest` — wsl2-vllm-baseline 6건, cloudrun 6건 통과.
  - `check_docs.py` 역방향 테스트: 깨진 링크·앵커에 exit 1, 코드 펜스 안 예시는 무시 확인.
  - `harness-init.sh --check` OK, `make overnight-where`가 핀 고정한 `.claude` 설치를 가리킴.
  - `benchmark.py --help`에 `--unique-prefix` 노출, 기본값이면 프롬프트가 원본 그대로임을 확인.
  - **미검증**: 시나리오의 PromQL과 vLLM 메트릭 이름(v0.23.0 실물 대조 안 함) — 시나리오 0-3에 확인 절차를 넣어둠. 무인 루프는 한 번도 돌리지 않음.
- **Blockers**: 없음.
- **Next**: 미커밋분 정리 후 커밋. WSL2 머신에서 시나리오 B1~B4 실행 → 결과로 2주차 과제 글 작성 (마감 2026-08-16 09:00).

## 2026-08-30 — 5주차(CH9·CH10) 계획 수립 + 노션 원문 대조

- **Status**: 게이트 green — `make check`(문서 3종 + labs) 통과. ★ **이 세션은 macOS라 `make`가 그대로 돕니다**(08-29 Windows 셸에서 GNU make가 없어 분리 실행했던 문제는 머신 차이였음).
- **노션 CH10 접근** — 첫 탭이 다른 계정(`yeongsigchoe7@`) 컨텍스트를 잡아 "사용 권한 없음"이 떴고, **새 탭에서 다시 열자 men16922 세션으로 정상 로드**됐습니다. MCP 노션 커넥션(`최병민 HQ`)으로는 `gasidaseo` 워크스페이스가 안 잡혀 404 — **원문 열람은 브라우저 경로만 됩니다.**
- **`study/Ch10.md`가 라이브 페이지의 완전한 사본임을 대조로 확인했습니다.** 토글 전체 펼침 후 가상 스크롤 25회로 본문을 모아(590 고유 라인) 로컬 파일과 정규화 키 해시로 대조 → **라이브에만 있고 로컬에 없는 라인 0건.** 섹션 8개 구조도 1:1. **파일은 수정하지 않았습니다.**
  - 대조 과정에서 정규화 버그 2회(리스트 마커 `-` 미제거 → 316건 오탐, 볼드 `**` → 158건 오탐). 최종 판정은 마크다운 기호·목록 마커·공백 제거 후 부분 문자열 매칭으로 확정.
- **5주차 계획 수립** — 축은 `study/Ch9.md:10`의 첫 질문(*"처리량이 올랐다는 건 GPU가 더 빨리 계산해서인가, 덜 다시 계산해서인가"*). 4주차가 **조건**(언제 이득)이었다면 5주차는 **인과**(왜 이득)를 커널 타임라인에서 귀속. 실험 F1(양자화·주인공) / F2(3계층 프로파일링) / F3(복제2 + LiteLLM) / F4(Multi-LoRA·선택).
- **Changed**
  - `docs/plans/2026-08-30-week5-attribution.md` 신규 — 축·근거·한계·통제 변수·실험 4종·잘라내기 순서·시간표·중단 기준·산출물 목록.
  - `docs/NEXT_PLAN.md` — Priority 0을 5주차로 교체(⓪ 선행 4 + 측정 ①~⑦ 체크리스트), 4주차는 **Priority 5 · 마감 경과·공유 확인 필요**로 강등.
- **Verified**: `make check-docs` green(links·index·tools) · `make check` green(docs + labs). 노션 대조는 위 서술대로 스크립트 판정.
- **Blockers**: ⚠️ **4주차 ⑦ 링크 공유 — 마감(08-30 09:00)이 14시간 지났고 공유 여부 미확인.** 미공유 1회 = 제명. AWS GPU 쿼터는 여전히 `0`(6주차 EKS가 걸려 이번 주가 사실상 마감).
- **Next**: 사용자에게 4주차 제출 확인 → 08-31(월) 밤 ⓪ 선행(Nsight 권한 · 양자화 팔 확보).

## 2026-08-29 — 4주차 글을 명료화하고 humanize A로 노션 재발행

- **Status**: 로컬·노션 갱신 완료. 문서 검사 3종 + labs 106건 green. 인덱스 1162 nodes / 96 docs.
- **Changed**: 제목을 `워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식`으로 중립화하고, 도입·결과 해석·운영 절을 질문→측정→해석→운영 판단 흐름으로 재작성.
- **Humanize**: `_workspace/2026-08-29-001/final.md` — 변경률 24.14%, S1 0건, S2 잔존 2개 범주, 자체검증 6/6, **A**.
- **Notion**: 대상 페이지의 기존 이미지·콜아웃·토글을 보존한 채 제목과 본문만 갱신. 되읽기 결과 이미지 5·콜아웃 6·토글 3·표 12·코드 블록 7·TOC 1.
- **Verified**: `py -3 scripts/check_docs.py` green · labs 106건 green · 이전 발행본↔최종 노션 수치 멀티셋 불일치 0 · 로컬↔노션 실질 본문 100% 일치(서식 토큰 제외). `make check`는 이 Windows 셸에 GNU make가 없어 직접 실행하지 못하고 같은 명령을 분리 실행.
- **Blockers**: ⑦ 과제 링크 공유는 사용자 몫. 마감 2026-08-30 09:00.
- **Next**: 사용자 제출 → 커밋 정리 → 5주차 예습.

## 2026-08-29 — 4주차 글을 **3주차 노션 발행본 형태로 재구성** + 실습 인증샷 4장

- **Status**: 게이트 green — 문서 3종 + labs 106건. 인덱스 **1159 nodes / 96 docs**(`--only md` 재생성, Inference Engineering의 `llm-claude-code-korean` 보존 확인). 커밋 없음(변경 12 + 신규 55).
- ★ **로컬 원고와 노션 발행본이 다른 문서였다는 걸 3주차 대조로 발견했다.** 사용자가 링크를 주며 "이런 구조 맞냐"고 물어 3주차 발행본을 뜯어보니, 발행 때 **다섯 가지 변환**을 거치고 있었다 — ①요약을 callout 3불릿로 압축 ②헤딩을 em-dash 부제형 → 평서 발견문 ③환경·한계·부록을 토글로 ④회고형 `결론` 장을 삭제하고 지침형 마지막 장에 흡수 ⑤제목을 단정형 → 중립 기술형. 4주차 글엔 하나도 안 들어가 있었다.
- **그 다섯 가지를 4주차 글에 적용했다** (제목만 제외 — 지시 없어 유지).
  - `## 7. 그래서 켜는 순서는 이렇게` + `## 한계` + `## 결론` → **`## 7. 실험의 한계`(토글) → `## 8. 워크로드를 먼저 보고 순서대로 켠다`(8-1~8-5)**. 글이 회고가 아니라 **행동으로 끝난다.**
  - *"부하가 늘면 방향이 뒤집힌다"* 가 요약·§7·결론 **세 번** 나오던 것을 8-4 한 곳으로.
  - `### 실험 환경` 토글 신설(GPU·커널 `6.18.33.1`·k3s `v1.36.2+k3s1` 전부 이번 세션 실측).
  - 표현: em-dash 40→24 · ★ 2→0 · 이탤릭 인용 7→0 · "팔"(arm) 16→0("구성").
  - **재조립은 블록 이동으로만** 했다(표·수치 재타이핑 금지). 수치 멀티셋·표 행·코드블록·이미지·링크를 전수 대조해 **손실 0** 확인.
- **실습 인증 스크린샷 4장 신규** (`proof-w4-01~04`). E1(ngram)·E2(mnbt=512) 두 구성으로 서버를 다시 띄워 찍었다.
  - ★ **재현이 소수점까지 맞았다** — ngram `235,440 / 57.48x`, mnbt512 `244,000 / 59.57x`로 08-27과 **완전 동일**. KV 예산은 기동 시 프로파일링 결과라 2주차엔 같은 설정에서 59.50x↔28.77x로 갈렸던 값이다. 부록 C에 「재현이 되는지 실제로 확인했습니다」로 추가.
  - 라이브 지표: spec_decode 수용 **375/610 = 61.5%**, 위치별 채택 113/80/62/60/60(뒤로 갈수록 감쇠). prefix cache **4,800/7,222 = 66.5%**.
- **자체 오독 1건(수정 없음)**: `mnbt=512`인데 2,405토큰 프리필이 한 스텝에 들어간 것으로 보여 청킹 미동작을 의심했으나, `vllm:iteration_tokens_total`이 **스텝당 스케줄 토큰이 아니라 프리필 완료 시점의 `computed`를 통째로 기록**하는 지표였다(`loggers.py:1163` + `stats.py:270`). 청킹은 정상이고 글에 고칠 것 없음. 이 지표는 token_budget 증거로 쓸 수 없다.
- **윤문**: 부록 D(08-28 신규분, 미처리였음)를 humanize light → 게이트 WARN → finalize 승급. `accept`·본문 보정 0건, 실제 변경은 **쉼표 2개 삭제**(변경률 0.12%·등급 A). 잔존 쉼표 3곳은 통사 기능 확인 후 보존.
- **Changed**
  - `articles/켜면 이득인 최적화는 없다.md` — 전면 재구성(454줄). 스크린샷 4장 + 캡션 배치.
  - `articles/screenshots/proof-w4-01~04.jpg` 신규 · `labs/wsl2-vllm-baseline/results/w4proof-e{1,2}-*-startup.txt` 신규.
  - `index/knowledge_structure.json` 재생성 · `_workspace/2026-08-28-001/`(humanize 산출물).
  - **노션 발행본 전면 교체**(같은 URL) — 이미지 5장 재업로드, 토글 3·콜아웃 6·TOC 블록.
- **Verified**: `make check` 상당(문서 3종 + pytest 106건) green · 노션 되읽기로 토글 3/콜아웃 6/이미지 5/표 11/수치 전수 대조 — 손실 0 · 배포 원복(`replicas=0`·`EXTRA_ARGS=''`·`MAX_NUM_SEQS=16`), GPU 0 MiB, port-forward 정리.
- **Blockers**: **⑦ 과제 링크 공유는 사용자 몫**(마감 **08-30 09:00**). 미커밋 67건.
- **Next**: 커밋 정리 · 사용자 제출 · 5주차 예습.

## 2026-08-28 — draft 팔 측정으로 **글의 마지막 공백을 메움** + 발행본 정정

- **Status**: 게이트 green — 문서 3종 + labs 106건. 인덱스 1149 nodes / 96 docs. **커밋 없음**(작업 트리에 변경 11 + 신규 48).
- ★ **E1 draft-0.5B 팔을 쟀고, "비교 성립 안 함"이 곧 결과였다.** KV 예산 **140,832 tokens / 34.38x = vanilla 대비 −42.2%**(ngram은 −3.4%). 12GB에 1.5B+0.5B를 같이 올리면 예산의 42%가 사라진다. 수용률 40.1%.
- ★ **이 팔이 글의 축을 한 번 더 증명했다.** 같은 "추측 디코딩"인데 예산에 정반대로 작용한다 — **ngram은 예산을 안 뺏어** `prefill` c=1에서 +199.3%인데, **draft 모델은 예산을 42% 줄이고 시작해** 같은 지점에서 −4.1%. 어느 워크로드·어느 동시성에서도 이득이 없었다. *"예산이 남는가"가 조건이라면 예산을 먹고 들어가는 방식은 출발부터 진다.*
- **운영 신호**: `decode` c=64에서 **goodput 0.0%**(e2e p95 45.6초, SLO 30초 초과). 처리량 −84.9%보다 이쪽이 무겁다. vanilla·ngram은 같은 지점에서 100%였다.
- **Changed**
  - `articles/켜면 이득인 최적화는 없다.md` — **부록 D** 신규 + 목차 반영, 한계 #4를 실측 근거로 교체(*"안 쟀습니다"* → *"같은 저울에 못 올렸습니다"*).
  - `labs/wsl2-vllm-baseline/results/` — `e1-draft.json` · `e1-draft-startup.txt` · `metrics-e1-draft.txt` · `e1-draft-metrics-{before,after}.txt`. `e-analysis.md`에 §1-4 추가.
  - **노션 페이지 갱신**(같은 URL) — 부록 D + 한계 #4 정정. <https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234>
  - `docs/{STATUS,NEXT_PLAN}.md` 갱신.
- **Verified**: `make check` green · 노션 갱신을 서브에이전트로 **4/4 항목 대조**(부록 D 헤딩·표 2개·한계 #4 교체·섹션 순서와 잔존) — 사라진 섹션 없음 · GPU 반환 0 MiB, 배포 `EXTRA_ARGS=''`·replicas=0으로 원복.
- **자체 오류 1건**: 노션 갱신 시 손으로 유니코드 이스케이프를 만들다 `다뤘는데`를 `다뤄는데`로 보냈다. 검증 에이전트가 잡아 정정. **로컬 원본은 정상이었고 노션만 틀렸다** — 이스케이프를 손으로 짜는 경로에 이 위험이 있다.
- **Blockers**: **⑦ 과제 제출은 사용자 몫**(직접 하겠다고 확정). 제출표가 스터디 멤버 전용 워크스페이스라 이 노션 연결(`get-teams` = `최병민 HQ` 하나, `list-shared-pages` 비어 있음)로는 닿지 않는다.
- **Next**: 사용자 제출(마감 08-30 09:00) · 커밋 정리 · 5주차 예습.

## 2026-08-27 — 4주차 **⓪ 선행 + 측정 4종 + 글 + 윤문 + 노션 발행**을 한 세션에

- **Status**: 게이트 green — 문서 3종 + labs **106건**(91 → 106, `test_manifest.py` 신규). 인덱스 1146 nodes / 96 docs. 발행: <https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234>
- **남은 것은 ⑦ 링크 공유뿐이고 사용자가 직접** 해야 합니다. 마감 08-30 09:00.
- ★★ **가설이 뒤집혔고, 뒤집힌 방식이 글의 축이 됐다.** 추측 디코딩의 손해를 "추측이 틀려서"로 설명하려 했는데, **수용률을 워크로드별로 갈라 재니 `prefill` c=64는 수용률 100.0%인데 처리량 −53.7%**였다. 하나도 안 틀렸는데 절반 이하로 느려진 것. 손해의 원인이 **"맞아도 쓸 예산이 없어서"** 로 분리됐고, 조건이 수용률이 아니라 **예산**임이 드러났다. 합산 수용률 68.7%로 만족했으면 못 봤다.
- ★ **소스 주석이 글의 주장을 그대로 말하고 있었다** — `scheduler.py:341` *"general enough to cover chunked prefills, prefix caching, speculative decoding"*. 셋이 같은 `token_budget`을 상한(E2)·시작점(E3)·끝점(E1)에서 건드린다. 3주차 글과의 차별점이 여기서 나왔다.

- **계획의 전제 두 개가 틀려 있었다** (착수 전 환경 실측에서 발견)
  - **`vllm/vllm-openai:v0.23.0`이 docker에 없고 k3s containerd에만 있다.** 런북의 `docker run`을 그대로 돌리면 ~10GB를 새로 받는다. 실험을 2주차 B1과 같은 k3s 경로로 돌리도록 전환 — 디스크 문제 이전에 **통제 변수** 문제다.
  - **매니페스트에 임의 플래그를 넣을 자리가 없었다.** args가 고정 문자열이라 E1·E2·E3가 전부 막혀 있었다. `EXTRA_ARGS` env 신설이 이번 주 유일한 도구 작업.
  - ~~디스크~~ → 리스크 아님(WSL 780G · C: 198GB 실측).

- **Changed**
  - `articles/켜면 이득인 최적화는 없다.md` 신규(388줄) — 8단계 구조 + 부록 3종.
  - `labs/wsl2-vllm-baseline/k8s/vllm-baseline.yaml` — `EXTRA_ARGS` env 추가(따옴표 없이 전개).
  - `labs/wsl2-vllm-baseline/test_manifest.py` 신규(15 tests + 12 subtests).
  - `tools/make_figures.py` — `fig_cost`를 계열별 시나리오·단위 지정 가능하게 확장. `fig-e1-spec-decode.svg` 신규.
  - `articles/4주차-00`~`-03` — `docker` 계열 명령을 `redeploy`/`kubectl logs`로 전면 정정.
  - 측정 원본 20여 종 + 분석 2종(`e-analysis.md`, `e4-scheduler-notes.md`).
  - `docs/{AGENT_BRIEF,STATUS,NEXT_PLAN}.md` + `docs/plans/2026-08-27-week4-execution.md` 신규.

- **측정 요약**
  - **E1** `prefill` +199.3%(c=1) → **−53.7%**(c=64) / `decode` 전 구간 −12~−29%. 수용률 `prefill` 100.0% · `decode` ~50%.
  - **E2** ITL 간섭은 청크와 무관(+16.3% vs +16.6%), **디코드 TTFT만 18배**(+10.5% vs +188.9%). 청크 512에서도 ITL +16.3%가 남는 것이 **PD 분리의 동기**.
  - **E3** 2×2 중 **ON+공유 한 칸만** 다름(TTFT p50 8.0배·p95 11.3배·처리량 +71%, 적중률 97.9%). 나머지 셋은 구별 안 됨.

- **측정 설계에서 두 번 걸렸다 (둘 다 기록에 남김)**
  1. **E2 첫 시도에서 간섭이 정확히 0**으로 나왔는데 결과가 아니라 **부하가 안 겹친 설계 결함**이었다(프리필 1초 / 디코드 5초). 배경 부하로 바꾸고 **겹친 초를 매 회 기록**하게 했다. → 부록 A.
  2. **ITL이 두 청크에서 똑같길래 플래그가 무시된 것부터 의심**했다. 기동 로그로 실제 적용을 확인(`Chunked prefill is enabled with max_num_batched_tokens=512/8192`). 무효 측정이 아니었다.

- **검증**: `make check` green · 글의 수치 26개를 측정 원본과 대조해 **불일치 0건** · 윤문 후 헤딩 21·코드 7블록·수치 391·표 40행·링크 18개 **무손상 재확인**(별도 스크립트) · humanize 게이트 exit 0(변경률 11.8%, `ending_comma_rate` z +3.28 → −0.15).
- **환경**: keeper를 `Start-Process`로 띄운 **독립 프로세스**로 해결(창 지킬 필요 없음). ❌ `.wslconfig`의 `vmIdleTimeout=-1`은 WSL 2.7.8.0에서 **안 먹는다**(원인이 유휴 타이머가 아니라 "세션이 없으면 내린다").
- **Blockers**: 없음. **⑦ 링크 공유는 사용자가 직접.**
- **Next**: 5주차 예습. 선택 항목으로 E1 draft-0.5B 팔. AWS GPU 쿼터는 여전히 `0`.

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
