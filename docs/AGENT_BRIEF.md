# Agent Brief

Last Updated: 2026-08-23

세션 시작용 압축 컨텍스트(≤60줄). 상세는 필요할 때만 링크 문서를 여세요.

> ▶ NEXT SESSION: **4주차(CH7·CH8) 과제 착수.** 마감 **2026-08-30(일) 09:00**. 3주차는 08-23 마감 통과했습니다.
> 설계 스냅샷은 [`docs/plans/2026-08-23-week4-conditional-optimization.md`](./plans/2026-08-23-week4-conditional-optimization.md), 체크리스트는 `docs/NEXT_PLAN.md` Priority 0.
>
> **글의 축 한 줄**: CH7의 기법들은 전부 **조건부로만 이득**이고, 조건은 하나의 축(**compute-bound vs memory-bound**)이며, 그 조건이 코드 어디에 있는지는 **CH8의 vLLM 스케줄러**가 답한다.
>
> **다음에 손댈 것 (순서대로)**
> 1. ⚠️ **`df -h` 먼저.** 그다음 `docker run --rm vllm/vllm-openai:v0.23.0 --help`로 플래그·메트릭 이름 확인 — 추측 금지.
> 2. `benchmark.py`에 공유 프리픽스 워크로드 옵션 추가 (`[auto]`, 오프라인 테스트 가능)
> 3. 실험 B(추측 디코딩)부터. 유일하게 다운로드가 있고 실패 가능성이 가장 높아 앞에 둡니다.
>
> **이번 주 통제 변수 원칙**: A·B·C를 **전부 `vllm/vllm-openai:v0.23.0` 하나 위에서** 돕니다(이미 로컬, 추가 다운로드 0). A를 ray-llm(0.7.2, V0)에서 돌리면 그것만 다른 엔진 숫자가 되어 같은 표에 못 넣습니다 — 3주차에 데인 자리입니다.
>
> **범위 확정**: 랩톱 GPU 1장(RTX 4080 12GB)만. 멀티GPU 도전과제·SGLang·TensorRT-LLM은 한계 절에 "왜 못 재는지"로 씁니다. ⚠️ **AWS GPU 쿼터는 `0`**(08-23 확인, 신청 이력 없음) — 6주차 EKS가 걸려 있어 사용자가 콘솔에서 신청해야 합니다(us-east-1 / `L-DB2E81BA` / 값 32). Windows 게이트는 `PYTHONIOENCODING=utf-8 py -3 ...`.

## Snapshot

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13, 총 7주) 자료 정리 저장소. 한국어 학습 문서 모음 + 문서·PDF 탐색용 로컬 인덱싱 도구 + **WSL2 GPU 실측용 랩 4종**입니다. 게이트는 오프라인·결정론적("문서와 인덱스가 어긋나지 않았는가" + labs 단위 테스트 91건)이고, **실제 GPU 측정은 게이트 밖**입니다. 현재 **1·2·3주차 완료·제출 완료**(3주차 마감 08-23 통과), **4주차(CH7·CH8) 착수 — 마감 08-30**.

핵심 설계는 **인덱스 파이프라인의 역할 분리**입니다 — 트리는 `build_pageindex.py`가 LLM 없이 결정론적으로 만들고, `summary`만 `enrich_summaries.py`가 한국어로 교체합니다. 근거는 `index/README.md` §2 실측 기록.

## Active Work

Authority: `docs/NEXT_PLAN.md`.

1. **4주차 과제 (CH7·CH8)** — 실험 4종: **B 추측 디코딩**(주인공, 저동시성 이득·고동시성 역효과) · **A chunked prefill**(3주차 이월분, PD 분리의 GPU 1장 대역) · **C prefix caching** · **D vLLM 스케줄러 해부**(설명층). A·B·C 전부 추가 다운로드가 사실상 0입니다.
2. 과제 마감은 **매주 일요일 09:00**, 미공유 1회 = 제명. 다음 마감 **08-30**.
3. 3주차 결론(글에 발행됨): **구조가 설정의 상한을 정한다** · **계층 가격은 요청 경로에 서 있는지가 가른다**(KServe −2.2% / Triton −12.6% / Ray Serve −70.0%).
4. 이월분 — C1(교재 자작 배칭, `async def` 발견) · 배칭 4종 표의 "없음"·"static" 칸. (chunked prefill은 4주차 실험 A로 흡수)

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
