# Progress Log

Last Updated: 2026-08-16

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
