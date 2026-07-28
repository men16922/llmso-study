# 자료 심층 분석

[priority-guide.md](./priority-guide.md)에서 🔴필수 · 🟡권장으로 분류한 자료 중 **실제로 읽고 핵심만 뽑아낸** 정리입니다. 링크 목록과 달리 여기 있는 건 "그래서 뭐라고 쓰여 있는가"를 담았습니다.

| # | 자료 | 등급 | 연결 주차 |
|---|---|---|---|
| 1 | [Inside vLLM](#inside-vllm) | 🔴 | 4주차 CH8 |
| 2 | [KV Cache (chooblog)](#kv-cache-chooblog) | 🟡 | 1·3주차 |
| 3 | [GPU에서 Attention 실행 (chooblog)](#attention-kernel-chooblog) | 🟡 | 3주차 CH6 |
| 4 | [8계층 관측 스택 (jimmysong)](#8-layer-observability) | 🟡 | 6주차 |
| 5 | [toss GPU 클러스터 도입기](#toss-gpu-cluster) | 🟡 | 과제 소재 |
| 6 | [InfiniBand vs RoCE (fergusfinn)](#infiniband-vs-roce) | ⚪ | 7주차 배경 |
| 7 | [llm-d](#llm-d) | 🔴 | 7주차 |
| 8 | [GPU 용어집 (Modal)](#gpu-glossary) | ⚪ | 상시 참조 |

---

## Inside vLLM
### Anatomy of a High-Throughput LLM Inference System

원문: [aleksagordic.com/blog/vllm](https://www.aleksagordic.com/blog/vllm) · 🔴 **4주차 CH8의 최고 보조자료**

교재 CH8이 "vLLM 내부 구조"를 다루는데, 이 글은 같은 주제를 5개 섹션으로 더 깊게 해부합니다.

### 1. Engine Core — 3단계 루프

```
Schedule  →  Forward pass  →  Postprocess
```

| 구성요소 | 역할 |
|---|---|
| **Scheduler** | FCFS 또는 priority 정책으로 요청 큐 관리. 매 step마다 무엇을 실행할지 결정 |
| **Paged Attention** | KV-cache 매니저가 `free_block_queue`(가용 블록 풀)를 유지. 블록 단위 인덱싱으로 메모리 관리 |
| **Continuous Batching** | 여러 시퀀스를 하나의 **"super sequence"로 평탄화**. 패딩 없이 prefill/decode 혼합 실행 |

> 핵심: prefill은 **compute-bound**, decode는 **memory-bandwidth-bound**. 하나의 루프가 성격이 다른 두 작업을 함께 처리합니다.

### 2. 주요 기능

| 기능 | 내용 |
|---|---|
| **Chunked Prefill** | 긴 프롬프트를 잘게 나눠 **한 요청이 자원을 독점하지 못하게** 함 |
| **Prefix Caching** | 토큰을 해싱해 공유 프리픽스의 KV 블록을 재사용 → 재계산 회피 |
| **Guided Decoding** | 문법 기반 FSM으로 logits를 제약해 출력 형식 보장 |
| **Speculative Decoding** | 작은 draft 모델(n-gram, EAGLE, Medusa)이 여러 토큰을 제안 → 본 모델이 검증. **통계적 동등성** 유지 |
| **Disaggregated P/D** | prefill과 decode를 독립 인스턴스로 분리, 전용 KV-cache 서비스. 성능 특성이 다르므로 각각 최적화 |

### 3~4. 확장

- **UniProcExecutor → MultiProcExecutor**: 단일 GPU에서 텐서 병렬 분산으로. 메시지 큐로 워커 프로세스 오케스트레이션, 복잡성은 통합 인터페이스 뒤로 숨김
- **분산 서빙**: headless 노드가 engine core 실행 + ZMQ 소켓으로 조율, API 서버 노드가 DP coordinator로 로드밸런싱, FastAPI가 OpenAI 호환 엔드포인트 제공

### 5. 성능 지표

| 지표 | 의미 |
|---|---|
| **TTFT** (time-to-first-token) | 지연 민감 지표 |
| **ITL** (inter-token latency) | 처리량 경쟁에 영향 |
| **Roofline Model** | 배치 크기가 지연-처리량 트레이드오프를 만드는 방식. 포화점이 커널 동작을 결정 |

> 글의 결론: **지연 vs 처리량의 긴장은 설계 한계가 아니라 하드웨어의 근본 제약**입니다. paged memory가 효율적 배칭을 가능케 하고, continuous batching이 혼합 연산을 지원하며, 분산 메커니즘은 상위 계층에 투명하게 유지됩니다.

**함께 볼 것**: 교재 CH8 · [Inference Engineering CH5.5 Disaggregation](./pdfs.md) · [llm-d](#llm-d)

---

## KV Cache (chooblog)

원문: [chooblog.xyz/blog/kvcache](https://www.chooblog.xyz/blog/kvcache) · 🟡 **1·3주차** · 한국어

### 무엇인가

Self-Attention에서 **이전 토큰들의 Key/Value 벡터를 GPU 메모리에 저장해 재사용**하는 기법. 토큰을 순차 생성할 때 이전 토큰의 K·V가 계속 필요한데, 이 값들은 **한 번 계산되면 변하지 않으므로** 캐싱합니다.

### 왜 없으면 안 되는가

`Attention(Q,K,V) = softmax(QKᵀ/√d_k)V` 에서, KV Cache가 없으면 N개 토큰 생성 시 연산량이 **O(N²·L·d)** 에 비례 → 추론이 **수백 배** 느려집니다.

### 메모리 비용 ★

> **LLaMA-2 70B 기준 토큰당 약 328KB**

동시에 수십~수백 요청을 처리하려면 **KV Cache만으로 GPU 메모리 수십 GB**가 필요합니다. 이게 처리량을 직접 제한합니다. — 교재 CH5의 "KV cache 사이징"이 왜 중요한지가 여기 있습니다.

### 두 단계

| 단계 | 성격 |
|---|---|
| **Prefill** | 입력 프롬프트 전체를 한 번에 처리하며 K,V 계산 → **연산 집약적** |
| **Decode** | 토큰을 하나씩 생성하며 캐시된 K,V 활용 → **메모리 집약적** |

### 한계 → 최적화가 나온 이유

| 문제 | 대응 기술 |
|---|---|
| **메모리 단편화** — 할당량 > 실사용량 | vLLM **PagedAttention** |
| **용량 병목** — long-context에서 급증 | GQA/MQA, KV 압축, offloading |
| **중복 연산** — 동일 프롬프트/멀티턴 반복 | **Prefix caching**, SGLang **RadixAttention** |

**함께 볼 것**: [영상 KV cache 8분](https://youtu.be/sq3XGM1qdQY) · [Inference Engineering CH5.3](./pdfs.md) (p.138~143) · 교재 CH5·CH6

---

## GPU에서 Attention은 실제로 어떻게 실행되는가 {#attention-kernel-chooblog}

원문: [chooblog.xyz/blog/kernel-tensor_core](https://www.chooblog.xyz/blog/kernel-tensor_core) · 🟡 **3주차 CH6** · 한국어

커널 launch부터 Tensor Core까지 3단계로 추적합니다.

### 실행 파이프라인

| 단계 | 내용 |
|---|---|
| **1. Kernel Launch** | CPU가 launch 명령을 발행 (커널 코드 자체가 아니라 — 이미 **SASS 바이너리로 GPU 메모리에 존재**). GPU의 **GigaThread Engine**이 수신, **Compute Work Distributor**가 레지스터/공유메모리 여유를 보고 Thread Block을 SM에 배치 |
| **2. Thread Block & Warp 분배** | **Query 타일은 서로 다른 SM에서 병렬 처리**, **Key-Value 타일은 블록 내에서 순차 처리** (online softmax 의존성 때문). 이 **"split-Q"** 방식이 워프 간 통신 오버헤드를 회피 |
| **3. Tensor Core 연산** | 워프 연산이 행렬곱(**Tensor Core**)과 softmax(**일반 CUDA 코어**)로 분해됨 |

### FlashAttention-2의 핵심

표준 어텐션은 중간 행렬(S, P)을 **느린 HBM에 씁니다.** FlashAttention-2는 이 연산들을 **하나의 커널로 융합(fuse)** 해 중간 결과를 빠른 **SRAM에 유지**하고 최종 출력만 씁니다. → 막대한 HBM 트래픽 제거 + online softmax를 점진적으로 수행.

### 기술 포인트

- **Systolic MAC grid**: Tensor Core가 곱셈을 시간이 아닌 **공간적으로 병렬화**해 16× 속도
- **Online softmax**: 블록을 넘나들며 통계치(m, l, o)를 갱신, 새 최댓값이 나오면 이전 결과를 보정
- **구체 예**: 256×128 쿼리를 128×128 타일 2개로 나눠 2개 Thread Block에, 블록당 4 워프가 32행씩 담당

> 교재 **CH6 "커널 퓨전"** 이 추상적으로 느껴진다면 이 글이 가장 구체적인 답입니다.

**함께 볼 것**: [Flash attention 원리 7분](https://youtu.be/4Tw_ytMYHLI) · [Inference Engineering CH4.1](./pdfs.md) (CUDA 커널 퓨전)

---

## GPU에서 토큰까지 — 8계층 관측 스택 {#8-layer-observability}

원문: [jimmysong.io/blog/gpu-to-token-observability](https://jimmysong.io/blog/gpu-to-token-observability/) · 🟡 **6주차**

### 8개 계층

| 계층 | 무엇을 보나 |
|---|---|
| **L1 GPU 하드웨어** | GPU 사용률, SM occupancy, Tensor Core 활동, VRAM, 온도 |
| **L2 CUDA 런타임** | NCCL 통신 효율, 커널 실행 시간, **rank skew 탐지** |
| **L3 호스트/OS** | CPU, 메모리, 디스크 처리량, 네트워크, 프로세스 |
| **L4 K8s 스케줄링** | Pod/네임스페이스 소유권, GPU 공유 할당, 토폴로지 인식 |
| **L5 학습 런타임** | **MFU**(Model FLOPs Utilization), gradient 통계, loss, 체크포인트 시간 |
| **L6 추론 엔진** ★ | **TTFT, inter-token latency, KV cache 사용량, 배치 효율** |
| **L7 GenAI API** | 입출력 토큰 수, 요청 시간, 토큰 처리량 |
| **L8 비즈니스/비용** | **GPU 시간당 비용, 토큰당 비용**, 유휴 자원 비용, 에너지 효율 |

### 핵심 주장 ★

> **"GPU 사용률은 목적지가 아니다. 토큰 비용이 AI 인프라의 진짜 북극성 지표다."**

조직들이 **GPU 사용률은 높은데 사용자 체감 성능은 나쁜 역설**을 겪는 이유는 전체 스택을 관통하는 모니터링이 없기 때문입니다. 인프라 중심 GPU 스케줄링에서 **하드웨어부터 비즈니스 가치까지 잇는 관측**으로 옮겨가야 하며, 결국 **GPU가 바쁘게 도는지가 아니라 의미 있는 산출을 내는지**를 재야 합니다.

> [GPU-Enabled Platforms on K8s PDF CH5](./pdfs.md)의 **"할당 vs 실사용 격차(Allocation vs Utilization Gap)"** 와 정확히 같은 문제의식입니다. 6주차 Grafana 대시보드를 볼 때 이 8계층을 염두에 두면 무엇이 빠졌는지 보입니다.

---

## toss 고성능 GPU 클러스터 도입기 {#toss-gpu-cluster}

원문: [toss.tech/article/securities_llm_1](https://toss.tech/article/securities_llm_1) · 🟡 **과제 소재 추천** · 한국어

### 왜 자체 구축했나

증권 데이터를 분석해 투자 인사이트를 뽑으려는데:

- **상용 LLM은 금융 전문 지식이 부족**
- **"증권 관련 데이터는 매우 방대하며, 개인정보를 포함하고 있어 수집과 사용이 제한"** → 데이터 주권 문제로 온프레미스 선택
- **외부 API 비용 구조**(입출력 토큰 길이 과금)가 공격적인 기능 실험을 제약

### 기술적 판단

| 항목 | 내용 |
|---|---|
| **온프레미스** | 민감 정보를 사내에 유지 + API 비용 제거 |
| **하드웨어 균일성** ★ | **"아웃라이어가 하나라도 존재할 경우 성능 병목이 생겨 전체 클러스터 성능이 저하"** — 부품 균일성이 클러스터 성능을 좌우 |
| **GPU 선택** | H100의 **3TB/s 메모리 대역폭**(CPU의 약 50배)이 딥러닝 행렬 연산에 적합 |

### 배운 것

- **병렬 프로그래밍 복잡도**: 분산 GPU 시스템 디버깅은 기존 CPU 개발보다 훨씬 어려움
- **데이터 이동 병목**: CPU→GPU 데이터 이동에 상당한 시간 소모, 아키텍처 설계가 중요
- **기준선 검증**: 성능 테스트와 하드웨어 검증이 대규모 클러스터의 연쇄 장애를 예방

> 과제 유형 중 **"LLM 서빙 관련 운영 경험 중 기술 내용 위주로 정리"** 에 그대로 쓸 수 있는 사례입니다. [#2편](https://toss.tech/article/securities_llm_2)과 [MIG 도입기](https://toss.tech/article/toss-securities-gpu-mig)까지 3부작.

---

## InfiniBand vs RoCE {#infiniband-vs-roce}

원문: [fergusfinn.com/blog/infiniband-roce-rdma](https://fergusfinn.com/blog/infiniband-roce-rdma/) · ⚪ **7주차 배경**

### RDMA란

CPU를 거치지 않고, 커널 버퍼 복사 없이 **머신 간 애플리케이션 버퍼끼리 직접** 데이터를 옮깁니다. AI 워크로드에서 중요한 이유:

> **"gradient all-reduce — 수백 개 GPU가 각자의 gradient를 모두와 합치는 단계 — 는 모든 GPU가 기다려야 하는 배리어다."**

### 비교

| | **InfiniBand** | **RoCE** |
|---|---|---|
| 성격 | RDMA 전용으로 처음부터 설계된 완전한 네트워크 스택 | InfiniBand의 전송 계층을 **표준 이더넷(UDP/IP)** 위에서 실행 |
| 무손실 | credit 기반 흐름 제어로 **패킷 드롭 없음** | 이더넷 기반 |
| 하드웨어 | 전용 케이블·스위치·NIC 필요, 기존 인프라와 분리 | **범용 스위치** 활용, 기존 운영 지식 재사용 |
| 성능 | — | 동일 링크 속도에서 **네이티브 IB와 성능 동등** |

### 실무 판단 기준

1. **규모가 커지면 경제성은 RoCE** — 이더넷 스위치는 다수 벤더의 범용 제품, IB 스위치는 단일 벤더 특수 하드웨어
2. **운영 레버리지** — 팀이 이미 이더넷 모니터링·툴링을 앎. 별도 IB 패브릭은 별도 전문성 필요
3. **최상위에서도 둘 다 통함** — **Meta가 가장 큰 Llama 3를 RoCE 인프라에서 학습**시킴
4. **제약에 따라 다름** — 전통 HPC와 NVIDIA 레퍼런스 아키텍처는 IB, 하이퍼스케일러는 RoCE로 수렴 중

**함께 볼 것**: [NCCL 서브페이지](../subpages/nccl-communication.md) · [AWS 인터커넥트](../subpages/aws-interconnect.md) (AWS는 제3의 길인 EFA/SRD) · [NHN 백서 §2.2](./pdfs.md)

---

## llm-d

원문: [llm-d.ai/docs](https://llm-d.ai/docs) · 🔴 **7주차 실습 본체**

### 무엇인가

**쿠버네티스용 오픈소스 추론 서빙 스택.** 단일 노드 엔진을 **클러스터 규모 시스템으로 전환**하는 것이 목표입니다.

| 특징 | 내용 |
|---|---|
| **엔진 비종속** | vLLM, SGLang 등 지원 — 하나에 락인되지 않음 |
| **하드웨어 유연성** | NVIDIA, AMD, 커스텀 가속기 |
| **Well-Lit Paths** | 검증된 배포 레시피 — Helm 차트, Kustomize 매니페스트, 튜닝 파라미터, 모니터링 구성 |
| **고급 워크로드** | 에이전틱 파이프라인, 멀티모달, 배치 처리, 고처리량 서빙 |

### 문서 구성

1. **Getting Started** — 퀵스타트, 가속기 지원
2. **Well-Lit Paths** — Foundations(최적화·라우팅·캐싱·스케일링) / Workloads(에이전틱·멀티모달·배치)
3. **Concepts & Architecture**
4. **Operations & Monitoring**
5. **Infrastructure & Environments**
6. **API References**

### 배경

Red Hat, Google Cloud, IBM Research, CoreWeave, NVIDIA가 참여하는 **CNCF Sandbox** 프로젝트.

> **예습 순서**: 교재 CH7의 **prefill-decode disaggregation** → CH8의 **vLLM 내부** → [Inside vLLM](#inside-vllm)의 Disaggregated P/D 절 → llm-d 문서. 이 순서로 보면 llm-d가 왜 이렇게 설계됐는지가 보입니다.

---

## GPU 용어집 (Modal) {#gpu-glossary}

원문: [modal.com/gpu-glossary](https://modal.com/gpu-glossary/readme) · ⚪ **상시 참조용**

GPU 문서가 파편화된 문제를 풀려고 Modal이 만든 **하이퍼텍스트 레퍼런스**. 4개 범주:

| 범주 | 내용 |
|---|---|
| **Device Hardware** | SM, CUDA 코어, 캐시, 메모리 시스템 |
| **Device Software** | 스레드, 워프, 커널, 메모리 계층 |
| **Host Software** | 컴파일러, 드라이버, API, 라이브러리 (CUDA 런타임, cuBLAS, cuDNN) |
| **Performance** | roofline 모델, occupancy, 메모리 병합, 병목 식별 |

### 이 스터디에서의 유용도 — 제한적

**저수준 GPU 메커니즘 설명은 훌륭**하지만, LLM 서빙은 모델 분할·배치 스케줄링·양자화·추론 프레임워크 같은 **상위 관심사**가 중심입니다.

> **쓰는 법**: 처음부터 읽지 마세요. LLM 자료를 보다가 **모르는 하드웨어 용어가 나올 때 찾아보는 사전**으로 쓰는 게 맞습니다. 상호 연결된 하이퍼텍스트라 추상화 계층을 넘나들며 개념을 잡기 좋습니다.

---

## 아직 분석하지 않은 자료

시간 대비 효용을 고려해 **링크와 분류만** 해둔 것들입니다. 필요하면 같은 형식으로 추가할 수 있습니다.

| 자료 | 위치 |
|---|---|
| Netflix 사내 LLM 서빙 (Medium 로그인 리다이렉트로 본문 미확보) | [articles-and-blogs.md](./articles-and-blogs.md) |
| aleksagordic Collective Communication / matmul kernels | 〃 |
| jimmysong 나머지 3편, fergusfinn 나머지 3편 | 〃 |
| winterrykim 3편, inferencex, HAMi 블로그 | 〃 |
| KServe/MLflow/Knative 시리즈 | 〃 |
| 영상 60여 편 (제목·길이·분류만 정리됨) | [videos.md](./videos.md) |
