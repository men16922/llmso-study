# 레퍼런스 라이브러리

LLMSO 스터디 관련 **모든 외부 자료의 단일 인덱스**입니다. 노션 페이지에 "Site", "Youtube", "Link" 같은 짧은 텍스트로만 걸려 있던 링크를 전부 실제 URL로 복원했고, 배포 가능한 PDF는 [`pdf/`](./pdf/)에 내려받아 두었습니다.

## 문서

| 파일 | 내용 |
|---|---|
| ★ [priority-guide.md](./priority-guide.md) | **중요 / 선택 등급 분류** — 180여 개 중 뭘 먼저 볼지 |
| ★ [deep-dives.md](./deep-dives.md) | 핵심 자료 **14종**을 실제로 읽고 정리한 심층 분석 |
| [books.md](./books.md) | 주교재 + 참고 도서 (챕터 목차 포함) |
| [pdfs.md](./pdfs.md) | 로컬에 받아둔 PDF 3종 — 목차 · 활용 가이드 |
| [videos.md](./videos.md) | 영상 80여 편 — 사전 시청 권장 22편 + 추천 Youtube 전체 |
| [articles-and-blogs.md](./articles-and-blogs.md) | 블로그·아티클·온라인 코스 60여 개 (노션 "추천 정보" 전체) |
| [workshops-and-docs.md](./workshops-and-docs.md) | AWS 워크숍, llm-d, 인터랙티브 도구, 코드 저장소 |

- 서브페이지(실습 가이드) 정리는 [`../subpages/`](../subpages/)
- 자료 본문 검색은 `python3 tools/search_index.py "키워드"` → [`../../index/`](../../index/)

> **처음이라면 [priority-guide.md](./priority-guide.md)부터 보세요.** 이 폴더의 나머지는 전수 목록이라 그대로 읽으면 길을 잃습니다.

## 로컬 자산

| 파일 | 크기 | 페이지 | 출처 |
|---|---|---|---|
| [`pdf/inference-engineering-2026.pdf`](./pdf/inference-engineering-2026.pdf) | 23.0 MB | 259p | Baseten (Philip Kiely) |
| [`pdf/gpu-enabled-platforms-on-kubernetes-v2-2026.pdf`](./pdf/gpu-enabled-platforms-on-kubernetes-v2-2026.pdf) | 15.4 MB | 202p | LearnKube × vCluster |
| [`pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf`](./pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf) | 3.2 MB | 66p | NHN Cloud |

> 출처는 노션 페이지 첨부파일. 각 자료의 원 배포처 정책에 따라 **개인 학습용**으로만 사용하세요.

---

## 전체 링크 표

### 스터디 핵심

| 자료 | 종류 | 링크 |
|---|---|---|
| Hands-On LLM Serving and Optimization | 주교재 (O'Reilly, 2026.4, 374p) | [Site](https://orca3.github.io/llm-model-inference/) · [Code](https://github.com/orca3/llm-model-inference) |
| Generative AI on Amazon EKS | AWS 워크숍 (6주차) | [Workshop](https://catalog.workshops.aws/genai-on-eks/en-US) · [Github](https://github.com/aws-samples/sample-genai-on-eks) |
| llm-d | 공식 문서 (7주차) | [Docs](https://llm-d.ai/docs) |
| g6e.2xlarge | 워크숍 권장 인스턴스 | [사양/요금](https://instances.vantage.sh/aws/ec2/g6e.2xlarge) |

### PDF 원 배포처

| 자료 | 링크 |
|---|---|
| Inference Engineering | [Baseten 다운로드](https://www.baseten.co/inference-engineering/digital-download/) · [100 Days of Inference](https://github.com/elizabetht/100-days-of-inference) |
| GPU-Enabled Platforms on Kubernetes | [vCluster](https://www.vcluster.com/gpu-enabled-platforms-on-kubernetes) · [웨비나 영상](https://youtu.be/eBbjSfxwL30) |
| NHN Cloud GPU 클러스터 기술 백서 | [NHN FactoryX](https://www.nhnfactoryx.com/resources/FFHJRc8axydGNtjn) |

### 참고 도서

| 도서 | 링크 |
|---|---|
| 밑바닥부터 만들면서 배우는 LLM | [교보문고](https://product.kyobobook.co.kr/detail/S000217570241) · [Youtube](https://youtu.be/R80Gfde4cpg) · [원서](https://www.manning.com/books/build-a-large-language-model-from-scratch) |
| AI Systems Performance Engineering | [Amazon](https://www.amazon.com/Systems-Performance-Engineering-Optimizing-Inference/dp/B0F47689K8) · [Github](https://github.com/cfregly/ai-performance-engineering) |
| CUDA for Deep Learning (MEAP) | [Manning](https://www.manning.com/books/cuda-for-deep-learning) |

### 도구 · 논문

| 자료 | 링크 |
|---|---|
| Transformer Explainer (GPT-2 인터랙티브) | [Site](https://poloclub.github.io/transformer-explainer/) · [한국어 해설](https://junhan-ai.tistory.com/590) |
| Attention Is All You Need | [arXiv:1706.03762](https://arxiv.org/abs/1706.03762) |
| Google Colab | [Site](https://developers.google.com/colab) |
| 모임장 (서종호 / gasida) | [LinkedIn](https://www.linkedin.com/in/gasida99/) |

### 영상

22편 전체 목록은 [videos.md](./videos.md) 참조. 최우선 3편만 추리면:

| 영상 | 길이 | 링크 |
|---|---|---|
| LLM prefill 설명 | 5분 | [Youtube](https://youtu.be/Vuu27UTFUZ8) |
| KV cache | 8분 | [Youtube](https://youtu.be/sq3XGM1qdQY) |
| Flash Attention의 원리 | 7분 | [Youtube](https://youtu.be/4Tw_ytMYHLI) |

---

## 주차별 자료 매핑

| 주차 | 주제 | 1순위 자료 | 보조 자료 |
|---|---|---|---|
| 1 (08-02) | CH1,2 서빙/최적화 소개 | 교재 CH1–2 | Inference Engineering CH0–2 · [videos.md](./videos.md) §2 |
| 2 (08-09) | CH3,4 시스템 설계/모범 사례 | 교재 CH3–4 | Inference Engineering CH7 (Production) |
| 3 (08-16) | CH5,6 핵심 과제/필수 최적화 | 교재 CH5–6 | Inference Engineering CH2.4, CH3, CH5.3 |
| 4 (08-23) | CH7,8 고급 최적화/프레임워크 | 교재 CH7–8 | Inference Engineering CH4, CH5 (양자화·speculative·병렬·disaggregation) |
| 5 (08-30) | CH9,10 실제 적용/새 방향 | 교재 CH9–10 | Inference Engineering CH6 (멀티모달) |
| 6 (09-06) | AWS EKS 워크숍 | [워크숍](https://catalog.workshops.aws/genai-on-eks/en-US) | GPU-Enabled Platforms on K8s (전체) · [EKS 예습 노트](../subpages/genai-on-eks-workshop-notes.md) |
| 7 (09-13) | llm-d | [llm-d Docs](https://llm-d.ai/docs) | Inference Engineering CH5.5 · NHN 백서 CH2 |

## 서브페이지 실습 가이드 (별도 폴더)

| 문서 | 언제 보나 |
|---|---|
| [gpu-setup-docker-k8s](../subpages/gpu-setup-docker-k8s.md) | GPU 환경을 직접 만들 때 (1주차 전후) |
| [gpu-interconnect-bandwidth](../subpages/gpu-interconnect-bandwidth.md) | 3주차 CH5(핵심 과제) 배경 |
| [ai-factory-ops-lab](../subpages/ai-factory-ops-lab.md) | Lesson 4가 3주차 TTFT/goodput 실측에 유용 |
| [hami-gpu-virtualization](../subpages/hami-gpu-virtualization.md) | GPU 공유·가상화 주제 |
| [nccl-communication](../subpages/nccl-communication.md) · [aws-interconnect](../subpages/aws-interconnect.md) | 분산 통신 주제 (7주차 llm-d 배경) |
| [genai-on-eks-workshop-notes](../subpages/genai-on-eks-workshop-notes.md) | **6주차 예습** |
| [nvidia-ai-infrastructure](../subpages/nvidia-ai-infrastructure.md) | 전체 스택 조망이 필요할 때 |
