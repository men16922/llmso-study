# NCCL: GPU Cluster Communication Model

원문: [노션 서브페이지](https://app.notion.com/p/gasidaseo/NCCL-GPU-Cluster-Communication-Model-3aa50aec5edf807c89b1d273875d1f07)
출처 도서: **Deep Learning for Network Engineers** (2025.5) — CH14: GPU Cluster Communication Model - NCCL

## 한 줄 요약

분산 학습 작업이 **시작되는 순간부터 그래디언트가 동기화되기까지** 무슨 일이 일어나는지를, NCCL Unique ID 배포 → Broadcast → **Ring AllReduce(ReduceScatter + AllGather)** 순서로 단계별 추적한 문서입니다.

---

## 0. 전제 — 세 가지 소프트웨어의 역할 분담

| 구성요소 | 역할 |
|---|---|
| **PyTorch** | 전체 학습 워크플로우 관리 — 데이터 로딩, 모델 정의, 병렬 실행, 그래디언트 동기화. 신경망 구조(레이어 수, 뉴런 수, 활성화 함수)를 정의하고 가중치 자동 초기화 |
| **CUDA** | CPU 메모리(DRAM) → GPU 메모리(VRAM) 데이터 이동의 메모리 할당. 순방향 패스에서 행렬 곱셈·활성화 함수 계산·오류 계산, 역방향 패스에서 그래디언트 계산 및 로컬 가중치 업데이트 |
| **NCCL** | GPU 간 고성능 데이터 교환을 위한 **다중 GPU·토폴로지 인식 집단 알고리즘**. CUDA가 각 GPU에서 그래디언트를 계산한 후, NCCL이 집단 통신으로 다른 GPU에 전송 |

NCCL이 지원하는 연산: **AllReduce, Broadcast, Reduce, AllGather, ReduceScatter**

예제 구성: **2개 노드(Host A, Host B) × 각 4 GPU = 총 8 GPU**

---

## 1. NCCL Unique ID 배포 — 통신 그룹 부트스트랩

여러 노드의 GPU가 통신하려면 먼저 **커뮤니케이터**(누가 참여하고 어떻게 데이터를 교환할지 정의하는 공유 컨텍스트)에 동의해야 합니다. 이를 위해 **NCCL Unique ID**라는 특수 식별자가 필요합니다.

- 지정된 **마스터 프로세스가 한 번 생성**한 뒤 다른 모든 프로세스와 공유
- **세션 식별자** 역할 — 모든 참여 GPU 프로세스가 동일한 통신 그룹에 가입하도록 보장
- 이게 없으면 AllReduce/Broadcast에 쓰이는 **링·트리 토폴로지를 구축할 공통 기준점이 없음**
- **네임스페이스 식별자** 역할도 함 — 같은 노드 집합에서 여러 분산 작업이 동시에 돌 때 작업 간 교차 대화(cross-talk) 방지

### 1-1. 마스터 노드에 TCP 소켓 열기

`torchrun` 명령으로 학습 작업이 시작되면 PyTorch 분산 프레임워크가 **각 노드에서 GPU당 하나의 프로세스**를 시작합니다. 각 프로세스는 **글로벌 랭크 ID**로 식별됩니다.

```
글로벌 랭크 ID = (--node_rank=n) × (--nproc_per_node=4) + 로컬 GPU 랭크
```

- **랭크 0** (Host A의 GPU 0) = **마스터 랭크**
- PyTorch가 `--master_addr=192.168.10.101`, `--master_port=12345`로 TCP 리스너를 엶
- `--nnodes=2`, `--nproc_per_node=4` → 마스터는 **랭크 1~7까지 7개 연결 요청**을 예상
- Host B의 랭크 4-7은 `192.168.10.101`을, **로컬 랭크 1-3은 루프백 `127.0.0.1`** 을 사용

이 연결 단계가 **랑데부(rendezvous) 프로세스**를 가능하게 합니다.

> **비유**: L3 멀티캐스트의 Rendezvous Point(RP)와 느슨하지만 유용한 유사점이 있습니다. 두 경우 모두 랑데부가 **조정 메커니즘**으로 작동합니다.

### 1-2. TCP 소켓을 통한 ID 배포

- 모든 랭크가 마스터와 TCP 연결을 맺으면, 마스터가 ID를 생성해 랭크 1~7에 전송
- 이 연결은 보통 **프론트엔드 또는 관리 네트워크**를 통해 흐름 (백엔드 GPU 네트워크가 아님)
- 모든 랭크가 이 ID로 **로컬 NCCL 커뮤니케이터를 초기화**

## 2. Broadcast — 모델 파라미터 동기화

모든 GPU가 **동일한 모델 파라미터로 시작**하도록 보장하는 단계입니다.

- 마스터가 ID를 공유한 후, NCCL 라이브러리가 **트리 토폴로지**를 구축
- **Broadcast 집합체**로 모델 파라미터를 모든 GPU에 전송

| 경로 | 방식 |
|---|---|
| **노드 내부** (랭크 1-3) | 고속 **NVLink를 통한 직접 메모리 복사**. CPU·운영체제를 거치지 않고 Queue Pair도 불필요 → 매우 빠르고 효율적 |
| **노드 간** (랭크 4-7) | **Queue Pair(QP)** 를 설정해 직접 데이터 경로 생성. **백엔드 네트워크**(예제에서는 라우팅된 L3 Clos Fabric) 사용 |

## 3. AllReduce — 그래디언트 동기화 ★ 이 문서의 핵심

순방향 패스 후 각 GPU가 역방향 패스로 그래디언트를 계산합니다. 이 그래디언트는 **버킷(bucket)** 이라는 예약 메모리 영역에 저장됩니다.

> **Iteration이란**: 미니 배치 하나를 GPU에 넣고 forward → loss 계산 → backward → weight 업데이트까지 한 번 수행하는 단위. 즉 모델이 한 번 배우는 작은 걸음.

### 설정

- 마지막 레이어에 **1024개 파라미터**, 각 GPU가 1024개 전부에 대해 그래디언트 계산
- 버킷을 **4개 청크**로 분할: 1024 ÷ 4 GPU = **청크당 256개 그래디언트**
- 각 GPU가 청크 **A–D**를 보유
- 담당: 랭크 0 → 청크 A, 랭크 1 → B, 랭크 2 → C, 랭크 3 → D
- **노드 내는 NVLink, 노드 간은 RoCEv2**

> 단방향 링 토폴로지에서 AllReduce는 **ReduceScatter → AllGather** 두 단계로 구현됩니다.

### 3-1. ReduceScatter (3회 반복)

각 랭크가 담당 청크를 링의 **다음 랭크**로 전송하고, 이웃에게서 하나를 받아 **자신의 로컬 버전에 더합니다**.

| 반복 | 상태 |
|---|---|
| **1회차** | 각 GPU가 원본 청크 3개 + **부분 축소된 청크 1개** 보유. 예: 랭크 0이 D3를 D0에 더함 → `chunk D = D0 + D3` |
| **2회차** | 두 번 부분 축소된 청크 1개 + 아직 통신에 안 쓰인 원본 2개 + 이번에 내보낸 것 1개. 예: 랭크 0은 `C = C2+C3+C0` 보유, 원본 A0·B0 유지, `D = D3+D0` 송출 |
| **3회차** | **ReduceScatter 완료.** 각 랭크가 **완전히 축소된 청크 정확히 1개**를 보유 (단, 원래 자기 소유였던 청크가 아닐 수 있음) |

**ReduceScatter의 목표**: 각 그래디언트의 합(또는 평균)을 계산. 종료 시 각 GPU는 4개 GPU 모두의 기여가 포함된 완전 축소 청크 1개를 갖습니다.

### 3-2. AllGather (3회 반복)

완전히 축소된 청크를 **모든 GPU에 다시 배포**하여, 각 GPU가 전체 그래디언트의 완전한 사본을 갖게 합니다.

| 반복 | 상태 |
|---|---|
| **1회차** | 각 GPU가 축소 청크 2개 보유 (자기가 축소한 것 + 이웃에게 받은 것) |
| **2회차** | 각 GPU가 축소 청크 3개 보유. **GPU당 1개만 누락** |
| **3회차** | **완료.** 모든 GPU가 A, B, C, D 4개 청크를 모두 수신 → **완전히 축소된 1024개 그래디언트 세트** 보유 |

### 3-3. 마무리 — 합을 평균으로

AllReduce는 **합**을 계산하지만, 데이터 병렬 학습에서는 보통 **평균**이 필요합니다.

- 각 GPU가 1024개 그래디언트를 **GPU 수(4)로 요소별 나눗셈**
- 이는 **추가 통신 없이 각 GPU에서 독립적으로 수행되는 로컬 연산**
- 모든 GPU가 동일한 동기화 데이터에서 평균을 내므로 결과는 클러스터 전체에서 일관됨
- 이후 추가 동기화 불필요 → 다음 학습 반복 시작 가능

---

## 왜 이 문서가 중요한가

| 관점 | 이유 |
|---|---|
| **인터커넥트가 왜 중요한지 체감** | AllReduce 한 번에 노드 내 NVLink와 노드 간 RoCEv2가 몇 번씩 오갑니다. [GPU Interconnect Bandwidth](./gpu-interconnect-bandwidth.md)에서 말한 "GPU 간 통신이 critical path에 들어간다"의 구체적 근거 |
| **Ring 토폴로지의 비용 구조** | N개 GPU에서 ReduceScatter N-1회 + AllGather N-1회 = 총 2(N-1) 스텝. GPU를 늘릴수록 통신 스텝이 선형 증가 |
| **서빙과의 관계** | 이 문서는 **학습(training)** 관점입니다. 다만 llm-d 같은 분산 **추론** 스택에서도 텐서 병렬·전문가 병렬 시 동일한 집합통신이 쓰입니다 |

## 스터디 연결

- [GPU Interconnect Bandwidth](./gpu-interconnect-bandwidth.md) — NVLink/NVSwitch/PCIe 물리 계층
- [AWS 인터커넥트](./aws-interconnect.md) — 3편이 "AWS 환경에서 NCCL을 이용한 GPU 간 통신"
- [NHN Cloud GPU 백서](../references/pdfs.md) §4.2 — 네트워크 병목(Communication-bound) 패턴
- [Inside TPU and GPU Clusters: The Anatomy of Collective Communication](https://www.aleksagordic.com/blog/collective-operations) — 같은 주제 영어 심화
