# Progress Log

Last Updated: 2026-08-22

## 2026-08-22 — 3주차 **측정 3종 전부 완료 + 글 작성 완료**. 남은 것은 노션 발행·링크 공유

- **Status**: 게이트 green — 문서 3종 + labs **91건**. 마크다운 인덱스 975 nodes / 81 docs. 커밋 `42a3446`·`cf95673`·`b44f061`.
- **08-16 → 08-21 닷새 공백 뒤 한 세션에 몰아서 수행.** 계획 일정(08-17 C3 / 08-18 B3 / 08-19~20 C2)이 통째로 밀렸으나, 측정이 계획 추정보다 훨씬 빨라(벤치마크 1회 약 4분, 롤아웃 20~60초) 셋 다 들어갔다. **2주차처럼 범위를 줄이지는 않았다.**
- ★ **통제 변수가 깨져 있는 것을 발견해 실험 설계를 바꿨다.** `ray-llm:2.44.1`이 품은 vLLM은 **0.7.2**인데 2주차 B1 기준선은 **0.23.0**. 그냥 빼면 "계층 + 엔진 16개 마이너 버전"의 합이 나온다. **같은 ray-llm 이미지로 Ray 없이 vLLM만 띄운 구성 B**를 추가해 변수를 계층 하나로 좁혔다(추가 다운로드 0, 약 15분).
- **Changed**
  - `articles/처리량의 천장은 어디에 있었나.md` 신규 — 8단계 템플릿. 세 실험을 "처리량 천장을 정하는 게 무엇인가" 한 줄기로 묶음.
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
- **Blockers**: 없음. **노션 발행 + 링크 공유만 남음** (마감 08-23 09:00).
- **Next**: 글 검토 → 노션 발행 → 과제 링크 공유.

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
