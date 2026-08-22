# Agent Brief

Last Updated: 2026-08-23

세션 시작용 압축 컨텍스트(≤60줄). 상세는 필요할 때만 링크 문서를 여세요.

> ▶ NEXT SESSION: **3주차 과제 — 노션 재발행 + 링크 공유가 남았습니다.** 마감 **2026-08-23(일) 09:00**.
> 원고는 [`articles/서빙 최적화, 설정부터 만지면 안 되는 이유.md`](../articles/) — 이전 원고 `슬롯을 4배로...`를 **대체**합니다(주제 재구성). 노션 페이지 https://app.notion.com/p/3c44c2420ac48157aaebe78f971e05c9 를 이 내용으로 갱신하면 됩니다.
> 측정은 **계층 3종 + 각각의 짝** 전부 완료돼 `labs/wsl2-vllm-baseline/results/`에 있습니다.
>
> **글의 결론 한 줄**: 서빙 최적화는 **구조를 먼저 고르고 그 위에서 설정을 조인다**. 계층 가격을 가르는 건 구현 품질이 아니라 **요청 경로에 서 있는가**다.
>
> **다음 실험을 설계할 때 알아둘 것**
> - **계층마다 품은 vLLM이 다릅니다** — Ray Serve 0.7.2 / Triton 0.5.5 / KServe 0.20.0. 비교 전에 반드시 양쪽 버전을 확인하고, **같은 이미지에서 계층만 뺀 짝**을 만드세요. 짝이 맞았는지는 기동 로그의 KV 예산으로 확인합니다.
> - **`vllm:*` 메트릭은 데이터 플레인 계층에서만 사라집니다** — Ray Serve·Triton은 0개, KServe(RawDeployment)는 66개 그대로. 서버 측 교차검증이 필요하면 KServe나 계층 없는 구성을 쓰세요.
> - **c=64 재현 측정은 10%까지 흔들립니다**(c≤32는 1.3% 안). 10%대 차이를 결론으로 쓰지 마세요.
> - **GPU 1장에서 롤링 업데이트는 교착합니다.** 옛 ReplicaSet을 0으로 내려야 새 파드가 GPU를 받습니다.
>
> ⚠️ **디스크 여유를 먼저 확인하세요.** Triton vLLM 이미지는 36.3GB입니다. 이번에 C: 잔여 공간을 소진해 WSL이 I/O 오류로 멈추고 k3s까지 죽었습니다.
>
> Windows에서 게이트·테스트는 `PYTHONIOENCODING=utf-8 py -3 ...`로 전부 돕니다.

## Snapshot

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13, 총 7주) 자료 정리 저장소. 한국어 학습 문서 모음 + 문서·PDF 탐색용 로컬 인덱싱 도구 + **WSL2 GPU 실측용 랩 4종**입니다. 게이트는 오프라인·결정론적("문서와 인덱스가 어긋나지 않았는가" + labs 단위 테스트 91건)이고, **실제 GPU 측정은 게이트 밖**입니다. 현재 **1·2주차 완료·제출 완료**, **3주차(CH5·CH6)는 계층 3종 측정 + 글 재작성 완료, 노션 재발행·링크 공유 대기**.

핵심 설계는 **인덱스 파이프라인의 역할 분리**입니다 — 트리는 `build_pageindex.py`가 LLM 없이 결정론적으로 만들고, `summary`만 `enrich_summaries.py`가 한국어로 교체합니다. 근거는 `index/README.md` §2 실측 기록.

## Active Work

Authority: `docs/NEXT_PLAN.md`.

1. **3주차 과제 — 계층 3종 측정 + 글 재작성 완료. 노션 재발행·링크 공유만 남음.** 결론: **구조가 설정의 상한을 정한다**(Ray Serve 위에서 설정 4종을 흔들어도 ±17%, 같은 슬롯 변경이 계층 없는 구성에서는 +139%) · **계층 가격은 요청 경로에 서 있는지가 가른다**(KServe −2.2% / Triton −12.6% / Ray Serve −70.0%, goodput 100·100·19%) · 같은 기준이 관측성도 설명한다(`vllm:*` 66 · 0 · 0개).
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
