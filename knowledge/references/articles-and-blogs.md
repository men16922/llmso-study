# 블로그 · 아티클 · 온라인 자료

노션의 **"추천 정보"** 토글 전체입니다. 스터디 커리큘럼 바깥이지만 과제("주제 기술 1개를 별도 조사")와 실무 이해에 바로 쓸 수 있는 자료가 모여 있습니다.

---

## 1. 학습 커리큘럼 · 코스

| 자료 | 설명 | 링크 |
|---|---|---|
| **AI Engineering from Scratch** | 직접 빌드하면서 이해하는 AI 엔지니어링 풀코스. 역전파를 NumPy로 짜고 나서 PyTorch를 쓰고, 토크나이저를 밑바닥부터 만든 뒤 HuggingFace를 쓰는 식의 구성 | [Site](https://aiengineeringfromscratch.com/) · [Github](https://github.com/rohitg00/ai-engineering-from-scratch) |
| **AI by Hand** | 손으로 직접 계산하며 이해하기 | [Site](https://www.byhand.ai/) · [Youtube](https://youtu.be/BAgxGp2WEu4) |
| [Coursera] 대규모 언어 모델을 통한 생성형 AI | Generative AI with LLMs | [Link](https://www.coursera.org/learn/generative-ai-with-llms) |
| [KodeKloud] vLLM을 직접 체험하며 이해하기 | | [Youtube](https://youtu.be/qdPkA5mxLhg) |
| [Free] YouTube Labs: Getting Started with LLM Inference Using vLLM | 무료 랩 | [Link](https://learn.kodekloud.com/user/courses/youtube-labs-vllm) |
| **GPU 용어집** (Modal) | GPU 용어 레퍼런스 | [Link](https://modal.com/gpu-glossary/readme) |
| Google Colab T4(GPU) 무료 | | [Link](https://colab.research.google.com/) |

## 2. AWS 고성능 네트워크 · 인터커넥트 (한국어)

노션 서브페이지 [`subpages/aws-interconnect.md`](../subpages/aws-interconnect.md)에 정리된 시리즈의 원문입니다.

### AWS 고성능 컴퓨팅 네트워크 (2부작)

| 편 | 제목 | 링크 |
|---|---|---|
| 1부 | AWS가 제공하는 고속 네트워크 인터페이스, **EFA**(Elastic Fabric Adapter) | [Blog](https://aws.amazon.com/ko/blogs/tech/aws-efaelastic-fabric-adaptor/) |
| 2부 | AWS가 제공하는 고성능 네트워크 프로토콜, **SRD**(Scalable Reliable Datagram) | [Blog](https://aws.amazon.com/ko/blogs/tech/srd/) |

### 분산 트레이닝 관점에서의 AWS 인터커넥트 기술 (4부작)

| 편 | 제목 | 링크 |
|---|---|---|
| 1편 | AWS는 왜 인터커넥트 기술로 EFA를 사용하는가? | [Blog](https://aws.amazon.com/ko/blogs/tech/aws-efa-distributed-training-interconnect-technology/) |
| 2편 | AWS의 인터커넥트 기반 기술, **ENI** 소개 | [Blog](https://aws.amazon.com/ko/blogs/tech/aws-eni/) |
| 3편 | AWS 환경에서 **NCCL**을 이용한 GPU 간 통신 | [Blog](https://aws.amazon.com/ko/blogs/tech/nccl/) |
| 4편 | 분산 트레이닝을 위해 알아야 할 **GPU 간 고속 통신 기술** | [Blog](https://aws.amazon.com/ko/blogs/tech/gpu-communications/) |

## 3. 국내 기업 사례 (한국어) ★ 과제 소재로 추천

| 자료 | 링크 |
|---|---|
| [toss] 고성능 GPU 클러스터 도입기 #1 | [Blog](https://toss.tech/article/securities_llm_1) |
| [toss] 고성능 GPU 클러스터 도입기 #2 | [Blog](https://toss.tech/article/securities_llm_2) |
| [toss] GPU를 밀도 있게 쓰는 방법 — 토스증권의 **GPU 가상화(MIG)** 도입기 | [Blog](https://toss.tech/article/toss-securities-gpu-mig) |
| **Netflix의 사내 LLM 서빙 플랫폼** | [Netflix Tech Blog](https://netflixtechblog.com/in-house-llm-serving-at-netflix-a5a8e799ea2c) · [GeekNews](https://news.hada.io/topic?id=31856) |

## 4. LLM 추론 내부 구조 심층 분석 (영어)

### aleksagordic — "Anatomy of" 시리즈 ★★

깊이 있는 내부 구조 해부 글. 교재 CH8(vLLM 내부)과 직접 대응합니다.

| 글 | 링크 |
|---|---|
| **Inside vLLM: Anatomy of a High-Throughput LLM Inference System** | [Blog](https://www.aleksagordic.com/blog/vllm) |
| Inside TPU and GPU Clusters: The Anatomy of Collective Communication | [Blog](https://www.aleksagordic.com/blog/collective-operations) |
| Inside NVIDIA GPUs: Anatomy of high performance matmul kernels | [Blog](https://www.aleksagordic.com/blog/matmul) |
| (블로그 홈) | [Blog](https://www.aleksagordic.com/blog) |

### fergusfinn — CUDA / 네트워크 내부

| 글 | 링크 |
|---|---|
| CUDA 커널을 실행하면 어떤 일이 발생할까요? | [Blog](https://fergusfinn.com/blog/what-happens-when-you-run-a-gpu-kernel/) |
| **인피니밴드, RoCE, 그리고 그 외 모든 것들** | [Blog](https://fergusfinn.com/blog/infiniband-roce-rdma/) |
| 클라우드버스트: **SGLang의 콜드 스타트 속도가 70배** 빨라졌습니다 | [Blog](https://fergusfinn.com/blog/fast-sglang-starts/) |
| NVIDIA의 CUDA 체크포인트를 역설계하여 콜드 스타트 속도 향상 | [Blog](https://fergusfinn.com/blog/what-happens-when-you-checkpoint-a-cuda-process/) |
| (블로그 홈) | [Blog](https://fergusfinn.com/) |

### jimmysong — K8s 엔지니어를 위한 GPU/AI 인프라

| 글 | 링크 |
|---|---|
| **GPU가 AI의 기반이 된 이유: Kubernetes 베테랑을 위한 GPU 입문 가이드** | [Blog](https://jimmysong.io/blog/why-gpu-foundation-of-ai/) |
| GPU 활용률에 문제가 발생하고 있다: AI 인프라에 새로운 효율성 정의가 필요 | [Blog](https://jimmysong.io/blog/beyond-gpu-utilization-productive-gpu-hours/) |
| **GPU에서 토큰까지: AI 인프라를 위한 8계층 관측 가능성 스택** | [Blog](https://jimmysong.io/blog/gpu-to-token-observability/) |
| 나만의 AI 스택: 월 약 100달러로 개인 AI 인프라 구축하기 | [Blog](https://jimmysong.io/blog/personal-ai-stack/) |
| (블로그 홈) | [Blog](https://jimmysong.io/blog/) |

### winterrykim — 밑바닥부터 언어 모델 학습

| 글 | 링크 |
|---|---|
| 언어 모델을 처음부터 학습시키기 (1부: 구성 요소) | [Blog](https://winterrykim.github.io/blog/2026/training-lm-from-scratch-part1-building-blocks/) |
| 언어 모델을 처음부터 학습시키기 (2부: **FlashAttention 및 장치 메모리**) | [Blog](https://winterrykim.github.io/blog/2026/training-lm-from-scratch-part2-flashattention-memory/) |
| 메모리에서 포토닉스까지: AI 확장의 차세대 병목 현상 해결 | [Blog](https://winterrykim.github.io/blog/2026/from-memory-to-photonics-ai-scaling/) |

### 기타

| 자료 | 링크 |
|---|---|
| CUDA 커널을 실행하면 내부에서 벌어지는 일 | [GeekNews](https://news.hada.io/topic?id=30953) |
| **[HAMi] Are You Making Good Use of Your Compute? Three Stages of vLLM Inference Cluster Optimization** | [Blog](https://project-hami.io/blog/vllm-meetup-shanghai-2026-recap) |
| **inferencex** (SemiAnalysis) — 벤더 중립·재현 가능한 AI 가속기 추론 벤치마크 | [Site](https://inferencex.semianalysis.com/inference) · [About](https://inferencex.semianalysis.com/about) |
| doubleword | [Blog](https://blog.doubleword.ai/) |

## 5. 서빙 프레임워크 · 플랫폼 실습 (한국어)

| 자료 | 링크 |
|---|---|
| **vLLM + LMCache: A Starter Guide, No GPU Required** | [Docs](https://blog.lmcache.ai/en/2026/06/23/vllm-lmcache-a-starter-guide-no-gpu-required/) |
| 분산 학습 K8S 에 Cilium — SR-IOV + Multus | [Blog](https://velog.io/@_gyullbb/Cilium-SR-IOV-Multus) |

### KServe / MLflow 시리즈

| 글 | 링크 |
|---|---|
| ML 모델을 쉽게 배포할 수 있는 KServe 알아보기 | [Blog](https://guide-to-devops.github.io/blog/introducing-kserve) |
| 로컬 Kind 클러스터에 KServe 배포하기 | [Blog](https://guide-to-devops.github.io/blog/deploying-kserve-in-local-k8s-cluster) |
| KServe의 InferenceService 직접 배포하고 테스트해보기 | [Blog](https://guide-to-devops.github.io/blog/deploying-inferenceservice-of-kserve-in-local-k8s-cluster) |
| 오픈소스 MLOps 플랫폼 MLflow를 minikube 클러스터에 배포하기 | [Blog](https://guide-to-devops.github.io/blog/deploying-mlflow-on-minikube) |

### chooblog ★ 서빙 최적화 한국어 해설

| 글 | 링크 |
|---|---|
| Knative Serving/Eventing: 쿠버네티스 기반 서버리스 (feat. 실습) | [Blog](https://www.chooblog.xyz/blog/knative-serving) |
| **LLM 서빙 프레임워크 SGLang 설치 및 실습 (WSL2)** | [Blog](https://www.chooblog.xyz/blog/use-sglang) |
| **KV Cache에 대해 알아보자 (Feat. Attention)** | [Blog](https://www.chooblog.xyz/blog/kvcache) |
| **GPU에서 Attention은 실제로 어떻게 실행되는가** — 커널 Launch부터 Tensor Core까지 (FlashAttention-2) | [Blog](https://www.chooblog.xyz/blog/kernel-tensor_core) |

## 6. 인터랙티브 도구 · 논문

| 자료 | 링크 |
|---|---|
| **Transformer Explainer** (GPT-2 인터랙티브) | [Site](https://poloclub.github.io/transformer-explainer/) · [한국어 해설](https://junhan-ai.tistory.com/590) · [arXiv](https://arxiv.org/abs/1706.03762) |

---

## 주제별 빠른 찾기

| 알고 싶은 것 | 먼저 볼 자료 |
|---|---|
| vLLM은 내부에서 어떻게 도는가 | [Inside vLLM](https://www.aleksagordic.com/blog/vllm) → 교재 CH8 |
| KV cache / Attention 커널 | [chooblog KV Cache](https://www.chooblog.xyz/blog/kvcache) → [chooblog 커널/Tensor Core](https://www.chooblog.xyz/blog/kernel-tensor_core) |
| GPU 인터커넥트 (IB/RoCE/EFA) | [fergusfinn IB·RoCE](https://fergusfinn.com/blog/infiniband-roce-rdma/) → AWS 4부작 |
| K8s에서 GPU 다루기 | [jimmysong GPU 입문](https://jimmysong.io/blog/why-gpu-foundation-of-ai/) → [GPU on K8s PDF](./pdfs.md) |
| GPU 모니터링·활용률 | [jimmysong 8계층 관측](https://jimmysong.io/blog/gpu-to-token-observability/) |
| 국내 실제 도입 사례 | [toss 3부작](https://toss.tech/article/securities_llm_1) · [Netflix](https://netflixtechblog.com/in-house-llm-serving-at-netflix-a5a8e799ea2c) |
| GPU 가상화 (MIG/HAMi) | [toss MIG](https://toss.tech/article/toss-securities-gpu-mig) · [HAMi 서브페이지](../subpages/hami-gpu-virtualization.md) |
