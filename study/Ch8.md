- `질문` ***→ 학습을 하시고 스스로 아래 질문에 답변을 해보시기 바랍니다!***
    - 왜 vLLM의 Scheduler는 "모델을 모른 채" 최적화를 결정하고, GPUWorker는 "스케줄링을 모른 채" 연산만 하는가? 이 관심사의 분리(separation of concerns)가 없었다면 무엇이 문제였을까?
        - 이 질문에 답하려면 Scheduler(시스템 전반·모델 무관)와 ModelExecutor/GPUWorker(모델 아키텍처별)의 역할 분리, 그리고 이를 확장한 4계층 최적화 전략(Scheduler→ModelExecutor→모델 레이어→CustomOp)을 이해해야 합니다.
        - 답은 "미래 대비성(futureproof)"입니다 → 새 모델·새 하드웨어가 나와도 상위 계층을 재설계하지 않고 해당 계층만 교체하면 되는 구조.
            
            
    - vLLM이 요청 단위가 아니라 토큰 단위로 스케줄링한다는 것은 구체적으로 무엇이 다르며, num_computed_tokens와 num_tokens_with_spec의 차이를 좁히는 것이 왜 청크드 프리필·프리픽스 캐싱 같은 모든 최적화의 공통 메커니즘이 되는가?
        - "요청 우선순위 결정(큐)"과 "토큰 수준 스케줄링(예산 계산)"이 분리되어 있다는 설계 원칙이 핵심입니다.
        - 이 분리 덕분에 다양한 우선순위 정책(FCFS, 우선순위 기반)과 다양한 실행 최적화(추측 디코딩, 프리픽스 재사용 등)를 독립적으로 조합할 수 있습니다.
    - "어떤 프레임워크가 최고인가"가 아니라 "내 SLO·워크로드·운영 현실에 어떤 프레임워크가 맞는가"를 물어야 한다면, 구체적으로 어떤 축(하드웨어 벤더, prefill/decode 비중, 구조화 출력 필요성, 동시성 수준)이 vLLM/TensorRT-LLM/SGLang/llama.cpp 중 하나를 가리키게 만드는가? 그리고 3~6개월마다 재평가해야 한다는 결론은 "정답이 없다"는 뜻인가, 아니면 "정답이 계속 바뀐다"는 뜻인가?
        - 이 질문은 4개 프레임워크의 차별점(NVIDIA 특화 vs 범용성 vs 멀티벤더+에이전틱 vs 초경량 로컬)을 단순 암기가 아니라, "왜 특정 상황에서 특정 선택이 최적인가"라는 인과관계로 이해했는지를 시험합니다. 또한 "프레임워크 추상화 레이어"와 "탈출 계획(exit plan)"이라는 실무적 함의까지 짚어야 완전한 답이 됩니다.
        
- **챕터 8 소개 :** LLM 서비스 프레임워크 4종 - vLLM, TensorRT-LLM, SGLang, llama.cpp
    - **LLM 서빙 프레임워크**
        - 주제 전환: 앞 장들의 시스템 설계/최적화 이론에서 **실제 이를 구현하는 프레임워크** 계층으로 초점 이동
        - 다루는 4개 프레임워크: vLLM, TensorRT-LLM, SGLang, llama.cpp - 각기 다른 철학과 하드웨어 특성 보유
        - 핵심은 vLLM: 가장 널리 쓰이는 프레임워크이므로 아키텍처, 초기화·실행 과정, 스케줄링, 최적화 전략까지 심층 분석 → 이를 이해하면 다른 프레임워크 평가에도 도움
        - 나머지 프레임워크: 간결한 비교/의사결정 중심 개요 + 짧은 예제로 처리
        - 마무리: 서빙 프레임워크 평가 방법론 제시
        - 다음 장 예고: **9장에서는 이번 장의 이론을 실제로 vLLM 성능 튜닝에 적용**
    - **요약**
        - 이 장은 LLM 서빙 프레임워크 4종을 소개하되 vLLM을 중심으로 깊이 파고들어, 독자가 프레임워크 내부 동작 원리를 이해하고 자신의 상황에 맞게 평가할 수 있도록 돕는다.
        
    - 앞선 장들에서 우리는 LLM 서빙의 기초 ‘시스템 설계, 서비스 구현, 그리고 실용적인 최적화 기법’을 살펴보았습니다. 이번 장에서는 기반 계층, 즉 실제 프로덕션 환경의 제약 조건 아래에서 다양한 최적화 기법으로 모델 추론을 구현하고 실행하는 서빙 프레임워크로 초점을 옮깁니다. 실무에서 마주치게 될 가능성이 높은, 널리 채택된 네 가지 오픈소스 서빙 프레임워크인 vLLM, TensorRT-LLM, SGLang, llama.cpp를 다룰 것입니다. 각 프레임워크는 저마다 뚜렷한 철학, 하드웨어 특성, 실전 검증된 기술을 갖추고 있으며, 활발한 커뮤니티와 늘어나는 프로덕션 채택 사례의 뒷받침을 받고 있습니다.
    - 가장 폭넓게 활용되는 프레임워크인 만큼, vLLM에 대해서는 깊이 있게 다룰 것입니다: 그 아키텍처, 초기화 및 모델 실행 과정, 요청 및 토큰 단위 스케줄링, 그리고 계층화된 최적화 전략까지 살펴봅니다. vLLM의 내부 동작을 이해하면 실제로 LLM 프레임워크가 어떻게 작동하는지에 대한 강력한 직관을 얻게 되고, 다른 프레임워크들의 트레이드오프를 평가하기도 더 쉬워질 것입니다.
    - 이어서 나머지 프레임워크들을 의사결정 중심의 간결한 개요와 짧은 예제로 다룹니다. 그리고 서빙 프레임워크를 비교하는 데 사용하는 평가 방법으로 이번 장을 마무리합니다.
    - 이 장을 읽고 나면 LLM 서빙 프레임워크가 무엇인지, 왜 필요한지, 내부적으로 어떻게 작동하는지, 그리고 자신의 사용 사례에 맞게 어떻게 평가해야 하는지에 대해 탄탄한 이해를 갖추게 될 것입니다. 다음 장에서는 이러한 최적화 기법과 서빙 프레임워크를 실전에 적용하여 vLLM 서빙 프레임워크로 LLM 성능을 튜닝하는 방법을 다룰 것입니다.
    
- **핵심 요약** : LLM Serving Framework가 GPU, KV Cache, Request, Token을 어떻게 스케줄링하고 실제 모델 실행으로 연결하는지 이해
    - `vLLM`, `TensorRT-LLM`, `SGLang`, `llama.cpp` 네 가지를 다루지만, 가장 깊게 설명하는 것은 **vLLM 내부 구조**입니다.
    - 특히 `LLMEngine → EngineCore → Scheduler → ModelExecutor → GPUWorker → GPUModelRunner` 흐름을 이해하면 다른 LLM Serving Framework도 훨씬 쉽게 볼 수 있습니다.
    - 이 장은 LLM serving framework가 왜 필요한지와 vLLM, TensorRT-LLM, SGLang, Llama.cpp의 특징을 비교한다. 핵심은 LLM serving framework가 단순 inference wrapper가 아니라 scheduler, KV cache manager, model executor, worker, distributed execution, optimization layer를 포함하는 runtime이라는 점이다.
    - Framework 선택은 "어느 것이 절대적으로 최고인가"보다 workload와 운영 조건에 맞는지를 기준으로 해야 한다. Online serving, high-throughput batch serving, NVIDIA GPU 최적화, structured generation, edge/local inference 등 요구사항에 따라 적합한 framework가 달라진다.
    

### **Why We Need Specialized LLM Serving Frameworks**

- **요약**
    - **범용 서빙 프레임워크**(TensorFlow Serving, TorchServe, Triton)는 **이미지/정형 데이터용으로 설계**되어 **LLM에는 부적합**하며, 이 때문에 **전문 LLM 서빙 프레임워크가 필요**하다.
    - **LLM 서빙의 5가지 고유 과제:**
        1. 자기회귀적 생성 : 토큰 단위 순차 생성으로 세션이 길게 유지됨
        2. 컨텍스트 길이 폭증 : 입력 크기 편차가 극단적(수 토큰~백만 토큰), KV 캐시가 병목
        3. 연속 배칭 필요성 : 가변 길이 요청에 정적 배칭은 비효율적
        4. 스트리밍 요구 : TTFT를 수백 ms 이내로, 토큰 단위 실시간 스트리밍 필요
        5. 자원 활용 압박 : 고가의 GPU를 낭비 없이 최대한 활용해야 함
    - **해결책**:
        - **vLLM, TensorRT-LLM, SGLang** 등은 페이지 단위 KV 캐싱, 연속 배칭, LLM 전용 양자화, 추측 디코딩 등의 혁신으로 이 문제들을 해결
        - **→ 처리량 증가 + 지연 시간 감소 → LLM 서빙의 표준**으로 자리잡음
    
- **책 본문 번역**
    - **전문 LLM 서빙 프레임워크가 필요한 이유**
        - LLM 시대 이전에도 TensorFlow Serving, TorchServe, 그리고 NVIDIA Triton과 같은 범용 추론 플랫폼 등 이미 많은 범용 모델 서빙 프레임워크가 존재했습니다. 이러한 프레임워크와 플랫폼들은 원래 이미지 인식이나 정형 데이터 추론과 같은 딥러닝 워크로드를 위해 설계된 것이었습니다. 이런 워크로드들은 보통 입력 크기가 짧고, 텐서 형태가 고정되어 있으며, 지연 시간 요구사항을 예측할 수 있어서, 주된 최적화 대상은 대체로 배치 처리(batch processing)였습니다.
        - 이 책을 여기까지 읽었다면, LLM을 서빙하는 것이 이미지 분류기나 추천 모델과 같은 전통적인 머신러닝 모델을 서빙하는 것과는 근본적으로 다르다는 점이 명확해졌을 것입니다.
        
    - **LLM 서빙과 최적화는 다음과 같은 새로운 과제들을 제기합니다:**
        - 자기회귀적 생성(Autoregressive generation):
            - LLM은 한 번에 하나의 토큰씩 출력을 생성합니다. 이미지 모델과 달리, 추론 세션이 수 초에서 수 분 동안 열려 있을 수 있습니다.
        - 컨텍스트 길이의 폭증(Context length explosion):
            - 모델은 몇 개의 토큰부터 수십만, 심지어 백만 개에 이르는 입력 프롬프트까지 처리해야 합니다. KV 캐시 메모리 관리가 중대한 병목 지점이 됩니다.
        - 연속 배칭(Continuous batching):
            - 요청마다 입력과 출력 길이가 크게 다릅니다. 정적 배칭 전략은 GPU를 제대로 활용하지 못합니다.
        - 스트리밍 요구사항(Streaming requirements):
            - 사용자는 첫 토큰까지의 시간(TTFT, time to first token)이 수백 밀리초 이내이길 기대하며, 지속적인 토큰 스트리밍도 요구합니다.
        - 자원 활용(Resource utilization):
            - GPU는 비쌉니다. 파편화나 유휴 토큰으로 인한 GPU FLOPS 낭비는 대규모 환경에서는 용납될 수 없습니다.
        
    - 이러한 요구를 충족시키기 위해 **vLLM, TensorRT-LLM, SGLang과** 같은 새로운 부류의 프레임워크 **‘전문 LLM 서빙 프레임워크’**가 등장했습니다.
    - 이 프레임워크들은 페이지 단위 KV 캐싱, 연속 배칭, LLM 전용 양자화, 그리고 (앞 장에서 다룬) 추측 디코딩(speculative decoding) 같은 혁신 기술을 도입하여 **LLM만의 고유한 과제들을 해결**합니다.
    - 이러한 LLM 서빙 프레임워크의 도움으로 우리는 최신 가속기로부터 더 많은 처리량을 짜내고 지연 시간을 낮추어 훨씬 더 나은 효율을 얻을 수 있으며, 이것이 바로 이 프레임워크들이 LLM 서빙의 주류 선택지가 된 이유입니다.
    
- [PY] 07 - LLM 추론의 공학: 프로덕션 환경에서의 서빙 : Serving Sofrware 엔진, 오케스트레이션 **** - Youtube
    - **[ENGINE TIER] 엔진 티어**
        - vLLM · SGLang · TensorRT-LLM · TGI 네 프레임워크를 각각 같은 3단 구조(스케줄러 / KV 캐시 / 커널)로 나란히 비교
        
        !스크린샷 2026-08-23 오전 10.56.46.png
        
        - vLLM 카드(하단에 "PYTORCH FOUNDATION" 표기)를 빨간 화살표로 가리킴
        - 하단에 지원 하드웨어 목록이 빨간 박스로 강조: INTEL, NVIDIA, AMD, TPU, AWS
        - → vLLM이 PyTorch 재단 소속이며, 가장 폭넓은 하드웨어(인텔/엔비디아/AMD/TPU/AWS 실리콘)를 지원한다는 점을 시사
        
        !스크린샷 2026-08-23 오전 10.57.35.png
        
        - SGLang 카드를 화살표로 가리킴
        - 우측 하단에 "96 GPUs · DEEPSEEK REPRODUCTION" 박스 강조
        - **SGLang이 DeepSeek 모델 재현/대규모 클러스터(96 GPU) 서빙에서 활용된 사례**
        
        !스크린샷 2026-08-23 오전 10.58.18.png
        
        - TensorRT-LLM 카드(하단 "NVIDIA" 표기)를 화살표로 가리킴
        - TensorRT-LLM이 NVIDIA 전용이며, NVIDIA GPU의 최고의 성능 제공
        
        !스크린샷 2026-08-23 오전 10.59.42.png
        
        - TGI 카드(하단 "HUGGING FACE" 표기)를 화살표로 가리킴
        - 하단 "THE HUB" 박스 강조 → TGI가 Hugging Face Hub 생태계와 통합되어 있다
        
    - **[ORCHESTRATION TIER] 오케스트레이션 티어**
        - ENGINE TIER 상위에 ORCHESTRATION TIER : **NVIDIA Dynamo**, **llm-d** (Kubernetes-native)
            
            !https://github.com/ai-dynamo/dynamo
            
            https://github.com/ai-dynamo/dynamo
            
        - 오케스트레이션 계층이 **여러 노드에 걸친 분산 서빙을 조율하는 역할**
        - 오케스트레이션 계층은 엔진이 아니라 **스케줄러/라우터**이며, 실제 **연산**(토큰 생성)은 **각 노드의 엔진 티어가 담당**한다
        
        !스크린샷 2026-08-23 오전 11.04.25.png
        
        - **Prefill/Decode 분리 아키텍처**
            - NODE 1, 2에는 "PREFILL POOL", NODE 3, 4에는 "DECODE POOL" 라벨이 붙어 있음
            - "THE FLEET" 격자에는 파란색(위쪽 행)·노란색(아래쪽 행) 셀과 초록색 점들이 활성화되어 있어, 실제 요청이 prefill 단계와 decode 단계로 나뉘어 서로 다른 노드 풀에 분산 처리되는 흐름을 시각화
            - Prefill-Decode 분리(disaggregated serving) 기법을 표현: 연산 집약적인 prefill과 메모리 대역폭 집약적인 decode를 별도 노드 풀에서 처리해 자원 효율을 높이는 최신 서빙 아키텍처
        
        !스크린샷 2026-08-23 오전 11.05.27.png
        
        - "NO ENGINE, NO TOKEN" 개념 강조
            - PREFILL/DECODE 라벨이 사라지고, 대신 오케스트레이션 박스 3개 아래로 빨간 눈금이 표시되며 "NO ENGINE, NO TOKEN" 문구와 빨간 경고 다이아몬드 아이콘이 등장
            - **오케스트레이션 계층(Dynamo, The Fleet, llm-d) 자체는 추론 엔진을 실행하지도, 토큰을 직접 생성하지도 않는다는 핵심 메시지를 강조**.
            - 즉 **이 계층은 요청을 스케줄링/라우팅만 담당**하고, **실제 토큰 생성(추론)은 하위의 엔진 티어(vLLM 등)가 각 노드에서 수행**한다는 구조적 구분을 시각적으로 설명
    

### vLLM

- 들어가며
    - **vLLM의 핵심 가치:**
        - 긴 프롬프트·높은 메모리 요구·다중 사용자 동시 서빙이라는 **LLM 서빙의 근본적 어려움을 해결**하며 오픈소스/엔터프라이즈 양쪽에서 빠르게 확산
    - **핵심 기술:**
        - 페이지 단위 KV 캐싱 + 연속 배칭 → 처리량 향상, 지연 시간 감소 (프레임워크의 근본 혁신)
        - **부가 기능**: 양자화, 추측 디코딩, 스트리밍, 멀티 GPU/분산 실행
    - **적합한 사용 사례**: 챗봇/RAG, 배치 텍스트 생성, 멀티 테넌트 서빙, 실시간 애플리케이션
    - **인기 요인** (4가지):
        1. 실전 검증됨 (battle-tested)
        2. 오픈소스/자체 파인튜닝 모델과 쉬운 통합
        3. 깊은 튜닝 없이도 GPU 효율 극대화
        4. 기본 설정만으로 예측 가능한 성능
    - **아키텍처적 강점**: 깔끔하고 확장 가능한 설계 → **최신 연구 성과를 빠르게 흡수** + 활발한 커뮤니티 → 미래 지속 가능성
    - **이 절의 구성**: 시스템 설계 개요 → 모델 초기화 워크플로우 → 요청 처리 파이프라인 → 요청 우선순위화/프레임워크 수준 최적화(심화)
    
- **vLLM’s Architecture** - Docs
    - **vLLM의 두 가지 사용 방식**
        
        !https://docs.vllm.ai/en/stable/design/arch_overview/
        
        https://docs.vllm.ai/en/stable/design/arch_overview/
        
        - LLM Class : 인프로세스 파이썬 라이브러리, 서버 불필요, 오프라인/배치 워크플로우에 적합
        - API Server : vllm serve 명령으로 실행, OpenAI 호환 HTTP 엔드포인트, 프로덕션/멀티클라이언트/스트리밍용
    - **내부 아키텍처 계층 구조:**
        
        !https://docs.vllm.ai/en/stable/design/arch_overview/#llm-engine
        
        https://docs.vllm.ai/en/stable/design/arch_overview/#llm-engine
        
        ```bash
        **LLMEngine** (공개 API, 요청 생명주기 관리)
           └─ **EngineCore** (내부 루프, 전체 파이프라인 오케스트레이션)
                └─ **Scheduler** (자원 배분 "교통 관제사")
                     ├─ 담당: 토큰 스케줄링, 동적 배칭, 프리픽스 캐싱, 청크 프리필 (모델-무관 최적화)
                     └─ 산출물: **SchedulerOutput** ("작업 지시서")
                          └─ **ModelExecutor** (다중 워커 프로세스 조율)
                               └─ **GPUWorker** (프로세스별 디바이스/모델 생명주기 관리)
                                    └─ **GPUModelRunner** (실제 신경망 순전파 실행)
        ```
        
    - **핵심 설계 원칙:**
        
        !https://docs.vllm.ai/en/stable/design/arch_overview/#process-count-summary
        
        https://docs.vllm.ai/en/stable/design/arch_overview/#process-count-summary
        
        - **관심사 분리**: 시스템 레벨 최적화(**Scheduler**)와 모델별 최적화(**ModelExecutor/GPUWorker**)를 명확히 구분
        - SchedulerOutput이 스케줄러 ↔ 실행기 사이의 표준화된 계약(작업 배치, 토큰 수, 메모리 블록, 파라미터 포함) 역할을 하며, 실행 결과는 **다음 반복을 위해 다시 스케줄러로 피드백**됨
        - **프로세스 간 통신이 필요**한 이유는 vLLM이 **각 모델을 별도 프로세스/프로세스 그룹에서 실행**하기 때문 → ModelExecutor(조율)·GPUWorker(워커 인터페이스)·GPUModelRunner(실제 실행)의 3단 계층으로 이를 관리
        
        !https://docs.vllm.ai/en/stable/design/arch_overview/#model
        
        https://docs.vllm.ai/en/stable/design/arch_overview/#model
        
    - **다음 내용 예고**: 모델 초기화 → 요청 실행까지 이 컴포넌트들이 실제로 어떻게 연동되는지 살펴볼 예정
    
    - **vLLM의 아키텍처**
    - vLLM은 단일 모델 서비스 구성에 최적화되어 있으며, 각 인스턴스는 시작 시 하나의 모델을 초기화합니다. 해당 모델을 사용하는 두 가지 주요 방법을 제공합니다:
        - **LLM 클래스 (인프로세스 라이브러리)**
            - 별도의 서버나 웹 API 없이 오프라인 추론을 위한 순수 파이썬 로컬 인터페이스입니다.
            - 이 "라이브러리 모드"는 vLLM을 기존 서비스나 배치 워크플로우에 직접 연결하고 싶을 때 이상적입니다.
        - **API 서버 (OpenAI 호환)**
            - 멀티 클라이언트 및 프로덕션 사용, 스트리밍을 위한 독립형 HTTP 서버로, Chat/Completions API를 통해 쉽게 통합할 수 있습니다.
    - LLM 클래스를 사용하면 세밀한 제어, 낮은 오버헤드, 그리고 자체 서빙 스택과의 손쉬운 통합이 가능한 반면, API 서버는 더 폭넓은 배포를 위한 바로 사용 가능한 네트워크 엔드포인트를 제공합니다.
    - **기본 Python API 사용** : 먼저 **LLM 클래스 예제**를 살펴보겠습니다
        
        ```bash
        # initialize LLM model
        llm = LLM(
          model="Qwen/Qwen3-7B-Instruct",
          trust_remote_code=True, # Qwen uses custom modeling code
          dtype="float16",  # Use float16 for GPU
          max_model_len=32768,
          gpu_memory_utilization=0.8,
        )
        
        # run model generation requests
        outputs = llm.generate(prompts, sampling)
        ```
        
    - **OpenAI-compatible API server : vllm serve 명령**으로 **vLLM API 서버를 시작**합니다
        
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
        
    - 이제 그림 8-1에 나타난 vLLM의 주요 내부 컴포넌트로 넘어가겠습니다.
        
        !Figure 8-1. vLLM system architecture
        
        Figure 8-1. vLLM system architecture
        
        - 그림 8-1은 vLLM 시스템 아키텍처를 보여주며, Configuration(설정), Model Execution(모델 실행), Output Processing(출력 처리) 등의 기능과 관련하여 LLMEngine, EngineCore, Scheduler 같은 컴포넌트들 간의 관계를 상세히 나타낸다.
    - **LLMEngine과 EngineCore**
        - LLMEngine은 vLLM 추론 시스템의 **상위 수준 인터페이스이자 주 진입점**입니다. 사용자가 상호작용하는 **공개 API 역할**을 하는 동시에, 내부적으로는 하위의 모든 컴포넌트를 조율합니다.
        - LLMEngine은 모든 컴포넌트를 명확한 데이터 흐름을 가진 하나의 응집력 있는 시스템으로 통합합니다. 동기 및 비동기 서빙 시나리오를 모두 처리하며, 요청 처리 파이프라인의 오케스트레이션, 요청 큐 및 설정 관리 등 전체 요청 생명주기를 관리합니다.
        - **EngineCore는 vLLM 추론 엔진의 중앙 오케스트레이터**입니다. 모델 익스큐터, 출력 프로세서, 스케줄러를 통합하며, 모든 주요 컴포넌트를 조율하고 전체 요청 처리 파이프라인을 관리하는 "내부 루프(inner loop)" 역할을 합니다.
    - **스케줄러(Scheduler)**
        - 스케줄러 컴포넌트는 전체 추론 파이프라인의 "교통 관제사(traffic controller)" 역할을 합니다. **컴퓨팅 자원을 관리하고 요청 전반에 걸친 토큰 계산을 조**율합니다. 주된 책임은 제한된 연산 자원(GPU 메모리, KV 캐시 블록, 처리 용량 등)을 **경쟁 중인 요청들 사이에 효율적으로 배분하면서, 처리량을 극대화하고 공정한 접근을 유지**하는 것입니다.
        - 최적화 관점에서 보면, 스케줄러는 토큰 단위 스케줄링, 동적 배칭, 프리픽스 캐싱, 청크 단위 프리필과 같은 시스템 전반의, **모델에 무관한**(model-agnostic) **최적화 전략을 담당**합니다. **반면 모델별 최적화는 다음에 다룰 ModelExecutor와 GPUWorker 내부에서 적용**됩니다.
        - 스케줄러는 자신의 모델 실행 계획을 SchedulerOutput이라는 포괄적인 데이터 구조에 캡슐화합니다. 이는 스케줄러가 ModelExecutor에 전달하는 "작업 지시서(work order)" 역할을 하며, 한 배치의 요청들을 실행하는 데 필요한 모든 정보를 담고 있습니다. ModelExecutor는 이에 응답하여 모델을 실행합니다. SchedulerOutput은 본질적으로 ModelExecutor에게 이렇게 말하는 것과 같습니다: "여기 처리할 요청 배치가 있다. 각 요청이 받아야 할 토큰 수는 이만큼이고, 여기 입력 데이터와 파라미터가 있으며, 여기 이들에게 할당된 메모리 블록이 있고, 여기 특별히 처리해야 할 요구사항들이 있다."
        - **ModelExecutor는 SchedulerOutput의 정보를 사용**하여 **실제 GPU 배치**(평탄화된 input ID, 어텐션 메타데이터, KV 캐시 블록 포함)를 준비하고 모델의 순전파(forward pass)를 실행한 뒤, 결과를 다음 반복(iteration)을 위해 스케줄러에게 다시 반환합니다.
    - **ModelExecutor, (GPU) Worker, ModelRunner**
        - vLLM은 각 모델을 별도의 프로세스 또는 프로세스 그룹에서 호스팅하고 실행하기 때문에, 프로세스 간 통신을 처리하고, 분산 워커 그룹을 조율하며, 다양한 모델 순전파 실행 세부사항을 처리하기 위해 계층화된 아키텍처를 사용합니다. 이 아키텍처는 세 가지 컴포넌트로 구성됩니다:
            - ModelExecutor : 여러 워커 프로세스를 조율하고 관리
            - GPUWorker : 각 워커 프로세스에서 실행되며 디바이스/모델 생명주기를 관리하는 워커 인터페이스 역할
            - GPUModelRunner : 실제로 신경망을 실행
        
    - 이러한 관심사의 분리(separation of concerns)를 통해 각 컴포넌트는 컴포넌트 간의 깔끔한 인터페이스를 유지하면서 자신의 특정 모델 실행 책임에 집중할 수 있습니다. 그림 8-2는 이러한 계층화된 프로세스 간 모델 실행 아키텍처를 보여줍니다.
        
        !Figure 8-2. ModelExecutor, GPUWorker, GPUModelRunner의 관계
        
        Figure 8-2. ModelExecutor, GPUWorker, GPUModelRunner의 관계
        
        - 그림 8-2는 ModelExecutor, GPUModelWorker, GPUModelRunner, 그리고 실제 모델 구현(Actual Model Implementation)의 역할을 강조하며, 계층화된 프로세스 간 모델 실행 아키텍처를 나타낸다.
        
    - 이러한 아키텍처를 염두에 두고, 이제 모델 초기화부터 요청 실행까지 **이 컴포넌트들이 실제로 어떻게 함께 작동하는지 살펴**보겠습니다.
    
- **Model Initialization Workflow (with Multi-Process Worker)** : 모델 초기화 워크플로우 (멀티 프로세스 워커 포함)
    - **모델 초기화 4단계 워크플로우**
        
        !Figure 8-3. Multi-process serving setup에서 vLLM initialization workflow
        
        Figure 8-3. Multi-process serving setup에서 vLLM initialization workflow
        
        1. **메인 프로세스 초기화:**
            - LLM() 생성 → LLMEngine, Scheduler, KVCacheManager, MultiProcessExecutor 등 **주요 컴포넌트를 메인 프로세스에서 기동**
                
                ```bash
                # 여기서는 **단일 노드에 여러 GPU가 있는 배포**를 위해 **멀티프로세스(MP) 백엔드**를 사용했지만, 여러 머신에 걸친 구성을 위해서는 **"ray" 백엔드를 선택할 수도 있습**니다:
                
                lm = LLM(
                  model="Qwen/Qwen2.5-7B-Instruct",
                  # specify 4 workers
                  **tensor_parallel_size=4,**
                  # use multi-process model executor
                  **distributed_executor_backend="mp"**
                )
                ```
                
        2. **워커 프로세스 그룹 생성:** 
            - MultiProcessExecutor → **N개 워커 프로세스** spawn + rpc_broadcast_mq (메인 → 워커 명령/신호 전달용 **큐) 설정**
        3. **워커 프로세스 초기화:**
            - 각 워커 → GPUWorker 실행 → CUDA 디바이스 설정, 프로세스 간 통신 수립, 모델 로드 + worker_response_mq (워커 → ModelExecutor 결과 반환용 큐) 유지
        4. **모델 준비 및 로드:**
            - GPUModelRunner → 모델 레지스트리에서 구현체 조회 (예: Qwen → Qwen3NextForCausalLM) → **`__**init**__**` 호출 → 가중치를 GPU에 로드
    - **핵심 설정 파라미터:**
        - `tensor_parallel_size` : 워커(GPU) 개수 지정 (예제에서는 4)
        - `distributed_executor_backend` : 실행 백엔드 선택
            - "**mp**" (멀티프로세스): 단일 노드, 다중 GPU 배포에 적합
            - "**ray**": 여러 머신에 걸친(멀티 노드) 배포에 적합
    - **핵심 내용:**
        - 초기화는 메인 프로세스 → 워커 프로세스 생성 → 워커별 모델 로드의 순차적 흐름을 따름
        - **메인 프로세스와 워커 간 통신은 양방향 메시지 큐**(rpc_broadcast_mq는 명령 하달용, worker_response_mq는 결과 회신용)로 이루어짐
        - 실제 모델 구현체 선택은 내부 레지스트리 조회 방식으로 이루어져, 다양한 모델 아키텍처(Qwen 등)를 유연하게 지원
        
    - **모델 초기화 워크플로우 (멀티프로세스 워커 포함)**
    - 이번 절에서는 vLLM의 모델 초기화 워크플로우를 살펴봅니다. 내부 컴포넌트를 어떻게 기동하는지, 워커 프로세스 그룹을 어떻게 구성하는지, 모델을 소스로부터 GPU 메모리로 어떻게 로드하는지, 그리고 통신 링크를 어떻게 수립하는지를 다룹니다.
    - vLLM은 폭넓은 모델과 다양한 실행 방식 ‘단일 디바이스 서빙, 한 노드에서의 다중 디바이스 서빙, 심지어 멀티 노드 클러스터까지’ 을 지원하기 때문에, 초기화 로직이 복잡하게 느껴질 수 있습니다. 이를 이해하기 쉽게 만들기 위해, 오늘날 프로덕션에서 가장 흔히 사용되는 구성인 멀티프로세스 설정으로 LLM을 초기화하는 실용적인 예제에 초점을 맞추겠습니다. 이 과정의 시각화는 그림 8-3을 참고하세요.
        
        !Figure 8-3. Multi-process serving setup에서 vLLM initialization workflow
        
        Figure 8-3. Multi-process serving setup에서 vLLM initialization workflow
        
        - 그림 8-3은 vLLM의 멀티프로세스 실행 워크플로우를 보여주며, LLM 엔진, 익스큐터, GPU 워커들 간의 상호작용과 여러 디바이스에 걸친 통신 흐름을 강조한다.
    - 그림 8-3에 나타난 네 단계를 하나씩 살펴보겠습니다:
        1. **vLLM 메인 프로세스에서 모든 컴포넌트 초기화**
            - LLM() 인스턴스를 생성할 때, 모델 설정, 자원 사용량, 서빙 최적화 파라미터를 정의하는 **설정값들을 전달**합니다. 아래 예제에서는 vLLM이 Hugging Face의 Qwen 모델을 4개의 워커 프로세스로 구성된 **멀티프로세스 그룹을 사용해 호스팅**하도록 설정합니다. 여기서는 **단일 노드에 여러 GPU가 있는 배포**를 위해 **멀티프로세스(MP) 백엔드**를 사용했지만, 여러 머신에 걸친 구성을 위해서는 **"ray" 백엔드를 선택할 수도 있습**니다:
                
                ```bash
                lm = LLM(
                  model="Qwen/Qwen2.5-7B-Instruct",
                  # specify 4 workers
                  **tensor_parallel_size=4,**
                  # use multi-process model executor
                  **distributed_executor_backend="mp"**
                )
                ```
                
            - LLM 클래스는 vLLM 메인 프로세스 내에서 LLMEngine, Scheduler, KVCacheManager, MultiProcessExecutor를 포함한 모든 주요 컴포넌트를 초기화하고, 설정값을 해당 모듈들에 배포합니다.
        2. **워커 프로세스 그룹 생성**
            - 초기화 과정에서 MultiProcessExecutor는 분산 모델 실행을 위해 4개의 워커 프로세스를 생성(spawn)합니다. 또한 이 워커들에게 신호와 명령을 전달하기 위한 rpc_broadcast_mq 메시지 큐를 설정합니다.
        3. **워커 프로세스 초기화**
            - 각 워커 프로세스는 GPUWorker를 실행하며, 이는 모델 추론을 실행하고 MultiProcessExecutor와 통신하는 역할을 담당합니다.
            - GPUWorker는 CUDA 디바이스를 설정하고, 프로세스 간 통신을 수립하며, 워커 프로세스 내에서 모델을 로드하고 초기화합니다.
            - 예를 들어, GPUWorker는 추론 결과를 ModelExecutor에게 다시 전송하기 위한 메시지 큐(worker_response_mq)를 유지합니다.
        4. **모델 준비 및 로드**
            - GPUModelRunner는 설정된 모델 이름을 기반으로 올바른 모델 구현체를 찾아내는 역할을 담당합니다.
            - 이 예제에서는 vLLM의 내부 모델 레지스트리에서 Qwen 모델을 조회하여 Qwen3NextForCausalLM 구현체를 선택합니다.
            - 그런 다음 해당 클래스의 **`__**init**__**` 함수를 호출하여 모델 가중치를 GPU에 로드합니다.
    
- **Generation-Request Execution Workflow** : 생성 요청 실행 워크플로우
    - 모델이 vLLM에 로드, 초기화, 설정되어 나면 서빙할 준비가 된 것입니다.
    - **생성 요청을 처리하는 고수준 워크플로우를 4단계**
        
        !Figure 8-4. vLLM generation-request execution workflow
        
        Figure 8-4. vLLM generation-request execution workflow
        
    - **llm.generate(prompts, sampling_params)**를 실행하면 vLLM 내부에서는 다음과 같은 일이 일어납니다:
        1. **Processor 컴포넌트**가 입력 프롬프트를 토큰화하는 것을 포함해, 원시 입력값을 검증하고 전처리하여 **Request 객체**로 만듭니다.
        2. **LLMEngine이 실행 루프**를 돌리며 **EngineCore를 반복적으로 호출해 요청을 처리**합니다. EngineCore는 **Scheduler가 다음에 실행할 요청 배치와 처리할 토큰을 결정하도록 합니다**. Scheduler는 이 단계에서 페이지드 어텐션(paged attention), 연속 배칭(continuous batching) 같은 **다양한 최적화를 적용**합니다.
        3. EngineCore는 Scheduler로부터 **스케줄링된 토큰(SchedulerOutput)을 MultiProcessExecutor로 전달**합니다. **MultiProcessExecutor는 이 요청을 워커 프로세스에 전달**하고, **GPU 워커가 모델 forward pass를 실행해 주어진 토큰을 계산하도록 위임**합니다. 실제 모델 실행이 일어나는 곳이 바로 여기입니다.
        4. EngineCore는 **모델 출력을 출력 프로세서(Output Processor)로 전달**하고, **출력 프로세서는 이를 최종 응답으로 만들어 사용자에게 반환**합니다.
        
        | 단계 | 담당 컴포넌트 | 역할 |
        | --- | --- | --- |
        | 1 | Processor | 입력 검증·토큰화 → Request 객체 생성 |
        | 2 | LLMEngine → EngineCore → Scheduler | 다음 배치 결정, PagedAttention·Continuous Batching 등 최적화 적용 |
        | 3 | MultiProcessExecutor → GPU Worker | 실제 모델 forward pass 실행 |
        | 4 | Output Processor | 모델 출력 → 최종 응답 변환 |
        
    - **핵심: 역할이 명확히 분리**되어 있습니다
        - **Scheduler**는 "언제, 무엇을, 어떻게 배치할지"를 결정하는 **서빙 최적화(계획) 담당**이고, **GPUWorker**는 **실제 연산(모델 실행)만 담당**합니다.
        - 이 관심사 분리 덕분에 **vLLM은 배칭·스케줄링 최적화를 GPU 실행 로직과 독립적으로 개선**할 수 있습니다.
    
- **Scheduler Deep Dive** 스케줄러 심층 분석
    - **요약**
        - **vLLM Scheduler**는 "교통 관제탑" 역할을 하며, **5가지 핵심 책임**을 가집니다.
            - **자원 오케스트레이션** : WAITING/RUNNING 큐 관리, GPU 메모리·KV 캐시·토큰 예산 기반 동적 결정
            - **토큰 단위 스케줄링** :  prefill/decode를 분리하지 않고 요청이 아닌 토큰 단위로 스케줄링 → 더 세밀한 제어
            - **최적화 통합 허브** : 프리픽스 캐싱, 추측 디코딩, 청크드 프리필, 분산 KV 캐시 전송을 상황에 맞게 적용
            - **동적 부하 분산** : 도착/완료/선점 등 이벤트에 실시간 대응, 지연시간-처리량 균형
            - **생명주기 관리** : FCFS/우선순위 정책, 자원 부족 시 선점(preemption)
            
        - **스케줄링 사이클 흐름** (그림 8-5):
            
            !Figure 8-5. vLLM internal request scheduling logic
            
            Figure 8-5. vLLM internal request scheduling logic
            
            1. **초기화**: 신규/재개/실행중/선점된 요청 수집, 가용 토큰·인코더 예산 갱신
            2. **RUNNING 요청 우선 처리**: 이미 KV 캐시를 점유 중이므로 먼저 처리 → 이 과정에서 청크드 프리필, 프리픽스 캐싱, 추측 디코딩 적용, 필요 시 선점
            3. **WAITING 요청 처**리: 남은 예산 내에서 활성화, 동일한 최적화 혜택
            4. **후처리**: LoRA 어댑터 추적, 멀티모달 인코더 입력 준비, 추측 토큰 확정
            5. **SchedulerOutput 생성**: 스케줄링된 요청·토큰 수·KV 캐시 할당 정보를 묶어 모델 실행기(Executor)에 전달
            
        - **핵심 설계 원칙** : "우선순위 결정"과 "토큰 스케줄링"의 **분리**
            - 큐(WAITING/RUNNING) → 요청의 처리 순서를 결정 (FCFS, 우선순위 등)
            - `num_computed_tokens` vs `num_tokens_with_spec`의 차이 → 각 요청이 이번 스텝에 몇 개 토큰을 처리할지 결정
            
        - **정리**
            - 이 둘을 분리했기 때문에, 다양한 요청 우선순위 정책과 실행 최적화 기법을 서로 독립적으로 조합할 수 있는 유연한 구조가 만들어집니다.
            - 코드 레벨에서는 이 "처리된 토큰 수와 처리해야 할 총 토큰 수 사이의 간극을 좁히는 것"이 청크드 프리필, 프리픽스 캐싱 같은 최적화가 적용되는 핵심 메커니즘입니다.
        
    - **Scheduler는 vLLM 추론 파이프라인에서 생성 요청을 실행하는 중앙 교통 관제탑 역할**
        - 먼저 vLLM Scheduler를 형성하는 **핵심 고려사항**들을 살펴본 뒤, **요청 스케줄링 워크플로우**를 자세히 살펴보겠습니다.
            
            
        - **요청 리소스 오케스트레이션** *Request resource orchestration*
            - **Scheduler**는 요청이 도착한 순간부터 완료될 때까지 **전체 생명주기를 조율**합니다.
            - 들어오는 요청을 받아 별도의 `WAITING 큐`와 `RUNNING 큐`로 정리하고, GPU 메모리, KV 캐시 블록, 토큰 예산 같은 가용 연산 자원을 기반으로 **어떤 요청을 실행할지 동적으로 결정**합니다.
            - 또한 Scheduler는 추측 디코딩(speculative decoding), 프리픽스 캐싱(prefix caching), 멀티모달 입력 등 **복잡한 자원 할당 문제도 다룹**니다. **목표는 동시 요청 간 공정성을 유지하면서 처리량을 극대화**하여, 시스템 자원을 효율적이고 균형 있게 사용하는 것입니다.
        - **토큰 단위 자원 할당 및 스케줄링** *Token-level resource allocation and scheduling*
            - vLLM의 핵심 강점 중 하나는 prefill과 decode 단계를 분리하지 않고, **통합된 토큰 기반 스케줄링 방식**을 사용한다는 점입니다.
            - 각 요청을 하나의 단위로 취급하는 **요청 기반 스케줄러와 달리, vLLM의 Scheduler는 토큰 단위로 동작**합니다.
            - 매 스케줄링 스텝마다 최대 배치 크기, GPU 메모리 한도 같은 전역 제약을 지키면서 **각 요청이 처리할 수 있는 토큰 수를 결정**합니다.
            - **요청 기반 스케줄링 전략과 비교했을 때, 토큰 기반 스케줄링은 더 세밀한 제어를 제공**합니다.
            - 토큰 예산을 할당하고, 어텐션 상태를 위한 KV 캐시 블록을 관리하고, 멀티모달 모델의 인코더 입력을 지원함으로써 **요청 간 경쟁하는 요구를 조율**합니다.
            - 이 접근 방식은 전체 연산 부하가 시스템 한계 내에 머물면서도 **병렬 실행 기회를 최대화하도록 보장**합니다.
        - **최적화 통합 허브** *Optimization integration hub*
            - **Scheduler는 모델에 무관한(model-agnostic) 성능 최적화의 중앙 통합 지점 역할**을 합니다.
            - 프리픽스 캐싱(이전에 계산된 상태 재사용), 추측 디코딩(미래 토큰 예측), 청크드 프리필(긴 시퀀스의 효율적 처리), 분산 KV 캐시 전송(멀티 GPU 실행 지원) 같은 **기법들을 조율**합니다.
            - 중요한 점은, Scheduler가 이러한 최적화를 언제 어떻게 적용할지 **적응적으로 결정**한다는 것입니다.
            - 이 결정은 요청 특성, 자원 가용성, 전체 시스템 상태에 따라 이루어지며, 각 **최적화가 충돌이나 비효율을 일으키지 않으면서 성능을 개선**하도록 보장합니다.
        - **동적 부하 분산** *Dynamic load balancing*
            - Scheduler는 시스템 자원과 **요청 특성을 모니터링**하여 **지연 시간과 처리량의 균형을 맞추는 실시간 결정**을 내립니다.
            - 도착, 완료, 선점(preemption), 자원 한계 같은 **동적 이벤트에 대응**하여 어떤 요청을 실행할지, 몇 개의 토큰을 처리할지, 언제 최적화를 적용할지를 **재평가**합니다.
            - 효율적인 큐 관리와 자원 할당을 통해 워커들과 협력하여 최적의 성능을 유지합니다.
        - **요청 생명주기 관리** *Request lifecycle management*
            - Scheduler는 각 요청을 `WAITING 큐` 도착부터 `RUNNING 큐` 실행, **최종 완료까지 생명주기 전반에 걸쳐 모니터링**합니다.
            - 또한 Scheduler는 **선입선출**(FCFS)이나 **우선순위 기반 정렬** 같은 고급 스케줄링 정책을 적용해 실행 순서를 결정합니다.
            - 자원이 부족할 때는 우선순위가 낮은 요청을 **선점(preempt)하여 우선순위가 높은 작업에 용량을 재할당**할 수 있습니다.
            - 또한 요청 상태 간의 원활한 전환을 관리하여 효율성과 공정성을 모두 보장합니다.
        
    - **Request scheduling workflow** 각 생성 요청에 적절한 토큰 수를 결정하여 모델의 forward pass에 전달
        - **Scheduler의 핵심 임무**는 들어오는 각 **생성 요청에 적절한 토큰 수를 결정**하여 **모델의 forward pass에 전달**하는 것입니다. **모델과 하드웨어 용량을 최대한 활용**하면서 균형 잡힌 사용자 경험을 유지하기 위해, Scheduler는 이 토큰 선택 과정에서 **다양한 모델 무관 최적화를 적용**합니다. 전체 요청 스케줄링 로직은 그림 8-5에 나와 있습니다.
            
            !Figure 8-5. vLLM internal request scheduling logic
            
            Figure 8-5. vLLM internal request scheduling logic
            
        - 그림 8-5에서 볼 수 있듯이, **vLLM 스케줄러는 내부 스케줄 상태를 구축**하는 것으로 **스케줄링 사이클을 시작**합니다. 이 상태는 새로 도착한 요청, 재개가 필요한 이전 일시 중지 요청, 현재 실행 중인 요청, 이전에 선점된 요청 등 관련된 **모든 요청을 수집**합니다. 이 초기화 단계에서 스케줄러는 현재 **토큰 예산 내에 남은 디코딩 토큰 수, 멀티모달 워크로드를 위해 남은 인코더 용량 같은 가용 자원 회계도 업데이트**합니다. 이 초**기 상태가 이후의 모든 결정을 규정**합니다.
        - 초기화가 끝나면, 스**케줄러는 두 번의 우선순위 웨이브로 연산을 할당**하기 시작합니다. `RUNNING 요청`이 먼저 처리되는데, 이미 **KV 캐시 블록을 점유하고 있고 활성 생성 타임라인**을 갖고 있기 때문입니다. 각 실행 중인 요청에 대해 스케줄러는 **새로 생성해야 할 토큰 수를 결정**하고, 멀티모달 입력이 관련된 경우 인코더 제약을 검증하며, **실행을 계속하기에 충분한 KV 캐시가 있는지 확인**합니다.
        - 이 단계에서 vLLM은 지연 시간을 크게 줄이고 처리량을 향상시키는 **여러 최적화를 적용**합니다. **청크드 프리필**은 전체 프롬프트를 한 번에 인코딩하지 않고도 긴 프롬프트를 부분적으로 처리할 수 있게 합니다. **프리픽스 캐싱**은 스케줄러가 서로 다른 요청 간에 동일한 프리픽스에 대해 이전에 계산된 KV 캐시 블록을 재사용할 수 있게 합니다. 한편 **추측 디코딩**은 초안 토큰을 미리 생성하여, 이 예측이 나중에 모델의 검증된 출력과 일치하면 더 빠른 생성을 가능하게 합니다. 어느 시점에서든 자원이 부족해지면, 스케줄러는 공정성과 일관성을 보장하기 위해 **우선순위가 낮은 작업을 선점**할 수 있습니다.
        - **모든 RUNNING 요청 처리가 끝나면**, **스케줄러**는 `WAITING 큐`로 넘어갑니다. 남은 토큰 및 인코더 **예산 내에 들어갈 수 있는 요청들은 활성화**되어 현재 **실행 배치에 포함**됩니다. `WAITING 요청`은 **더 낮은 우선순위를 받지만**, 해당되는 경우 `RUNNING 요청`과 **동일한 최적화의 혜택**을 받습니다.
        - **요청 할당이 완료**되면, 스케줄러는 다가오는 디코딩 스텝에 필요한 **추가 조율 작업을 수행하는 후처리 단계**에 들어갑니다. 이 단계에서 스케줄러는 **각 요청에 활성화되어야 할 LoRA 어댑터를 추적**하고, 멀티모달 작업을 위한 인코더 입력을 준비하며, **추측 디코딩에 사용될 초안 토큰 예측을 확정**합니다. 이 단계의 목표는 모든 스케줄링 결정을 깔끔하고 **실행 가능한 계획으로 통합**하는 것입니다.
        - 마지막으로, **스케줄러는 전체 사이클의 결과를 요약하는 SchedulerOutput 객체를 조립**합니다. 이 출력은 **새로 스케줄링된 요청들, 각 요청에 할당된 토큰 수, 배치 전체의 총 스케줄링된 토큰 수를 나열**합니다. 또한 KV 캐시 할당, 준비된 인코더 입력, 멀티모달 라우팅 정보 등 모델 실행기에 필요한 **메타데이터**도 포함합니다. 모델 실행기는 이 출력을 사용해 **새 토큰을 생성하는 실제 forward pass를 실행**합니다.
            
            !https://www.aleksagordic.com/blog/vllm
            
            https://www.aleksagordic.com/blog/vllm
            
        - 또한, 모델에 무관한 요청-토큰 스케줄링 프로세스를 지원하기 위해 **vLLM Scheduler는 토큰 수준에서 동작**합니다. RUNNING 큐부터 WAITING 큐 순으로 각 요청을 순회하며, 다음 forward pass에 어느 요청의 몇 개 토큰을 포함할지 결정하고, 전체 토큰 수가 모델의 한계 내에 머물도록 보장합니다.
        - 구현 수준에서 Scheduler는 `num_computed_tokens`(이미 처리된 토큰 수)와 `num_tokens_with_spec`(프롬프트, 출력, 추측 토큰을 포함한 처리해야 할 총 토큰 수) 사이의 간극을 최소화하려 합니다. 이 **간극을 좁히려는 목표가 스케줄링 중 적용되는 일련의 최적화 전략**을 이끕니다. 코드로는 다음과 같습니다:
            
            ```bash
            while req_index < len(self.running) and token_budget > 0:
                request = self.running[req_index]
                num_new_tokens = (request.num_tokens_with_spec +
                                  request.num_output_placeholders -
                                  request.num_computed_tokens)
            ```
            
            <aside>
            👉🏻
            
            **우선순위 결정과 최적화의 분리**
            vLLM 스케줄링에서 요청 큐는 요청 처리 순서를 결정하고, num_computed_tokens와 num_tokens_with_spec의 비교는 각 요청이 실행할 수 있는 토큰 수를 결정합니다.
            이러한 **요청 우선순위 결정**과 **토큰 수준 스케줄링**의 **명확한 분리** 덕분에, Scheduler는 다양한 요청 우선순위 전략과 LLM 실행 최적화를 **하나의 통합된 프레임워크 안에서 결합**할 수 있으며, 동시 요청 간 공정성을 유지하면서도 시스템 자원을 효율적으로 사용할 수 있습니다.
            
            </aside>
            
        
    - **Applying model optimization techniques** 모델 최적화 기법 적용
        - 스케줄링 과정에서 vLLM은 6장과 7장에서 소개한 여러 최적화 기법 ‘청크드 프리필, 프리픽스 캐싱, 문법 제약 유한상태기계를 통한 가이디드 디코딩, PD 분리(prefill-decode disaggregation) 등’을 통합합니다.
        - 실제로 어떻게 동작하는지 보여주기 위해 두 가지 간단한 예시를 살펴보겠습니다.
            - **청크드 프리필** *Chunked prefill*
                - Scheduler는 요청에 대해 실행되는 **새 토큰 수가 설정된 prefill 청크 크**기(`scheduler_config.long_prefill_token_threshold`)를 **초과하지 않도록 보장**합니다:
                
                ```bash
                if (0 < self.scheduler_config.long_prefill_token_threshold \
                                  < num_new_tokens):
                   num_new_tokens = self.scheduler_config.long_prefill_token_threshold
                ```
                
            - **프리픽스 캐싱** *Prefix caching*
                - Scheduler는 로컬 또는 원격 캐시에서 계산된 KV 캐시 블록을 재사용하기 위해 프리픽스 캐싱을 처리합니다:
                
                ```bash
                # 이미 캐시된 토큰 가져오기.
                if request.num_computed_tokens == 0:
                    # 로컬에 캐시된 토큰 가져오기.
                    new_computed_blocks, num_new_local_computed_tokens = \
                          self.kv_cache_manager.get_computed_blocks(
                                           request)
                
                    # 외부에 캐시된 토큰 가져오기.
                    if self.connector is not None:
                        num_external_computed_tokens, load_kv_async = (
                            self.connector.get_num_new_matched_tokens(
                                request, num_new_local_computed_tokens))
                ```
                
            
        - 가이디드 디코딩 **guided decoding** , **prefill-decode** 분리 같은 다른 최적화 기법과 구현도 직접 탐구해 보길 권장합니다.
        - Scheduler.py 코드 구현이 좋은 출발점이며, 추가로 Aleksa Gordić의 블로그 글 "Inside vLLM: Anatomy of a High-Throughput LLM Inference System"도 훌륭한 참고 자료입니다.
            
            !image.png
            
            !https://www.aleksagordic.com/blog/vllm
            
            https://www.aleksagordic.com/blog/vllm
            
            !image.png
            
- `도전과제` vLLM 주요 동작의 소스 코드 분석 해보기 - Github
- `도전과제` Aleksa Gordić의 블로그 글 Inside vLLM: Anatomy of a High-Throughput LLM Inference System 정리해보기
    - Inside NVIDIA GPUs: Anatomy of high performance matmul kernels 정리해보기 - Blog
- **vLLM’s Layered Optimization Strategy** vLLM의 계층적 최적화 전략
    - vLLM의 핵심 설계 철학은 **"최적화는 그것이 속한 올바른 계층에서 이루어져야 한다"**는 것입니다.
    - **LLM 아키텍처와 하드웨어가 매우 빠르게 변화하기 때문에, 특정 모델·하드웨어에 최적화를 하드코딩하면 시스템이 금방 낡아**버립니다.
    - 이를 해결하기 위해 **vLLM은 최적화 책임을 4개 계층으로 분리**합니다.
        - **Scheduler: 범위(시스템 전반의, 모델 무관 최적화) → 배칭, 캐싱, 공정성·처리량 관리**
            - Scheduler는 시스템 레벨에서의 공정성, 효율성, 확장성을 책임집니다.
        - **ModelExecutor: 범위(모델 아키텍처별 최적화) → Transformer용 융합 어텐션 커널, 멀티모달 인코더 특수 연산자**
            - Scheduler는 모델에 무관하게 유지되는 반면, ModelExecutor는 각 모델 아키텍처의 세부사항을 이해합니다.
            - 예를 들어, Transformer 기반 모델에는 융합된(fused) 어텐션 커널을, 멀티모달 인코더에는 특수 연산자를 적용합니다.
            - 이 레벨은 아키텍처를 인지하는 최적화를 분리하여, 시스템 레벨 스케줄링과 독립적으로 진화할 수 있게 합니다.
        - **모델 레이어: 범위(컴포넌트별 최적화 )→ KV 캐시 재사용, 플래시 어텐션, 레이어 단위 연산자 융합**
            - 모델 아키텍처의 레이어 수준(예: 어텐션 레이어, 피드포워드 블록)에서는 최적화가 연산 병목에 맞춰 조정됩니다.
            - KV 캐시 재사용, 플래시 어텐션, 레이어 단위 연산자 융합 같은 기법들이 여기서 일어납니다.
            - 이 설계는 특정 하위 컴포넌트를 대상으로 하는 최적화가 시스템 전반의 스케줄링 로직으로 새어 나가지 않도록 보장합니다.
        - **CustomOp: 범위(하드웨어별 최적화) → CUDA 커널, 텐서 코어 가속, 양자화 연산자**
            - 마지막으로, CustomOp는 CUDA 커널, 텐서 코어 가속, 양자화된 연산자 같은 기저 하드웨어에 대한 최적화를 담당합니다.
            - 이를 별도로 분리함으로써, vLLM은 상위 레벨의 스케줄링이나 모델 로직을 바꾸지 않고도 새로운 GPU 기능과 가속기를 활용할 수 있습니다.
    - **설계 의도:**
        - **위로 갈수록(Scheduler) 범용적이고 모델에 무관하며, 아래로 갈수록(CustomOp) 특정 하드웨어에 특화됨**
        - 각 계층이 자신의 관심사만 처리하므로, **한 계층의 변경이 다른 계층에 영향을 주지 않음** (예: 새 GPU가 나와도 Scheduler·모델 로직은 그대로 두고 CustomOp만 확장)
        - 결과적으로 **vLLM은 새로운 모델 아키텍처나 하드웨어가 등장해도 전체 시스템을 재설계할 필요 없이**, 해당 최적화를 알맞은 계층에 "끼워 넣기"만 하면 되는 **미래 대비적(futureproof) 구조**를 갖게 됨
    

### **TensorRT-LLM**

- **TensorRT-LLM : NVIDIA GPU에서 고성능 LLM 추론을 위한 NVIDIA의 오픈소스 라이브러리** - Github , Docs , KrBlog
- 소개
    - TensorRT-LLM은 NVIDIA가 만든 **자사 GPU 전용 고성능 LLM 추론 라이브러리**
    - **핵심 방식** : 모델 체크포인트 → 고도로 튜닝된 TensorRT 엔진으로 컴파일
    - **런타임** : Python/C++ 런타임 제공
    - **주요 기능** : in-flight batching(연속 배칭), 페이지드 KV 캐시, 추측 디코딩, 다중 정밀도 양자화(FP8/FP4/INT4/INT8), 텐서/파이프라인 병렬화
    - **생태계 통합** : NVIDIA Dynamo, Triton과 긴밀히 연동
    - **API 사용성** : vLLM과 거의 동일한 고수준 LLM(`model=...`) / `generate()` 인터페이스 제공 → 사용 편의성 확보
        
        
    - TensorRT-LLM의 **고수준 LLM API를 사용**한 간단한 예시
        
        ```bash
        llm = LLM(model="Qwen/Qwen3-7B")
        
        # 샘플 프롬프트.
        prompts = [
           "Hello, my name is",
           "The capital of France is",
           "The future of AI is",
        ]
        
        # 샘플링 파라미터 생성.
        sampling_params = SamplingParams(temperature=0.8, top_p=0.95)
        
        # 모델 생성 요청 실행
        for output in llm.generate(prompts, sampling_params):
           print(
               f"Prompt: {output.prompt!r}, Generated text: {output.outputs[0].text!r}"
           )
        ```
        
    - **핵심 포지셔닝**:
        - TensorRT-LLM의 목표는 범용성이 아니라 **NVIDIA 하드웨어에서 낼 수 있는 최대 실전 성능**을 뽑아내는 것입니다.
        - 즉, vLLM이 "모델·하드웨어에 무관한 유연성"을 추구하는 것과 대조적으로, TensorRT-LLM은 "**NVIDIA GPU의 Tensor Core·CUDA 커널을 극한까지 활용**하는 것"에 초점을 맞춥니다.
    - **적합한 사용처**:
        - 이미 **NVIDIA 하드웨어와 서빙 스택(Triton, Dynamo 등)으로 표준화**되어 있고, **프로덕션에서 최고 수준의 처리량·효율성이 필요**한 조직에 가장 적합합니다.
        - 앞서 다룬 vLLM이 다양한 하드웨어·모델에 걸친 범용 프레임워크를 지향한다면, TensorRT-LLM은 **NVIDIA 생태계 안에서의 "끝판왕 성능**"을 지향한다고 이해하면 됩니다.
    
- `도전과제` **TensorRT-LLM** QuickStart 가이드 실습 따라해보기 : Linux, NVIDIA GPU, Python 3.10이상 - HW , Install , Docs , Colab
    - **NVIDIA 블랙웰** : B200, GB200, B300, GB300, DGX Spark
    - **NVIDIA Hopper** : H100, H200, GH200
    - **NVIDIA Ampere** : A100
    - **NVIDIA Ada Lovelace** :  RTX 4070 (Ada, SM89), L20, L40/L40S ***⇒ Runpod 에서 실습 해보자!***
        
        ```bash
        # Ubuntu 24.04, NVIDIA Container Tooklit, Driver:CUDA 13.2, PyTorch 2.11.0(cu13.0) 을 요구.
        # GPU 지원: Ampere/Ada Lovelace/Hopper/Blackwell — RTX 40-series(Ada, SM89)는 공식 지원.
        
        # 
        **docker pull nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc24
        docker images**
        IMAGE                                           ID             DISK USAGE   CONTENT SIZE
        nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc24   16a103b8b1b6       **54.8GB**         **17.7GB**
        
        #
        docker run --rm -it \
          --ipc host \
          --gpus all \
          --ulimit memlock=-1 \
          --ulimit stack=67108864 \
          -v ~/.cache/huggingface:/root/.cache/huggingface \
          -p 8000:8000 \
          nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc24 \
          **python3 -c "import tensorrt_llm"
        ...
        [TensorRT-LLM] TensorRT LLM version: 1.3.0rc24**
        
        # 기동
        docker run -d --rm -it --ipc host --gpus all --name trtllm-server --ulimit memlock=-1 --ulimit stack=67108864 \
          -v ~/.cache/huggingface:/root/.cache/huggingface -p 8000:8000 nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc24 \
          **sleep infinity**
        
        **docker ps**
        CONTAINER ID   IMAGE                                           COMMAND                  CREATED          STATUS          PORTS                                                             NAMES
        fa17e7f3ec77   nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc24   "/opt/nvidia/nvidia_…"   14 seconds ago   Up 14 seconds   6006/tcp, 8888/tcp, 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp   trtllm-server
        
        # https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve/trtllm-serve.html#trtllm-serve
        docker exec -it trtllm-server **hostname**
        docker exec -it trtllm-server **pwd**
        docker exec -it trtllm-server **nvidia-smi**
        docker exec -it trtllm-server **trtllm-serve serve "TinyLlama/TinyLlama-1.1B-Chat-v1.0" --host 0.0.0.0 --port 8000** 
        docker exec -it trtllm-server sh -c 'trtllm-serve --host 0.0.0.0 --port 8000 "TinyLlama/TinyLlama-1.1B-Chat-v1.0"'
          
        # trtllm-serve로 모델 서빙 : TinyLlama/TinyLlama-1.1B-Chat-v1.0
        **trtllm-serve serve "TinyLlama/TinyLlama-1.1B-Chat-v1.0" --host 0.0.0.0 --port 8000** 
        
        # 호출 확인
        **curl -s -X POST http://localhost:8000/v1/chat/completions \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            -d '{
                "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "messages":[{"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "Where is New York? Tell me in a single sentence."}],
                "max_tokens": 32,
                "temperature": 0
            }' | jq**
        {
          "id": "chatcmpl-6270b7ac7ce9495881ae089501de43e8",
          "object": "chat.completion",
          "created": 1787479381,
          "model": "**TinyLlama/TinyLlama-1.1B-Chat-v1.0**",
          "choices": [
            {
              "index": 0,
              "message": {
                "role": "assistant",
                "content": "**New York is a city in the United States that is known for its iconic landmarks, diverse culture, and world-class cuisine.**",
                "reasoning_content": "",
                "reasoning": null,
                "tool_calls": []
              },
              "logprobs": null,
              "finish_reason": "stop",
              "stop_reason": null,
              "mm_embedding_handle": null,
              "disaggregated_params": null,
              "avg_decoded_tokens_per_iter": 1.0
            }
          ],
          "usage": {
            "prompt_tokens": 41,
            "total_tokens": 72,
            "completion_tokens": 31,
            "prompt_tokens_details": {
              "cached_tokens": 40
            }
          },
          "prompt_token_ids": null,
          "prompt_token_ids_b64": null
        }
        
        # 종료
        **docker rm -f trtllm-server**
        
        ```
        
    

### SGLang

- **SGLang** : high-performance serving framework for large language models and multimodal models - Github , Home , Docs , Blog
- 소개
    
    !image.png
    
    - SGLang은 **구조화된 생성(structured generation)**과 **에이전트 애플리케이션**을 **타깃**으로 하는 비교적 새로운 진입자입니다.
    - SGLang은 **LLM**과 비전-언어 모델(**VLM**)을 위한 **오픈소스 고성능 서빙 프레임워크**입니다.
    - **빠른 백엔드 런타임**(커널, 캐싱, 스케줄링)을 유연한 프론트엔드 언어 및 API(OpenAI 호환 및 네이티브)와 함께 공동 설계하여, 생성을 더 빠르고 더 제어 가능하게 만듭니다.
        
        
    - **SGLang은 vLLM의 직접적인 동급 경쟁 프레임워크**로, 특히 구조화된 생성(JSON/정규식/EBNF)과 에이전트/다단계 워크플로우에 강점
    - **설계 철학**: 빠른 백엔드 런타임 + 유연한 프론트엔드 언어/API를 공동 설계
    - **핵심 기능**: RadixAttention(프리픽스/KV 재사용), 연속 배칭, 페이지드 KV, 추측 디코딩(EAGLE-2/3), 청크드 프리필, 구조화된 출력, 멀티-LoRA, 다양한 병렬화(텐서/파이프라인/전문가/데이터)
    - **하드웨어 지원**: NVIDIA뿐 아니라 AMD Instinct, CPU, TPU, Jetson Orin, Ascend까지 vs TensorRT-LLM보다 훨씬 폭넓음
    - **API 사용성**: vLLM·TensorRT-LLM과 유사한 고수준 `Engine/generate()` 인터페이스
        
        
    - **사용 예시**
        
        ```bash
        # Qwen3 모델 로드
        llm = sgl.Engine(model_path="Qwen/Qwen3-7B")
        
        prompts = [
            "Hello, my name is",
            "The president of the United States is",
            "The capital of France is",
            "The future of AI is",
        ]
        sampling_params = {"temperature": 0.8, "top_p": 0.95}
        
        # 모델 생성 요청 실행
        outputs = llm.generate(prompts, sampling_params)
        for prompt, output in zip(prompts, outputs):
            print("===============================")
            print(f"Prompt: {prompt}\nGenerated text: {output['text']}")
        ```
        
    - **비교**
        - **TensorRT-LLM**: NVIDIA GPU 전용, 최대 실전 성능에 특화
        - **vLLM**: 모델·하드웨어 무관, 가장 큰 오픈소스 생태계·커뮤니티
        - **SGLang**: 멀티 벤더 하드웨어 지원 + RadixAttention 기반 프리픽스 재사용 강점, 구조화된 출력·에이전트 워크플로우에 특화되어 vLLM의 대안이자 경쟁자로 부상 중
        
    - **핵심 차별점:**
        - RadixAttention은 여러 호출에 걸친 KV 캐시 재사용을 트리(radix tree) 구조로 관리하여, 특히 반복적인 프리픽스가 많은 에이전트/멀티턴 시나리오에서 강점을 보입니다.
            
            vLLM과 SGLang은 같은 문제를 어떻게 다르게 풀었나
            
        - 성능은 vLLM과 경쟁력 있는 수준이지만, vLLM이 아직 더 넓은 커뮤니티·생태계를 갖고 있다는 것이 현재 시점(2026년)의 주요 차이로 언급됩니다.
    
- `도전과제` SGLang QuickStart 가이드 실습 따라해보기 - Docs , Colab
    
    ```bash
    # Docker 예제 (가이드 원문):
    docker run --gpus all --shm-size 32g -p 30000:30000 \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      --env "HF_TOKEN=<secret>" --ipc=host \
      lmsysorg/sglang:latest python3 -m sglang.launch_server \
      --model-path meta-llama/Llama-3.1-8B-Instruct \
      --host 0.0.0.0 --port 30000
    
    # 검증 방법: curl(OpenAI 호환), OpenAI Python 클라이언트, SGLang 네이티브 /generate API, 오프라인 배치 추론(sgl.Engine).
    
    # 실습 계획
    1. 이미지 pull: lmsysorg/sglang:latest (또는 40% 작은 latest-runtime) 
    2. 컨테이너를 detached로 기동하고 launch_server를 그 안에서 실행
    3. curl로 /v1/chat/completions 검증 
    4. OpenAI Python 클라이언트로 재검증 (base_url=http://127.0.0.1:30000/v1)
    5. 네이티브 /generate API 검증 
    6. (선택) 서버 종료 후, 노트북과 동일한 Qwen/Qwen3-8B-AWQ로 오프라인 sgl.Engine 배치 추론 재현
    
    # 이미지 pull: lmsysorg/sglang:latest 
    **docker pull lmsysorg/sglang:latest**
    **docker images**
    IMAGE                    ID             DISK USAGE   CONTENT SIZE
    **lmsysorg/sglang**:latest   9e148f5ac788       **47.4GB**         14.2GB
    
    # 컨테이너를 detached로 기동하고 launch_server를 그 안에서 실행
    HF_TOKEN=hf_SrtLCeF...
    docker run -d **--name sglang-server** \
        --gpus all --shm-size 32g \
        -p 30000:30000 \
        -v ~/.cache/huggingface:/root/.cache/huggingface \
        --ipc=host \
        lmsysorg/sglang:latest **python3 -m sglang.launch_server** \
        --model-path **qwen/qwen2.5-0.5b-instruct** \
        --host 0.0.0.0 --port 30000
    
    **docker ps**
    CONTAINER ID   IMAGE                    COMMAND                  CREATED         STATUS              PORTS                                             NAMES
    cff2765319e2   lmsysorg/sglang:latest   "/opt/nvidia/nvidia_…"   2 minutes ago   Up About a minute   0.0.0.0:30000->30000/tcp, [::]:30000->30000/tcp   sglang-server
    
    # curl로 /v1/chat/completions 검증 
    curl -sS http://localhost:30000**/v1/chat/completions** \
        -H "Content-Type: application/json" \
        -d '{"model": "**qwen/qwen2.5-0.5b-instruct**",
             "messages": [{"role": "user", "content": "**What is the capital of France?**"}]}' | jq
    {
      "id": "a840b837009d4b3dad206411a519683c",
      "object": "chat.completion",
      "created": 1787480898,
      "model": "qwen/qwen2.5-0.5b-instruct",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "**The capital of France is Paris."**,
            "reasoning_content": null,
            "tool_calls": null
          },
          "logprobs": null,
          "finish_reason": "stop",
          "matched_stop": 151645
        }
      ],
      "usage": {
        "prompt_tokens": 36,
        "total_tokens": 44,
        "completion_tokens": 8,
        "prompt_tokens_details": null,
        "reasoning_tokens": 0
      },
      "metadata": {
        "weight_version": "default"
      }
    }
    
    # OpenAI Python 클라이언트로 재검증 (base_url=http://127.0.0.1:30000/v1)
    docker exec sglang-server python3 -c "
    import openai
    client = openai.Client(base_url='**http://127.0.0.1:30000/v1**', api_key='None')
    response = **client.chat.completions.create**(
        model='**qwen/qwen2.5-0.5b-instruct**',
        messages=[{'role': 'user', 'content': '**List 3 countries and their capitals.**'}],
        temperature=0, max_tokens=64
    )
    print(response.choices[0].message.content)
    "
    Sure, here are three countries and their respective capitals:
    1. **United States** - Washington D.C.
    2. **Canada** - Ottawa
    3. **Australia** - Canberra
    
    # 네이티브 /generate API 검증 
    curl -sS -X POST **http://localhost:30000/generate** \
        -H "Content-Type: application/json" \
        -d '{"text": "**The capital of France is"**, "sampling_params": {"temperature": 0, "max_new_tokens": 32}}' | jq
    {
      "text": " Paris. It is the largest city in Europe and the second largest city in the world. It is located in the south of France, on the banks of the",
      "output_ids": [
        12095,
        13,
        1084,
        374,
        279,
        7772,
        3283,
        304,
        4505,
        323,
        279,
        2086,
        7772,
        3283,
        304,
        279,
        1879,
        13,
        1084,
        374,
        7407,
        304,
        279,
        9806,
        315,
        9625,
        11,
        389,
        279,
        13959,
        315,
        279
      ],
      "meta_info": {
        "id": "3feed15121284a7691868f0465ce5392",
        "finish_reason": {
          "type": "length",
          "length": 32
        },
        "prompt_tokens": 5,
        "weight_version": "default",
        "num_retractions": 0,
        "reasoning_tokens": 0,
        "completion_tokens": 32,
        "cached_tokens": 4,
        "cached_tokens_details": {
          "device": 4,
          "host": 0
        },
        "dp_rank": null,
        "e2e_latency": 0.14213981700004297,
        "response_sent_to_client_ts": 1787481184.2625177
      }
    }
    
    # 삭제
    **docker rm -f sglang-server**
    
    ```
    
    !https://huggingface.co/settings/gated-repos : 20~30분 정도 소요
    
    https://huggingface.co/settings/gated-repos : 20~30분 정도 소요
    

### **Llama.cpp**

- **Llama.cpp** : LLM inference in C/C++ , 어디서나, 저비용으로 실행 - Github , Home , Docs
- 소개
    
    !image.png
    
    - Llama.cpp는 노트북·워크스테이션부터 온프레미스 서버, 엣지 디바이스에 이르기까지 **거의 모든 머신에서 최신 오픈 웨이트 LLM을 효율적으로 실행**하도록 만들어진, **가벼운 오픈소스 C/C++ 추론 스택입**니다. 모델은 **GGUF 포맷으로 패키징**되며(일반적으로 저장소의 스크립트를 사용해 Hugging Face 체크포인트에서 변환), **내장된 OpenAI 호환 HTTP 서버를 통해 서빙**하거나 **실험 및 벤치마킹용 소형 CLI 도구로 구동**할 수 있습니다.
        
        !*VLM session with **llama cli***
        
        *VLM session with **llama cli***
        
        !*Built-in web UI against **llama serve***
        
        *Built-in web UI against **llama serve***
        
    - 이 프로젝트는 **최소한의 의존성, 빠른 시작 시간, 공격적인 정수 양자화**(예: 8/6/5/4비트), 그리고 **이식 가능한 CPU/GPU 백엔드 집합**(SIMD를 사용하는 CPU, 그리고 Metal, CUDA/ROCm, Vulkan 같은 선택적 가속기)을 강조합니다.
    - llama.cpp를 차별화하는 것은 "**어디서나 실행된다"는 철학**과 **매우 작은 운영 부담**입니다. 주된 목표는 **저비용 또는 저사양 디바이스**를 포함한 광범위한 하드웨어에서, 오프라인이든 클라우드든, **최소한의 설정으로 최첨단 로컬 추론을 견고한 성능과 함께 제공**하는 것입니다. 이와 대조적으로, 여기서 다룬 다른 세 서빙 프레임워크 “**vLLM, TensorRT-LLM, SGLang**” 는 멀티테넌트 배칭, 고급 스케줄링, 대규모 배포 기능 같은, 데이터센터 GPU에서의 **고처리량·저지연 서빙을 최우선으로 최적**화합니다.
    - Llama.cpp는 절대적인 최고 처리량보다 **이식성, 단순성, 비용 효율성을 우선시**하여, 로컬 개발, 프라이버시에 민감한 워크로드, 엣지 배포, 예산 제약이 있는 환경에 이상적입니다. 다만 가능한 경우 **선택적 GPU 가속도 여전히 제공합**니다.
        
        
        | 항목 | 내용 |
        | --- | --- |
        | 구현 | 가벼운 C/C++ 스택, 최소 의존성, 빠른 시작 |
        | 모델 포맷 | GGUF (HF 체크포인트에서 변환) |
        | 양자화 | 공격적인 2~8비트 정수 양자화 |
        | 하드웨어 | CPU(SIMD) 기본, Metal/CUDA/ROCm/Vulkan 선택적 가속 |
        | 인터페이스 | 내장 OpenAI 호환 HTTP 서버 + CLI, llama_cpp 파이썬 바인딩 |
        | 상위 래퍼 | Ollama가 llama.cpp를 감싸 더 쉬운 REST API 경험 제공 |
        
    - llama.cpp로 **Qwen3 모델**을 **CPU 디바이스**에서 실행하는 간단한 예시를 살펴보겠습니다:
        
        ```bash
        from llama_cpp import Llama
        
        # llama.cpp로 **CPU에서 Qwen3 모델 실행**
        # Hugging Face에서 Qwen 모델(GGUF 포맷)을 로드
        llm = Llama.from_pretrained(
           repo_id="**Qwen/Qwen3-8B-GGUF**",
           filename="*Q8_0.gguf",
           verbose=False
        )
        
        # 고수준 API로 LLM 생성 실행
        output = llm(
             "Q: Name the planets in the solar system? A: ", # 프롬프트
             max_tokens=32, # 최대 32개 토큰 생성
             stop=["Q:", "\n"], # 모델이 새 질문을 생성하기 직전에 멈춤
             echo=True # 출력에 프롬프트를 그대로 포함
        )
        
        # 채팅 완성 API 예시
        output = **llm.create_chat_completion**(
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant who perfectly describes "
                               "images.",
                },
                {
                    "role": "**user**",
                    "content": "**Describe this image in detail please."**,
                },
            ])
        ```
        
    - llama.cpp는 저사양 디바이스(CPU와 엣지 하드웨어)에 LLM 서빙을 가져다주기 때문에, 다음 세 가지 시나리오 사용 추천
        - **로컬 개발**: 내장된 OpenAI 호환 서버를 자신의 머신에서 실행하고 기존 클라이언트(예: RAG, 검색 시스템)를 그대로 재사용할 수 있음
        - **프라이빗 및 온프레미스 어시스턴트**: 모든 데이터를 VPC나 디바이스 경계 내부에 유지
        - **엣지 추론**: 노트북, 데스크톱, Apple Silicon, 소형 서버에서 - 공격적인 2~8비트 양자화와 이식 가능한 CPU/GPU 백엔드로 가능
        
    - **llama.cpp를 REST API 호출로 노출**하고 싶다면, llama.cpp(그리고 때로는 Mistral.cpp나 RWKV 러너 같은 다른 백엔드)를 감싸서 로컬 LLM 사용을 간단하고 일관되며 개발자 친화적으로 만드는 **상위 레벨 프레임워크인 Ollama를 사용**할 수 있습니다.
    - 모든 LLM 애플리케이션이 고처리량 서빙을 필요로 하는 것은 아닙니다. 추론을 로컬(온디바이스 또는 온프레미스 엣지)에서 실행할 때는 목표가 달라집니다:
        - 플릿 전체의 초당 토큰 수가 아니라, 지연 시간과 응답성을 최적화하고 싶어짐
        - 낮은 동시성(흔히 단일 사용자)이므로 대규모 배칭과 복잡한 스케줄러의 가치가 줄어듦
        - 메모리·연산·전력 측면의 풋프린트와 비용이 주요 제약이 됨
        - 프라이버시와 오프라인 신뢰성이 최우선 요구사항이 됨
    - Llama.cpp는 이 프로필에 딱 들어맞습니다:
        - **CPU, Apple Silicon, 소형 GPU에서 오픈 웨이트 모델을 직접 실행**할 수 있고, 드롭인 통합을 위한 **OpenAI 호환 서버를 제공**합니다.
        - 그 결과, 토큰당 클라우드 요금이나 데이터 유출 없이, 로컬 개발, 프라이빗·온프레미스 어시스턴트, 엣지 배포를 위한 초저비용·저운영 서빙 옵션이 만들어집니다.
    
- `도전과제` llama.app QuickStart 가이드 실습 따라해보기 - Install , Docs , Docker , Colab

### **Selecting the Right Framework**

- **프레임워크 선택**은 "벤치마크 1위"가 아니라 "**내 SLO·워크로드·운영 현실에 맞는가**"를 기준으로 해야 합니다.
    - 일반적으로 권장하는 평가 접근법 6단계
        1. **기능이 아니라 SLO부터 시작하라.** 
            - 지연 시간(TTFT, p95/p99), 처리량(TPS/QPS), 토큰당 비용, 품질 제약(구조화된 JSON, 안전성), 가용성에 대한 목표를 적어 두세요.
        2. **여러분의 사용 사례에서 나오는 실제 프롬프트를 분석하라:** 
            - prefill 위주인지 decode 위주인지, 컨텍스트 길이는 어느 정도인지, 도구 호출(tool call)이나 멀티턴 체인이 포함되는지를 명확히 하세요.
        3. **동일한 조건으로 비교하라:** 
            - 경쟁 프레임워크들 사이에서 동일한 모델, dtype/양자화, 최대 시퀀스 길이, 배치/동시성, 스트리밍 설정을 사용해 사과 대 사과 비교가 되도록 하세요.
        4. **운영성을 측정하라:** 
            - 콜드 스타트 시간, 관측 가능성(observability), 오토스케일링 동작, 멀티테넌시 공정성, 업그레이드 마찰, 장애 모드 같은 지표를 활용하세요.
        5. **하드웨어와 벤더 종속(lock-in)을 고려하라.** 
            - 여러 벤더(예: NVIDIA/AMD/CPU/TPU/엣지)를 사용한다면, 이식성이 크게 중요해집니다.
        6. **변화를 계획하라.** 
            - 모델 교체와 새로운 디코딩 기법은 **매주 일어나므로, 큰 수술 없이 업데이트할 수 있는 프레임워크를 선택**하세요.
        
    - **최종 프레임워크 선택 가이드:**
        - **프로덕션까지의 가장 빠른 경로, 폭넓은 모델 커버리지, 파이썬 네이티브 워크플로우를 원한다면 vLLM**을 선택하세요. 강력한 기본 성능, 연속 배칭, 그리고 큰 커뮤니티와 생태계를 제공합니다.
        - 여러분의 **워크로드가 에이전틱하거나 다단계 워크플로우, 엄격한 JSON/정규식(문법 제약) 출력, 다중 벤더 이식성을 포함한다면 SGLang**을 고르세요. 프리픽스/KV 재사용, 추측 디코딩, 스케일아웃 클러스터를 위한 라우터를 얻을 수 있습니다.
        - **NVIDIA와 그 서빙 스택에 완전히 올인했고 대규모에서 달러당 최고 토큰 수를 원한다면 TensorRT-LLM**부터 시작하세요. 최상급 Triton·Dynamo 통합과 깊은 CUDA/Tensor Core 최적화 덕분에 NVIDIA 하드웨어에서 효율성 리더가 됩니다.
        - **로컬, 온프레미스, 또는 엣지 서빙이 필요하고 작은 풋프린트, 저비용, 기본적인 프라이버시를 원한다면 llama.cpp**를 사용하세요. GGUF 양자화(2~8비트)와 이식 가능한 CPU/GPU 백엔드 덕분에 노트북, 데스크톱, 소형 서버에 이상적입니다.
        
        | 상황 | 추천 프레임워크 | 이유 |
        | --- | --- | --- |
        | 빠른 프로덕션 배포, 폭넓은 모델 지원, 파이썬 워크플로우 | vLLM | 강력한 기본 성능 + 가장 큰 생태계 |
        | 에이전틱/다단계 워크플로우, 구조화된 출력(JSON/정규식), 멀티 벤더 | SGLang | 프리픽스/KV 재사용, 추측 디코딩, 스케일아웃 라우터 |
        | NVIDIA 스택 올인, 달러당 최고 처리량 | TensorRT-LLM | Triton/Dynamo 통합, 깊은 CUDA 최적화 |
        | 로컬/온프레미스/엣지, 저비용, 프라이버시 | llama.cpp | GGUF 양자화, 이식 가능한 경량 백엔드 |
        
    - **핵심:**
        - 이 선택은 일회성 결정이 아니라 **지속적인 재평가 과정**이어야 합니다.
        - **LLM 서빙 생태계가 매달 바뀌므로**, 서빙 엔지니어는 **3~6개월 주기로 프레임워크를 재검토**하고, **프레임워크 추상화 레이어와 탈출 계획을 마련**해 **앱 코드를 다시 쓰지 않고도 프레임워크를 교체**할 수 있어야 합니다.
        - 즉, 목표는 "영원한 승자"를 정하는 것이 아니라 **유연성을 유지하는 것** ← 이는 앞서 다룬 vLLM의 "계층화된 최적화" 철학(변화에 대비해 시스템을 설계)과 같은 맥락의 원칙입니다.
- Summary
    - 이번 장에서는 범용 머신러닝 서빙 스택이 왜 LLM에는 부족한지를 설명했습니다 → 주된 이유는 토큰 단위 스케줄링, KV 캐시 관리, 긴 컨텍스트 메모리 처리, 스트리밍 우선 실행 같은 LLM 특화 기능 지원이 결여되어 있기 때문입니다.
    - 그런 다음 vLLM을 깊이 있게 다루며, 그 아키텍처, 요청 스케줄링과 우선순위 결정, 그리고 시스템 전반의 스케줄링을 모델·커널 레벨의 특화와 분리하는 계층화된 최적화 전략을 살펴보았습니다. 이 조사를 보완하기 위해 세 가지 상호보완적인 프레임워크도 다루었습니다: NVIDIA GPU에서 최고 효율을 끌어내는 TensorRT-LLM, 경량 로컬/온프레미스/엣지 서빙을 위한 llama.cpp, 그리고 다양한 하드웨어에서 에이전틱하고 다단계인 워크플로우와 구조화된 출력을 지원하는 SGLang입니다.
    - 우리가 여러분께 드리는 **핵심 시사점은, 프레임워크 선택은 맥락(context)에 달려 있다**는 것입니다. 많은 팀이 온라인 서빙에는 vLLM으로, 로컬 개발에는 llama.cpp로 시작하지만, 엣지 배포, NVIDIA 중심 최적화, 엄격한 JSON/문법 제약 출력, 에이전트 파이프라인 같은 특정 요구사항이 있다면 대신 TensorRT-LLM이나 SGLang을 가리킬 수도 있습니다. 생태계가 계속 진화함에 따라, 프레임워크에 종속되지 않는 태도를 유지하는 것이 좋습니다. 실무적으로 이는 주기적으로 프레임워크를 조사하고, 이식 가능한 인터페이스를 선호하며, 비즈니스와 기술적 요구가 변화함에 따라 서빙 스택이 적응할 수 있도록 컴포넌트를 교체할 준비가 되어 있어야 한다는 것을 의미합니다.
        
        
    - 이번 장 전체를 관통하는 흐름을 정리
        1. **문제 제기**: 범용 ML 서빙 스택은 토큰 단위 스케줄링, KV 캐시 관리, 긴 컨텍스트 처리, 스트리밍 실행 같은 LLM 고유의 요구사항을 지원하지 못함
        2. **vLLM 심층 분석**: 아키텍처(Processor → Scheduler/EngineCore → Executor → Output Processor), 토큰 단위 요청 스케줄링, 그리고 Scheduler/ModelExecutor/모델 레이어/CustomOp로 이어지는 계층화된 최적화 전략
        3. **대안 프레임워크 3종 비교:**
            - TensorRT-LLM : NVIDIA GPU 최고 효율
            - llama.cpp : 경량 로컬/온프레미스/엣지
            - SGLang : 멀티 벤더 하드웨어 + 에이전틱/구조화 출력
        
    - **이 장의 핵심 메시지**: "어떤 프레임워크가 최고인가"가 아니라 "내 상황(SLO, 하드웨어, 워크로드)에 어떤 프레임워크가 맞는가"를 물어야 합니다. 실무에서 흔한 패턴은 온라인 서빙 = vLLM + 로컬 개발 = llama.cpp 조합이지만, 요구사항에 따라 TensorRT-LLM(NVIDIA 올인)이나 SGLang(에이전트/구조화 출력)으로 전환할 수 있습니다.
    - 가장 중요한 실천적 결론은 **프레임워크 무관성(**framework-agnostic) **유지**입니다:
        - 3~6개월 주기로 프레임워크 재조사
        - 이식 가능한(portable) 인터페이스 선호
        - 컴포넌트를 쉽게 교체할 수 있는 추상화 레이어 확보
    - 즉, LLM 서빙 생태계가 계속 빠르게 변하는 만큼, **특정 프레임워크에 정착하기보다는 변화에 올라탈 수 있는 유연한 서빙 아키텍처를 유지**하는 것이 이 장의 최종 결론입니다.
    

### 4주차 과제

- **4주차 스터디**에서 학습한 내용 혹은 **LLM 관련 내용(혹은 도전과제)**을 **간략히 정리**하여 **공개된 링크에 글 작성** 후 해당 링크를 **과제제출표**에 공유 🙇🏻‍♂️🙇🏻‍♀️
    - **작성 도구** : 블로그, Github, 개인 홈페이지, 개인 Youtube, ‘페이스북/링크드인 공개 게시 글’ 등
    - **정리 내용(예시)**
        - 해당 주차 스터디에서 학습한 내용을 요약 정리 작성
        - 해당 주차 스터디에서 다룬 주제 기술 1개를 별도 조사 학습해서 정리
        - LLM 서빙 관련 운영 경험 중 기술 내용 위주로 정리
        - 최근 LLM 서빙 관련 새로운 기술에 대한 분석 정리
    

### 도전 과제

- `도전과제` vLLM or SGLang 에 ‘Base모델 vs Speculative Decoding’ 실습 및 측정 해보기 : gpu **데탑 혹은 아래 Runpod, AWS GPU EC2 실습 환경 구성**
- `도전과제` Runpod **Serverless** - Blog Blog2 or Runpod **Clusters** - Blog Blog2 사용 해보기
- `도전과제` How to run **Kimi K3 on Runpod**'s Public Endpoint - Blog , Docs , Playground
- `도전과제` From No-Code to Pro: **Optimizing Mistral-7B** on Runpod for Power Users - Blog
- `도전과제` AWS GPU EC2 기동 후 vLLM 설처 후 사용해보기
- `도전과제` 단일 GPU 노드에 8개 GPU 장착된 환경(NVLink or PCIe)에서 TP=8(혹은 TP=4 x DP=2)로 서빙 실행 및 속도 측정
- `도전과제` 2대의 GPU 노드(각 노드에 8개 GPU 장착)에서 환경(IB or RoCEv2 or 등등)에서 ‘TP=8 + DP=2’로 서빙 실행 및 속도 측정
- `도전과제` 2대의 GPU 노드에서 vLLM Data Parallel Deployment 에 ‘Internal LB vs External LB’ 설정 후 서빙 실행 및 비교
- `도전과제` 멀티 GPU 노드 환경에서 큰 모델(MoE 아키텍처) 를 vLLM Expert Parallel Deployment 배포 후 서빙 실행해보기
- `도전과제` **vLLM + LMCache: A Starter Guide, No GPU Required*** - Blog
- `도전과제` GPU 노드에 vLLM 에 LMCache 설정 후 성능 테스트 후 정리해보기
- `도전과제` vLLM 주요 동작의 소스 코드 분석 해보기 - Github
- `도전과제` Aleksa Gordić의 블로그 글 Inside vLLM: Anatomy of a High-Throughput LLM Inference System 정리해보기
    - Inside NVIDIA GPUs: Anatomy of high performance matmul kernels 정리해보기 - Blog
- `도전과제` **TensorRT-LLM** QuickStart 가이드 실습 따라해보기 : Linux, NVIDIA GPU, Python 3.10이상 - HW , Install , Docs , Colab
- `도전과제` SGLang QuickStart 가이드 실습 따라해보기 : Linux, NVIDIA GPU, Python 3.10이상 - Docs , Colab
- `도전과제` llama.app QuickStart 가이드 실습 따라해보기 : Linux, NVIDIA GPU, Python 3.10이상 - Install , Docs , Docker , Colab