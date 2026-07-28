# PageIndex 적용 검토 및 로컬 인덱스

이 폴더는 [PageIndex](https://github.com/VectifyAI/PageIndex)를 이 저장소에 적용할 수 있는지 검토하고, **PageIndex와 동일한 스키마의 트리 인덱스를 로컬에서 생성한 결과**입니다.

> 🔧 **바로 쓰는 법만 필요하면 → [USAGE.md](./USAGE.md)**
> 이 문서는 "왜 이렇게 만들었나"(검토 과정과 실측 근거)를 다룹니다.

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

### 진입 장벽

| 장벽 | 실제 확인 결과 |
|---|---|
| **PyPI 패키지는 클라우드 SDK** | `pip install pageindex`(v0.2.8, 6KB)를 받아 열어보니 `PageIndexClient` 하나뿐 — `api.pageindex.ai`로 업로드하는 래퍼. **PageIndex 클라우드 API 키 필요** |
| **셀프호스팅도 LLM 필요** | `run_pageindex.py`는 TOC 탐지·트리 생성·요약 전 과정에서 LLM 호출. 기본 모델 `gpt-4o` |
| **API 키가 없음** | 환경에 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` 없음 |
| **문서를 외부로 업로드** | 클라우드 API 경로는 노션 자료 **외부 전파 금지** 정책과 충돌 ([스터디 규칙](../knowledge/03-study-rules.md)) |

### ⚠️ 정정 — API 키는 필수가 아니었다

처음엔 "OpenAI 키가 필요하다"고 판단했지만 **틀렸습니다.** PageIndex는 `requirements.txt`에 `litellm==1.84.0`을 쓰고, `pageindex/config.yaml`에는 아래 줄이 **주석으로 이미 들어 있습니다**:

```yaml
model: "gpt-4o-2024-11-20"
# model: "anthropic/claude-sonnet-4-6"    ← Claude 공식 지원
```

즉 프로바이더 중립입니다. 나아가 **LLM 호출 지점이 `llm_completion` / `llm_acompletion` 두 개뿐**이라, 그 아래의 `litellm.completion`을 가로채면 **어떤 LLM이든** 붙일 수 있습니다.

그래서 [`tools/pageindex_claude.py`](../tools/pageindex_claude.py)를 만들어 **이미 로그인된 Claude Code(`claude -p`)를 백엔드로** 물렸습니다. API 키 0개로 진짜 PageIndex가 돕니다.

### 실측 검증 결과 (NHN 백서 66p, `--no-summary`)

| 항목 | 값 |
|---|---|
| LLM 호출 | **121회** (실패 0회) |
| 벽시계 시간 | **278초** (동시 3) |
| 입출력 | 입력 33.9만 자 / 출력 5.1만 자 |
| TOC 정확도 | PageIndex 자체 리포트 **100%** |
| 산출 노드 | **55개** |

**로컬 결정론 버전(LLM 0회, 1초 미만)과 비교:**

| 비교 항목 | 결과 |
|---|---|
| 노드 제목 | **54/54 완전 일치** (PageIndex에 `Preface` 1개 추가) |
| 페이지 범위 | 10개 노드가 다름 — PageIndex는 다음 섹션 시작까지 겹치게 잡고, 로컬은 겹치지 않게 자름 |
| **범위 오류(end < start)** | **PageIndex 2개** (`NHN FactoryX 기술 백서 p.2-1`, `08 부록 p.58-57`) / **로컬 0개** |

### 2차 실측 — 요약을 켜고 다시 (같은 PDF)

`--no-summary`를 빼고 한 번 더 돌렸습니다.

| 항목 | 1차 (요약 X) | 2차 (요약 O) |
|---|---|---|
| LLM 호출 | 121회 | **176회** |
| 시간 | 278초 | **508초** |
| 출력량 | 5.1만 자 | **15.7만 자** |
| 실패 | 0 | 0 |

**요약 품질은 확실히 좋습니다.** 평균 1,934자로, 제 발췌본(265자)과는 성격이 다릅니다. 예를 들어 `4.2.1 네트워크 병목` 노드는 증상(SM Activity 저하, NIC 버스트 패턴, All-Reduce가 스텝 시간의 30% 초과)·원인(oversubscribed 토폴로지, rail 정렬 실패, NCCL 미튜닝)·진단법까지 서술합니다. 발췌 방식으로는 절대 나올 수 없는 내용입니다.

**그런데 두 가지 문제가 드러났습니다.**

#### ① 실행 간 재현성이 낮다 ⚠️

두 실행은 `--no-summary` 여부만 달랐는데 **트리 제목이 달라졌습니다.**

| | 결과 |
|---|---|
| 두 실행 간 제목 일치 | **12개 / 합집합 98개** |
| 1차 | `1.1 문서의 목적과 범위`, `2.1.1 클러스터 계층 구조` … (**절 번호 유지**) |
| 2차 | `AI 전용 인프라 요구 사항`, `Compute Fabric 아키텍처` … (**번호 제거**) |

같은 PDF·같은 목차인데 LLM이 매번 다르게 정규화합니다. 인덱스를 다시 만들 때마다 노드 제목이 바뀌면 **북마크·인용·diff가 전부 깨집니다.**

#### ② 한국어 문서인데 요약이 영어로 나온다 ⚠️

요약 55개 중 **54개(98%)가 사실상 영어**입니다. NHN 백서는 한국어 문서인데도 그렇습니다. 한국어 스터디에서 쓰기엔 어색하고, 원문 용어와 대조가 어렵습니다.

### 최종 결론

> **기본값은 로컬 결정론 방식을 유지합니다.**
>
> - **트리**: LLM을 쓸 이유가 없음이 확인됨. 내장 TOC가 더 정확하고, 공짜이고, **재현 가능**함
> - **요약**: LLM 쪽이 내용은 확실히 풍부하나, **붙어 있는 트리가 매번 흔들리고 언어도 원문과 다름**
>
> 요약 깊이가 필요해지면 정답은 PageIndex 통째로가 아니라 **[5-C 경로](#c-plan)** 입니다 — 트리는 결정론적으로 두고 요약만 LLM에 맡기면, 재현성 문제와 언어 문제(프롬프트로 한국어 지정)를 동시에 피할 수 있습니다.
>
> 두 방식의 JSON 스키마가 같으므로 언제든 파일만 덮어쓰면 전환됩니다. 실측 산출물은 [`_verify/`](./_verify/)에 보관했습니다.

---

## 3. 생성된 인덱스

`python3 tools/build_pageindex.py` 로 생성 · 재생성합니다. (총 **612 노드**, 약 290 KB)

| 파일 | 대상 | 노드 | 트리 출처 |
|---|---|---|---|
| [`inference-engineering-2026_structure.json`](./inference-engineering-2026_structure.json) ★ | 259p PDF | 146 | PDF 내장 TOC + **LLM 한국어 요약** |
| [`gpu-enabled-platforms-on-kubernetes-v2-2026_structure.json`](./gpu-enabled-platforms-on-kubernetes-v2-2026_structure.json) | 202p PDF | 86 | 사이드카 (`tools/toc/`) |
| [`nhn-cloud-factoryx-gpu-whitepaper-2026_structure.json`](./nhn-cloud-factoryx-gpu-whitepaper-2026_structure.json) | 66p PDF | 54 | PDF 내장 TOC |
| [`knowledge_structure.json`](./knowledge_structure.json) | repo 내 md **25개** (루트 README 포함) | 326 | 마크다운 헤딩 |

### 진짜 PageIndex와 다른 점 (정직하게)

| 항목 | PageIndex | 여기 |
|---|---|---|
| 트리 생성 | LLM이 문서를 읽고 구조 추론 | **내장 TOC / 헤딩을 그대로 사용** |
| `summary` | LLM 생성 요약 | **발췌(extractive)** — 해당 구간 앞부분을 다듬어 잘라냄 |
| 검색 | LLM이 트리를 추론하며 순회 | 키워드 스코어링 (`tools/search_index.py`) |
| 비용 / 재현성 | API 비용 발생, 비결정론적 | **0원, 결정론적** |

각 JSON의 `meta.summary_method`에 어느 방식인지 표기했습니다 — `extractive-*`(발췌) 또는 `llm-claude-code-korean`(C안 적용).

**Inference Engineering은 C안을 적용했습니다** (아래 §5-C). 나머지는 발췌 방식입니다.

발췌 방식의 요약 추출은 3단계 폴백입니다: ① 자기 구간의 산문 → ② 비면 하위 트리까지 확장 → ③ 그래도 비면 **표 셀 내용까지** 긁음(이 저장소는 표 비중이 큼). 그 결과 빈 요약이 **71개(14.1%) → 19개(3.1%)** 로 줄었습니다. 남은 19개는 구분선·이미지만 있는 섹션입니다.

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

### A-0. Claude Code 백엔드 ★ 키 불필요 · 검증 완료

```bash
git clone https://github.com/VectifyAI/PageIndex.git /tmp/PageIndex
pip install PyPDF2                     # litellm은 스텁으로 대체하므로 설치 불필요

python3 tools/pageindex_claude.py \
  --pageindex /tmp/PageIndex \
  --pdf knowledge/references/pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf \
  --out index/ --no-summary
```

동작 원리: `litellm.completion` / `acompletion` / `token_counter`를 가로채 `claude -p`(헤드리스)로 돌립니다. litellm 실물이 없어도 `sys.modules`에 스텁을 꽂아 import를 만족시킵니다.

⚠️ **비용이 사라지는 게 아니라 옮겨갑니다** — API 크레딧 대신 **Claude Code 구독 사용량**을 씁니다. 66페이지 PDF 하나에 호출 121회였으니, 259페이지 PDF는 수백 회가 됩니다. `--dry-run`으로 먼저 규모를 가늠하세요.

### A. 셀프호스팅 (OpenAI / Anthropic API 키)

```bash
git clone https://github.com/VectifyAI/PageIndex.git
cd PageIndex && pip3 install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
# config.yaml 에서: model: "anthropic/claude-sonnet-4-6" (주석 해제)

python3 run_pageindex.py \
  --pdf_path "../knowledge/references/pdf/inference-engineering-2026.pdf" \
  --if-add-node-summary yes
# → results/inference-engineering-2026_structure.json
```

생성된 파일을 이 폴더에 덮어쓰면 `tools/search_index.py`가 **그대로 동작**합니다 (스키마 동일).

> ⚠️ 문서가 해당 프로바이더로 전송됩니다. 노션 출처 자료의 외부 전파 금지 정책을 고려해 판단하세요. 위 3종 PDF는 **공개 배포 자료**라 상대적으로 부담이 적지만, `knowledge/` 정리 문서는 스터디 내부 자료입니다.

### B. 클라우드 API / MCP

```python
from pageindex import PageIndexClient
client = PageIndexClient(api_key="...")
doc = client.submit_document("....pdf")
```

OCR 강화판과 MCP 연동이 제공됩니다. 다만 **문서 업로드가 전제**입니다.

<a id="c-plan"></a>

### C. 트리는 로컬, 요약만 LLM ★ 채택

실측 끝에 고른 방식입니다. [`tools/enrich_summaries.py`](../tools/enrich_summaries.py)가 **기존 인덱스의 `summary` 필드만** LLM 요약으로 교체합니다. 트리는 결정론적 결과 그대로라 **재현성이 유지되고**, 프롬프트로 언어를 지정해 **한국어 요약**을 얻습니다 — PageIndex 통째 실행에서 나온 두 문제를 동시에 피합니다.

```bash
# 규모·비용 먼저 (LLM 호출 없음)
python3 tools/enrich_summaries.py --dry-run

# 문서 하나만, 상위 2단계, 5건 시험
python3 tools/enrich_summaries.py --doc nhn --max-depth 2 --limit 5

# 실제 적용 (--max-depth 0 = 전체 깊이)
python3 tools/enrich_summaries.py --doc inference --max-depth 0
```

| 특징 | 내용 |
|---|---|
| **캐시** | 노드 원문 해시 기준. 중단 후 재실행하면 만든 것은 건너뜀 (`index/.summary_cache.json`, 커밋 제외) |
| **부분 실행** | `--doc` / `--max-depth` / `--limit` 으로 비용 조절 |
| **원본 보존** | `summary` 외 필드는 손대지 않음 |
| **표시** | 갱신된 문서는 `meta.summary_method`가 `llm-claude-code-korean` 으로 바뀜 |

문서별 대상 노드 수 (`--max-depth 0` 기준): Inference Engineering **145** · GPU on K8s **81** · NHN 백서 **54** · 마크다운 전체 171

#### 적용 결과 — Inference Engineering (145노드)

| 항목 | 값 |
|---|---|
| LLM 호출 | **142회** (캐시 적중 3, 실패 0) |
| 요약 평균 길이 | **382자** (발췌 246자 / PageIndex 통째 1,934자) |
| **트리 보존** | node_id 집합·제목 **100% 동일** — 재현성 문제 해결 ✅ |
| **한국어 비율** | 145개 중 **131개**(90%) — PageIndex 통째는 2% ✅ |

**가장 큰 이득은 한국어 검색이 생긴 것입니다.** 이 PDF는 영문이라 이전에는 한국어 질의로 아무것도 찾을 수 없었습니다.

| 한국어 질의 | 이전(발췌) | 이후(LLM) |
|---|---|---|
| 양자화 | 0 | **11** |
| 캐시 | 0 | **7** |
| 병렬 | 0 | **12** |
| 메모리 대역폭 | 0 | **9** |
| 커널 | 0 | **16** |
| 추론 | 0 | **83** |

> 한글이 포함된 요약: **0개 → 145개**. 영문 원서를 한국어로 검색할 수 있게 된 것이 이 작업의 실질 성과입니다.

실행 예:

```
$ python3 tools/search_index.py "양자화" --top 1
 1. inference-engineering-2026.pdf  p.130-130
      Table of Contents › Chapter 5: Techniques › 5.1 Quantization
      ▸ 5.1.3 Measuring Quality Impact
        양자화 후 품질 검증 방법으로 perplexity, MMLU·SWE-bench 같은 intelligence
        benchmark, 제품 특화 custom eval 세 가지를 제시하고…
```

---

## 6. 앞으로

- 주차별 정리 문서가 추가되면 `--only md`로 재생성
- 새 PDF를 받으면 `knowledge/references/pdf/`에 넣고 재생성 (내장 TOC 없으면 `tools/toc/<이름>.json` 추가)
- `index/*.json`은 생성물이지만 **커밋해 두는 것을 권장** — 재생성 없이 바로 탐색 가능하고, 문서 구조 변화가 diff로 보임
