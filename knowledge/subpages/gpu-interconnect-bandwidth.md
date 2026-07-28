# [기초부터 이해하는 GPU Network] 1. GPU Interconnect Bandwidth

원문: [노션 서브페이지](https://gasidaseo.notion.site/GPU-Network-1-GPU-Interconnect-Bandwidth-38750aec5edf80428383e33957b728cf)

## 한 줄 요약

> GPU 서버 성능은 **GPU 개수만으로 결정되지 않는다.**
> `Disk → DRAM → CPU → PCIe → GPU Memory → GPU` 흐름, **HBM 메모리 대역폭**, 그리고 GPU 간 **PCIe/NVLink/NVSwitch 토폴로지**가 함께 성능을 결정한다.

핵심 주장 4가지:

- GPU 클러스터의 주된 병목은 **메모리 대역폭**이다. GPU는 계산은 빠르지만 HBM에서 데이터를 충분히 빨리 못 받으면 **대기한다**.
- Multi-GPU 서버에서는 GPU 개수보다 **GPU 간 연결 구조**가 더 중요하다. PCIe-only / NVLink pair / 4-way NVLink / HGX NVSwitch fabric은 성능 특성이 완전히 다르다.
- 대형 LLM 학습·추론에서는 GPU 간 **activation, intermediate tensor, KV cache, gradient 교환**이 critical path에 들어간다.
- **NVSwitch 기반 HGX** 구조가 GPU 간 통신을 가장 균일하게 만들어 대형 모델에 유리하다.

---

## 1. 데이터 흐름 기초

### CPU만 쓸 때

```
Application → read()/mmap() → Linux Kernel → Page Cache 확인
  → Disk I/O 요청 → NVMe/SATA Controller
  → DMA로 Disk 데이터를 DRAM에 적재        # Disk → DRAM
  → CPU가 DRAM에서 읽어 Cache로            # DRAM → CPU
  → CPU Core 연산 → 결과 저장
```

**DMA(Direct Memory Access)**: Disk Controller가 CPU를 거치지 않고 DRAM에 직접 씀. 대량 데이터 이동은 Controller가 하고 CPU는 제어·연산에 집중. DMA가 없으면 CPU가 데이터 복사에 계속 묶임.

### GPU를 쓸 때

```
Disk → System DRAM → CPU → PCIe → GPU Memory → GPU(연산)
                                        ↓
                        (결과) GPU Memory → PCIe → DRAM → CPU
```

| 구간 | 하는 일 |
|---|---|
| Disk → DRAM | dataset, model weight, checkpoint가 메인 메모리로 |
| DRAM → CPU | 전처리, batch 구성, tensor 생성, 실행 흐름 제어 |
| CPU → PCIe | GPU 연산 요청, tensor 전송 시작 |
| PCIe → GPU Memory | 입력 tensor·model weight를 GPU 전용 메모리로 복사 |
| GPU Memory → GPU | GPU kernel 실행 |
| GPU → GPU Memory | 결과 저장. **다음 layer가 있으면 CPU로 돌아가지 않고 HBM 안에서 계속 이어짐** |
| GPU Memory → … → CPU | 최종 결과만 회수 |

## 2. 메모리 대역폭 병목 — "The Memory Wall" ★

- GPU 연산 코어는 충분히 빠른데 메모리에서 데이터를 가져오는 데서 병목 → GPU 입장에서 **'데이터 기아' 상태**
- **HBM(High Bandwidth Memory)**: 처리 *속도*가 아니라 **너비(Interface Width)** 를 확장. 이를 위해 DRAM 칩을 **수직으로 적층**하고, 기존 방식으로는 연결이 불가능해 **실리콘 인터포저**에 GPU와 HBM을 함께 연결

### 메모리 장벽의 수치

2026년 1월, 구글의 샤오위 마와 튜링상 수상자 데이비드 패터슨의 논문:

| 지표 | 2012→2022 증가 |
|---|---|
| NVIDIA GPU FP64 연산 성능 | **80배** |
| 메모리 대역폭 | **17배** |
| 격차 | 80 ÷ 17 ≈ **4.7배** |

이 4.7배 격차가 **"메모리 장벽(The Memory Wall)"** 이며, **나아지기는커녕 악화되고 있습니다.**

> LLM **학습과 Prefill**은 연산 성능이 중요하지만, 토큰을 한 개씩 만드는 **Decode**는 GPU FLOPS보다 **메모리 대역폭과 인터커넥트 지연시간**에 더 크게 제한된다.

이는 교재 CH5(Challenges When Serving LLMs)의 핵심 주제와 정확히 같습니다.

### 참고 자료

- [안될공학] GPU만 빠르면 뭐해? HBM과 CoWoS — AI 인프라 5가지 병목 · [Youtube](https://youtu.be/D0LxcXu9W3M)
- [Why is Inference Slow and Expensive?](https://theaiengineer.substack.com/p/why-is-inference-slow-and-expensive)
- [What is a GPU?](https://theaiengineer.substack.com/p/what-is-a-gpu)
- [GPU는 왜 AI에서 필수가 되었나 — 5. 병목: 메모리](https://velog.io/@infra_manager/GPU는-왜-AI에서-필수가-되었나)
- [HBM (나무위키)](https://namu.wiki/w/HBM)

## 3. 패키징 용어 정리

| 용어 | 쉽게 말하면 | 예시 |
|---|---|---|
| **Wafer** | 반도체를 한꺼번에 만드는 원판 | 300mm 실리콘 웨이퍼 |
| **Die** | 웨이퍼에서 잘라낸 실제 회로 조각 | GPU die, CPU die |
| **Chip** | 패키징되어 제품처럼 쓰이는 부품 | CPU chip, GPU chip |
| **Chiplet** | 큰 칩을 여러 작은 기능 die로 나눈 조각 | CPU compute chiplet, I/O die |
| **Package** | die/chiplet을 올리고 핀·전원·신호를 연결하는 물리 제품 | CPU 패키지 |
| **Interposer** | 여러 die를 고밀도로 연결하는 중간 연결판 | GPU + HBM 연결 |
| **Substrate** | 패키지 내부에서 die와 메인보드를 연결하는 기판 | organic substrate |
| **C2C** | chip-to-chip / die-to-die 고속 연결 | NVLink-C2C, UCIe |
| **SiP** | 여러 칩을 하나의 패키지로 묶은 제품 | CPU+GPU superchip |

## 4. 인터커넥트 계층 — 칩(다이)에서 Rack까지

### NV-HBI (다이 ↔ 다이)

한 패키지 안에서 GPU 다이 두 개를 직접 붙이는 기술. **Blackwell은 칩 하나가 사실 다이 두 개**이며, 이 둘을 약 **10 TB/s**로 이어 운영체제에는 단일 GPU로 보이게 만듭니다.

### NVLink-C2C (칩 ↔ 칩)

같은 패키지 안에서 **종류가 다른 칩(CPU ↔ GPU)** 을 잇습니다. Grace CPU와 Blackwell GPU를 **900 GB/s**로 연결하고 메모리를 **cache-coherent**하게 공유 — GPU가 CPU 메모리를, CPU가 GPU 메모리를 **복사 없이 바로** 들여다볼 수 있는 것이 핵심.

### NVSwitch Fabric > NVLink Bridge > PCIe

| 방식 | 성격 |
|---|---|
| **PCIe** | 범용 연결. CPU-GPU, GPU-GPU 모두 가능하나 대역폭이 상대적으로 낮음 |
| **NVLink** | GPU끼리 직접 잇는 고속 링크. 2-GPU 또는 4-GPU domain에 유리 |
| **NVSwitch** | 여러 GPU를 고대역폭 fabric으로 묶음. HGX 같은 8-GPU급 서버에서 통신 병목을 줄이는 핵심 |

```
PCIe-only GPU 서버      → GPU 간 통신이 상대적으로 느림
NVLink Bridge 서버      → 2장 또는 4장 묶음 안에서는 빠름
HGX + NVSwitch 서버     → 8장이 하나의 고속 GPU fabric처럼 통신
```

### 구성별 대역폭 비교

| 구성 | Form Factor / Topology | Interconnect | Point-to-Point BW |
|---|---|---|---|
| RTX PRO 6000 | PCIe Gen5 | PCIe | 128 GB/s bidirectional |
| H100 NVL | PCIe, 2-card bridge | NVLink | 600 GB/s bidirectional |
| H200 NVL | PCIe, 2-way bridge | NVLink | 900 GB/s bidirectional |
| H200 NVL | PCIe, 4-way bridge | NVLink | 1.8 TB/s aggregate, 900 GB/s per GPU |
| **HGX H100** | SXM + NVSwitch | NVSwitch | 900 GB/s per GPU to fabric |
| **HGX H200** | SXM + NVSwitch | NVSwitch | 900 GB/s per GPU to fabric |
| **HGX B200** | SXM + NVSwitch | NVSwitch | **1.8 TB/s per GPU to fabric** |

### 비유로 정리

- **NVLink** = GPU끼리의 **지름길**. 원래 GPU는 CPU를 거쳐야 다른 GPU와 통신했는데, 그 우회로를 없앰
- **NVSwitch** = **교차로**. 여러 GPU의 NVLink 포트를 하나의 스위치 칩에 모아, 어떤 GPU 쌍이든 같은 속도로 통신하는 **All-to-All 패브릭**
- **PCIe** = 시스템 전체의 **표준 도로**. 범용이라 호환성은 좋지만 AI가 요구하는 데이터량엔 좁음

같은 세대 기준 대역폭 차이는 약 **14배** (PCIe Gen5 ×16 약 128 GB/s vs NVLink 5 1.8 TB/s). 다만 PCIe가 사라진 건 아니고 CPU-GPU 표준 경로, NIC 등 I/O 장치 연결 통로로 여전히 쓰입니다.

## 5. 후속 예정

**Rack ↔ Rack 간 네트워크 장비**는 다른 연재글에서 작성 예정.

---

## 스터디 연결

- [NHN Cloud GPU 백서](../references/pdfs.md) §2.2(고속 인터커넥트)와 직접 이어집니다.
- [NCCL 서브페이지](./nccl-communication.md) — 이 인터커넥트 위에서 실제 집합통신이 어떻게 도는지
- [AWS 인터커넥트 서브페이지](./aws-interconnect.md) — 클라우드(EFA/SRD)에서의 대응 기술
- 원문 참고 블로그: [From A100 to B300: The Evolution of NVIDIA GPUs and Interconnects](https://medium.com/@dk02315/from-a100-to-b300-the-evolution-of-nvidia-gpus-and-interconnects-d01a892bd306)
