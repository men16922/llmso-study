# knowledge — LLMSO 스터디 자료 정리

CloudNet@ **Hands-On LLM Serving and Optimization Study (LLMSO)** 멤버 페이지 전체(메인 + 서브페이지 8개 + 접힌 토글 포함)를 정리한 폴더입니다.

- 원본: [Notion — Hands-On LLM Serving and Optimization Study](https://app.notion.com/p/gasidaseo/Hands-On-LLM-Serving-and-Optimization-Study-3aa50aec5edf8027b6a6ffff4325d077) (멤버 전용)
- 정리 기준일: 2026-07-28

> ⚠️ **원문 노션은 저작권 보호 내용이 포함되어 외부 공개·전파가 금지**되어 있습니다. 이 폴더는 개인 학습용 정리이며 그대로 외부에 공개하지 마세요. 가공하여 활용(블로그 포스팅 등)하는 것은 스터디에서 권장합니다. → [03-study-rules.md](./03-study-rules.md)

## 구조

```
knowledge/
├── 00-study-overview.md      스터디 목적 · 운영 방식 · 주차별 커리큘럼(교재 목차 매핑)
├── 01-environment-setup.md   실습 환경 요구사항 · 체크리스트 · 비용 주의
├── 02-assignments.md         과제 방법 · 마감표 · 제명 규칙 · 발표 가이드
├── 03-study-rules.md         저작권 정책 · 슬랙/노션/ZOOM 준비 · 질문하는 법
│
├── subpages/                 ★ 노션 서브페이지 8종 정리
│   ├── README.md             인덱스 · 주제 지도 · 읽는 순서
│   ├── gpu-setup-docker-k8s.md         PC→Docker→K8s GPU 설정 (OCI 훅, Device Plugin 내부)
│   ├── gpu-interconnect-bandwidth.md   메모리 장벽, NVLink/NVSwitch/PCIe
│   ├── hami-gpu-virtualization.md      SW GPU 가상화 HAMi
│   ├── nccl-communication.md           Ring AllReduce 단계별 추적
│   ├── nvidia-ai-infrastructure.md     NVIDIA 인프라 6계층 지도
│   ├── ai-factory-ops-lab.md           가짜 GPU로 하는 플랫폼 운영 실습
│   ├── genai-on-eks-workshop-notes.md  6주차 예습 (EKS + vLLM + Ray)
│   └── aws-interconnect.md             AWS EFA / SRD / ENI
│
└── references/               ★ 모든 외부 자료의 단일 인덱스
    ├── README.md             전체 링크 표 + 주차별 자료 매핑
    ├── priority-guide.md     ★★ 중요/선택 등급 분류 — 여기부터 보세요
    ├── deep-dives.md         ★ 핵심 자료 8종 심층 분석
    ├── books.md              주교재 CH1~10 목차 + 참고 도서
    ├── pdfs.md               로컬 PDF 3종 목차 · 활용 가이드
    ├── videos.md             영상 80여 편 (필수 22 + 추천 60여)
    ├── articles-and-blogs.md 블로그·아티클·코스 60여 개
    ├── workshops-and-docs.md AWS 워크숍 · llm-d · 도구 · 코드 저장소
    └── pdf/                  다운로드된 PDF (41.6 MB)
        ├── inference-engineering-2026.pdf                 23.0 MB · 259p
        ├── gpu-enabled-platforms-on-kubernetes-v2-2026.pdf 15.4 MB · 202p
        └── nhn-cloud-factoryx-gpu-whitepaper-2026.pdf      3.2 MB ·  66p
```

## 핵심 요약

- **기간**: 2026년 8월 2일 ~ 9월 13일 (총 7주)
- **시간**: 매주 일요일 20:30 ~ 22:30 (+α) / ZOOM, 결석 시 녹화 시청
- **모임장**: 서종호(gasida) — Cisco CCIEx3, [LinkedIn](https://www.linkedin.com/in/gasida99/)
- **주교재**: *Hands-On LLM Serving and Optimization* (Chi Wang, Peiheng Hu / O'Reilly 2026.4, 374p) — 구매 필수 아님
- **소통**: 슬랙 `CloudNetaStudy` 워크스페이스의 비공개 채널 `llmso`
- **필수 준비물**: AWS/GCP/Azure GPU 인스턴스 사용 준비 (6주차는 AWS EKS, `g6e.2xlarge`)
- **과제**: 매주 학습 내용을 공개 링크로 정리·공유, 다음 주 일요일 09:00까지. **1회 미공유 시 제명** (단, 경험 발표 시 전 과제 면제)

## 어디부터 볼까

| 상황 | 문서 |
|---|---|
| 스터디가 뭘 하는지 알고 싶다 | [00-study-overview.md](./00-study-overview.md) |
| 시작 전 준비물 (슬랙/노션/ZOOM/GPU) | [03-study-rules.md](./03-study-rules.md) → [01-environment-setup.md](./01-environment-setup.md) |
| **자료가 너무 많다, 뭘 봐야 하나** | **[references/priority-guide.md](./references/priority-guide.md)** — 필수 12개만 추림 |
| 그 자료가 무슨 내용인지 먼저 알고 싶다 | [references/deep-dives.md](./references/deep-dives.md) |
| 이번 주 뭘 읽어야 하나 | [references/priority-guide.md](./references/priority-guide.md) 주차별 권장 |
| GPU/K8s 실습을 따라해보고 싶다 | [subpages/README.md](./subpages/README.md) |
| 과제 소재를 찾고 있다 | [references/priority-guide.md](./references/priority-guide.md) "과제용" 섹션 |
| **PDF에서 개념 위치 찾기** | `python3 tools/search_index.py "KV cache"` → [index/](../index/) |
| 자료 원문을 보고 싶다 | [references/pdf/](./references/pdf/) |

> <Copyright. CloudNet@ All right reserved.>
