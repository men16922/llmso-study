# Status

Last Updated: 2026-08-09

## Current Baseline

**게이트 green.** `make check` = 문서 검사 3종(`links` / `index` / `tools`) + `labs/` 단위 테스트 10건, 전부 오프라인·결정론적, 약 2초.

- `knowledge/` — 번호 문서 `00`~`05` + `subpages/` 11종 + `references/` 6종. 상대 링크·앵커 전부 유효.
- `index/` — PDF 3종 + 마크다운 묶음(36개 문서) 인덱스. 스키마 검증 통과. 현재 Inference Engineering만 `llm-claude-code-korean`으로 보강됨, 나머지는 `extractive-*`.
- `labs/` — `wsl2-vllm-baseline`(6 tests), `cloudrun-gemma4-vllm`(6 tests). 둘 다 localhost mock HTTP라 GPU·네트워크 불필요. 서빙 파라미터 3종이 env로 분리되어 `kubectl set env`만으로 스윕 가능.
- `articles/` — Cloud Run Gemma 4(1주차 제출 완료), WSL2 GPU K8s 실습(미제출), CH3·CH4 실습 시나리오(측정 대기).

스터디 진행: **1주차(CH1·CH2) 완료, 과제 링크 공유 완료.** 2주차(CH3·CH4)는 2026-08-09 20:30.

## Active Focus

Authority: `docs/NEXT_PLAN.md`.

0. **2주차 과제** — `articles/vLLM 배칭·큐 실습 시나리오 (CH3·CH4).md`의 B1~B4를 WSL2 머신에서 실행하고 결과 표를 채우면 글이 됨. 마감 2026-08-16 09:00.

## Open Risks

- **과제 미공유 1회 = 제명.** 마감은 매주 일요일 09:00. 다음 마감 2026-08-16.
- **시나리오의 PromQL이 미검증.** vLLM v0.23.0의 실제 메트릭 이름을 실물로 대조하지 않았습니다(특히 `vllm:prefix_cache_*`). 시나리오 0-3에 확인 절차를 넣어뒀으니, 빈 결과가 나오면 실습 실패가 아니라 이름 차이입니다.
- **전부 미커밋.** 하네스·예습 노트·시나리오·랩 보강이 워킹 트리에만 있습니다.
- **PDF 인덱스 재생성 사고** — `build_pageindex.py`를 `--only md` 없이 돌리면 LLM 한국어 요약이 날아갑니다. 게이트는 스키마만 보므로 이 회귀를 **잡지 못합니다**(`meta.summary_method` 회귀 검사는 미도입). 복구는 `enrich_summaries.py` 재실행(해시 캐시 있어 거의 공짜).
- **AWS GPU 쿼터 미신청** — 6주차(09-06) EKS 실습용. 목표 시한 2026-08-23.
