# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 저장소의 성격

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13) 자료 정리 저장소입니다. 애플리케이션이 아니라 **한국어 학습 문서 모음 + 그 문서·PDF를 탐색하기 위한 로컬 인덱싱 도구**입니다. 빌드·린트·테스트 파이프라인이 없고, `tools/`의 독립 실행 Python 스크립트 4개가 전부입니다.

**모든 문서는 한국어로 작성합니다.** 새 문서를 만들거나 기존 문서를 고칠 때 이 관례를 따르세요.

## 명령

모든 명령은 저장소 루트에서 실행합니다. 유일한 외부 의존성은 `pymupdf`(PDF 파싱)이며, 인덱싱·탐색에 **LLM API 키는 필요 없습니다.**

```bash
pip install pymupdf

python3 tools/search_index.py "KV cache"                      # 개념이 어느 자료 몇 쪽인지 (일상적으로 쓰는 건 사실상 이것뿐)
python3 tools/search_index.py "MIG" --doc gpu-enabled --top 15
python3 tools/search_index.py --outline inference --depth 3    # 목차 출력

python3 tools/build_pageindex.py --only md                     # 마크다운 수정 후 (1초 미만, LLM 0회)
python3 tools/build_pageindex.py --only pdf                    # 새 PDF 추가 후
python3 tools/build_pageindex.py                               # 전체 — ⚠️ 아래 "깨지기 쉬운 지점" 참조

python3 tools/enrich_summaries.py --dry-run                    # 규모 가늠 (LLM 0회) — 반드시 먼저
python3 tools/enrich_summaries.py --doc nhn --max-depth 2 --limit 5
```

`--doc`은 부분 일치입니다: `inference` / `gpu-enabled` / `nhn` / `knowledge`.

상세 사용법과 시나리오·트러블슈팅은 [`index/USAGE.md`](./index/USAGE.md)에 있습니다.

## 인덱스 파이프라인 구조

세 스크립트가 하나의 파이프라인을 이루며, **역할 분리가 이 저장소 설계의 핵심**입니다 (근거는 [`index/README.md`](./index/README.md) §2 실측 기록).

```
build_pageindex.py  →  index/*.json  →  search_index.py
   (트리: 결정론)         ↑
                    enrich_summaries.py  (summary 필드만 LLM 교체)
```

1. **`build_pageindex.py`** — PageIndex와 동일한 JSON 스키마(`title` / `node_id` / `start_index` / `end_index` / `summary` / `nodes[]`)를 **LLM 없이** 생성합니다. 트리 출처는 PDF 내장 TOC → 없으면 `tools/toc/<파일명>.json` 사이드카, 마크다운은 헤딩입니다. `summary`는 해당 구간에서 잘라낸 **발췌**입니다.
2. **`enrich_summaries.py`** — 트리는 손대지 않고 `summary` 필드만 `claude -p`로 만든 **한국어 요약**으로 교체합니다.
3. **`search_index.py`** — 제목(가중치 10)·요약(3) 키워드 스코어링으로 후보 노드를 뽑습니다. 출력의 `p.NNN`(PDF 쪽) 또는 `LNNN`(마크다운 줄)을 원문에서 펼쳐 읽는 흐름입니다.

**왜 트리를 LLM에 맡기지 않는가**: PageIndex 본체를 Claude Code 백엔드로 두 번 실측한 결과, ① 같은 PDF인데 실행마다 노드 제목이 달라졌고(제목 일치 12/98) ② 한국어 문서인데 요약 98%가 영어로 나왔습니다. 그래서 **트리는 결정론적으로 고정하고 요약만 LLM에 맡기는** 지금 방식(C안)을 택했습니다. 실측 산출물은 `index/_verify/`에 보관되어 있으며, **이 폴더는 근거 보관용이지 탐색 대상이 아닙니다.**

각 JSON의 `meta.summary_method`가 현재 상태를 표시합니다 — `extractive-*`(발췌) 또는 `llm-claude-code-korean`(LLM 보강됨). 현재 Inference Engineering만 보강되어 있습니다.

`index/*.json`은 생성물이지만 **커밋합니다** (재생성 없이 바로 탐색 가능, 문서 구조 변화가 diff로 보임).

## 깨지기 쉬운 지점

- **`build_pageindex.py`를 PDF 포함해 재생성하면 LLM 한국어 요약이 발췌로 되돌아갑니다.** 마크다운만 고쳤다면 반드시 `--only md`를 쓰세요. 이미 되돌렸다면 `enrich_summaries.py`를 다시 돌리면 됩니다(해시 캐시가 있어 거의 공짜).
- **`--only md`는 `knowledge/`가 아니라 저장소 전체를 순회합니다** (`.git`, `.claude`, `node_modules`, `__pycache__`, `.venv` 제외). 루트 `README.md`도, **이 `CLAUDE.md`도** `index/knowledge_structure.json`에 들어갑니다. 마크다운을 추가·수정했으면 `--only md`로 인덱스를 갱신하세요.
- **`enrich_summaries.py`는 API 키 대신 Claude Code 구독 사용량을 씁니다.** 건당 7~12초(프로세스 기동), 전체 깊이면 문서당 5~14분입니다. 반드시 `--dry-run` → `--limit 5` 시험 → 실제 적용 순으로 진행하세요. `--doc` 없이 실행하면 전 문서가 대상이 됩니다.
- **캐시** `index/.summary_cache.json`은 노드 원문 해시 기준이며 용량 때문에 **커밋 제외**입니다. 지워도 무방하지만 재생성 비용이 다시 듭니다.
- **내장 TOC 없는 PDF를 추가하면** 루트 노드만 생기고 경고가 뜹니다. `tools/toc/<파일명>.json`에 `[레벨, 제목, 시작쪽]` 배열을 직접 만들어 넣으세요 (예시: `tools/toc/gpu-enabled-platforms-on-kubernetes-v2-2026.json`).
- **`tools/pageindex_claude.py`는 평소 쓰지 않습니다.** PageIndex 본체를 검증하려고 `litellm.completion`을 가로채 `claude -p`로 돌리는 실험용 스크립트입니다. 259쪽 PDF면 호출 수백 회 규모입니다.

## 콘텐츠 정책 (중요)

- **이 저장소는 비공개로 유지합니다.** 원본 노션은 멤버 전용이고 스터디 규칙상 외부 공개·전파가 금지되어 있습니다 ([`knowledge/03-study-rules.md`](./knowledge/03-study-rules.md)).
- `knowledge/references/pdf/`에 제3자 배포 PDF 3종(527p, 41.6MB)이, `index/*.json`에 그 PDF들의 짧은 발췌가 들어 있습니다. **공개 원격 저장소에 푸시하거나 문서를 외부 서비스에 업로드하는 작업은 먼저 확인을 받으세요.**
- 원문 그대로의 전재는 금지, **소화해서 자기 언어로 가공하는 것(블로그 등)은 권장**입니다.

## 실증 스크린샷 규칙 (중요)

- **"스크린샷"·"실증"·"인증샷"은 항상 실제 관측 화면의 캡처를 뜻합니다** — Prometheus·Grafana 대시보드, 또는 그에 준하는 실제 UI. 터미널 로그를 HTML/이미지로 렌더링한 "카드"나 데이터로 그린 차트를 스크린샷 자리에 넣지 마세요. 사용자가 두 번(2026-09-03) 이를 되돌렸습니다.
- 차트(`figures/*.svg`)는 **그림**으로만 쓰고 스크린샷이라 부르지 않습니다. 로그·오류 메시지는 코드 블록으로 인용합니다.
- 캡처는 한 곳에 몰지 말고 **해당 결론을 다루는 장 안에** 넣고, 시간 구간과 패널 이름을 캡션으로 적습니다.
- Grafana는 로그인이 필요해 에이전트가 캡처할 수 없습니다. Prometheus는 `kubectl port-forward` + `/query?g0.tab=graph`로 캡처합니다(`docs/STATUS.md` Open Risks).

## 문서 구조

- `knowledge/` — 스터디 정리 문서. `00`~`05` 번호 문서(개요·환경·과제·규칙·체크리스트·예습) + `subpages/`(노션 서브페이지 8종 실습 정리) + `references/`(외부 자료 단일 인덱스, `priority-guide.md`가 진입점)
- `index/` — 생성된 트리 인덱스. `USAGE.md`(사용법) / `README.md`(설계 근거·실측) / `_verify/`(실측 산출물)
- `tools/` — 위 스크립트 + `toc/` 사이드카 목차
- `logs/` — `pageindex_claude.py` 실행 부산물, gitignore 대상
