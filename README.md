# Hands-On LLM Serving and Optimization Study (LLMSO)

CloudNet@ **LLMSO 스터디**(2026-08-02 ~ 09-13, 7주) 자료 정리 저장소입니다.

> ## ⚠️ 이 저장소는 비공개로 유지하세요
>
> - 원본 노션은 **멤버 전용**이며 스터디 규칙상 **외부 공개·전파 금지**입니다. → [스터디 규칙](./knowledge/03-study-rules.md)
> - `knowledge/references/pdf/`에 **제3자 배포 PDF 3종(527p)** 이 포함되어 있습니다. 각 배포처의 무료 자료지만 재배포는 별개 문제입니다.
> - `index/*.json`에는 그 PDF들의 **짧은 발췌문**이 노드별로 들어 있습니다.
>
> **공개 저장소로 올릴 계획이라면** 먼저 `knowledge/references/pdf/`를 `.gitignore`에 추가하고 `index/`의 PDF 인덱스를 제외하세요. 가공하여 활용(블로그 포스팅 등)하는 것은 스터디에서 오히려 권장합니다.

## 구조

```
.
├── knowledge/           스터디 자료 정리 (문서 24개)
│   ├── 00-study-overview.md      커리큘럼 · 교재 CH1~10 매핑
│   ├── 01-environment-setup.md   GPU 실습 환경
│   ├── 02-assignments.md         과제 규정 · 마감표
│   ├── 03-study-rules.md         저작권 · 슬랙/ZOOM · 질문법
│   ├── 04-kickoff-checklist.md   시작 전 실행 체크리스트
│   ├── 05-week1-prep.md          1주차 CH1~2 예습 노트
│   ├── subpages/                 노션 서브페이지 8종 정리 (실습 가이드)
│   └── references/               외부 자료 인덱스
│       ├── priority-guide.md     ★ 중요/선택 등급 분류
│       ├── deep-dives.md         ★ 핵심 자료 14종 심층 분석
│       └── pdf/                  다운로드된 PDF 3종 (41.6 MB · 527p)
│
├── index/               PageIndex 호환 트리 인덱스 (612 노드)
└── tools/               인덱스 생성 · 탐색 스크립트
```

## 빠른 시작

| 하고 싶은 것 | 명령 / 문서 |
|---|---|
| **시작 전 준비** | [`knowledge/04-kickoff-checklist.md`](./knowledge/04-kickoff-checklist.md) |
| **1주차 예습** | [`knowledge/05-week1-prep.md`](./knowledge/05-week1-prep.md) |
| 스터디 전반 파악 | [`knowledge/README.md`](./knowledge/README.md) |
| **뭘 먼저 봐야 하나** | [`knowledge/references/priority-guide.md`](./knowledge/references/priority-guide.md) |
| 자료 내용이 궁금 | [`knowledge/references/deep-dives.md`](./knowledge/references/deep-dives.md) |
| **PDF에서 개념 찾기** | `python3 tools/search_index.py "KV cache"` |
| 문서 목차 보기 | `python3 tools/search_index.py --outline inference-engineering` |
| 인덱스 재생성 | `python3 tools/build_pageindex.py` |

### 검색 예시

```
$ python3 tools/search_index.py "KV cache" --top 2
'KV cache' → 13개 노드 매칭 (상위 2개)

 1. [ 176.0] inference-engineering-2026.pdf  p.141-141
      Table of Contents › Chapter 5: Techniques › 5.3 Caching
      ▸ 5.3.2 Where to Store the KV Cache
        The KV cache is very valuable. But KV caches take up a lot of memory, and GPUs…
```

## 스터디 개요

- **일정**: 2026-08-02 ~ 09-13, 매주 일요일 20:30~22:30 (ZOOM)
- **교재**: *Hands-On LLM Serving and Optimization* (Chi Wang, Peiheng Hu / O'Reilly 2026.4)
- **커리큘럼**: 1~5주차 CH1~10 → 6주차 AWS EKS 워크숍 → 7주차 llm-d
- **과제**: 매주 학습 내용을 공개 링크로 정리·공유 (다음 주 일요일 09:00까지)

## 필요 패키지

```bash
pip install pymupdf     # PDF 인덱싱용 (tools/build_pageindex.py)
```

인덱싱·탐색은 **LLM API 키가 필요 없습니다.** 배경은 [`index/README.md`](./index/README.md) 참조.
