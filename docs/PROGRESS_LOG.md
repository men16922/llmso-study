# Progress Log

Last Updated: 2026-08-15

## 2026-08-15 — 2주차 세션 1(B1·B2) 실측 완료 + 과제 글 작성. **첫 실제 GPU 실행**

- **Status**: 게이트 green — 문서 3종 + labs **91건**(56+6+19+10). 미커밋.
- **범위 결정**: 08-09 이후 6일간 측정이 없었고 마감(08-16 09:00)까지 하루가 안 남아 **세션 1만 수행하고 C1·C2·C3는 통째 이월**. 근거는 시나리오 자체의 안전판(*"B1·B2만으로도 글 한 편이 선다"*).
- **Changed**
  - **B1·B2 전 구간 실측** (모델 `Qwen2.5-1.5B-Instruct`, vLLM v0.23.0, RTX 4080 Laptop 12GB). `short`·`decode` × slots 1/16/64 + B2 큐 부하. 결과 8종을 `labs/wsl2-vllm-baseline/results/`에 커밋.
  - `articles/Continuous Batching이 처리량을 높이는 방식.md` 신규 — 8단계 템플릿 전부 + 한계 6개 + 재현 부록.
  - `.gitattributes` 신규(`*.sh text eol=lf`), `articles/2주차-00`에 함정 3건을 트러블슈팅·본문으로 반영.
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
