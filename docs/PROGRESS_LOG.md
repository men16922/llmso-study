# Progress Log

Last Updated: 2026-08-09

최근 증분 요약만 유지합니다 (최신 3~5건, ≤120줄). 오래된 항목은 `/tidy-docs`로 `docs/archive/progress-YYYY-MM.md`에 보관합니다.

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
