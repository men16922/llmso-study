# Status

Last Updated: 2026-08-15

## Current Baseline

**게이트 green.** `make check` = 문서 검사 3종(`links` / `index` / `tools`) + `labs/` 단위 테스트 **91건**, 전부 오프라인·결정론적, 약 2초.

> ⚠️ **이 머신에서는 `make check-labs`가 그대로 안 돕니다.** WSL의 `python3`(3.14)에 **pip 자체가 없고** pytest도 없습니다. 2026-08-15에는 Windows Python 3.12에 `pytest`·`pyyaml`을 설치해 91건을 확인했습니다. `Makefile`의 `PY ?= python3`를 Windows 파이썬으로 덮어쓰거나 WSL에 pip를 넣어야 합니다.

- `knowledge/` — 번호 문서 `00`~`06` + `subpages/` 11종 + `references/` 6종. 상대 링크·앵커 전부 유효.
- `index/` — PDF 3종 + 마크다운 묶음(66개 문서) 인덱스. 스키마 검증 통과. 현재 Inference Engineering만 `llm-claude-code-korean`으로 보강됨, 나머지는 `extractive-*`.
- `labs/` — 4개. `wsl2-vllm-baseline`(56) · `cloudrun-gemma4-vllm`(6) · `triton-dynamic-batching`(19) · `rayserve-on-k8s`(10). 전부 mock·순수 로직이라 GPU·네트워크 불필요.
- `articles/` — Cloud Run Gemma 4(1주차 제출 완료), WSL2 GPU K8s 실습(미제출), CH3·CH4 실습 시나리오 4편, **`Continuous Batching이 처리량을 높이는 방식`(2주차 과제 글 — 작성 완료, 제출 대기)**.
- **측정 원본** — `labs/wsl2-vllm-baseline/results/`에 B1·B2 8종 + `b1-timeline.txt`(구간 시각) + `environment.md` + `metrics-v0.23.0.txt`(v0.23.0 메트릭 96개).
- `study/` — 노션 원문 로컬 사본. **gitignore + 인덱스 제외** (멤버 전용 자료). ⚠️ **현재 체크아웃에는 없음.**

스터디 진행: **1주차(CH1·CH2) 완료·제출 완료. 2주차(CH3·CH4) B1·B2 측정 완료, 글 작성 완료.**

## Active Focus

Authority: `docs/NEXT_PLAN.md`.

0. **2주차 과제 제출** — 글은 완성됨. 남은 것은 ① 사람 검토 ② **Grafana 스크린샷**(선택) ③ 공유. 마감 2026-08-16 09:00.
1. **3주차(CH5·CH6) 예습 노트** — 모임 2026-08-16 20:30.

## Open Risks

- **과제 미공유 1회 = 제명.** 마감은 매주 일요일 09:00. 다음 마감 2026-08-16 09:00 — **글은 준비됐고 제출만 남음.**
- ~~Grafana 스크린샷 미확보~~ → **해소.** 서버 측 원본을 `results/b2-prometheus.{json,txt}`로 내보내고 `tools/make_figures.py`가 SVG 3종을 생성합니다. 캡처는 재현·검증이 안 되지만 이 파일들은 다시 그릴 수 있고, `b1-timeline.txt`의 시각이 있어 사후 재조회도 됩니다. 굳이 Grafana 화면이 필요하면 `localhost:30002`에서 같은 PromQL로 찍으면 됩니다.
- **백그라운드 태스크가 이 환경에서 반복 강제 종료됩니다.** 0-1 keeper가 죽으면 WSL 유휴 poweroff로 k3s 파드가 `Completed`/`Unknown`이 되어 측정이 끊깁니다. **긴 측정은 포그라운드로 돌리거나, keeper를 별도 PowerShell 창에서 사람이 직접 띄우세요.**
- **`make check-labs`가 이 머신에서 그대로 안 됩니다** (위 Baseline 참조).
- **GPU·8000 포트가 하나씩뿐.** B1·B2 / C1 / C2 / C3는 서로 배타적입니다. 세션 전환 시 앞의 것을 안 내리면 다음 실험이 OOM으로 안 뜹니다.
- **KV cache 크기가 롤아웃마다 흔들립니다.** 같은 `slots=64`인데 `Maximum concurrency`가 59.50x / 28.77x로 갈렸습니다. 직전 파드의 VRAM 반환 지연이 유력하나 **미확인**. 롤아웃 직후 이 로그 줄을 반드시 확인하세요 — 조용히 절반이 되면 처리량 천장도 절반입니다.
- **C1이 노션 CH3 원문 대조로 재설계됐습니다.** 교재 서버는 `main.py:63/69/74`가 `async def` 안에서 동기 호출을 해 이벤트 루프가 막히고 동시 요청이 순차 처리됩니다. 배칭 축을 `--prompts-per-request`로 바꿨고, 동시성은 `async def`→`def` 수정 전후 비교로 씁니다. **이 발견 자체가 02편의 핵심**입니다.
- **PDF 인덱스 재생성 사고** — `build_pageindex.py`를 `--only md` 없이 돌리면 LLM 한국어 요약이 날아갑니다. 게이트는 스키마만 보므로 이 회귀를 **잡지 못합니다**(`meta.summary_method` 회귀 검사는 미도입). 복구는 `enrich_summaries.py` 재실행(해시 캐시 있어 거의 공짜).
- **AWS GPU 쿼터 미신청** — 6주차(09-06) EKS 실습용. 목표 시한 2026-08-23.
