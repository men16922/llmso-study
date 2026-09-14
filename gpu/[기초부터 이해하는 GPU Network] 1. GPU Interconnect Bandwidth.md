

**`요약`** : GPU 서버 성능은 GPU 개수만으로 결정되지 않는다. Disk→DRAM→CPU→PCIe→GPU Memory→GPU **흐름**, HBM **메모리 대역폭**, 그리고 GPU 간 PCIe/NVLink/NVSwitch **topology가 함께 성능을 결정**한다.

1. GPU 클러스터의 주된 병목은 **메모리 대역폭**이다.
2. GPU는 계산은 매우 빠르지만, 데이터를 HBM쪽에서 충분히 빨리 공급받지 못하면 **GPU는 대기**한다.
3. Multi-GPU 서버에서는 GPU 개수보다 **GPU 간 연결 구조**가 더 **중요**하다.
4. PCIe-only, NVLink pair, 4-way NVLink domain, HGX NVSwitch fabric은 성능 특성이 완전히 다르다.
5. 대형 LLM 학습/추론에서는 GPU 간 activation, intermediate tensor, KV cache, gradient 교환이 critical path에 들어간다.
6. **NVSwitch** 기반 HGX 구조는 GPU 간 통신을 가장 균일하게 만들어 대형 모델에 유리하다.
- 연재 글 목록
    - [[기초부터 이해하는 GPU Network] 1. GPU Interconnect Bandwidth](https://app.notion.com/GPU-Network-1-GPU-Interconnect-Bandwidth-38750aec5edf80428383e33957b728cf?pvs=21)
    - [[기초부터 이해하는 GPU Infra] 2. 전력/냉각의 중요성](https://app.notion.com/GPU-Infra-2-38e50aec5edf80ab9faae86b2d12bac7?pvs=21)
    - [[기초부터 이해하는 GPU Infra] 3. 전력/냉각](https://app.notion.com/GPU-Infra-3-38e50aec5edf8046bf26d70039835ec9?pvs=21)
    - 

### 기초 지식

- 서버에서 Disk 데이터를 DRAM으로 가져와 CPU가 연산하는 흐름 : *(단순 Flow)* **Disk → DRAM → CPU(연산)**
    - Disk Controller가 DMA를 사용해 Disk 데이터를 DRAM으로 데이터를 옮기고, CPU는 DRAM에 올라온 데이터를 Cache로 읽어와 연산.
    - **흐름**
        
        !mermaid-diagram.png
        
        ```bash
        **Application**
        → read() / mmap()
        **→ Linux Kernel**
        → Page Cache 확인
        → Disk I/O 요청 생성
        **→ NVMe/SATA (Disk) Controller**
        **→ DMA로 Disk Data를 DRAM에 적재           # Disk -> DRAM**
        **→ CPU가 DRAM에서 데이터를 읽어 Cache로 가져옴  # DRAM -> CPU**
        → CPU Core가 연산
        → 결과를 Register/Cache/DRAM/File로 저장
        ```
        
        - *글 서술 시, 쉬운 이해를 위해 CPU 내부에 L1/L2/L3 Cache 와 Register 생략하고 CPU로 표현합니다.*
    - (참고) **DMA** Direct Memory Access 역할
        - Disk Controller가 CPU를 거치지 않고 DRAM에 직접 데이터를 씀 ⇒ 대량 데이터 이동은 Controller가 하고, CPU는 제어와 연산에 집중.
        - *DMA없을 경우 ⇒ CPU가 Disk Controller에서 데이터를 하나씩 읽고 DRAM에 써야 합니다. CPU가 데이터 복사 작업에 계속 묶임.*
    
- GPU를 사용하는 코드 실행 시, CPU/GPU 연산 흐름 : Disk → **DRAM** → CPU → PCIe/NVLink → **GPU Memory** → **GPU(연산)**
    - *(약식)* 구성 요소 : Disk - DRAM - CPU - PCIe/NVLink - GPU - GPU Memory
        
        !https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html
        
        https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html
        
    - Disk → System **DRAM** → CPU → PCIe → **GPU Memory** → **GPU(연산)** ⇒ (결과 리턴) GPU Memory → PCIe → DRAM → CPU
        1. Disk → DRAM : dataset, model weight, checkpoint 같은 데이터가 디스크에서 서버 메인 메모리인 System DRAM으로 올라온다.
        2. DRAM → CPU : CPU가 DRAM에 있는 데이터를 읽어서 전처리, batch 구성, tensor 생성, 실행 흐름 제어를 한다.
        3. CPU → PCIe : CPU가 GPU 연산을 요청하고, 필요한 tensor를 GPU 쪽으로 보내기 위해 PCIe 전송을 시작한다.
        4. PCIe → GPU Memory : 입력 tensor나 model weight가 PCIe를 통해 GPU 전용 메모리로 복사된다.
        5. GPU Memory → GPU(연산) : GPU가 GPU Memory에 있는 데이터를 읽어서 GPU kernel을 실행한다.
        6. GPU → (결과 리턴) GPU Memory : GPU 연산 결과는 다시 GPU Memory에 저장된다. 다음 layer나 다음 GPU kernel이 있으면 CPU로 돌아가지 않고 HBM 안에서 계속 이어진다.
        7. GPU Memory → PCIe → DRAM → CPU : 최종 결과를 CPU가 필요로 하면 GPU Memory의 결과가 PCIe를 통해 DRAM으로 복사되고, CPU가 그 값을 읽어서 출력, 저장, 후처리를 한다.
    - **요약**
        - 입력 준비: Disk → DRAM → CPU
        - GPU로 전달: CPU → PCIe → GPU Memory
        - GPU 연산: GPU Memory ↔ GPU
        - 결과 회수: GPU Memory → PCIe → DRAM → CPU
    - **정리**
        - Disk 데이터는 CPU DRAM 옮겨가고, 다시 GPU Memory로 옮겨간 후, GPU 내부로 옮겨간 후 GPU가 연산 수행!
            
            !출처 toss tech : https://toss.tech/article/securities_llm_2
            
            출처 toss tech : https://toss.tech/article/securities_llm_2
            

### GPU 클러스터 주된 병목 : 메모리 대역폭

- **병목**(**메모리 대역폭**) 이해를 위한 추천 정보
    - [안될공학] **GPU만 빠르면 뭐해?** ... HBM과 CoWoS가 없어서 못 팔게된 이유 | **AI 인프라 5가지 병목** - Youtube
    - https://velog.io/@infra_manager/GPU는-왜-AI에서-필수가-되었나#5-병목-메모리
    - Why is Inference Slow and Expensive? - Blog
        
        
- GPU **연산 코어 Compute Core**는 충분히 빠른데, **메모리에서 데이터를 가져오는데 병목이 발생** *⇒ GPU 입장에서 ‘데이터 기아’ 상태*
    - **HBM** High Bandwidth Memory : 처리 속도가 아닌 너비(Interface Width)를 확장 ← 이를 위해 DRAM 칩을 수직으로 쌓아올림
        - 기존의 GPU/CPU 와 Memory 연결이 불가능 → (반도체 웨이퍼를 가공해서 만든)실리콘 인터포저에 GPU와 HBM을 연결
        
        !https://namu.wiki/w/HBM
        
        https://namu.wiki/w/HBM
        
        !https://youtu.be/D0LxcXu9W3M?si=WcN9wbVwiZo8eujG&t=489
        
        https://youtu.be/D0LxcXu9W3M?si=WcN9wbVwiZo8eujG&t=489
        
        !https://theaiengineer.substack.com/p/what-is-a-gpu
        
        https://theaiengineer.substack.com/p/what-is-a-gpu
        
    - GPU는 메모리가 데이터를 공급하는 속도보다 훨씬 빠르게 연산을 처리할 수 있습니다.
        - 텍스트 생성 과정에서 고가의 GPU는 아무런 작업도 하지 않고 대기 상태에 놓이게 됩니다.
    
- "**메모리 장벽** The Memory Wall"
    - 2026년 1월, 구글의 샤오위 마와 튜링상 수상자 데이비드 패터슨이 발표한 논문은 이 문제에 대해 정확한 수치를 제시합니다.
        - *LLM 학습과 Prefill은 연산 성능이 중요하지만, 토큰을 한 개씩 만드는 Decode는 GPU FLOPS보다 **메모리 대역폭과 인터커넥트 지연시간**에 더 크게 제한된다,*
    - GPU 연산 능력은 2012년부터 2022년까지 80배 증가했지만, 메모리 대역폭은 17배만 증가했습니다.
        - *2012~2022년 NVIDIA GPU의 **FP64 연산 성능은 80배**, 메모리 대역폭은 **17배** 증가했습니다. `80 ÷ 17 ≈ 4.7`이므로, 연산 성능과 메모리 공급 능력 사이의 **상대적 불균형이 약 4.7배 확대**됐다*
    - 4.7배라는 격차를 "**메모리 장벽** The Memory Wall"이라고 부르는데, 이 현상은 나아지기는커녕 악화되고 있습니다.
        
        !https://theaiengineer.substack.com/p/why-is-inference-slow-and-expensive
        
        https://theaiengineer.substack.com/p/why-is-inference-slow-and-expensive
        
        !https://qtscott.tistory.com/1 지난 10여 년간 GPU의 연산 성능 증가폭은 메모리 대역폭 증가폭을 크게 앞질렀다
        
        https://qtscott.tistory.com/1 지난 10여 년간 GPU의 연산 성능 증가폭은 메모리 대역폭 증가폭을 크게 앞질렀다
        

### GPU Interconnect Bandwidth

- **The Evolution of NVIDIA GPUs and Interconnects** : ‘칩(다이) → Rack 간’ - Blog ⇒ 해당 원글에 스샷을 포함하여 정리하였습니다.
    
    !https://medium.com/@dk02315/from-a100-to-b300-the-evolution-of-nvidia-gpus-and-interconnects-d01a892bd306
    
    https://medium.com/@dk02315/from-a100-to-b300-the-evolution-of-nvidia-gpus-and-interconnects-d01a892bd306
    
    - **용어 정리**
        
        ```bash
        **Die** = 실제 회로가 새겨진 실리콘 조각
        **Chiplet** = 특정 기능을 담당하는 작은 die
        **Chip** = die/chiplet을 패키징한 제품 또는 넓은 의미의 반도체 칩
        **Package** = die/chiplet을 담고 외부와 연결하는 물리 단위
        **C2C** = die/chiplet/chip 사이를 연결하는 인터커넥트
        ```
        
        | 용어 | 쉽게 말하면 | 예시 |
        | --- | --- | --- |
        | **Wafer** | 반도체를 한꺼번에 만드는 원판 | 300mm 실리콘 웨이퍼 |
        | **Die** | 웨이퍼에서 잘라낸 실제 회로 조각 | GPU die, CPU die |
        | **Chip** | 패키징되어 제품처럼 쓰이는 반도체 부품 | CPU chip, GPU chip |
        | **Chiplet** | 하나의 큰 칩을 여러 작은 기능 die로 나눈 조각 | CPU compute chiplet, I/O die |
        | **Package** | die/chiplet을 올리고 외부 핀·전원·신호를 연결하는 물리 제품 | CPU 패키지, GPU 패키지 |
        | **Interposer** | 여러 die를 고밀도로 연결하는 중간 연결판 | GPU + HBM 연결 |
        | **Substrate** | 패키지 내부에서 die와 메인보드를 연결하는 기판 | organic substrate |
        | **C2C** | chip-to-chip 또는 die-to-die 고속 연결 | NVLink-C2C, UCIe |
        | **SiP** | 여러 칩을 하나의 패키지로 묶은 제품 | CPU+GPU superchip |
    
1. **다이 ↔ 다이** Die **: NV-HBI** (High-Bandwidth Interface)
    
    !image.png
    
    - **한 패키지** 안에서 **GPU 다이** Die **두 개**를 **직접 붙이는 기술**이다.
    - Blackwell은 칩 하나가 사실 다이 두 개인데, 이 둘을 약 10 TB/s로 이어 운영체제에는 단일 GPU로 보이게 만든다.
        
        !https://developer.nvidia.com/blog/inside-nvidia-blackwell-ultra-the-chip-powering-the-ai-factory-era/
        
        https://developer.nvidia.com/blog/inside-nvidia-blackwell-ultra-the-chip-powering-the-ai-factory-era/
        
    
2. **NVLink-C2C (Chip-to-Chip) :** NVSwitch 에 per GPU가 BW가 더 크지만, 칩 간 연결이라서 두번째로 설명함 **- Link**
    
    !image.png
    
    - **같은 패키지** 안에서 **종류가 다른 칩**, 즉 **CPU와 GPU**를 잇기.
    - Grace CPU와 Blackwell GPU를 900 GB/s로 연결하고 **메모리를 공유**(cache-coherent)한다.
    - GPU가 CPU 메모리를, CPU가 GPU **메모리를 복사 없이 바로 들여다볼 수 있다는 게 핵심!**
        
        !*Figure 2. NVIDIA Grace Hopper Superchip logical overview*
        
        *Figure 2. NVIDIA Grace Hopper Superchip logical overview*
        
        !Figure 1:Architecture of the Quad GH200 node of the Alps supercomputer. Every node is composed of four GH200 fully connected using NVLink and a cache coherent interconnect. Every GH200 is connected to a Slingshot network through a separate NIC.
        
        Figure 1:Architecture of the Quad GH200 node of the Alps supercomputer. Every node is composed of four GH200 fully connected using NVLink and a cache coherent interconnect. Every GH200 is connected to a Slingshot network through a separate NIC.
        
        !https://arxiv.org/html/2408.11556v2
        
        https://arxiv.org/html/2408.11556v2
        
    
3. **NVSwitch** Fabric **> NVLink** Bridge **> PCIe**
    
    !image.png
    
    !image.png
    
    - Multi-GPU 서버에서 주로 등장하는 연결 방식은 **PCIe, NVLink, NVSwitch**다.
        - **PCIe**: 범용 연결. CPU-GPU, GPU-GPU 통신 가능하지만 대역폭이 상대적으로 낮음.
        - **NVLink**: GPU끼리 직접 빠르게 연결하는 고속 링크. 2-GPU 또는 4-GPU domain 구성에 유리.
        - **NVSwitch**: 여러 GPU를 고대역폭 fabric으로 묶는 구조. HGX 같은 8-GPU급 서버에서 GPU 간 통신 병목을 줄이는 핵심.
        
        ```bash
        **PCIe-only GPU 서버**
        → GPU 간 통신이 상대적으로 느림
        
        **NVLink Bridge 서버**
        → 2장 또는 4장 GPU 묶음 안에서는 빠름
        
        **HGX + NVSwitch 서버**
        → 8장 GPU가 하나의 고속 GPU fabric처럼 통신
        ```
        
        | 구성 | Form Factor / Topology
        *GPU가 어떤 물리 형태와 구조로 장착되는지* | Interconnect
        *GPU 간 통신 기술* | Point-to-Point BW
        *GPU 간 또는 GPU-to-fabric 대역폭* |
        | --- | --- | --- | --- |
        | RTX PRO 6000 | PCIe Gen5 | PCIe | 128 GB/s bidirectional |
        | H100 NVL | PCIe, 2-card bridge | NVLink | **600 GB/s bidirectional** |
        | H200 NVL | PCIe, 2-way bridge | NVLink | 900 GB/s bidirectional |
        | H200 NVL | PCIe, 4-way **bridge** | **NVLink** | 1.8 TB/s aggregate, **900 GB/s per GPU** |
        | HGX H100 | SXM + NVSwitch | NVSwitch | 900 GB/s per GPU to fabric |
        | HGX H200 | SXM + NVSwitch | NVSwitch | 900 GB/s per GPU to fabric |
        | HGX B200 | SXM + NVSwitch | **NVSwitch** | **1.8 TB/s per GPU to fabric** |
    - **Multi-GPU Spectrum**
        
        !image.png
        
        - 그림은 단일 서버 안에서 가능한 Multi-GPU 연결 구조를 성능/균일성 관점으로 나열한다.
        - 왼쪽의 PCIe 기반 구성은 유연하지만 통신 병목이 크고, 오른쪽의 NVSwitch 기반 HGX 구성은 GPU 간 통신이 가장 균일하다.
        
    - **NVLink**
        - GPU와 GPU를 직접 잇는 고속 프로토콜이자, 위 두 가지의 뿌리가 되는 기술이다.
        - 원래 GPU는 CPU를 거쳐야만 다른 GPU와 통신했는데, **NVLink는 그 우회로를 없애고 GPU끼리 직접 데이터를 주고받**게 한다
            
            !*Figure 11. Memory accesses across NVLink-connected Grace Hopper Superchips*
            
            *Figure 11. Memory accesses across NVLink-connected Grace Hopper Superchips*
            
        
    - **NVSwitch**
        - NVLink가 ‘길’이라면 **NVSwitch는 ‘교차로**’다.
        - 여러 GPU의 NVLink 포트를 하나의 스위치 칩에 모아, 어떤 GPU 쌍이든 같은 속도로 직접 통신하는 All-to-All 패브릭을 만든다
            
            !*Figure 14. NVIDIA HGX Grace Hopper with NVLink Switch System for strong-scaling giant ML and HPC workload*
            
            *Figure 14. NVIDIA HGX Grace Hopper with NVLink Switch System for strong-scaling giant ML and HPC workload*
            
        
    - **PCIe**
        
        !image.png
        
        ![[**inter-GPU** bandwidth] **NVIDIA NVLink**: full-mesh topology as below, so (bi-directional) `GPU-to-GPU max bandwidth` is `400GB/s` (note that below is `8*A100` module, 600GB/s, `8*A800` shares a similar full-mesh topology)](attachment:6f7b393e-420b-4e95-a6e3-7d860130035e:image.png)
        
        [**inter-GPU** bandwidth] **NVIDIA NVLink**: full-mesh topology as below, so (bi-directional) `GPU-to-GPU max bandwidth` is `400GB/s` (note that below is `8*A100` module, 600GB/s, `8*A800` shares a similar full-mesh topology)
        
        - PCIe는 CPU와 주변장치(GPU, NIC, SSD 등)를 잇는 업계 표준 버스다.
        - 범용이라 호환성은 좋지만, AI가 요구하는 GPU 간 데이터량을 감당하기엔 좁다.
        - NVLink는 바로 이 PCIe 병목을 우회하려고 만든 GPU 전용 길이고, 같은 세대 기준 대역폭이 약 14배 차이 난다(PCIe Gen5 ×16 약 128 GB/s vs NVLink 5 1.8 TB/s).
        - 다만 PCIe가 사라진 건 아니다. CPU와 GPU를 잇는 표준 경로로, 또 NIC 같은 I/O 장치를 붙이는 통로로 여전히 쓰인다.
        - NVLink는 ‘GPU끼리의 지름길’, PCIe는 ‘시스템 전체의 표준 도로’라고 보면 된다.
    
4. **Rack ↔ Rack 간 네트워크 장비** : 다른 연재글에서 작성 예정입니다.
    
    !image.png
    
- [**참고**] Understanding Multi-GPU Topologies Within a Single Host : **GPU Interconnect Bandwidth** - Blog
    - **요약** : “한 서버 안에 GPU가 여러 장 있어도, GPU들이 모두 같은 속도로 통신하는 것은 아니다. PCIe, NVLink, NVSwitch, CPU Socket/NUMA 경계에 따라 GPU 배치가 모델 성능을 크게 좌우한다.”
        
        ```bash
        GPU 개수만 보면 안 된다.
        GPU 간 연결 구조를 봐야 한다.
        
        **4 GPU 서버라도**
        - PCIe 4장
        - NVLink 2쌍
        - 4-way NVLink 1도메인
        - SXM NVLink 도메인
        은 성능 특성이 다르다.
        
        **8 GPU 서버도**
        - PCIe + 2개의 4-GPU NVLink island
        - HGX + NVSwitch fabric
        은 완전히 다른 시스템이다.
        ```
        
        - **핵심 주제**: 단일 호스트 내부의 Multi-GPU 연결 구조와 분산 모델 성능 영향
        - **주요 기술**: PCIe Gen5, NVLink, NVLink domain, NVSwitch, HGX, H200 NVL, H100/H200/B200, NUMA, UPI, NVIDIA Fabric Manager
        
    - **핵심 메시지**
        - 분산 모델은 여러 GPU에 weight를 나누어 올리고, inference 중 intermediate tensor, activation, KV cache 조각을 계속 교환한다.
        - 이 교환은 작은 단계의 collective operation으로 반복되며, **각 단계는 가장 느린 GPU 간 경로를 기다린다**.
            
            ```bash
            GPU 0: 계산 완료
            GPU 1: 계산 완료
            GPU 2: 계산 완료
            **GPU 3: 아직 데이터 수신 중**
            
            → 전체 다음 단계는 GPU 3을 기다림, 즉 나머지 CPU0,1,2는 대기중...
            ```
            
        - 따라서 "GPU 개수"보다 "GPU들이 어떤 경로로 연결되어 있는지"가 실제 scaling efficiency를 좌우한다.
        - 같은 서버 안의 GPU라도 PCIe root complex, CPU socket, UPI, NVLink domain 경계에 따라 성능이 다르게 보일 수 있다.
        - 단일 호스트 Multi-GPU 설계는 PCIe 기반 독립 가속기, NVLink pair, 4-way NVLink domain, dual NVLink domain, HGX NVSwitch fabric 순으로 통신 균일성과 성능 예측 가능성이 높아진다.
            
            
    - **분산 모델이 Multi-GPU를 사용하는 방식**
        - 모델이 여러 GPU를 사용할 때 각 GPU는 모델 weight의 일부를 자기 HBM에 저장한다. Inference 과정에서는 layer와 token 처리를 진행하면서 GPU들이 activation, intermediate tensor, KV cache 일부를 서로 주고받는다.
            
            !image.png
            
        - 이 통신은 단순한 부가 작업이 아니라 모델 실행의 critical path에 들어간다. GPU 간 연결이 느리거나 비대칭이면 전체 collective operation이 느린 경로에 맞춰 지연된다.
        
    - **GPU Interconnect Bandwidth 해석**
        - Multi-GPU 서버에서 주로 등장하는 연결 방식은 PCIe, NVLink, NVSwitch다.
            
            
            | 구성 | Form Factor / Topology | Interconnect | Point-to-Point BW |
            | --- | --- | --- | --- |
            | RTX PRO 6000 | PCIe Gen5 | PCIe | 128 GB/s bidirectional |
            | H100 NVL | PCIe, 2-card bridge | NVLink | 600 GB/s bidirectional |
            | H200 NVL | PCIe, 2-way bridge | NVLink | 900 GB/s bidirectional |
            | H200 NVL | PCIe, 4-way bridge | NVLink | 1.8 TB/s aggregate, 900 GB/s per GPU |
            | HGX H100 | SXM + NVSwitch | NVSwitch | 900 GB/s per GPU to fabric |
            | HGX H200 | SXM + NVSwitch | NVSwitch | 900 GB/s per GPU to fabric |
            | HGX B200 | SXM + NVSwitch | NVSwitch | 1.8 TB/s per GPU to fabric |
        - 주의할 점:
            - PCIe Gen5 x16은 양방향 합산 128 GB/s로 표현되지만, 실제 GPU collective traffic은 CPU, PCIe switch, root complex, NUMA 경계를 지나며 지연이 커질 수 있다.
            - **NVLink bridge의 aggregate bandwidth와 GPU 간 point-to-point bandwidth를 구분**해야 한다.
                
                !mermaid-diagram.png
                
                - 예를 들어 4-GPU NVLink bridge가 1.8 TB/s aggregate라고 해도 각 GPU가 무제한으로 1.8 TB/s를 쓰는 것이 아니라, GPU당 900 GB/s 한계가 있음.
            - NVSwitch는 각 GPU가 fabric에 full NVLink speed로 붙고, switch가 non-blocking 방식으로 GPU 간 통신을 처리하므로 훨씬 균일하다.
            
    - **Multi-GPU Spectrum**
        - 아래 그림은 단일 서버 안에서 가능한 Multi-GPU 연결 구조를 성능/균일성 관점으로 나열한다. 왼쪽의 PCIe 기반 구성은 유연하지만 통신 병목이 크고, 오른쪽의 NVSwitch 기반 HGX 구성은 GPU 간 통신이 가장 균일하다.
            
            !image.png
            
        
    - **4 x RTX PRO 6000: PCIe Connected GPUs *← 상단 그림에서 맨 왼쪽 구성***
        - 4개의 RTX PRO 6000 GPU를 PCIe로 연결한 구조는 GPU 간 직접 링크가 없다. **각 GPU는 host PCIe fabric을 통해 통신**한다.
        - **특징:**
            - 여러 독립 inference service, 서로 다른 모델 serving, GPU 단위 workload 분리에 적합하다.
            - GPU들이 tightly coupled workload를 수행하면 **PCIe fabric이 collective operation의 공유 병목**이 된다.
            - PCIe switch, CPU root complex, NUMA 경계 때문에 통신 경로가 예측 가능하지 않을 수 있다.
            - GPU 수를 늘려 memory와 compute는 늘릴 수 있지만, 분산 모델 scaling은 통신 overhead 때문에 선형으로 증가하지 않을 수 있다.
        - 실무 해석: PCIe Multi-GPU는 flexible starting point지만, 하나의 큰 모델을 여러 GPU로 나눠 실행하는 경우에는 topology-aware placement가 중요해진다.
        
    - **Two NVLink Pairs: 두 개의 NVLink Domain *← 상단 그림에서 왼쪽에서 두번째 구성***
        - 두 GPU가 NVLink bridge로 직접 연결되면 하나의 NVLink domain이 된다. 이 domain 안에서는 GPU 간 통신이 빠르고 안정적이다.
            - *NVLink domain은 GPU들이 NVLink로 직접 연결되어 domain 밖으로 나가지 않고 통신할 수 있는 GPU 그룹*
            
            !image.png
            
        - 4-GPU 서버에서는 H100 계열 PCIe 구성처럼 두 개의 NVLink pair가 만들어질 수 있다. 이 경우 각 pair 내부는 빠르지만, **pair 사이 통신은 PCIe와 CPU socket 경계를 지나야 한다.**
            - *아래 그림 처럼 맨 하단 H100 GPU에서 PCIe Switch - Numa Node 0 ⇒ UPI ⇒ Numa Node 1 → PCIe Switch → H100 경로*
            
            !image.png
            
        - 핵심 개념:
            - NVLink domain은 NVLink로 직접 연결된 GPU 그룹이다.
            - domain 내부에서는 peer memory access와 shared memory model 활용이 가능하지만, 물리적으로 HBM이 하나로 합쳐지는 것은 아니다.
            - **domain 밖으로 나가는 통신은 PCIe 경로를 사용**한다.
            - dual-socket 서버에서는 각 domain이 CPU socket에 매핑되는 경우가 많다.
        - **Cross-domain 통신은 다음 경로를 탈 수 있다 *⇒ two PCIe hops plus a UPI crossing!***
            1. Source GPU에서 PCIe로 나감
            2. PCIe switch 통과
            3. local CPU root complex 도달
            4. UPI를 통해 remote CPU socket으로 이동
            5. remote PCIe switch를 거쳐 destination GPU로 진입
        - 이 과정에서 UPI는 memory coherency, remote memory access, storage I/O, NIC I/O와 공유된다. 따라서 부하가 커지면 두 NVLink island 사이의 UPI 구간이 서버 전체 병목이 될 수 있다.
        - (참고) Intel 서버 CPU 소켓 간(UPI/xGMI) 통신 모니터링 툴 : Intel® Performance Counter Monitor - Github
        
    - **Four GPUs in a Single NVLink Domain *← 상단 그림에서 왼쪽에서 세번째 구성***
        - H200 NVL 같은 구성은 **4개의 GPU를 하나의 NVLink domain**으로 묶을 수 있다. 이 경우 4-GPU 범위 안에서는 내부 경계가 사라지고, distributed model scaling이 더 예측 가능해진다.
            
            !image.png
            
        - 다만 OEM 서버 설계에 따라 NUMA 배치 차이가 생긴다 = trade-off
            - **선택지 A: 4 GPU를 한 Socket 쪽에 몰아 배치**
                - 장점
                    - GPU, host I/O, memory, NVMe, NIC를 한 NUMA node 안에 묶기 쉬움
                    - UPI crossing 최소화
                - 단점 : PCIe lane과 thermal load가 한쪽에 집중된다.
                    - 다른 socket의 PCIe lane 활용이 낮을 수 있음
                    - 한쪽 thermal load 집중
            - **선택지 B: 2+2로 양쪽 Socket에 나눠 배치**
                - 장점
                    - PCIe bandwidth와 냉각 cooling 균형
                - 단점 : host memory/storage/network I/O는 GPU별로 비대칭
                    - GPU-GPU는 NVLink로 빠르더라도 host memory, NIC, NVMe I/O는 비대칭이 될 수 있음
        - 운영 관점에서는 서버 문서와 `nvidia-smi topo -m`으로 실제 배치를 확인해야 한다.
        
    - **Eight GPUs as Two Four-GPU NVLink Domains *← 상단 그림에서 왼쪽에서 네번째 구성***
        - 8-GPU PCIe 기반 H200 구성에서는 보통 4-GPU NVLink domain 두 개로 나뉜다.
            
            !image.png
            
        - **특징:**
            - 각 4-GPU domain 내부 통신은 빠르고 균일하다.
            - **두 domain 사이 통신은 PCIe, CPU socket, UPI 경계를 다시 통과한다.**
            - **하나의 8-GPU distributed model을 실행하면 cross-domain 통신이 병목이 될 수 있다.**
            - 반대로 workload를 두 개의 4-GPU domain에 의도적으로 분리하면 효율적으로 사용할 수 있다.
        - 실무 해석: 8-GPU PCIe 구성은 licensing이나 OEM 선택지 측면에서 매력적일 수 있지만, HGX H200과 같은 균일한 8-GPU fabric으로 보면 안 된다.
        
    - **Four H100 SXM GPUs in a Single NVLink Domain *← 상단 그림에서 오늘쪽에서 두번째 구성***
        - 4-GPU HGX H100 SXM 구성은 **NVSwitch 없이도 4개 GPU가 하나의 NVLink domain을 형성**할 수 있다.
        - 중요한 점:
            - **SXM이라고 해서 항상 NVSwitch가 있는 것은 아니다. *⇒ SXM 소켓을 통해 NVLink로 직접 연결!***
            - HGX 4-GPU는 PCIe 기반 H100의 두 NVLink pair 구조보다 placement가 단순하고 scaling이 안정적이다.
            - H200 NVL의 4-way NVLink domain 등장으로, 일부 PCIe 기반 4-GPU 구성도 작은 HGX 구성과 비슷한 topology 단순성을 제공할 수 있다.
            
    - **HGX with NVSwitch *← 상단 그림에서 맨 오른쪽 구성***
        - 8-GPU HGX 구성은 NVSwitch를 통해 **단일 호스트 내부 GPU fabric**을 만든다. 이 구조는 단순한 **GPU 간** 케이블링이 아니라 **non-blocking switch fabric**이다.
            
            !image.png
            
        - **핵심 특징:**
            - **각 GPU는 NVSwitch에 full NVLink speed로 연결**된다.
            - **어떤 GPU도 다른 GPU와 contention 없이 통신**할 수 있다.
            - H200 HGX 기준 aggregate GPU memory는 1.1 TB 수준으로 fabric 전체에서 접근 가능한 구조가 된다.
            - NVSwitch는 단순 message passing보다 peer memory read/write 같은 memory semantics에 강하다.
            - Mixture-of-Experts처럼 token 단위 routing과 fine-grained data movement가 많은 모델에서 특히 유리하다.
        
    - **NVIDIA Fabric Manager**
        - NVSwitch 기반 HGX에서는 NVIDIA Fabric Manager가 중요 ⇒ NVSwitch memory fabric과 NVLink interconnect를 관리해 multi-GPU 구성을 가능하게 한다!
            
            !mermaid-diagram (1).png.png)
            
        - **역할:**
            - 부팅 시 NVSwitch topology 탐지
            - routing table 구성
            - GPU partition을 OS에 노출
            - 물리적 GPU fabric 위에 logical partition 정의
        - 물리적으로는 NVSwitch가 경계를 줄이지만, Fabric Manager는 플랫폼 정책에 맞춰 논리적 GPU partition을 구성한다. 8-GPU 시스템에서는 기본적으로 4-GPU partition 두 개가 만들어지는 경우가 많다. 이 partition은 VM이나 workload가 topology에 맞춰 GPU를 묶어 쓰도록 하는 기준이 된다.
        
    - **설계 시사점**
        - Multi-GPU 서버를 고를 때 GPU 개수만 보면 안 되고, GPU 간 topology(=GPU 그룹) 를 먼저 확인해야 한다.
            
            ```bash
            8 GPU 서버
            = 항상 8 GPU 단일 fabric이 아님
            
            8 GPU 서버
            = 4 GPU domain 2개일 수도 있음
            = 8 GPU NVSwitch fabric일 수도 있음
            ```
            
        - 모델 parallelism 방식에 맞춰 topology를 고른다
            
            ```bash
            Data Parallel:
            GPU 간 통신 빈도 상대적으로 낮음
            PCIe도 가능할 수 있음
            
            Tensor Parallel:
            layer마다 activation 교환
            빠르고 균일한 GPU 간 링크 필요
            
            Pipeline Parallel:
            stage 간 통신 경로 중요
            stage placement가 topology와 맞아야 함
            
            MoE:
            token routing이 자주 발생
            NVSwitch 같은 균일 fabric이 유리
            ```
            
            - PCIe-only 구성은 독립 workload 여러 개를 돌릴 때 유리하지만, tightly coupled distributed model에는 통신 overhead가 크다.
            - 2-GPU NVLink pair는 pair 내부 workload에는 좋지만, 4-GPU 이상에서 domain 경계가 생기면 scaling efficiency가 낮아질 수 있다.
            - 4-way NVLink domain은 4-GPU 단위 모델 실행에 좋은 기준점이다.
        - 8-GPU PCIe 서버는 보통 두 개의 4-GPU island로 이해하는 편이 안전하다.
        - HGX + NVSwitch는 8-GPU 전체를 균일한 fabric으로 다루는 데 가장 적합하다.
        - VM 배치, device group, scheduler 정책은 `nvidia-smi topo -m`, NVLink domain, NUMA locality, Fabric Manager partition을 기준으로 topology-aware하게 설계해야 한다.
            - NUMA와 I/O도 같이 본다 : GPU-GPU 통신만 보면 부족!
                
                ```bash
                # 모두 topology 영향을 받습니다.
                GPU ↔ GPU
                GPU ↔ CPU memory
                GPU ↔ NIC/EFA/RDMA
                GPU ↔ NVMe/storage
                ```
                
        
    - **운영 체크리스트**
        - `nvidia-smi topo -m`으로 GPU-GPU, GPU-NIC, GPU-CPU socket 관계를 확인한다.
        - GPU 간 연결이 `NV#`, `PIX`, `PXB`, `PHB`, `NODE`, `SYS` 중 무엇으로 표시되는지 해석한다.
        - 분산 모델이 하나의 NVLink domain 안에 들어가는지 확인한다.
        - Cross-domain 또는 cross-socket 통신이 필요한 경우 UPI 병목 가능성을 고려한다.
        - GPU와 NIC/NVMe가 같은 NUMA domain에 있는지 확인한다.
        - HGX/NVSwitch 환경에서는 Fabric Manager 상태와 partition 구성을 확인한다.
        - VM 또는 container 배치 시 topology boundary를 넘지 않도록 device group을 설계한다.
        
    - **핵심 용어**
        - **NVLink domain**: NVLink로 직접 연결되어 빠른 peer-to-peer 통신이 가능한 GPU 그룹.
        - **NVSwitch**: 여러 GPU를 non-blocking 방식으로 연결하는 NVIDIA GPU fabric switch.
        - **PCIe root complex**: CPU와 PCIe 장치 사이의 연결 루트. GPU가 어느 CPU socket에 붙는지 결정한다.
        - **NUMA locality**: CPU, memory, PCIe device가 어느 socket에 가까운지에 따른 접근 비용 차이.
        - **UPI**: Intel dual-socket 서버에서 CPU socket 사이를 연결하는 링크. Cross-socket GPU/I/O 통신의 공유 병목이 될 수 있다.
        - **Fabric Manager**: NVSwitch topology와 routing, GPU partition을 관리하는 NVIDIA driver stack 구성요소.
        - **Collective operation**: 여러 GPU가 동시에 참여하는 통신 연산. 가장 느린 경로가 전체 지연을 결정하기 쉽다.