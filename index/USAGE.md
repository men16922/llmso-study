# 사용 가이드

인덱스와 도구를 **실제로 어떻게 쓰는지**만 다룹니다. 왜 이렇게 만들었는지(PageIndex 검토·실측)는 [README.md](./README.md)를 보세요.

모든 명령은 **저장소 루트에서** 실행합니다.

```bash
cd "~/Desktop/AI/Hands-On LLM Serving and Optimization Study"
```

---

## 30초 요약

일상적으로 쓰는 건 **사실상 하나뿐**입니다.

```bash
python3 tools/search_index.py "찾을 개념"
```

나머지 둘은 가끔 씁니다.

| 언제 | 명령 |
|---|---|
| **개념이 어느 자료 몇 쪽인지 찾을 때** (거의 매번) | `search_index.py "키워드"` |
| 문서를 고치거나 새 PDF를 넣었을 때 | `build_pageindex.py` |
| 요약을 한국어 LLM 요약으로 바꾸고 싶을 때 | `enrich_summaries.py --doc <문서>` |

---

## 1. 검색 — `search_index.py`

### 기본

```bash
python3 tools/search_index.py "speculative decoding"
```

```
'speculative decoding' → 12개 노드 매칭 (상위 3개)

 1. [ 116.0] inference-engineering-2026.pdf  p.133-133
      Table of Contents › Chapter 5: Techniques › 5.2 Speculative Decoding
      ▸ 5.2.1 Draft-Target Speculative Decoding
        두 개의 모델을 사용하는 원조 speculative decoding 방식으로, draft model이
        speculative draft token을 생성하고 target model이 그 draft token을 검증한다…
```

읽는 법:

| 부분 | 의미 |
|---|---|
| `[116.0]` | 매칭 점수 (제목 일치에 가중치 10, 요약 3) |
| `p.133-133` | **PDF 133쪽**을 펴면 된다 (마크다운이면 `L133` = 줄 번호) |
| `Table of Contents › Chapter 5 › 5.2` | 문서 안에서의 위치 (부모 경로) |
| `▸ 5.2.1 …` | 해당 노드 제목 |
| 그 아래 | 요약 발췌 (검색어 주변을 잘라 보여줌) |

### 한국어로도 찾을 수 있습니다

Inference Engineering은 영문 원서지만 요약을 한국어로 만들어 두어서 한국어 질의가 통합니다.

```bash
python3 tools/search_index.py "양자화"
python3 tools/search_index.py "메모리 대역폭"
python3 tools/search_index.py "커널 퓨전"
```

> 다른 PDF 2종은 아직 발췌(원문 언어) 요약입니다. 한국어 검색이 필요하면 [3번](#3-요약-보강--enrich_summariespy)으로 보강하세요.

### 옵션

```bash
# 결과 개수
python3 tools/search_index.py "KV cache" --top 20

# 특정 자료 안에서만
python3 tools/search_index.py "MIG" --doc gpu-enabled
python3 tools/search_index.py "prefill" --doc inference

# 여러 단어 (모두 걸리는 노드가 크게 우대됨)
python3 tools/search_index.py "prefill decode 분리"
```

`--doc`에 쓸 수 있는 이름(부분 일치):

| 축약 | 대상 |
|---|---|
| `inference` | Inference Engineering (259p) |
| `gpu-enabled` | GPU-Enabled Platforms on Kubernetes (202p) |
| `nhn` | NHN Cloud GPU 백서 (66p) |
| `knowledge` | `knowledge/` 정리 문서 |

### 목차 보기

```bash
python3 tools/search_index.py --outline inference-engineering --depth 2
```

```
=== inference-engineering-2026.pdf ===
- Table of Contents  (p.5-10)
  - Preface  (p.11-16)
  - Chapter 0: Inference  (p.17-24)
  - Chapter 2: Models  (p.41-43)
  - Chapter 5: Techniques  (p.119-121)
  ...
```

`--depth 3`으로 올리면 절 단위까지 나옵니다.

---

## 2. 인덱스 재생성 — `build_pageindex.py`

**문서를 고치거나 새 자료를 넣은 뒤**에 돌립니다. LLM을 쓰지 않아 1초 안에 끝납니다.

```bash
python3 tools/build_pageindex.py            # 전체
python3 tools/build_pageindex.py --only md  # 마크다운만 (문서만 고쳤을 때)
python3 tools/build_pageindex.py --only pdf # PDF만
```

> ⚠️ `--only pdf`나 전체 재생성은 **LLM 요약을 발췌 요약으로 되돌립니다.** Inference Engineering의 한국어 요약을 유지하려면 문서 수정 후에는 `--only md`를 쓰거나, 재생성 후 [3번](#3-요약-보강--enrich_summariespy)을 다시 돌리세요(캐시가 있어 비용은 거의 안 듭니다).

### 새 PDF를 추가할 때

1. `knowledge/references/pdf/` 에 넣는다
2. `python3 tools/build_pageindex.py --only pdf`
3. 내장 목차가 없으면 이런 메시지가 나옵니다:

```
! <이름>: 내장 TOC 없음, 사이드카(tools/toc/<이름>.json)도 없음 → 루트 노드만 생성
```

이때는 목차를 직접 만들어 `tools/toc/<파일명>.json`에 넣습니다. 형식은 `[레벨, 제목, 시작쪽]`:

```json
[
  [1, "Chapter 1. 제목", 7],
  [2, "1.1 절 제목", 8],
  [3, "1.1.1 소절", 11]
]
```

기존 예시: [`tools/toc/gpu-enabled-platforms-on-kubernetes-v2-2026.json`](../tools/toc/gpu-enabled-platforms-on-kubernetes-v2-2026.json)

---

## 3. 요약 보강 — `enrich_summaries.py`

발췌 요약을 **LLM 한국어 요약**으로 교체합니다. 트리(제목·쪽수)는 건드리지 않습니다.

`claude -p`를 쓰므로 **API 키는 필요 없지만 Claude Code 사용량을 소모**합니다. 반드시 규모부터 보세요.

```bash
# ① 비용 가늠 (LLM 호출 0)
python3 tools/enrich_summaries.py --dry-run

# ② 소규모 시험 (5건만)
python3 tools/enrich_summaries.py --doc nhn --max-depth 2 --limit 5

# ③ 실제 적용
python3 tools/enrich_summaries.py --doc nhn --max-depth 0
```

### 옵션

| 옵션 | 의미 |
|---|---|
| `--doc <이름>` | 대상 문서 (부분 일치). **생략하면 전부** — 권장하지 않음 |
| `--max-depth N` | 깊이 N 미만만. 기본 **2**(상위 2단계). `0`이면 전체 깊이 |
| `--limit N` | 문서당 최대 N건 (시험용) |
| `--dry-run` | 대상 개수·예상 시간만 출력 |

### 문서별 규모 (`--max-depth 0` 기준)

| 문서 | 노드 | 대략 소요 |
|---|---|---|
| Inference Engineering | 145 | ~12분 ✅ **적용 완료** |
| GPU on K8s | 81 | ~7분 |
| NHN 백서 | 54 | ~5분 |
| 마크다운 전체 | 171 | ~14분 |

### 캐시

노드 원문 해시로 캐시하므로 **중단 후 다시 돌려도 만든 건 건너뜁니다**. 재생성 후 다시 돌릴 때도 거의 공짜입니다.

- 위치: `index/.summary_cache.json` (용량 때문에 커밋 제외)
- 지우고 싶으면 그냥 삭제하면 됩니다

### 적용 여부 확인

```bash
python3 -c "
import json,glob
for f in glob.glob('index/*.json'):
    d=json.load(open(f,encoding='utf-8'))
    print(f\"{f.split('/')[-1]:52} {d['meta']['summary_method']}\")
"
```

`llm-claude-code-korean` = 보강됨, `extractive-*` = 발췌 상태.

---

## 4. (참고) 진짜 PageIndex 실행 — `pageindex_claude.py`

평소엔 쓸 일이 없습니다. PageIndex 본체를 Claude Code 백엔드로 돌려보는 **검증용** 스크립트입니다.

```bash
git clone https://github.com/VectifyAI/PageIndex.git /tmp/PageIndex
pip install PyPDF2

python3 tools/pageindex_claude.py \
  --pageindex /tmp/PageIndex \
  --pdf knowledge/references/pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf \
  --out /tmp/out --no-summary
```

실측 결과와 왜 채택하지 않았는지는 [README.md §2](./README.md)에 있습니다. 요약하면 **트리가 실행마다 바뀌고(제목 98개 중 12개만 일치) 한국어 문서를 영어로 요약**해서, 트리는 로컬로 두고 요약만 LLM에 맡기는 지금 방식을 택했습니다.

---

## 시나리오별

### 스터디 중 "이거 어느 자료에 있더라?"

```bash
python3 tools/search_index.py "chunked prefill"
```

→ 나온 `p.NNN`을 PDF에서 펴면 됩니다.

### 과제 쓸 때 근거 찾기

```bash
# 주제를 정하고 관련 노드를 넓게 훑기
python3 tools/search_index.py "disaggregation" --top 20

# 그 챕터 전체 구조 확인
python3 tools/search_index.py --outline inference --depth 3
```

### 다음 주 예습 범위 잡기

```bash
python3 tools/search_index.py --outline inference --depth 2
```

→ [`knowledge/references/priority-guide.md`](../knowledge/references/priority-guide.md)의 주차별 매핑과 대조해서 읽을 쪽수를 정합니다.

### 정리 문서를 고친 뒤

```bash
python3 tools/build_pageindex.py --only md
```

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `index/ 가 없습니다` | `python3 tools/build_pageindex.py` 를 먼저 실행 |
| `PyMuPDF(fitz)가 필요합니다` | `pip install pymupdf` |
| 검색 결과 0개 | 다른 표현으로 재시도. 영문 PDF는 한국어 요약이 없으면 한국어 질의가 안 걸림 → [3번](#3-요약-보강--enrich_summariespy) |
| 한국어 요약이 사라짐 | `build_pageindex.py`를 PDF 포함해 재생성한 것. `enrich_summaries.py`를 다시 실행(캐시로 빠름) |
| `enrich_summaries.py`가 느림 | 정상입니다. `claude -p` 프로세스 기동에 건당 7~12초. `--max-depth 2`로 범위를 줄이세요 |
| `claude -p 실패` | Claude Code 로그인 상태 확인. 사용량 한도일 수도 있음 |

---

## 정리

```
평소       search_index.py "키워드"          ← 이것만 기억하면 됨
문서 수정  build_pageindex.py --only md
새 PDF     PDF 넣고 → build_pageindex.py --only pdf → (목차 없으면 tools/toc/ 추가)
요약 보강  enrich_summaries.py --dry-run → --doc X --limit 5 → --doc X
```
