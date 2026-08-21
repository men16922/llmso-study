# Progress Log — 2026-08 아카이브

`docs/PROGRESS_LOG.md`가 컨텍스트 예산(120줄)을 넘어 옮겨둔 오래된 항목입니다. 최신 증분은 그쪽에 있습니다.

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
