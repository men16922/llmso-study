# Next Plan

Last Updated: 2026-09-12

열린 작업만 관리합니다. 완료한 측정·발행은 [COMPLETED_SUMMARY](./COMPLETED_SUMMARY.md), 설계·판단 이력은 [DECISIONS](./DECISIONS.md)를 봅니다.

## 6주차 후속 확인

- [ ] [manual] **외부 CLB 호출:** [과제 글](../articles/6주차%20과제.md)의 외부 검사 절차를 허용된 클라이언트에서 실행하고 `external-http.json`을 확보합니다. 내부 성공을 외부 성공으로 바꾸지 않습니다.
- [ ] [manual] **실제 가용 복제본 증설:** 단일 Trainium 노드의 자원 부족을 해소할 수 있을 때 별도 설계합니다. HPA 목표 증가만으로 완료 처리하지 않습니다. 노드·쿼터 확대는 이번에 수행하지 않았습니다.
- [ ] [manual] **6주차 제출:** 지정 Notion에 워크샵 전체 원고·GPU 대비 구성표·Neuron 동시 관측·실제 스크린샷 반영 완료. ZIP은 Notion에서 제거했고 원본 81개 파일과 후속 관측 자료를 articles 안에 보존했습니다. 제출표 공유와 공개 접근 여부는 별도로 확인합니다.

- [ ] [manual] **워크샵 리소스 종료:** 추가 실험·증거 회수 완료. EKS·노드·Ingress·모니터링·IAM 정책·CloudWatch 로그는 유지 상태입니다. 사용자 종료 시점에 맞춰 워크샵 절차로 정리하고 잔존 리소스를 확인합니다.

## Priority 0 — 5주차 검증·제출 (마감 2026-09-06 09:00)

원고·노션은 결론과 소제목까지 개정했습니다. 09-05 원격 동기화로 측정 원본도 확보했습니다. 첫 작업은 [추가 검증 계획](./plans/2026-09-05-week5-followup-validation.md) §1의 원본 대조입니다. 측정이 없었다고 가정해 ⓪부터 다시 실행하지 않습니다.

- [ ] [manual] **F1b 대조:** `results/f1b-*-r{1,2,3}.json`·기동 로그로 반복 평균·σ·실제 생성 토큰·KV 예산을 확인합니다.
- [ ] [manual] **F2 대조:** `results/f2-traces/`와 `summarize_trace.py`에서 58·98스텝 및 약 28배 정규화 차이, 중복·겹친 커널 집계를 확인합니다.
- [ ] [manual] **보조 지표 대조:** F1c의 tok/s 필드, F5 C 구간의 표 19회·화면 약 22회 선점 차이를 확인합니다. 별도 F1d 실행과 구분합니다.
- [ ] [manual] **추가 실험 선택:** 필요하면 BF16·FP8 × KV 여유·부족의 2×2 비교. 원인 규명에는 같은 작업량 프로파일링, 운영 도입에는 품질 평가가 필요합니다. 새 GPU 실험은 아직 실행하지 않았습니다.
- [ ] [manual] **제출표 공유 확인:** 사용자가 [5주차 발행본](https://app.notion.com/p/3d04c2420ac481c89ce1de666fbf9fbe)을 제출표에 공유했는지 확인합니다. 발행과 제출을 구분합니다.

## Priority 1 — 미확인 제출과 다음 주 준비

- [ ] [manual] **4주차 제출 확인:** 08-30 09:00 마감 경과. [발행본](https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234)의 제출표 공유 여부가 미확인입니다. 기존 연결은 제출표에 접근하지 못했습니다.
- [ ] [manual] **AWS GPU 쿼터 확인·신청:** 08-23 조회에서 us-east-1·ap-northeast-2가 0, 신청 이력 없음이었습니다. 현재 상태를 재조회하고 필요하면 사용자가 콘솔에서 신청합니다. 기준은 us-east-1 / `L-DB2E81BA` / 32 vCPU이며 [준비 문서](../knowledge/07-aws-gpu-quota.md)를 따릅니다.
- [ ] [manual] **통합 메모리 vs VRAM 비교:** [G 시리즈 계획](./plans/2026-09-01-unified-memory-vs-vram.md)의 트리거에 따라 착수합니다. 5주차 마감 전에는 보류하며, 제출 후 별도 글 또는 AWS 쿼터로 6주차 EKS가 막힐 때 대안으로 검토합니다.

## Priority 2 — 오프라인 검증 보강

- [ ] [auto] **PDF 요약 회귀 검사:** `meta.summary_method`가 LLM 보강에서 `extractive-*`로 바뀌면 `make check-index`가 실패하도록 검증합니다.
- [ ] [auto] **문서 검사 자체 테스트:** 링크·앵커·펜스 예시·URL 인코딩·명시 앵커를 검증하는 `scripts/test_check_docs.py`를 추가하고 게이트에 연결합니다.
- [ ] [auto] **표 열 개수 검사:** 마크다운 표가 깨졌을 때 문서 검사가 실패하도록 합니다.
- [ ] [auto] **WSL 기본 Python 게이트 경로:** pip·pytest가 없는 WSL 환경에서 사용할 Python 경로를 정리합니다. macOS 임시 venv 통과와 WSL 검증은 별개이며 현재 게이트 기준은 120건입니다.

## Priority 3 — 이월·선택 작업

- [ ] [manual] **F3 복제 2개:** 별도 매니페스트와 GPU 자원 광고 변경이 필요합니다. 기존 비교에 혼합하지 않고 [09-02 결정](./DECISIONS.md)을 바탕으로 별도 실험을 설계합니다.
- [ ] [manual] **Grafana 캡처:** 필요하면 사용자 로그인 후 DCGM 화면을 추가합니다. 현재 글은 Prometheus 실측을 사용하므로 발행의 필수 조건은 아닙니다. 포트포워딩은 `labs/wsl2-vllm-baseline/_pf_dashboards.sh`를 참고합니다.
- [ ] [manual] **Ray Serve V0 chunked prefill:** vLLM 0.7.2의 ON/OFF 비교는 [3주차 설계](./plans/2026-08-16-week3-triton-rayserve.md)의 이월분입니다.
- [ ] [manual] **C1 교재 서버 비교:** WSL에 별도 환경을 준비하고 `max_new_tokens`를 비교 엔드포인트와 맞춥니다. `async def` 안 동기 호출 때문에 동시 요청이 직렬화되는 조건을 분리합니다.
- [ ] [manual] **C2 선행 작업의 완료 여부 대조:** Triton 측정 기록은 있으나 옛 계획에 이미지 풀·ONNX export가 열린 상태로 남았습니다. [옛 체크리스트](./archive/context-2026-09-05-local/NEXT_PLAN.md)와 기존 결과를 대조한 뒤 중복 작업을 닫습니다.

## 참고와 실행 규칙

- 4주차 완료 체크리스트·일정은 [보관본](./archive/context-2026-09-05-local/NEXT_PLAN.md)에, 원격의 선택 작업은 [원격 보관본](./archive/context-2026-09-05-remote/NEXT_PLAN.md)에 보존했습니다. 과제 제출 확인이 남은 날짜별 계획은 이동하지 않습니다.
- `[auto]`는 오프라인·결정론적 게이트로 검증할 수 있는 작업, `[manual]`은 원문 대조·사용자 판단·외부 접근이 필요한 작업입니다. 태그가 없으면 무인 실행 대상이 아닙니다.
- 새 작업 전 AGENT_BRIEF → STATUS → NEXT_PLAN 순으로 읽습니다. GPU 측정·외부 게시·비용 발생은 기존 사용자 승인 범위 안에서만 수행합니다.
