# [AWS] 고성능 컴퓨팅 네트워크 & 분산 트레이닝 관점에서의 AWS 인터커넥트 기술

원문: [노션 서브페이지](https://app.notion.com/p/gasidaseo/AWS-AWS-3aa50aec5edf8018aef9c4db2b0e05cd)

AWS 한국 기술 블로그의 두 시리즈(총 6편)를 정리한 페이지입니다. 원문 링크는 [`references/articles-and-blogs.md`](../references/articles-and-blogs.md) §2에 모두 정리해 두었습니다.

## 구성

| 시리즈 | 편 | 제목 |
|---|---|---|
| **AWS 고성능 컴퓨팅 네트워크** | 1부 | AWS가 제공하는 고속 네트워크 인터페이스, **EFA** (Elastic Fabric Adapter) |
| | 2부 | AWS가 제공하는 고성능 네트워크 프로토콜, **SRD** (Scalable Reliable Datagram) |
| **분산 트레이닝 관점에서의 AWS 인터커넥트 기술** | 1편 | AWS는 왜 인터커넥트 기술로 EFA를 사용하는가? |
| | 2편 | AWS의 인터커넥트 기반 기술, **ENI** 소개 |
| | 3편 | AWS 환경에서 **NCCL**을 이용한 GPU 간 통신 |
| | 4편 | 분산 트레이닝을 위해 알아야 할 **GPU 간 고속 통신 기술** |
| 부록 | | Building Blocks for Foundation Model Training and Inference on AWS |

---

## 핵심 개념 — EC2 네트워크 인터페이스 3종

AWS EC2 인스턴스 간 네트워크 인터페이스는 **ENI / ENA / EFA** 세 가지로 나뉩니다.

| 인터페이스 | 성격 | 대역폭 | 비고 |
|---|---|---|---|
| **ENI** (Elastic Network Interface) | TCP/IP 기반 기본 인터페이스 | 일반적으로 **10Gbps 이하** | AWS의 기본 가상 네트워크 인터페이스 |
| **ENA** (Elastic Network Adapter) | TCP/IP 기반 + **SR-IOV** (단일 루트 I/O 가상화) — 하나의 물리 네트워크 디바이스를 여러 가상 디바이스로 구현 | **최대 100Gbps** | HPC 클러스터 구현은 가능하나, **초저지연 고속 네트워크가 필요한 환경엔 일반적으로 비권장** |
| **EFA** (Elastic Fabric Adapter) | AWS 자체 개발 프로토콜 **SRD** 탑재 | 일반적으로 **100Gbps 이상** | 대량 엔지니어링 시뮬레이션, Gen AI ML 트레이닝 등 **고성능 HPC 인프라에 권장** |

> **결론**: AWS에서 대규모 ML 트레이닝이나 HPC 인프라를 구축한다면 **EFA가 탑재된 인스턴스**를 사용하세요.

## 왜 EFA인가

- 일반 TCP/IP 스택은 커널을 거치므로 지연이 큼 → EFA는 **OS 커널 바이패스**로 지연을 줄임
- **SRD**(Scalable Reliable Datagram)는 AWS가 자체 개발한 프로토콜로, InfiniBand의 대안 역할
- **NCCL**이 EFA 위에서 동작하도록 지원 (aws-ofi-nccl 플러그인) → 3편의 주제

---

## 온프레미스 기술과의 대응 관계

| 계층 | 온프레미스 | AWS |
|---|---|---|
| 노드 내부 GPU 연결 | NVLink / NVSwitch | NVLink / NVSwitch (동일) |
| 노드 간 인터커넥트 | InfiniBand / RoCEv2 | **EFA + SRD** |
| 집합통신 라이브러리 | NCCL | NCCL (+ aws-ofi-nccl) |

> [GPU Interconnect Bandwidth](./gpu-interconnect-bandwidth.md)와 [NCCL](./nccl-communication.md) 문서가 온프레미스 관점이라면, 이 문서는 **같은 문제를 클라우드가 어떻게 푸는가**를 보여줍니다.

## 스터디 연결

- [NCCL: GPU Cluster Communication Model](./nccl-communication.md) — 3편의 배경 이론
- [NHN Cloud GPU 백서](../references/pdfs.md) §2.2 — InfiniBand 기반 온프레미스 설계와 비교
- [fergusfinn: 인피니밴드, RoCE, 그리고 그 외 모든 것들](https://fergusfinn.com/blog/infiniband-roce-rdma/) — 프로토콜 비교 심화
- **6주차 AWS EKS 실습**에서 다중 GPU 노드를 쓴다면 EFA 지원 인스턴스 여부가 성능을 좌우합니다
