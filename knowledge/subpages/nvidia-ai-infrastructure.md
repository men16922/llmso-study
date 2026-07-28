# NVIDIA AI Infrastructure

원문: [노션 서브페이지](https://app.notion.com/p/gasidaseo/NVIDIA-AI-Infrastructure-3a450aec5edf802eadaff3b99cffc9fa) 🚒

NVIDIA AI 인프라 전체 스택을 **6개 레이어로 계층화**한 목차 중심 페이지입니다. 각 항목은 토글 안에 상세 내용이 들어 있습니다.

## 구성

```
Inside an AI-Centric DataCenter   ← 데이터센터 관점
NVIDIA Technology Stack (L1~L6)   ← 기술 스택 계층
AI Workflows                      ← 워크플로우/운영
```

---

## 1. Inside an AI-Centric DataCenter

| 주제 | 내용 |
|---|---|
| CPU vs GPU Arch | 아키텍처 차이 |
| **DPU** | Data Processing Unit |
| Network Fabric | 네트워크 패브릭 |
| **Ethernet vs InfiniBand** | 상호 비교 |
| Converged Ethernet (CE) | RoCE 계열 |
| Storage | 스토리지 |

## 2. NVIDIA Technology Stack — 6계층

### Layer 1: Physical Layer

- **DGX A100 Platform**, **DGX SuperPOD**
- **ConnectX** IB HCAs / NICs
- **BlueField** DPUs / SuperNICs
- NVIDIA Reference Architectures
- GPU Cores / GPU Family — **CUDA Cores, Tensor Cores, RT Cores**
- NVIDIA DGX Platform Timeline, **DGX A100 vs H100**

### Layer 2: Data Movement and I/O Acceleration

- **NVLink, NVSwitch**
- **InfiniBand (IB)**, IB vs CE
- **DMA and RDMA**
- **GPUDirect RDMA**
- **GPUDirect Storage**
- Quick Comparison

> [GPU Interconnect Bandwidth](./gpu-interconnect-bandwidth.md) 문서와 가장 많이 겹치는 계층입니다.

### Layer 3: DGX OS, GPU Drivers, vGPU / MIG

- GPU Drivers
- **CPU vs GPU Virtualization**
- **vGPU vs MIG**

> [HAMi 서브페이지](./hami-gpu-virtualization.md)의 "SW 격리 vs HW 격리(MIG)" 논의와 연결됩니다.

### Layer 4: CUDA, NCCL

- **CUDA**
- **NCCL**
- NVLink, NVSwitch, PCIe, RDMA **vs** NCCL

> [NCCL 서브페이지](./nccl-communication.md) 참조.

### Layer 5: Monitoring and Management

- **nvidia-smi**
- **DCGM**
- **BCM** (Base Command Manager)
- NVIDIA Tools for monitoring and management

> [PC GPU 설정 실습](./gpu-setup-docker-k8s.md) 6단계(DCGM Exporter)와 연결됩니다.

### Layer 6: Application & Vertical Solutions

## 3. AI Workflows

| 주제 | 내용 |
|---|---|
| ML Frameworks | |
| The NVIDIA Differentiator | |
| **Model Training vs Model Inference** | 학습과 추론의 차이 |
| **Job Scheduling — Container Orchestration** | |
| **Slurm vs K8s** | 워크로드 매니저 비교 |
| NVIDIA Integration | |
| NVIDIA Tools Supporting MLOps | |

---

## 어떻게 쓰면 좋은가

이 페이지는 **지도(map)** 성격입니다. 개별 주제를 깊게 파기 전에 "지금 내가 보는 게 스택의 어느 층인가"를 확인하는 용도로 쓰세요.

| 알고 싶은 것 | 이 스택에서 | 함께 볼 문서 |
|---|---|---|
| GPU 간 통신이 왜 느린가 | Layer 2 | [GPU Interconnect](./gpu-interconnect-bandwidth.md) · [NCCL](./nccl-communication.md) |
| GPU를 어떻게 나눠 쓰나 | Layer 3 | [HAMi](./hami-gpu-virtualization.md) |
| GPU 상태를 어떻게 보나 | Layer 5 | [PC GPU 설정](./gpu-setup-docker-k8s.md) · [AI Factory Ops Lab](./ai-factory-ops-lab.md) Lesson 3 |
| Slurm이냐 K8s냐 | AI Workflows | [AI Factory Ops Lab](./ai-factory-ops-lab.md) Lesson 2 (작성 예정) |
