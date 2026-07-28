# 자료 우선순위 가이드 — 중요 / 선택 분류

노션에 모인 자료는 **180여 개**입니다. 전부 보는 건 불가능하고 필요하지도 않습니다. 이 문서는 **스터디 목적(LLM 서빙과 최적화)** 기준으로 등급을 나눈 것입니다.

## 등급 기준

| 등급 | 의미 | 총량 |
|---|---|---|
| 🔴 **필수** | 이걸 안 보면 스터디 진행이 막힘. 교재 진도와 직접 겹침 | 12개 · 약 6시간 |
| 🟡 **권장** | 해당 주차를 깊게 이해하려면 필요. 과제 소재로도 좋음 | 20여 개 |
| ⚪ **선택** | 관심 있을 때. 배경지식·인접 주제·다른 관점 | 나머지 전부 |

> 판단 기준: **교재 CH1~10 및 6·7주차 실습과의 직접성**. 좋은 자료지만 학습(training)·이미지 생성·에이전트 등 서빙 밖 주제는 등급을 낮췄습니다.

---

# 🔴 필수 (12개)

## 스터디 시작 전 — 총 55분

노션에서 👍🏻로 표시된 것 중에서도 **서빙에 직결되는 것**만 추렸습니다.

| # | 자료 | 길이 | 왜 필수인가 |
|---|---|---|---|
| 1 | [LLM prefill 설명](https://youtu.be/Vuu27UTFUZ8) | 5분 | prefill/decode 구분은 **교재 CH2부터 끝까지 전제**로 쓰임 |
| 2 | [KV cache](https://youtu.be/sq3XGM1qdQY) | 8분 | KV cache를 모르면 CH5(사이징), CH6(prefix caching), CH7(long-context) 전부 막힘 |
| 3 | [Flash attention의 원리](https://youtu.be/4Tw_ytMYHLI) | 7분 | HBM/SRAM 개념 포함. CH6 커널 퓨전의 대표 사례 |
| 4 | [왜 컴퓨터는 한 가지 메모리만 쓰지 않을까](https://youtu.be/TfhL5kBiQVI) | 27분 | 메모리 계층이 **모든 추론 최적화의 바닥**. 이거 하나로 뒤가 편해짐 |
| 5 | [LLM 설명 (요약버전)](https://youtu.be/HnvitMTkXro) | 8분 | 트랜스포머가 처음이라면. 이미 안다면 건너뛰어도 됨 |

> 1→2→3 순서로 **20분**만 투자해도 1주차 CH2가 훨씬 수월합니다. 4번은 시간 될 때.

## 교재 병행 — 주차별

| # | 자료 | 언제 | 왜 필수인가 |
|---|---|---|---|
| 6 | **[교재] Hands-On LLM Serving and Optimization** | 1~5주차 | 스터디의 뼈대. → [books.md](./books.md) |
| 7 | [Inference Engineering PDF](./pdf/inference-engineering-2026.pdf) **CH2.4** (p.63) | 1~3주차 | **ops:byte ratio / arithmetic intensity** — "내 워크로드가 memory-bound인가"를 계산하는 법. 교재 CH5를 읽기 전 필수 |
| 8 | [Inference Engineering PDF](./pdf/inference-engineering-2026.pdf) **CH5** (p.119) | 3~4주차 | 양자화·speculative·캐싱·병렬·disaggregation이 한 챕터에. 교재 CH6~7과 정확히 대응 |
| 9 | [Inside vLLM](https://www.aleksagordic.com/blog/vllm) | 4주차 | 교재 CH8(vLLM 내부)의 **가장 좋은 보조 자료**. → [deep-dives.md](./deep-dives.md#inside-vllm) |
| 10 | [GPU-Enabled Platforms on K8s PDF](./pdf/gpu-enabled-platforms-on-kubernetes-v2-2026.pdf) **CH1** (p.7) | 6주차 전 | GPU 파드가 실제로 뜨는 과정. EKS 실습 중 뭐가 일어나는지 알게 됨 |
| 11 | [AWS Workshop: GenAI on EKS](https://catalog.workshops.aws/genai-on-eks/en-US) | 6주차 | 실습 본체. **Quota 증설은 미리** |
| 12 | [llm-d Docs](https://llm-d.ai/docs) — Getting Started + Concepts | 7주차 | 실습 본체 |

---

# 🟡 권장 (주차별)

## 1주차 — CH1,2 모델 서빙 / LLM 서빙 소개

| 자료 | 성격 | 비고 |
|---|---|---|
| [Transformer Explainer](https://poloclub.github.io/transformer-explainer/) | 인터랙티브 | 5분만 만져도 어텐션이 잡힘. [한국어 해설](https://junhan-ai.tistory.com/590) |
| [chooblog: KV Cache에 대해 알아보자](https://www.chooblog.xyz/blog/kvcache) | 한국어 블로그 | 수식·메모리 계산까지. → [deep-dives](./deep-dives.md#kv-cache-chooblog) |
| [Attention/Transformer 시각화](https://youtu.be/6s69XY025MU) | 영상 30분 | 임커밋 [0]편 |
| Inference Engineering **CH0~2** | PDF | 추론 전반 개괄 |

## 2주차 — CH3,4 시스템 설계 / 모범 사례

| 자료 | 성격 | 비고 |
|---|---|---|
| [Netflix 사내 LLM 서빙 플랫폼](https://netflixtechblog.com/in-house-llm-serving-at-netflix-a5a8e799ea2c) | 사례 | 대규모 조직의 실제 아키텍처 |
| [테크톡톡: LLM 서빙, 띄우는 것과 잘 띄우는 것 사이](https://youtu.be/Z6JfgjIauSw) | 영상 (한국어) | 제목 그대로 CH4의 주제 |
| Inference Engineering **CH7 Production** | PDF | 컨테이너화·오토스케일링·배포 |

## 3주차 — CH5,6 핵심 과제 / 필수 최적화

| 자료 | 성격 | 비고 |
|---|---|---|
| **[AI Factory Ops Lab Lesson 4](../subpages/ai-factory-ops-lab.md)** | 실습 | **TTFT/goodput 붕괴점을 직접 측정.** Docker만 있으면 됨 — 강력 추천 |
| [GPU Interconnect Bandwidth](../subpages/gpu-interconnect-bandwidth.md) | 정리 | **메모리 장벽 4.7배** — CH5의 배경 |
| [chooblog: GPU에서 Attention은 실제로 어떻게 실행되는가](https://www.chooblog.xyz/blog/kernel-tensor_core) | 한국어 블로그 | 커널 launch → Tensor Core → FlashAttention-2. → [deep-dives](./deep-dives.md#attention-kernel-chooblog) |
| [Why LLMs Waste 99% of Compute — KV Cache](https://youtu.be/HmWQhBjbtLE) | 영상 | |

## 4주차 — CH7,8 고급 최적화 / 프레임워크

| 자료 | 성격 | 비고 |
|---|---|---|
| [Speculative decoding 설명](https://youtu.be/v5al_cwvkJQ) | 영상 | 임커밋 [5]편 |
| [GQA vs MQA in 10 minutes](https://youtu.be/yzONjmXM8As) | 영상 | KV cache 75% 절감 원리 |
| [LLM 추론의 엔지니어링: 양자화](https://youtu.be/1JWnEze9V5g) | 영상 | |
| [chooblog: SGLang 설치 및 실습](https://www.chooblog.xyz/blog/use-sglang) | 실습 | vLLM 외 프레임워크 비교용 |
| [시각화로 이해하는 터보퀀트](https://youtu.be/ye0oQfvWhoc) | 영상 | 양자화 시각 해설 |

## 5주차 — CH9,10 실제 적용 / 새 방향

| 자료 | 성격 | 비고 |
|---|---|---|
| [inferencex (SemiAnalysis)](https://inferencex.semianalysis.com/inference) | 벤치마크 | 벤더 중립 추론 벤치마크 — CH9 성능 측정 |
| [vLLM + LMCache Starter Guide](https://blog.lmcache.ai/en/2026/06/23/vllm-lmcache-a-starter-guide-no-gpu-required/) | 실습 | **No GPU Required** — 캐싱 계층 실습 |
| Inference Engineering **CH6 Modalities** | PDF | 멀티모달 서빙 |

## 6주차 — AWS EKS

| 자료 | 성격 | 비고 |
|---|---|---|
| **[[Old] GenAI on EKS 실습 정리](../subpages/genai-on-eks-workshop-notes.md)** | 예습 | 이전 회차 전체 흐름 |
| [PC에 GPU 설정 by Docker/K8S](../subpages/gpu-setup-docker-k8s.md) | 실습 | Device Plugin 내부 동작 |
| GPU-Enabled Platforms on K8s **CH5 Monitoring** | PDF | 할당 vs 실사용 격차, 좀비 프로세스 |
| [jimmysong: GPU에서 토큰까지 8계층 관측](https://jimmysong.io/blog/gpu-to-token-observability/) | 블로그 | → [deep-dives](./deep-dives.md#8-layer-observability) |

## 7주차 — llm-d

| 자료 | 성격 | 비고 |
|---|---|---|
| Inference Engineering **CH5.5 Disaggregation** (p.150) | PDF | llm-d 설계 의도의 근거 |
| [NCCL: GPU Cluster Communication](../subpages/nccl-communication.md) | 정리 | 분산 집합통신 |
| [Inside TPU and GPU Clusters: Collective Communication](https://www.aleksagordic.com/blog/collective-operations) | 블로그 | 위 주제 영어 심화 |

## 과제용 (주차 무관) ★

과제는 "학습 내용 요약" 또는 "주제 1개 별도 조사" 또는 **"운영 경험/신기술 분석"** 입니다. 마지막 유형에는 국내 사례가 최고의 소재입니다.

| 자료 | 왜 |
|---|---|
| [toss 고성능 GPU 클러스터 도입기 #1](https://toss.tech/article/securities_llm_1) · [#2](https://toss.tech/article/securities_llm_2) | 온프레미스 선택 이유, 하드웨어 균일성 문제 → [deep-dives](./deep-dives.md#toss-gpu-cluster) |
| [toss GPU 가상화(MIG) 도입기](https://toss.tech/article/toss-securities-gpu-mig) | HW 격리 실제 도입 사례 |
| [대규모 AI 서비스 K8s GPU 클러스터 도입기](https://youtu.be/cUn5KjNGiuI) | 영상 |
| [MLXP: K8s LLM Serving 최적화 도입기](https://youtu.be/sgEEs5yvYGs) | 영상 |
| [Lablup: LLM 서빙토크 — 싸고 빠르게 돌리는 꿀팁](https://youtu.be/O00dArdImoI) | 영상 |
| [HAMi 가상화 실습](../subpages/hami-gpu-virtualization.md) | **"compute 격리는 실패했다"는 실측 결과**가 있어 분석 글 소재로 좋음 |

---

# ⚪ 선택

아래는 **좋은 자료지만 서빙 커리큘럼과 거리가 있거나, 위 자료와 내용이 겹치는** 것들입니다. 관심 생길 때 보세요.

| 분류 | 내용 | 왜 선택인가 |
|---|---|---|
| **학습(training) 주제** | [2조 개 매개변수 LLM 훈련](https://youtu.be/yn4GGAtZ7QE) · [winterrykim 언어모델 처음부터 학습 1·2부](https://winterrykim.github.io/blog/2026/training-lm-from-scratch-part1-building-blocks/) · [밑바닥부터 만들면서 배우는 LLM](https://product.kyobobook.co.kr/detail/S000217570241) | 스터디는 **서빙(추론)**이 주제. 학습은 배경지식 |
| **딥러닝 기초** | 3Blue1Brown DL1·DL3·DL4 (뉴럴넷, 백프로파게이션) | 이미 아는 내용이면 불필요 |
| **하드웨어 일반** | [CPU는 어떻게 작동할까](https://youtu.be/Fg00LN30Ezg) · [양자컴퓨터](https://youtu.be/8GummfGLBc0) · [GPU 용어집](https://modal.com/gpu-glossary/readme) | 용어집은 **모르는 용어 나올 때 찾아보는 용도**로만 |
| **인접 모달리티** | 이미지 생성·확산 모델·비디오 생성·TTS/ASR 영상 | CH10에서 잠깐 다룸 |
| **에이전트/기타** | [클로드 코드의 내부](https://youtu.be/ofLvTNZEHVk) · [하네스 엔지니어링](https://youtu.be/Xxuxg8PcBvc) · [기계적 해석 가능성](https://youtu.be/tDzqCDEYc0A) | 재미있지만 서빙과 별개 |
| **네트워크 심화** | [AWS EFA/SRD 6부작](./articles-and-blogs.md#2-aws-고성능-네트워크--인터커넥트-한국어) · [fergusfinn IB/RoCE](https://fergusfinn.com/blog/infiniband-roce-rdma/) · [NHN 백서](./pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf) | **다중 노드 학습**에서 중요. 단일 노드 서빙 위주면 후순위 → [deep-dives](./deep-dives.md#infiniband-vs-roce) |
| **MLOps 플랫폼** | KServe 4부작 · MLflow · Knative · [Ray MLOps](https://tv.naver.com/v/80335756) | 교재가 vLLM/Triton 중심. 대안 스택에 관심 있을 때 |
| **커리큘럼/코스** | [AI Engineering from Scratch](https://aiengineeringfromscratch.com/) · [AI by Hand](https://www.byhand.ai/) · [Coursera GenAI with LLMs](https://www.coursera.org/learn/generative-ai-with-llms) | 별도 완주 코스. 7주와 병행은 부담 |
| **참고 도서** | [AI Systems Performance Engineering](https://www.amazon.com/Systems-Performance-Engineering-Optimizing-Inference/dp/B0F47689K8) · [CUDA for Deep Learning](https://www.manning.com/books/cuda-for-deep-learning) | 스터디 후 심화용. CUDA 책은 26.10 출간 예정 |
| **CUDA 저수준** | [fergusfinn CUDA 커널 실행](https://fergusfinn.com/blog/what-happens-when-you-run-a-gpu-kernel/) · [SGLang 콜드스타트 70배](https://fergusfinn.com/blog/fast-sglang-starts/) | CH6 커널 퓨전을 더 파고들 때 |
| **채널 전체** | Visual AI 트랜스포머 10편 · Branch Education 등 | 특정 개념이 안 잡힐 때 해당 편만 |

---

## 한 장 요약

```
지금 당장          prefill(5분) → KV cache(8분) → Flash attention(7분)     = 20분
1주차까지          + 메모리 계층(27분) + Transformer Explainer(5분)         = 52분
매주               교재 해당 CH + Inference Engineering 대응 챕터
3주차 실습         AI Factory Ops Lab Lesson 4 (TTFT/goodput 직접 측정)
6주차 전           Quota 증설 신청 + [Old] EKS 정리 읽기
과제 막힐 때       toss / Netflix / 국내 도입기 영상에서 소재 찾기
```

## 관련 문서

- 자료별 상세 분석 → [deep-dives.md](./deep-dives.md)
- 전체 링크 목록 → [README.md](./README.md) · [videos.md](./videos.md) · [articles-and-blogs.md](./articles-and-blogs.md)
- PDF 목차 → [pdfs.md](./pdfs.md) · 검색 → `python3 tools/search_index.py "키워드"`
