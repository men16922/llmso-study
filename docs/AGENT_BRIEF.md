# Agent Brief

Last Updated: 2026-08-29

세션 시작용 압축 컨텍스트(≤60줄). 상세는 필요할 때만 링크 문서를 여세요.

> ▶ NEXT SESSION: **4주차는 ⑦ 과제 제출만 남았고, 사용자가 직접** 합니다(본인이 그렇게 결정). 마감 **2026-08-30(일) 09:00** · 미공유 1회 = 제명.
> 발행된 글: <https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234> (`워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식`) — **08-29에 3주차 발행본을 기준으로 구조·문체를 다시 정리하고 인증샷 4장까지 반영 완료.** 로컬·노션 동일.
> ⚠️ **제출표는 이 노션 연결로 안 잡힙니다** — `get-teams`가 `최병민 HQ` 하나, `list-shared-pages`는 비어 있음. 스터디 멤버 전용 워크스페이스는 별도라 에이전트가 대신 제출할 수 없습니다. 상세는 `docs/NEXT_PLAN.md` ⑦.
> 기록: [`docs/plans/2026-08-27-week4-execution.md`](./plans/2026-08-27-week4-execution.md) · 측정 분석 `labs/wsl2-vllm-baseline/results/e-analysis.md`·`e4-scheduler-notes.md`.
>
> **글의 축 한 줄**: 켜면 이득인 최적화는 없다. 세 기법이 전부 **조건부**이고 조건은 셋 다 **한 스텝의 토큰 예산에 여유가 있는가**(= compute-bound vs memory-bound). 셋이 vLLM 스케줄러의 **같은 `token_budget`**을 상한(E2)·시작점(E3)·끝점(E1)에서 건드린다.
>
> ★ **최대 발견 둘**
> 1. `prefill` c=64에서 **수용률 100%인데 −53.7%** — 손해가 "틀려서"가 아니라 **"맞아도 쓸 예산이 없어서"**. 워크로드별로 갈라 재지 않았으면 못 봤다(합산 68.7%는 설명력 0).
> 2. **draft-0.5B 팔은 KV 예산 −42.2%** 라 같은 저울에 못 올렸는데, 그게 축을 더 증명했다 — ngram은 예산을 안 뺏어 +199.3%, draft는 예산을 먹고 시작해 같은 지점 −4.1%. `decode` c=64 **goodput 0.0%**.
>
> **다음에 할 만한 것**: **커밋 정리(미커밋 67건)** · 5주차 예습 · 이월분(C1 교재 자작 배칭, 배칭 4종 표의 "없음"·"static") · **AWS GPU 쿼터 신청**(값 `0`, 6주차 EKS가 걸림, 사용자가 콘솔에서 직접).
>
> ★ **노션 발행 = 로컬 원고 + 변환 5단계**(3주차 대조로 확인): ①요약→callout 3불릿 ②헤딩 em-dash 부제→평서 발견문 ③환경·한계·부록 토글 ④`결론` 장 삭제 후 지침형 마지막 장에 흡수 ⑤제목 단정형→중립형. 4주차도 **①~⑤ 모두 적용 완료**. 도구 `tools/md_to_notion.py --toggle-h2` + 콜아웃 후처리.
>
> **환경 메모 (다음에도 걸릴 것)**
> - keeper는 `Start-Process wsl.exe ... 'sleep','infinity' -WindowStyle Hidden` **독립 프로세스**(창 안 지켜도 됨, **재부팅하면 다시**). `.wslconfig`의 `vmIdleTimeout=-1`은 **안 먹습니다.**
> - ⚠️ **`docker run vllm/...` 금지** — 이미지가 k3s containerd에만 있어 ~10GB를 새로 받습니다. 이유는 디스크가 아니라 **통제 변수**(2주차 B1과 같은 경로 유지). `docs/DECISIONS.md` 2026-08-27 참조.
> - 실험 플래그는 매니페스트 **`EXTRA_ARGS` env** 한 곳으로만(따옴표 없이 전개 — `test_manifest.py`가 감시). 플래그 이름은 **`vllm serve --help=all`** 로 확인(`--help`는 그룹 이름만, v0.23.0은 평탄화된 **`--spec-*`**).
> - Windows 게이트는 `PYTHONIOENCODING=utf-8 py -3 ...`.

## Snapshot

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13, 총 7주) 자료 정리 저장소. 한국어 학습 문서 모음 + 문서·PDF 탐색용 로컬 인덱싱 도구 + **WSL2 GPU 실측용 랩 4종**입니다. 게이트는 오프라인·결정론적("문서와 인덱스가 어긋나지 않았는가" + labs 단위 테스트 **106건**)이고, **실제 GPU 측정은 게이트 밖**입니다. 현재 **1·2·3주차 완료·제출 완료**, **4주차(CH7·CH8)는 측정·글·노션 발행까지 완료 — 링크 공유만 남음(마감 08-30)**.

## Active Work

Authority: `docs/NEXT_PLAN.md`.

1. **4주차 과제 (CH7·CH8) — 발행·재구성·인증샷까지 완료, 링크 공유만 남음.** 실험 4종 전부 측정됨: E1 추측 디코딩(+199.3% ~ −53.7%) · E2 chunked prefill(ITL 무차별, TTFT 18배) · E3 prefix caching(2×2 중 한 칸만 8배) · E4 스케줄러 소스 해부.
2. 과제 마감은 **매주 일요일 09:00**, 미공유 1회 = 제명. 다음 마감 **08-30**.
3. 이월분 — C1(교재 자작 배칭, `async def` 발견) · 배칭 4종 표의 "없음"·"static" 칸 · E1 draft-0.5B 팔(선택).

## Read Order

`docs/STATUS.md`(현재 상태) → `docs/NEXT_PLAN.md`(다음 작업) → `docs/PROGRESS_LOG.md`(최근 기록). 저장소 자체 규칙(깨지기 쉬운 지점·콘텐츠 정책)은 `CLAUDE.md`.

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
