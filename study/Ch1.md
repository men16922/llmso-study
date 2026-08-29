### **Introduction to Model Serving and Optimization**

- 요약 : 학습이 끝난 모델을 실제 서비스로 전달하고, 빠르고 안정적이며 저렴하게 운영하는 방법
    - **모델은 가중치 파일 하나가 아니라, 데이터·구조·실행 코드가 합쳐진 실행 가능한 소프트웨어입니다.**
    - **모델 서빙**은 이 모델을 API 형태로 제공하고, 트래픽 증가에 맞게 확장하며, 지연시간·처리량·안정성·보안·비용을 관리하는 **시스템 엔지니어링 영역!**
    - **주요 서빙 방식**
        
        
        | 방식 | 핵심 특징 | 적합한 상황 |
        | --- | --- | --- |
        | On-device | 단말 안에서 직접 실행 | 초저지연, 오프라인, 개인정보 |
        | Single-model | 컨테이너 하나에 모델 하나 | 높은 성능, 독립적 확장 |
        | Multi-model | 컨테이너 하나에 여러 모델 | 모델 수가 많고 트래픽이 낮거나 불규칙 |
        | Serving platform | 여러 앱·모델·워크플로 통합 | 대규모 조직, 복잡한 AI 서비스 |
- **모델의 구성 요소** : 모델 데이터, 모델 아키텍처, 모델 실행 코드
    
    !Figure 1-1. A model is composed of model architecture, model execution code, and model data
    
    Figure 1-1. A model is composed of model architecture, model execution code, and model data
    
    - **모델 데이터**: 학습으로 얻은 weight, bias, configuration. 배치 크기, 입력/출력 텐서, 라벨, 임베딩 같은 실행 메타데이터도 여기에 포함된다.
        
        ```markdown
        # 모델이 '학습'하거나 '실행'에 필요한 숫자와 설정입니다.
        Weight
        Bias
        Configuration
        Embedding 정보
        클래스 정보
        입출력 Tensor 정의
        최대 Batch 크기
        ```
        
        ```python
        # 예를 들어 PyTorch에서는 Weight와 Bias가 state_dict에 저장됩니다.
        torch.save(model.state_dict(), "model_weights.pt")
        ```
        
    - **모델 아키텍처 Model Architecture** : 레이어 구조, 연결 방식, 연산 정의. 입력이 어떤 계산 경로를 지나 출력으로 변환되는지를 결정한다.
        
        ```markdown
        # 모델 내부 설계도
        Layer 개수
        Layer 종류
        Layer 간 연결
        연산 순서
        입력과 출력 구조
        
        # LLM이라면:
        Embedding
        → Transformer Block
        → Attention
        → FFN
        → Output head
        ```
        
        ```python
        # 아키텍처는 학습 코드에서 사용한 모델 클래스 정의와 같은 형태로 서빙 환경에도 필요하다.
        # PyTorch로 작성된 간단한 CNN(합성곱 신경망) 모델 정의입니다. LeNet과 유사한 고전적인 이미지 분류 구조
        class TheModelClass(nn.Module):
            def __init__(self):
                super(TheModelClass, self).__init__()
                self.conv1 = nn.Conv2d(3, 6, 5)
                self.pool = nn.MaxPool2d(2, 2)
                self.conv2 = nn.Conv2d(6, 16, 5)
                self.fc1 = nn.Linear(16 * 5 * 5, 120)
                self.fc2 = nn.Linear(120, 84)
                self.fc3 = nn.Linear(84, 10)
        
            def forward(self, x):
                x = self.pool(F.relu(self.conv1(x)))
                x = self.pool(F.relu(self.conv2(x)))
                x = x.view(-1, 16 * 5 * 5)
                x = F.relu(self.fc1(x))
                x = F.relu(self.fc2(x))
                x = self.fc3(x)
                return x
                
        # 구조 설명
        __init__ (레이어 정의)
        self.conv1 = nn.Conv2d(3, 6, 5)   # 입력 채널 3(RGB), 출력 채널 6, 커널 크기 5x5
        self.pool = nn.MaxPool2d(2, 2)    # 2x2 맥스풀링, stride=2 → 크기 절반으로 축소
        self.conv2 = nn.Conv2d(6, 16, 5)  # 입력 채널 6, 출력 채널 16, 커널 5x5
        self.fc1 = nn.Linear(16*5*5, 120) # 완전연결층: 400 → 120
        self.fc2 = nn.Linear(120, 84)     # 120 → 84
        self.fc3 = nn.Linear(84, 10)      # 84 → 10 (클래스 개수, 예: CIFAR-10)
        
        forward (데이터 흐름)
        x = self.pool(F.relu(self.conv1(x)))  # conv1 → ReLU → 풀링
        x = self.pool(F.relu(self.conv2(x)))  # conv2 → ReLU → 풀링
        x = x.view(-1, 16 * 5 * 5)            # 4차원 텐서를 1차원으로 평탄화(flatten)
        x = F.relu(self.fc1(x))               # 완전연결층 + ReLU
        x = F.relu(self.fc2(x))               # 완전연결층 + ReLU
        x = self.fc3(x)                       # 최종 출력층 (활성화 함수 없음, logits 반환)
        return x
        
        # 전체 흐름 (입력이 32x32 이미지라고 가정)
        ┌──────────────┬────────────────────┐
        │     단계      │       텐서 크기      │
        ├──────────────┼────────────────────┤
        │ 입력          │ (batch, 3, 32, 32) │
        ├──────────────┼────────────────────┤
        │ conv1 → pool │ (batch, 6, 14, 14) │
        ├──────────────┼────────────────────┤
        │ conv2 → pool │ (batch, 16, 5, 5)  │
        ├──────────────┼────────────────────┤
        │ flatten      │ (batch, 400)       │
        ├──────────────┼────────────────────┤
        │ fc1          │ (batch, 120)       │
        ├──────────────┼────────────────────┤
        │ fc2          │ (batch, 84)        │
        ├──────────────┼────────────────────┤
        │ fc3 (출력)    │ (batch, 10)        │
        └──────────────┴────────────────────┘
        ```
        
    - **모델 실행 코드 Model Execution Code** : 아키텍처를 초기화하고, weight를 로드하고, inference를 실행하는 코드.
        
        ```python
        # 모델을 실제로 실행하는 코드. 주요 역할:
        모델 구조 생성
        → Weight 로드
        → 추론 모드 설정
        → 입력 전달
        → 예측 결과 생성
        ```
        
        ```python
        # 서빙 시에는 모델 클래스를 초기화하고, 저장된 weight를 로드한 뒤, evaluation mode에서 입력을 추론한다.
        model = TheModelClass(*args, **kwargs)
        model.load_state_dict(torch.load("model_weights.pt", weights_only=True))
        model.eval()
        pred = model(inputs)
        ```
        
    - 아키텍처와 데이터를 분리해서 저장하는 이유
        - 전체 모델을 하나의 파일로 저장할 수도 있지만, 아키텍처와 weight를 분리하면 버전 변경, 부분 로딩, fine-tuning, 레이어 추가 같은 운영 시나리오에 더 유연하다.
        - 예를 들어 새 모델 구조와 기존 checkpoint 사이에 일부 key가 맞지 않아도 호환되는 파라미터만 선택적으로 로드할 수 있다.
        
        ```python
        **# 설정(Config) 파일
        config.json : 모델 아키텍처 정보 (**레이어 수, hidden size, 어텐션 헤드 수, activation 함수 등). 이 파일만으로모델 구조를 재구성 가능
        generation_config.json : 텍스트 생성 시 기본 파라미터 (max_length, temperature, top_p 등)
        
        **# 가중치(Weight) 파일**
        **pytorch_model.bin** : PyTorch의 전통적인 가중치 저장 포맷 (pickle 기반). state_dict()를 직렬화한 것   
        **model.safetensors** : 최신 표준 포맷. pickle 대신 안전한 직렬화 방식 사용 (임의 코드 실행 위험 없음, 로딩 속도도 더 빠름
        **.pt / .pth** : PyTorch에서 torch.save()로 저장한 파일 (전체 모델 또는 state_dict) 
        ...
        
        **# 토크나이저 관련 파일** (NLP/LLM 모델일 경우)
        tokenizer.json : Fast tokenizer용 통합 파일 (vocab + merge rules + 설정 모두 포함)
        tokenizer_config.json: 토크나이저 클래스, special token 설정 등
        vocab.txt / vocab.json : 단어(토큰) 사전
        ...
        ```
        
    
- **모델 생명주기**: 학습에서 서빙까지
    
    !mermaid-diagram.png
    
    | 단계 | 역할 |
    | --- | --- |
    | 데이터 수집 | 로그, 문서, 센서, 사용자 데이터 수집 |
    | 학습 | 데이터에서 패턴 학습 |
    | 평가 | 정확도, Loss, Benchmark 검증 |
    | 배포 | 모델을 버전 있는 소프트웨어 산출물로 패키징 |
    | 서빙 | API를 통해 실제 요청 처리 |
    | 최적화 | 속도, 비용, 안정성 개선 |
    | 재학습 | 운영 데이터를 다시 학습에 반영 |
    - ML 생명주기는 데이터 수집, 학습, 평가, 배포, 모니터링, 재학습으로 이어진다.
    - 이 중 **모델 서빙**은 **학습된 모델**이 **실제 요청을** 받아 **예측 결과를 반환하는 운영 단계**다.
    - 훈련은 정확도와 학습 효율이 핵심이고, 서빙은 **지연 시간, 처리량, 안정성, 비용, 보안, 모니터링**이 핵심이다.
    
- **모델 서빙** : 입력 요청 수신 → 모델 실행 → 예측 결과 반환 , **트랜스포머Transformers 에 대한 탄탄한 이해가 필수!**
    - 모델 서빙은 API, 웹 서비스, 애플리케이션 내 통합 방식 등을 통해 모델 inference를 제공하는 과정이다.
        
        !mermaid-diagram (1).png.png)
        
    - 아래 구조는 챗봇 애플리케이션이 SageMaker Inference Endpoint에 배포된 LLM을 호출하는 예시
        
        !Figure 1-2. Serving an LLM model for a chatbot app in SageMaker Inference Endpoint
        
        Figure 1-2. Serving an LLM model for a chatbot app in SageMaker Inference Endpoint
        
    - LLM 서빙에서는 일반 모델 서빙 지식만으로 부족하다.
    - 토큰 생성 방식, KV Cache, attention 비용, batching, decoding, GPU memory 병목 같은 LLM 고유 특성을 알아야 운영 비용과 성능을 제대로 제어할 수 있다.
    - **LLM 지식은 LLM 서비스에 필수적**입니다
    - 효과적인 LLM 서비스와 최적화를 위해서는 AI 알고리즘, 특히 **트랜스포머Transformers 에 대한 탄탄한 이해가 필수적**입니다.
    - LLM 서비스 기술의 모든 발전은 LLM 실행 과정에서 발생하는 병목 현상을 극복하기 위해 설계되었습니다.
    - 따라서 LLM 아키텍처를 잘 이해하면 처리량과 지연 시간을 최적화하는 데 필요한 직관을 얻을 수 있습니다.
    - 다음 장들에서는 LLM 서비스와 최적화 방법을 이해하는 데 필요한 기초 지식을 다룰 것입니다.
    
    !image.png
    
- **왜 모델 서빙을 공부해야 하는가?** : 모델 서빙의 원리를 이해하고 있어야 최적의 선택을 할 수 있다!
    - 클라우드 벤더가 managed endpoint를 제공하더라도, 모델 서빙을 이해하지 못하면 다음 결정을 제대로 내리기 어렵다.
        - 어떤 모델을 어떤 인프라에 배포할지
        - latency와 throughput 목표를 어떻게 맞출지
        - GPU/CPU/memory 비용을 어떻게 통제할지
        - autoscaling과 routing을 어떻게 설계할지
        - 모니터링, 보안, 장애 대응을 어떻게 구성할지
    - 핵심 메시지는 "모든 상황에 맞는 하나의 서빙 솔루션은 없다"는 점이다.
    - 모델 크기, 트래픽 패턴, 보안 요구사항, 비용 구조, 지연 시간 **목표에 따라 다른 설계가 필요**하다.
    - **기술은 계속 진화**하므로, 서빙의 기본기를 탄탄히 알아야 **새로운 기술이 나왔을 때 장단점을 판단**하고 특정 프레임워크/벤더에 종속되지 않은 채 **비즈니스에 유리한 선택**을 할 수 있음
    - 클라우드나 LLM API를 그대로 써도 되지만, 서**빙의 원리를 이해해야 비용·보안·성능 면에서 최적의 판단을 내릴 수 있고**, 특정 벤더에 종속되지 않으면서 경쟁력을 유지할 수 있다.
    
- **LLM 서빙 최적화가 중요한 이유**
    - 모델을 배포해서 정상 작동한다고 ‘끝’이 아닙니다. LLM은 특히 별도 최적화 없이 서빙하면 **실사용자가 몰릴 때 빠르게 문제**가 생깁니다:
        - 부하가 걸리면 지연시간(latency) 증가
        - 처리량(throughput)이 하드웨어 성능보다 훨씬 낮은 수준에서 정체
        - 사용량이 늘수록 비용이 선형적으로(또는 그 이상) 증가
    - 데모나 파일럿 단계에선 잘 작동하던 시스템이, **실제 유저가 유입**되면 경제적/운영적으로 감당 불가능해지는 경우가 많습니다.
    - 핵심 개념 정의
        - **모델 서빙 최적화**: 지연시간 감소, 처리량 증가, 리소스 활용도 개선 등을 통해 서빙 성능을 향상시키는 작업
            - 낮은 latency
            - 높은 throughput
            - 높은 GPU 활용률
            - 낮은 cost per request
            - 안정적인 tail latency
            - 효율적인 메모리 사용
        - **목표**: 비용을 통제하면서 서빙 효율을 극대화하는 것
    - **왜 특히 LLM에서 중요한가**
        - LLM은 연산 요구량이 매우 커서 **운영 비용 부담이 큼**
        - 예시: Alphabet 회장 John Hennessy는 2023년 로이터와의 인터뷰에서 "LLM 요청 1건 처리 비용이 전통적인 키워드 검색보다 10배 비쌀 수 있고, 이는 수십억 달러 규모의 추가 비용으로 이어질 수 있다"고 언급
        - L**LM에서는 최적화**가 "선택"이 아니라 **"필수"**에 가까움
    
- **vLLM 소개** : The High-Throughput and Memory-Efficient **inference and serving engine for LLMs** - Site
    
    !image.png
    
    - vLLM은 high-throughput, low-latency LLM serving을 위해 설계된 대표적인 open source framework다. PagedAttention, continuous batching, OpenAI-compatible API server, tensor parallelism 등을 제공한다. ***⇒ 책 8장 상세 소개 예정!***
        
        !vLLM.jpeg
        
    - 기본 Python API 사용
        
        ```python
        # initialize LLM model
        llm = LLM(
          model="Qwen/Qwen3-7B-Instruct",
          trust_remote_code=True,
          dtype="float16",
          max_model_len=32768,
          gpu_memory_utilization=0.8,
        )
        
        # run model generation requests
        outputs = llm.generate(prompts, sampling)
        ```
        
    - OpenAI-compatible API server
        
        ```bash
        # start vLLM API server
        vllm serve Qwen/Qwen3-7B-Instruct \
          --trust-remote-code \
          --dtype bfloat16 \
          --max-model-len 32768 \
          --gpu-memory-utilization 0.8
        
        # call the Qwen model via the OpenAI-compatible API
        curl http://localhost:8000/v1/chat/completions \
         -H "Content-Type: application/json" \
         -d '{
           "model": "Qwen/Qwen3-7B-Instruct",
           "temperature": 0.7,
           "max_tokens": 256,
           "stream": true
         }'
        ```
        
    - **vLLM Architecture**
        
        !Figure 8-1. vLLM system architecture
        
        Figure 8-1. vLLM system architecture
        
        - **LLMEngine**: 사용자-facing API와 engine core 사이의 **orchestration 계층.**
        - **EngineCore**: scheduler, KV cache manager, model executor를 **조율**한다.
        - **Scheduler**: request를 어떤 iteration에 넣을지 결정한다.
        - **ModelExecutor**: worker process를 관리하고 distributed execution을 담당한다.
        - **GPUWorker / GPUModelRunner**: GPU에서 실제 model forward를 수행한다.
    - **Workflow**
        
        !Figure 8-4. vLLM generation-request execution workflow
        
        Figure 8-4. vLLM generation-request execution workflow
        
    
- vLLM이 일반적인 Hugging Face 실행 방식보다 높은 처리량을 보이는 사례 소개 → **설정값 하나하나가 성능에 큰 영향!**
    - **vLLM 주요 최적화 요소**
        - PagedAttention
        - 동적 batching
        - KV Cache 효율화
        - GPU 메모리 활용률 설정
        - Tensor Parallelism
        - 정밀도 조정
    - 실행 예시 : f16 정밀도, GPU memory utilization, 동시 sequence 수, batched token 수, tensor parallel size를 조정해 H100 GPU 환경에서 처리량과 지연 시간을 균형 있게 맞추는 설정
        
        ```bash
        # gpt-oss 20B 모델, H100 80GB GPU >> 자세한 내용은 6~7장에서 다룰 예정!
        # PagedAttention(KV 캐시 최적화 기법)은 vLLM에서 기본 활성화됨
        python -m vllm.entrypoints.openai.api_server \
          --model openai/gpt-oss-20b \
          **--dtype bf16** \                    # 모델 정밀도 설정
          **--gpu-memory-utilization 0.9** \
          **--max-num-seqs 16** \               # 동시 처리 요청 수(배치 크기)
          **--max-num-batched-tokens** 16384 \
          **--tensor-parallel-size 2**          # H100 GPU 2개에 모델 분산
        ```
        
        | 옵션 | 의미 |
        | --- | --- |
        | `--dtype bf16` | 모델 계산 정밀도 |
        | `--gpu-memory-utilization 0.9` | GPU 메모리 90% 사용 목표 |
        | `--max-num-seqs 16` | 최대 동시 시퀀스 수 |
        | `--max-num-batched-tokens` | 한 배치의 최대 토큰 수 |
        | `--tensor-parallel-size 2` | GPU 2개에 모델 분할 |
    - **model serving-specific frameworks 중 HF vs TGI vs vLLM 비교**
        
        !Figure 1-3. vLLM은 HF Transformers 및 TGI 대비 더 높은 throughput을 보인다
        
        Figure 1-3. vLLM은 HF Transformers 및 TGI 대비 더 높은 throughput을 보인다
        
        - vLLM 팀 실험 (2023, Llama-7B on A10G / Llama-13B on A100 40GB): HF Transformers 대비 최대 24배, HF TGI 대비 최대 3.5배 높은 처리량 달성 (그래프 기준으로는 HF 대비 8.5~15배, TGI 대비 3.3~3.5배)
        - 책 저자들의 DeepSeek R1 실험: vLLM에서 단 두 가지 설정만 바꿔서(FP8 MLA 커널 활성화 + 배치 크기 증가) 38 TPS → 600 TPS로 15배 향상
    - **요약**
        - GPU는 비싼 자원이므로, 추가 인프라 투자 없이 **설정 최적화만으로 처리량을 6배, 지연시간을 3배 개선할 수 있다는 건 게임체인저**
        - 프로덕션 LLM 시스템에서 최적화는 "성능을 더 짜내는" 선택사항이 아니라, **비용을 지속 가능하게 유지하면서 비즈니스 SLA(**지연시간/처리량 기준)를 **충족시키기 위한 필수 요소**
        - **서빙 프레임워크의 설정값 하나하나가 성능에 큰 영향을 미치는 잠재적 최적화 포인트**
    

### 모델 서빙 방안

- [모델 서빙 방안 1] **On-Device** 또는 Edge Serving : 모델을 서버가 아니라 **사용자 기기에서 직접 실행**
    - On-device Serving은 모델을 스마트폰, 드론, 카메라, 로봇 등에서 직접 실행하는 방식입니다.
    - 온디바이스 앱의 핵심 **구성 요소**
        - **모델 런타임**(Model Runtime): 다양한 하드웨어(스마트폰, 드론 등)와 OS(iOS, Android, Linux)에서 모델을 효율적으로 실행하도록 추상화하는 소프트웨어 계층. GPU 같은 전용 하드웨어로 연산을 넘기는 "delegate" 기능도 지원. 대표적으로 LiteRT, ONNX Runtime(ORT), Core ML 등이 있음
        - **모델 래퍼**(Model Wrapper): 개발자가 직접 구현하는 컴포넌트로, 입력 전처리 → 모델 로딩 → 실행 → 출력 후처리 등 런타임과의 상호작용을 캡슐화해 앱 로직이 쉽게 모델을 호출할 수 있게 함
            
            !Figure 1-4. On-device (a) AI app design and (b) model deployment workflow
            
            Figure 1-4. On-device (a) AI app design and (b) model deployment workflow
            
        - **흐름**: 앱 로직 → **모델 래퍼** 호출 → (데이터 변환 후) **모델 런타임** 실행 → **로컬 하드웨어에서 추론**
        - **모델을 온디바이스용으로 준비하는 과정** : Qualcomm AI Hub 같은 도구가 이 과정을 자동화해줌
            1. 변환(Convert): 학습 포맷 → 런타임 전용 포맷으로 변환 (예: PyTorch ResNet → .tflite for LiteRT)
            2. 정확도 검증: 서버와 기기에서 동일 입력으로 실행해 출력 차이 비교 (변환/최적화로 정확도 저하가 없는지 확인)
            3. 성능 측정: 로컬 하드웨어가 비즈니스 요구사항을 만족하는 속도로 실행되는지 확인
            4. 패키징 및 배포: 앱 설치/업데이트에 포함해 배포
        
    - 온디바이스 서빙이 **적합한 경우**
        - **프라이버시** 우선 워크로드: 생체 인증, 건강 데이터 등 원본 데이터가 기기 밖으로 나가면 안 되는 경우
        - **초저지연** 애플리케이션: 제스처 인식, 로봇 제어, AR/VR, 실시간 오디오 처리 등 밀리초 단위가 중요한 경우
        - 연결이 **불안정하거나 끊기는** 환경: 산업 장비, 원격 센서, 차량, 드론 등
        - **IoT/스마트시티/로봇공학**: 특정 작업에 최적화된 저전력 모델이 필요한 경우
    - 온디바이스 서빙의 **제약/트레이드오프**
        1. **연산·저장 공간 제약**: CPU/GPU/메모리가 제한적이라 **대형 모델 실행이 어려움** (예외적으로 Gemma 3 270M 같은 경량 모델은 온디바이스용으로 설계됨)
        2. **전력 소모**: 배터리를 빠르게 소모함 (예: 저해상도→고해상도 실시간 영상 향상은 전력 소모가 커서 로컬에서 잘 안 함)
        3. **업데이트/유지보수의 어려움**: 모델 개선 시 모든 기기에 개별적으로 업데이트를 배포해야 함 (예: 은행 앱의 사기 탐지 모델 개선 시 잦은 앱 업데이트 필요)
        4. **하드웨어 지원의 불일치**: 기기마다 NPU 지원 여부가 다름 (예: iPhone Neural Engine 최적화 모델이 Android Snapdragon에선 비효율적일 수 있음)
    
- [모델 서빙 방안 2] **Single-model Service** : **단일 모델 서비스**, 모델 하나 또는 **모델 버전 하나를 전용 서비스로 배포**
    - 클라우드 기반 모델 서빙에서 가장 널리 쓰이는 클래식한 패턴으로, 각 모델(그리고 각 모델 버전)을 독립된 웹 서비스로 배포하여 HTTP/gRPC로 예측 API를 노출하는 방식입니다. 표준 마이크로서비스 구조(컨테이너화)를 따르며, API가 요청을 받아 백엔드 워커(컨테이너)로 라우팅합니다.
        
        !Figure 1-5. Single-model service architecture
        
        Figure 1-5. Single-model service architecture
        
    - 단일 모델 서빙 컨테이너의 3대 구성 요소
        
        !Figure 1-6. Single-model serving container design
        
        Figure 1-6. Single-model serving container design
        
        1. **API-Server**: HTTP/gRPC로 추론 기능을 외부에 노출
        2. **Model Management**: 모델 다운로드 → 로컬 저장소 추출 → 추론 백엔드에 로딩 (신규 모델을 감지해 자동 갱신)
        3. **Inference Backend**: 실제 모델 실행 담당 (TensorFlow Serving, TorchServe, vLLM, TensorRT-LLM 등 활용)
    - **라우팅 전략** : 단순 라운드로빈(순서대로 c1→c2→c3)은 한계가 있음
        - 요청마다 처리 시간이 다르기 때문(예: 5,000토큰 LLM 요청 vs 100토큰 요청, 고해상도 이미지 vs 저해상도 이미지).
        - 그래서 더 정교한 전략이 필요: ***⇒ 좀 더 똑똑하고 지능적인 LLM 라우팅은 뒤에서 다룸 예정!***
            - 가중 라운드로빈: 성능 좋은 서버에 더 많은 요청 할당
            - 최소 연결 수(Least Connections): 활성 연결이 가장 적은 서버로 라우팅
            - 최소 응답시간(Least Response Time): 응답이 가장 빠른 서버로 라우팅
            - 동적 로드 밸런싱: CPU/GPU/메모리/큐 길이 등 실시간 지표 기반 분배
            - (참고) Cache-Aware Routing
                
                !image.png
                
        
    - **스케일링 방식**
        - **수평 확장**(Horizontal Scaling / Scale Out): 트래픽 증가 시 인스턴스(컨테이너)를 여러 대 추가. 보통 오토스케일링(예: Kubernetes HPA)으로 CPU/메모리/지연시간/요청 수 등을 모니터링해 자동 조정 ← 같은 모델 Container를 더 많이 추가
        - **수직 확장**(Vertical Scaling / Scale Up): GPT-4, Llama-2-70B처럼 모델이 너무 커서 GPU 1개 메모리로 안 될 때, 더 강력한 GPU(H100, A100 등)를 쓰거나 여러 GPU/머신에 분산. vLLM 같은 프레임워크가 `--tensor-parallel-size` 옵션 하나로 이를 쉽게 해줌 ← 더 큰 GPU 또는 여러 GPU에 모델을 분할
            
            ```bash
            python -m vllm.entrypoints.api_server \
               --model meta-llama/Llama-2-13b-hf \ 
               **--tensor-parallel-size 4** \ 
            ```
            
    - **중요 원칙**: 가능하면 여러 머신에 분산(inter-node)하기보다, ‘**한 머신에 여러 GPU(intra-node)**’로 구성하는 게 낫습니다. 머신 간 분산은 네트워크 오버헤드와 동기화 복잡도로 인해 지연시간이 늘어나기 때문입니다.
        - **NVLink 900GB/s** 보다 **IB/RoCEv2** 400Gbps(=**50GB/s**) 가 **18배 느림**
            
            !https://youtu.be/yn4GGAtZ7QE?si=NiWFxv2m4It900Zw&t=33
            
            https://youtu.be/yn4GGAtZ7QE?si=NiWFxv2m4It900Zw&t=33
            
            !image.png
            
        - **K8S Bin Packing 스케줄러** : GPU 파편화 완화 - Blog
            - 기본 스케줄러는 가능한 골고루 분산 - 만약 GPU Worker Node 가 5개가 있고, GPU 리소스 요구량이 1 GPU이면서 Replica 가 5인 GPU Workload 가 배치된다면, 기본 스케줄러는 이를 골고루 분산하여 개별 Worker Node 가 하나씩의 GPU Pod 을 가지도록 배치한다.
            - Bin Packing은 제한된 자원을 최적화하여 사용하는 스케줄링 전략이다. GPU와 같은 제한된 자원을 다룰 때, Pod을 배치할 Node를 가능한 빈틈없이 채워 리소스 사용률을 극대화하기 위해서 사용한다. (bin 은 말 통, 상자라는 의미이다. bin packing은 상자에 물건을 담을 때 차곡차곡 쌓아서 빈공간이 없도록 하는 경우를 떠올려보자.)
        - **(참고) GPU 스케줄러** AI Factory Operations Lab 정리 중…  , (따라하며 확인하는) GPU 가상화: HAMi 설치 및 사용
        
    - 단일 모델 서비스가 기본 선택지인 이유
        - 리소스 경쟁 없음 → 최고의 성능/최저 지연시간
        - 모델별 독립적 확장 가능
        - 로그/지표/업데이트가 격리되어 있어 배포·디버깅이 쉬움
        - 한 모델이 죽어도 다른 모델에 영향 없음 (신뢰성)
        - 모델별 하드웨어 최적화로 비용 통제 용이
    - 한계
        - 자원 효율성과 비용 측면에서 약점이 있음. 예를 들어 고객 100명이 각자 모델 10개씩 배포하는 에이전트 플랫폼이면 총 1,000개의 개별 서비스를 운영해야 함 → 유지보수/패치/모니터링 부담이 압도적이고, 실제로 안 쓰이는 모델도 자원을 낭비하게 됨
    - 결론
        - 이런 한계를 해결하기 위해, 여러 모델이 컴퓨팅 자원을 동적으로 공유하도록 하는 멀티 모델 서비스(Multi-Model Service) 방식이 다음 대안으로 등장합니다.
    
- [모델 서빙 방안 3] **Multi-Model Service** : 컨테이너 하나가 여러 모델을 공유해서 실행
    - 하나의 서빙 컨테이너 안에 여러 모델을 함께 호스팅하며, GPU/CPU/메모리를 모델들끼리 공유하고, 트래픽에 따라 동적으로 모델을 로드/언로드하는 방식입니다. 비용을 크게 절감하고 가격 대비 성능을 극대화할 수 있습니다.
        
        ```bash
        Container 1
        ├─ Model A
        ├─ Model B
        └─ Model D
        ```
        
        - 모든 모델을 항상 GPU에 올리지 않고, 요청이 오면 동적으로 로드합니다.
        - "고객 100명 × 모델 10개 = 1,000개 모델" 에이전트 플랫폼 예시:
        - 단일 모델 서비스처럼 1,000개를 다 GPU/메모리에 올리는 대신, 요청이 들어올 때만 모델을 로드하고, 비활성 상태이거나 메모리가 필요하면 언로드하는 방식으로 인프라 비용을 크게 절감.
        
    - **멀티-모델 서빙 컨테이너 디자인**
        1. **Model Server Inference Backend**: 프레임워크(TensorFlow, ONNX, PyTorch 등)가 서로 달라도 통합된 예측 API로 처리하는 "블랙박스" 역할. 내부적으로 각 프레임워크별 백엔드를 여러 개 갖고 있음. 대표 오픈소스 예시: NVIDIA Triton Inference Server
        2. **Model Cache Management**: 두 가지 역할
            - 모델 저장소에서 모델을 다운로드해 추론 백엔드에 로드
            - LRU(Least Recently Used) 캐시로 자원 사용량이 높으면 가장 안 쓰인 모델을 언로드해 메모리 확보
        
        !Figure 1-7. Multi-model serving container design
        
        Figure 1-7. Multi-model serving container design
        
        1. 모델 A가 이미 로드되어 있으면 → 바로 실행 후 결과 반환
        2. 로드 안 되어 있으면 → 저장소에서 다운로드 → 로드 → 실행
        3. 메모리/디스크 사용량이 임계치(예: 80%) 초과 시 → 캐시에서 가장 덜 쓰인 모델을 찾아 언로드
        
    - 멀티 모델 서비스는 두 가지 문제 : 라우팅과 오토스케일링의 어려움
        
        !Figure 1-8. Serving and scaling challenges in multi-model serving
        
        Figure 1-8. Serving and scaling challenges in multi-model serving
        
        1. **라우팅 문제**: 모델이 아무 컨테이너에나 있을 수 있어서, **이미 해당 모델이 로드된 컨테이너로 요청을 보내야 함**. 안 그러면 콜드 스타트(모델 로딩 대기)나 모델 스와핑(기존 모델 언로드 후 새 모델 로드)으로 지연이 생김
        2. **모델별 스케일링 문제**: 모델마다 트래픽이 달라서, 인기 있는("hot") 모델은 더 많은 인스턴스가 필요함
        
    - **해결책 : 라우팅 계층에 두 가지 기능 추가 ⇒ 최근 AI Gateway 제품군 : Envoy AI Gateway , LiteLLM 등**
        - **replica(복제본) 속성**: 각 모델을 몇 개 인스턴스로 호스팅할지 정의
        - **route map**: 어떤 모델이 어떤 컨테이너에 있는지 추적하는 맵
        
        !Figure 1-9. Route model server requests with host/model map and model replica counts
        
        Figure 1-9. Route model server requests with host/model map and model replica counts
        
        - 모델 A의 replica가 2라면 → 라우터가 컨테이너 C1, C3에 모델 A를 배치하고 → 이후 모델 A 요청을 C1/C3에 균등 분배.
        - 트래픽 변화에 따라 replica 수를 실시간 조정하고, 새 replica를 어느 컨테이너에 넣을지도 라우터가 결정(일종의 bin-packing 문제)
        - Envoy AI Gateway
            
            !https://github.com/envoyproxy/ai-gateway
            
            https://github.com/envoyproxy/ai-gateway
            
        
    - **멀티 모델 서비스가 어려운 상황**
        - 모델이 너무 커서 GPU 하나에 여러 모델을 공유할 여지가 없거나, 언로드가 빈번해 콜드 스타트 오버헤드가 큰 경우
        - 개별 모델의 트래픽이 많고 저지연이 필요해서 항상 로드된 상태여야 하는 경우 → 이땐 단일 모델 서비스가 더 나음
        - 모델별로 보안 정책이 다른 경우
        - 캐시 관리, 모델별 라우팅/스케일링, 프레임워크 호환성, 의존성 충돌 등으로 운영 복잡도가 높은 경우
        
    - 결론
        - **단일 모델 서비스와 멀티 모델 서비스는 상호 보완적**입니다. 실무에서는 두 방식을 조합해 서로 다른 서빙 케이스를 하나의 플랫폼 안에서 처리하며, 이것이 다음 주제인 모델 서빙 플랫폼(Model Serving Platform)으로 이어집니다.
    
- [모델 서빙 방안 4] **Model Serving Platform** : 오케스트레이션 + 리소스 그룹 + 워크플로우까지 포함
    - 비즈니스가 성장하면 서빙 요구사항이 복잡해지고, 단일 모델 서비스와 멀티 모델 서비스를 단순히 나열하는 것만으로는 부족해집니다. 두 가지 큰 과제가 생깁니다.
        1. **여러 모델의 협업이 필요한 태스크 증가**: 예를 들어 Siri 같은 음성 비서는 음성 인식 + NLP + 추천 모델 + 음성 합성(TTS)을 하나의 명령 처리를 위해 함께 작동시켜야 함
        2. **자원 최적화의 복잡도 증가**: 플랫폼 위에 앱이 늘어날수록 GPU/CPU/메모리를 여러 모델에 걸쳐 효율적으로 배분하면서도 확장성, 비용 효율성, 자원 경합 최소화를 모두 챙겨야 함
        
    - **모델 서빙 플랫폼의 설계**
        1. **Gateway:** 외부 요청 진입점.
        2. **Routing:** 모델과 serving group을 선택한다.
        3. **그래프 실행(Graph Execution) 컴포넌트 : 한 AI 요청이 여러 모델을 순차 또는 병렬로 사용 지원**
            - Airflow, Ray 같은 도구로 다단계(multistep) 추론 워크플로우를 지원
            - 각 앱 팀이 자신만의 추론 워크플로우를 정의해 그래프 실행 엔진에 배포
            - 요청이 들어오면 그래프 엔진이 사전 정의된 워크플로우를 실행하고, 각 단계마다 라우팅 컴포넌트를 호출해 올바른 서빙 그룹/서비스로 요청을 전달
            - 한 AI 요청이 여러 모델을 순차 또는 병렬로 사용할 수 있습니다. 예를 들어 고객 상담 챗봇은 다음 모델을 사용할 수 있습니다.
                
                !mermaid-diagram (2).png.png)
                
                ```bash
                Intent Classification
                → Embedding
                → Retrieval
                → LLM
                → Safety Filter
                ```
                
            - Graph Executor는 이 실행 순서를 관리하고 각 단계마다 적절한 모델 서비스로 요청을 전달합니다.
        4. **리소스 그룹(Resource Groups) : 앱마다 CPU, GPU, 메모리 한도를 분리**
            - 애플리케이션/비즈니스 시나리오별로 예측 워크로드를 분리
            - 예: App1 리소스 그룹 안에 단일 모델 서비스 2개 + 멀티 모델 서비스 1개가 함께 존재
            - 각 리소스 그룹은 비즈니스 요구사항에 맞춰 자체 CPU/GPU/메모리 쿼터를 할당받음 → 성능과 비용 최적화
        
        !Figure 1-10. Model serving platform design
        
        Figure 1-10. Model serving platform design
        
        - 요청 → Gateway → 그래프 실행 엔진(다단계 워크플로우 실행) → 각 단계마다 라우팅 컴포넌트 호출 → 해당 리소스 그룹의 적절한 단일/멀티 모델 서비스로 전달
        - *실제 플랫폼에는 여기에 접근 제어, 보안, metric/monitoring, deployment/DevOps 통합이 추가된다.*
    
    - 모델 서빙 "플랫폼" (오케스트레이션 + 리소스 그룹 + 워크플로우까지 포함)
        
        !kserve-mlflow-llm.gif
        
        - KServe (구 KFServing) : Kubernetes 네이티브, 오토스케일링(scale-to-zero 포함), 멀티 프레임워크 지원.
            
            !image.png
            
        - Ray Serve : Ray 기반, 다단계 추론 그래프(그래프 실행 컴포넌트 Graph Execution) 구성에 강점
            
            !architecture-2.0.svg
            
        - MLflow (Model Serving) : 모델 레지스트리와 연동된 서빙, 실험 추적까지 통합 관리
    
- Summary
    - 이 장에서는 모델을 엔지니어링 관점에서 다뤘습니다. **모델**은 정적 데이터 파일이 아니라 실행 가능한 **구성요소**로 봐야 하며, 다음 세 가지 핵심 요소로 이루어집니다.
        - 모델 데이터 — 가중치, 편향, 설정값
        - 모델 아키텍처 — 레이어와 연산의 구조
        - 모델 실행 코드 — 모델을 로드하고 추론을 실행하는 코드
    - 이어서 **모델 서빙(model serving) 개념**을 소개했습니다. 모델 서빙이란 실제 운영 환경에서 모**델을 배포해 실시간 데이터를 처리하고 예측을 생성하는 과정**입니다. 배포 시나리오로는 온디바이스(on-device), 온프레미스(on-premises), 클라우드 기반 **서빙 세 가지**를 다뤘고, 확장성(scalability), 지연시간(latency), 모니터링, 보안, 비용 최적화 등 **서빙 시 고려해야 할 핵심 요**소들을 짚었습니다.
    - 또한 클라우드 벤더 솔루션이나 대규모 언어 모델(LLM)을 사용하더라도 **왜 모델 서빙에 대한 이해와 최적화가 여전히 중요**한지 설명했습니다. 클라우드 서빙은 편리하지만 복잡한 통합, 비용 트레이드오프, 보안 문제를 여전히 해결해야 하며, LLM 역시 강력하지만 실무에 적용하려면 다중 모델 파이프라인, 파인튜닝, 비용 효율적인 배포 전략이 필요합니다.
    - 특히 **LLM 서빙 최적화의 중요성**을 강조했는데, KV Cache + Paged Attention(vLLM), Radix Attention(SGLang) 같은 기법을 활용하면 추가 인프라 비용 없이 처리량을 6배 높이고 지연시간을 1/3로 줄일 수 있습니다. LLM 추론은 연산 비용이 크기 때문에, 서빙 최적화는 선택이 아니라 비용 효율적인 AI 배포를 위한 필수 요소입니다.
    - 마지막으로 온디바이스(엣지) 서빙부터 단일 모델 서비스, 다중 모델, 풀 모델 서빙 플랫폼까지 **대표적인 모델 서빙 패러다임**들을 소개했으며, 각각 지연시간·비용·확장성·복잡도 측면에서 서로 다른 장단점을 가진다고 설명했습니다.
    - 이 장을 통해 **모델 서빙**이 **학습 알고리즘 설계보다는** 모델을 실제 애플리케이션에 효율적으로 배포하고 통합하는 **엔지니어링 중심의 분야**임을 전달하고자 했습니다. 다음 장부터는 실습을 통해 실제로 모델 서빙이 어떻게 구축되고 동작하는지 살펴봅니다 — 2장에서는 LLM 모델 서빙, 3장에서는 더 넓은 범위의 모델 서빙 시스템 설계와 구현을 다룰 예정입니다.