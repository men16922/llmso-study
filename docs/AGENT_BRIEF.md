# Agent Brief

Last Updated: 2026-08-16

세션 시작용 압축 컨텍스트(≤60줄). 상세는 필요할 때만 링크 문서를 여세요.

> ▶ NEXT SESSION: **3주차 과제 실행 시작.** 계획은 [`docs/plans/2026-08-16-week3-triton-rayserve.md`](./plans/2026-08-16-week3-triton-rayserve.md), 실행 런북은 `articles/3주차-00`~`-03`. 마감 **2026-08-23(일) 09:00**.
> **첫 행동**: Triton·ray-llm 이미지 풀을 **별도 창에서 사람이 직접** 띄우기 → 그다음 C3(Ray Serve) 배포 + 계층 오버헤드 측정(안전판).
> 순서는 **C3 → B3(KV cache 스윕) → C2(Triton)** 이며, C3까지만 해도 글 한 편이 섭니다. GPU 1장이라 셋은 배타적입니다.
>
> ⚠️ 이 머신에서 **백그라운드 태스크가 반복 강제 종료**됩니다. 긴 측정은 포그라운드로 돌리고, `0-1` keeper(`wsl -d Ubuntu -u root -- sleep infinity`)는 **사람이 별도 PowerShell 창에서** 띄우세요 — 죽으면 WSL 유휴 poweroff로 k3s 파드가 내려갑니다.
>
> `study/`(노션 원문)가 **복귀했습니다** — `Ch1~Ch6.md` + `LLM기초.md`. 3주차 판단 근거가 대부분 여기서 나왔습니다. **커밋 대상 아님**(gitignore + 인덱스 제외, 0건 확인).

## Snapshot

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13, 총 7주) 자료 정리 저장소. 한국어 학습 문서 모음 + 문서·PDF 탐색용 로컬 인덱싱 도구 + **WSL2 GPU 실측용 랩 4종**입니다. 게이트는 오프라인·결정론적("문서와 인덱스가 어긋나지 않았는가" + labs 단위 테스트 91건)이고, **실제 GPU 측정은 게이트 밖**입니다. 현재 **1·2주차 완료·제출 완료**, **3주차(CH5·CH6)는 방향 확정 + 실습 문서 5편 작성 완료·측정 미시작**.

핵심 설계는 **인덱스 파이프라인의 역할 분리**입니다 — 트리는 `build_pageindex.py`가 LLM 없이 결정론적으로 만들고, `summary`만 `enrich_summaries.py`가 한국어로 교체합니다. 근거는 `index/README.md` §2 실측 기록.

## Active Work

Authority: `docs/NEXT_PLAN.md`.

1. **3주차 과제 — 이월했던 C3(Ray Serve)·C2(Triton)를 수행.** 근거: Ray Serve는 **CH4 공식 도전과제**, Triton dynamic batching은 **CH6 본문**(vLLM엔 그 모드가 없어 vLLM으로는 실측 불가). 여기에 **B3(KV cache 상한 = 공식 도전과제 2)** 를 C3 환경 위에 얹음.
2. 과제 마감은 **매주 일요일 09:00**, 미공유 1회 = 제명. 다음 마감 08-23.
3. C1(교재 자작 배칭, `async def` 발견)은 계속 이월 — CH3 주제라 이번 주와 어긋남.

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
