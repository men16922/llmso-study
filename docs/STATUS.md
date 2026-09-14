# Status

Last Updated: 2026-09-14

## Current Baseline

- 비공개 원격 `men16922/llmso-study`의 `main`을 `d37fbae`까지 동기화했습니다(18개 선행 커밋). 원격 측정 코드·결과와 이번 macOS 원고 편집을 함께 보존합니다.
- 09-05 동기화 전 macOS 게이트는 문서 검사 + labs 106건 통과였습니다. 원격은 `test_summarize_trace.py` 14건을 추가한 **120건 구성**입니다. 동기화 후 실행 결과는 아래 Verification에 기록합니다.
- `study/`는 Git 추적 0건, 로컬 원문 11개 보존입니다. 원격 `cc9da27`의 추적 해제가 반영됐으며 `.gitignore`·인덱스 제외 규칙을 유지합니다.
- `index/*.json`은 커밋 대상 생성물입니다. Markdown만 재생성하며 PDF 3종의 기존 요약은 보존합니다.

## Active Focus

Authority: [NEXT_PLAN](./NEXT_PLAN.md).

**AWS GPU 아키텍처 TA 검토 표준 완료:** [Simple 7장](../GPU_검토표준_Simple.html)·[Detail 15장](../GPU_검토표준_Detail.html)·[상세 근거](../GPU_검토표준_상세근거.md)·[발표 스크립트](../GPU_검토표준_발표스크립트.md). 상단 메뉴 없는 슬라이드 방식이며 번호·좌우 키로 이동합니다. TA 범위를 세 영역으로 간소화하고, Simple 5장·Detail 10장의 GPU 통신은 AWS 원본으로 설명합니다. 간결한 7장 발표문과 예상 Q&A 12개를 별도 문서에 정리했습니다. 후속 요청으로 gpu/ 문서 4개·기존 그림 66개를 복구하고 AWS 통신 그림 1개를 추가했습니다. 원본 복구본은 삭제 전 백업과 바이트 단위로 일치합니다. 이전에 정리한 다른 루트 입력·중간 산출물은 복원하지 않았고 기존 스터디 자료는 유지했습니다.

**6주차 AWS 워크샵 아티클:** [과제 글](../articles/6주차%20과제.md)과 [지정 Notion 페이지](https://app.notion.com/p/3d94c2420ac4805ca5faeff33f549054)의 제목은 「AWS Trainium·EKS로 LLM을 서비스로 연결하기」입니다. 기존 Lab 1·2의 모델 준비·S3 캐시·배포 구성을 확인하고, 직접 수행한 Lab 3~6의 Ingress → 관측 → 부하 테스트 → HPA를 중심으로 설명합니다. **워크샵 전체가 본문이며 추가 실험은 부하 테스트의 한 과정입니다.** CLB·Grafana·CloudWatch·HPA 화면과 비교 그림을 유지하고, 표 8개·접기 9개에 실제 설정·관측 근거를 포함했습니다. 원고는 첨부 없이 읽도록 정리하고, ZIP 81개 파일과 ZIP 원본은 `articles/week6-workshop-materials/`에 복구해 대조했습니다. Notion 사용자가 추가한 이미지도 보존했습니다. 결론은 「확장은 요청 대기에서 실제 응답 용량까지 이어져야 한다」로 확정했습니다. 기존 실증 화면과 원본 수치로 근거를 대조했고, 추론·HPA 화면은 본문에 노출했습니다. 후속 요청에 따라 NVIDIA GPU 대비 구성표와 Neuron 동시 관측 640건, 실제 Grafana 화면을 추가했습니다. Notion 이미지 9개(사용자 추가 이미지 포함)와 로컬 이미지 8개를 유지합니다.

- 실측 근거: Prometheus 11 targets up, 기본 부하 120/120·llmperf 50/50 성공. CloudWatch Agent와 performance 로그 그룹 한정 IAM 정책 적용 후 Pod CPU·메모리 datapoint 확인. HPA 목표 1→2→3→1, 가용 1 유지. 기존 추가 추론 1,024/1,024와 후속 Neuron 관측 640/640 성공. 새 C4→C8 비교는 처리량 451.54→452.82 tok/s, TTFT p95 0.173→2.439초, CPU 평균 약 0.45코어, 두 NeuronCore 평균 약 79%, waiting 0→4, HPA 목표·가용 1 유지입니다. 지속 시험은 조건별 1회이며 79%를 완전 포화로 해석하지 않습니다.
- 원본: `labs/eks-trainium-workshop/execution-record.md`, `results/2026-09-12/`, `results/2026-09-12-extra/`, `articles/screenshots/week6-*.png`. 마지막 실측 후 테스트 Pod 삭제, EKS·Ingress·관측·HPA 유지. 후속 원본은 `results/2026-09-12-neuron/`이며 코드·결과·실제 화면을 `articles/week6-workshop-materials/supplementary/neuron-observation/`에도 보존했습니다. 임시 수집기·scrape job·테스트 Pod 정리 후 API 재검사와 기존 Prometheus 11/11 up을 확인했습니다. vLLM Pod·이미지·모델 설정과 노드는 유지했습니다.

- 6주차 한계: 외부 CLB 호출은 도구 정책 제한, CloudWatch 수집기 부재·로그 전송 거부는 후속 작업에서 해결했습니다. IAM 변경은 사용자 제공 참가자 세션으로 수행했습니다. HPA 새 Pod는 neuron·CPU·임시 저장 공간 부족으로 Pending이었다.

**5주차 원고·노션 최종 편집 완료, 원측정 대조·제출 확인은 별도입니다.** 마감은 2026-09-06 09:00입니다.

- 원고: [FP8 양자화로 처리량이 늘어난 이유](../articles/처리량이%20올랐다면%20무엇이%20빨라진%20것인가.md). [노션 발행본](https://app.notion.com/p/3d04c2420ac481c89ce1de666fbf9fbe).
- 구조: 질문·핵심 결론·세 구성 비교표·용어 설명·본문 6절. 표 15개·그림 5개·코드 11개·접기 14개. 결론 제목은 「FP8의 효과는 메모리 절감에 그치지 않았다」입니다.
- 관측: FP8 기본 +33.7%, KV 예산 축소 FP8 +33.8%, ITL p50 9.7→7.3ms. 캐시 용량 증가만으로는 이득을 설명할 수 없지만, KV 기여율 0%나 특정 커널·대역폭의 기여율을 확정하지 않습니다.
- Humanize A(19.41%, 6/6)는 앞선 윤문 단계의 자체평가입니다. 이후 구조·결론 편집을 같은 수치로 재평가하지 않았습니다.
- **원본 확보 완료:** `labs/wsl2-vllm-baseline/results/f*`, F2 압축 트레이스 2개, `summarize_trace.py`, `run_f*.sh`가 원격에서 들어왔습니다. ‘현재 체크아웃에 없음’은 동기화 전 상태입니다. [추가 검증 계획](./plans/2026-09-05-week5-followup-validation.md)에 따라 대조합니다.
- 1~3주차 제출 완료. 4주차는 측정·발행 완료, 제출표 공유 미확인(08-30 마감 경과). 5주차도 발행과 과제 제출은 구분합니다.

## Verification

- 09-14 최종 GPU 자료: Chrome에서 Simple 7장·Detail 15장의 번호/키보드/해시 이동, 한 장 표시, 상단 메뉴 제거, 그림 확대(Simple 3개·Detail 10개), 오프라인 이미지, 데스크톱·모바일·작은 화면 검사 통과. A4 7/15장 전체 인쇄와 텍스트 경계 검사 통과. HTML의 도식은 내부에 포함하고 Markdown은 AWS 링크·gpu/ 이미지를 사용합니다. 복구 원본 70개와 삽입한 AWS 통신 이미지의 바이트 일치 확인. 검증 기록은 `/tmp/gpu-ta-final/{simple,detail}-slideshow/`에 있습니다.

- 09-12 Neuron 후속 관측: 640건 실요청 성공, 원본 집계·Python 구문·보존본 바이트 대조, Markdown 인덱스·문서 링크·diff 검사 통과. Notion 재조회와 실제 화면에서 새 구성 비교표·Grafana 이미지·측정표를 확인했습니다. 임시 자원 정리 후 API 정상·Prometheus 11/11 up.

- 09-12: Python 3.11 임시 venv로 `make check` 통과 — 문서·인덱스, labs **99 passed / 21 skipped / 8 subtests passed**. 기본 Python 3.9에서는 기존 타입 문법 오류가 나므로 사용하지 않습니다. 신규 실습 JSON 파싱·Python 구문·민감 패턴 검사 통과. 실제 AWS 실행 근거는 결과 폴더에 별도 보존합니다.

- 최종 노션: 6번 결론 본문 대조와 소제목 6개 재조회 통과. 공개 화면·용어 접기 동작은 앞선 구조 개정에서 확인했고 마지막 제목 변경 후 UI는 재확인하지 않았습니다.
- 현재 정리본: `python3 tools/build_pageindex.py --only md`와 `make check PY=/tmp/w5-review-venv/bin/python` 통과(문서 links·index·tools + labs **120건**, 85+6+19+10). GPU 재측정·응답 품질 평가·원본 수치 전수 대조는 수행하지 않았습니다.
- 09-12 로컬 임시 venv는 `/tmp/week6-py311-venv`입니다. 기본 Python의 pytest 미설치와 Windows/WSL 실행 환경을 혼동하지 않습니다.

## Open Risks


- F1b 반복별 평균·σ와 KV 예산 잔여 2.4%, F1c 처리량 필드, F2의 58·98스텝 및 약 28배 정규화 차이를 원본으로 대조해야 합니다. 역할별 커널 집계는 현재 잠정 근거입니다.
- Prometheus C 구간의 표 19회와 화면 마지막 약 22회 선점은 아직 대조가 필요합니다. 별도 F1d 실행의 4회와 섞지 않습니다.
- 커널 duration 합계는 실제 step elapsed time과 다릅니다. `Maximum concurrency`는 KV 수용량이며 실제 활성 요청 수가 아닙니다. ITL·TTFT·생성/프롬프트 처리량도 구분합니다.
- 제출표 접근은 이전 Notion 연결에서 불가능했습니다. 사용자 제출 여부는 미확인입니다. AWS GPU 쿼터 0은 **08-23 조회 기록**이므로 현재 값을 다시 확인해야 합니다.
- PDF 요약 회귀 검사는 아직 없습니다. 스키마 검사가 통과해도 LLM 보강 요약이 발췌로 되돌아갈 수 있습니다.
- 기존 조립기의 sections는 최종 원고와 다릅니다. `assemble.py`를 다시 실행하지 않습니다. 이전 FP8 초안은 `_workspace/2026-09-05-009/archived-draft.md`에 보존하고 검색 대상에서 제외했습니다.

## 상세 기록

현재 판단의 기준은 이 문서와 NEXT_PLAN입니다. 이전 상태·해결된 위험·환경 함정은 [로컬 상태 보관본](./archive/context-2026-09-05-local/STATUS.md)과 [원격 상태 보관본](./archive/context-2026-09-05-remote/STATUS.md), 날짜별 결과는 [진행 로그](./PROGRESS_LOG.md)와 월별 아카이브에 남겼습니다.
