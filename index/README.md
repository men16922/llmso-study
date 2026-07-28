# PageIndex 적용 검토 및 로컬 인덱스

이 폴더는 [PageIndex](https://github.com/VectifyAI/PageIndex)를 이 저장소에 적용할 수 있는지 검토하고, **PageIndex와 동일한 스키마의 트리 인덱스를 로컬에서 생성한 결과**입니다.

---

## 1. PageIndex란

**벡터 없는(vectorless), 추론 기반 RAG**입니다. 임베딩 유사도 대신 사람이 목차를 훑듯 문서를 탐색합니다.

| 단계 | 내용 |
|---|---|
| **① Tree Structure Indexing** | 문서를 인위적 chunk가 아니라 **목차 형태의 의미 계층**으로 변환. 각 노드는 `title` · `page range` · `summary` 보유 |
| **② Reasoning-Based Retrieval** | LLM이 트리를 타고 내려가며 관련 섹션을 선택. 결과가 특정 페이지·섹션을 가리키므로 **추적·설명 가능(traceable & explainable)** |

- 입력: **PDF, Markdown**
- 출력: `./results/{filename}_structure.json`
- 벤치마크: 금융 문서에서 98.7% 정확도 (자사 주장)

### 노드 스키마

```json
{
  "title": "Financial Stability",
  "node_id": "0006",
  "start_index": 21,
  "end_index": 22,
  "summary": "The Federal Reserve ...",
  "nodes": [ { "...": "child nodes" } ]
}
```

---

## 2. 이 저장소에 적합한가 — 판단

### 적합하다고 본 이유

| 근거 | 설명 |
|---|---|
| **자료가 "긴 문서" 중심** | PDF 3종 **527페이지**. 청크 기반 벡터 RAG는 "5.3.2 Where to Store the KV Cache" 같은 섹션 경계를 뭉갠다 |
| **이미 목차가 훌륭함** | 3종 중 2종이 **PDF 내장 TOC 보유**(146 · 54 항목). 트리를 새로 추론할 필요가 거의 없다 |
| **탐색 질의가 "어디에 있나" 형태** | 스터디 중 질문은 "KV cache 사이징은 어느 자료 몇 페이지?"에 가깝다. 페이지를 정확히 가리키는 게 유사도 top-k보다 유용 |
| **문서가 계속 늘어남** | 주차별 정리가 추가되므로 재생성 가능한 인덱스가 필요 |

### 그대로 쓰기 어려웠던 이유 ⚠️

| 장벽 | 실제 확인 결과 |
|---|---|
| **PyPI 패키지는 클라우드 SDK** | `pip install pageindex`(v0.2.8, 6KB)를 받아 열어보니 `PageIndexClient` 하나뿐 — `api.pageindex.ai`로 업로드하는 래퍼. **PageIndex 클라우드 API 키 필요** |
| **셀프호스팅은 OpenAI 키 필요** | GitHub의 `run_pageindex.py`는 트리 생성·요약 전 과정에서 LLM 호출. 기본 모델 `gpt-4o` |
| **키가 없음** | 현재 환경에 `OPENAI_API_KEY` 등 LLM 키 없음 (확인함) |
| **문서를 외부로 업로드** | 노션 자료는 **외부 공개·전파 금지**([스터디 규칙](../knowledge/03-study-rules.md)). 클라우드 API에 통째로 올리는 건 정책상 부적절 |
| **비용** | 527페이지 × 노드별 요약 LLM 호출. 반복 재생성 시 누적 |

### 결론

> **스키마는 채택하고, 트리 생성은 로컬에서 결정론적으로 한다.**
>
> PDF 2종은 이미 내장 TOC가 있어 **LLM으로 트리를 "추론"할 이유가 없습니다.** TOC를 그대로 읽으면 더 정확하고, 공짜이고, 재현 가능합니다. 나머지 1종은 목차 페이지를 파싱해 사이드카 파일로 보관했습니다.
>
> 결과 JSON이 PageIndex 스키마와 동일하므로, 나중에 API 키가 생기면 **같은 파일을 덮어쓰는 것만으로 진짜 PageIndex로 갈아탈 수 있습니다.**

---

## 3. 생성된 인덱스

`python3 tools/build_pageindex.py` 로 생성 · 재생성합니다. (총 **503 노드**, 243 KB)

| 파일 | 대상 | 노드 | 트리 출처 |
|---|---|---|---|
| [`inference-engineering-2026_structure.json`](./inference-engineering-2026_structure.json) | 259p PDF | 146 | PDF 내장 TOC |
| [`gpu-enabled-platforms-on-kubernetes-v2-2026_structure.json`](./gpu-enabled-platforms-on-kubernetes-v2-2026_structure.json) | 202p PDF | 86 | 사이드카 (`tools/toc/`) |
| [`nhn-cloud-factoryx-gpu-whitepaper-2026_structure.json`](./nhn-cloud-factoryx-gpu-whitepaper-2026_structure.json) | 66p PDF | 54 | PDF 내장 TOC |
| [`knowledge_structure.json`](./knowledge_structure.json) | `knowledge/` md 20개 | 217 | 마크다운 헤딩 |

### 진짜 PageIndex와 다른 점 (정직하게)

| 항목 | PageIndex | 여기 |
|---|---|---|
| 트리 생성 | LLM이 문서를 읽고 구조 추론 | **내장 TOC / 헤딩을 그대로 사용** |
| `summary` | LLM 생성 요약 | **발췌(extractive)** — 해당 구간 앞부분을 다듬어 잘라냄 |
| 검색 | LLM이 트리를 추론하며 순회 | 키워드 스코어링 (`tools/search_index.py`) |
| 비용 / 재현성 | API 비용 발생, 비결정론적 | **0원, 결정론적** |

각 JSON의 `meta.summary_method`에 이 사실을 표기했습니다. 요약이 비어 있는 노드가 **71개(14.1%)** 있는데, 대부분 본문 없이 하위 제목만 있는 중간 노드나 표만 있는 섹션입니다.

---

## 4. 사용법

### 인덱스 재생성

```bash
python3 tools/build_pageindex.py            # 전체
python3 tools/build_pageindex.py --only pdf # PDF만
python3 tools/build_pageindex.py --only md  # 마크다운만 (문서 수정 후)
```

필요 패키지: `pymupdf` (PDF 처리용, 이미 설치되어 있음)

### 탐색

```bash
# 키워드로 노드 찾기
python3 tools/search_index.py "KV cache"
python3 tools/search_index.py "MIG" --doc gpu-enabled --top 15

# 문서 목차 보기
python3 tools/search_index.py --outline inference-engineering --depth 2
```

실행 예:

```
$ python3 tools/search_index.py "KV cache" --top 3
'KV cache' → 13개 노드 매칭 (상위 3개)

 1. [ 176.0] inference-engineering-2026.pdf  p.141-141
      Table of Contents › Chapter 5: Techniques › 5.3 Caching
      ▸ 5.3.2 Where to Store the KV Cache
        The KV cache is very valuable. But KV caches take up a lot of memory, and GPUs…
```

→ **"KV cache 어디에 저장하나"가 궁금하면 Inference Engineering 141쪽**임을 바로 알 수 있습니다. 벡터 DB도, API 키도 없이.

---

## 5. 진짜 PageIndex로 업그레이드하려면

LLM 요약 품질이나 추론 기반 검색이 필요해지면:

### A. 셀프호스팅 (OpenAI 키)

```bash
git clone https://github.com/VectifyAI/PageIndex.git
cd PageIndex && pip3 install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env

python3 run_pageindex.py \
  --pdf_path "../knowledge/references/pdf/inference-engineering-2026.pdf" \
  --if-add-node-summary yes
# → results/inference-engineering-2026_structure.json
```

생성된 파일을 이 폴더에 덮어쓰면 `tools/search_index.py`가 **그대로 동작**합니다 (스키마 동일).

> ⚠️ 문서가 OpenAI로 전송됩니다. 노션 출처 자료의 외부 전파 금지 정책을 고려해 판단하세요. 위 3종 PDF는 **공개 배포 자료**라 상대적으로 부담이 적지만, `knowledge/` 정리 문서는 스터디 내부 자료입니다.

### B. 클라우드 API / MCP

```python
from pageindex import PageIndexClient
client = PageIndexClient(api_key="...")
doc = client.submit_document("....pdf")
```

OCR 강화판과 MCP 연동이 제공됩니다. 다만 **문서 업로드가 전제**입니다.

### C. 지금 구조를 유지하며 요약만 개선

가장 현실적인 중간 지점입니다. `tools/build_pageindex.py`의 `make_summary()`만 LLM 호출로 바꾸면 트리는 그대로 두고 요약 품질만 올릴 수 있습니다. 트리가 이미 정확하므로 **LLM은 요약에만 쓰면 됩니다.**

---

## 6. 앞으로

- 주차별 정리 문서가 추가되면 `--only md`로 재생성
- 새 PDF를 받으면 `knowledge/references/pdf/`에 넣고 재생성 (내장 TOC 없으면 `tools/toc/<이름>.json` 추가)
- `index/*.json`은 생성물이지만 **커밋해 두는 것을 권장** — 재생성 없이 바로 탐색 가능하고, 문서 구조 변화가 diff로 보임
