# Engineering Interpretation — llmso-study

`docs/engineering/*_ENGINEERING.md`(바이블)이 정의한 **일반 개념**을 이 저장소의 **실제 파일·명령·메커니즘**에 매핑한 문서입니다. 바이블은 "무엇을/왜"(이식 가능), 이 문서는 "이 저장소에서 어떻게"(저장소 고유)를 담습니다.

> **이 저장소의 특수성**: 애플리케이션이 아니라 CloudNet@ LLMSO 스터디(2026-08-02 ~ 09-13)의 **한국어 학습 문서 모음 + 인덱싱 도구**입니다. 빌드 산출물도 런타임도 없습니다. 따라서 "컴파일되는가"가 아니라 **문서와 인덱스가 서로 어긋나지 않았는가**가 검증의 전부입니다. 자율 루프가 할 수 있는 일도 문서 작업에 한정됩니다.

## HARNESS — 성숙도 / 검증 / 권한 (바이블 `HARNESS_ENGINEERING.md`)

- **gate**: `make check` (= `make check-docs` + `make check-labs`) — `.claude/harness-config.json`의 `gate`
- **permission boundary**: `scripts/overnight/overnight-settings.json`
  - 이 저장소의 실제 위험은 "코드를 망가뜨림"이 아니라 아래 넷입니다. DENY 목록은 이 넷을 겨냥합니다.
    1. **구독 사용량 소진** — `tools/enrich_summaries.py`(문서당 5~14분), `tools/pageindex_claude.py`(259쪽 PDF면 호출 수백 회) → deny
    2. **LLM 한국어 요약 파괴** — `build_pageindex.py`를 PDF 포함해 재생성하면 `summary`가 발췌로 되돌아감 → 스크립트 직접 실행은 전부 deny, 안전한 `make index-md`만 allow
    3. **비용 발생** — `gcloud`/`aws`/`kubectl`/`terraform`/`docker`, `labs/*/benchmark*.py`(실제 엔드포인트 호출) → deny
    4. **자료 외부 유출** — 이 저장소는 **비공개 유지**가 규칙(`knowledge/03-study-rules.md`). `git push`/`gh`/`curl`/`WebFetch`/Notion·Gmail·Chrome MCP → deny
- **maturity / 다음 투자**: 게이트는 기계적 계층만 있습니다. 다음 투자 후보는 (a) 스터디 주차 ↔ 문서 존재 여부의 정합성 검사, (b) `CRITIC_PROMPT.md`로 한국어 서술 품질의 의미 계층 도입.

## LOOP — 무인 루프 (바이블 `LOOP_ENGINEERING.md`)

- **runner**: 플러그인 소유 (`make overnight-where`로 확인). 이 저장소는 벤더링하지 않습니다.
  - `harness_root`를 **핀 고정**했습니다 — 이 머신에는 `~/.codex` 아래에도 같은 플러그인 사본이 있어 자동 해석이 경로 정렬 때문에 Codex 사본(1.2.0)을 골랐습니다. 등록된 Claude 설치와 스킬을 일치시키기 위한 조치입니다.
- **backlog 태그**: `docs/NEXT_PLAN.md`의 `[auto]` / `[manual]` / `[blocked]`
- **iteration prompt**: 플러그인 기본값 사용 (`scripts/overnight/PROMPT.md` 없음)
- **skills**: `/sync` `/checkpoint` `/overnight-report` `/overnight-seed` `/tidy-docs` `/diagnose`

## VERIFICATION — 3계층 (바이블 `VERIFICATION_ENGINEERING.md`)

각 검사를 가능한 한 아래로(기계적 > 의미적 > 창의적) 밀어냅니다.

- **mechanical (gate)**: `make check` — 실제로 증명하는 것:
  | 검사 | 증명하는 것 |
  |---|---|
  | `links` | 마크다운의 상대 경로 링크·앵커가 실존하는 파일/헤딩(및 `<a id>`)을 가리킨다. 코드 펜스 안 예시는 제외 |
  | `index` | `index/*.json`이 PageIndex 스키마(`title`/`node_id`/`start_index`/`end_index`/`nodes[]`)를 지키고 구간이 뒤집히지 않았다. `documents[]`(마크다운 묶음)와 `structure`(PDF) 양쪽 형태를 모두 검사 |
  | `tools` | `tools/`·`scripts/`의 파이썬이 문법적으로 성립한다 |
  | `check-labs` | `labs/`의 벤치마크 스크립트 단위 테스트 (localhost mock HTTP, 네트워크·GPU 불필요, 약 1.4초) |

  네트워크·LLM·GPU를 쓰지 않고 같은 트리에 대해 항상 같은 결과를 냅니다.

- **semantic (critic)**: 현재 `OVERNIGHT_CRITIC=0`. 이 저장소의 "green인데 틀린" 사례는:
  - 링크는 살아 있는데 **가리키는 내용이 주차와 안 맞음** (예: 3주차 문서가 CH5가 아닌 내용을 설명)
  - 인덱스 스키마는 맞는데 `meta.summary_method`가 `extractive-*`로 되돌아가 **한국어 요약이 사라짐**
  - 한국어 문서 관례를 어기고 영어로 작성됨
  - 도입한다면 `CRITIC_PROMPT.example.md`를 복사해 위 세 가지를 불변식으로 적으세요.

- **creative (human)**: `[manual]` 기준 = **스터디 내용의 사실관계와 교재 대응**. 자율 루프는 PDF 쪽수 매핑이나 개념 설명의 정확성을 검증할 수 없습니다(원문 대조가 필요). 아침 검수 초점 = 새로 쓴 예습 노트의 **쪽수 인용이 실제 그 쪽에 있는가**, 과제 마감(매주 일요일 09:00) 관련 기술이 최신인가.

## AGENTIC — 멀티 에이전트 (바이블 `AGENTIC_ENGINEERING.md`)

단일 엔진(claude). 저장소 규모상 레인 분리·워크트리 격리의 이득이 없습니다. 도입 안 함.

## CONTEXT — 컨텍스트/문서 규율 (바이블 `CONTEXT_ENGINEERING.md`)

- **Read Path**: `docs/AGENT_BRIEF.md` → `docs/STATUS.md` → `docs/NEXT_PLAN.md` → `docs/PROGRESS_LOG.md`
- **line budget**: brief ≤60 · status/plan/log ≤120 (`harness-config.budgets`)
- **Resume Pointer**: `docs/AGENT_BRIEF.md` 최상단의 `▶ NEXT SESSION` 줄
- **archive**: `docs/archive/`
- ⚠️ `docs/`는 **하네스 운영 문서**이고, 스터디 내용은 `knowledge/`입니다. 둘을 섞지 마세요. `tools/build_pageindex.py --only md`는 저장소 전체를 순회하므로 `docs/`도 `index/knowledge_structure.json`에 들어갑니다.

## PROMPT — 프롬프트 계층 (바이블 `PROMPT_ENGINEERING.md`)

- **harness prompt**: 플러그인 기본 `PROMPT.md` (저장소 오버라이드 없음)
- **runtime/domain prompt**: `tools/enrich_summaries.py` 안의 한국어 요약 프롬프트 — 트리는 결정론적으로 두고 요약만 LLM에 맡기는 설계(C안)의 핵심. 근거는 `index/README.md` §2 실측 기록.
