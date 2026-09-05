# Status

Last Updated: 2026-09-05

## Current Baseline

- 비공개 원격 `men16922/llmso-study`의 `main`을 `d37fbae`까지 동기화했습니다(18개 선행 커밋). 원격 측정 코드·결과와 이번 macOS 원고 편집을 함께 보존합니다.
- 09-05 동기화 전 macOS 게이트는 문서 검사 + labs 106건 통과였습니다. 원격은 `test_summarize_trace.py` 14건을 추가한 **120건 구성**입니다. 동기화 후 실행 결과는 아래 Verification에 기록합니다.
- `study/`는 Git 추적 0건, 로컬 원문 11개 보존입니다. 원격 `cc9da27`의 추적 해제가 반영됐으며 `.gitignore`·인덱스 제외 규칙을 유지합니다.
- `index/*.json`은 커밋 대상 생성물입니다. Markdown만 재생성하며 PDF 3종의 기존 요약은 보존합니다.

## Active Focus

Authority: [NEXT_PLAN](./NEXT_PLAN.md).

**5주차 원고·노션 최종 편집 완료, 원측정 대조·제출 확인은 별도입니다.** 마감은 2026-09-06 09:00입니다.

- 원고: [FP8 양자화로 처리량이 늘어난 이유](../articles/처리량이%20올랐다면%20무엇이%20빨라진%20것인가.md). [노션 발행본](https://app.notion.com/p/3d04c2420ac481c89ce1de666fbf9fbe).
- 구조: 질문·핵심 결론·세 구성 비교표·용어 설명·본문 6절. 표 15개·그림 5개·코드 11개·접기 14개. 결론 제목은 「FP8의 효과는 메모리 절감에 그치지 않았다」입니다.
- 관측: FP8 기본 +33.7%, KV 예산 축소 FP8 +33.8%, ITL p50 9.7→7.3ms. 캐시 용량 증가만으로는 이득을 설명할 수 없지만, KV 기여율 0%나 특정 커널·대역폭의 기여율을 확정하지 않습니다.
- Humanize A(19.41%, 6/6)는 앞선 윤문 단계의 자체평가입니다. 이후 구조·결론 편집을 같은 수치로 재평가하지 않았습니다.
- **원본 확보 완료:** `labs/wsl2-vllm-baseline/results/f*`, F2 압축 트레이스 2개, `summarize_trace.py`, `run_f*.sh`가 원격에서 들어왔습니다. ‘현재 체크아웃에 없음’은 동기화 전 상태입니다. [추가 검증 계획](./plans/2026-09-05-week5-followup-validation.md)에 따라 대조합니다.
- 1~3주차 제출 완료. 4주차는 측정·발행 완료, 제출표 공유 미확인(08-30 마감 경과). 5주차도 발행과 과제 제출은 구분합니다.

## Verification

- 최종 노션: 6번 결론 본문 대조와 소제목 6개 재조회 통과. 공개 화면·용어 접기 동작은 앞선 구조 개정에서 확인했고 마지막 제목 변경 후 UI는 재확인하지 않았습니다.
- 현재 정리본: `python3 tools/build_pageindex.py --only md`와 `make check PY=/tmp/w5-review-venv/bin/python` 통과(문서 links·index·tools + labs **120건**, 85+6+19+10). GPU 재측정·응답 품질 평가·원본 수치 전수 대조는 수행하지 않았습니다.
- 로컬 임시 venv는 `/tmp/w5-review-venv`입니다. 기본 Python의 pytest 미설치와 Windows/WSL 실행 환경을 혼동하지 않습니다.

## Open Risks

- F1b 반복별 평균·σ와 KV 예산 잔여 2.4%, F1c 처리량 필드, F2의 58·98스텝 및 약 28배 정규화 차이를 원본으로 대조해야 합니다. 역할별 커널 집계는 현재 잠정 근거입니다.
- Prometheus C 구간의 표 19회와 화면 마지막 약 22회 선점은 아직 대조가 필요합니다. 별도 F1d 실행의 4회와 섞지 않습니다.
- 커널 duration 합계는 실제 step elapsed time과 다릅니다. `Maximum concurrency`는 KV 수용량이며 실제 활성 요청 수가 아닙니다. ITL·TTFT·생성/프롬프트 처리량도 구분합니다.
- 제출표 접근은 이전 Notion 연결에서 불가능했습니다. 사용자 제출 여부는 미확인입니다. AWS GPU 쿼터 0은 **08-23 조회 기록**이므로 현재 값을 다시 확인해야 합니다.
- PDF 요약 회귀 검사는 아직 없습니다. 스키마 검사가 통과해도 LLM 보강 요약이 발췌로 되돌아갈 수 있습니다.
- 기존 조립기의 sections는 최종 원고와 다릅니다. `assemble.py`를 다시 실행하지 않습니다. 이전 FP8 초안은 `_workspace/2026-09-05-009/archived-draft.md`에 보존하고 검색 대상에서 제외했습니다.

## 상세 기록

현재 판단의 기준은 이 문서와 NEXT_PLAN입니다. 이전 상태·해결된 위험·환경 함정은 [로컬 상태 보관본](./archive/context-2026-09-05-local/STATUS.md)과 [원격 상태 보관본](./archive/context-2026-09-05-remote/STATUS.md), 날짜별 결과는 [진행 로그](./PROGRESS_LOG.md)와 월별 아카이브에 남겼습니다.
