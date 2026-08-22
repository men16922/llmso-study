# Agent Brief

Last Updated: 2026-08-22

세션 시작용 압축 컨텍스트(≤60줄). 상세는 필요할 때만 링크 문서를 여세요.

> ▶ NEXT SESSION: **3주차 과제 — 링크 공유만 남았습니다.** 마감 **2026-08-23(일) 09:00**.
> 발행본: https://app.notion.com/p/3c44c2420ac48157aaebe78f971e05c9 (윤문·발행·전 수치 대조까지 완료). 원고는 [`articles/슬롯을 4배로 늘렸는데 처리량이 그대로였다.md`](../articles/%EC%8A%AC%EB%A1%AF%EC%9D%84%204%EB%B0%B0%EB%A1%9C%20%EB%8A%98%EB%A0%B8%EB%8A%94%EB%8D%B0%20%EC%B2%98%EB%A6%AC%EB%9F%89%EC%9D%B4%20%EA%B7%B8%EB%8C%80%EB%A1%9C%EC%98%80%EB%8B%A4.md).
> 측정 3종(C3 계층 · B3 KV cache · C2 Triton)은 **전부 완료**돼 `labs/*/results/`에 있습니다.
>
> **다음 주 실험을 설계할 때 알아둘 것 두 가지**
> - **Ray Serve 아래에서는 `vllm:*` 메트릭이 없습니다** (`:8000/metrics` 404). 2주차식 서버 측 교차검증이 필요하면 Ray Serve 위에 올리면 안 됩니다.
> - **`ray-llm:2.44.1`의 vLLM은 0.7.2**입니다(2주차 기준선은 0.23.0). 이미지를 바꾸면 엔진도 바뀝니다 — 비교 전에 반드시 양쪽 버전을 확인하세요.
>
> ⚠️ 백그라운드 태스크 강제 종료는 이번 세션에서 **겪지 않았습니다.** WSL 안에서 `setsid`로 분리한 프로세스(keeper·이미지 풀·벤치마크)는 별도 `wsl.exe` 호출을 넘어 살아남습니다. keeper는 `/usr/local/bin/llmso-keeper`에 있습니다.
>
> Windows에서 게이트·테스트는 `PYTHONIOENCODING=utf-8 py -3 ...`로 전부 돕니다.

## Snapshot

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13, 총 7주) 자료 정리 저장소. 한국어 학습 문서 모음 + 문서·PDF 탐색용 로컬 인덱싱 도구 + **WSL2 GPU 실측용 랩 4종**입니다. 게이트는 오프라인·결정론적("문서와 인덱스가 어긋나지 않았는가" + labs 단위 테스트 91건)이고, **실제 GPU 측정은 게이트 밖**입니다. 현재 **1·2주차 완료·제출 완료**, **3주차(CH5·CH6)는 측정 3종 + 글 + 노션 발행 완료, 링크 공유 대기**.

핵심 설계는 **인덱스 파이프라인의 역할 분리**입니다 — 트리는 `build_pageindex.py`가 LLM 없이 결정론적으로 만들고, `summary`만 `enrich_summaries.py`가 한국어로 교체합니다. 근거는 `index/README.md` §2 실측 기록.

## Active Work

Authority: `docs/NEXT_PLAN.md`.

1. **3주차 과제 — 측정 3종 + 글 + 노션 발행 완료. 링크 공유만 남음.** 결론 셋: 계층이 처리량 천장을 정하고 있었다(같은 엔진·슬롯 64에서 **−70.0%**, 엔진이 낼 수 있는 값의 함수) · KV cache는 상한을 정하지만 그게 처리량은 아니다(노브가 4.5배 흔들려도 ±17%) · dynamic batching은 노브가 아니라 **도착률의 함수**.
2. 과제 마감은 **매주 일요일 09:00**, 미공유 1회 = 제명. 다음 마감 08-23.
3. 이월분 — C1(교재 자작 배칭, `async def` 발견) · 도전과제 3(chunked prefill, 환경은 확인됨) · 배칭 4종 표의 "없음"·"static" 칸.

## Read Order

1. 현재 상태: `docs/STATUS.md`
2. 다음 작업: `docs/NEXT_PLAN.md`
3. 최근 기록: `docs/PROGRESS_LOG.md`
4. (저장소 자체 규칙) `CLAUDE.md` — 깨지기 쉬운 지점·콘텐츠 정책

## Commands

- 검증 게이트: `make check`  <!-- harness-config.gate와 일치 -->
- 빠른 확인: `make smoke-local` (링크만)
- 개념 위치 찾기: `python3 tools/search_index.py "KV cache"`
- 마크다운 수정 후: `make index-md`

## Guardrails

- **이 저장소는 비공개 유지.** 스터디 규칙상 외부 공개·전파 금지(`knowledge/03-study-rules.md`). 공개 원격 푸시·외부 서비스 업로드는 **반드시 사전 확인**. (`origin`은 비공개 확인됨)
- **`study/`는 커밋하지 않습니다.** 노션 멤버 전용 원문의 로컬 사본입니다. `.gitignore`와 `tools/build_pageindex.py`의 `MD_SKIP_DIRS` 양쪽에 들어 있습니다 — 인덱스는 커밋되므로 거기 발췌가 들어가면 사실상 저장소 전재가 됩니다.
- **`make index-pdf` / `build_pageindex.py` 직접 실행 금지** — PDF까지 재생성하면 LLM 한국어 요약이 발췌로 되돌아갑니다. 마크다운만 고쳤으면 `make index-md`.
- `enrich_summaries.py`는 API 키가 아니라 **Claude Code 구독 사용량**을 씁니다. 반드시 `--dry-run` → `--limit 5` → 실제 순서로.
- `labs/`의 벤치마크를 **실제 엔드포인트에 돌리면 비용**이 발생합니다. 무인 루프에서는 금지(단위 테스트만 허용).
- **모든 문서는 한국어로 작성합니다.**
- 스터디 내용의 사실관계·쪽수 인용 검증은 원문 대조가 필요하므로 `[manual]`입니다.
