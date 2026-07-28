# 로컬 PDF 자료

노션 페이지에 첨부되어 있던 무료/공개 배포 PDF 3종을 [`pdf/`](./pdf/)에 내려받아 두었습니다. 아래 목차는 각 PDF에서 직접 추출한 것입니다.

| 파일 | 크기 | 페이지 | 저자/발행 |
|---|---|---|---|
| [inference-engineering-2026.pdf](./pdf/inference-engineering-2026.pdf) | 23.0 MB | 259p | Philip Kiely / Baseten |
| [gpu-enabled-platforms-on-kubernetes-v2-2026.pdf](./pdf/gpu-enabled-platforms-on-kubernetes-v2-2026.pdf) | 15.4 MB | 202p | Daniele Polencic (LearnKube), Saiyam Pathak (vCluster) |
| [nhn-cloud-factoryx-gpu-whitepaper-2026.pdf](./pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf) | 3.2 MB | 66p | NHN Cloud |

> 개인 학습용으로만 사용하세요. 재배포는 각 배포처 정책을 따릅니다.

---

## 1. Inference Engineering (Baseten, 259p)

**한 줄 요약**: LLM 추론을 "엔지니어링 문제"로 다루는 실무 가이드. 교재의 CH5~8과 가장 많이 겹치며, 서술이 더 구체적입니다.

원 배포처: [baseten.co](https://www.baseten.co/inference-engineering/digital-download/) · 실습 부록: [100 Days of Inference](https://github.com/elizabetht/100-days-of-inference)

### 목차

```
Preface                                              p.11
Chapter 0: Inference                                 p.17
Chapter 1: Prerequisites                             p.25
  1.1 Scale and Specialization                       p.28
  1.2 About Your App (AI-native / online·offline / consumer·B2B)
  1.3 Model Selection (평가, 파인튜닝, 증류)
  1.4 Measuring Latency and Throughput (지연 백분위, E2E 지표)
Chapter 2: Models                                    p.41
  2.1 Neural Networks (linear layer, matmul, 활성함수)
  2.2 LLM Inference Mechanics (아키텍처, 트랜스포머 블록, 어텐션, MoE)
  2.3 Image Generation Inference Mechanics
  2.4 Calculating Inference Bottlenecks  ★ ops:byte ratio, arithmetic intensity
  2.5 Optimizing Attention
Chapter 3: Hardware                                  p.73
  3.1 GPU Architecture (compute, memory & caches)
  3.2 GPU 세대별 (Hopper / Ada Lovelace / Blackwell / Rubin / Grace·Vera)
  3.3 Instances (multi-GPU, MIG)
  3.4 기타 데이터센터 가속기
  3.5 Local Inference (데스크톱, 모바일)
Chapter 4: Software                                  p.95
  4.1 CUDA (커널, 커널 선택, 커널 퓨전)
  4.2 DL 프레임워크·라이브러리 (PyTorch, 모델 파일 포맷, ONNX/TensorRT)
  4.3 Inference Engines                              p.107
  4.4 NVIDIA Dynamo                                  p.113
  4.5 Performance Benchmarking and Load Testing      p.114
Chapter 5: Techniques                                p.119   ★ 최적화 핵심
  5.1 Quantization                                   p.122
  5.2 Speculative Decoding                           p.131
  5.3 Caching                                        p.138
  5.4 Model Parallelism                              p.144
  5.5 Disaggregation                                 p.150
Chapter 6: Modalities                                p.155
  VLM / Embedding / ASR / TTS / Image Gen / Video Gen
Chapter 7: Production                                p.179
  7.1 Containerization    7.2 Autoscaling    7.3 Multi-Cloud Capacity
  7.4 Testing & Deployment    7.5 Client Code    7.6 Baseten
Appendix A: Inference Glossary                       p.211   ★ 용어 사전
Appendix B: Recommended Reading                      p.233
  Architecture / Developer Tools / Frontier Open Models /
  GPU Infrastructure / Inference Optimization Research / Intelligence Evaluation
```

### 스터디 활용 포인트

- **CH2.4 (Calculating Inference Bottlenecks)** — ops:byte ratio와 arithmetic intensity로 "내 워크로드가 memory-bound인가 compute-bound인가"를 계산하는 법. 교재 CH5(핵심 과제)를 읽기 전에 보면 이해도가 크게 올라갑니다.
- **CH5 전체** — 교재 CH6~7(필수/고급 최적화)과 정확히 대응. 양자화·speculative decoding·캐싱·병렬화·disaggregation이 한 챕터에 정리되어 있습니다.
- **Appendix A 용어 사전** — 스터디 내내 옆에 두고 참고하기 좋습니다.
- **Appendix B** — 과제("주제 기술 1개를 별도 조사")의 소재를 찾기 좋은 논문/자료 목록.

---

## 2. GPU-Enabled Platforms on Kubernetes V2 (LearnKube × vCluster, 202p)

**한 줄 요약**: "GPU는 왜 쿠버네티스의 컨테이너 모델에 맞지 않는가"를 커널 수준부터 풀어낸 eBook. **6주차 AWS EKS 실습의 배경 지식**으로 가장 잘 맞습니다.

원 배포처: [vcluster.com](https://www.vcluster.com/gpu-enabled-platforms-on-kubernetes) · [웨비나 영상](https://youtu.be/eBbjSfxwL30)

### 목차

```
Chapter 1. Foundations — How GPUs Meet Kubernetes            p.7
  Syscalls: 커널의 API 표면                                   p.8
  cgroups: 리소스 제한 강제                                   p.11
  Namespaces: 프로세스가 볼 수 있는 것의 격리                  p.13
  From Kernel Primitives to Docker (CPU 선점형 멀티태스킹, 메모리 페이지 할당)
  CUDA Fundamentals: 컨텍스트 · 커널 · 메모리                 p.20
  Why GPUs Don't Support Kernel Preemption   ★               p.27
  GPU Memory: 완전히 다른 모델                                p.29
  Kubernetes와 CRI / The GPU Problem in Kubernetes           p.34
  Running a GPU Pod: End-to-End                              p.45

Chapter 2. Why GPU Multi-Tenancy Is Hard                     p.53
  전통적 K8s 격리(Namespace/cgroup/RBAC)가 작동하는 이유       p.54
  GPU에서 이 모델이 무너지는 이유                              p.62
    - GPU 스케줄링은 커널 밖에서 일어난다                       p.64
    - CUDA 컨텍스트가 컨테이너를 가로지른다                     p.65
    - K8s는 API 레이어에서만 스케줄링을 강제한다                p.67
  Threat Scenarios in Practice                               p.68
  Time-Slicing / MIG / vGPU                                  p.76~83
  The Trust Spectrum: 신뢰 수준별 전략 선택   ★               p.85

Chapter 3. Orchestrating GPU Sharing                         p.89
  GPU는 이미 공유를 지원한다 / GPU 컨텍스트 스위칭             p.90
  The Memory Illusion                                        p.93
  KAI-Scheduler의 Reservation Pod 전략                        p.98
  NVIDIA "Time-Slicing" — 오해를 부르는 이름   ★              p.104
  A Practical Example: The Scheduler Showdown                p.111

Chapter 4. Hardware Isolation and Enforcement                p.115
  병렬 vs 순차의 근본적 차이                                  p.116
  MIG: NVIDIA가 실리콘으로 해결한 방식 (왜 7 슬라이스인가)     p.118
  MIG 인스턴스 생성 / Pod에서 사용 / 비용·아키텍처 트레이드오프
  HAMi: 소프트웨어 강제 (Compute Throttling, 토큰 버킷)  ★    p.129
  The Evolution of GPU Sharing                               p.141

Chapter 5. Monitoring GPU Clusters                           p.143
  GPU 현실의 세 가지 관점 / nvidia-smi는 실제로 무엇을 재는가  p.145
  세 계층 메모리 / 좀비 프로세스 문제   ★                     p.148
  GPU Hoarding의 연쇄 효과                                    p.157
  DCGM: 현실 격차 메우기 / 할당 vs 실사용 격차                p.159
  실제로 중요한 모니터링 패턴                                 p.165

Chapter 6. Multi-Tenant GPU Platforms with vCluster          p.170
  vCluster 아키텍처 입문                                      p.174
  Demo: KAI Scheduler + vCluster 분수 GPU 공유 (Ollama RAG)   p.189
    1. Prerequisites  2. NVIDIA GPU Operator  3. KAI-Scheduler
    4. vCluster 생성  5. 애플리케이션 배포
```

### 스터디 활용 포인트

- 노션 서브페이지 **"GPU 가상화: HAMi 설치 및 사용"** 과 CH4(HAMi)가 직접 연결됩니다.
- **6주차 EKS 실습** 전에 CH1(GPU Pod가 실제로 뜨는 과정)과 CH5(모니터링)를 읽으면 실습 중 무슨 일이 벌어지는지 이해하기 쉽습니다.
- CH5의 "할당 vs 실사용 격차", "좀비 프로세스가 GPU 메모리를 잡는 이유"는 운영 트러블슈팅 사례 과제 소재로 좋습니다.

---

## 3. NHN Cloud GPU 클러스터 기술 백서 (NHN FactoryX, 66p, 한국어)

**한 줄 요약**: 엑사스케일 GPU 클러스터를 실제로 설계·운영한 사업자의 기술 백서. 네트워크·전력·냉각 등 **인프라 물리 계층**까지 다루는 국내 자료.

원 배포처: [nhnfactoryx.com](https://www.nhnfactoryx.com/resources/FFHJRc8axydGNtjn)

### 목차

```
01 개요                                                      p.8
   1.1 문서의 목적과 범위
   1.2 패러다임의 전환: 범용 클라우드 → AI 전용 인프라
       1.2.1 대규모 클러스터 성능 저하의 구조적 원인   ★
       1.2.2 AI 전용 인프라 요구 사항
02 시스템 아키텍처                                           p.14
   2.1 GPU 클러스터 구성
       계층 구조 / Compute Fabric / Fat-Tree 기반 Rail-Optimized 토폴로지  ★
   2.2 고속 인터커넥트
       노드 내부: NVLink·NVSwitch / 노드 간: InfiniBand / 설계 균형 원칙
   2.3 전력 및 냉각 설계
       공랭식의 한계 / D2C 수랭식 도입 / 수랭 요소 설계 / PUE 개선
   2.4 GPU 동적 할당 기술 (GPU Live)                          p.25
       개념과 필요성 / 동적 할당 구현 / 향후 방향
03 하드웨어 구성                                             p.38
   CPU·메모리 / GPU 사양과 성능 / Tiered Storage · 네트워크
04 성능 분석                                                 p.43
   4.1 이론적 연산 성능
   4.2 성능 저하 패턴 분석   ★
       네트워크 병목 / 메모리 부족(HBM·시스템) / 스토리지 I/O 병목
       열 스로틀링 / 체크포인트 오버헤드
   4.3 패턴별 설계 단계 대응 체크리스트   ★
05 확장성 및 운영                                            p.48
   Scalable Unit 기반 증설 / 수평·수직 확장 분리 / 자원 활용 효율
06 활용 사례                                                 p.51
   NHN FactoryX 엑사스케일 클러스터 / 기업 프라이빗 AI 인프라 구축
07 결론                                                      p.55
08 부록  GPU 모델별 사양 / 용어 정의 / 참고 문헌               p.58
```

### 스터디 활용 포인트

- 노션 서브페이지 **"[기초부터 이해하는 GPU Network] GPU Interconnect Bandwidth"**, **"NCCL: GPU Cluster Communication Model"** 과 §2.2(인터커넥트)가 직접 이어집니다.
- **§4.2 성능 저하 패턴 분석 + §4.3 체크리스트**는 그 자체로 운영 관점 과제 소재입니다.
- 서빙(추론)보다 학습/클러스터 인프라 쪽 비중이 크므로, 교재와는 **보완재**로 보는 것이 맞습니다.

---

## PDF에서 목차/텍스트를 다시 뽑고 싶다면

이 저장소의 PDF는 `pypdf` / `PyMuPDF(fitz)`로 목차를 추출했습니다.

```python
import fitz
d = fitz.open("knowledge/references/pdf/inference-engineering-2026.pdf")
for lvl, title, page in d.get_toc():
    print("  " * (lvl - 1) + f"- {title} (p.{page})")
```
