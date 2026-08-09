# Next Plan

Last Updated: 2026-08-09

열린 작업만 담는 롤링 플랜입니다. 완료 이력은 `docs/COMPLETED_SUMMARY.md`.

> **이 저장소에서 `[auto]`가 드문 이유**: 게이트는 링크·스키마·문법만 증명합니다. 스터디 문서의 **내용이 맞는가**(교재 챕터 대응, PDF 쪽수 인용)는 원문 대조가 필요해 오프라인으로 검증할 수 없습니다. 그래서 문서 집필은 원칙적으로 `[manual]`이고, `[auto]`는 게이트 자체를 두껍게 만드는 작업에 집중됩니다.

## Priority 0 — 2주차 (CH3·CH4)

- [x] [manual] `knowledge/06-week2-prep.md` 작성 — 완료 (2026-08-09). PDF 해당 구간을 직접 추출해 읽고 작성했고, 인용 쪽수는 물리 페이지 기준으로 `search_index.py` 출력과 일치. 교재의 Triton·RAG·에이전틱은 이 PDF가 다루지 않아 "어긋날 수 있는 지점" 표로 명시.
- [ ] [manual] 모임(오늘 20:30) 후 — 노트의 "스터디 중 확인할 질문" 5개가 강의에서 채워졌는지 확인하고, 안 채워진 것은 과제 소재로 이월.
- [ ] [manual] **2주차 과제 — 시나리오 B1·B2·C1·C2 실행 후 글 작성.** 마감 **2026-08-16 09:00**. 시나리오는 `articles/vLLM 배칭·큐 실습 시나리오 (CH3·CH4).md`에 완성돼 있고 랩 코드도 준비됨(`--unique-prefix`, env 파라미터화). WSL2 머신에서 **4.5~5.5시간, 세 세션**. Done: B1 표 3개 + 파레토 곡선 + B2 Grafana 스크린샷 + C1 표 3개 + C2 표 2개 + 배칭 4종 종합표가 채워지고 해석이 붙음.
  - 글의 축: **배칭 4종(없음/static/dynamic/continuous)을 전부 실측해 예습 노트 §1 표를 숫자로 채운다.** dynamic이 전제하는 "요청들이 같은 시간 걸린다"가 LLM에서 깨지는 것이 결론
  - **세션 순서 고정**: ① B1·B2 (안전판) → ② C1 → ③ C2. 세션 ① 시작 시 `docker pull nvcr.io/nvidia/tritonserver:24.12-py3`(~17GB)와 C1 venv 설치를 백그라운드로 걸어둘 것
  - ⚠️ **포트 충돌**: vLLM port-forward와 교재 C1 서버가 둘 다 8000. B1·B2와 C1은 동시 실행 불가. Triton은 8009/8010/8011로 충돌 없음
  - B3~B5는 다음 편으로 이월 (시나리오 문서 뒤쪽에 설계 보존). B1의 `results/b1-timeline.txt`가 B4의 입력이므로 **반드시 남길 것**
- [ ] [manual] **C1 선행 작업 2건** (WSL2에서, 착수 전 확인) — ① 교재 저장소 `orca3/llm-model-inference` 클론 + `ch03/single_model_llm_serving` venv 설치(`vllm==0.9.0.1`, 8~10GB·30~40분) ② `model_worker.py:48`의 `max_new_tokens=50`을 20으로 맞춰 엔드포인트 간 출력 토큰 수 정렬. 이 정렬을 빠뜨리면 처리량 비교가 2.5배 왜곡됨.
- [ ] [manual] `benchmark.py`에 `--api book` 모드 추가 — 교재 서버는 OpenAI 호환이 아님(`{"prompts":[...]}` / SSE `{"token":...}`). `run_request()`만 분기하고 백분위·goodput 로직은 재사용. 비스트리밍 엔드포인트는 TTFT 미정의로 처리. 40분.
- [ ] [manual] **C2 선행 작업 — `mobilenet_v2`를 배치 축 열린 ONNX로 export.** 저장소의 `densenet_onnx`는 `max_batch_size: 0` + `reshape`로 배치 축이 1에 고정돼 있어 **dynamic batching을 켤 수 없음**. `torch.onnx.export(..., dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}})`로 새로 뽑아야 함. 스크립트는 시나리오 C2-1에 있음. 20분.

## Priority 1 — 게이트 두껍게 만들기

- [ ] [auto] `meta.summary_method` 회귀 검사를 `scripts/check_docs.py`의 `index` 검사에 추가. LLM 보강이 끝난 문서가 `extractive-*`로 되돌아가면 실패해야 함 — 기대값을 저장소에 기록해두고 대조하는 방식. 이게 현재 게이트의 가장 큰 구멍(`docs/STATUS.md` Open Risks 참조). Done: 되돌린 상태를 만들면 `make check-index`가 exit 1.
- [ ] [auto] `scripts/check_docs.py` 자체 테스트 `scripts/test_check_docs.py` 작성 — 깨진 링크/앵커/펜스 안 예시/`%20` 인코딩/`<a id>` 명시 앵커 각각에 대한 케이스. 지금은 손으로만 역방향 확인했음. Done: `python3 -m pytest -q scripts/test_check_docs.py` 통과하고 `make check`에 편입.
- [ ] [auto] 마크다운 표의 열 개수 불일치 검사 추가 — 이 저장소는 표가 많아 실수가 잦음. Done: 고의로 깨진 표에 대해 exit 1.

## Priority 2 — 남은 준비물

- [ ] [manual] AWS GPU 쿼터 증설 신청 (EC2 `Running On-Demand G and VT instances`, 최소 8 vCPU). 6주차(09-06) EKS 실습용, 목표 시한 **2026-08-23**. 절차는 `knowledge/04-kickoff-checklist.md` ⑥.

## Rules

- 작업 시작 전 `docs/AGENT_BRIEF.md` → `docs/STATUS.md` → 이 파일 순으로 읽으세요.
- 큰 작업의 설계 스냅샷은 `docs/plans/YYYY-MM-DD-<topic>.md`에 둡니다.
- **모든 문서는 한국어로.** `CLAUDE.md`의 깨지기 쉬운 지점·콘텐츠 정책을 먼저 확인하세요.

### Automation Tags (무인 루프용)

상태 박스(`[x]`/`[/]`/`[ ]`)와 별개 축으로, 무인 루프가 소비 가능한지를 나타냅니다.

- `[auto]` — 로컬·결정론적·오프라인 게이트(`make check`)로 검증 가능한 항목만.
- `[manual]` — 사람의 판단·감각·외부 서비스가 필요. 무인 루프는 건너뜁니다.
- `[blocked]` — 의존성 미충족 또는 Blocker 2회 누적(러너가 자동 표시). 사람이 검토 후 해제.
- **태그 없음 = 무인 실행 대상 아님** (보안 기본값). 러너는 `[auto]`만 소비합니다.
