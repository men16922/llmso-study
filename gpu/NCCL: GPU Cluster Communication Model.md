### Intro

- 이 장의 초점은 훈련 작업을 시작하는 데 필요한 것이 무엇인지 설명하고 작업 중에 어떤 일이 일어나는지 개요를 제공하는 것입니다. 그런 의미에서 이 장은 "AI DC에서의 딥 러닝 여정"의 일종의 마무리 장입니다. 그림 14-1은 각각 **4개의 GPU와 외부 네트워크 연결이 있는 두 GPU 호스트**의 고수준이지만 단순화된 아키텍처와 주요 구성 요소를 보여줍니다. 두 호스트는 동일한 훈련 클러스터의 일부입니다. 이 예제의 전제 조건으로 다음 소프트웨어 패키지가 두 호스트에 모두 설치되어 있습니다:
    
    !ChatGPT Image 2026년 6월 27일 오전 12_33_28.png
    
- **PyTorch with CUDA and NCCL Support**: PyTorch는 데이터 로딩, 모델 정의, 병렬 실행, 그래디언트 동기화 등 전체 학습 워크플로우를 관리하는 딥러닝 프레임워크입니다. 레이어 수, 레이어당 뉴런 수, 활성화 함수 등 신경망의 구조를 정의하고 가중치를 자동으로 초기화합니다.
- **'CUDA** (Comput Unified Device Architecture): CUDA는 NVIDIA의 병렬 컴퓨팅 플랫폼이자 API 모델입니다. PyTorch는 CPU 메모리(DRAM)에서 GPU 메모리(VRAM)로 이동하는 데이터의 메모리 할당에 CUDA를 사용합니다. 여기에는 배치 텐서, 모델 가중치, 그리고 순방향/역방향 패스 동안의 중간 변수가 포함됩니다. 순방향 패스에서 CUDA는 행렬 곱셈을 수행하고, 활성화 함수(예: ReLU, Tanh, Sigmoid)를 사용하여 뉴런 출력 값 y를 계산하며, 모델 오류를 계산합니다. CUDA는 또한 역방향 패스를 처리하여 가중치 업데이트에 필요한 그래디언트를 계산하고 로컬 가중치를 업데이트합니다
- '**NCCL**(NVIDIA Collective Communication Library): NCCL은 GPU 간의 고성능 데이터 교환을 위해 설계된 다중 GPU, 토폴로지 인식 집단 알고리즘입니다. 이 알고리즘은 GPU 간에 계산된 그래디언트가 교환되는 훈련의 그래디언트 통신 단계에서 사용됩니다. 예를 들어, CUDA가 각 GPU에서 그래디언트를 계산한 후, NCCL은 집단 통신 연산을 사용하여 해당 그래디언트를 다른 GPU로 전송합니다. 작성 시점에서 NCCL은 다음 연산을 지원합니다: AllReduce, Broadcast, Reduce, AllGather, 그리고 ReductSatter
- PyTorch, CUDA, NCCL 프로세스 및 종속성에 대해서는 다음 섹션에서 자세히 설명합니다.
- 원문
    - ‘The focus of this chapter is to describe what is needed to start a training job and give an overview what happens during the job. In that sense, this is a kind of closing chapter for our “Deep Learning in AI DC journey”. Figure 14-1 shows a high-level, yet simplified architecture and the main building blocks of two GPU hosts, each with four GPUs and their external network connections. Both hosts are part of the same training cluster. As a prerequisite in our example, the following software packages are installed on both hosts:
    - PyTorch with CUDA and NCCL Support: PyTorch is a deep learning framework that manages the entire training workflow, including data loading, model definition, parallel execution, and gradient synchronization. It defines the structure of the neural network, such as the number of layers, neurons per layer, activation functions, and initializes the weights automatically.
    - ‘CUDA (Compute Unified Device Architecture): CUDA is a parallel computing platform and API model from NVIDIA. PyTorch uses CUDA for memory allocation for the data you move from CPU memory (DRAM) to GPU memory (VRAM), including batch tensors, model weights, and intermediate variables during the forward/backward passes. In the forward pass, CUDA does matrix multiplication, computes neuron output values y using the activation functions (e.g., ReLU, Tanh, Sigmoid) and computes the model error. CUDA also handles the backward pass, where it calculates gradients needed for weight updates and updates local weights.’
    - ‘NCCL (NVIDIA Collective Communication Library): NCCL is a multiGPU, topology-aware collective algorithm designed for high-performance data exchange between GPUs, especially in multi-GPU and multi-node systems. It is used during the gradient communication phase of training, where computed gradients are exchanged between GPUs. For example, after CUDA computes gradients on each GPU, NCCL transfers those gradients to other GPUs using collective communication operations. At the time of writing, NCCL supports the following operations: AllReduce, Broadcast, Reduce, AllGather, and ReduceScatter.’
    - PyTorch, CUDA, and NCCL processes and dependencies are explained detail in upcoming section.

### 훈련 클러스터에서 GPU를 위한 NCCL 고유 ID 배포하기: Distributing NCCL Unique Id for GPUs in a Training Cluster

- '여러 노드의 GPU가 분산 학습 중에 효율적으로 통신하기 전에 먼저 누가 참여하고 데이터를 어떻게 교환할지를 정의하는 공유 컨텍스트인 커뮤니케이터에 동의해야 합니다. 이를 활성화하려면 NVIDIA 집단 통신 라이브러리(NCCL)에 **NCCL Unique ID**라는 특수 식별자가 필요합니다. 이 ID는 지정된 마스터 프로세스에 의해 **한 번 생성된 후 학습 작업의 다른 모든 프로세스와 공유**됩니다. 이 ID는 세션 식별자 역할을 하여 **모든 참여 GPU 프로세스가 동일한 통신 그룹에 가입하도록 보장합**니다. 이 ID가 없으면 AllReduce 또는 Broadcast와 같은 작업에 사용되는 링이나 트리와 같은 통신 토폴로지를 구축하는 데 공통 기준점이 없습니다. 본질적으로 NCCL 고유 ID는 조정된 초기화를 가능하게 하고 분산 GPU 환경에서 집단 통신을 가능하게 합니다. NCCL 고유 ID는 TCP 연결을 통해 분산됩니다. 다음 두 섹션에서는 이 프로세스를 설명합니다
- ‘Before GPUs across multiple nodes can communicate efficiently during distributed training, they must first agree on a shared context, a communicator, that defines who is participating and how data will be exchanged. To enable this, the NVIDIA Collective Communications Library (NCCL) requires a special identifier known as the NCCL Unique ID. This ID is generated once by a designated master process and then shared with all other processes in the training job. It acts as a session identifier, ensuring that every participating GPU process joins the same communication group. Without it, there would be no common reference point for building the communication topologies (such as rings or trees) used in operations like AllReduce or Broadcast. In essence, the NCCL Unique ID enables coordinated initialization and makes collective communication possible in a distributed GPU environment. The NCCL Unique ID is distributed over TCP connection. The following two section describes the process.’

### 마스터 노드에 TCP 소켓 열기: Opening TCP Socket to Master Node

- 훈련 작업이 그림 14-2에 표시된 토치런 명령을 사용하여 시작되면 PyTorch의 분산 프레임워크는 각 노드에서 GPU당 하나의 프로세스를 시작합니다. 이러한 프로세스는 나중에 글로벌 랭크 ID로 식별됩니다. 일반적으로 **랭크 ID가 0인 프로세스에 마스터 역할**이 할당되므로 NCCL 고유 ID를 생성하고 다른 **모든 프로세스(즉, 다른 GPU에서 실행되는 랭크)에 배포**합니다.
When the training job is launched using the torchrun command shown in Figure 14-2, PyTorch’s distributed framework starts one process per GPU on each node. These processes are later identified by their global rank ID. Typically, the process with rank ID 0 is assigned the master role, which means it creates and distributes the NCCL Unique ID to all other processes (i.e., ranks running on other GPUs).
    
    !Figure 14-2: Opening TCP Socket with the Master Rank
    
    Figure 14-2: Opening TCP Socket with the Master Rank
    
- 글로벌 랭크 ID는 `--node_rank=n` 변수에 `--nproc_per_node=4` 값(노드당 processes)을 곱한 다음 **로컬 GPU 랭크를 더하여 계산**됩니다. 그 결과 다음과 같은 **글로벌 랭크 ID가 생성**됩니다:
The global rank IDs are calculated by multiplying the `--node_rank=n` variable with the `--nproc_per_node=4` value (processes per node) and then adding the local GPU rank. This results in the following global rank IDs:
    
    ```bash
    Host A: GPU 0 - Rank ID: 0 * 4 + 0 = 0
    Host A: GPU 1 - Rank ID: 0 * 4 + 1 = 1
    Host A: GPU 2 - Rank ID: 0 * 4 + 2 = 2
    Host A: GPU 3 - Rank ID: 0 * 4 + 3 = 3
    
    Host B: GPU 0 - Rank ID: 1 * 4 + 0 = 4
    Host B: GPU 1 - Rank ID: 1 * 4 + 1 = 5
    Host B: GPU 2 - Rank ID: 1 * 4 + 2 = 6
    Host B: GPU 3 - Rank ID: 1 * 4 + 3 = 7
    ```
    
- 호스트 A의 GPU 0(노드 랭크 0)은 글로벌 랭크 ID 0을 가지므로 마스터 랭크가 됩니다. PyTorch는 `--master_addr=192.168.10.101` 및 `--master_port=12345` 값을 사용하여 이 GPU에서 192.168.10.101:12345에 TCP 리스너를 엽니다. 스크립트 매개변수 `--node=2`는 클러스터에 두 개의 노드가 있음을 지정하고, `--nproc_per_node=4`는 각 노드에서 네 개의 프로세스(GPU당 하나)가 실행되고 있음을 나타냅니다. 이 정보를 바탕으로 **마스터 랭크는 랭크 1에서 7까지 7개의 연결 요청**을 예상합니다.
Since GPU 0 on Host A (node rank 0) has the global rank ID 0, it becomes the master rank. PyTorch opens a TCP listener on this GPU at 192.168.10.101:12345, using the values of `--master_addr=192.168.10.101` and `--master_port=12345`. The script parameter `--nnodes=2` specifies that there are two nodes in the cluster, and `--nproc_per_node=4` indicates that four processes (one per GPU) are running on each node. Armed with this information, the master rank expects 7 connection requests (from ranks 1 through 7).
- 다른 모든 랭크는 마스터 프로세스와 함께 TCP 소켓을 열기 위한 3방향 핸드셰이크 프로세스를 시작합니다. 호스트 B의 랭크 4-7은 '`--master_addr = 192.168.10.101`'을 대상 IP 주소로 사용하는 반면, 로컬 랭크 1-3은 루프백 IP 주소 127.0.0.1을 사용합니다. 모든 랭크는 '`--master_port=12345`'를 대상 TCP 포트로 사용합니다.
All other ranks start a three-way handshake process for opening TCP socket with the master process. The ranks 4-7 on the host B use `--master_addr = 192.168.10.101` as a destination IP address, while local ranks 1-3 use the loopback IP address 127.0.0.1. All ranks use the `--master_port=12345` as destination TCP port.
- 이 연결 단계는 마스터가 NCCL 고유 ID를 배포하여 GPU가 집단 작업을 위한 통신 토폴로지를 형성할 수 있도록 하는 랑데부 프로세스를 가능하게 합니다.
This connection phase enables a rendezvous process, during which the master distributes the NCCL Unique ID so that GPUs can form a communication topology for collective operations.
- 레이어 3 멀티캐스트 네트워킹에서 NCCL 랑데부 프로세스와 랑데부 포인트(RP) 사이에는 느슨하지만 유용한 유사점이 있습니다. 두 경우 모두 랑데부는 조정 메커니즘으로 작용합니다. **NCCL 랑데부 프로세스는 마스터 프로세스에서 분산 학습에 참여하는 모든 GPU 프로세스에 고유한 NCCL 식별자를 배포합니다**. 마찬가지로 멀티캐스트 RP는 송신자로부터 여러 수신자에게 데이터 프레임을 배포하는 공유 포인트 역할을 합니다.
There is a loose but useful analogy between the NCCL rendezvous process and the Rendezvous Point (RP) in Layer 3 multicast networking. In both cases, the rendezvous acts as a coordination mechanism. The **NCCL rendezvous process distributes a unique NCCL identifier from a master process to all GPU processes participating in distributed training**. Similarly, a multicast RP serves as a shared point which distributes the data frames from the sender to multiple receivers.
    
    

### 기존 TCP 소켓을 통한 NCCL 고유 ID 배포: Distributing the NCCL Unique ID Over Established TCP Sockets

- 모든 랭크가 마스터 프로세스(랭크 ID 0)와 **TCP 연결**을 설정하면 다음 단계는 **NCCL 고유 ID를 배포**하는 것입니다. **마스터 프로세스**는 이 식별자를 생성하여 이미 설정된 TCP 연결을 사용하여 **다른 모든 랭크(1~7)로 보냅**니다.
Once all ranks have established TCP connections with the master process (rank ID 0), the next step is to distribute the NCCL Unique ID. The master process generates this identifier and sends it to all other ranks (1 through 7) using the already established TCP connections.
    
    !Figure 14-3: Redistribution NCCL unique Id over TCP Socket.
    
    Figure 14-3: Redistribution NCCL unique Id over TCP Socket.
    
    !ChatGPT Image 2026년 6월 27일 오전 01_07_45.png
    
- 이러한 연결은 일반적으로 클러스터 구성에 따라 프론트엔드 또는 관리 네트워크를 통해 실행됩니다. 그림 14-3은 마스터 프로세스의 관점에서 연결 상태를 보여줍니다.
These connections typically run over the frontend or management network, depending on the cluster configuration. Figure 14-3 illustrates the state of the connections from the perspective of the master process.
- NCCL 고유 ID는 작업의 네임스페이스 식별자 역할을 하여 동일한 훈련 작업에 속하는 프로세스만 동일한 통신 그룹에 참여할 수 있도록 합니다. 이는 여러 분산 작업이 동일한 노드 집합에서 동시에 실행될 수 있는 환경에서 특히 중요합니다. 고유 ID는 작업을 서로 분리하고 관련 없는 프로세스 간의 교차 대화를 방지합니다. 그런 다음 모든 랭크는 이 고유 ID를 사용하여 로컬 NCCL 통신기를 초기화하여 동일한 통신 그룹에 가입하도록 합니다. 이 배포 단계는 매우 중요합니다: **NCCL 고유 ID는 부트스트랩 메커니즘으로 작용하여 모든 GPU 프로세스가 동일한 통신 그룹에 가입하고 올-리듀스 및 브로드캐스트와 같은 집단 작업에 참여할 수 있도록 합**니다.
The NCCL Unique ID serves as a namespace identifier for the job, ensuring that only processes belonging to the same training job can participate in the same communication group. This is particularly important in environments where multiple distributed jobs may be running concurrently on the same set of nodes. The unique ID isolates jobs from each other and prevents cross-talk between unrelated processes. All ranks then use this unique ID to initialize their local NCCL communicators, ensuring they join the same communication group. This distribution phase is critical: the NCCL Unique ID acts as a bootstrap mechanism, allowing all GPU processes to join the same communication group and participate in collective operations like all-reduce and broadcast.

### NCCL 브로드캐스트 집합 및 모델 매개변수 동기화: NCCL Broadcast Collective and Model Parameter Synchronization

- 이 시점에서 **각 프로세스에는 이미 모델의 로컬 복사본**이 있으며 **모든 GPU는 동기화된 학습을 시작할 준비**가 되었습니다. **첫 번째 단계는 모든 GPU가 동일한 모델 매개변수로 시작**하도록 하는 것입니다. **NCCL은 선택한 통신 토폴로지를 사용하여 이를 자동으로 처리**합니다.
At this point, each process already has a local copy of the model, and all GPUs are ready to begin synchronized training. The first step is to ensure that every GPU starts with identical model parameters. NCCL handles this automatically, using the chosen communication topology.
    
    !Figure 14-4: 마스터 랭크 0에 따른 모델 매개변수 분포. Model Parameters Distribution by Master Rank 0.
    
    Figure 14-4: 마스터 랭크 0에 따른 모델 매개변수 분포. Model Parameters Distribution by Master Rank 0.
    
- 마스터 프로세스(랭크 0, 호스트 A의 GPU 0에서 실행됨)가 **TCP 소켓**을 통해 **NCCL 고유 ID를 다른 모든 프로세스와 공유**한 후, **NCCL 라이브러리**는 **트리 토폴로지를 구축**합니다. 이 토폴로지는 **Broadcast 집합체**를 사용하여 **모델 매개변수를 다른 모든 GPU로 전송**하는 데 사용됩니다. 그림 14-4는 호스트 A의 GPU 0에서 실행되는 **마스터 프로세스**가 **모델 매개변수를 다른 모든 프로세스에 분배하는 방법**을 보여줍니다. 글로벌 랭크 ID가 1-3인 GPU는 마스터 프로세스와 동일한 호스트에 있으므로 NCCL은 **고속 NVLink**를 통해 **직접 메모리 복사**를 사용합니다. 이러한 전송은 CPU나 운영 체제 없이 이루어지며, 큐 쌍이 필요하지 않아 노드 내 통신이 매우 빠르고 효율적입니다.
After the master process (rank 0, running on GPU 0 of Host A) shares the NCCL Unique ID with all other processes over TCP sockets, the NCCL library builds a tree topology. This topology is used for sending model parameters to all other GPUs using the Broadcast collective. Figure 14-4 illustrates how the master process, running on GPU 0 of Host A, distributes its model parameters to all other processes. GPUs with global rank IDs 1-3 are on the same host as the master process, so NCCL uses direct memory copy over high-speed NVLink. These transfers happen without involving the CPU or operating system, and no Queue Pairs are needed, making intra-node communication extremely fast and efficient.
- GPU가 **서로 다른 호스트**에 위치한 경우, NCCL은 마스터 프로세스와 원격 프로세스 간에 빠르고 직접적인 데이터 경로를 생성하기 위해 **대기열 쌍**(QP)을 설정합니다. 이러한 연결은 백엔드 네트워크를 사용하는데, 이 네트워크는 예시에서 라우팅된 레이어 3 클로즈 패브릭(네트워크 레이아웃은 단순화를 위해 제외)입니다.
If GPUs are located on different hosts, NCCL sets up Queue Pairs (QPs) to create fast, direct data paths between the master process and remote processes. These connections use the backend network, which in our example is a routed Layer 3 Clos Fabric (the network layout is excluded for simplicity).

### AllReduce 집합체를 사용한 그라디언트 동기화: Gradient Synchronization Using AllReduce Collective

- 모델 매개변수를 동기화한 후, **순방향 패스의 첫 번째 iteration**은 **클러스터의 모든 GPU에서 동시에 시작**됩니다. 순방향 패스 동안 GPU별 **mini-batches**는 **각 레이어에서 행렬 곱셈**을 수행한 다음 **활성화 함수 연산**을 수행하여 **모델의 모든 레이어에서 처리**됩니다. **모델 출력 y를 계산**한 후 각 GPU는 **역방향 패스**를 시작합니다. **마지막 레이어에 1024개의 매개변수**가 있고 각 **GPU가 모든 1024개의 매개변수에 대해 기울기를 계산**한다고 가정해 보겠습니다. 이러한 기울기는 **버킷이라는 예약된 메모리 영역에 저장**됩니다.
After synchronizing model parameters, the first iteration of the forward pass begins simultaneously on all GPUs in the cluster. During the forward pass, GPU-specific mini-batches are processed through all layers of the model by performing matrix multiplications followed by activation function operations at each layer. After computing the model output y, each GPU starts the backward pass. Let’s assume the last layer has 1024 parameters and each GPU computes gradients for all 1024 parameters. These gradients are stored in a reserved memory region called a bucket.
    - *GPU 훈련에서 **Iteration**은 쉽게 말해 **“미니 배치 하나를 GPU에 넣고, forward → loss 계산 → backward → weight 업데이트까지 한 번 수행하는 단위” ⇒** 즉, **Iteration은 모델이 한 번 배우는 작은 걸음**입니다.*
        
        ```bash
        Iteration 1회 =
        데이터 일부, 즉 mini-batch 1개를 읽음
        → GPU에서 예측 계산 : Forward - 입력 데이터를 모델에 넣고 결과를 계산
        → 정답과 비교해서 loss 계산
        → gradient 계산 : Backward - loss를 기준으로 각 weight가 얼마나 잘못됐는지 gradient 계산
        → 모델 weight 업데이트
        ```
        
- 다음으로, 각 GPU는 **버킷을 네 개의 청크**로 나눕니다. 각 청크에는 **256개의 그래디언트**가 포함되어 있습니다(1024개의 매개변수 / 4개의 GPU = 256개의 그래디언트가 포함되어 있기 때문입니다). 이 시점에서 각 GPU는 256개의 그래디언트를 가진 **A-D라는 라벨이 붙은 네 개의 청크**를 가지고 있습니다. **단방향 링 토폴로지에서 AllReduce 집합체**를 사용할 때, 이 연산은 **ReduceScatter로 구현되며 AllGather**가 그 뒤를 잇습니다.
Next, each GPU divides its bucket into four chunks, each containing 256 gradients (since 1024 parameters / 4 GPUs = 256 gradients per chunk). At this point, every GPU has four chunks labeled A–D, each with 256 gradients. When using the AllReduce collective in a unidirectional ring topology, the operation is implemented as ReduceScatter followed by AllGather.
    - *gradient(그래디언트): 모델 학습에서 가중치를 얼마나 조정할지 알려주는 값*
- 그림 14-5에 나와 있는 예시에서, 우리는 **두 개의 노드**(호스트 A와 호스트 B)를 가지고 있으며, 각각은 **네 개의 GPU**를 가지고 있습니다. 모든 GPU는 **1024개의 그래디언트를 모두 계산**하여 **VRAM에서 네 개의 로컬 청크**(A–D)로 구성했습니다. 이 예시에서 **GPU 0**(글로벌 랭크 0에서는 앞으로 글로벌 랭크를 사용할 것입니다)은 **청크 A의 평균화**를 담당하고, **청크 B의 랭크 1**(블루 GPU 1), **청크 C의 랭크 2**(그린 GPU 0), **청크 D의 랭크 3**(옐로우 GPU 1)을 **담당**합니다. 노드 내 GPU 연결은 **고속 NVLink**를 사용하며, 노드 간 연결은 **RoCEV2**를 사용합니다.
In our example, shown in figure 14-5, we have two nodes (Host A and Host B), each with four GPUs. Every GPU has computed all 1024 gradients and organized them into four local chunks (A–D) in VRAM. In this example, GPU 0 (with global rank 0, we’ll use global ranks from now on) is responsible for averaging chunk A, rank 1 (Blue GPU 1) for chunk B, rank 2 (Green GPU 0) for chunk C, and Rank 3 (Yellow GPU 1) for chunk D. Intra-node GPU connections use high-speed NVLink, while inter-node connections use RoCEv2.
    
    !Figure 14-5: 링 토폴로지의 AllReduce와 ReduceScatter 및 AllReduce 연산을 사용합니다. AllReduce in Ring Topology with ReduceScatter and AllReduce Operations.
    
    Figure 14-5: 링 토폴로지의 AllReduce와 ReduceScatter 및 AllReduce 연산을 사용합니다. AllReduce in Ring Topology with ReduceScatter and AllReduce Operations.
    

### ReduceScatter: First Iteration

- 그림 14-6에서 그림 14-5의 **링 토폴로지**는 여전히 사용 중이지만, GPU는 **AllReduce 데이터 흐름**을 더 쉽게 **시각화**할 수 있도록 **선형 시퀀스로 배치**되어 있습니다.
In Figure 14-6, the ring topology from Figure 14-5 is still in use, but the GPUs are laid out in a linear sequence for easier visualization of the AllReduce data flow.
    
    !Figure 14-6: ReduceScatter: The First Iteration
    
    Figure 14-6: ReduceScatter: The First Iteration
    
    !GPU 간 화살표 위치는 원본 사진 참고
    
    GPU 간 화살표 위치는 원본 사진 참고
    
- AllReduce 연산의 **ReduceScatter 단계**에서 각 **랭크**는 **자신이 담당하는 청크를 링의 다음 랭크로 보냅**니다:
During the ReduceScatter phase of the AllReduce operation, each rank sends the chunk it is responsible for to the next rank in the ring:
    
    ```bash
     Rank 0 sends chunk A0 to Rank 1
     Rank 1 sends chunk B1 to Rank 2
     Rank 2 sends chunk C2 to Rank 3
     Rank 3 sends chunk D3 to Rank 0
    ```
    
- 이러한 각 청크에는 매개변수 공간의 특정 부분에 대한 **그래디언트가 포함**되어 있으며, 각 랭크는 데이터가 **링 주위를 순환**할 때 모든 GPU에서 해당 부분을 줄이는(즉, 합산) 역할을 합니다.
Each of these chunks contains gradients for a specific portion of the parameter space, and each rank is responsible for reducing (i.e., summing) that portion across all GPUs as data circulates around the ring.

- 그림 14-7은 ReductScatter 단계에서 **첫 번째 send iteration** 후 **그래디언트 동기화 상태**를 보여줍니다. 이 시점에**서 각 GPU는 할당된 청크를 링 토폴로지의 다음 GPU로 전송**했으며, **인접 GPU로부터도 하나의 청크를 받았**습니다:
Figure 14-7 shows the status of gradient synchronization after the first send iteration in the ReduceScatter phase. At this point, each GPU has sent its assigned chunk to the next GPU in the ring topology and has also received one chunk from its neighbor:
    
    !Figure 14-7: 분산 감소: 첫 번째 반복 후의 덩어리. ReduceScatter: Chunks After the First Iteration.
    
    Figure 14-7: 분산 감소: 첫 번째 반복 후의 덩어리. ReduceScatter: Chunks After the First Iteration.
    
    ```
    Rank 0 has received chunk D3 from rank 3
    Rank 0 has received chunk D3 from rank 3
    Rank 0 has received chunk D3 from rank 3
    Rank 0 has received chunk D3 from rank 3
    ```
    
- 이 첫 번째 전송(ReduceScatter 단계의 iteration 1) 후에도 각 GPU는 여전히 로컬 메모리에 세 개의 원본 청크와 하나의 부분적으로 축소된 청크를 보유합니다. 각 GPU는 수신된 청크를 동일한 청크의 로컬 버전에 추가합니다. 예를 들어, 랭크 0은 청크 D3를 D0에 추가합니다(**chunk D = D0 + D3)**.
After this first send (iteration 1 of the ReduceScatter phase), each GPU still holds three original chunks in local memory, plus one partially reduced chunk. Each GPU adds the received chunk to its local version of the same chunk. For example, rank 0 adds chunk D3 to D0 (chunk D = D0 + D3).
- 이것은 첫 번째 **부분 축소 partial reduction**일 뿐입니다. 할당된 청크에 대한 완전한 축소를 완료하려면 **각 GPU가 다음 세 번의 반복**에 걸쳐 나머지 **GPU로부터 해당 청크를 수신하고 합산**해야 합니다. ReductScatter 단계가 끝날 때(4-GPU 링에서 세 번의 반복 후), **각 GPU**는 원래 소유했던 청크가 아니더라도 **정확히 하나의 완전 축소 청크를 보유**하게 됩니다.
This is only the first partial reduction. To complete the full reduction for its assigned chunk, each GPU must receive and sum the corresponding chunks from the remaining GPUs over the next three iterations. By the end of the ReduceScatter phase (after three iterations in a 4-GPU ring), each GPU holds exactly one fully reduced chunk, though not necessarily the one it originally owned.

### ReduceScatter: Second Iteration

- 그림 14-8은 ReductScatter 단계의 두 번째 반복을 보여줍니다: The figure 14-8 shows the second iteration of the ReduceScatter phase:
    
    !ChatGPT Image 2026년 6월 27일 오전 02_06_35 (2).png.png)
    
    ```
    Rank 0 sends the partially averaged chunk D (Sum of D3 + D0) to Rank 1.
    Rank 1 sends the partially averaged chunk A (Sum of A0 + A1) to Rank 2.
    Rank 2 sends the partially averaged chunk B (Sum of B1 + B2) to Rank 3.
    Rank 3 sends the partially averaged chunk C (Sum of C2 + C3) to Rank 0.
    ```
    
- 두 번째 ReduceScatter 반복 후, 각 랭크는 이제 유지됩니다: After the second ReduceScatter iteration, each rank now holds:
    - 부분적으로 두 번 축소된 하나의 청크(로컬 청크 + 원격 청크 두 개)
    One chunk that has been partially reduced twice (local chunk + two remote chunks)
    - 아직 어떤 의사소통에도 관여하지 않은 두 개의 원본 청크 Two original chunks that have not yet been involved in any communication
    - 이 반복 중에 전송된 하나의 청크 One chunk that was sent out during this iteration
    
- 랭크별 구체적인 상태는 다음과 같습니다 Here’s the specific status per rank:
    
    !Figure 14-9: ReduceScatter: Chunks After the Second Iteration
    
    Figure 14-9: ReduceScatter: Chunks After the Second Iteration
    
    !각 GPU 별 청크에 색은 1개씩만 채워져 있음. 위 그림 오타..png)
    
    각 GPU 별 청크에 색은 1개씩만 채워져 있음. 위 그림 오타.
    
    - Rank 0:
        - 부분적으로 축소된 청크 C = C2 + C3 + C0을 보유합니다(랭크 3에서 방금 받아 로컬 C0에 추가됨)
        Holds partially reduced chunk C = C2 + C3 + C0 (just received from Rank 3 and added to local C0)
        - 여전히 원본 청크 A0와 B0가 있습니다 Still has original chunks A0 and B0
        - 전송된 청크 D = D3 + D0 Sent out chunk D = D3 + D0
    - Rank 1:
        - Holds partially reduced chunk D = D3 + D0 + D1
        - Still has original chunks B1 and C1
        - Sent out chunk A = A0 + A1
    - Rank 2:
        - Holds partially reduced chunk A = A0 + A1 + A2
        - Still has original chunks C2 and D2
        - Sent out chunk B = B1 + B2
    - Rank 3:
        - Holds partially reduced chunk B = B1 + B2 + B3
        - Still has original chunks A3 and D3
        - Sent out chunk C = C2 + C3
    

### ReduceScatter: Third Iteration

- 그림 14-10은 ReductScatter 단계의 세 번째 반복을 보여줍니다 The figure 14-10 shows the third iteration of the ReduceScatter phase:
    
    !ChatGPT Image 2026년 6월 27일 오전 02_23_49 (2).png.png)
    
    ```bash
    Rank 0 sends the partially averaged chunk C (Sum of C2 + C3+ C0) to Rank 1.
    Rank 1 sends the partially averaged chunk D (Sum of D3 + D0+ D1) to Rank 2.
    Rank 2 sends the partially averaged chunk A (Sum of A0 + A1+ A2) to Rank 3.
    Rank 3 sends the partially averaged chunk B (Sum of B1 + B2+ B3) to Rank 0.
    ```
    
- 세 번째 ReduceScatter 반복 후, ReduceScatter 단계가 완료됩니다. 이제 각 랭크는 **네 개의 GPU로부터의 기여를 포함한 하나의 완전히 축소된 청크를 보유**하게 됩니다. 그러나 이러한 완전히 축소된 청크는 원래 소유자 랭크에 위치하지 않습니다. 각 랭크는 최종 청크를 하나 받고 로컬 복사본과 합산하여 축소를 완료합니다. 이 시점에서:
After the third ReduceScatter iteration, the ReduceScatter phase is complete. Each rank now holds one fully reduced chunk, which includes contributions from all four GPUs. However, these fully reduced chunks are not located on their original owner ranks. Each rank receives one final chunk and completes its reduction by summing it with its local copy. At this point:
    
    !ChatGPT Image 2026년 6월 27일 오전 02_23_49 (1).png.png)
    
    ```bash
    Rank 0 holds fully reduced chunk B = B1 + B2 + B3 + B0
    Rank 1 holds fully reduced chunk C = C2 + C3 + C0 + C1
    Rank 2 holds fully reduced chunk D = D3 + D0 + D1 + D2
    Rank 3 holds fully reduced chunk A = A0 + A1 + A2 + A3
    ```
    
- **ReduceScatter 연산**은 **Ring AllReduce 프로세스의 첫 번째 단계**로, 분산 학습 설정에서 **모든 GPU에 걸쳐 그래디언트 데이터를 집계하는 역할**을 합니다. 이 연산의 목표는 각 그래디언트의 합(또는 평균)을 계산하는 것입니다. ReduceScatter 단계가 끝나면:
The ReduceScatter operation is the first step in the Ring AllReduce process and is responsible for aggregating gradient data across all GPUs in a distributed training setup. Its goal is to compute the sum (or average) of each gradient. At the end of the ReduceScatter phase:
    - 각 GPU는 완전히 축소된 하나의 청크를 보유하고 있으며, 이는 네 개의 GPU 모두의 기여를 포함합니다.
    Each GPU holds one fully reduced chunk, which includes contributions from all four GPUs.
    - 축소된 청크는 현재 보유하고 있는 GPU에 반드시 국한된 것은 아니며, 다른 랭크에 의해 소유되고 있습니다.
    The reduced chunk is not necessarily local to the GPU that now holds it, it’s owned by a different rank.

### AllGather: The first Iteration

- 이제 ReduceScatter 단계가 완료되었으므로 **AllGather 단계가 시작**됩니다. 이 단계의 역할은 **완전히 축소된 청크**를 **모든 GPU에 다시 배포**하여 각 청크가 모델 업데이트에 사용할 수 있도록 **동기화된 모든 그래디언트의 완전한 복사본**을 완성하는 것입니다.
Now that the ReduceScatter phase has completed, the AllGather phase begins. Its job is to distribute the fully reduced chunks back to all GPUs, so that each one ends up with a complete, synchronized copy of all gradients, ready to be used to update the model.
- AllGather의 첫 번째 버전에서 In the first iteration of AllGather:
    
    !C2 칸 색은 녹색이 아니라, 흰(공백)색임.
    
    C2 칸 색은 녹색이 아니라, 흰(공백)색임.
    
    - 각 GPU는 현재 보유하고 있는 완전히 축소된 청크를 링의 다음 GPU로 전송합니다
    Each GPU sends the fully reduced chunk it currently holds to the next GPU in the ring.
    - 동시에 이전 GPU로부터 새로운 축소된 청크를 수신합니다
    At the same time, it receives a new reduced chunk from the previous GPU.
- 이 반복 동안 각 순위에서 일어나는 일은 다음과 같습니다: Here’s what happens on each rank during this iteration:
    
    ```bash
    Rank 0 sends reduced chunk B to Rank 1 and receives chunk A from Rank 3
    Rank 1 sends reduced chunk C to Rank 2 and receives chunk B from Rank 0
    Rank 2 sends reduced chunk D to Rank 3 and receives chunk C from Rank 1
    Rank 3 sends reduced chunk A to Rank 0 and receives chunk D from Rank 2
    ```
    
- 이제 **각 GPU는 두 개의 축소된 청크를 보유**하게 됩니다: 원래 ReductScatter 동안 축소된 청크와 이웃으로부터 받은 청크입니다. 이 과정은 세 번의 반복 동안 계속되며, 그 후 모든 GPU는 완전하고 평균화된 그래디언트 집합을 갖게 됩니다.
Each GPU now holds two reduced chunks: the one it originally reduced during ReduceScatter, and one received from its neighbor. This process continues for three iterations, after which all GPUs will have a complete, fully averaged set of gradients.
    
    !GPU0 에 A0..+A3 칸은 ‘빨간’배경색,  GPU 1에 B1..+B3은 ‘파란’배경색임.
    
    GPU0 에 A0..+A3 칸은 ‘빨간’배경색,  GPU 1에 B1..+B3은 ‘파란’배경색임.
    

### AllGather: The Second Iteration

- 두 번째 반복에서는 각 GPU가 가장 최근에 수신한 청크를 다시 링의 다음 GPU로 전송합니다. 이는 모든 피어에 완전히 축소된 그래디언트 청크를 배포하는 프로세스를 계속합니다.
In the second iteration, each GPU again sends the most recently received chunk to the next GPU in the ring. This continues the process of distributing fully reduced gradient chunks to all peers.
    
    !Figure 14-14: AllGather: the Second Iteration
    
    Figure 14-14: AllGather: the Second Iteration
    
- Here’s what happens:
    
    ```bash
    Rank 0 sends chunk A (received from Rank 3 in iteration 1) to Rank 1
    Rank 1 sends chunk B (received from Rank 0) to Rank 2
    Rank 2 sends chunk C (received from Rank 1) to Rank 3
    Rank 3 sends chunk D (received from Rank 2) to Rank 0
    ```
    
- Each GPU now holds three fully reduced chunks:
    
    ```bash
    Rank 0 has: A (original), B, and D
    Rank 1 has: B (original), C, and A
    Rank 2 has: C (original), D, and B
    Rank 3 has: D (original), A, and C
    ```
    
- GPU당 여전히 하나의 청크만 누락되어 있으며, 이 청크는 세 번째이자 마지막 AllGather 반복에서 수신되어 동기화가 완료됩니다.
Only one chunk is still missing per GPU, which will be received in the third and final AllGather iteration, completing the synchronization.
    
    !33.jpeg
    

### AllGather: Third Iteration

- 최종 AllGather 반복에서 각 GPU는 **두 번째 반복 중에 받은 청크를 링의 다음 GPU로 보냅**니다. 이 **작업이 끝나면 모든 GPU는 동기화된 그라디언트 청크 세트를 갖게 됩**니다.
In the final AllGather iteration, each GPU sends the chunk it received during the second iteration to the next GPU in the ring. After this operation, all GPUs have a complete set of synchronized gradient chunks.
    
    !Figure 14-16: AllGather: the Third Iteration.
    
    Figure 14-16: AllGather: the Third Iteration.
    
- Here’s what happens:
    
    ```bash
    Rank 0 sends chunk D to Rank 1
    Rank 1 sends chunk A to Rank 2
    Rank 2 sends chunk B to Rank 3
    Rank 3 sends chunk C to Rank 0
    ```
    
- 이 시점에서 각 GPU는 네 개의 축소된 청크(A, B, C, D)를 모두 받았으며, 이제 모든 GPU는 완전히 축소된 1024개의 그래디언트 세트를 가지게 되었습니다(모든 GPU에 걸쳐 합산).
At this point, each GPU has received all four reduced chunks (A, B, C, and D), and all GPUs now have a complete set of 1024 gradients, each fully reduced (summed across all GPUs).
- AllReduce 프로세스는 모든 GPU에서 각 그래디언트의 합을 계산하지만, 데이터 병렬 학습에서는 일반적으로 **평균 그래디언트를 원합**니다. 따라서 **네 개의 청크(각각 256개의 그래디언트를 포함)를 모두 수신**한 후, **각 GPU는 요소별로 GPU 수(설정에서 4개)로 나눕**니다. 이는 다음을 의미합니다:
The AllReduce process computes the sum of each gradient across all GPUs, but in data-parallel training, we usually want the average gradient. So, after receiving all four chunks (each containing 256 gradients), every GPU performs element-wise division by the number of GPUs (which is 4 in your setup). This means:
    - 각 1024개의 기울기는 4로 나뉩니다. Each of the 1024 gradients is divided by 4.
    - 그 결과 모든 GPU의 로컬 미니 배치에서 결합된 학습 신호를 나타내는 평균 그래디언트가 도출됩니다.
    The result is the average gradient, which represents the combined learning signal from all GPUs' local mini-batches.
- 이러한 평균 그래디언트는 로컬로 모델 가중치를 업데이트하는 데 사용되며, **이제 모든 GPU의 그래디언트 값이 동일하므로 각 모델 복제본은 완벽하게 동기화된 상태로 유지**됩니다.
These averaged gradients are then used to update the model weights locally, and since all GPUs now have the same gradient values, each model replica remains perfectly synchronized
    
    !44.jpeg
    

### Finalizing the AllReduce Operation

- AllGather 단계가 끝나면 각 GPU는 모든 GPU의 해당 그래디언트의 합을 나타내는 1024개의 값을 완전히 축소한 모든 그래디언트 세트를 보유하게 됩니다. 이는 **이제 동기화가 완료**되었음을 의미합니다. **모든 GPU는 동일한 그래디언트 벡터**를 가지며 클러스터 전반에 걸쳐 **모델 일관성이 보장**됩니다. 그러나 분산 학습의 목표는 일반적으로 평균 그래디언트를 계산하는 것이지 합을 계산하는 것이 아닙니다. 이를 달성하기 위해 각 GPU는 1024개의 그래디언트 값을 참여하는 GPU 수로 나누기만 하면 됩니다. 이는 추가 통신 없이 각 GPU에서 독립적으로 수행되는 로컬 작업입니다.
At the end of the AllGather phase, each GPU holds a complete, fully reduced set of all gradients, in our example, 1024 values that represent the sum of corresponding gradients from all GPUs. This means the synchronization is now complete: all GPUs have identical gradient vectors, and model consistency across the cluster is guaranteed. However, the goal of distributed training is typically to compute the average gradient, not the sum. To achieve this, each GPU simply divides each of the 1024 gradient values by the number of participating GPUs, in our case, four. This is a local operation, performed independently on each GPU, without further communication.
- 모든 GPU가 동일한 동기화된 데이터에서 이 평균화를 수행하기 때문에 클러스터 전체에서 결과가 일관되게 유지됩니다. 이 단계 이후에는 추가 동기화가 필요하지 않습니다. **이제 모델은 모든 GPU에서 일관된 가중치 업데이트를 수행할 준비가 되었으며, 다음 학습 반복을 시작할 수 있습니다.**
Because all GPUs perform this averaging on the same synchronized data, the result remains consistent across the cluster. No additional synchronization is needed after this step. The model is now ready for a consistent weight update across all GPUs, and the next training iteration can begin.