- **[멤버 투표 1] LLM 서빙 플랫폼**을 **운영(경험)** 및 **준비** 중인지(자사 or 고객사 모두 포함) 관련 간단한 투표
    1. LLM 서빙 플랫폼를 **운영 및 관리** 중 : 17분
    2. LLM 서빙 플랫폼를 **기획/운영 경험** 있음 : 4분
    3. LLM 서빙 플랫폼를 **도입을 위한 준비** 중(기획, PoC 등) : 15분
    4. 아직 계획 없음 : 18분
    
- `질문` ***→ 학습을 하시고 스스로 아래 질문에 답변을 해보시기 바랍니다!***
    1. 단일 모델 서빙 시스템은 왜 API server, LLM engine, Workload manager, Model executor, Model worker를 굳이 별도 프로세스/컴포넌트로 분리해서 설계할까? (GPU와 CPU 작업을 격리하는 이유는 무엇인가?)
    2. 배칭(batching)과 스트리밍(streaming)은 각각 어떤 문제를 해결하며, 두 기능이 하나의 서빙 시스템 안에서 어떻게 공존할 수 있는가?
    3. 하나의 서비스가 여러 모델을 동시에 서빙해야 할 때(멀티 모델 서빙), 리소스를 어떻게 동적으로 관리(로딩/캐싱/제거)하며, 비용 효율 최적화와 지연시간/확장성 최적화 사이의 트레이드오프는 무엇인가?
    
- `실습 환경 참고` : 로컬 PC로 실습가능 - GPU 없이 실습 가능, Docker 로 Triton 실행

### Intro

- **목표** : 특정 프레임워크(vLLM, Triton 등)를 바로 다루기보다, from first principles로 **서빙 시스템을 직접 만들어보면서 원리를 체득**
    - 오픈소스 서빙 프레임워크가 워낙 많아서 선택 어려움 → 기본 원리를 알면 합리적인 판단을 할 수 있음
- **구성** : 학습을 위해 의도적으로 간소화
    - 학습 : batching, streaming, routing, isolation, resource management
    1. **Single-model serving** : 하나의 서비스가 하나의 모델을 전용으로 실행
        - batching + streaming을 지원하는 단일 모델 서빙 서비스부터 만들고, 이를 일반화한 설계 패턴과 실무적 제약을 짚음.
    2. **Multi-model serving** : 하나의 서비스가 여러 모델을 필요할 때 로드하고 공유 자원에서 실행
        - 위 아이디어를 확장해 여러 모델을 서빙하는 시스템 : 비용 효율 최적화 버전, 레이턴시/스케일러빌리티 최적화 버전
- **한줄 요약**
    - **모델 서빙**은 단순히 모델의 `generate()` 함수를 호출하는 것이 아니라, API 처리·요청 추적·배치·스트리밍·프로세스 격리·메모리 관리·라우팅·확장·장애 복구를 **함께 설계하는 시스템 엔지니어링**

### Build on Online LLM Serving Service from Scratch

- 배경
    - vLLM과 Triton 같은 최신 서비스 프레임워크는 LLM 호스팅에 수반되는 복잡성의 상당 부분을 추상화합니다. 하지만 이러한 추상화는 중요한 아키텍처적 트레이드오프도 함께 숨기고 있습니다. 성능, 비용, 확장성에 대해 효과적으로 판단하려면, 프레임워크에 의존하기 전에 **서빙 시스템의 핵심 메커니즘을 이해**하는 것이 필수적입니다.
    - 이 섹션에서는 단순화된 **온라인 단일 모델 LLM 서비스를 구축**해 보겠습니다. 목표는 프로덕션 서비스 프레임워크를 대체하는 것이 아니라, 요청 처리, 배칭, 스트리밍, 스케줄링, 그리고 LLM 서비스를 위한 자원 관리 같은 기본 구성 요소를 노출하는 것입니다.
    - 최소한의 생성 서비스부터 시작해 **점차 배칭과 스트리밍 기능을 추가**할 것입니다. 마지막으로, 실제로 vLLM이 배칭을 어떻게 처리하는지 보여주며 마무리하겠습니다. 두 가지 접근법을 모두 이해하면 단일 모델 서빙 아키텍처에 대해 논리적으로 판단하고, 프레임워크 선택을 평가하며, 실제 시스템에서 설계 트레이드오프를 합리적으로 결정할 수 있게 될 것입니다.
    - 책 후반부, 특히 **8장에서는 vLLM**을 자세히 살펴보고, 이와 같은 문제들을 매우 최적화되고 확장 가능한 방식으로 어떻게 해결하는지 알아볼 것입니다.
    - 책 흐름
        1. 단일 생성 요청 처리부터 시작
        2. 배칭(batching) 지원 추가
        3. 스트리밍(streaming) 지원 추가
        4. 마지막에 vLLM이 실무에서 배칭을 어떻게 처리하는지 비교
    
- **Design Goals** : 단일 모델 serving service 목표
    - 이번 연습에서는 시작 시 단일 LLM을 로드하고 배치 및 스트리밍 모두에 대해 동시 생성 요청을 지원하는 서비스를 제공하는 모델을 구축할 것입니다. 이 예제는 **CPU에서 실행 가능한 하나의 LLM 모델에만 적용**할 수 있도록 의도적으로 단순화했지만, 앞으로 고급 모델 최적화 기법을 활용해 다중 노드의 일반화된 프로덕션급 시스템으로 확장하는 데 필요한 모든 핵심 요소를 포함하고 있습니다.
        - HTTP API로 prompt를 받는다.
        - backend worker process에서 모델을 로드하고 inference를 수행한다.
        - 단일 요청, batch 요청, streaming 요청을 처리한다.
        - request와 output을 추적하기 위해 sequence id를 관리한다.
        - 나중에 vLLM 같은 serving framework로 backend를 교체할 수 있게 구조를 분리한다.
    - 복잡하고 운영 준비가 된 서비스를 직접 구축하기보다는, LLM 서비스의 다음과 같은 핵심 요소들을 이해할 수 있도록 기본 구성 요소를 구현하는 방식을 추구합니다:
        - 웹 API가 생성 요청을 처리하도록 설계되는 방식 , 배칭과 스트리밍 포함
        - 일반적인 LLM 요청 처리 워크플로우는 어떻게 생겼는가
        - 다양한 LLM 모델의 유연성과 확장성을 지원하기 위해 서비스가 내부적으로 어떻게 구성되어 있는지
        - 동시 요청이 어떻게 묶여서 배치 단위로 처리되는지
        - 스트리밍 세대가 내부적으로 어떻게 작동하는가
        - 배칭과 스트리밍이 동일한 시스템에서 어떻게 공존할 수 있는지
        - LLM 서비스에서 주요 성능 병목 현상이 주로 나타나는 곳
    - 이 샘플 서비스가 어떻게 구조화되어 있고 핵심 구성 요소들이 어떻게 조화를 이루는지 고수준에서 파악하기 위해 서비스 아키텍처를 자세히 살펴보겠습니다.
    
- **Service Architecture : 6가지 구성 요소**
    
    !Figure 3-1. Single-model serving system architecture
    
    Figure 3-1. Single-model serving system architecture
    
    - API server : HTTP 요청/응답 처리 (배칭, 스트리밍 엔드포인트)
    - LLM engine: 전체를 지휘하는 오케스트레이터, 마치 오케스트라 지휘자처럼 다른 컴포넌트들을 초기화하고 조율
    - Workload manager: 요청 큐잉과 배치 구성 관리, 어떤 배칭 전략을 적용할지 결정하는 핵심 지점 ← "언제 어떤 요청들을 묶어서 배치로 보낼지"를 결정하는 스케줄링
    - Model executor : 모델 워커 프로세스들을 초기화·관리하고, 프로세스 간 통신으로 추론을 트리거
    - Model worker : 실제 모델 추론을 자신의 별도 프로세스에서 실행
    - Model manager : 모델을 로드하고 캐싱
        
        
    - *초기 구조는 `LLMEngine`이 `ModelExecutor`와 `WorkloadManager`를 갖고, `ModelExecutor`가 worker process를 시작하는 형태다.*
    - 요청 처리 흐름
        
        ```python
        Client → API server → LLM engine → Workload manager → Model executor → Model worker(별도 프로세스)
                                                                                      ↓
        Client ← API server ← LLM engine ← Workload manager ←──── 생성 결과 ────────────┘
        ```
        
        1. API server가 HTTP 요청(생성 요청)을 받아 파싱
        2. LLM engine(지휘자)이 이 요청을 받아 전체 흐름을 조율 — 시작 시점에 모델 로딩을 포함해 모든 컴포넌트를 초기화한 상태
        3. Workload manager가 요청을 큐에 넣고, 현재 대기 중인 프롬프트들의 상태를 추적하다가 "다음 배치로 어떤 프롬프트들을 묶어서 보낼지" 결정 (여기가 배칭 전략이 들어가는 지점)
        4. Model executor가 그 배치를 실제로 실행하도록 Model worker(별도 프로세스)에게 cross-process call로 전달
        5. Model worker가 GPU에서 추론을 실행하고 결과를 반환
        6. 결과가 다시 Model executor → LLM engine → API server를 거쳐 클라이언트로 전달 (배치/스트리밍 여부에 따라 반환 방식이 다름)
        
    - 왜 프로세스를 분리하는지 (핵심 포인트)
        
        !mermaid-diagram.png
        
        - GPU는 비싸고, 놀리면 손해
        - 토크나이징, 전/후처리 같은 CPU 작업이 GPU와 같은 프로세스/스레드에서 돌면 GPU가 그 작업이 끝날 때까지 기다리게 됨
        - 그래서 Model worker = GPU 전용 프로세스로 격리하고, API server/LLM engine = CPU에서 오케스트레이션만 담당하도록 분리 → GPU는 계산에만 집중, CPU는 요청 관리에만 집중 → GPU 활용률(utilization) 극대화
        - *이 구조는 실제로는 규모가 작은 예제에 비해 "과한" 설계처럼 보이지만, 실제 프로덕션 GPU 서빙 시스템의 표준 패턴을 그대로 반영한 것입니다.*
        
    - 아키텍처를 이해했으니, 이제 서비스 구현으로 넘어가겠습니다. 먼저 단일 세대 요청을 처리하는 것부터 시작하고, 이후 점차 배칭과 스트리밍 지원을 추가할 것입니다.
    

`단일 요청`

- **[코드] Single-model serving** : 하나의 서비스가 하나의 모델을 전용으로 실행
    - batching + streaming을 지원하는 단일 모델 서빙 서비스부터 만들고, 이를 일반화한 설계 패턴과 실무적 제약을 짚음.
        
        ```python
        **# facebook/opt-125m(작은 모델, 데모용)을 서빙하는 FastAPI 서비스. 
        # 하나의 모델을 서빙할 때 필요한 구성요소(큐잉, 배칭, 프로세스 격리, 스트리밍)를 최소 형태로 직접 구현해서 보여주는 교육용 코드.
        tree ch03/single_model_llm_serving/**
        ├── llm
        │   ├── __init__.py
        │   ├── **llm.py**
        │   ├── model_executor.py
        │   ├── model_manager.py
        │   ├── model_worker.py
        │   └── workload_manager.py
        ├── **main.py**
        ├── pytest.ini
        ├── **README.md**
        ├── requirements.txt
        └── tests
            ├── test_api.py
            ├── test_stream.sh
            └── test_vllm.py
            
        # 계층 구조
        **main.py** (FastAPI)
          └─ LLMEngine (**llm/llm.py**)              # 오케스트레이션
               ├─ WorkloadManager                # 큐잉/배칭 상태 관리
               └─ ModelExecutor                  # 별도 프로세스와 IPC
                    └─ ModelWorker (별도 process) # 실제 forward pass
                         └─ ModelManager         # 모델/토크나이저 로드
                         
        # 4개 엔드포인트가 있고, 각각 다른 실행 경로를 탑니다:
        ┌──────────────────┬────────────────────────────────────────────────────────────┬───────────────────────────────────────────┐
        │    엔드포인트       │                         실행 경로                            │                 캐싱/배칭                 │
        ├──────────────────┼────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
        │ /basic_generate  │ ModelExecutor → HF model.generate() (1개 시퀀스)             │ HF 내부 KV 캐시 사용                      │
        ├──────────────────┼────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
        │ /generate        │ WorkloadManager 큐 → 최대 4개씩 배치 → HF model.generate()     │ HF 내부 KV 캐시 사용                      │
        ├──────────────────┼────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
        │ /generate_stream │ 별도 스레드의 processing loop → 토큰 1개씩 forward               │ 캐시 없음 (아래 참고)                     │
        ├──────────────────┼────────────────────────────────────────────────────────────┼───────────────────────────────────────────┤
        │ /generate_vllm   │ vllm.LLM 엔진 직접 호출                                       │ vLLM의 PagedAttention/continuous batching │
        └──────────────────┴────────────────────────────────────────────────────────────┴───────────────────────────────────────────┘
        
        # 눈여겨볼 설계 포인트 (의도된 것으로 보이는 것들)
        1. 모델이 사실상 두 벌 로드됩니다: LLMEngine.__init__에서 (a) 별도 프로세스의 transformers 모델과 (b) 메인 프로세스의 vllm.LLM 엔진을 둘 다 초기화합니다(llm.py:20,23). 같은 facebook/opt-125m을 손수 만든 배칭 구현과 vLLM 구현 양쪽에서 나란히 서빙하게 만들어서, 이 장이 강조하는 "직접 만든 것 vs 프레임워크"의 비교 체험을 코드 레벨에서 가능하게 한 구조입니다.
        2. 스트리밍 경로는 KV 캐시를 안 씁니다: model_worker.py:88-93의 generate_forward_batch가 매 토큰마다 use_cache=False로 전체 프롬프트를 처음부터 다시 forward합니다. workload_manager.py:86에서 생성된 토큰을 sequence.prompt += token으로 프롬프트에 이어붙이는 방식이라, 토큰 길이가 늘어날수록 매 스텝의 연산량이 커지는 O(n²) 패턴입니다. ModelWorker.__init__에 stream_states 딕셔너리(request_id -> past_key_values용)가 선언은 돼 있지만 실제로는 전혀 쓰이지 않습니다(model_worker.py:23) — 증분 디코딩으로 확장할 자리를 남겨뒀지만 데모에서는 구현하지 않은 것으로 보입니다. 이 부분은 "제대로 만들면 KV 캐시가 왜 필요한지"를 체감하게 하는 반면교사 역할일 수 있습니다.
        3. 워커 프로세스는 하나뿐, 배치/스트리밍 큐를 공유: ModelExecutor가 task_queue/result_queue 한 쌍과 워커 프로세스 1개만 띄우고(model_executor.py:17-20), /generate(배치)와 /generate_stream(스트리밍)이 같은 워커에 순차적으로 작업을 던집니다. 즉 배치 요청과 스트리밍 요청이 GPU/CPU 연산 자원을 놓고 직렬로 경쟁합니다 — 실제 단일 모델 서버에서 흔히 겪는 리소스 경합 문제를 그대로 재현합니다.
        4. 배칭은 고정 크기 폴링 방식: WorkloadManager.batch_size = 4(workload_manager.py:23)로 고정, get_next_batch()가 큐에서 최대 4개까지 채워서 반환합니다. vLLM의 continuous batching(요청이 끝나는 즉시 슬롯 교체)과 달리, 여기서는 활성 배치가 다 끝나야 다음 배치로 넘어가는(generate()의 while 루프가 _is_batch_finished를 기다림) 정적 배칭에 가깝습니다.
        5. 프로세스 격리: 실제 추론은 mp.Process로 뜬 별도 프로세스(ModelWorker.run)에서 실행되고 메인 API 프로세스와는 multiprocessing.Queue로만 통신합니다. 모델 크래시가 API 프로세스를 죽이지 않도록 하는 격리 패턴 — README가 강조하는 "Reliability" 포인트.
        
        # 사소한 코드 관찰
        - main.py:16의 _llm_lock = multiprocessing.Lock()은 사실 단일 asyncio 프로세스 내 지연 초기화를 막는 용도라 threading.Lock이면 충분한데, 크게 문제 되진 않습니다.
        - model_worker.py:118-119에 "Waiting for debugger to attach..." 로그가 있는데 실제 debugpy 연결 코드는 없음 — 디버깅 실험 흔적으로 보이는 죽은 로그 문구.
        - requirements.txt에 vllm==0.9.0.1, torch==2.7.0 고정 — 실제 실행 환경 재현 시 이 버전으로 맞추는 게 안전합니다.
        
        # 테스트
        tests/에 test_api.py(FastAPI 엔드포인트), test_vllm.py(vLLM 경로), test_stream.sh(curl 기반 스트리밍 수동 테스트)가 있고 pytest-asyncio로 비동기 테스트를 지원합니다.
        
        # 한 줄 요약: 이 디렉토리는 "제대로 된 서빙 시스템에 필요한 모든 구성요소(큐잉/배칭/프로세스 격리/스트리밍)를 최소 구현으로
        # 보여주되, 의도적으로 비효율적인 스트리밍 경로(캐시 를 나란히 두어 왜 vLLM 같은 프레임워크가 필요한지체감시키는" 교육용 레퍼런스입니다.
        
        ```
        
    - 단일 요청 처리 과정 : rompt 하나를 받아 결과 전체를 반환
        
        ```python
        POST /basic_generate
        {
          "prompt": "Hello, I am"
        }
        ```
        
        !mermaid-diagram (1).png.png)
        
    - 문제점 : Prompt 1 처리 완료 → Prompt 2 처리 → Prompt 3 처리
        - GPU가 한 번에 하나의 Prompt만 처리하므로 처리량이 낮습니다.
    
- **[설명] Implement Single Generation Request Handling**
    - **초기화 단계 (서비스 시작 시 1회)**
        
        ```python
        LLMEngine.__init__()
          → ModelExecutor() 생성 (task_queue, result_queue 두 개의 mp.Queue 생성)
          → WorkloadManager() 생성
          → model_executor.setup_worker("facebook/opt-125m")
                → mp.Process로 ModelWorker.run()을 별도 프로세스로 실행
                → 그 프로세스 안에서 ModelManager가 HuggingFace에서 모델+토크나이저 로드
        ```
        
        - task_queue / result_queue가 핵심입니다 : 별도 프로세스인 API 서버(부모)와 model worker(자식) 프로세스가 서로 직접 함수를 호출할 수 없기 때문에, 프로세스 간 통신(IPC) 을 큐로 구현한 것입니다.
        - ModelWorker.run()은 자식 프로세스에서 무한 while True 루프를 돌며 task_queue.get()으로 블로킹 대기 → 요청이 오면 처리 → result_queue.put()으로 결과 반환
        
    - First, initialize the core components in the `LLMEngine` class: facebook/opt-125m (GPT-3 성능 수준, 디코더 전용 모델) - HF-Link
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        class LLMEngine:
           def __init__(self):
               self.model_executor = ModelExecutor()
               self.workload_manager = WorkloadManager()
               self.max_tokens = 20
        
        self.model_executor.setup_worker("**facebook/opt-125m"**)
        ```
        
    - ModelWorker와 ModelExecutor 클래스를 설정 : 하나의 ModelWorker를 별도의 프로세스에서 실행
        
        ```python
        # ch03/single_model_llm_serving/llm/model_executor.py
        
        class ModelExecutor:
           def __init__(self):
               self.task_queue = mp.Queue()
               self.result_queue = mp.Queue()
        
           def setup_worker(self, model_name: str):
               self.worker_process = mp.Process(
                   target=ModelWorker.run,
                   args=(model_name, self.task_queue, self.result_queue)
               )
               self.worker_process.start()
        ```
        
        - 모델 실행기는 두 개의 이벤트 큐를 사용해 워커와 통신합니다:
        - task_queue 작업 큐와 result_queue  결과 큐: 작업자는 작업 큐를 통해 프롬프트 요청을 보내고, 결과 큐로부터 생성 결과를 받습니다
        
    - ModelManager의 도움을 받아 AutoModelForCausalLM 클래스를 사용해 Hugging Face에서 facebook/opt-125m 모델을 로드하는 ModelWorker를 준비
        
        ```python
        # ch03/single_model_llm_serving/llm/model_worker.py
        
        class ModelWorker:
           def __init__(self, model_name: str):
               self.device = "cuda" if torch.cuda.is_available() else "cpu"
               logger.debug(f"Loading model {model_name} on device {self.device}")
               self.model, self.tokenizer = ModelManager().load_model(model_name)
        ```
        
        ```python
        # ch03/single_model_llm_serving/llm/model_manager.py
        
        class ModelManager:
           def load_model(self, model_name: str = "facebook/opt-125m"):
               model = AutoModelForCausalLM.from_pretrained(model_name)
               tokenizer = AutoTokenizer.from_pretrained(model_name)
               return model, tokenizer
        ```
        
    - ModelWorker는 자체 프로세스에서 while 루프를 실행하며(다음의 run 함수를 참고), 이 루프는 task_queue를 지속적으로 감시합니다.
    - 요청이 큐에 도착하면, 작업 큐에서 프롬프트를 가져와 모델 추론을 수행한 뒤 생성 결과를 결과 큐에 넣습니다.
        
        ```python
        # ch03/single_model_llm_serving/llm/model_worker.py
        
        class ModelWorker:
           @staticmethod
           def run(model_name: str, task_queue: mp.Queue, result_queue: mp.Queue):
               worker = ModelWorker(model_name)
               while True:
                   request = task_queue.get()
                   result_queue.put(("complete", worker.generate(request)))
        ```
        
    - 코드 실행 워크플로우
        
        !Figure 3-2. Single generation request의 model serving workflow
        
        Figure 3-2. Single generation request의 model serving workflow
        
    - 요청 1건 처리 흐름 (/basic_generate)
        
        ```python
        Client
         → API server: POST /basic_generate {prompt: "..."}
         → LLMEngine.basic_generate(prompt)
              → Sequence 객체 생성 (요청을 고유 id로 추적)
              → ModelExecutor.execute(sequence)
                   → task_queue.put((prompt, ...))    # 자식 프로세스로 전달
                   → result_queue.get()               # 결과 올 때까지 블로킹 대기
                        (이 사이 자식 프로세스에서:
                         ModelWorker.run() → task_queue.get()
                                           → worker.generate(prompt)  # model.generate() 실제 추론
                                           → result_queue.put(('complete', 결과)))
        ```
        
    - ***아래 책 설명에 코드와 Repo 코드에 일부 차이가 있음.***
        
        
    - FastAPI endpoint는 prompt를 받고 `LLMEngine.basic_generate()`를 호출한다.
        - 먼저 웹 API인 basic_generate 엔드포인트를 정의하는 것부터 시작합니다.
        - 이 엔드포인트는 요청 페이로드로 단일 프롬프트를 받아 생성된 텍스트를 일반 문자열로 반환합니다:
        
        ```python
        # ch03/single_model_llm_serving/main.py
        
        @app.post("**/basic_generate**", response_model=GenerateResponse)
        async def basic_generate(
            request: GenerateRequest,
            llm: LLMEngine = Depends(get_llm)
        ):
           generated_text = llm.basic_generate(request.prompt)
           return GenerateResponse(generated_text=generated_text)
        
        class GenerateRequest(BaseModel):
           prompt: str
        
        class GenerateResponse(BaseModel):
           generated_text: str
        ```
        
    - 다음으로 LLMEngine에서 오케스트레이션 로직을 구현합니다. 먼저, basic_generate 함수가 프롬프트를 ModelExecutor에 전달합니다.
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        class LLMEngine:
           # process 1 request with only one prompt at a time.
           def basic_generate(self, prompt: str) -> str:
               sequence = Sequence(str(uuid.uuid4()), prompt, None, None)
               # Execute the batch
               results = self.model_executor.execute(sequence)
               return results[0]["generated_text"]
        ```
        
    - 그 후 ModelExecutor는 작업 큐를 통해 프롬프트를 ModelWorker에 전달합니다.
    - ModelExecutor가 result_queue로부터 생성된 결과를 받으면, 그 결과를 LLMEngine에 반환하고, LLMEngine은 이를 웹 API로 다시 전달합니다:
        
        ```python
        # ch03/single_model_llm_serving/llm/model_executor.py
        
        class ModelExecutor:
           def execute_batch(self, prompt: str):
               # Send prompt to the ModelWorker’s task queue
               self.task_queue.put((prompts, False))
               # Collect generation results from ModelWorker
               results = self.result_queue.get()
               return results
        ```
        
    - 마지막으로 ModelWorker 내에서 추론 로직을 구현합니다.
    - ModelWorker는 실행 함수에서 task_queue로부터 요청을 받아 모델을 생성하고, 결과를 result_queue를 통해 ModelExecutor에 전달합니다:
        
        ```python
        class ModelWorker:
           def generate(self, prompt: str):
               # Run model inference, model is loaded during service initialization
               outputs = self.model.generate(...) 
               # Decode all outputs
               generated_text = self.tokenizer.decode(outputs[0], …)
               # Map results back to request IDs
               return {
                   'request_id': prompt_data.id,
                   'generated_text': generated_text
               }
           @staticmethod
           def run(model_name: str, task_queue: mp.Queue, result_queue: mp.Queue):
               … …
               request = task_queue.get()  # Fetch generation(prompt) task 
               # Return result to ModelExecutor
               result_queue.put(('complete', worker.generate(request)))
        ```
        
    - 이로써 온라인 모델 서빙 서비스의 첫 번째 버전이 완료되었습니다.
    - 2장에서 살펴본 LLM 모델 실행과 비교해 보면, 모델 서빙 서비스가 웹 인터페이스를 통해 모델 추론을 노출하는 효율적인 소프트웨어 구축에 중점을 둔다는 것을 알 수 있습니다.
    
- **[실습1] 서버 기동, 단일 요청 처리 확인**
    - 실행 계획 by 클로드코드
        
        ```python
        1. 가상환경 생성
        cd ch03/single_model_llm_serving
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        
        2. 의존성 관련 주의점
          - torch==2.7.0 + vllm==0.9.0.1이 명시적으로 고정돼 있는데, vLLM은 설치 시 자기 요구 버전의 torch를 끌고 오려는 경우가 있어 버전 충돌 가능성이 있습니다 → 설치 로그를 확인하고 문제 생기면 알려드리겠습니다.
          - GPU는 감지됩니다 (RTX 4070 Ti SUPER), 이 환경에서 torch.cuda.is_available()이 True가 되어 ModelWorker가 GPU를 사용하도록 동작할 겁니다.
          - facebook/opt-125m 모델을 HuggingFace에서 다운로드해야 하므로 네트워크 접근이 필요합니다 (최초 1회, 캐시됨).
        
        3. 구조상 눈에 띄는 점 (버그는 아니지만 리소스 사용 관점에서 알아두면 좋은 부분)
          - LLMEngine.__init__에서 facebook/opt-125m을 두 번 로드합니다: transformers 기반 ModelExecutor(별도 프로세스) + vLLM 엔진(self.vllm_model) 각각 따로. /basic_generate, /generate, /generate_stream은 앞의 경로를, /generate_vllm은 뒤의 경로를 씁니다. 두 경로를 비교 학습하려는 책의 의도로 보이나, 서비스 기동 시 GPU 메모리를 이중으로 씁니다.
        
        4. 검증 순서
          - 먼저 서버를 수동으로 띄워 임포트/모델 로딩이 정상 동작하는지 확인 (python main.py)
          - pytest tests/test_api.py -v — basic/batch/streaming(단일+동시) 테스트
          - pytest tests/test_vllm.py -v — vLLM 경로 테스트
          - 필요시 tests/test_stream.sh로 curl 기반 스트리밍도 별도 확인
        ```
        
    - 가상 환경 생성
        
        ```python
        **cd ch03/single_model_llm_serving**
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        
        **cat requirements.txt**
        setuptools==77.0.3
        **fastapi==0.115.12**
        uvicorn==0.24.0
        pydantic==2.11.5
        **transformers==4.52.4**
        **torch==2.7.0**
        numpy==1.26.4
        debugpy==1.8.0
        pytest==8.4.0
        httpx==0.27.0
        pytest-asyncio==1.0.0
        ```
        
    - 서버 수동 기동
        
        !스크린샷 2026-08-05 오전 3.33.11.png
        
        ```mermaid
        flowchart LR
            Client["curl / pytest"] -->|HTTP| API["FastAPI main.py"]
            API --> Engine[LLMEngine]
            Engine -->|수동 배칭| WM["WorkloadManager<br/>Sequence, FIFO batch_size=4"]
            WM --> ME["ModelExecutor<br/>mp.Process IPC"]
            ME --> MW["ModelWorker<br/>transformers, use_cache=False"]
            Engine -->|vLLM 통합| VLLM["vllm.LLM<br/>동기 generate() 호출"]
            MW --> GPU[("RTX 4070 16GB")]
            VLLM --> GPU
        ```
        
        ```python
        # uvicorn.run(app, host="0.0.0.0", port=8000): 8000 포트 리슨
        venv/bin/**python main.py**
        *...
        model.safetensors: 100%|███████████████████████████████████████████████████████████████████████| 251M/251M [00:08<00:00, 30.0MB/s]
        INFO 08-04 18:45:29 [gpu_model_runner.py:1933] Graph capturing finished in 8 secs, took 0.19 GiB
        INFO 08-04 18:45:29 [core.py:167] init engine (profile, create kv cache, warmup model) took 15.36 seconds
        INFO:     Started server process [25603]
        INFO:     Waiting for application startup.
        INFO:     Application startup complete.
        INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)*
        
        # 8000 포트 리슨 확인
        **ss -tnlp | grep 8000**
        LISTEN 0      2048           0.0.0.0:8000       0.0.0.0:*    users:(("python",pid=25603,fd=50))
        
        # 기동 시 프로세스 정보 확인
        **ps auxf | tail -n 3**
        *root       **30195**  0.6  1.2 5730140 814568 ?      Sl   18:55   0:06  \_ venv/bin/**python main.py**
        root       **30237**  0.3  1.9 13622100 1249116 ?    Sl   18:55   0:03      \_ venv/bin/python main.py
        root       **30323**  2.5  2.2 27726008 1436600 ?    Sl   18:55   0:23      \_ venv/bin/python main.py*
        **python(30195)**  ← 부모: uvicorn + FastAPI 메인 프로세스, 직접 실행해서 뜬 프로세스, 아래 두 자식 프로세스를 순서대로 기동
         ├─ python(30237)  ← 자식 1: **ModelExecutor**가 띄운 **ModelWorker** (transformers 경로) - (GPU 메모리 788MB)
         └─ python(30323)  ← 자식 2: **vLLM** 엔진의 EngineCore 프로세스 - (GPU 메모리 13.7GB)
        
        # 30237 — ModelWorker (GPU 메모리 788MB)
        - ModelExecutor.setup_worker()가 mp.Process(target=ModelWorker.run, ...)로 띄운 프로세스입니다.
        - 방금 고친 transformers 기반 경로: task_queue에서 요청을 받아 model.generate()로 추론하고 result_queue로 결과를 돌려줍니다.
        - /basic_generate, /generate, /generate_stream이 이 프로세스를 씁니다.
        - 메모리가 작은 이유: facebook/opt-125m은 파라미터 1.25억 개짜리 작은 모델이라 fp32로 올려도 GPU 메모리를 많이 안 씁니다.
        
        # 30323 — vLLM EngineCore (GPU 메모리 13.7GB)
        - LLMEngine.__init__의 self.vllm_model = VLLM(model="facebook/opt-125m") 호출로 생성됩니다.
        - vLLM 0.9(V1 아키텍처)는 TP=1(단일 GPU)이어도 실제 모델 실행을 별도 프로세스(EngineCore) 로 분리하는 구조라서, main.py 프로세스와는 다른 PID로 뜹니다.
        - /generate_vllm이 이 경로를 씁니다.
        - 메모리가 큰 이유:  vLLM이 의도적으로 GPU 메모리를 미리 통째로 예약(0.9=90%), 로그에 찍힌 대로 gpu_memory_utilization 기본값(0.9)에 따라 KV 캐시를 위해 GPU 메모리를 넉넉히 선점해두기 때문입니다(GPU KV cache size: 356,816 tokens) — 모델 자체 가중치는 0.24GiB뿐입니다.
        
        # 부모 프로세스는 GPU 를 사용하지 않음
        **nvidia-smi**
        +-----------------------------------------------------------------------------------------+
        | NVIDIA-SMI 595.84                 Driver Version: 595.84         CUDA Version: 13.2     |
        +-----------------------------------------+------------------------+----------------------+
        | GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
        | Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
        |                                         |                        |               MIG M. |
        |=========================================+========================+======================|
        |   0  NVIDIA GeForce RTX 4070 ...    Off |   00000000:01:00.0  On |                  N/A |
        |  0%   38C    P8             13W /  285W |   14581MiB /  16376MiB |      0%      Default |
        |                                         |                        |                  N/A |
        +-----------------------------------------+------------------------+----------------------+
        
        +-----------------------------------------------------------------------------------------+
        | Processes:                                                                              |
        |  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
        |        ID   ID                                                               Usage      |
        |=========================================================================================|
        |    0   N/A  N/A           **30237**      C   venv/bin/python                         **788MiB** |
        |    0   N/A  N/A           **30323**      C   venv/bin/python                       **13762MiB** |
        +-----------------------------------------------------------------------------------------+
        
        ```
        
    - 이제 몇 가지 테스트 케이스를 사용해 basic_generate API가 예상대로 작동하는지 확인할 수 있습니다:
        
        !Figure 3-2. Single generation request의 model serving workflow
        
        Figure 3-2. Single generation request의 model serving workflow
        
        - `/basic_generate` endpoint에 prompt 보내기
        
        ```python
        #
        **curl -s -X POST http://localhost:8000/basic_generate \
          -H "Content-Type: application/json" \
          -d '{"prompt": "Hello, I am"}' | jq**
        {
          "generated_text": "Hello, I am **a student at the University of California, Berkeley. I am a graduate student in the Department of Psychology. I am a graduate student in the Department of Psychology. I am a graduate student in the Department of Psychology. I am a graduate student in the**"
        }
        ```
        
    - 이 서비스를 그대로 운영하면 **가장 먼저 마주하게 될 문제는 낮은 처리량**입니다.
    - 현재 추론 서비스에서는 사용자가 한 번에 하나의 프롬프트만 보낼 수 있으며, **모델 워커는 추론 호출당 하나의 프롬프트만 처리**합니다.
    - "LLM 배치 서빙 기초"에서 배웠듯이, LLM은 여러 프롬프트를 한 번에 처리하는 배치 방식에 적합하기 때문에 컴퓨팅 자원이 충분히 활용되지 않고 있습니다.
    - 다음 섹션에서는 처리량을 크게 향상시킬 **배칭 지원**을 위해 서비스를 업그레이드할 것입니다.
    

`배치 요청`

- **[코드/설명] Batching :** 여러 prompt를 묶어 한 번에 model worker로 보내 GPU utilization을 높이는 방식
    - 이제 새로운 생성 API를 사용해 배칭 Batching 을 구현해 보겠습니다.
    - 이 API는 하나의 예측 요청에 프롬프트 목록을 입력받고, 입력 배열과 동일한 순서(프롬프트 기준)로 생성된 텍스트 목록을 반환합니다
    - Batch API는 여러 prompt를 받는다.
        
        ```python
        # ch03/single_model_llm_serving/main.py
        
        # process multiple prompts in a request
        @app.post("**/generate**", response_model=BatchGenerateResponse)
        async def generate(request: BatchGenerateRequest):
           generated_texts = llm.generate(request.prompts)
           return BatchGenerateResponse(generated_texts=generated_texts)
        
        class BatchGenerateRequest(BaseModel):
           prompts: List[str]
        
        class BatchGenerateResponse(BaseModel):
           generated_texts: List[str]
        ```
        
    - **필요 이유**
        - **LLM과 GPU**는 **여러 Prompt를 함께 처리할 때 더 효율**적인 경우가 많습니다.
        - 예를 들어 요청이 다음과 같이 들어왔다고 하겠습니다.
            
            ```
            Request 1:
            - Prompt A
            - Prompt B
            
            Request 2:
            - Prompt C
            - Prompt D
            - Prompt E
            ```
            
        - 서버는 사용자 **요청 경계를 그대로 따르지 않고, Prompt들을 다시 묶을 수** 있습니다.
            
            ```
            Batch 1: A, B, C, D
            Batch 2: E
            ```
            
        - 이를 통해 GPU 행렬 연산을 더 크게 만들고 자원 활용률을 높입니다.
        
    - API를 염두에 두고, 구현하기 전에 배칭의 일반적인 개념에 대해 이야기해 보겠습니다.
    - **두 개의 요청**을 받았다고 가정해 봅시다.
    - **요청1**에는 두 개의 프롬프트(promptA와 promptB)가 있고, **요청2**에는 세 개의 프롬프트(promptC, promptD, promptE)가 포함되어 있습니다.
        
        !Figure 3-3. Service design에서 batching이 처리되는 방식
        
        Figure 3-3. Service design에서 batching이 처리되는 방식
        
    - 서비스에서 이 **두 요청을 처리하려면 두 가지 핵심 과제를 해**결해야 합니다.
        - 첫째, 서로 **다른 요청들의 프롬프트를 몇 개의 배치로 합쳐서 LLM이 요청별이 아니라 큰 배치 단위로 프롬프트를 실행**할 수 있게 해야 자원 활용도를 극대화할 수 있습니다.
        - 둘째, **생성된 출력물을 원래 요청과 정확히 연결해 서비스가 올바른 순서로 적절한 사용자에게 결과를 돌려**줄 수 있어야 합니다.
            - *여러 요청의 Prompt를 섞어서 실행하려면, 생성 결과가 어느 요청의 것인지 반드시 기억해야 합니다.*
            - *각 Prompt를 `Sequence` 객체로 감쌉니다.*
                
                ```python
                Sequence
                ├─ 고유 ID
                ├─ Prompt
                ├─ 생성 결과
                ├─ 완료 여부
                ├─ 토큰 수
                └─ Streaming Queue
                
                # 예
                A → seq-101
                B → seq-102
                C → seq-103
                ```
                
            - *모델 결과도 ID와 함께 반환합니다. 그 후 ID를 이용해 원래 순서로 다시 정리합니다.*
                
                ```python
                seq-103 → Generated Text C
                seq-101 → Generated Text A
                seq-102 → Generated Text B
                ```
                
            - *이 구조가 중요한 이유는 웹 요청과 실제 GPU 실행 순서를 분리할 수 있기 때문입니다.*
            - *덕분에 Dynamic Batching, Priority Scheduling, Continuous Batching 같은 최적화를 적용할 수 있습니다.*
    - 그림 3-3은 그림 3-2의 단일 요청 서비스 아키텍처를 확장한 우리의 업데이트된 설계를 보여줍니다.
    - 배칭을 지원하기 위해 이번 버전에서는 **각 프롬프트마다 Sequence**라는 **추적 데이터 구조**와 **WorkloadManager라는 새로운 컴포넌트**를 도입했으며, LLM 엔진에 추가적인 역할을 부여했습니다.
        
        ```python
        # Workload Manager는 요청을 관리하는 대기실입니다.
        # 주요 자료구조
        incoming_queue → 새로 들어온 Sequence 대기
        active_sequences → 현재 GPU Batch에 포함된 Sequence
        sequence_map → ID로 Sequence 조회
        ```
        
    - 서비스 설계에서 배칭이 어떻게 처리되는지를 보여주는 다이어그램으로, API 서버, 워크로드 매니저, LLM 엔진, 모델 실행기 간의 상호작용을 통해 여러 프롬프트를 효율적으로 처리하는 과정을 나타냅니다.
    - 그림 3-3의 순서를 따라 도표에 있는 숫자를 사용하여 시스템이 두 개의 들어온 생성 요청과 그에 따른 여러 프롬프트를 어떻게 처리하는지 확인하세요:
        1. ***Request intake*** 접수 요청하기
            - API 서버는 요청을 받아 각 페이로드에서 개별 프롬프트를 추출합니다.
        2. ***Prompt queuing*** 프롬프트 큐잉
            - API 서버는 요청을 LLM 엔진에 전달하고, LLM 엔진은 이를 워크로드 매니저로 전달합니다.
        3. ***Prompt tracking and batching*** 프롬프트 추적 및 배칭
            - 워크로드 매니저는 **각 프롬프트에 고유 ID를 부여**하고 이를 **시퀀스 객체**로 감쌉니다.
            - 워크로드 매니저는 **모든 활성 시퀀스를 메모리 내에서 추적**하며, 어떤 **프롬프트를 다음 처리 배치**로 묶어야 할지 결정합니다.
        4. ***Batch execution*** 배치 실행
            - LLM 엔진은 워크로드 매니저로부터 **다음 프롬프트 배치**를 가져와 **모델 실행기와 워커에 전달하여 추론을 수행**합니다.
        5. ***Model inference*** 모델 추론
            - 모델 워커는 **한 번의 추론 호출로 전체 배치를 처리**하고, 생성된 **텍스트와 각 프롬프트 ID를 쌍으로 반환**합니다.
        6. ***Response mapping*** 응답 매핑
            - LLM 엔진은 **프롬프트 ID**를 사용해 **생성된 각 텍스트를 원래의 웹 요청과 연결**합니다.
            - 이를 통해 생성된 출력을 올바르게 반환할 수 있는데, 예를 들어 GenTextA와 GenTextB를 request1에, GenTextC, GenTextD, GenTextE를 request2에 매핑하는 식입니다.
        
    - 실제 코드 흐름 (ch03/single_model_llm_serving/llm/)
        1. **Sequence (workload_manager.py:6-14)**
            - 프롬프트 하나의 생명주기를 담는 객체. id, prompt, output(생성된 토큰들), finished 상태를 가짐.
        2. **WorkloadManager.add_request (workload_manager.py:27-32)**
            - uuid로 요청 ID를 발급하고 Sequence를 만들어 incoming_queue(FIFO)에 넣고, 동시에 sequence_map이라는 딕셔너리(id → Sequence)에도 등록합니다. 이 맵이 나중에 ‘ID로 결과 찾기의 핵심입니다.
        3. **WorkloadManager.get_next_batch (workload_manager.py:42-54)**
            - active_sequences가 batch_size(4개) 미만이고 대기 큐에 남은 게 있으면 큐에서 꺼내 채웁니다.
            - 즉 이미 실행 중인 배치에 빈 자리가 생겨야 다음 프롬프트가 들어감 — FIFO + 고정 배치 크기 방식.
        4. **LLMEngine.generate (llm.py:92-121)** 실제로 이렇게 동작합니다:
            
            ```python
            def generate(self, prompts):
                request_ids = [self.workload_manager.add_request(p) for p in prompts]  # 등록
                while not self._is_batch_finished(request_ids):               # 내 요청의 모든 프롬프트가 끝날 때까지
                    sequences = self.workload_manager.get_next_batch()        # 다른 요청 프롬프트와 섞인 배치일 수 있음
                    results = self.model_executor.execute_batch(sequences)    # 실제 추론 (별도 프로세스)
                    for result in results[1]:
                        self.workload_manager.update_sequence_output(result['request_id'], result['generated_text'], is_finished=True)
                return [self.workload_manager.get_sequence(rid).output[0] for rid in request_ids]  # ID로 결과 매핑
            ```
            
        - 등록(3단계) → 배치 실행(4단계) → 모델 추론(5단계, ModelExecutor.execute_batch가 별도 프로세스인 ModelWorker로 던짐) → ID로 응답 매핑(6단계).
        
    - 이 워크플로우를 염두에 두고, 각 프롬프트가 어떻게 추적되는지와 어떤 프롬프트를 배치에 넣을지 결정하는 방법부터 핵심 구현을 살펴보겠습니다(예제 3-1).
    - `WorkloadManager`는 prompt마다 `Sequence`를 만들고 FIFO 방식으로 batch를 구성한다.
    - **Example 3-1. Workload manager batch scheduling implementation**
        
        ```python
        # ch03/single_model_llm_serving/llm/workload_manager.py
        
        class Sequence:
           def __init__(self, seq_id: str, prompt: str, client_stream, loop):
               self.id = seq_id
               self.prompt = prompt
               self.output = []
        
        **class WorkloadManager:**
           **self.batch_size = 4**   # Process up to 4 sequences at a time
           
           # for basic generate and batch generate  
           def add_request(self, prompt: str) -> str:
               request_id = str(uuid.uuid4())
               sequence = Sequence(request_id, prompt, None, None)
               self.incoming_queue.put(sequence)
               self.sequence_map[request_id] = sequence
               return request_id
        
           def **get_next_batch**(self) -> List[Sequence]:
               while len(self.active_sequences) < self.batch_size \
                     and not self.incoming_queue.empty():
                  sequence = self.incoming_queue.get()
                  self.active_sequences.append(sequence)
               return self.active_sequences
        ```
        
        - **get_next_batch** 함수의 두 가지 핵심 부분을 강조하고자 합니다.
        - 첫째, 워크로드 매니저는 선입선출(FIFO) 전략을 사용해 다음 배치에 선택할 프롬프트를 결정합니다.
        - 둘째, 최대 배치 크기를 제한해 LLM이 한 번에 최대 네 개의 프롬프트를 처리할 수 있도록 했습니다.
        
    - (참고) 배치 내 처리량 최적화 : 처리량과 개별 사용자 지연시간 사이에서 균형을 찾아야 함!
        - *Batching 최적화에서 중요한 것은 batch size만 크게 만드는 것이 아니다.*
        - *throughput은 좋아질 수 있지만, 각 request의 queue time과 latency가 늘어날 수 있다.*
        - *Production에서는 max batch size, max batched tokens, timeout, request priority를 함께 봐야 한다.*
        - 실제로 배치 크기와 배칭 전략은 추론 처리량에 큰 영향을 미칩니다.
        - 적절한 배치 구성을 선택하려면 세심한 조정이 필요하며, 이 단순화된 예시보다 훨씬 복잡합니다.
        - 이 설정들은 특정 LLM 모델, 프롬프트 특성, 웹 트래픽의 성격, 그리고 모델이 실행되는 하드웨어에 따라 자주 조정되어야 합니다.
        
    - 이 예제에서는 직관을 키우기 위해 간단한 FIFO 배칭 전략을 사용했지만, **동적 배칭 dynamic batching** 이나 **연속 배칭 continuous batching** 같은 배칭 최적화 기법을 더 깊이 탐구하려면 **6장과 7장**을 참고하세요.
        
        
    - 이제 LLMEngine에서 배치 **응답 매핑**을 구현하는 방법(예제 3-2)을 살펴보겠습니다.
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        class LLMEngine:
        
           # process multiple prompts in a request
           def generate(self, prompts: List[str]) -> List[str]:
           
               # Register prompt to workload manager Track the prompt ID, assigned by workload manager
               prompt_ids = []          *# Repo 코드에는 request_ids = [] 되어 있음. 책 실습 코드 표현이 오타..*
               for prompt in prompts:
                   prompt_id = self.workload_manager.add_request(prompt)
                   prompt_ids.append(prompt_id)
        
               # Keep executing batches until all prompts in the requests are completed.
               while not self._is_batch_finished(prompt_ids):
                   sequences = self.workload_manager.get_next_batch()
                   results = self.model_executor.execute_batch(sequences)
                   self.workload_manager.update(results)
         
               # Get generated result by using prompt_id
               generated_texts = []
               for prompt_id in prompt_ids:
                   generated_texts.append(
                       self.workload_manager.get_sequence(prompt_id).output[0]
                   )
                   self.workload_manager.remove_finished_sequence(prompt_id)
        
               return generated_texts
        ```
        
        - LLMEngine의 생성 함수에서 보듯이, generate 로직은 **먼저 generate 요청과 관련된 모든 prompt_ids를 수집**합니다.
        - 그 후 이 I**D들을 사용해 해당하는 생성된 텍스트를 불러**옵니다. 모든 프롬프트에 대한 결과가 모두 준비된 후에야 기능이 완료됩니다.
        - **배칭은 일부 요청이 대기해야 하므로 개별 요청에 지연이 발생할 수 있지만, 요청 간 자원 활용을 최적화해 전체 서비스 처리량을 크게 향상시킵니다.**
        
    - 배칭 로직을 구현했으니, 다음 테스트 코드를 사용해 구현이 제대로 되었는지 확인하세요:
        - Batch 테스트는 여러 prompt를 `/generate`로 보내는 형태다.
        
        ```python
        def test_generate_batch(client):
           test_prompts = [
               **"Hello, I am",
               "The weather is",
               "I want to",
               "The best way to",
               "The most efficient way to"**
           ]
        
           response = client.post(
               "/generate",
               json={"prompts": test_prompts}
           )
        ```
        
    - 모든 프롬프트 실행 추적하기
        - 각 프롬프트를 개별적으로 추적하는 것은 LLM 서비스에서 흔히 사용되는 기법입니다.
        - 이는 사용자의 웹 요청과 실제 모델 실행을 분리하여, 시스템이 프롬프트를 재구성해 백엔드에서 더 효율적으로 처리할 수 있도록 합니다.
        - 이러한 추상화는 서빙 서비스가 동적 배치와 우선순위 지정(6장에서 다룸) 같은 최적화 기법을 유연하게 적용할 수 있도록 합니다
        - 이 예시에서 사용자 요청의 각 프롬프트는 시퀀스 객체(예제 3-1에 나타난 것처럼)로 변환되며, 이는 LLM 실행 작업 부하를 관리하는 기본 단위가 됩니다.
        
    - 특징 : 트레이드오프
        - execute_batch는 **동기 호출**(model_executor.py:33-46)
            - task_queue.put() 후 result_queue.get()으로 블로킹 대기. 즉 워커 프로세스가 배치를 다 처리할 때까지 이 스레드가 멈춥니다.
        - **다른 요청과 섞임**
            - get_next_batch()가 반환하는 배치는 "내가 요청한 프롬프트들"이 아니라 큐에 쌓인 아무 프롬프트 4개입니다.
            - 그래서 내 프롬프트 2개가 다른 유저 요청과 같은 배치에 섞여 처리될 수 있음
                - 이게 배치 처리의 핵심(자원 공유)이자, 지연시간이 요청마다 들쭉날쭉해지는 이유(레이턴시 vs 처리량 트레이드오프)입니다.
        - **FIFO + 고정 배치 크기라 최적은 아님**
            - 4장/6장/7장에서 다룰 continuous batching, dynamic scheduling으로 개선되는 지점입니다.
        
    - 여기서 보여주는 배칭 구현은 의도적으로 단순화된 것입니다.
    - 그 목적은 요청 그룹화 로직과 실행 흐름을 명확히 하는 것이지, 완전히 최적화된 운영 시스템을 구현하는 것이 아닙니다.
    - 실제 서버 프레임워크에서는 배칭이 더 복잡합니다.
    - 프로덕션 시스템은 연속 배치, 동적 스케줄링, 메모리 효율적인 KV 캐시 관리(6장에서 다룰 예정) 같은 기법을 사용해 GPU 활용도를 극대화하면서 지연 시간을 제어합니다.
    - 예를 들어, vLLM의 연속 배칭은 새로운 요청이 활성 디코딩 배치에 참여할 수 있게 해, 고정된 배치가 완료되기를 기다리지 않고도 처리량을 향상시킵니다.
    - 이 구현은 개념적인 기반으로 생각할 수 있습니다.
    - 이 기본 설계를 이해하면, vLLM 같은 최적화된 서빙 엔진이 실제로 이러한 개념을 어떻게 확장하고 다듬는지 더 잘 알 수 있을 것입니다.
    
- **[실습2] Batching 요청**
    
    !Figure 3-3. Service design에서 batching이 처리되는 방식
    
    Figure 3-3. Service design에서 batching이 처리되는 방식
    
    - test_prompts 5개를 그대로 JSON body에 담아 /generate로 POST
        
        ```python
        # Batching 요청 : 5개 프롬프트 - 처음 4개 배치 실행 -> 남은 1개 배치 실행.
        **curl -s -X POST http://localhost:8000/generate \
          -H "Content-Type: application/json" \
          -d '{
            "prompts": [
              "Hello, I am",
              "The weather is",
              "I want to",
              "The best way to",
              "The most efficient way to"
            ]
          }' | jq**
        *{
          "generated_texts": [
            "Hello, I am a student at the University of California, Berkeley. I am a graduate student in the Department of Psychology. I am a graduate student in the Department of Psychology. I am a graduate student in the Department of Psychology. I am a graduate student in the",
            "The weather is, of course, a factor in the weather.\n\nThe weather is a factor in the weather.\n\nThe weather is a factor in the weather.\n\nThe weather is a factor in the weather.\n\nThe weather is a factor",
            "I want toand I want to be a part of this.\nI want to be a part of this.\nI want to be a part of this.\nI want to be a part of this.\nI want to be a part of this.",
            "The best way to get a job is to get a job.                                         ",
            "The most efficient way to get a job is to get a job.                                         "
          ]
        }*
        ```
        
    - 로그 확인
        
        ```python
        # 로그 확인
        tail -f ch03/single_model_llm_serving/server_run.log
        
        # 1단계 — 첫 배치: 4개 (batch_size 상한 적용)
        **Sending batch to worker: [Sequence, Sequence, Sequence, Sequence]**  # 4개
        Batch input shape: torch.Size([4, 5])
        
        WorkloadManager.get_next_batch() (workload_manager.py:50-52)가 batch_size=4 제한 때문에 5개 중 앞의 4개(Hello, I am / The weather is / I want to / The best way to)만 꺼내 active_sequences에 채웠습니다. 5번째 프롬프트(The most efficient way to)는 incoming_queue에 남아 대기.
        torch.Size([4, 5])는 model_worker.py:34-40에서 토크나이저가 padding=True로 4개 프롬프트를 한 텐서에 묶은 결과입니다 — 4개 시퀀스 × (배치 내 최장 프롬프트 기준) 5토큰으로 패딩. 이게 배칭의 핵심: 서로 다른 요청(request1의 promptA/B, request2의 promptC/D)이 하나의 GPU forward pass에 섞여 들어간 것.
        
        # 2단계 — 결과에 request_id가 딸려 나옴
        Received results from worker: ('complete', [{'request_id': '2629c26e...', 'generated_text': 'Hello, I am a student...'}, ...])
        
        model_worker.py:59-65가 zip(request_ids, generated_texts)로 생성 결과에 원래 Sequence.id를 다시 붙여 돌려줍니다. 이게 그림 3-3의 "6. Response mapping" 단계 — 배치로 섞여 들어갔어도 각 결과가 어느 프롬프트(ID) 것인지 잃지 않는 이유입니다. LLMEngine.generate(llm.py:111-113)가 이 request_id로 workload_manager.update_sequence_output()을 호출해 각 Sequence에 결과를 채워 넣습니다.
        
        # 3단계 — 두 번째 배치: 1개만 (자리가 나서야 다음 프롬프트 진입)
        **Sending batch to worker: [Sequence]**  # 1개
        Batch input shape: torch.Size([1, 6])
        Generated texts: ['The most efficient way to get a job is to get a job. ...']
        
        첫 배치가 끝나 active_sequences가 비워지고 나서야(_is_batch_finished 루프가 다시 get_next_batch() 호출) 대기 중이던 5번째 프롬프트가 단독 배치로 실행됐습니다. 앞서 설명한 "이미 실행 중인 배치에 빈 자리가 생겨야 다음 프롬프트가 들어간다"는 FIFO 고정 배치 크기의 동작이 로그로 그대로 증명된 셈입니다.
        ```
        
    

`스티리밍 배치 요청`

- **[코드/설명] Streaming with Batching**
    - 이 섹션에서는 방금 구현한 **배칭 메커니즘** 위에 **스트리밍 지원을 추가**하겠습니다. 현재 배칭 코드는 **모든 프롬프트가 완전히 처리될 때까지 결과를 반환하지 않아, 상당한 지연이 발생하고 사용자 경험이 나빠질 수** 있습니다.
    - 2장에서 논의했듯이, **LLM은 한 번에 한 토큰씩 추론을 생성**합니다. 전체 배치가 완료될 때까지 **기다리는 지연 시간을 줄이기** 위해, **토큰이 생성되는 즉시 사용자에게 다시 전송**하고, **각 생성 단계에서 내부적으로 요청을 배치**하는 방식을 취하고자 합니다. 이를 통해 높은 처리량을 유지하면서도 사용자에게 더 빠르고 실시간에 가까운 경험을 제공할 수 있습니다.
        
        
    - **Streaming이 필요한 이유**
        - 일반 Batch API는 모든 토큰이 생성될 때까지 기다린 후 결과 전체를 반환합니다.
            
            ```
            Washington D.C. is the capital...
            ```
            
        - 하지만 LLM은 실제로 다음처럼 한 토큰씩 생성합니다.
            
            ```python
            Washington
            → D.C.
            → is
            → the
            → capital
            ```
            
        - Streaming은 토큰이 생성되는 즉시 사용자에게 전달합니다.
            
            ```mermaid
            sequenceDiagram
                participant U as User
                participant API as API Server
                participant LLM as LLM Engine
                participant GPU as Model Worker
            
                U->>API: Prompt 전송
                API->>LLM: Streaming Request 등록
            
                loop 토큰 생성
                    LLM->>GPU: Batch의 다음 토큰 생성
                    GPU-->>LLM: 새 Token
                    LLM-->>API: Event Queue에 Token 전달
                    API-->>U: SSE로 Token Streaming
                end
            ```
            
            - Streaming은 모델의 전체 계산 시간을 반드시 줄이는 것은 아닙니다.
            - 하지만 첫 토큰부터 바로 보여주기 때문에 체감 지연시간이 크게 줄어듭니다.
        
    - Batching과 Streaming을 함께 사용하는 방법
        - Batching과 Streaming은 반대 개념이 아닙니다.
        - 서버 내부에서는 여러 요청을 묶어 계산하고, 외부 사용자에게는 요청별로 토큰을 따로 전송할 수 있습니다.
            
            ```python
            시간 T0:
            Batch = A
            
            시간 T1:
            Batch = A, B
            
            시간 T2:
            Batch = A, B, C
            
            시간 T3:
            A 종료
            Batch = B, C, D
            ```
            
        - GPU에서는 Batch 단위로 계산하지만, 결과는 Sequence ID를 이용해 각 사용자의 Queue로 분배합니다.
        
    - **SSE를 이용한 스트리밍** Server-Sent Events
        - 응답 형식은 대략 다음과 같습니다.
            
            ```
            data: {"token":" a","sequence_id":"..."}\n\n
            ```
            
        - 각 요청은 자신만의 `asyncio.Queue`를 가집니다.
            
            ```mermaid
            sequenceDiagram
                participant BG as Background Batch Thread
                participant Q as Client Event Queue
                participant API as Async API Handler
                participant C as Client
            
                BG->>Q: 새 Token put()
                API->>Q: await queue.get()
                Q-->>API: Token 반환
                API-->>C: data: token
                BG->>Q: None
                Q-->>API: 종료 신호
                API-->>C: Stream 종료
            ```
            
            - Background Thread가 GPU Batch 실행을 담당
            - API Coroutine이 사용자 연결을 담당
            - Queue가 두 실행 영역 사이를 연결
    
    - **generate vs generate_stream**
        - 앞서 본 /generate(전체 배치)는 프롬프트 전체가 다 끝날 때까지 블로킹됩니다(model_worker.py:46-52의 model.generate(max_new_tokens=50) 한 번 호출로 텍스트 전체 생성).
        - 반면 /generate_stream은 한 스텝에 토큰 1개씩만 생성해서(model_worker.py:90-101, outputs.logits[:, -1, :]로 다음 토큰 하나만 샘플링) 나오는 즉시 클라이언트에 흘려보냅니다.
        - Table 3-1이 보여주는 게 바로 이 "**토큰 단위 스트리밍** + 그 안에서의 **배치 슬라이딩 윈도우**"입니다.
            
            
    - Table 3-1 시나리오 ↔ 실제 코드 : outlines the new streaming and batching user experiences we plan to support.
        - **T0, A 도착** → event_generator(llm.py:123-130)가 호출돼 workload_manager.add_streaming_request(prompt, queue, loop)로 Prompt1을 incoming_streaming_queue에 넣음.
        - **T1, B 도착** → 마찬가지로 큐에 추가. 백그라운드 스레드(requests_processing_loop)가 다음 루프에서 get_next_batch(is_streaming=True)를 호출하면 active_streaming_sequences가 batch_size=4 미만이므로 Prompt2도 배치에 합류(workload_manager.py:42-48) ⇒ Table 3-1의 [Prompt1, Prompt2] 배치가 이렇게 만들어집니다.
        - **T2, C 도착** → 같은 방식으로 [Prompt1, Prompt2, Prompt3].
        - **T3, A 완료 → D 합류** → Prompt1이 max_tokens(llm.py:17, 20토큰) 도달하거나 EOS가 나오면 remove_finished_sequence로 active_streaming_sequences에서 빠지고(llm.py:55), 그 빈자리에 대기 중이던 Prompt4가 다음 루프에서 채워짐([Prompt2, Prompt3, Prompt4]). 배치 슬롯이 고정 크기(4)라 완료된 자리만큼만 새 요청이 들어온다는 게 지난번 /generate 테스트 로그에서 확인한 것과 완전히 동일한 메커니즘 ⇒ 다만 이번엔 토큰 단위로 훨씬 빠르게 회전합니다.
        
        | Time | Action | Backend batch | Streamed tokens |
        | --- | --- | --- | --- |
        | T0 | User A’s prompt arrives
        [Prompt1: “Hello, I am"] | [Prompt1] | Prompt1: “a” |
        | T1 | User B’s prompt arrives
        [Prompt2: “I want to"] | [Prompt1, Prompt 2] | Prompt1: “a”, “student”
        Prompt2: “see” |
        | T2 | User C’s prompt arrives
        [Prompt3: “I like to"] | [Prompt1, Prompt 2, Prompt 3] | Prompt1: “a”, “student”, “[end]”
        Prompt2: “see”, “a”
        Prompt3: “eat” |
        | T3 | A finishes, D joins
        [Prompt4: “The best way to"] | [Prompt 2, Prompt 3, Prompt 4] | Prompt2: “see”, “a”
        Prompt3: “eat”
        Prompt4: “success” |
        - 표 3-1에서는 서비스가 시간에 따라 프롬프트를 처리하는 과정을 T0부터 T3까지 확인할 수 있습니다.
        - 프롬프트 [1–4]는 서로 다른 시점 [T0–T3]에 네 명의 서로 다른 사용자 [A–D]로부터 받습니다.
        - 서비스는 백엔드에서 이 프롬프트들을 모델 추론을 위해 배치합니다. 또한 각 프롬프트별로 생성된 토큰을 개별적으로 추적합니다.
        - 토큰이 생성되면 실시간으로 사용자에게 스트리밍됩니다. 프롬프트가 완료되면 새로운 요청을 위해 백엔드 배치에서 제거됩니다.
        - 예를 들어, Prompt1은 T2에서 완료되었기 때문에 T3에서 제거됩니다.
        
    - 이러한 스트리밍 사용자 경험을 염두에 두고, 샘플 서비스에서 배칭을 활용해 스트리밍을 구현하는 방법을 개괄적으로 이해하려면 그림 3-4를 참고하세요.
        
        !Figure 3-4. Batching과 streaming을 함께 처리하는 workflow
        
        Figure 3-4. Batching과 streaming을 함께 처리하는 workflow
        
        - Streaming은 batch 처리와 충돌하기 쉽다. 여러 요청을 batch로 묶어 처리하면서도, 각 client에는 자신의 token stream만 순서대로 보내야 하기 때문이다.
    - **스트리밍을 배칭으로 서비스하는 워크플로우를 보여주는 다이어그램**으로, API 서버, LLM 엔진, 워크로드 매니저, 모델 실행기 간의 상호작용을 통해 요청을 처리하고 토큰을 효율적으로 생성하는 과정을 나타냅니다.
        1. ***Request intake*** 접수 요청하기
            - API 서버는 각각 하나의 프롬프트를 포함한 두 개의 생성 요청을 받습니다.
            - **비동기 인터페이스**이기 때문에, 생성되는 토큰을 클라이언트가 순차적으로 받을 수 있도록 **Server-Sent Events(SSE) 스트림을 반환**합니다.
        2. ***Prompt initialization*** 프롬프트 초기화
            - LLM 엔진은 각 프롬프트마다 시퀀스 객체를 생성합니다.
            - 이 객체는 생성된 토큰을 저장하는 출력 버퍼와 토큰을 클라이언트로 다시 스트리밍하는 이벤트 큐를 가지고 있습니다.
        3. ***Batching loop*** 배치 루프
            - LLM 엔진은 백그라운드 스레드를 실행하며, 반복 루프 내에서 배치 생성을 지속적으로 조율합니다.
            - 각 루프 반복은 토큰 생성의 한 배치 단계를 나타냅니다.
        4. ***Model execution*** 모델 실행
            - 프롬프트 묶음이 모델 실행기와 워커로 전송되며, 이들은 추론을 수행하고 묶음 내 각 프롬프트마다 하나의 토큰을 생성합니다.
        5. ***Token collection*** 토큰 수집
            - 모델 워커는 새로 생성된 토큰들의 목록을 반환하며, 각 토큰은 프롬프트 ID와 연결되어 있습니다.
        6. ***Sequence update*** 시퀀스 업데이트
            - LLM 엔진은 새로운 토큰마다 해당 시퀀스에 추가하여 출력과 프롬프트를 모두 업데이트하고, 이를 다음 토큰 생성 라운드에 사용합니다.
        7. ***Streaming tokens*** 스트리밍 토큰
            - LLM 엔진은 새로운 토큰을 각 프롬프트의 이벤트 큐로 보내고, 이 큐는 API 서버에 토큰이 SSE 스트림을 통해 클라이언트로 스트리밍될 준비가 되었다는 신호를 보냅니다.
        
    - 우리는 그림 3-3의 배치 구현과 비교해 이 구현에 몇 가지 변화를 도입했습니다. 우리가 도입한 주요 변경 사항은 다음과 같습니다:
        - 이제 **generation** **API**가 **비동기**로 전환되어, **토큰이 생성되는 즉시 사용자가 업데이트**를 **받을 수** 있습니다.
        - **ModelWorker**는 전체 출력을 한 번에 생성하는 대신, **추론 단계마다 하나의 토큰을 생성**합니다.
        - **WorkloadManager는 부분 출력을 추적**하고, 각 프롬프트를 **실시간으로 새로 생성된 토큰으로 업데이트**합니다.
        - **각 프롬프트는 자체 이벤트 큐**를 가지게 되어, **LLMEngine이 ModelWorker에서 비동기 API 계층**으로 토큰을 효율적으로 **전달**할 수 있습니다.
        - LLMEngine은 프롬프트 전반에 걸쳐 **토큰 단위 추론을 조율하는 전용 배치 처리 스레드**를 포함하고 있습니다.
        
    - 이제 핵심 구현을 할 시간입니다.
    - 다음 코드 예제에서는 **스트리밍을 위해 SSE**를 사용해 생성된 **토큰이 클라이언트로 다시 전달되는 방식**을 중점적으로 다루겠습니다.
    - 먼저, 백그라운드 스레드(reqs_processing_loop)에서 LLMEngine은 WorkloadManager로부터 프롬프트 배치를 지속적으로 가져와 ModelExecutor와 ModelWorker에 전달해 다음 토큰을 생성합니다.
    - 다음은 배경 스레드 코드의 첫 번째 부분입니다:
        - Batch-processing loop는 active sequence들을 가져와 model executor에 보내고, 생성된 token들을 다시 request별 queue로 분배한다.
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        class LLMEngine:
           def **requests_processing_loop**(self):
             while True:
               **active_sequences** = self.**workload_manager**.get_next_batch(is_streaming=True)
               prompts = [
                   {"prompt": seq.prompt, "request_id": seq.id}
                   for seq in active_sequences
               ]
               tokens = self.**model_executor.execute_forward_batch**(prompts)
        ```
        
    - 다음으로 **requests_processing_loop**에서는 LLMEngine이 **ModelExecutor로부터 토큰을 받으**면, 각 프롬프트에 연결된 **이벤트 큐(client_stream)**를 통해 이를 **API 서버의 해당 요청 스레드로 전달**합니다. 예제 3-3에서 구현을 확인하세요.
    - 예시 3-3. LLMEngine 배치 처리 루프 구현 **batch-processing loop implementation**
        - 생성된 token은 해당 request의 `client_stream` queue로 전달된다. 완료 token이 오면 stream을 닫고 sequence를 제거한다.
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        def requests_processing_loop(self):
        
            **# Stream tokens back to respective clients**
            for token in tokens:
               seq = self.workload_manager.get_sequence(token["request_id"])
               if result["is_finished"] or seq.token_count > self.max_tokens:
                  asyncio.run_coroutine_threadsafe(
                     seq.client_stream.put(None),   **# push finish token to request thread**
                     seq.loop
                  )
                  seq.finished = True
                  self.workload_manager.remove_finished_sequence(token["request_id"])
               else:
                  asyncio.run_coroutine_threadsafe(
                     seq.client_stream.put(json.dumps({  **# push token to request thread**
                        "token": token["token"],
                        "sequence_id": token["request_id"]
                     })),
                     seq.loop
                  )
                  self.workload_manager.update_sequence_output(
                     token["request_id"],
                     token["token"]
                  )
        ```
        
    - 각 웹 요청 처리 스레드에서 **event_generator(**아래 코드 참조)는 LLMEngine이 **들어오는 프롬프트를 위한 이벤트 큐를 생성**하고 **워크로드 매니저에 등록**합니다: **workload_manager.add_streaming_request**(prompt, queue, loop).
    - 이제 **요청은 이 이벤트 큐에 있는 토큰을 비동기적으로 기다릴 수** 있습니다:
        - Client별 async generator는 queue에서 token을 읽어 Server-Sent Events 형태로 yield한다.
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        async def **event_generator**(self, loop, prompt: str):
           queue = asyncio.Queue()
           seq_id = self.**workload_manager.add_streaming_request**(prompt, queue, loop)
        
           while True:
              data = await queue.get()
              if data is None:
                 break
              yield f"data: {data}\n\n"
        ```
        
    - 한편, 백그라운드 스레드인 **requests_processing_loop**(예제 3-3 참조)는 **프롬프트를 배치 단위로 지속적으로 처리**하고 **생성된 토큰을 해당 이벤트 큐로 다시 전달**합니다. 이 코드는 **각 프롬프트에 이벤트 큐를 할당**하여 **개별 요청 스레드와 중앙 집중식 배치 처리 스레드 간의 통신**을 가능하게 합니다.
        
        
    - 마지막으로, API 서버는 **비동기 스트리밍 API**인 **generate_stream**을 제공하는데, 이 API는 **LLMEngine으로부터 토큰을 받아 SSE**를 통해 **StreamingResponse**로 클라이언트에 **텍스트/이벤트 스트림 콘텐츠 타입으로 전송**합니다:
        - FastAPI endpoint는 `StreamingResponse`로 token stream을 반환한다.
        
        ```python
        # ch03/single_model_llm_serving/llm/llm.py
        
        @app.post("**/generate_stream**")
        async def generate_stream(
            request: GenerateRequest,
            llm: LLMEngine = Depends(get_llm)
        ):
           async def event_generator():
               loop = asyncio.get_event_loop()
               async for token in llm.event_generator(loop, request.prompt):
                   # token = 'data: {"token": " a", "sequence_id": "8310f5e1-6f6f-480e-b2f9-c8144a12cc17"}\n\n'
                  yield token
        
           return **StreamingResponse**(
               event_generator(),
               media_type="**text/event-stream**"
           )
        ```
        
    - 스트리밍 구현이 완료되었으니, 다음 코드를 사용해 테스트할 수 있습니다:
        - Streaming test는 response stream을 직접 읽어 `data:` line에서 token을 파싱한다.
        
        ```python
        @pytest.mark.asyncio
        async def test_generate_stream(async_client):
           prompt = "Hello, I am"
           
           # Create a streaming request
           async with async_client.stream(
               "POST",
               "/generate_stream",
               json={"prompt": prompt}
           ) as response:
        
               # Process the response stream directly
               assert response.status_code == 200
               async for chunk in response.aiter_bytes():
        
                  # Convert bytes to string and split by newlines
                  lines = chunk.decode().split("\n")
                  for line in lines:
                     if line.startswith("data: "):
                        data = json.loads(line[6:])
                        token = data["token"]
        ```
        
    - 그림 3-5가 스트리밍과 배칭을 통해 토큰이 어떻게 생성되고 클라이언트로 반환되는지 시각적으로 보여줍니다.
        
        !Figure 3-5. Token streaming async workflow
        
        Figure 3-5. Token streaming async workflow
        
    - 비동기 토큰 스트리밍 워크플로우를 보여주는 다이어그램으로, **LLM이 프롬프트를 배치로 처리**하고 **이벤트 큐를 통해 관리**하며, **SSE 이벤트를 통해 토큰을 클라이언트에게 실시간으로 전달**하는 과정을 설명합니다.
    - 그림 3-5는 LLM이 토큰을 배치 단위로 처리하면서도 실시간으로 개별 클라이언트에게 스트리밍하는 방식을 보여줍니다.
    - 핵심 아이디어는 **전용 이벤트 큐를 사용해 각 프롬프트의 실행을 추적**하고, **새로 생성된 토큰을 각 채널로 전달**해 **각 클라이언트에게 적시에 질서 있게 전달**되도록 하는 것입니다.
        
        
    - **이제 단일 프롬프트 추론, 배치 처리, 스트리밍 추론을 포함한 단일 모델 LLM 서비스의 모든 핵심 기능을 구현**했습니다.
    - 이 사례들은 LLM 모델을 일반적이고 확장 가능한 방식으로 최종 사용자와 애플리케이션에 제공하기 위해 얼마나 많은 공학적 노력이 필요한지 감을 잡게 해줄 것입니다.
    - 실제로 스레드 관리, 이벤트 큐잉, 프로세스 간 통신, 그리고 다양한 모델 아키텍처 전반에 걸친 실행 세부 사항 처리 등 복잡한 요소를 모두 갖춘 완전한 프로덕션급 모델 서비스를 구축하는 것은 매우 벅찰 수 있습니다. 이때 **vLLM 같은 모델 서빙 프레임워크가 중요한 역할**을 합니다.
    
- **[실습3] Streaming with Batching 요청**
    
    !Figure 3-4. Batching과 streaming을 함께 처리하는 workflow
    
    Figure 3-4. Batching과 streaming을 함께 처리하는 workflow
    
    !Figure 3-5. Token streaming async workflow
    
    Figure 3-5. Token streaming async workflow
    
    - Streaming with Batching 요청
        
        ```python
        # Streaming Generation For real-time token streaming:
        curl -X POST http://localhost:8000/**generate_stream** \
          -H "Content-Type: application/json" \
          -d '{"prompt": **"Hello, I am"**}' \
          **--no-buffer**
        *data: {"token": " **a**", "sequence_id": "8528ef12-5a8c-4506-9e3c-18b7289196cd"}
        data: {"token": " **16**", "sequence_id": "8528ef12-5a8c-4506-9e3c-18b7289196cd"}
        data: {"token": "**-**", "sequence_id": "8528ef12-5a8c-4506-9e3c-18b7289196cd"}
        ...*
        
        # 혹은 Send streaming request and process the response
        curl -N -H "Accept: text/event-stream" \
             -H "Content-Type: application/json" \
             -d '{"prompt": "'**The weather is**"}' \
             http://localhost:8000/**generate_stream** | while read -r line; do
            if [[ $line == data:* ]]; then
                token=$(echo $line | sed 's/^data: //' | jq -r '.token')
                echo "Received token: $token"
            fi
        done
        ```
        
    - Streaming with Batching 동시 2개 요청 → 로그 분석
        
        ```python
        # 정확히 Table 3-1이 묘사한 대로 두 프롬프트가 하나의 배치로 묶여 처리됐습니다.
        
        **1. 배치 결합 확인 — 처음부터 끝까지 batch size 2 고정**
        Sending streaming batch to worker: [{'prompt': 'The weather is', ...}, {'prompt': 'I want to', ...}]
        Batch input shape: torch.Size([2, 4])
        
        두 요청이 거의 동시에(02:12:50,3xx) 들어와서 첫 배치 스텝부터 곧바로 합쳐졌습니다. 이후 스텝을 세보면:
        
        **[2, 4] → [2, 5] → [2, 6] → ... → [2, 25]   (총 22스텝, 계속 배치 크기 2 유지)**
        
        torch.Size([1, ...]) 형태는 새 로그에 단 한 번도 등장하지 않았습니다 — 즉 두 요청이 끝까지 같은 배치 슬롯에서 나란히 처리됐다는 뜻입니다. 지난번 단일 요청 때는 항상 [1, ...]이었던 것과 대조적입니다.
        
        **2. 스텝별 토큰 생성 — 한 번의 forward pass에서 두 시퀀스 동시 생성**
        Generated token for prompt 'The weather is': ' going'
        Generated token for prompt 'I want to': ' know'
        
        매 스텝마다 로그에 두 줄씩 찍히는 게 보이는데, 이게 model_worker.py:97-101의 outputs.logits[:, -1, :] 한 번의 배치 forward에서 두 시퀀스의 다음 토큰을 동시에 뽑아낸 결과입니다. **각자 독립적으로 두 번 모델을 호출한 게 아니라 GPU 상에서 한 번에 처리됐다는 것** — 배칭의 핵심 이점이 로그로 그대로 드러났습니다.
        
        **3. ID 매핑 정확성 — 서로 다른 큐로 올바르게 전달됨**
        Received data in queue for sequence b528ea9d...: {"token": " going", "sequence_id": "b528ea9d..."}
        Received data in queue for sequence d9efd319...: {"token": " know", "sequence_id": "d9efd319..."}
        
        각 토큰이 정확히 **원래 자신의 client_stream(이벤트 큐)로 라우팅**됐습니다. 실제 curl 출력도 이를 뒷받침합니다:
        - b528ea9d (The weather is) → "...going to be extremely cold and the forecast calls for a big snow storm with a high of 40 degrees on"
        - d9efd319 (I want to) → "...know why some people don't watch this, but I'm curious why I don't. I mean,"
        
        **두 문장이 섞이지 않고 각각 온전하게 재구성**됐습니다.
        ```
        
    

`vLLM 배치 서빙`

- **[코드/설명] Batch Serving with vLLM : 서빙 시스템의 내부에서 어떤 일이 일어나는지 이해하는 것이 필수적!**
    - **직접 수동 구현 vs vLLM 사용 비교**
        - 직접 구현한 batching/streaming logic은 학습에는 좋지만 production에서는 복잡도가 높다.
        - vLLM은 batching, scheduling, KV cache 관리 등을 내부에서 처리한다.
        
        !mermaid-diagram.png
        
        |  | 수동 구현 (generate, event_generator) | vLLM 구현 (generate_vllm) |
        | --- | --- | --- |
        | 배치 구성 | WorkloadManager.get_next_batch() : FIFO + 고정 batch_size=4 | vLLM 내부 스케줄러 (**continuous batching**) |
        | 토큰 생성 | ModelWorker가 별도 프로세스에서 한 스텝씩 forward (use_cache=False로 매번 전체 재계산 , O(n²) 비효율) | vLLM의 PagedAttention + KV 캐시로 최적화 |
        | 결과 매핑 | sequence_map, request_id 수동 추적 | vLLM LLM.generate()가 입력 순서 그대로 outputs 반환 |
        | 스트리밍 | client_stream(asyncio.Queue) + 백그라운드 스레드 직접 구현 | vLLM이 내부적으로 처리(별도 API 필요) |
        | 코드량 |  workload_manager.py(90줄) + model_executor.py(72줄) + model_worker.py(141줄) | llm.py:151-174, 약 20줄 |
    - 지금까지는 서빙 시스템의 내부 메커니즘을 드러내기 위해 배칭을 수동으로 구현해 왔습니다.
    - 이제 실제 서비스에 쓰이는 vLLM 프레임워크가 같은 문제를 어떻게 해결하는지 살펴보겠습니다.
    - 이 섹션은 이전 구현을 대체하지 않습니다. 대신, 그것은 그것을 기반으로 합니다.
    - 먼저 자체적으로 단순화된 배칭 시스템을 구축함으로써, 요청 그룹화, 스케줄링, 동시성 제어에 수반되는 조정상의 어려움을 명확히 파악할 수 있었습니다.
    - 이 기반을 바탕으로, 이제 vLLM이 이러한 책임들을 어떻게 추상화하고 최적화하는지 살펴볼 수 있습니다.
        
        
    - vLLM과 같은 모델 서빙 프레임워크는 이러한 메커니즘을 상용화하기 위해 설계되었습니다.
    - 모델 로딩, 메모리 관리, 동적 배치, 스트리밍, 스케줄링을 매우 최적화된 방식으로 처리합니다.
    - 이러한 컴포넌트를 운영 환경에서 다시 구현하기보다는, 팀들은 보통 서비스 아키텍처 내에 이런 프레임워크를 래핑하거나 통합합니다.
        
        
    - 다음 예제에서는 vLLM을 사용해 배치와 실행을 제공하는 단일 모델 서빙 서비스를 구축하는 방법을 보여줍니다.
    - 목표는 최소한의 교육적 구현과 생산 최적화된 프레임워크라는 두 가지 접근 방식을 비교하는 것입니다.
    - 서비스 아키텍처는 그림 3-6에 설명되어 있으며, GitHub 저장소의 코드를 통해 직접 따라 해볼 수 있습니다.
        
        !Figure 3-6. vLLM 기반 single-model LLM serving architecture
        
        Figure 3-6. vLLM 기반 single-model LLM serving architecture
        
    - vLLM을 사용하는 단일 모델 LLM 서비스 아키텍처를 보여주는 다이어그램으로, API 서버가 LLM 엔진과 통신하고, LLM 엔진은 모델 실행을 위해 vLLM과 인터페이스합니다.
    - 그림 3-4와 3-5에 나타난 스트리밍 설계와 비교했을 때, **그림 3-6의 아키텍처는 훨씬 더 단순**합니다. 모든 **무거운 작업은 vLLM에 위임**됩니다.
    - LLMEngine은 `facebook/opt-125m` 모델을 이용해 **vLLM**을 초기화하고, 생성 요청을 직접 전달합니다.
    - 배치 요청 처리를 위해 vLLM이 LLMEngine에 어떻게 통합되는지 예제 3-4의 구현을 참고하세요.
    - 예시 3-4. vLLM을 사용해 코드를 서비스하는 LLM
        - `LLMEngine`의 backend를 vLLM으로 교체하면 application API는 유지하면서 serving engine만 바꿀 수 있다.
        
        ```python
        class LLMEngine:
           def __init__(self):
            
               # Initialize vLLM with a model
               self.vllm_model = VLLM(model="facebook/opt-125m")
        
           def generate_vllm(self, prompts: List[str]) -> List[str]:
               # Configure sampling parameters for vLLM text generation
               sampling_params = SamplingParams(
                   temperature=0.7,
                   top_p=0.95,
                   max_tokens=self.max_tokens
               )
        
               # Generate text for all prompts
               outputs = self.vllm_model.generate(prompts, sampling_params)
        
               # Extract generated text from outputs
               generated_texts = [
                   output.outputs[0].text
                   for output in outputs
               ]
        
               return generated_texts
        ```
        
    - 예제 3-4에서 보듯이, **vLLM을 사용하면 단 10줄의 코드로 배치 추론을 활성화**할 수 있습니다.
    - 이 때문에 이러한 **서비스 프레임워크가 모델 서비스 구현에서 매우 널리 사용**됩니다.
    - 서빙 프레임워크를 커스터마이징하면 이를 더욱 **최적화하는 데 도움**이 됩니다.
    - **vLLM 프레임워크가 모델 서빙의 많은 복잡성을 추상화하지만, 기본값에 문제가 없다면 직접 커스터마이징할 필요가 있습니다.**
    - 그래서 **서빙 시스템의 내부에서 어떤 일이 일어나는지 이해하는 것이 필수적**입니다.
        - *내부 원리를 알아야 다음 설정을 올바르게 튜닝할 수 있습니다.*
            - *최대 동시 Sequence 수*
            - *Batch Token 수*
            - *GPU Memory Utilization*
            - *KV Cache 크기*
            - *Chunked Prefill*
            - *Scheduling 정책*
    - 일반적으로 모델 서빙 시스템이 어떻게 작동하는지 이해하면 프레임워크의 잠재력을 최대한 활용하고, 시스템 요구사항, 트래픽 패턴, 서비스 수준 목표(SLO/SLA)에 맞게 효과적으로 조정할 수 있습니다.
        
        
    - 또한, 6장과 7장에서 소개된 많은 **모델 최적화 기법들이 vLLM의 구성 옵션과 직접적으로 대응**됩니다.
    - **모델 실행과 서빙의 기본 원리를 확실히 이해하면, 이러한 파라미터를 효과적으로 조정할 수 있는 감각을 갖추게 됩니다.**
    - 예를 들어, 배칭이 지연 시간과 처리량에 어떤 영향을 미치는지 알게 되면, `max_batch_size`나 `max_num_seqs` 같은 설정을 조정해 **실시간 응답성과 배치 효율성 사이에서 적절한 균형**을 맞출 수 있습니다.
    - 마찬가지로, 디코딩이 프롬프트 재사용을 어떻게 활용하는지 알면 GPU 메모리 할당을 최적화해 더 많은 동시 사용자를 지원할 수 있습니다.
        
        
    - 서빙 프레임워크는 독립 실행형 웹 서버로 실행될 수 있습니다.
    - vLLM과 SGLang 같은 많은 모델 서빙 프레임워크는 사용 사례와 통합 요구에 따라 두 가지 방식으로 배포할 수 있습니다.
    - 프레임워크를 커스텀 서빙 애플리케이션 내에 라이브러리 형태로 임베드해 긴밀한 통합과 실행 흐름에 대한 높은 제어를 가능하게 하거나, 독립적인 웹 서버로 실행해 외부 클라이언트나 다른 서비스가 호출할 수 있는 REST 또는 스트리밍 API를 제공할 수도 있습니다.
    - 샘플 코드에서는 단순화와 이해를 돕기 위해 라이브러리 기반 방식을 채택했습니다.
    - 하지만 실제 환경에서는 서빙 프레임워크를 독립적인 웹 서버 모드로 실행하는 경우가 많습니다. 다음 장에서 그 패턴을 더 자세히 살펴보겠습니다.
        
        
    - **Continuous Batching 개념**
        - 기존 Static Batch:
            
            ```
            A, B, C 시작
            → 모두 끝날 때까지 새 요청 진입 불가
            ```
            
        - Continuous Batch: 이 방식은 GPU의 빈 슬롯을 줄이고 처리량을 높입니다.
            
            ```
            A, B, C 시작
            → A가 끝남
            → 빈 자리에 D 즉시 추가
            ```
            
            ```mermaid
            sequenceDiagram
                participant Q as Request Queue
                participant B as Active Batch
            
                Q->>B: A, B, C 추가
                B-->>B: Decode Step
                B-->>B: A 완료
                Q->>B: D 즉시 추가
                B-->>B: B, C, D Decode
                B-->>B: C 완료
                Q->>B: E 즉시 추가
            ```
            
        - **Static vs Continuous 비교** - Youtube
            - Static 경우 모든 요청 완료될 때가지 대기 발생
                
                !image.png
                
            - Continuous 경우 새로운 요청 수행 가능
                
                !image.png
                
            - 결과
                
                !image.png
                
            
    
- **[실습4] Batch Serving with vLLM**
    
    !Figure 3-6. vLLM 기반 single-model LLM serving architecture
    
    Figure 3-6. vLLM 기반 single-model LLM serving architecture
    
    - 프롬프트 3개 : 검증 포인트 - generated_texts 배열 길이 3
        
        ```python
        #vLLM Generation : For efficient batched inference using vLLM, use the `/generate_vllm` endpoint:
        **curl -s -X POST http://localhost:8000/generate_vllm \
          -H "Content-Type: application/json" \
          -d '{"prompts": ["Hello, I am", "The weather is", "Once upon a time"]}' | jq**
        {
          "generated_texts": [
            " a student in the UK and I would love to see you if you are still interested!\nHi",
            " great, and it's beautiful.\nSeriously, there are no sunshine days, so that's great",
            ", I used to play a bit of this game. I'd hate to give up on it."
          ]
        }
        
        # 로그
        Adding requests: 100%|██████████| 3/3 [00:00<00:00, 4469.95it/s]
        Processed prompts: 100%|██████████| 3/3 [00:00<00:00, 77.09it/s, est. speed input: 359.96 toks/s, output: 1542.60 toks/s]
        ```
        
    - 빈 리스트 : 검증 포인트 - generated_texts가 빈 배열([])로 반환되는지
        
        ```python
        #
        curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/generate_vllm \
          -H "Content-Type: application/json" \
          -d '{"prompts": []}'
        {"generated_texts":[]}
        HTTP 200
        
        # 로그
        Adding requests: 0it [00:00, ?it/s]
        Processed prompts: 0it [00:00, ?it/s, est. speed input: 0.00 toks/s, output: 0.00 toks/s]
        ```
        
    - 필드명 오류 : 검증 포인트 - prompts 필드가 없어 Pydantic 검증에 걸려 HTTP 422(Unprocessable Entity) 기대
        
        ```python
        #
        curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/generate_vllm \
          -H "Content-Type: application/json" \
          -d '{"invalid_field": ["Hello"]}'
        {"detail":[{"type":"missing","loc":["body","prompts"],"msg":"Field required","input":{"invalid_field":["Hello"]}}]}
        HTTP 422
        
        # 로그
        INFO:     127.0.0.1:40088 - "POST /generate_vllm HTTP/1.1" 422 Unprocessable Entity
        ```
        
    - (참고) vllm 2개 이상 동시 요청 시 현재 코드 상태(continuous batching 불가)로는 순차 처리됨.
        - 하나의 실행 배치에 섞으려면 →  vllm.AsyncLLMEngine(비동기 엔진) 설정 필요.

### **A General Design for Single-Model LLM Serving**

- **Requirements for Single-Model Serving**
    - 단일 모델 서빙에 대한 요구사항
        - ***Low latency*** 지연 시간이 짧음
            - 시스템은 모델 추론을 신속히 완료하고 지연 없이 결과를 반환해 사용자 참여를 유지해야 합니다.
            - */generate(전체 배치 완료까지 블로킹) vs /generate_stream(토큰 하나씩 즉시 전달)의 차이를 Table 3-1 실습에서 직접 비교했습니다.*
            - *같은 처리량이라도 스트리밍이 사용자 체감 지연을 크게 줄인다는 걸 로그로 확인했음.*
        - ***High throughput*** 높은 처리량
            - 시스템은 동시에 많은 요청을 처리할 수 있어야 합니다.
            - 초당 쿼리 수(QPS)나 초당 처리 수(TPS)로 측정되는 처리량을 최대화하는 것은 대규모 서비스 제공, 운영 비용 절감, 자원 활용도 향상에 필수적입니다.
            - *WorkloadManager.batch_size=4로 여러 프롬프트를 한 forward pass에 묶는 것(torch.Size([4, 5]) 로그),*
            - *그리고 vLLM의 PagedAttention 배칭이 둘 다 이 요구사항을 위한 기능*
        - ***Scalability*** 확장성
            - 시스템은 변동하는 트래픽을 수용할 수 있도록 수평적으로 확장되어야 하며, 피크 수요 시에는 원활하게 확장되고 한가한 시기에는 확장되어야 합니다.
            - *이건 우리가 이번 세션에서 한계를 직접 발견한 부분입니다.*
            - *앞 실습에서 vLLM 동시 요청 테스트에서, Uvicorn이 단일 이벤트 루프로 동작하고 generate_vllm이 await 없는 동기 호출이라 두 요청이 진짜 동시에 처리되지 못하고 순차 처리됐습니다.*
            - *즉 지금 우리 서비스는 프로세스 하나, 스레드(이벤트 루프) 사실상 하나라서 수평 확장은커녕 단일 프로세스 내 동시성조차 제한적입니다.*
            - *실제 스케일링은 여러 워커 프로세스/여러 GPU 노드로 나가야 합니다.*
        - ***Reliability and availability*** 신뢰성과 가용성
            - 생산 모델 서비스 시스템은 일관되고 중단 없는 서비스를 보장하기 위해 높은 가용성과 장애 허용성을 갖추어야 합니다.
        - ***Resource efficiency and cost management*** 자원 효율성과 비용 관리
            - 특히 GPU에서 ML 모델, 그중에서도 LLM을 서비스하는 것은 많은 자원을 필요로 합니다.
            - 쿼리당 비용을 관리 가능한 수준으로 유지하려면 하드웨어(CPU, GPU, 메모리)를 효율적으로 활용하는 것이 매우 중요합니다.
            - *facebook/opt-125m은 0.24GiB인데 vLLM이 기본 gpu_memory_utilization=0.9로 VRAM 90%를 선점했었죠.*
            - *리소스 효율은 모델 크기가 아니라 설정값을 얼마나 잘 튜닝하느냐에 달려 있다는 걸 실측했습니다*
        - ***Observability*** 관측 가능성
            - 지연 시간, 처리량, 오류율 같은 핵심 성과 지표(KPI)와 예측 신뢰도 같은 모델별 지표를 추적하기 위해서는 강력한 모니터링과 로깅이 필수적입니다.
            - 이러한 가시성은 병목 현상을 파악하고 SLO를 달성하는 데 도움을 줍니다.
    - 이러한 일반적인 서빙 요구사항 외에도, LLM 서빙 요구사항
        - ***Large model size and memory footprint*** 큰 모델 크기와 메모리 사용량
            - LLM은 수십에서 수백 기가바이트의 메모리를 필요로 하는 경우가 많아 GPU 자원과 메모리 할당을 신중하게 관리해야 합니다.
        - ***KV cache management*** KV 캐시 관리
            - 긴 컨텍스트 윈도우와 효율적인 상태 기반 디코딩을 지원하려면, 서빙 시스템은 여러 요청과 세션에 걸쳐 KV 캐시를 효과적으로 관리해야 합니다.
        - ***Streaming responses*** 스트리밍 응답
            - 인터랙티브한 애플리케이션에서는 토큰이 생성될 때마다 클라이언트로 다시 스트리밍하는 것이 중요합니다.
        - ***Concurrency and batching with variable-length workloads*** 가변 길이 워크로드를 활용한 동시성 및 배치
            - LLM 요청은 종종 입력과 출력의 길이가 다양합니다.
            - 서빙 시스템은 높은 처리량과 GPU 활용도를 유지하기 위해 이러한 이기종 워크로드를 지능적으로 배치하고 스케줄링해야 합니다.
            - *FIFO 고정 배치(batch_size=4) vs vLLM의 동적 스케줄링을 비교했고, 방금은 vLLM 통합 방식(동기 API)에서 오히려 요청 간 배칭이 전혀 안 되는 역설적 사례까지 확인했음.*
        
    - LLM 서비스 요구사항은 끊임없이 진화하고 있습니다
        - 대부분의 전통적인 딥러닝 모델 서비스는 비교적 안정적이며, 모델을 블랙박스처럼 다룰 수 있게 해줍니다.
        - 지연 시간과 확장성을 위한 표준 엔지니어링 솔루션을 제공합니다. 반면, LLM 서비스는 더 동적이고 모델을 인지하는 처리가 필요합니다.
        - LLM 서빙 요구사항은 모델 아키텍처와 성능이 발전함에 따라 자주 변경되며, 대개 모델별로 다릅니다.
        - LLM의 입력 및 출력 길이도 사용자 시나리오에 따라 달라집니다.
        - 예를 들어, KV 캐시의 동작은 사용자 입력의 크기와 모델의 어텐션 메커니즘(멀티헤드와 멀티쿼리 어텐션 등)에 따라 달라집니다.
        - 따라서 LLM 서빙 시스템을 설계할 때는 변화하는 구성 요소를 안정적인 인프라와 분리하여, 모델별 요구에 유연하게 대응할 수 있도록 하고 핵심 서빙 로직의 견고함도 확보하는 것이 매우 중요합니다.
    
- **General Design**
    - 이 절에서는 일반 모델 서비스 요구사항과 우리가 논의한 LLM 특유의 문제를 모두 해결하는 상위 수준의 시스템 설계에 대해 다룹니다.
    - 디자인은 특정 도구, 플랫폼, 시스템 또는 라이브러리에 의존하지 않고 의도적으로 개념적이고 추상적으로 유지됩니다.
    - 덕분에 사설 인프라든 퍼블릭 클라우드든 다양한 환경에서 폭넓게 적용할 수 있습니다.
    - 핵심 설계 아이디어는 앞서 언급한 서빙 요구사항을 세 가지 구분된 영역으로 나누어 각각 따로 다루는 것입니다:
        - **Service infrastructure management** : 확장성, 가용성, 모니터링, 효율적인 자원 할당에 중점을 둡니다
        - **Business logic handling** : 고객 사용 사례 통합, 요청 배치, 스트리밍 응답을 다룹니다
        - **Model serving performance** : LLM 특화 성능을 위해 지연 시간, 처리량, 최적화를 목표로 합니다
        
    - 그림 3-7은 이러한 관심사의 분리를 기반으로 한 전체 서비스 아키텍처를 보여줍니다.
        
        !Figure 3-7. Single-model serving general design
        
        Figure 3-7. Single-model serving general design
        
    - 단일 모델 서빙 아키텍처를 보여주는 다이어그램으로, 확장, 장애 허용, 자원 할당을 위해 사용되는 분산 컴퓨팅 인프라를 상세히 설명하며, 로드 밸런서, 모델 서빙 인스턴스, 외부 시스템, 고객 애플리케이션 등의 구성 요소를 포함합니다.
        1. 인프라 관리 : 로드밸런서, 복제(replica) 스케일링, 헬스체크·재시작, 리소스 할당, 모니터링/로깅 인터페이스
        2. 서빙 프론트엔드(비즈니스 로직) : 인증/인가, 외부 시스템 연동, 요청 검증·정규화·배칭, rate limiting, 모델 설정 관리
        3. 서빙 백엔드(모델 추론) : "별도 프로세스로 실행", 서빙 프론트엔드만 접근 가능, vLLM/Triton 같은 프레임워크가 담당
        
    - 먼저, 그림 3-7의 **A 부분**에서는 모델 서빙 로직을 Docker 컨테이너나 Kubernetes Pod 같은 재현 가능한 단위로 캡슐화하고, 인프라 수준의 책임을 분산 컴퓨팅 시스템에 위임합니다.
    - 이 시스템은 트래픽 수요에 따라 서비스 복제본을 수평 확장하거나 축소하고, 상태가 좋지 않은 인스턴스를 재시작하며, 자원을 동적으로 할당하고, 로깅 및 모니터링 인터페이스를 노출하는 등의 주요 작업을 관리합니다.
    - 이러한 인프라 관리 기능은 AWS, Azure 같은 퍼블릭 클라우드 제공업체와 Kubernetes 같은 오픈소스 솔루션을 포함한 대부분의 최신 컴퓨팅 플랫폼에서 기본적으로 제공됩니다.
    - 인프라 관련 문제를 서비스 로직에서 분리함으로써, 모델 서비스와 가용성, 장애 허용, 자원 할당 같은 저수준 세부 사항을 분리할 수 있습니다.
    - 이 구성에서는 최종 사용자가 개별 서비스 인스턴스와 직접 상호작용하지 않습니다.
    - 대신 요청은 로드 밸런서를 통해 전달되며, 로드 밸런서는 사용 가능한 인스턴스들에 트래픽을 투명하게 분산시킵니다.
    - 방식은 내부 확장의 복잡성을 감추고, 사용자에게 백엔드 세부 사항을 노출하지 않으면서 탄력성을 제공합니다.
        
        
    - 다음으로, **파트 B**에서는 각 모델 서빙 인스턴스 내에 웹 서비스 인터페이스를 처리하고 모델 서빙의 핵심 비즈니스 로직을 관리하는 서빙 프론트엔드 컴포넌트가 포함됩니다.
    - 이 레이어는 다음을 담당합니다:
        - 고객 애플리케이션의 요청을 인증하고 승인하기
        - 사용자 및 고객 데이터, 모델 메타데이터, 감사 로그, 결제 시스템 등 외부 또는 내부 시스템과의 통합
        - 모델 다운로드 및 설정하기
        - 모델 설정 및 런타임 컨텍스트 관리하기
        - 요청 검증, 정규화, 배칭 로직을 포함한 추론 요청 사전 처리
        - 속도 제한 및 로깅과 같은 트래픽 제어
    - 이 컴포넌트는 고객 인터페이스와 백엔드 모델 추론 엔진 사이의 중간 계층 역할을 합니다.
    - 이 설정은 고객 대면 챗봇과 같은 비즈니스 환경과 안전하고 유연하며 상황을 인지하는 통합을 가능하게 하면서, 고객 로직을 C 부분에서 처리되는 백엔드 추론 작업과 명확히 분리합니다.
        
        
    - **파트 C**는 실제 모델 추론이 이루어지는 서빙 백엔드 컴포넌트를 보여줍니다.
    - 이 컴포넌트는 보통 별도의 프로세스로 실행되며, 서빙 프론트엔드에만 접근할 수 있습니다. 이는 전적으로 고성능 모델 실행에 집중되어 있습니다.
    - 서빙 백엔드는 다양한 모델 아키텍처와 최적화 전략을 이해하고 지원하도록 설계되었습니다.
    - 실제로 개발자들은 vLLM, Triton 같은 성숙하고 프로덕션급 모델 서빙 프레임워크에 의존하는 경우가 많으며, 이들은 다음과 같은 장점을 제공합니다:
        - LLM에 최적화된 고처리량·저지연 추론 엔진
        - 양자화, KV 캐시 관리, 가변 길이 시퀀스의 지속적 배칭을 포함한 고급 최적화 기법
        - 대규모 환경에서 하드웨어 성능을 극대화하는 효율적인 GPU 활용
        - 지속적인 진화와 강력한 커뮤니티 지원으로 최신 모델 발전과의 일관성을 보장합니다
    - 이 백엔드 컴포넌트에서 모델 실행을 분리함으로써 비즈니스 로직과 추론 성능 문제를 명확히 분리하는 모듈화되고 확장 가능한 아키텍처를 구현할 수 있습니다.
    - 다음 장에서는 이 단일 모델 서빙 패러다임이 실제로 어떻게 작동하는지 보여주는 몇 가지 실제 사례를 살펴보겠습니다.
    - 이 장의 다음 부분에서는 샘플 멀티모드 서비스에 대해 다룹니다.
    

### Build a Multi-Model Serving Service from Scratch

- **멀티 모델 서빙 서비스를 처음부터 직접 구축하기 소개 & 목표** : 여러 모델을 하나의 서비스가 공유 자원으로 서빙
    - 지금까지는 단일 모델 서빙에 집중해 왔습니다. 이 설계는 서비스가 예측 가능한 트래픽과 전용 하드웨어를 가진 하나의 모델을 호스팅할 때 잘 작동합니다. 하지만 많은 실제 시스템에서는 이 가정이 더 이상 성립하지 않습니다.
        
        ```markdown
        # 실제 서비스에서는 이런 상황 발생:
        사용자 요청
         ├─ 감성 분석 → DistilBERT
         ├─ 이미지 분류 → MobileNet
         ├─ Embedding → Embedding Model
         └─ 텍스트 생성 → LLM
        ```
        
    - 애플리케이션이 커지면 **여러 모델을 동시에 제공**해야 할 수도 있습니다. 모델 크기, 버전, 또는 분류, 임베딩, 생성 같은 작업별 모델이 그 예입니다. 모델마다 별도의 서비스를 배포하면 자원이 제대로 활용되지 못하고, 인프라 비용이 증가하며, 운영 복잡성이 커질 수 있습니다. 일부 모델에 트래픽이 적을 때 GPU가 유휴 상태가 되고, 다른 모델은 병목 현상을 겪을 수 있습니다.
        
        ```markdown
        # 모델마다 서버를 따로 만들면:
        Server A → Model A → GPU 사용률 10%
        Server B → Model B → GPU 사용률 20%
        Server C → Model C → GPU 사용률 5%
        Server D → Model D → GPU 사용률 80%
        *=> 일부 서버/GPU는 놀고 있는데 어떤 서버는 과부하가 될 수 있습니다.*
        ```
        
    - 이럴 때 **멀티 모드 서빙**이 선택이 아닌 **필수**가 됩니다.
    - 이 실습 섹션에서는 멀티 모드 서빙 서비스를 구축하는 데 필요한 핵심 개념들을 배우게 됩니다. 단일 모델 인스턴스만 호스팅하는 단일 모델 서비스와 달리, 멀티 모델 서비스는 **공유 인프라 내 여러 모델에 대한 요청을 동적으로 관리하고 라우팅**할 수 있습니다. 이 방법은 특히 수많은 소형 또는 미세 조정된 모델을 서비스할 때 효과적이며, **하드웨어 활용도를 높이고 운영 부담을 줄여줍**니다.
    - 핵심 원칙인 **모델 로딩, 라우팅, 격리, 리소스 공유**를 설명하기 위해 **커스텀 백엔드를 활용한 단순화된 멀티 모드 서비스를 구현하는 것부터 시작**하겠습니다. 그 후에는 **프로덕션 등급의 백엔드 사용으로 전환**할 것입니다(NVIDIA Triton 추론 서버). 이러한 개념들이 실제 시스템에서 어떻게 적용되는지 보여주기 위해.
    - 이 구현 이후에는 **비용 효율성**에 최적화된 패턴과 **지연 시간 및 확장성**에 최적화된 패턴, 두 가지 일반적인 **멀티 모드 서빙 디자인 패턴**을 살펴보겠습니다. 이러한 차이점들은 실제 생산 아키텍처를 형성하는 상충관계를 부각시킵니다.
        
        
    - 설계 목표 **Design Goals** : 3개 모델 - LLM 2개 + 이미지 분류 1개, 모두 CPU
    - 이번 설계에서는 세 개의 모델을 호스팅하는 서비스 모델을 만들 것입니다. 두 개는 트랜스포머 기반 언어 모델이고, 하나는 이미지 분류 모델입니다. 세 개 모두 CPU에서 실행됩니다. 목표는 멀티 모드 서빙의 여러 핵심 요소를 이해하는 데 필요한 핵심 구성 요소만 적절히 활용하는 것입니다. 여기에는 다음이 포함됩니다:
    1. **Cross-framework support (크로스 프레임워크 지원)**
        - PyTorch와 ONNX 같은 다양한 머신러닝 프레임워크와 NLP, Vision 같은 아키텍처로 만들어진 모델들이 어떻게 하나의 통합 시스템 아래에서 호스팅될 수 있는지.
            
            ```markdown
            # 예를 들면 같은 서버에서 다양한 모델 형식을 지원:
            Transformers
            PyTorch / TorchVision
            ONNX
            ...
            ```
            
    2. **Unified API interface (통합 API 인터페이스)**
        - 하나의 서비스가 텍스트 생성이나 이미지 분류 같은 기본 작업과 상관없이, 다양한 유형의 모델에 대해 일관된 웹 인터페이스(예: REST API)를 제공할 수 있는 방법.
            
            ```markdown
            # 클라이언트 입장에서는 아래 형식으로 호출:
            POST /predict
            
            # 그리고 안에 아레 처럼 어떤 모델을 사용할지만 지정:
            {
              "model_id": "**model-A**",
              "input_data": "This movie was great!"
            }
            ```
            
    3. **Resource management (자원 관리: lazy loading + LRU eviction)**
        - 단일 서버 인스턴스에서 여러 모델을 호스팅할 때 제한된 컴퓨팅 자원(CPU, 메모리, 선택적으로 GPU)을 관리하고 할당하는 방법으로, 지연 로딩과 최근 사용량 최소(LRU) 기반 모델 제거 같은 전략을 포함합니다.
            
            ```markdown
            # 서버 메모리는 무한하지 않습니다. 제한된 Memory 관리 필요:
            모델 요청
               ↓
            메모리에 모델 존재?
             ├─ Yes → 바로 추론
             └─ No
                  ↓
               모델 로딩
                  ↓
               **메모리 부족?**
                ├─ No → 그대로 사용
                └─ **Yes**
                     ↓
                  **오래 안 쓴 모델 제거**
            ```
            
    
- **Service Architecture & Serving Workflow**
    1. **API server API 서버** : HTTP 엔드포인트를 노출하고 요청/응답 처리를 담당합니다
    2. **Model manager 모델 관리자*(중심)** : 모델 캐시를 관리하고 모델 워커의 라이프사이클을 조정합니다
        - cache에 없는 모델은 동적으로 로드한다.
        - cache가 가득 차면 LRU 같은 정책으로 모델을 제거한다.
        - *Model Manager는 캐시/수명주기만 조정하고, 실제 인스턴스 생성은 Model Engine에 위임합니다.*
    3. **Model store 모델 상점** : 모델 메타데이터를 저장하고 조회합니다
    4. **Model engine 모델 엔진** : 모델 스토어에서 제공된 메타데이터를 기반으로 모델 워커 인스턴스를 생성하는 역할을 합니다
    5. **Model worker 모델 작업자** : 모델을 메모리에 로드하고 추론 실행을 처리합니다 - **Transformer**Worker, **TorchVision**Worker
    
    !Figure 3-8. Sample multi-model serving service architecture
    
    Figure 3-8. Sample multi-model serving service architecture
    
    - **서빙 작업 흐름**
    1. **Client request 고객 요청**
        - 클라이언트는 모델 ID와 입력 페이로드를 지정하여 API 서버에 **예측 Prediction 요청**을 보냅니다. 예를 들어:
        
        ```markdown
        # Prediction request는 `model_id`와 input data를 포함
        **model_id** = "550e8400-e29b-41d4-a716-446655440000"  
        **input_data** = "This movie was great! I really enjoyed it."
        ```
        
    2. **Model lookup 모델 조회**
        - API 서버의 요청 핸들러는 요청을 ModelManager로 전달하며, ModelManager는 모델이 이미 모델 캐시에 로드되어 있는지 확인합니다.
    3. **Metadata fetch (if not cached) 메타데이터 가져오기 (캐시되어 있지 않은 경우)**
        - 모델이 캐시에 없으면, ModelManager가 모델의 메타데이터를 얻기 위해 ModelStore에 질의하며, 이 메타데이터는 모델을 어떻게 로드하고 호스팅할지 정의합니다. 메타데이터 샘플 항목은 다음과 같이 생겼을 수 있습니다:
        
        ```markdown
        {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "name": "distilbert-base-uncased-finetuned-sst-2-english",
          "type": "text",
          "framework": "transformers",
          "version": "1.0.0",
          "description": "Sentiment analysis model"
        }
        ```
        
    4. **Model worker creation 워커 생성**
        - ModelManager는 메타데이터를 ModelEngine에 전달하고, ModelEngine은 모델을 메모리에 로드하고 추론 준비를 담당하는 ModelWorker를 생성합니다.
    5. **Worker registration 워커 등록**
        - 모델워커가 초기화되면, 모델매니저가 이를 모델 캐시에 등록합니다. 캐시가 가득 차 있으면, ModelManager는 가장 최근에 사용되지 않은 ModelWorker를 제거하여 새 모델을 위한 공간을 만듭니다.
    6. **Inference execution 추론 실행**
        - API 서버는 ModelManager에서 적절한 ModelWorker를 가져와 클라이언트의 입력 데이터를 사용해 추론을 수행하도록 호출합니다.
    7. **Response 응답**
        - API 서버는 추론 결과를 클라이언트에게 반환합니다.
        
    - 보시다시피, 멀티 모델 서빙 워크플로우는 개념적으로 간단합니다. 모델 요청을 받고, 필요하면 요청된 모델을 불러오고, 추론을 실행하는 방식입니다.
    - 핵심 엔지니어링 과제는 **서로 다른 아키텍처와 프레임워크로 학습된 모델들**을 **호스팅하고 운영할 수 있는 통합 인터페이스를 구축**하는 것이며, 동시에 **모델 캐시를 효율적으로 관리해 컴퓨팅 자원 사용을 최적화**하는 데 있습니다.
    
- **[코드/설명] Core Implementation**
    - 목표
        - 이는 제한된 자원으로 여러 ML 모델을 관리하는 멀티 모델 서빙 서비스의 간단한 시연입니다.
        - 이 서비스는 한 번에 최대 2개의 모델을 저장할 수 있는 모델 캐시를 구현하며, 사용 패턴에 따라 필요에 맞게 모델을 불러오고 해제합니다.
    - 기능
        - 필요 시 모델 로드
        - LRU(최소 최근 사용) 모델 캐싱
        - 다양한 모델 유형(텍스트 및 이미지) 지원
        - 다양한 모델 입력을 위한 일반 API 인터페이스
        - 메타데이터 관리 모델링
        - 프레임워크별 모델 워커(트랜스포머, 토치비전)
    - 디렉터리 구조
        
        ```python
        **tree ch03/multi_model_serving/**
        ├── app            # 아래 핵심 로직
        │   ├── engine.py  # Model worker factory and management
        │   ├── manager.py # Model caching and lifecycle
        │   ├── server.py  # FastAPI server and endpoints
        │   ├── store.py   # Model metadata management
        │   └── worker.py  # Abstract worker and framework-specific implementations
        ├── config
        │   └── models.json # Model configurations , 모델 4개 메타데이터
        ├── model_dir
        │   └── densenet_onnx
        │       ├── 1
        │       │   └── model.onnx
        │       ├── config.pbtxt
        │       └── densenet_labels.txt
        ├── **README.md**
        ├── requirements.txt
        └── tests
            ├── images
            │   └── cat1.jpg
            ├── __init__.py
            ├── test_models.py
            └── test_triton_densenet.py
        ```
        
        !mermaid-diagram.png
        
    - 전체 흐름
        
        ```python
        **클라이언트** → **/predict** (server.py)
                   → **ModelManager.get_model_worker()** (manager.py)
                       → 캐시에 있으면: **ModelEngine.get_worker() 반환**
                       → 없으면: ModelStore에서 메타데이터 조회 → **ModelEngine.create_worker()**
                   → **worker.predict(input_data)**
        ```
        
        ```mermaid
        sequenceDiagram
        
            participant C as Client
            participant API as API Server
            participant MM as ModelManager
            participant MS as ModelStore
            participant ME as ModelEngine
            participant MW as ModelWorker
        
            C->>API: POST /predict<br/>model_id + input
        
            API->>MM: get_model_worker(model_id)
        
            MM->>MM: Model Cache 확인
        
            alt Cache Hit
                MM-->>API: 기존 Worker 반환
            else Cache Miss
                MM->>MS: Model Metadata 조회
                MS-->>MM: framework, name, version ...
        
                MM->>ME: Worker 생성 요청
                ME->>MW: Model Load
        
                ME-->>MM: Worker 반환
        
                MM->>MM: Worker Cache 등록
            end
        
            API->>MW: predict(input)
            MW-->>API: prediction
        
            API-->>C: response
        ```
        
        1. `server.py` API 계층
            - /predict는 얇은 라우팅 레이어입니다. model_id로 워커를 받아 predict()를 호출할 뿐, 모델이 어떤 프레임워크인지는 전혀 알지 못합니다. 입력(input_data: Any)과 출력이 모두 범용 타입이라, 전처리/후처리 책임은 클라이언트에게 넘어갑니다. ⇒ "입력 포맷 다양성"에 대한 대응 방식.
        2. `manager.py` ModelManager (LRU 캐시)
            - self.model_cache는 OrderedDict로 구현된 LRU 캐시:
                - 캐시 히트: move_to_end()로 최근 사용 순서를 갱신하고, ModelEngine에서 워커를 반환합니다.
                - 캐시 미스: ModelStore에서 메타데이터를 조회 → 캐시가 max_models(기본 2)를 넘으면 popitem(last=False)로 가장 오래 안 쓴 모델을 꺼내 ModelEngine.delete_worker()로 메모리에서 제거 → 새 워커를 생성해 캐시에 넣습니다.
            - "메모리에 몇 개 모델까지만 동시에 올려둘지"를 여기서 통제합니다.
            - 실제 서빙 시스템(Triton, TorchServe 등)에서 모델 리페어토리 관리가 하는 역할을 아주 단순화해서 흉내낸 부분.
        3. `engine.py` ModelEngine (워커 팩토리)
            - model_metadata.framework 값(transformers / torchvision / triton)에 따라 어떤 ModelWorker 서브클래스를 인스턴스화할지 분기합니다.
            - self.workers 딕셔너리에 model_id → worker 매핑을 들고 있어서, ModelManager의 캐시와 사실상 이중으로 생명주기를 관리하는 구조입니다(캐시에서 지우면 엔진에서도 지움).
        4. `worker.py` ModelWorker 추상 클래스와 구현체들
            - ModelWorker(ABC)는 _load_model()과 predict() 두 개의 추상 메서드만 강제합니다. 실제 리포에는 책 본문보다 하나 더 있는 TritonWorker까지 총 3개 구현체가 있습니다:
                - **TransformerWorker**: AutoModelForSequenceClassification + AutoTokenizer로 감성분석 같은 텍스트 분류 모델을 로드/추론.
                - **TorchVisionWorker**: mobilenet_v2를 로드하고 transforms.Compose로 이미지 전처리 후 추론.
                - **TritonWorker**: 로컬에서 모델을 직접 로드하는 대신, HTTP로 Triton 서버의 모델 리포지토리 API(/v2/repository/models/.../load)를 호출해 원격으로 로드/언로드하고, tritonclient로 추론 요청을 보냅니다. __del__에서 언로드까지 시도하는 게 특징입니다.
            - 다형성(polymorphism) 덕분에 ModelManager/ModelEngine은 어떤 구체 워커인지 몰라도 동일한 predict() 인터페이스로 다룰 수 있습니다. ⇒ "다양한 모델 타입 지원"
        5. `store.py` 메타데이터
            - ModelMetadata(pydantic 모델)와 ModelStore는 config/models.json을 읽어 id → metadata 매핑을 메모리에 올려둡니다.
            - 실무에서는 이 부분이 별도 메타데이터 서비스나 DB로 대체되는 게 일반적입니다.
        
    - **API 서버에서 예측 요청을 처리하는 것부터 시작해 주요 구현 사항들을 살펴보기**
    - API endpoint는 `model_id`로 worker를 찾고 prediction을 수행한다
        
        ```python
        # ch03/multi_model_serving/app/**server.py**
        
        class PredictionRequest(BaseModel):
           model_config = ConfigDict(protected_namespaces=())
           model_id: str
           input_data: Any
        
        @app.post("**/predict**")
        async def predict(request: PredictionRequest):
           # Get model worker
           worker = model_manager.get_model_worker(**request.model_id**)
           # Make prediction
           result = **worker.predict**(request.input_data)
           return result
        ```
        
    - **predict API 구현**에서는 **ModelMan⁠age**r로부터 **ModelWorker를 가져와 모델 추론을 실행**하는 데 사용합니다.
    - ModelManager가 모델 조회를 어떻게 처리하는지 좀 더 자세히 살펴보겠습니다:
    - **ModelManager**는 c**ache를 확인**하고, 없으면 **metadata를 읽어 worker**를 만든다.
    - cache가 가득 차면 **LRU 방식으로 가장 오래 쓰지 않은 모델을 제거**한다.
        
        ```python
        # ch03/multi_model_serving/app/**manager.py**
        
        class **ModelManager**:
           def __init__(self, model_store: ModelStore, max_models: int = 2):
               self.model_store = model_store
               self.max_models = max_models
               self.model_cache = **OrderedDict**()  # model id -> worker
        	self.model_engine = ModelEngine()
          
           def **get_model_worker**(self, model_id: str) -> Optional[ModelWorker]:
               **# Check if model is in cache**
               if model_id in self.model_cache:
                   # Move to end (most recently used)
                   self.**model_cache.move_to_end**(model_id)
                   return self.model_engine.get_worker(model_id)
              
               **# Get model metadata**
               model_metadata = self.model_store.get_model(model_id)
               if not model_metadata:
                   return None
              
               **# Check if we need to remove least used model**
               if len(self.model_cache) >= self.max_models:
                   # **Remove least recently used model**
                   id, model_worker = self.model_cache.popitem(last=False)
                   self.model_engine.delete_worker(id)
               **# Create and cache new model worker**
               self.model_cache[model_id] = \
                         self.model_engine.create_worker(model_metadata)
               return self.model_cache[model_id]
        ```
        
        - get_model_worker 함수에서 ModelManager의 주요 역할이 모델 캐시를 유지하는 것임을 알 수 있습니다.
        - 즉, 어떤 모델을 메모리에 로드할지, 그리고 동시에 몇 개를 활성 상태로 유지할지 제어합니다.
        - 이 예에서는 **간단한 LRU** (Least Recently Used) **전략**을 사용합니다.
            - *LRU 알고리즘은 페이지 교체 알고리즘 중 하나로 사용되는 가장 오랫동안 참조되지 않은 페이지를 교체하는 기법*
        - 캐시된 모델 수가 max_model_count를 초과하면 **가장 최근에 사용하지 않은 모델을 제거해 메모리를 확보**합니다.
    - **ModelManager가 가장 중요한 이유?**
        - ModelManager 의 역할은 사실상 **“어떤 모델을 RAM/VRAM/HBM에 올려둘 것인가?”** 를 결정하는 것입니다.
        - 실제 구현에서는 Python의 `OrderedDict`를 이용하여 모델 Cache를 관리하고, cache가 `max_models`에 도달하면 가장 오래 사용되지 않은 모델을 제거합니다.
        
    - 다음으로 **ModelWorker가 모델을 어떻게 로드하고 초기화**하는지 살펴보겠습니다:
        
        ```python
        # ch03/multi_model_serving/app/**engine.py**
        
        class **ModelEngine**:
           def **create_worker**(self, model_metadata: ModelMetadata) -> ModelWorker:
               if model_metadata.id not in self.workers:
                   if model_metadata.framework == "**transformers**":
                       self.workers[model_metadata.id] = \
                           TransformerWorker(model_metadata)
                   elif model_metadata.framework == "**torchvision**":
                       self.workers[model_metadata.id] = \
                           TorchVisionWorker(model_metadata)
                 # elif model_metadata.framework == "**triton**"..(생략): # **Repo 에는 triton 포함되어서 총 3개 모델 있음**
               return self.workers[model_metadata.id]
        ```
        
        - ModelEngine은 framework별 worker를 생성한다.
        - create_worker 함수에서 ModelEngine은 모델의 프레임워크(예: TorchVision)에 따라 적절한 유형의 ModelWorker를 선택합니다.
        - 이 예제는 다양한 모델 유형을 지원하기 위해 서로 다른 모델 백엔드가 필요함을 보여주기 위해 **TransformerWorke**r와 **TorchVisionWorker** 두 가지 유형의 워커를 구현합니다. ⇒ **Repo 에는 triton 포함되어서 총 3개 모델(워커) 있음**
    - **ModelEngine은 Worker Factory** : 새로운 Framework를 추가하고 싶다면 → Worker를 추가하는 형태로 확장 할 수 있음!
        
        !mermaid-diagram (1).png.png)
        
    - 다음 코드에서 TransformerWorker의 _load_model과 predict 함수 구현을 좀 더 자세히 살펴보겠습니다:
        
        ```python
        # ch03/multi_model_serving/app/**worker.py**
        
        class **TransformerWorker(ModelWorker)**:
           def __init__(self, model_metadata):
               self.tokenizer: Optional[AutoTokenizer] = None
               super().__init__(model_metadata)
        
           def _**load_model**(self):
               if self.model is None:      # Only load if not already loaded
                   self.model = AutoModelForSequenceClassification.from_pretrained(
                       self.model_metadata.name
                   )
                   self.tokenizer = AutoTokenizer.from_pretrained(
                       self.model_metadata.name
                   )
        
           def **predict(**self, input_data: Any) -> Dict[str, Any]:
               **# Tokenize the input** 
               **inputs = self.tokenizer(**
                   input_data,
                   return_tensors="pt",
                   padding=True,
                   truncation=True
               )
               **with torch.no_grad():      # Run model inference**
                   outputs = self.model(**inputs)
               predictions = torch.softmax(outputs.logits, dim=-1)
               return {"predictions": predictions.tolist()}
        ```
        
        - Transformer worker는 tokenizer와 model을 로드하고 classification inference를 수행한다.
            
            ```python
            **# 모델 로딩 함수**
            AutoModelForSequenceClassification.from_pretrained(...)
            AutoTokenizer.from_pretrained(...)
            
            # 모델 로딩 함수 실행 시 : 모델과 tokenizer를 올립니다.
            Storage
               ↓
            Model Weight
               ↓
            Memory
            
            **# 추론 함수**
            inputs = tokenizer(...)
            
            with torch.no_grad():
                outputs = model(**inputs)
            
            predictions = torch.softmax(outputs.logits)
            
            # 추론 함수 실행 시
            # 참고로 여기 모델은 생성형 LLM이 아니라 Sequence Classification 모델입니다.
            sentence
             → classification model
             → logits
             → softmax
             → positive / negative probability
            
            # Sequence Classification 모델은 문장 전체를 보고 “이건 어떤 종류인가?”를 고르는 모델이고, 
            # 생성형 LLM은 앞의 문장을 보고 “다음에 어떤 말을 이어갈까?”를 반복해서 만들어내는 모델
            
            # (만약) 생성형 LLM 모델 추론 실행 시:
            *prompt
             → token
             → next token generation*
            ```
            
        - 이제 모델 메타데이터 로직을 살펴보겠습니다. 이전 ModelManager와 ModelEngine 코드에서 알 수 있듯이, 시스템은 추론 요청을 처리할 적절한 ModelWorker를 결정하기 위해 각 모델의 메타데이터에 의존합니다.
        
    - 간소화된 예시에서 모델 메타데이터는 다음과 같이 정의됩니다:
        
        ```python
        **class ModelMetadata(BaseModel)**:
           id: str
           name: str
           type: str
           framework: str
           version: str
           description: str
        
        **class ModelStor**e:
           def __init__(self, config_path: str):
               self.models: Dict[str, ModelMetadata] = {}
               self._load_config(config_path)
        
           def _load_config(self, config_path: str):
               with open(config_path, "r") as f:
                   config = json.load(f)
                   for model in config["models"]:
                       self.models[model["id"]] = ModelMetadata(**model)
        ```
        
        - Model store는 설정 파일에서 모델 metadata를 로드한다.
            - *ModelStore에는 모델 자체가 아니라 **모델을 어떻게 실행할지 알려주는 Metadata**가 있습니다.*
        - 실제 환경에서는 모델 메타데이터가 보통 모델 관리를 위해 특별히 설계된 원격 데이터베이스나 메타데이터 서비스에 저장됩니다.
        - 하지만 여기서는 간단하게 **로컬 JSON 파일에서 메타데이터를 불러와 호스팅하기 위해 ModelStore 클래스를 사용**합니다.
            
            ```python
            Model ID
               ↓
            ModelStore
            
            *"이 모델은
             Transformers 모델이고
             이름은 DistilBERT이고
             version은 1.0.0이다."*
            ```
            
        
    - 다음은 그 **JSON 파일의 예시**입니다:
        
        ```python
        "models": [
          {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "distilbert-base-uncased-finetuned-sst-2-english",
            "type": "text",
            "framework": "transformers",
            "version": "1.0.0",
            "description": "Sentiment analysis model"
          },
          {
            "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "name": "pytorch/vision:mobilenet_v2",
            "type": "image",
            "framework": "torchvision",
            "version": "1.0.0",
            "description": "Image classification model"
          }
        ]
        ```
        
    - 우리 샘플 서비스가 세 가지 핵심 설계 요구사항을 어떻게 다루는지 다시 정리해 보겠습니다:
        - **다양한 모델 유형을 지원**하기 위해, **특정 모델 유형의 로딩과 실행 로직**을 처리하도록 설계된 **여러 ModelWorker 클래스를 구현**합니다.
        - 다양한 모델 입력 형식을 수용하기 위해 **predict 인터페이스**는 예측 요청에 사용된 **모델에 구애받지 않는 일반적인 입력 및 출력 구조**를 사용합니다.
        - 클라이언트는 자신이 호출하는 모델을 이해할 것으로 기대되기 때문에 입력을 준비(전처리)하고 출력을 해석(후처리)하는 책임이 있다고 가정합니다.
        - **자원 관리**를 위해 **모델은 요청이 들어올 때마다 필요에 따라 메모리에 로드**됩니다. **메모리 사용량이 미리 정한 임계값을 넘으면 가장 적게 사용된 모델을 제거하는 LRU 캐시를 사용해 메모리 소모를 관리**합니다.
        
    - 실제로는 다양한 모델의 로드와 실행을 위한 백엔드 지원을 유지하고, 모델 메타데이터와 구성을 관리하며, 스레드 안전성과 동시성을 조율하는 일이 복잡하고 오류가 발생하기 쉽습니다. 이런 이유로, 이러한 책임을 전용 멀티 모드 서빙 프레임워크에 위임하는 것이 더 효율적인 경우가 많습니다. 이를 통해 해당 프레임워크를 비즈니스 애플리케이션에 통합하는 데 본인의 노력을 집중할 수 있습니다.
    - 다음으로, **현재 예제에서 ModelEngine과 ModelWorker 컴포넌트를 NVIDIA Triton 추론 서버로 대체하는 방법**을 살펴보겠습니다.
    
- **[실습5] 기본 서비스**
    - **실행 계획** - README.md
        
        
    - ch03/multi_model_serving에 전용 venv 생성 후 requirements.txt 설치
        
        ```python
        # cd
        cd ch03/multi_model_serving
        
        # Create virtual environment
        python -m venv venv
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Install dependencies:
        pip install -r requirements.txt
        ```
        
    - python -m app.server (포트 8001)로 서버 기동
        
        ```python
        # Run with default port (8001)
        **python -m app.server**
        
        *# Or specify a custom port
        PORT=8002 python -m app.server*
        ```
        
        !Figure 3-8. Sample multi-model serving service architecture
        
        Figure 3-8. Sample multi-model serving service architecture
        
    - GET /models, POST /predict (sentiment / spam / image) curl 테스트
        
        ```mermaid
        sequenceDiagram
        
            participant C as Client
            participant API as API Server
            participant MM as ModelManager
            participant MS as ModelStore
            participant ME as ModelEngine
            participant MW as ModelWorker
        
            C->>API: POST /predict<br/>model_id + input
        
            API->>MM: get_model_worker(model_id)
        
            MM->>MM: Model Cache 확인
        
            alt Cache Hit
                MM-->>API: 기존 Worker 반환
            else Cache Miss
                MM->>MS: Model Metadata 조회
                MS-->>MM: framework, name, version ...
        
                MM->>ME: Worker 생성 요청
                ME->>MW: Model Load
        
                ME-->>MM: Worker 반환
        
                MM->>MM: Worker Cache 등록
            end
        
            API->>MW: predict(input)
            MW-->>API: prediction
        
            API-->>C: response
        ```
        
        ```python
        # GET /models
        **curl -s http://localhost:8001/models | jq**
        *{
          "available_models": {
            "550e8400-e29b-41d4-a716-446655440000": {
              "id": "**550e8400-e29b-41d4-a716-446655440000**",
              "name": "**distilbert-base-uncased-finetuned-sst-2-english"**,
              "type": "**text"**,
              "framework": **"transformers"**,
              "version": "1.0.0",
              "description": "Sentiment analysis model"
            },
        ...(생략)...*
          ***"loaded_models": {}**  # 아직 /predict 호출은 없어서 모델은 하나도 로드되지 않은 상태입니다(
        }*
        
        **# POST /predict** 감성분석 (sentiment) : curl 2번 실행 하자. 처음은 모델 (가중치)로딩에서 끝났음. 두번째 호출 시 결과 리턴!
        **curl -X POST http://localhost:8001/predict \
          -H "Content-Type: application/json" \
          -d '{"model_id": "550e8400-e29b-41d4-a716-446655440000", "input_data": "This movie was great! I really enjoyed it."}'**
        ***{"predictions":[[0.00011904446000698954,0.9998809099197388]]} # 입력프롬프트에 대해 부정(0.001..), 긍정(0.99..)로 분류!***
        
        **curl -s http://localhost:8001/models | jq**
        *...
          **"loaded_models":** {
            "**550e8400-e29b-41d4-a716-446655440000": "distilbert-base-uncased-finetuned-sst-2-english**",
        ...*
        
        ## 로그 : 첫줄 로그에 모델 (가중치)다운로드
        */root/llm-model-inference/ch03/multi_model_serving/venv/lib/python3.12/site-packages/huggingface_hub**/file_download.py**:949: FutureWarning: `resume_download` is deprecated and will be removed in version 1.0.0. Downloads always resume when possible. If you want to force a new download, use `force_download=True`.
          warnings.warn(
        /root/llm-model-inference/ch03/multi_model_serving/venv/lib/python3.12/site-packages/transformers/utils/generic.py:309: UserWarning: torch.utils._pytree._register_pytree_node is deprecated. Please use torch.utils._pytree.register_pytree_node instead.
          _torch_pytree._register_pytree_node(
        INFO:     127.0.0.1:53590 - "POST /predict HTTP/1.1" 200 OK
        INFO:     127.0.0.1:52434 - "POST /predict HTTP/1.1" 200 OK* # 두 번째 요청부터는 캐시에 있는 모델을 재사용
        
        **# POST /predict** 스팸 탐지 (spam)
        **curl -X POST http://localhost:8001/predict \
          -H "Content-Type: application/json" \
          -d '{"model_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "input_data": "Win a free iPhone now!"}'**
        ***{"predictions":[[0.9324164986610413,0.06758350878953934]]}***
        
        **curl -s http://localhost:8001/models | jq**
        *...
          "loaded_models": {
            "**550e8400-e29b-41d4-a716-446655440000": "distilbert-base-uncased-finetuned-sst-2-english"**,
            "**6ba7b810-9dad-11d1-80b4-00c04fd430c8": "mrm8488/bert-tiny-finetuned-sms-spam-detection**"
        ...*
        
        ## 로그
        *Asking to truncate to max_length but no maximum length is provided and the model has no predefined maximum length. Default to no truncation.
        INFO:     127.0.0.1:60582 - "POST /predict HTTP/1.1" 200 OK*
        
        **# POST /predict** 이미지 분류 (image, torchvision/mobilenet_v2)
        ## 이미지 파일은 python 서버 프로세스가 접근 가능한 절대경로여야 합니다 "tests/images/cat1.jpg"
        **curl -X POST http://localhost:8001/predict \
          -H "Content-Type: application/json" \
          -d '{"model_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7", "input_data": "tests/images/cat1.jpg"}'**
        *{"predictions":[[0.0005569091881625354,0.0005300699267536402,0.0004282000591047108,0.0004879590414930135,0.0007765541085973382,0.00048326607793569565,0.00037369379424490035,0.00028169876895844936,0.0005176462582312524,0.0006431406945921481,0.0005171012599021196,0.0008888093871064484,0.0003733299672603607,0.0004699268320109695,0.0005291578127071261,0.0005390503210946918,0.0017128940671682358,0.0005886905710212886,0.0015381213743239641,0.0004179733223281801,0.0005149548524059355,0.0025300784036517143,0.0003734752244781703,0.000562...*
        
        ## 로그 : mobilenet_v2 사전학습 가중치(13.6MB)를 PyTorch 공식 모델 허브에서 처음 다운로드하는 로그, 
        Downloading: "https://download.pytorch.org/models/mobilenet_v2-7ebf99e0.pth" to /root/.cache/torch/hub/checkpoints/mobilenet_v2-7ebf99e0.pth
        100%|██████████| 13.6M/13.6M [00:01<00:00, 8.38MB/s]
        INFO:     127.0.0.1:53384 - "POST /predict HTTP/1.1" 200 OK # 이미지 분류 추론 정상 처리
        
        # 로드된 모델 정보 확인 : 최대 2개 모델까지 로드(메로리) 할 수 있다. 즉, 처음 호출 시 사용한 모델은 로드에서 제거됨
        **curl -s http://localhost:8001/models | jq
        *...**
          **"loaded_models": {**
            "**6ba7b810-9dad-11d1-80b4-00c04fd430c8": "mrm8488/bert-tiny-finetuned-sms-spam-detection**",
            "**7c9e6679-7425-40de-944b-e07fc1f90ae7": "pytorch/vision:mobilenet_v2**"
          }*
        ```
        
    
- **[코드/설명] Using NVIDIA Triton as a Model Server** 를 백엔드로 연동하는 방법
    - PyTorch, TensorFlow, ONNX, TensorRT 등 서로 다른 포맷의 모델을 동일한 HTTP/gRPC API로 서빙할 수 있게 해주는 표준화된 고성능 멀티모델 서버 - Site , Docs
        
        !https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/introduction/index.html
        
        https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/introduction/index.html
        
    - 이번 섹션에서는 멀티 모델 서빙 예제를 확장해 Triton을 모델 서빙 백엔드로 통합하는 방법을 보여드리겠습니다.
    - 하지만 먼저 그림 3-9에서 트라이톤이 어떻게 작동하는지 간단히 살펴보겠습니다.
    - Triton Server에서 모델을 통합하는 워크플로우를 보여주는 다이어그램으로, 모델 관리와 추론 API를 활용해 모델을 관리하고 예측하는 단계를 설명합니다.
        - Triton Inference Server는 여러 framework/model을 serving할 수 있는 backend로 사용할 수 있다.
        - Multi-model service에서 직접 모델을 로드하는 대신 Triton에 load/infer/unload를 위임할 수 있다.
        
        !Figure 3-9. Triton Server 사용 방식
        
        Figure 3-9. Triton Server 사용 방식
        
        - 그림 3-9에서 보듯이, 트라이튼 서버는 웹 서비스로 실행되며 두 가지 주요 API를 제공합니다.
        - 하나는 모델을 로드, 언로드, 구성하는 모델 관리 API이고, 다른 하나는 예측 요청을 보내는 모델 추론 API입니다.
            - **모델 관리 API: 모델 로드/언로드/설정** (/v2/repository/models/{name}/load, /unload)
            - **추론 API: 실제 예측 요청** (/v2/models/{name}/infer)
        
    - **Triton으로 모델 추론을 실행**하는 데는 몇 가지 간단한 단계만 필요합니다:
        1. 모델을 (Triniton 지원 형식으로) 서버의 지정된 모델 저장소 디렉터리(예: /models/densenet_onnx/)에 복사하세요.
        2. Triton의 관리 API를 사용해 모델을 로드합니다. 예를 들어:
            
            ```python
            # 모델 로드는 Triton repository API로 호출한다
            curl -X POST http://localhost:8000/v2/**repository/models/densenet_onnx/load**
            ```
            
        3. 이 명령은 densenet_onnx 모델이 저장소에 존재하고 제대로 설정되어 있다면 Triton이 해당 모델을 불러오도록 지시합니다.
        4. 추론 API를 사용해 추론 요청을 보내세요. 예를 들어:
            
            ```python
            # Inference는 Triton inference API로 호출한다.
            curl -X POST http://localhost:8000/v2/**models/densenet_onnx/infer**
            ```
            
        5. 이는 요청 페이로드에 제공된 입력 데이터를 사용해 로드된 모델에 대한 예측을 실행합니다.
        
    - 이제 Triton 서버를 멀티 모드 서비스에 통합하는 방법을 살펴보겠습니다.
        - 기존 멀티모델 서비스(그림 3-8)에 **TritonWorker**와 **TritonServer 두 컴포넌트가 추가**됩니다.
    - 이전의 멀티 모드 설계(그림 3-8 참조)와 비교했을 때, 그림 3-10의 업데이트된 아키텍처는 두 가지 새로운 구성 요소를 도입합니다:
        
        !mermaid-diagram (2).png.png)
        
        - **TritonWorker and TritonServer**.
        - *TritonServer: 별도 프로세스로 독립 실행되는 실제 Triton 웹 서비스*
        - *TritonWorker: ModelWorker와 동일한 역할을 하는 wrapper. 다만 내부에서 직접 추론을 실행하는 대신 Triton에게 위임*
    - **Triton worker**는 별도의 웹 서비스로 실행되는 **Triton Inference 서버**를 통해 모델 로딩과 추론 요청을 처리하는 **wrapper 역할**을 합니다.
        
        !Figure 3-10. Triton을 multi-model service의 serving backend로 통합
        
        Figure 3-10. Triton을 multi-model service의 serving backend로 통합
        
    - 이 설계에서는 **모델 호스팅과 실행 책임**을 **Triton에 완전히 위임**하고, 모델 캐시 관리, 모델 파일 처리, 외부 웹 인터페이스는 멀티 모델 서비스 계층 내에 유지합니다.
    - 비록 단순화된 설계이지만, 이 디자인은 실제로 흔히 쓰이는 패턴을 보여줍니다. 즉, **클라이언트 웹 요청 처리**를 위한 **래퍼 서비스 사용**, 의존 시스템 통합, 메모리와 CPU/GPU 같은 자원 및 모델 파일 수명 주기 관리, 그리고 **핵심 추론 작업은 Triton에 맡기는 방식**입니다.
    - *"클라이언트 요청 처리 + 리소스/생명주기 관리는 wrapper, 무거운 추론 워크로드는 전문 엔진에 위임"이라는 실무에서 흔한 패턴 예시*
        
        
    - 이제 **모델 초기화 로직**부터 시작해서 **TritonWorker의 코드 구현**을 살펴보겠습니다.
        1. `_load_model` : 초기화 시 Triton의 management API에 POST 요청을 보내 모델을 로드
        2. `predict` : 실제 추론
        3.  `__del__` : 워커 소멸 시 unload API를 호출해 Triton에서 모델을 내려 GPU/CPU 메모리를 회수
        
        ```mermaid
        sequenceDiagram
        
            participant Repo as Model Repository
            participant App as Multi-Model Service
            participant Triton as Triton Server
            participant Model as Model
        
            Note over Repo: /models/densenet_onnx
        
            App->>Triton: POST /repository/models/.../load
        
            Triton->>Repo: Model File Read
        
            Repo-->>Triton: Model
        
            Triton->>Model: Load into Memory
        
            App->>Triton: /models/.../infer
        
            Triton->>Model: Inference
        
            Model-->>Triton: Result
        
            Triton-->>App: Prediction
        ```
        
    - **TritonWorker**는 다음과 같이 **_load_model 함수**를 사용해 **Triton 관리 API를** 통해 주어진 **모델을 Triton에 로드**합니다:
        - Triton worker는 Triton HTTP client를 만들고, load API를 호출해 모델을 준비한다
        
        ```python
        # ch03/multi_model_serving/app/**worker.py**
        
        class **TritonWorker(**ModelWorker):
           def **__init__**(self, model_metadata):
              self.triton_url = "0.0.0.0:8009"
              self.client = httpclient.InferenceServerClient(url=self.triton_url)
        
           def **_load_model**(self):
               load_url = (
                  f"http://{self.triton_url}/v2/repository/models/"
                  f"{self.model_metadata.name}/load"
               )
               response = requests.post(load_url)
        ```
        
    - 그럼 **추론 코드**를 살펴보겠습니다.
    - 다음 **predict function**에서는 먼저 입력 데이터를 모델 설정에 선언된 Triton 형식으로 변환한 뒤, 모델 추론을 실행하기 위해 Triton 서버(self.client.infer())에 **예측 prediction 요청**을 보냅니다:
        - Prediction은 input tensor를 Triton `InferInput`으로 변환하고 `client.infer()`를 호출한 뒤, 결과 tensor를 JSON으로 직렬화 가능한 list로 바꾼다.
        
        ```python
        # ch03/multi_model_serving/app/**worker.py**
        
        def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
           """Make prediction through Triton inference API
           Args:
             input_data: Dictionary containing input tensors for
                         the model
             Each key should be an input name and value should be a 
                numpy array Example: {"data_0": np.array(...)}
              
             Returns:
               Dictionary containing output tensors from the model
                 Each key is an output name and value is a numpy array
               """
        
            **# Create input tensors**
            inputs = []
            for name, data in input_data.items():
               if not isinstance(data, np.ndarray):
                 **# Convert list or other array-like data to numpy array**
                 shape = data["shape"]
                 content = data["data"]
                 **# Explicitly set dtype to float32**
                 array = np.array(content, dtype=np.float32).reshape(shape)
               else:
                 **# Ensure existing numpy array is float32**
                 array = data.astype(np.float32)
        
               input_tensor = httpclient.InferInput(name, array.shape, "FP32")
               input_tensor.set_data_from_numpy(array)
               inputs.append(input_tensor)
        
            **# Hardcode output name for DenseNet model : 단순화된 예시(DenseNet 모델 전용)**
            output_name = "fc6_1"
          
            **# Make inference request**
            response = self.client.infer(
               model_name=self.model_metadata.name,
               inputs=inputs,
               outputs=[httpclient.InferRequestedOutput(output_name)]
            )
        
            **# Get predictions and convert numpy arrays to lists for JSON serialization**
            predictions = {
                output_name: response.as_numpy(output_name).tolist()
            }
            
            return predictions
        ```
        
        - 입력 데이터(dict 또는 리스트)를 float32 numpy 배열로 변환
        - httpclient.InferInput으로 Triton이 요구하는 텐서 포맷 생성
        - self.client.infer()로 Triton에 추론 요청 전송
        - 결과(response.as_numpy(...))를 JSON 직렬화 가능하도록 .tolist()로 변환
        
    - 마지막으로, **모델 언로드 unload 요청**을 보내서 **Triton 서버의 리소스를 정리**해 봅시다.
    - 리소스 정리는 모든 멀티 모델 서빙 시스템에서 매우 중요한 부분으로, 제한된 컴퓨팅 및 메모리 자원을 회수해 다른 모델을 서빙하는 데 사용할 수 있게 해줍니다:
        - Worker가 제거될 때는 Triton unload API를 호출해 backend 자원을 정리한다
        
        ```python
        # ch03/multi_model_serving/app/**worker.py**
        
        def __del__(self):
           **"""Cleanup: unload model when worker is destroyed"""**
           try:
             unload_url = (
                f"http://{self.triton_url}/v2/repository/models/"
                f"{self.model_metadata.name}/unload"
             )
             requests.post(unload_url)
           except:
               pass  # Ignore cleanup errors 
        ```
        
        - 워커 소멸 시 unload API를 호출해 Triton에서 모델을 내려 GPU/CPU 메모리를 회수합니다.
        - 멀티모델 환경에서는 리소스가 한정돼 있으므로, 다른 모델이 그 자리를 쓸 수 있도록 정리하는 게 중요하다
        
    - 자체 개발한 멀티 모드 서빙 시스템을 살펴봤으니, 자세한 서비스 설정 방법과 로컬 실행 단계는 저희 GitHub 저장소를 참고하시면 됩니다.
    
- **[실습6] Triton as a Model Server 를 백엔드로 연동 - Blog**
    - **실행 계획** - README.md
    - 사전 준비 : Docker 설치, (옵션) Nvidia Container Toolkit 설치 및 설정
    - **Triton Server Setup**
        
        !Figure 3-10. Triton을 multi-model service의 serving backend로 통합
        
        Figure 3-10. Triton을 multi-model service의 serving backend로 통합
        
        ```python
        # Create a model repository directory structure:
        mkdir -p model_dir/densenet_onnx/1
        
        # Create a model configuration file `model_dir/densenet_onnx/config.pbtxt`:
        name: "densenet_onnx"
        platform: "onnxruntime_onnx"
        max_batch_size: 0
        input [
          {
            name: "data_0"
            data_type: TYPE_FP32
            dims: [ 3, 224, 224 ]
          }
        ]
        output [
          {
            name: "fc6_1"
            data_type: TYPE_FP32
            dims: [ 1000 ]
          }
        ]
        
        # 디렉터리 확인
        **tree model_dir/**
        *model_dir/
        └── densenet_onnx
            ├── 1
            │   └── model.onnx
            ├── config.pbtxt
            └── densenet_labels.txt*
            
        
        # Start Triton server with explicit model control:
        # HTTP 8000/GRPC 8001/Metrics 8002 → 호스트 포트 8009/8010/8011로 매핑
        **docker run -p8009:8000 -p8010:8001 -p8011:8002 \
            -v $(pwd)/model_dir:/models \
            nvcr.io/nvidia/tritonserver:24.12-py3 \
            tritonserver --model-repository=/models --model-control-mode=explicit**  #(옵션) --gpus=1 
        
        # **nvcr.io/nvidia/tritonserver:24.12-py3** 컨테이너 이미지 9.6G 정도로 다운로드에 다소 시간 필요
        **docker images**
        *IMAGE                                   ID             DISK USAGE   CONTENT SIZE
        nvcr.io/nvidia/tritonserver:24.12-py3   e6d844f6cfd9       27.4GB          **9.63G***
        
        # 확인
        **docker ps**
        CONTAINER ID   IMAGE                                   COMMAND                  CREATED         STATUS              PORTS                                                                                                                                   NAMES
        8578e397c419   nvcr.io/nvidia/tritonserver:24.12-py3   "/opt/nvidia/nvidia_…"   2 minutes ago   Up About a minute   0.0.0.0:8009->8000/tcp, [::]:8009->8000/tcp, 0.0.0.0:8010->8001/tcp, [::]:8010->8001/tcp, 0.0.0.0:8011->8002/tcp, [::]:8011->8002/tcp   triton-densenet
        
        # 컨테이너 내부 프로세스 확인
        **docker exec -it triton-densenet ps -ef**
        UID          PID    PPID  C STIME TTY          TIME CMD
        root           1       0  0 13:59 ?        00:00:00 **tritonserver --model-repository=/models --model-control-mode=explicit**
        root         207       0 50 14:03 pts/0    00:00:00 ps -ef
        
        # (옵션) 
        **nvidia-smi**
        +-----------------------------------------------------------------------------------------+
        | NVIDIA-SMI 595.84                 Driver Version: 595.84         CUDA Version: 13.2     |
        +-----------------------------------------+------------------------+----------------------+
        | GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
        | Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
        |                                         |                        |               MIG M. |
        |=========================================+========================+======================|
        |   0  NVIDIA GeForce RTX 4070 ...    Off |   00000000:01:00.0  On |                  N/A |
        |  0%   37C    P8             12W /  285W |     **300MiB** /  16376MiB |      0%      Default |
        |                                         |                        |                  N/A |
        +-----------------------------------------+------------------------+----------------------+
        
        +-----------------------------------------------------------------------------------------+
        | Processes:                                                                              |
        |  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
        |        ID   ID                                                               Usage      |
        |=========================================================================================|
        |    0   N/A  N/A           30340      C   **tritonserver**                            **274MiB** |
        +-----------------------------------------------------------------------------------------+
        
        ```
        
    - 사용
        
        ```mermaid
        sequenceDiagram
        
            participant Repo as Model Repository
            participant App as Multi-Model Service
            participant Triton as Triton Server
            participant Model as Model
        
            Note over Repo: /models/densenet_onnx
        
            App->>Triton: POST /repository/models/.../load
        
            Triton->>Repo: Model File Read
        
            Repo-->>Triton: Model
        
            Triton->>Model: Load into Memory
        
            App->>Triton: /models/.../infer
        
            Triton->>Model: Inference
        
            Model-->>Triton: Result
        
            Triton-->>App: Prediction
        ```
        
        ```python
        # 현재 모델 로드 확인
        **curl -s http://localhost:8001/models | jq
        *...***
        
        # Triton의 model management API로 로드 요청
        ## 포트 8009는 앞서 컨테이너 실행 시 -p8009:8000으로 매핑한 Triton HTTP 포트입니다.
        ## 성공하면 빈 응답 + HTTP 200이 돌아오고, 실패(설정 오류 등)면 에러 메시지가 담긴 JSON과 함께 4xx/5xx가 옵니다.
        **curl -X POST http://localhost:8009/v2/repository/models/densenet_onnx/load**
        
        # 모델 로드 확인 : 200 응답 여부
        # (참고) 언로드 .../densenet_onnx/unload
        **curl -v http://localhost:8009/v2/models/densenet_onnx/ready**
        
        # 로그 확인
        **docker logs triton-densenet**
        ...
        I0808 14:06:04.406318 1 model_lifecycle.cc:849] "successfully loaded 'densenet_onnx'"
        
        **# 추론 테스트 by 클로드코드** :  실제 테스트 이미지(tests/images/cat1.jpg)로 JSON payload 파일을 만들고 그걸 curl로 보내는 방식
        # 추론이 실제로 성공했고 (HTTP 200), cat1.jpg를 "EGYPTIAN CAT"(index 285, logit 11.5로 압도적 1위)로 정확히 분류했
        
        **1) payload용 JSON 만들기 (이미지 → 224x224 리사이즈 → /255 정규화 → CHW 변환 → Triton REST v2 형식):**
        import json, numpy as np
        from PIL import Image
        
        img = Image.open("tests/images/cat1.jpg").convert("RGB").resize((224, 224))
        arr = np.transpose(np.array(img).astype(np.float32) / 255.0, (2, 0, 1))
        
        payload = {
            "inputs": [{"name": "data_0", "shape": [3, 224, 224], "datatype": "FP32",
                        "data": arr.flatten().tolist()}],
            "outputs": [{"name": "fc6_1"}]
        }
        json.dump(payload, open("triton_payload.json", "w"))
        
        **2) curl로 추론 요청:**
        curl -X POST http://localhost:8009/**v2/models/densenet_onnx/infer** \
          -H "Content-Type: application/json" \
          -d @**triton_payload.json**
        
        응답의 outputs[0].data가 1000개짜리 ImageNet 클래스 로짓이고, argmax 인덱스를 densenet_labels.txt에서 찾으면 클래스명이 나옵니다.
        payload 파일과 응답은 스크래치패드(/tmp/.../scratchpad/triton_payload.json, triton_response.json)에 남겨뒀습니다.
        
        ```
        
        !image.png
        
    - tests by 클로드코드
        
        ```python
        **tests/test_models.py 코드 실행해줘.**
        
        tests/test_models.py는 **FastAPI TestClient**로 **app.server.app을 인메모리에서 직접 호출하며 4가지 프레임워크
        (Transformers×2, TorchVision, Triton) 전체를 검증하는 통합 테스트**입니다. 
        **실제로 돌려본 결과 7개 전부 통과했습니다 (아래).**
        
        **테스트 케이스별 내용**
        ┌──────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐
        │          테스트          │                                            검증 내용                                             │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_list_models         │ /models GET → available_models/loaded_models 키 존재 확인                                        │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_sentiment_model     │ 긍정/부정 문장 각각 /predict → _get_label()로 실제 HF 모델의 config.id2label을 불러와 예측       │
        │                          │ 라벨과 비교                                                                                      │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_spam_model          │ ham/spam 문장 각각 /predict → ham은 LABEL_0과 비교, spam은 응답만 확인 (아래 참고)               │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_image_model         │ TorchVisionWorker(mobilenet_v2)로 cat1.jpg 경로 문자열을 그대로 전달해 분류                      │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_image2_triton_model │ TritonWorker(densenet_onnx)로 이미지를 직접 전처리(resize→정규화→CHW)해 {"data_0": {"shape":..., │
        │                          │  "data":...}} 형태로 전달, 출력 shape (1000,) 검증                                               │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_invalid_model_id    │ 존재하지 않는 model_id → 404 확인                                                                │
        ├──────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ test_model_cache         │ 3개 모델 연속 호출 후 loaded_models 개수가 max_models=2 이하인지 확인 (LRU 캐시 상한 검증)       │
        └──────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘
        ...(생략)...
        ```
        
        ```python
        **tests/test_triton_densenet.py 코드 실행해줘.**
        
        3개 테스트 모두 통과했습니다 (0.277초):
        - test_model_loading — management API로 densenet_onnx 로드 → 200 OK
        - test_model_inference — cat1.jpg를 224×224 정규화 후 추론 요청 → fc6_1 shape (1000,) 확인, top prediction이 정수 인덱스인지 확인
        - test_model_unloading — unload API 호출 → 200 OK
        
        ```
        
    - 실습 리소스 정리
    

### **Trade-offs in Multi-Model Serving Designs**

- **멀티 모델 서빙 과제** : 사용자 경험 - *Cold start latency , Hot model scaling*
    - 멀티 모델 서비스는 하나의 서빙 인스턴스나 컨테이너 내에서 여러 모델을 공동 호스팅하도록 설계되어 GPU, CPU, 메모리 자원을 효율적으로 공유할 수 있다는 것을 보셨습니다. 실시간 트래픽에 따라 동적으로 모델을 적재하고 해제할 수 있어 비용 절감과 가격 대비 성능 향상을 가능하게 합니다.
    - 멀티 모델 서빙은 많은 모델을 만들었지만 모두를 동시에 사용할 필요가 없을 때 특히 유용합니다. 예를 들어, 하루에 3~4시간만 실행되는 예약 처리 작업이 있다고 가정해 봅시다. 각 모델마다 별도의 컨테이너를 할당하는 대신, 필요할 때 모델을 불러와 작업을 실행하고, 이후에는 해제하여 다른 모델이나 작업에 자원을 할당할 수 있습니다. 또 다른 예로, 1,000명의 고객을 위해 1,000개의 모델을 학습시켜야 할 수도 있습니다. 모든 모델이 동시에 사용되는 것은 아니므로, 시스템이 최대 200개의 모델만 동시에 호스팅하도록 제한하고, 요청이 도착할 때마다 필요에 따라 모델을 불러올 수 있습니다.
    - **멀티 모드 서빙 과제**
        - 모델별 dependency와 framework가 다를 수 있다.
        - model load/unload가 latency spike를 만든다.
        - hot model과 cold model의 traffic 차이가 크다.
        - 모델 cache eviction 정책이 성능과 비용에 직접 영향을 준다.
        - 보안, 격리, observability가 single-model보다 복잡하다.
        
    - **멀티 모드 서빙이 비용 절감에 도움**이 된다는 점은 분명하지만, 실제 현장에서 **가장 큰 두 가지 과제**는 모두 **사용자 경험**에 있습니다:
        - ***Cold start latency***
            - 현재 로드되어 있지 않은 모델에 대한 요청이 들어오면, 서빙 인스턴스는 모델 파일을 다운로드하고 메모리에 로드해야 하며, 캐시가 가득 찬 경우 다른 모델을 제거할 수도 있습니다. 이 과정에서 몇 초, 심지어 **수십 초의 지연이 발생할 수 있어 사용자 경험을 저하**시킵니다. 많은 모델이 콜드 상태인 트래픽이 많은 상황에서는 요청 타임아웃과 하위 애플리케이션에서 연쇄적인 장애가 발생할 수 있습니다.
        - ***Hot model scaling***
            - 특정 모델에 갑자기 많은 트래픽이 몰리면, 부하가 커짐에 따라 지연 시간이 증가합니다. 이 **모델을 확장하는 것은 비단순**한데, 각 인스턴스가 독립적인 모델 캐시를 가지고 있기 때문에 모델을 여러 인스턴스에 복제하고 라우팅 계층을 업데이트하는 일이 **복잡해집**니다. 이로 인해 엔지니어링 복잡성이 증가하고 성능 면에서 비결정적 동작이 나타납니다.
            
    - 모든 사람에게 딱 맞는 만능 해결책은 없습니다. 엔지니어로서 우리는 끊임없이 여러 가지를 저울질합니다.
    - 다음으로 살펴볼 두 가지 멀티 모드 서비스 방식은 각각 **비용과 지연 시간**이라는 **서로 다른 우선순위에 최적화**되어 있습니다.
    
- **A Cost-Optimized Multi-Model Design 비용 최적화 설계**
    - 이번 내용은 3장 후반부의 비용 최적화 멀티모델 아키텍처(그림 3-11) 설명입니다. 지금까지 실습한 multi_model_serving 코드는 이 큰 그림의 일부(B+C)에 해당하고, 이번 절은 **거기에 빠져있던 상위 레이어(A)를 추가한 버전**입니다.
    - **핵심 구조**
        - **B + C (지금까지 실습한 부분)**: 각 "멀티모델 서빙 인스턴스" 안에 모델 로딩·메모리 관리·호스팅 로직이 캡슐화됨.
            - **프론트엔드(B)**: 웹 API, 캐싱, 모델 관리 : FastAPI + ModelManager(LRU 캐시) + ModelEngine(Factory) 역할 ← 실습 확인
            - **백엔드(C)**: 실제 추론 실행 + 리소스 최적화 : 실무에서는 대부분 Triton 같은 전용 서버에 위임 ← 실습 TritonWorker 확인
        - **A (이번에 새로 추가되는 부분)**: **모델 서비스 API와 라우팅 로직**. 어떤 모델이 어떤 인스턴스에 로드돼 있는지 매핑을 유지하면서:
            1. **콜드 스타트 최소화** : 이미 해당 모델이 로드된 인스턴스로 요청을 라우팅
            2. **핫 모델 수평 확장** : 모델별 레플리카 수를 추적해, 트래픽이 몰리는 모델은 여러 인스턴스에 복제 배치
            3. **빈 패킹(bin-packing)** : 모델들을 최소한의 서버 수에 몰아서 배치해 자원 사용을 최적화 (전체 인스턴스 대수를 줄여 비용 절감)
    - 즉, 우리가 실습한 것은 인스턴스 하나(B+C) 였고, 그림 3-11은 **그 인스턴스를 여러 개 두고, A라는 라우팅/스케줄링 계층**이 그 위에서 "어떤 모델을 어느 인스턴스에 얼마나 띄울지"를 **조정하는 상위 설계**입니다.
        
        
    - 먼저 1장에서 다룬 개념을 바탕으로 추가적인 세부사항과 정교화를 반영한, 비용 효율적인 멀티모드 아키텍처(그림 3-11)를 살펴보겠습니다(그림 1-8과 1-10 참조). 이 아키텍처는 이 장에서 탐구한 개념들로부터 파생된 것입니다.
    - 그림 3-11의 설계는 비용 효율성을 최적화하며, 다양한 모델 간에 서빙 자원을 공유하는 데 중점을 두고, **콜드 스타트 지연 시간**과 **핫 모델 확장** 문제를 완화하려고 합니다.
        
        !Figure 3-11. 비용 효율에 최적화된 multi-model serving design
        
        Figure 3-11. 비용 효율에 최적화된 multi-model serving design
        
    - 이 아키텍처에서는 모델 로딩, 메모리 관리, 호스팅과 관련된 모든 로직이 각 멀티 모드 서빙 인스턴스 내에 캡슐화되어 있습니다(그림 3-11의 B와 C 부분).
    - 서빙 프론트엔드는 웹 API, 캐싱, 모델 관리를 담당하고, 백엔드는 추론 실행과 자원 최적화를 책임집니다. 실제로 대부분의 개발자들은 Triton과 같은 모델 서버 솔루션을 서빙 백엔드로 사용합니다.
    - 이 설계의 핵심 부분은 A 부분에 나와 있는데, **모델 서비스 API와 라우팅 로직**입니다. 이 컴포넌트는 모델과 서빙 인스턴스 간의 매핑을 유지하며, 다음을 가능하게 합니다:
        - 모델이 이미 로드된 인스턴스로 요청을 전달해 콜드 스타트를 최소화합니다.
        - 모델별 복제본 수를 추적하고 인스턴스에 모델을 분산시켜 핫 모델을 수평적으로 확장합니다.
        - 빈 패킹 전략을 적용해 최소한의 서버 수에 모델을 적재함으로써 백엔드에서 모델 트래픽을 효율적으로 분산시키고 자원 사용을 최적화합니다.
        
    - **이 설계의 한계**
        - **반응형(reactive) 시스템**: 트래픽 패턴이 이미 나타난 후에 대응하는 구조라 항상 수요를 뒤쫓는 형태 — 갑작스러운 트래픽 급증 시 예측 지연(prediction latency)이 늘어나는 건 구조적으로 피할 수 없음
        - **운영 복잡도 증가**: 라우팅 로직·스케일링 결정·인스턴스 간 캐시 상태 일관성까지 관리해야 해서, 운영/디버깅/유지보수 난이도가 크게 올라감
        
    - 하지만 이러한 접근 방식에도 어려움이 존재합니다. 이 시스템은 반응형으로, 교통 패턴이 나타난 후에 그에 맞춰 조정됩니다. 즉, 수요에 계속 뒤처지게 되고, 갑작스러운 트래픽 급증이 있을 때는 예측 지연 시간이 불가피하게 늘어납니다. 라우팅 로직, 확장 결정, 캐시 상태를 인스턴스 간에 관리하는 것은 복잡성을 증가시켜 운영, 디버깅, 유지보수를 더 어렵게 만듭니다.
    
- **A Latency-Optimized Multi-Model Design 지연 시간 최적화 설계**
    - 분산 시스템에서 흔한 트레이드오프인 "용량(capacity)을 희생해서 성능을 얻는다"는 전략을 멀티모델 서빙에 적용한 버전.
    - 3-11의 "**part A(공용 라우팅+빈패킹)**"가 여기서는 "**part A(모델별 전용 인스턴스 그룹) + part C(사전 프로비저닝 서비스)**"로 바뀐 구조입니다.
    
    !Figure 3-12. 지연 시간에 최적화된 multi-model serving design
    
    Figure 3-12. 지연 시간에 최적화된 multi-model serving design
    
    ```python
    ┌────────────────┬───────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │                │          3-11 (비용 최적화)              │                **3-12 (지연시간 최적화)**                                                                                                                   │
    ├────────────────┼───────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │ 자원 배치        │ 여러 모델이 인스턴스 자원을 공유              │ **모델마다 전용 인스턴스 그룹을 따로 프로비저닝**                                                                                                                  │
    ├────────────────┼───────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │ 모델 로딩 시점    │ 요청 시 온디맨드로 로드 (LRU 캐시 등)         │ **사전 프로비저닝**(part C: model-provisioning service) — 클라이언트가 예측 요청 전에 먼저 이 서비스를 호출해 해당 모델의 인스턴스 그룹을 미리 만들어둠                           │
    ├────────────────┼───────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │ 라우팅           │ 로드된 인스턴스를 찾아 라우팅 (동적)          │ **프로비저닝 완료 시 라우팅 맵이 갱신되고, 이후 요청은 그 맵을 참조해 전용 그룹으로 바로 전달 (정적)                                                                         │**
    └────────────────┴───────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
    ```
    
    - **장점**
        - 콜드 스타트 지연 없음 : 모델이 이미 항상 켜져 있는 전용 자원 풀에 상주
        - 독립적 확장(scale) : 모델별로 따로 스케일 아웃 가능, 인기 모델(hot model)에 특히 유리
        - 자원 정책을 모델별로 분리 가능 (운영 유연성 ↑)
        - 캐시 상태를 동적으로 관리하는 3-11보다 구조가 단순 → 유지보수/트러블슈팅이 쉬움
    - **단점**
        - **비용 효율이 낮음** : 트래픽이 적은 모델도 전용 자원을 계속 점유하므로, 어떤 모델이 얼마나 뜨거워질지 미리 예측하기 어려운 상황에서는 과다 프로비저닝(overprovisioning)으로 컴퓨트 낭비가 발생
        - 대신 꾸준하고 예측 가능한 수요를 가진 다수 모델을 서빙할 때는 매우 효과적
        
    - 지연 시간을 우선시하는 멀티 모드 접근법을 살펴보겠습니다. 분산 시스템 엔지니어링에서 흔히 사용되는 전략 중 하나는 용량을 희생하는 대신 성능을 향상시키는 것입니다. 이 설계에서는 여러 모델에 자원을 공유하는 대신, 각 모델마다 전용 리소스 그룹을 할당합니다. 이러한 리소스 제공 방식은 확장성을 높이고 콜드 스타트 시나리오에서 지연 시간을 크게 줄여, 수요가 많은 모델에 매우 효과적입니다. 서비스 아키텍처는 그림 3-12를 참조하세요.
    - 그림 3-11과 3-12의 설계에서 가장 큰 차이점은 멀티 모델 서빙 인스턴스를 전용 단일 모델 서빙 인스턴스 그룹으로 대체했다는 점입니다—모델당 하나의 인스턴스 그룹(부분 A).
    - 또 다른 중요한 변화는 모델을 필요할 때마다 불러오는 방식이 아니라는 점입니다. 대신 모델 프로비저닝 서비스(파트 C)에 의해 사전 프로비저닝됩니다. 예측 요청을 보내기 전에 클라이언트는 먼저 이 프로비저닝 서비스를 호출해 대상 모델을 위한 인스턴스 그룹을 생성해야 합니다. 프로비저닝이 완료되면, 서비스는 라우팅 맵에서 모델과 인스턴스 그룹 간 매핑을 업데이트합니다. 클라이언트가 예측 요청을 보내면, 모델 서비스 API가 라우팅 맵을 확인하고 해당 모델에 대해 미리 프로비저닝된 적절한 인스턴스 그룹으로 요청을 전달합니다.
    - 이 설계는 특히 핫 모델에서 지연 시간과 확장성이 뛰어난데, 각 모델이 전용의 항상 가동되는 리소스 풀을 갖고 있기 때문입니다. 콜드 스타트 지연이 없으며, 모델들이 독립적으로 확장될 수 있습니다. 운영자는 서로 다른 모델별로 별도의 리소스 정책을 정의할 수도 있어, 리소스 관리와 운영에 더 큰 유연성을 제공합니다. 또한 아키텍처가 더 단순해 비용 최적화 버전의 더 동적이고 캐시가 많은 방식보다 유지보수와 문제 해결이 쉽습니다.
    - 주요한 상충관계는 비용 효율성입니다. 많은 경우에 어떤 모델이 많은 트래픽을 받을지 예측하기가 어렵습니다. 그 결과, 활용도가 낮은 모델에 과도한 자원을 할당해 컴퓨팅 용량을 낭비할 수 있습니다. 그럼에도 불구하고, 여러 모델에 꾸준하고 예측 가능한 수요가 있을 때 이 방법은 매우 효과적입니다.
    - 궁극적으로 이 비교가 모델 서빙의 기본을 이해하면 비용, 성능, 운영의 간편함 등 특정 목표에 맞게 아키텍처를 맞춤화할 수 있다는 점을 전달하길 바랍니다.
        
        
    - **LLM에도 멀티모델 서빙이 적용되는 이유**
        - LLM은 보통 연산/메모리 요구량이 커서 단일 모델 서빙(single-model serving)으로 다루지만, 아래 두 케이스에서는 멀티모델 서빙 패러다임이 그대로 유효합니다.
            - **프리픽스 캐싱 + 라우팅**: 프롬프트 프리픽스가 같은 요청들을 이미 **해당 KV 캐시가 채워진 특정 레플리카로 라우팅해 중복 연산을 줄임** (→ 7장에서 다룸)
            - **다중 LoRA 어댑터 서빙**: 하나의 공유 베이스 모델 위에 **여러 LoRA 어댑터를 동적으로 로드/관리** — 테넌트별/유스케이스별 개**인화를 메모리 효율적으로 확장** (→ 10장에서 다룸)
        - 두 케이스 모두 "베이스 모델/KV 캐시라는 **무거운 리소스는 공유**하되, 그 위에 얹는 **가벼운 변형**(어댑터, 캐시 상태)을 어떤 레플리카가 갖고 있느냐에 따라 라우팅한다"는 점에서, 지금까지 배운 멀티모델 서빙의 로드/캐시/라우팅 개념이 그대로 재사용됩니다.
    
- Summary
    1. 단일 모델 서빙 (자체 구현)
        - API 서버, 워크로드 매니저, 모델 익스큐터, 모델 워커가 어떻게 협력해 동시 요청을 관리하고 실시간으로 결과를 반환하는지 훑어봄. 프
        - 롬프트 트래킹, 토큰 스트리밍, 동시 배칭 같은 심화 기법도 포함.
        - single_model_llm_serving 실습에서 직접 확인:
            - 수동 배칭이 매 스텝 KV 캐시 없이 O(n²)로 전체 시퀀스를 재계산한다는 것, 동시 스트리밍 요청 2개가 실제로 하나의 배치로 합쳐지는 것 등을 로그로 검증.
    2. vLLM과의 대조
        - 프로덕션급 프레임워크가 복잡도를 어떻게 추상화하면서도 세밀한 튜닝 여지를 남기는지 비교.
        - "내부에서 뭐가 일어나는지 알아야 프레임워크 설정을 제대로 튜닝하고 올바른 아키텍처 판단을 할 수 있다"
        - 동기 vllm.LLM.generate()를 비동기 핸들러에서 await 없이 호출하면 이벤트 루프가 막혀 동시 요청이 오히려 순차 처리됨
    3. 멀티모델 서빙으로 전환
        - 온디맨드 모델 로딩, 메타데이터 관리, LRU 기반 메모리 효율적 캐싱, NLP/Vision 등 프레임워크를 가로지르는 통합 API.
        - multi_model_serving에서 ModelManager(LRU max=2)와 ModelEngine(Factory)으로 Transformers/TorchVision 모델을 함께 서빙하며 확인
    4. Triton을 백엔드로 통합
        - 모델 호스팅·실행·최적화 책임을 전용 서버로 위임해 복잡도를 낮추고 확장성을 높임.
        - TritonWorker를 Docker 컨테이너로 실제 기동해 densenet_onnx를 로드/추론/언로드까지 end-to-end로 검증
    5. 두 가지 설계 패턴 비교
        - 비용 최적화(공유 자원 + 동적 로딩, 그림 3-11) vs 지연시간 최적화(전용 인스턴스 그룹 + 사전 프로비저닝, 그림 3-12).
        - 비용/성능/확장성/운영 복잡도 사이의 트레이드오프
    - 다음 챕터 예고
        - 4장은 이 기초 위에서 퍼블릭 클라우드(AWS Bedrock/JumpStart/DLC)와 오픈소스를 활용한 실제 케이스 스터디로 넘어갑니다.

### 멤버 경험 발표 : 김재호

- LiteLLM + vLLM 사내 온프렘 GPU로 운영 경험
    - vLLM의 잦은 버전 업데이트 → 업그레이드마다 API 변경 부담 ⇒ 재시작(다운타임) : 무중단 전략이 필요
    - LiteLLM AI Gateway : Optimization , Observability, Routing, Governance - Docs
        - 통합 게이트웨이 : OpenAI 호환 API 제공
        - 키/접근 관리 : Virtual Key + RBAC
        - 사용량/비용 추적
        - 로깅/관측성 : Langfuse 연동
        - 라우팅/로드밸런싱
    - 장애 경험
        - LLM 동작 중 사망 → 원인 : 버그로 패치
        - LiteLLM LB  기반 무중단 롤링 업그레이드 : 뒷단 vLLM vA, vLLM vB
        - 모델 최대 길이를 잘못 설정해서 기동 시 : 전수 조사 후 조치