# Status

Last Updated: 2026-08-09

## Current Baseline

**게이트 green.** `make check` = 문서 검사 3종(`links` / `index` / `tools`) + `labs/` 단위 테스트 **86건**, 전부 오프라인·결정론적, 약 2초.

- `knowledge/` — 번호 문서 `00`~`06` + `subpages/` 11종 + `references/` 6종. 상대 링크·앵커 전부 유효.
- `index/` — PDF 3종 + 마크다운 묶음(66개 문서) 인덱스. 스키마 검증 통과. 현재 Inference Engineering만 `llm-claude-code-korean`으로 보강됨, 나머지는 `extractive-*`.
- `labs/` — 4개. `wsl2-vllm-baseline`(51) · `cloudrun-gemma4-vllm`(6) · `triton-dynamic-batching`(19) · `rayserve-on-k8s`(10). 전부 mock·순수 로직이라 GPU·네트워크 불필요.
- `articles/` — Cloud Run Gemma 4(1주차 제출 완료), WSL2 GPU K8s 실습(미제출), CH3·CH4 실습 시나리오(**도구 완성, 측정 대기**).
- `study/` — 노션 원문 로컬 사본. **gitignore + 인덱스 제외** (멤버 전용 자료).

스터디 진행: **1주차(CH1·CH2) 완료, 과제 링크 공유 완료.** 2주차(CH3·CH4) 모임 2026-08-09 20:30.

## Active Focus

Authority: `docs/NEXT_PLAN.md`.

0. **2주차 과제** — 시나리오의 B1·B2·C1·C2·C3를 WSL2에서 실행하고 표를 채우면 글이 됨. **도구는 전부 준비 완료 — 실행과 기록만 남음.** 6.5~8시간·네 세션. 마감 2026-08-16 09:00.

## Open Risks

- **과제 미공유 1회 = 제명.** 마감은 매주 일요일 09:00. 다음 마감 2026-08-16.
- **분량 대비 시간이 빠듯함.** 6.5~8시간을 일주일에 나눠야 합니다. **B1·B2만으로도 글 한 편이 서므로 세션 1을 반드시 먼저** 끝내세요. 잘라내는 순서는 시나리오 머리말에 명시돼 있습니다(C3-4 → C1의 `bs` 축 → C2의 20ms).
- **GPU·8000 포트가 하나씩뿐.** B1·B2 / C1 / C2 / C3는 서로 배타적입니다. 세션 전환 시 앞의 것을 안 내리면 다음 실험이 OOM으로 안 뜹니다.
- **실제 GPU 실행은 한 번도 안 했습니다.** 도구는 mock·순수 로직으로만 검증됐습니다. vLLM v0.23.0 메트릭 이름, Triton 이미지 동작, KubeRay 배포는 전부 노트북에서 첫 확인입니다. 시나리오에 각각 확인 절차와 대안을 넣어뒀습니다.
- **`study/Ch3.md`가 0바이트** — 재복사 필요. CH3 원문 대조는 아직 못 했습니다(CH4는 완료).
- **PDF 인덱스 재생성 사고** — `build_pageindex.py`를 `--only md` 없이 돌리면 LLM 한국어 요약이 날아갑니다. 게이트는 스키마만 보므로 이 회귀를 **잡지 못합니다**(`meta.summary_method` 회귀 검사는 미도입). 복구는 `enrich_summaries.py` 재실행(해시 캐시 있어 거의 공짜).
- **AWS GPU 쿼터 미신청** — 6주차(09-06) EKS 실습용. 목표 시한 2026-08-23.
