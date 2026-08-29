- `질문` ***→ 학습을 하시고 스스로 아래 질문에 답변을 해보시기 바랍니다!***
    - Decoder-only Transformer는 프롬프트 하나를 받아 다음 토큰 하나를 생성하기까지 내부적으로 어떤 단계를 거치는가?
        - Tokenizer/Embedding → Decoder Block(Self-Attention + FFN) N개 반복 → LM head → 다음 토큰 확률분포. 그리고 그 토큰이 다시 입력에 append되어 반복되는 자기회귀적(autoregressive) 구조
        
    - Self-Attention 연산은 왜 이렇게 비싸며, 그 비용은 KV Cache로 어떻게 줄일 수 있는가?
        - Attention 복잡도가 시퀀스 길이에 대해 O(L²D)로 증가하는 이유(모든 토큰 쌍의 Query·Key 내적), 그리고 매 스텝 전체 시퀀스를 재계산하는 대신 이전 토큰들의 Key/Value를 캐시해 O(LD)로 줄이는 KV Cache 메커니즘 → 캐시 없음(9.12초) vs 있음(3.14초) 실측 비교가 이 질문의 답을 데이터로 보여줌.
        
    - Prefill과 Decode는 왜 서로 다른 병목(compute-bound vs memory-bound)을 가지며, 이것이 실제 서빙 최적화(vLLM, PagedAttention, batching/streaming) 전략을 어떻게 결정하는가?
        - Prefill=연산 집약적(GPU 컴퓨트가 병목), Decode=KV 캐시 반복 접근으로 메모리 대역폭이 병목이라는 구분이, PagedAttention의 메모리 단편화 해결, continuous batching, streaming 같은 이후 모든 최적화 기법의 설계 근거
    

### Intro

- **배경**
    - 모델 서빙 시스템은 빠르게 변화하는 모델 아키텍처, 학습 알고리즘, 툴링에 더해 모니터링·스케일링·보안·CI/CD 등 프로덕션 인프라까지 겹쳐 있어 초심자에게는 복잡하고 압도적으로 느껴지기 쉽습니다. 그래서 시스템 세부사항에 매몰되기 전에 핵심 원리부터 이해하는 것이 중요합니다.
- 접근 방식
    - 이 책은 기초부터 시작합니다. **LLM을 서빙하는 데 필요한 최소한의 코드**부터 시작해 점차 **확장**해 나가면서, 토큰 생성 과정이 어떻게 동작하는지, 그리고 LLM 서빙이 왜 독특한 어려움을 갖는지에 대한 탄탄한 멘탈 모델을 세웁니다.
- 이 장에서 다루는 내용
    - **LLM의 기본 아키텍처** : 토큰 생성 과정과 어텐션(attention) 메커니즘
    - 실습 코드 예제를 통해 **추론(inference)** 시 내부에서 실제로 일어나는 일
    - LLM 서빙의 핵심 개념: **prefill, decode, KV 캐시 재사용**
    - 이런 **기초 개념을 이해**하는 것이 병목 현상을 진단하고 성능 개선에 기여하는 데 **왜 중요한지**
    - 이후에는 최신 서빙 프레임워크인 **vLLM을 사용해 서빙 효율을 높이는 방법을 실습**하며, 프로덕션급 성능을 위해 필수적인 **스트리밍(streaming)과 배치 처리(batching)** 기법을 소개합니다.
- 이 장의 목표
    - 이 책 전체의 기초가 되는 장으로, LLM 서빙 시스템의 동작 방식, 한계, 최적화 포인트에 대한 실질적인 이해와 직관을 기르는 것이 목표입니다.
    - 이후 시스템 설계, 확장성, 고급 서빙 최적화 전략을 다루는 장들의 토대가 됩니다.
    - 서빙(추론) 중심이므로 깊은 수학적 지식은 필요 없으며, 수학적 개념은 직관적으로 풀어 설명해 엔지니어링 관점에 집중할 수 있도록 구성했습니다.
    - 다음 장(3장)에서는 이 장에서 배운 내용을 실제 웹 서비스로 감싸는(wrap) 방법과 핵심 설계 결정 및 원칙을 다룰 예정입니다.

### Inside the Mind of a Transformer

- **LLM Evolution** LLM 발전 과정
    - LLM의 역사를 아는 것은 단순한 역사적 흥미가 아니라, 모델 설계 선택과 아키텍처 패턴, 실행 동작을 이해하는 데 **핵심적인 통찰**을 줍니다
        - → 이는 **추론(inference)과 최적화 작업의 기반**이 됩니다.
    - **Transformer와 LLM의 발전**
        
        !mermaid-diagram (3).png.png)
        
        !**Figure 2-1. The history and development of language models ([source)**](attachment:0d989896-7384-434d-b09b-8d682857c7b9:image.png)
        
        **Figure 2-1. The history and development of language models (source)**
        
        - LLM은 언어 모델의 규모, 학습 데이터, Transformer 아키텍처, instruction tuning, RLHF, tool use, multimodal 기능이 결합되며 발전해왔다.
        - LLM의 정의는 계속 변한다. 모델 파라미터 수만으로 LLM을 정의하기보다는, 긴 context 처리, instruction following, reasoning, multimodal, agentic workflow 같은 기능적 특성까지 함께 봐야 한다.
    - **초기 발전 과정**
        - 2013년 Word2Vec (Google, Mikolov 외): **단어를 연속 벡터 공간에 밀집 표현**(dense embedding)하는 방식을 도입해, **단어 간 의미적 관계를 포**착할 수 있게 됨
        - 2013년 **RNN(순환 신경망):** 언어의 순차적 특성을 모델링하기 위해 등장, 감성 분석·텍스트 생성 등에 활용
        - 2014년 **LSTM/GRU**: RNN의 **장기 의존성 문제를 개선**하기 위해 게이팅 메커니즘과 메모리 셀 도입
    - **RNN 계열의 한계**
        - 입력을 한 스텝씩 순차 처리해야 해서 **병렬화가 어렵고**, GPU 같은 현대 하드웨어에서 확장성·효율성이 떨어졌으며, 장거리 의존성 처리에도 여전히 취약했습니다.
            
            ```bash
            # 앞의 정보를 순서대로 기억합니다.
            토큰 1 → 토큰 2 → 토큰 3
            # 문제는 순차 계산이라 GPU 병렬화가 어렵다는 점입니다.
            ```
            
    - **Transformer의 등장 (2017)**
        - Google의 논문 "**Attention Is All You Need**"에서 소개된 Transformer는 순환 레이어를 **셀프 어텐션(self-attention)**과 **위치 인코딩(positional encoding)**으로 대체해, **병렬 처리가 가능**하면서도 장거리 의존성을 효율적으로 포착할 수 있게 했습니다. 이는 시퀀스 모델링의 혁신이었습니다.
            - 문장 안의 먼 토큰 관계를 잘 찾음
            - 여러 입력 토큰을 병렬 계산 가능
            - GPU 행렬 연산에 적합
            - 대규모 모델로 확장하기 쉬움
    - **BERT vs GPT** : Transformer 등장 이후 두 계열이 나타났습니다.
        - **BERT (양방향 인코더 기반)**: 텍스트를 양방향으로 동시에 읽어 문맥 이해에 강함 → 분류, 문맥 임베딩 등에 적합
        - **GPT (단방향 디코더 기반)**: 이전 문맥을 바탕으로 다음 토큰을 예측하며 생성 → **생성형 작업에 적합**
        - 핵심 전환점은 태스크마다 처음부터 학습시키는 대신, 대규모 비지도(unlabeled) 텍스트로 **사전학습**(pre-training) 한 뒤 특정 태스크에 맞게 파인튜닝하는 방식으로 옮겨간 것입니다.
    - **스케일링의 힘**
        - 모델 크기와 학습 데이터를 키울수록 성능이 크게 향상된다는 사실이 밝혀지며, **few-shot·zero-shot 학습 같은 능력**이 열렸습니다. 파라미터 수의 폭발적 증가가 이를 잘 보여줍니다.
            - **Zero-shot 학습**: 모델이 한 번도 **예시를 보지 않고도, 지시(instruction)만으로 새로운 태스크를 수행**하는 능력입니다.
            예: "이 문장을 프랑스어로 번역해줘" 라고만 요청해도, **번역 예시를 하나도 주지 않았는데 번역을 수행함**.
            - **Few-shot 학습**: 프롬프트 안에 몇 개(보통 1~수십 개)의 **예시를 함께 제공하면, 모델이 그 패턴을 참고해 유사한 새로운 입력에 대해 답을 생성**하는 능력입니다. 이때 모델의 가중치(weight)는 업데이트되지 않고, **단지 프롬프트 문맥(context) 안에서 예시를 참고할** 뿐입니다.
            예: "사과 → apple, 바나나 → banana, 포도 → ?" 처럼 몇 개의 번역 예시를 보여주면, 모델이 "포도 → grape"를 추론함.
            - **핵심 포인트**: 기존 머신러닝에서는 **새로운 태스크마다 별도의 학습(fine-tuning)이 필요**했지만, **GPT-3 같은 대규모 모델은 학습 없이 프롬프트만으로(zero-shot) 또는 소수 예시만으로(few-shot) 새로운 태스크에 적응**할 수 있음을 보여줬습니다. 이는 모델 크기와 학습 데이터 **규모를 키운 결과로 나타난 능력**(emergent ability)입니다.
        - GPT-1: 1억 1,700만 개
        - GPT-3 (2년 후): 1,750억 개
        - DeepSeek R1: 6,710억 개
        - 이런 규모 때문에 **"대규모 언어 모델(LLM)"**이라는 용어가 등장했습니다.
    
- **The Autoregressive Nature of Transformers** 트랜스포머의 자기회귀적 특성
    
    !Figure 2-2. Transformers generate tokens one at a time: the output token will be appended to the input sequence as a prompt for the next token generation Transformer는 token을 하나씩 생성하고, 생성된 token은 다음 token 생성을 위한 prompt에 추가된다.
    
    Figure 2-2. Transformers generate tokens one at a time: the output token will be appended to the input sequence as a prompt for the next token generation Transformer는 token을 하나씩 생성하고, 생성된 token은 다음 token 생성을 위한 prompt에 추가된다.
    
    - LLM의 핵심 특징 중 하나는 **자기회귀적(autoregressive)으로 텍스트를 생성**한다는 점입니다. 즉, **한 번에 토큰 하나씩 생성**하며, 새로 생성되는 각 토큰은 **이전에 생성된 모든 토큰을 조건으로 예측**됩니다.이 과정을 **반복하면 문장이 생성**된다.
        - 운영 관점에서 이 특성은 중요하다.
        - 요청 하나가 "한 번의 forward pass"가 아니라 여러 decode step의 연속이며, **생성 길이가 길수록 GPU 점유 시간이 길어진다.**
    - 왜 이런 방식인가
        - 이 단계적 과정 덕분에 **모델은 문맥적 일관성을 유지**하며, 각 단어가 이미 생성된 내용과 의미적으로 맞아떨어지도록 함
        - 이는 **사람이 언어를 만들어내는 방식**(앞선 맥락에 따라 점진적으로 단어를 이어가는 방식)과도 **유사**함
    - 생성 과정 예시 ("**미국 수도에 대한 짧은 소개를 써줘**"라는 프롬프트 기준)
        - 1단계: 모델이 초기 프롬프트를 받아 첫 토큰 **Washington** 생성
        - 2단계: 생성된 Washington을 원래 입력에 이어붙이고, 업데이트된 시퀀스를 다시 모델에 입력 → 다음 토큰 **D.C.** 생성
        - 3단계: 이제 프롬프트에 Washington D.C.까지 포함된 상태로 다음 토큰 **is** 생성
        - 4단계: is가 추가된 시퀀스로 다음 토큰 **the** 생성
    - 핵심 메커니즘
        - 매 단계마다 **직전 출력 토큰을 입력 시퀀스에 다시 덧붙여(append) 다음 토큰 생성의 입력**으로 사용합니다.
        - 이 과정은 최대 길이 도달 또는 특수 종료 토큰(stop token) 생성 같은 종료 조건을 만날 때까지 반복되며, 이렇게 토큰을 한 개씩 쌓아가면서 최종 출력 시퀀스를 완성합니다.
    
- **Decoder-Only Transformer Architecture**
    - 왜 디코더 전용 아키텍처를 다루는가
        - Transformer 기반 아키텍처는 여러 변형이 있지만, 이 책은 GPT, Llama, Qwen 등 대부분의 **생성형 LLM에 사용되는 디코더 전용(decoder-only) 구조에 집중**합니다. (번역·요약 등에 쓰이는 인코더-디코더 구조는 별도 주제)
    - **모델의 3대 구성요소** : 아래 "미국 수도에 대해 짧게 소개해줘" → "Washington" 생성 과정
        
        !Figure 2-3. Decoder-only Transformer는 tokenizer/embedding, transformer block 목록, LM head로 구성된다
        
        Figure 2-3. Decoder-only Transformer는 tokenizer/embedding, transformer block 목록, LM head로 구성된다
        
        - **1단계: 토크나이저 & 임베딩**
            - 원문 텍스트를 고정된 어휘(vocabulary) 기준으로 토큰으로 분리
            - 각 토큰을 토큰 ID(숫자)로 변환
            - 토큰 ID를 임베딩 레이어를 통해 벡터로 매핑 → Transformer 블록이 처리할 수 있는 형태로 준비
            - 예: "Write a short introduction about the US capital city" → 11개 토큰 → 토큰 ID → 임베딩 벡터
        - **2단계: Transformer(디코더) 블록**
            - 모델의 핵심부로, 실제 대부분의 연산이 일어나는 곳
            - 여러 개(예: 12, 24개 이상)의 디코더 블록이 쌓여, 프롬프트와 이전 출력에 대한 풍부한 문맥 이해를 토큰 단위로 구축
            - 출력은 hidden states(문맥화된 토큰 표현) : shape [N, d] (N=토큰 수, d=은닉 차원, 예: 768/2048/4096)
            - 보통 마지막 토큰에 해당하는 hidden state만 다음 토큰 예측에 사용됨
        - **3단계: LM(Language Modeling) 헤드**
            - hidden state를 어휘 전체에 대한 확률분포(logits)로 매핑
            - 가장 확률 높은 토큰을 다음 출력으로 선택 (예: Washington > London > New York > Cat)
    
- **실제 모델 사례: Qwen 2.5-0.5B ⇒ 아래 실습1 확인**
    - model.config를 통해 아키텍처 정보를 직접 확인할 수 있습니다.
        - Hidden size: 896, 레이어 수: 24, 어텐션 헤드 수: 14, Intermediate size: 4864
        - Vocabulary size: 151,936, 최대 시퀀스 길이: 32,768
        - 총 파라미터: 약 4억 9,400만 개
    - **왜 모델 설정(config)을 미리 확인해야 하나**
        - 레이어 수, 은닉 차원, 어텐션 헤드 수, 어휘 크기 등을 미리 파악하면 필요한 GPU 메모리 추정, 서빙 전략 선택(양자화, 배치 등), 성능 최적화 계획(레이어 병렬화, 모델 샤딩 등)에 도움이 됩니다.
    
- **Transformer (decoder) block ⇒ 아래 실습2 확인**
    
    !Figure 2-4. Transformer decoder block은 self-attention layer와 feedforward layer로 구성된다
    
    Figure 2-4. Transformer decoder block은 self-attention layer와 feedforward layer로 구성된다
    
    - 디코더 블록은 두 가지 핵심 컴포넌트로 구성됩니다.
        1. **셀프 어텐션(Self-Attention) 레이어**: Transformer의 핵심 혁신 요소로, 입력 토큰들 간의 의미·상대적 위치를 기반으로 동적으로 연관성을 계산합니다. 문맥 정보를 파악해 모호성을 줄이고 일관된 해석을 가능케 함, 이전 모든 토큰을 살펴보며 각 토큰에 다른 중요도(가중치)를 부여
        2. **피드포워드 신경망(FFN)**: 어텐션에서 얻은 문맥 정보를 활용해, 토큰 단위로 표현을 더 정교하게 다듬는 역할(고차원 dense 벡터로 정제)
        
    - Qwen 2.5 모델의 디코더 레이어를 확인 **⇒ 아래 실습2 확인**
    
- **Capture Token Context by Calculating Attention** : Attention으로 Token Context 포착 **⇒ 아래 실습3 확인**
    - **왜 문맥이 중요한가**
        - "I saw a dog chasing a squirrel, and it climbed up the tree"라는 문장에서, 문맥 없이는 "it"이 개를 가리키는지 다람쥐를 가리키는지 알 수 없습니다.
        - 2017년 "Attention Is All You Need" 논문 이후, 셀프 어텐션(self-attention)이 Transformer의 핵심 메커니즘이 되어, **시퀀스 내 각 토큰이 다른 토큰들을 "바라보며" 자신의 표현을 계산할 때 그 관련성을 반영**할 수 있게 했습니다.
    - 예: "Write a short introduction about the US capital city"에서 **capital 토큰**을 처리할 때 **셀프 어텐션**은
        - **US를 참조해 "국가의 수도"라는 의미임을 파악** (금융 용어 "capital"이 아니라)
        - introduction을 참조해 **간결하고 일반적인 톤을 유지**해야 함을 인식
        - Write를 참조해 전체 작업이 **"지시문(instructional)"임을 파악**
    - **어텐션 계산 원리** : 각 토큰마다 Query(Q), Key(K), Value(V) **세 벡터를 계산**합니다.
        1. 어떤 토큰의 Query와 시퀀스 내 모든 토큰의 Key를 내적(dot product)
        2. 결과를 스케일링(scaling)
        3. softmax를 적용해 가중치(weight)로 변환
        4. 이 가중치로 Value 벡터들의 가중합(weighted sum)을 계산
        - 이 결과가 해당 토큰의 업데이트된 표현이 되며, 전체 시퀀스의 문맥 정보가 반영됩니다. (자세한 수식은 논문의 "Scaled Dot-Product Attention" 절 참고)
    - 멀티헤드 어텐션(Multi-Head Attention)
        
        !Figure 2-5. Multi-head self-attention 계산 개념도
        
        Figure 2-5. Multi-head self-attention 계산 개념도
        
        - 토큰 하나당 어텐션을 한 번만 계산하는 게 아니라, 각기 다른 Q/K/V 프로젝션을 가진 **여러 개의 "헤드(head)"가 병렬로 어텐션을 계산**합니다.
        - 이를 통해 문법적·위치적·의미적 관계 등 **서로 다른 종류의 관계를 동시에 포착**할 수 있습니다.
        - 모든 헤드의 **출력은 이어붙여진(concatenate)** 뒤 선형 레이어를 거쳐 **최종 어텐션 출력**이 됩니다.
        
    - 실습 코드 (BertViz를 이용한 어텐션 시각화) **⇒ 아래 실습3 확인**
        
        
    - LLM 서빙에 집중하는 엔지니어에게는 수식을 깊이 파고들기보다 개념적으로 이해하는 것으로 충분!
    - 서빙 관점에서 정말 중요한 것은:
        - **어텐션은 연산량이 매우 크다**는 것 (특히 다음에 다룰 prefill 단계에서)
        - **메모리·지연시간 비용이 입력 시퀀스 길이에 비례해 증가**한다는 것
        - 이 정도의 이해만으로도 추론 성능 튜닝, KV 캐싱 구현, GPU 간 워크로드 분산 등을 다루는 데 충분합니다.
    
- https://github.com/orca3/llm-model-inference/blob/main/ch02/ch2_Inside_the_Mind_of_a_Transformer.ipynb : **Qwen 모델 설정 확인** by 구글 Colab
    - GPU T4 연결
        
        !스크린샷 2026-08-02 오전 3.11.01.png
        
        !colab-t4.png
        
    - **[실습1]** 모델 설정: model.config는 무엇인가요?
        - 모델의 모든 하이퍼파라미터와 설정을 포함하는 구성 객체입니다. 모델의 아키텍처, 크기, 그리고 동작 방식을 정의합니다.
        - 본질적으로 모델이 어떻게 구조화되어 있는지를 보여주는 설계도입니다.
        
        !Figure 2-3. Decoder-only Transformer는 tokenizer/embedding, transformer block 목록, LM head로 구성된다
        
        Figure 2-3. Decoder-only Transformer는 tokenizer/embedding, transformer block 목록, LM head로 구성된다
        
        ```python
        from transformers import AutoModelForCausalLM
        from pprint import pprint
        
        model_name = "**Qwen/Qwen2.5-0.5B**"
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            device_map="auto"
        )
        
        # Print all configuration parameters
        **config = model.config**
        print("\n=== Model Configuration Parameters ===")
        
        # Architecture parameters
        print("\nArchitecture Parameters:")
        print(f"Hidden size: {config.hidden_size}")  # Size of the hidden layers
        print(f"Number of layers: {config.num_hidden_layers}")  # Number of transformer blocks
        print(f"Number of attention heads: {config.num_attention_heads}")  # Number of attention heads
        print(f"Intermediate size: {config.intermediate_size}")  # Size of the MLP intermediate layer
        
        # Tokenizer parameters
        print("\nTokenizer Parameters:")
        print(f"Vocabulary size: {config.vocab_size}")  # Size of the vocabulary
        print(f"Maximum position embeddings: {config.max_position_embeddings}")  # Maximum sequence length
        
        # Print model size
        total_params = sum(p.numel() for p in model.parameters())
        print(f"\nModel Size:")
        print(f"Total parameters: {total_params:,}")
        
        # Model-specific parameters
        print("\nModel-specific Parameters:")
        for key, value in config.to_dict().items():
            if key not in ['architectures', 'model_type', 'torch_dtype']:
                print(f"{key}: {value}")
        
        # Free GPU memory
        free_gpu(model)
        ```
        
        ```python
        arning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
        WARNING:huggingface_hub.utils._http:Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
        **config.json**: 100%
         681/681 [00:00<00:00, 65.7kB/s]
        **model.safetensors**: reconstructing file: 100%
          988MB /  988MB, 61.8MB/s  
        **model.safetensors**: downloading bytes: 
          855MB, 67.4MB/s  
        **Loading weights**: 100%
         290/290 [00:00<00:00, 849.09it/s]
        **generation_config.json**: 100%
         138/138 [00:00<00:00, 14.7kB/s]
        
        **=== Model Configuration Parameters ===**
        
        **Architecture Parameters: 아키텍처 파라미터 - 총 파라미터 약 4억 9,400만 개**
        Hidden size: 896         # 모델 내부에서 토큰 하나를 표현하는 벡터의 차원 수(임베딩 차원), 모든 레이어를 통과하는 동안 이 크기의 벡터로 정보가 흐름
        Number of layers: 24     # 트랜스포머 블록(Self-Attention + FFN)이 24번 반복됨, 레이어가 깊을수록 더 복잡한 패턴/추론을 학습할 수 있지만, 학습 난이도와 추론 지연시간도 증가
        Number of attention heads: 14  #  Multi-Head Attention에서 어텐션을 14개의 독립적인 "머리"로 나눠 병렬로 계산 , 각 head 차원 = 896 / 14 = 64
        Intermediate size: 4864  # FFN(Feed-Forward Network)의 은닉층 크기
        
        Tokenizer Parameters:
        **Vocabulary size: 151936  # 모델이 인식하는 고유 토큰(서브워드)의 개수, 다국어(특히 중국어 포함) 지원을 위해 매우 큰 편 — 영어 전용 모델(GPT-2 등)은 보통 5만 개 내외**
        Maximum position embeddings: 32768  # 모델이 한 번에 처리할 수 있는 최대 시퀀스 길이(컨텍스트 윈도우), 32K 토큰 ≈ 책 한 권 분량의 텍스트를 한 번에 처리 가능
        
        Model Size:
        **Total parameters: 494,032,768  #** 임베딩(1.36억) + 24개 레이어(약 3.5억대) 를 합치면 약 4.94억 개
        
        **Model-specific Parameters: 세부 설정값**
        transformers_version: 5.13.1
        return_dict: True
        **dtype: bfloat16**            # 가중치가 16비트 부동소수점으로 저장됨 (메모리 절반 절약, GPU 서빙 표준)
        chunk_size_feed_forward: 0
        is_encoder_decoder: False
        id2label: {0: 'LABEL_0', 1: 'LABEL_1'}
        label2id: {'LABEL_0': 0, 'LABEL_1': 1}
        problem_type: None
        vocab_size: 151936
        hidden_size: 896
        intermediate_size: 4864
        num_hidden_layers: 24
        num_attention_heads: 14
        **num_key_value_heads: 2**    # GQA(Grouped Query Attention) 사용 — 어텐션 헤드는 14개지만 K/V 헤드는 2개만 사용해 KV 캐시 메모리를 크게 절감
        hidden_act: silu          # FFN(피드포워드)의 활성화 함수로 SiLU 사용
        max_position_embeddings: 32768
        initializer_range: 0.02
        rms_norm_eps: 1e-06       # RMSNorm(레이어 정규화)의 안정성용 작은 상수
        **use_cache: True**           # 생성 시 KV 캐시를 재사용하겠다는 설정 (디코딩 속도 향상의 핵심)
        tie_word_embeddings: True # 입력 임베딩과 출력(LM head) 가중치를 공유해 파라미터 수 절약 - 작은 모델(0.5B)에서 흔한 기법
        rope_parameters: {'rope_theta': 1000000.0, 'rope_type': 'default'} # RoPE(Rotary Position Embedding) 방식으로 위치 정보를 인코딩
        use_sliding_window: False # 슬라이딩 윈도우 어텐션 미사용 → 모든 레이어가 전체 시퀀스에 대해 어텐션 계산 (layer_types가 전부 full_attention인 것과 일치)
        sliding_window: None
        max_window_layers: 24
        layer_types: ['full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention', 'full_attention']
        attention_dropout: 0.0
        pad_token_id: None
        bos_token_id: 151643      # 시작/종료 토큰 ID (Qwen은 둘이 동일)  — 생성 종료 조건 판단에 사용
        eos_token_id: 151643      # 상동
        _name_or_path: Qwen/Qwen2.5-0.5B
        use_mrope: False
        output_attentions: False  # 추론 시 어텐션 가중치나 중간 hidden state를 반환하지 않음 (성능을 위해 기본값 False)
        output_hidden_states: False # 상동
        ```
        
    - **[실습2]** Qwen 2.5 모델의 디코더 레이어를 확인
        - 모델 내부 모듈을 출력하면 embedding, decoder layer, self-attention, MLP, normalization 계층이 반복되는 구조를 확인할 수 있다.
        
        !Figure 2-4. Transformer decoder block은 self-attention layer와 feedforward layer로 구성된다
        
        Figure 2-4. Transformer decoder block은 self-attention layer와 feedforward layer로 구성된다
        
        ```python
        import torch
        from transformers import AutoModelForCausalLM
        from pprint import pprint
        
        # Load the model
        model = AutoModelForCausalLM.from_pretrained(
            "**Qwen/Qwen2.5-0.5B**",
            trust_remote_code=True,
            device_map="auto"  # This will automatically handle device placement
        )
        
        print(f"\n=== {model_name} Architecture ===")
        print("\nModel Configuration:")
        # pprint(model.config.to_dict())
        
        print("\nModel Structure:")
        **def print_module_structure(module, prefix=''):**
            for name, child in module.named_children():
                # Skip certain internal modules for clarity
                if name in ['_orig_mod', 'wrapped_model']:
                    continue
        
                # Print the current module
                print(f"{prefix}{name}: {type(child).__name__}")
        
                if "Qwen2Attention" in name.lower():
                  print(f"\nFound attention module: {name}")
                  print(f"Type: {type(module).__name__}")
        
                  **# Print attention-specific attributes**
                  if hasattr(module, 'num_heads'):
                      print(f"Number of attention heads: {module.num_heads}")
                  if hasattr(module, 'head_dim'):
                      print(f"Head dimension: {module.head_dim}")
                  if hasattr(module, 'hidden_size'):
                      print(f"Hidden size: {module.hidden_size}")
                  if hasattr(module, 'rotary_emb'):
                      print(f"Has rotary embeddings: {module.rotary_emb is not None}")
        
                # If it's a container module (has children), recurse
                if list(child.children()):
                    print_module_structure(child, prefix + '  ')
        
        print_module_structure(model)
        
        free_gpu(model)
        ```
        
        ```python
        Loading weights: 100%
         290/290 [00:00<00:00, 904.81it/s]
        
        === Qwen/Qwen2.5-0.5B Architecture ===
        
        Model Configuration:
        
        Model Structure:
        model: Qwen2Model
          **embed_tokens: Embedding**        # 토큰 ID → 임베딩 벡터 변환
          **layers: ModuleList**             # 디코더 블록 24개 (0~23)
            0: Qwen2DecoderLayer
              self_attn: Qwen2Attention
                **q_proj / k_proj / v_proj / o_proj: Linear**   # Query/Key/Value/Output 투영
              mlp: Qwen2MLP
                gate_proj: Linear
                up_proj: Linear
                down_proj: Linear
                act_fn: SiLUActivation
              input_layernorm: Qwen2RMSNorm
              post_attention_layernorm: Qwen2RMSNorm
            1: Qwen2DecoderLayer  **(동일 구조 반복)**
            ...
            **23**: Qwen2DecoderLayer **(동일 구조 반복)**
          **norm: Qwen2RMSNorm**                # 마지막 디코더 블록 이후 최종 정규화
          rotary_emb: Qwen2RotaryEmbedding  # 모든 레이어가 공유하는 RoPE 위치 인코딩 모듈
        **lm_head: Linear**                     # 최종 hidden state → vocab logits 변환
        ```
        
        - 0부터 23까지 총 24개 레이어 : 앞서 config에서 확인한 num_hidden_layers: 24와 정확히 일치
            - 각 레이어는 완전히 동일한 구조(self_attn + mlp + 2개의 layernorm)를 가지며, 학습된 가중치 값만 다름.
        - self_attn 내부 4개의 Linear:
            - q_proj, k_proj, v_proj: 입력을 Query/Key/Value로 투영
            - o_proj: 어텐션 결과를 다시 hidden_size 차원으로 투영
            - 앞서 config의 num_key_value_heads: 2(GQA)로 인해 k_proj/v_proj의 출력 차원이 q_proj보다 작을 것으로 예상됨 (일반 MHA와 다른 점)
        - mlp 내부 구조 (SwiGLU 계열 FFN):
            - gate_proj + up_proj → act_fn(SiLU) 적용 → down_proj로 다시 축소
            - 이는 GPT류 모델에서 흔한 단순 2-layer FFN이 아니라, Llama/Qwen 계열이 채택한 게이트형 FFN(SwiGLU) 구조
        - 레이어 바깥의 norm, rotary_emb, lm_head: 이 세 모듈은 layers 리스트 안에 속하지 않고 Qwen2Model/model 레벨에 한 번만 존재
            - 즉 모든 디코더 레이어가 rotary_emb(위치 인코딩 계산 로직)을 공유하며, 최종 출력 직전에 norm 한 번, 이후 lm_head에서 vocab 크기(151,936)로 매핑.
        
    - [실습2.5/옵션] attention layer 확인 ⇒ **GQA 확인**
        
        ```python
        model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-0.5B",
            trust_remote_code=True,
            device_map="auto"
        )
        
        print(f"\n=== Detailed {model_name} Attention Analysis ===")
        
        # Find all attention layers
        attention_layers = []
        for name, module in model.named_modules():
            #if "attention" in name.lower():
            if "Qwen2Attention" in type(module).__name__:
                attention_layers.append((name, module))
        
        print(f"\nFound {len(attention_layers)} attention layers")
        
        # Analyze each attention layer
        for i, (name, module) in enumerate(attention_layers):
            print(f"\nAttention Layer {i}: {name}")
            print("=" * 50)
        
            # Basic information
            print(f"Type: {type(module).__name__}")
        
            # Attention parameters
            if hasattr(module, 'num_heads'):
                print(f"Number of attention heads: {module.num_heads}")
            if hasattr(module, 'head_dim'):
                print(f"Head dimension: {module.head_dim}")
            if hasattr(module, 'hidden_size'):
                print(f"Hidden size: {module.hidden_size}")
        
            # Rotary embeddings
            if hasattr(module, 'rotary_emb'):
                print(f"Rotary embeddings: {type(module.rotary_emb).__name__ if module.rotary_emb else 'None'}")
        
            # Attention projections
            print("\nAttention projections:")
            for sub_name, sub_module in module.named_children():
                if hasattr(sub_module, 'weight'):
                    shape = sub_module.weight.shape
                    print(f"  {sub_name}: {type(sub_module).__name__}, Shape: {shape}")
        
            # Additional attention-specific attributes
            print("\nAdditional attributes:")
            for attr_name in dir(module):
                if not attr_name.startswith('_') and not callable(getattr(module, attr_name)):
                    try:
                        value = getattr(module, attr_name)
                        if not isinstance(value, (torch.Tensor, torch.nn.Module)):
                            print(f"  {attr_name}: {value}")
                    except:
                        pass
        
        # Print model's attention-related configuration
        print("\nAttention-related configuration:")
        config = model.config.to_dict()
        attention_config = {k: v for k, v in config.items() if 'attention' in k.lower()}
        pprint(attention_config)
        
        free_gpu(model)
        ```
        
        ```python
        Loading weights: 100%
         290/290 [00:01<00:00, 286.85it/s]
        
        === Detailed Qwen/Qwen2.5-0.5B Attention Analysis ===
        
        Found 24 attention layers
        
        Attention Layer 0: model.layers.0.self_attn
        ==================================================
        Type: Qwen2Attention
        Head dimension: 64
        
        Attention projections:
          q_proj: Linear, Shape: torch.Size([896, 896])
          k_proj: Linear, Shape: torch.Size([128, 896])
          v_proj: Linear, Shape: torch.Size([128, 896])
          o_proj: Linear, Shape: torch.Size([896, 896])
        
        Additional attributes:
          T_destination: ~T_destination
          attention_dropout: 0.0
          call_super_init: False
          config: Qwen2Config {
          "architectures": [
            "Qwen2ForCausalLM"
          ],
          "attention_dropout": 0.0,
          "bos_token_id": 151643,
          "dtype": "bfloat16",
          "eos_token_id": 151643,
          "hidden_act": "silu",
          "hidden_size": 896,
          "initializer_range": 0.02,
          "intermediate_size": 4864,
          "layer_types": [
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention",
            "full_attention"
          ],
          "max_position_embeddings": 32768,
          "max_window_layers": 24,
          "model_type": "qwen2",
          "num_attention_heads": 14,
          "num_hidden_layers": 24,
          "num_key_value_heads": 2,
          "pad_token_id": null,
          "rms_norm_eps": 1e-06,
          "rope_parameters": {
            "rope_theta": 1000000.0,
            "rope_type": "default"
          },
          "sliding_window": null,
          "tie_word_embeddings": true,
          "transformers_version": "5.13.1",
          "use_cache": true,
          "use_mrope": false,
          "use_sliding_window": false,
          "vocab_size": 151936
        }
        
          dump_patches: False
          head_dim: 64
          is_causal: True
          layer_idx: 0
          layer_type: full_attention
          num_key_value_groups: 7
          scaling: 0.125
          sliding_window: None
          training: False
        
        Attention Layer 1: model.layers.1.self_attn
        ==================================================
        Type: Qwen2Attention
        Head dimension: 64
        ... 반복
        ```
        
        - Q/K/V 프로젝션의 shape가 다른 이유 ⇒ **GQA(Grouped Query Attention)**
            - q_proj [896, 896] : 14개 헤드 × head_dim 64 = 896
            - k_proj [128, 896] : 2개 KV 헤드 × head_dim 64 = 128
            - v_proj [128, 896] : 2개 KV 헤드 × head_dim 64 = 128
            - o_proj [896, 896] : 어텐션 출력을 다시 hidden_size(896)로 투영
        - 즉 Query는 14개 헤드를 온전히 갖지만, Key/Value는 단 2개 헤드만 계산합니다
            - config : num_attention_heads: 14 vs num_key_value_heads: 2
        - 핵심 파생 값들
            - head_dim: 64 → 각 헤드가 다루는 벡터 차원 (896 ÷ 14 = 64)
            - num_key_value_groups: 7 → Query 헤드 14개를 KV 헤드 2개가 나눠서 공유 (14 ÷ 2 = 7). 즉 Query 헤드 7개씩이 같은 K/V 헤드 하나를 공유
            - scaling: 0.125 → 어텐션 스코어 계산 시 나누는 값, 1/√head_dim = 1/√64 = 0.125 (Scaled Dot-Product Attention 공식의 스케일링 팩터)
            - is_causal: True → 각 토큰이 자기 자신과 이전 토큰들만 볼 수 있도록 마스킹 (미래 토큰을 못 보게 함) — 자기회귀적 생성과 직결되는 설정
            - layer_type: full_attention / sliding_window: None → 슬라이딩 윈도우 없이 전체 시퀀스에 대해 어텐션 계산
        - **왜 GQA를 쓰는가 (서빙 관점에서 중요)**
            - 일반적인 멀티헤드 어텐션(MHA)이라면 Key/Value도 14개 헤드를 다 가져야 하지만, **GQA는 2개 헤드만 사용해 K/V를 저장**합니다.
            - 이는 **추론 시 유지해야 하는 KV 캐시의 크기를 약 7배 줄여주는 효**과가 있어, **메모리 사용량과 서빙 비용을 크게 낮춥**니다.
            - 이것이 뒤에서 다룰 KV 캐시 최적화(vLLM 등)의 배경이 되는 아키텍처적 선택입니다.
        
    - **[실습3]** BertViz를 이용한 어텐션 시각화 ⇒ **특정 token이 어떤 token에 더 많이 주목하는지 확인**
        - BertViz의 head_view를 이용해 Qwen2.5-0.5B 모델의 셀프 어텐션을 시각화하는 실습입
        
        ```python
        # prompt: use bertviz library to visualize the attention result of the input prompt "write a short introduction about US capital city"
        from transformers import AutoTokenizer
        from bertviz import head_view
        
        # Your input text
        text = "The tiny animal was overwhelmed by the confetti and it attempted to bat away the glitter with its little paws."
        model_name = "Qwen/Qwen2.5-0.5B"
        tokenizer = AutoTokenizer.from_pretrained(model_name, output_attentions=True)
        model = AutoModelForCausalLM.from_pretrained(model_name, output_attentions=True).eval().cuda()
        
        # Tokenize input and get token strings
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
        
        # Generate outputs with attention
        with torch.no_grad():
            outputs = model(**inputs, output_attentions=True)
        
        # Get attention weights
        attention = outputs.attentions
        
        # Use bertviz to visualize
        head_view(attention, tokens)
        ```
        
        ```python
        tokenizer_config.json: 100%
         7.23k/7.23k [00:00<00:00, 702kB/s]
        vocab.json: 100%
         2.78M/2.78M [00:00<00:00, 45.4MB/s]
        merges.txt: 100%
         1.67M/1.67M [00:00<00:00, 49.3MB/s]
        tokenizer.json: 100%
         7.03M/7.03M [00:00<00:00, 110MB/s]
        [transformers] The following generation flags are not valid and may be ignored: ['output_attentions']. Set `TRANSFORMERS_VERBOSITY=info` for more details.
        Loading weights: 100%
         290/290 [00:00<00:00, 3775.85it/s]
        ```
        
        !Figure 2-6. Transformer layer 10에서 "capital" token의 multi-head attention 시각화
        
        Figure 2-6. Transformer layer 10에서 "capital" token의 multi-head attention 시각화
        
- `도전과제` Why LLMs Use 75% Less Memory - GQA & MQA Explained in 8 Min - Youtube : 해당 영상 학습 후 동작 정리
- `도전과제` ipynb 실습을 자신의 로컬 PC에 주피터 노트북 설치 후 실행 해보기
- `도전과제` 1주차 학습 내용과 관련된 주제를 **Inference Engineering(2026).pdf** 내용에서 발췌해서 정리 해보기
- `도전과제` **’밑바닥부터 만들면서 배우는 LLM’ 책** 제공 실습으로 LLM 추론/학습 후 정리 해보기 - Code , Youtube

### Executing LLM Generation: A Step-by-Step Waklthrough

- 실습 개요
    - 이 섹션에서는 KV 캐시, 프리필, 디코딩 같은 핵심 내부 LLM 서비스 개념을 설명하며, **LLM이 토큰을 생성하는 과정**을 단계별로 보여드리겠습니다.
    - 우리의 목표는 트랜스포머 이론을 가르치는 것이 아니라, **LLM이 추론 중 어떻게 실행**되는지에 대한 서비스 지향적 정신 모델을 구축하는 것입니다. 왜냐하면 이 실행 패턴이 LLM 서비스 시스템의 거의 모든 설계 결정을 이끄는 핵심이기 때문입니다.
    - 데모 코드에서는 시연을 위해 **단일 요청**과 **단일 시퀀스 예제**를 사용했으며, 실제 운영 환경에서는 권장되지 않습니다. 이후 장에서는 **서빙 시스템이 이 실행 패턴을 대규모로 배치**하고, **스트리밍**하며, **최적화**하는 방법을 설명할 것입니다.
    - **LLM 생성 과정을 한 줄씩 따라가면서, 각 코드가 무엇을 하는지뿐 아니라 실행이 시간에 따라 어떻게 전개되는지에 주목**하세요. 여기서 소개한 토큰 단위 실행, 프리필과 디코드, 캐시된 상태 같은 개념들은 배칭, 스트리밍, KV 캐시 최적화, 그리고 vLLM이나 SGLang 같은 프레임워크를 다룰 때 **책 전반에 걸쳐 다시 등장**할 것입니다.
    - 이 워크스루를 마치면 LLM 추론이 어떻게 작동하는지 명확하고 실용적으로 이해하게 될 것입니다. 처음 읽었을 때 어떤 세부 사항이 낯설게 느껴져도 괜찮습니다. 이 절의 목적은 여러분에게 직관을 제공하는 것이며, 이러한 개념들은 이후 장에서 다시 다루고 구체화할 것입니다.
    
- https://github.com/orca3/llm-model-inference/blob/main/ch02/ch2_Workthrough_LLM_execution.ipynb : **Qwen 모델 설정 확인** by 구글 Colab
- **[실습1]** Qwen 모델 실행하기 (Hugging Face pipeline 사용) : **텍스트 생성 실습**
    - **가장 간단하게 LLM을 사용**하는 방법으로 **Hugging Face**의 **pipeline API**를 소개합니다 - Docs
    - **pipeline 객체**는 토크나이징, 모델 로딩, 생성, 디코딩 등 **내부 복잡한 과정을 모두 추상화**해서, **몇 줄의 코드만으로 텍스트 생성을 가능**하게 합니다.
        
        ```python
        # 텍스트 생성 태스크용 파이프라인을 초기화하면서 지정한 모델(Qwen2.5-0.5B)과 그에 맞는 토크나이저를 자동으로 로드
        # Initialize the text generation pipeline
        generator = pipeline('text-generation', model='Qwen/Qwen2.5-0.5B')
        
        # Define your prompt
        prompt = "**Write a short introduction about the US capital city.**"
        
        # max_length=**50**: 생성될 전체 시퀀스(입력 프롬프트 + 생성된 텍스트)의 최대 토큰 길이를 50으로 제한
        # num_return_sequences=1: 하나의 결과만 생성 (여러 개 생성하고 싶다면 값을 늘리면 됨, 이 경우 서로 다른 샘플링 결과를 여러 개 받을 수 있음)
        # Generate text
        generated_text = generator(prompt, max_length=**50**, num_return_sequences=**1**)
        
        # 반환값 generated_text는 딕셔너리 리스트 형태이며, generated_text[0]['generated_text']로 생성된 전체 텍스트(프롬프트 포함)에 접근
        # Print the generated text
        print(generated_text[0]['generated_text'])
        ```
        
        ```python
        **# 아래 출력 문장 확인**
        **Write a short introduction about US capital city.** *The US capital city, Washington, D.C., is the only capital city in the United States, as well as the only one in the world with both a white and a black population. The city is located on the National Mall in the heart of the nation's capital, and is home to many historical landmarks, museums, and government buildings. Washington is also known as the "City of Democracy" and is home to the United States' oldest political institutions, the United States Capitol and the White House. The city is home to the President of the United States, as well as the Mayor of the United States, and has a vibrant cultural scene, including the National Gallery, the Smithsonian National Museum of African American History and Culture, and the National Museum of Natural History. Washington is also home to many of the most important institutions of the United States, including the White House, the National Mall, and the historic buildings of the Smithsonian Institution.*
        
        미국의 수도에 대한 짧은 소개를 작성하세요. 미국의 수도인 워싱턴 D.C.는 미국에서 유일한 수도일 뿐만 아니라, 백인과 흑인 인구가 모두 존재하는 세계 유일의 수도이기도 합니다. 이 도시는 수도 중심부에 있는 내셔널 몰에 위치해 있으며, 많은 역사적 명소와 박물관, 그리고 정부 청사들이 자리하고 있습니다. 워싱턴은 또한 "민주주의의 도시"로 알려져 있으며, 미국에서 가장 오래된 정치 기관들과 미국 국회의사당, 그리고 백악관이 있는 곳입니다. 이 도시는 미국 대통령과 미국 시장의 거주지이며, 국립미술관, 스미스소니언 국립 아프리카계 미국인 역사·문화 박물관, 국립 자연사 박물관 등 활기찬 문화 명소를 갖추고 있습니다. 워싱턴에는 백악관, 내셔널 몰, 그리고 스미스소니언 박물관의 역사적인 건물들처럼 미국에서 가장 중요한 기관들이 많이 자리하고 있습니다.
        ```
        
        ```python
        # Define your prompt
        prompt = "**대한민국의 수도에 대한 짧은 소개를 작성하세요."**
        
        대한민국의 수도에 대한 짧은 소개를 작성하세요. 대한민국의 수도는 서울입니다. 서울은 대한민국의 중심지로, 대전, 남양주, 성남, 김포, 용인等 지역에서도 주민들이 삶의 전환을 위해 뛰어들인다.
        대한민국의 수도에 대한 짧은 소개를 작성하세요. 대한민국의 수도는 서울입니다. 서울은 대한민국의 중심지로, 대전, 남양주, 성남, 김포, 용인等 지역에서도 주민들이 삶의 전환을 위해 뛰어들인다.
        대한민국의 수도에 대한 짧은 소개를 작성하세요. 대한민국의 수도는 서울입니다. 서울은 대한민국의 중심지로, 대전, 남양주, 성남, 김포, 용인等 지역에서도 주민들이 삶의 전환을 위해 뛰어들인다.
        ```
        
        ```python
        # Define your prompt
        prompt = "Write a short introduction about US capital city."
        ```
        
    - pipeline은 프로토타이핑이나 빠른 실험에는 훌륭하지만, 내부에서 정확히 어떤 일이 일어나는지(토크나이징, KV 캐시, 배치 처리 등)를 이해하기는 어렵습니다.
    - 이후 절에서는 이 추상화를 한 겹씩 벗겨내면서, LLM 서빙의 핵심 동작 원리를 직접 코드로 확인해볼 예정입니다
    
- **[실습2]** 모델 예측을 한 줄씩 뜯어보기 (Line by Line) :  KV Cache 미사용 시
    
    !Figure 2-7. LLM의 token-by-token generation workflow
    
    Figure 2-7. LLM의 token-by-token generation workflow
    
    - pipeline()이 내부적으로 하던 일을 이번엔 **AutoModelForCausalLM**을 사용해 **직접 구현**합니다.
    - 이렇게 하면 생성 설정, 입력 처리, 디코딩 전략까지 전 과정을 세밀하게 제어할 수 있습니다.
        
        
    1. **토크나이저와 모델 로드**
        
        ```python
        # (1) Load tokenizer and model
        model_name = "Qwen/Qwen2.5-0.5B"
        **tokenizer** = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        **model** = (
            **AutoModelForCausalLM**.from_pretrained(
                model_name, trust_remote_code=True,
            ).to("cuda" if torch.cuda.is_available() else "cpu")
        )
        ```
        
    2. **입력 프롬프트 정의** : “인간 역사~다음 세대 커뮤니케이션 도구에 대한 질문”
        
        ```python
        # (2) Define the input prompt
        prompt = """The history of human … … … How might the next wave of 
        communication tools shape our relationships, societies, and sense 
        of identity?"""
        ```
        
    3. 프롬프트 토큰화 : 
        
        ```python
        # (3) Convert (tokenize) prompt to the input format that model understands
        max_new_tokens = 100
        # tokenize the input prompt for the first output token
        # PS: prompt is the initial input sequence for LLM generation
        # idx는 이후 계속 갱신되는 입력 시퀀스로, 최초에는 프롬프트만 담고 있다가 매 스텝마다 새로 생성된 토큰이 덧붙여짐
        **idx = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)**
        start_time = total_time = time.time()
        times = []
        ```
        
    4. **메인 생성 루프** : 토큰을 하나씩 생성, `max_new_tokens=100`회 반복
        
        ```python
        # (4) Main generation loop - generate tokens one by one
        for _ in range(max_new_tokens):
           # (A) Set the current context for generation
           **idx_cond = idx**
           with torch.no_grad():
               # (B) Generate predictions (token candidates) for next token
               **outputs = model(idx_cond)**
               # Get the logits (raw prediction scores) for each token prediction
               logits = outputs.logits
        ```
        
        - (A) 현재까지의 시퀀스(idx_cond = idx)를 컨텍스트로 설정
        - (B) outputs = model(idx_cond) → 모델이 forward pass를 실행해 logits(각 토큰에 대한 원시 예측 점수) 획득
        
        ```python
        # (C) Select next token from the predictions generated in step (B)
           **logits = logits[:, -1, :]** #  Select only the logits for the last token
           # Convert logits to probabilities using softmax
           probas = **torch.softmax**(logits, dim=-1)    
           # Sample the next token from the probability distribution of the 
           predicted tokens from step (B)
           idx_next = **torch.multinomial(probas, num_samples=1)**
           print("Next Token is:", tokenizer.decode(idx_next[0])
           time_cost = time.time() - start_time
           times.append(time_cost)
        ```
        
        - (C) 다음 토큰 선택
            - logits[:, -1, :]로 **마지막 토큰의 logits**만 사용 (다음에 올 토큰을 예측하는 것이므로)
            - **softmax**로 확률분포 변환
            - torch.multinomial(probas, num_samples=1)로 **확률적 샘플링**(단순히 가장 높은 확률의 토큰만 뽑는 게 아니라 분포에서 **무작위 샘플링** → 이 때문에 같은 프롬프트라도 실행할 때마다 다른 결과가 나올 수 있음)
        
        ```python
          # (D) Append the new token to the input sequence
           idx = torch.cat((idx, idx_next), dim=1)
        
           # (E) Check if end-of-sequence token was generated
           if idx_next.item() == tokenizer.eos_token_id:
               print("\n[Generation completed - EOS token reached]")
               break
        ```
        
        - (D) idx = torch.cat((idx, idx_next), dim=1) → 새 토큰을 시퀀스 끝에 이어붙임 (앞서 설명한 자기회귀 방식 그대로)
        - (E) 생성된 토큰이 EOS(문장 종료) 토큰이면 루프 종료
        
    5. 전체 시퀀스 디코딩
        
        ```python
        # (5) Decode the entire generated sequence
        generated_text = tokenizer.decode(idx[0], skip_special_tokens=True)
        ```
        
    6. Display the generation time taken for each token
        
        ```python
        import matplotlib.pyplot as plt
        
        # First chart: First bar red, others blue
        plt.figure(figsize=(12, 4))
        # plt.subplot(1, 2, 1)
        plt.bar(range(len(times)), times, color=['red'] + ['blue'] * (len(times) - 1))
        plt.xlabel("Token ID")
        plt.ylabel("Time Spent in Token Generation")
        plt.title("LLM Generation Times for each token")
        
        # # Second chart: Exclude the first element
        # plt.subplot(1, 2, 2)
        # plt.bar(range(len(times) - 1), times[1:])
        # plt.xlabel("Token ID")
        # plt.ylabel("Time Spent in Token Generation")
        # plt.title("Token Generation Times (Excluded the initial prompt tokens)")
        
        # plt.tight_layout()
        # plt.show()
        ```
        
    - 결과
        
        !image.png
        
    - **실측 결과 및 중요한 관찰**
        - **100개 토큰 생성에 총 12.87초**, 토큰당 평균 약 0.12초
            
            !스크린샷 2026-08-02 오전 4.05.38.png
            
        - 첫 토큰을 제외하면, **토큰이 생성될수록 생성 시간이 점점 늘어나는 패턴이 관찰됨**
            
            !Text(0.5, 1.0, 'LLM Generation Times for each token')
            
            Text(0.5, 1.0, 'LLM Generation Times for each token')
            
        
    - **왜 점점 느려지는가? → 핵심 비효율 포착**
        
        !Figure 2-9. KV cache 없이 매번 전체 input sequence를 재처리하는 구조
        
        Figure 2-9. KV cache 없이 매번 전체 input sequence를 재처리하는 구조
        
        - 매 스텝마다 idx_cond(=idx 전체)를 다시 모델에 통째로 입력하기 때문에, **시퀀스가 길어질수록 이전에 이미 계산했던 토큰들의 어텐션까지 매번 처음부터 다시 계산**하게 됩니다. 즉:
            - 새 토큰 1개를 얻기 위해 이전 토큰 전체에 대한 **Q/K/V 및 어텐션을 반복 재계산**
            - 시퀀스 길이가 길어질수록 연산량과 리소스 사용량이 계속 증가
        - 이는 명백히 **불필요한 중복 계산**입니다.
            - "이미 계산된 이전 토큰의 어텐션은 재사용하고, **새로 추가된 토큰에 대해서만 계산하면 되지 않을까?"**
        - 이 질문이 바로 다음 절에서 다룰 **KV 캐시(KV Cache) 개념**으로 이어집니다 ⇒ 이전 토큰들의 Key/Value를 캐싱해두어 매 스텝 재계산을 피하는 최적화 기법입니다.
    
- **[딥러닝 큐레이터 임커밋] KV cache** - Youtube & [Visual AI] And How KV Cache Fixes It - Youtube
    - Attention 계산 과정
        
        !https://www.youtube.com/watch?v=vkhPtpUiLd8
        
        https://www.youtube.com/watch?v=vkhPtpUiLd8
        
    - cache : 이미 계산한 걸 또 쓰려고 저장
    - KV cache : Attention 의 Key, Value 를 캐시
    - Attention 구성 요소 : Q 쿼리, K 키, V 값 = Wq, Wk, Wv
        
        !image.png
        
        - Q 쿼리 : 가중치 계산에서 주입하는 재료
            
            !image.png
            
        - K 키 : 주어진 맥락 정보(가중치 재료)
            
            !image.png
            
        - V 값 : 각 키에 대응되는 attention 출력 재료
            
            !image.png
            
        
    - **KV cache 이해 3단계**
        1. KV cache 없이 생성한다면?
        2. 정확히 무엇을 caching 하는지
        3. 어떤 중복 계산을 피하는지
    - **KV cache 없이 생성한다면?**
        - 주어진 텍스트를 앞에 붙여놓고,
            
            !image.png
            
        - 전부 다 LLM 입력에 집어넣습니다.
            
            !image.png
            
        - 앞에 텍스트 token 길이가 L,
            
            !image.png
            
        - self-attention 안에서 이 sequence 가 q, k, v weight 를 통과해서 ⇒ L 길이 Q시퀀스, K시퀀스, V시퀀스가 됨!
            
            !image.png
            
            !image.png
            
            !image.png
            
        - 여기서 query, key 의 내적으로, L개 query 각각에 대한 L길이 가중치가 생김 ***⇒ $L^2$ 개의 가중치가 생김!***
            
            !맨 하단이 쿼리
            
            맨 하단이 쿼리
            
            !query, key 의 내적 작업
            
            query, key 의 내적 작업
            
            !L개 query 각각에 대한 L길이 가중치가 생김
            
            L개 query 각각에 대한 L길이 가중치가 생김
            
        - 이 가중치와 value 로 weighted sum 인 = attention 출력이 나오구요.
            
            !스크린샷 2026-06-24 오후 6.28.08.png
            
            !weighted sum 수행
            
            weighted sum 수행
            
        - 이 뒤에는 FFN이고, 같은 layer 가 반복돼서,
            
            !image.png
            
        - LLM의 출력이 만들어짐
            
            !image.png
            
        - 다시 돌아와서, self attention 계산 복잡도를 보자 : 가장 많은 계산은 **가중치를 구하는 query, key 내적**입니다.
            
            !image.png
            
        - sequence 의 dimension이 D라고 하면,
            
            !image.png
            
        - 내적에 필요한 D번의 곱셉과 D번의 덧셈, D에 비례하는 계산을 query 전체 길이 L, key 전체 길이 L = 총  ***$L^2$*** 번 수행.
            
            !image.png
            
        - 계산 복잡도  ***O($L^2$ D) ,*** 참고로 L은 sequence 길이이다.
            
            !image.png
            
        - 이 부담스러운 계산 결과, 결국 얻는 건 고작 **다음 토큰 하나!**
        - **해당 토큰**은 LLM 출력 sequence 에서 **맨 뒤만 쓰고**, 그 **앞에 것들은 다 버립니다.**
            
            !스크린샷 2026-06-24 오후 6.36.04.png
            
        - 해당 토큰이 앞에 붙고, 다시 도  ***O($L^2$ D)*** 계산을 반복!
            
            !스크린샷 2026-06-24 오후 6.38.20.png
            
        - 결국 계산 부담은 ***f((L+2$)^2$)*** 제곱으로 늘어나게 됨!
            
            !image.png
            
            !image.png
            
    - **정확히 무엇을 caching 하는지**
        
        !https://vllm.ai/blog/2026-06-03-deeplearning-ai-vllm-course
        
        https://vllm.ai/blog/2026-06-03-deeplearning-ai-vllm-course
        
        - 무엇을 저장하는지 알아보자!
            
            !image.png
            
        - 맨 처음 LLM 다음 토큰 생성은, 앞과 동일하게 계산합니다.
        - 그런데, 여기서 이 k, v sequence 를 저장합니다.
            
            !스크린샷 2026-06-24 오후 6.42.36.png
            
        - 그 다음 attention 계산을 똑같이 함.
            
            !image.png
            
        - LLM 출력 sequence 의 맨 마지막을 써서, 다음 토큰을 구합니다. ***+ KV Cache 에 K, V sequence 가 저장되어 있음!***
            
            !image.png
            
        - KV Cache 가 무엇을 저장하나? **key, value sequence 저장**
            
            
    - **어떤 중복 계산을 피하는지, 어떻게 부담을 경감?**
        - self attention 의 입력부터 바뀜!
        - **q, k, v weight 의 sequence 가 입력되는게 아니라, sequence 의 맨 마지막 샘플만 들어갑니다!**
            
            !image.png
            
        - 그럼 q,k,v weight 를 통과한 결과도 sequence 의 마지막 샘플 정보 하나만 있음 + k 와 v는
            
            !image.png
            
        - **k 와 v 에는 직전 LLM 생성에서 저장해둔 k 와 v 를 앞에 붙임!**
            
            !스크린샷 2026-06-24 오후 6.49.17.png
            
        - 다음을 위해 kv cache 에 이번에 계산한 샘플 값을 추가합니다.
            
            !스크린샷 2026-06-24 오후 6.51.59.png
            
        - q 는 마지막 샘플 정보 뿐이지만, **K와V는 전체 sequence 정보를 다 활용하는 셈이다!**
            
            !image.png
            
        - 단일 샘플 query 만으로 attention 계산 결과는 주입된 단일 query에 대해서, key 내적으로 가중치를 구하고,
            
            !image.png
            
            !스크린샷 2026-06-24 오후 6.55.08.png
            
            - 가중치로 values 랑 weighted sum 해서, **attention 의 결과가 됩니다.**
            
            !image.png
            
        - query 는 sequence 내에서 서로 의존성 없이 병렬적으로 처리된다.
            
            !image.png
            
        - **그래서 query sample 마지막만 있고, sequence 안에 다른 샘플이 없더라도, attention 계산 결과는 같습니다!**
            
            
        - 그리고 어차피 LLM 출력에서, 맨 마지막 샘플로만 다음 토큰을 구하니까요.
        - 버려지는 것들은 제외하고, **필요한 맨 마지막 샘플로만 계산하겠다는 전략**입니다.
            
            !image.png
            
        - **key, value**는 softmax 와 weighted sum 으로, sequence 내에서 길이 축에 서로 의존성이 있기 때문에, **전체 length 가 필요합니다.**
            
            !image.png
            
        - 하지만 key, value sequence 는 직전에 이미 계산된 적이 있어서, 저장해놨다가 다시 쓸 수 있음!
            
            !image.png
            
            !image.png
            
    - **가능하게 된 3요소 ⇒ self attention 에 마지막 단일 샘플 입력으로만 LLM에서 다음 토큰을 생성할 수 있습니다!**
        - query 는 이전 샘플 의존성 X
        - LLM 출력은 맨 마지막 샘플만 씀
        - key, value 는 전체 시퀀스 필요 → KV[:-1]은 **직접 계산의 KV(kv cache)** 쓰면 됨
    - **kv cache 사용 시, 계산 복잡도**
        - 한 query 에서만 L 길이의 key 계산, 즉 D dimension 의 내적을 L 번 하기 때문에  ***O(LD) 의 계산 복잡도를 가짐!***
            
            !image.png
            
            !image.png
            
            !https://www.youtube.com/watch?v=HmWQhBjbtLE
            
            https://www.youtube.com/watch?v=HmWQhBjbtLE
            
        
    - **KV Cache 를 위한 GPU 메모리 공간 확보 필요!**
        
        !Figure 5-10. GPU memory usage breakdown
        
        Figure 5-10. GPU memory usage breakdown
        
        !image.png
        
        !image.png
        
        !image.png
        
    
- [[기초부터 이해하는 GPU Network] 1. GPU Interconnect Bandwidth](https://app.notion.com/p/GPU-Network-1-GPU-Interconnect-Bandwidth-38750aec5edf80428383e33957b728cf?pvs=21)
- **[실습3] KV Cache로 성능 개선**
    - KV 캐시 방식: 이전 레이어별 Key/Value를 저장해두고 재사용, **새 토큰에 대해서만 증분(incremental) 계산**
        - 메모리를 더 쓰는 대신 연산량을 크게 절약하는 트레이드오프
    
    !Figure 2-10. KV cache를 사용하면 이전 key/value를 재사용해 중복 계산을 줄인다
    
    Figure 2-10. KV cache를 사용하면 이전 key/value를 재사용해 중복 계산을 줄인다
    
    - KV cache는 이전 token들에 대해 계산한 key/value를 저장해두고 다음 decode step에서 재사용한다.
    - 그러면 새 token을 생성할 때 전체 sequence를 다시 계산하지 않고 새 token 중심으로만 처리할 수 있다.
    - 아래 예제는 `past_key_values`를 유지하면서 새 token만 다음 step의 입력으로 넣는다.
        
        ```python
        # (1) Define key/value cache for faster generation
        past_key_values = None
        
        for _ in range(num_interations):
           print("input_ids size: " + str(input_ids.size()))
           with torch.no_grad():
               outputs = model(input_ids=input_ids,
                 # (2) Use KV-cache from previous iteration
                 **past_key_values=past_key_values**,           # 이전 스텝의 KV 캐시
                 # (2) Enable KV caching
                 use_cache=True,                            # 캐시 사용/생성 활성화
                 max_new_tokens = 100,
                 min_new_tokens= 100)
        
               logits = outputs.logits
               # (3) Update KV Cache
               **past_key_values = outputs.past_key_values**    # 모델이 새 토큰을 처리하면서 계산한 Key/Value를 기존 캐시에 이어붙여 다음 스텝에 전달
               torch.cuda.synchronize()
        
           logits = logits[:, -1, :]
           probas = torch.softmax(logits, dim=-1)
           generated_token_id = torch.multinomial(probas, num_samples=1)
          
           # (4) Update input_ids with only the new token (using KV-cache)
           # Note: Not concatenating with previous tokens due to KV-cache
           **input_ids = generated_token_id**  
           idx = torch.cat((idx, generated_token_id), dim=1)
        
           if generated_token_id.item() == tokenizer.eos_token_id:
               print("\n[Generation completed - EOS token reached]")
               break
        ```
        
        1. **입력이 달라짐**
            - 기존: idx_cond = idx (전체 시퀀스를 매번 통째로 입력)
            - **캐시 사용 시**: input_ids = generated_token_id (방금 생성한 토큰 하나만 입력)
        2. **모델 호출 시 캐시를 함께 전달**
            - past_key_values=past_key_values, # 이전 스텝의 KV 캐시
            - use_cache=True                                 # 캐시 사용/생성 활성화
        3. **매 스텝마다 캐시를 갱신**
            - past_key_values = outputs.past_key_values # 모델이 새 토큰을 처리하면서 계산한 Key/Value를 기존 캐시에 이어붙여 다음 스텝에 전달
    - **실측 성능 비교 : 아래 책 결과 기준 설명**
        
        ![[책 결과 기준] KV cache 사용 전후 token generation time 비교](attachment:73af6285-a0ac-4152-9f4b-6ec799b6c15c:image.png)
        
        [책 결과 기준] KV cache 사용 전후 token generation time 비교
        
        - 캐시 없음(Example 2-1): 100토큰 생성에 9.12초, 토큰이 늘어날수록 점점 느려짐 (매번 늘어난 시퀀스 전체를 재처리하기 때문)
        - KV 캐시 사용(Example 2-2): 100토큰 생성에 3.14초 — 약 3배 가까이 빠름, 첫 토큰 이후로는 생성 속도가 안정적으로 유지됨
        
        !image.png
        
    - **의미**
        - 이 실습은 KV 캐시가 LLM 생성의 지연시간(latency)과 처리량(throughput) 모두에 얼마나 큰 영향을 미치는지 직접 눈으로 보여줍니다.
        - 이는 이후 다룰 vLLM의 Paged Attention, SGLang의 Radix Attention 같은 고급 KV 캐시 최적화 기법들을 이해하는 기초가 되며, 6장·7장(성능 튜닝)에서 더 깊이 다룰 예정입니다.
        - KV cache는 decode 단계의 반복 계산을 크게 줄이지만, cache 자체가 GPU memory를 사용한다.
        - 따라서 **serving에서는 KV cache memory 관리가 throughput, latency, concurrency를 결정하는 핵심 요소**가 된다.
        
    - (참고) KV 캐시는 추론에서만 사용됨. 훈련 단계에서는 모든 정보가 필요하여 사용할 수 없음
        
        !https://www.youtube.com/watch?v=_PAfSUr6k2o 어텐션 비용 비교: 훈련 vs 추론 vs 추론 시 KV cache 사용시
        
        https://www.youtube.com/watch?v=_PAfSUr6k2o 어텐션 비용 비교: 훈련 vs 추론 vs 추론 시 KV cache 사용시
        
- **[딥러닝 큐레이터 임커밋] LLM - prefill 설명** : KV 캐시 설명 포함 - Youtube
- LLM inference **prefill +** **decode**(반복)
    - **Prefill**
        - **입력 prompt 전체를 한 번에 처리**해 internal state와 **KV cache**를 만든다.
        - **prompt가 길수록 prefill 비용이 커진다.**
        - **병렬화**가 비교적 잘 되기 때문에 **GPU compute를 많이 쓰는 경향**이 있다.
        
    - **Decode**
        
        !Figure I-3. LLM processing steps "What is the highest mountain on Earth?"라는 입력에서 prefill 이후 decode가 `Mount`, `Everest`, `<EOS>`를 순차 생성하는 과정을 보여준다.
        
        Figure I-3. LLM processing steps "What is the highest mountain on Earth?"라는 입력에서 prefill 이후 decode가 `Mount`, `Everest`, `<EOS>`를 순차 생성하는 과정을 보여준다.
        
        - 모델이 **output token을 하나씩 생성**하는 단계다.
        - 새로 생성된 token은 다시 **다음 token 생성을 위한 context에 포함된**다.
        - decode는 sequential dependency가 강하고, **KV cache를 계속 읽고 쓰기** 때문에 **memory bandwidth 병목이 중요**해진다.
        - token throughput, Time To First Token(TTFT), KV cache utilization 같은 지표가 운영 관측의 핵심이 된다.
    
    - LLM workload는 상황에 따라 compute-bound 또는 memory-bound로 달라진다.
        
        !Figure I-4. Compute-bound and memory-bound resource utilization compute-bound에서는 processor 활용률이 높고 memory bandwidth가 상대적으로 낮으며, memory-bound에서는 memory bandwidth가 포화되어 processor가 완전히 활용되지 못하는 구조를 보여준다.
        
        Figure I-4. Compute-bound and memory-bound resource utilization compute-bound에서는 processor 활용률이 높고 memory bandwidth가 상대적으로 낮으며, memory-bound에서는 memory bandwidth가 포화되어 processor가 완전히 활용되지 못하는 구조를 보여준다.
        
        ```mermaid
        flowchart LR
            A["Prefill"] --> B["Compute-bound"]
            B --> C["GPU 연산 성능 중요"]
        
            D["Decode"] --> E["Memory-bound"]
            E --> F["HBM bandwidth / KV Cache 관리 중요"]
        ```
        
    - **Compute-bound**: GPU 연산 유닛이 병목이다. **prefill**처럼 대량의 행렬 연산을 병렬 처리하는 구간에서 나타나기 쉽다.
    - **Memory-bound**: GPU memory bandwidth가 병목이다. **decode**처럼 KV cache를 반복 접근하는 구간에서 나타나기 쉽다.
        - Decode 단계에서는 매번 이전 sequence 전체를 참조해야 합니다. 이를 매번 처음부터 계산하면 매우 비효율적입니다.그래서 LLM runtime은 **KV Cache**를 사용합니다.
            
            ```bash
            K = Key
            V = Value
            KV Cache = 이전 token들의 attention 계산 결과를 저장한 cache
            ```
            
        - KV Cache는 계산을 줄여주지만, 문제를 다른 쪽으로 옮깁니다.
            
            ```bash
            계산 병목 감소
            → 메모리 저장/조회 병목 증가
            ```
            
        - KV cache 때문에 decode 단계가 memory-bound가 된다고 설명합니다. 또한 출력 길이를 미리 알 수 없기 때문에 KV cache 크기를 정확히 예측하기 어렵고, 이를 해결하기 위해 PagedAttention 같은 기법이 등장했다
        - GPU utilization이 낮다고 해서 항상 GPU가 부족하지 않은 것은 아니다. memory bandwidth가 병목이면 연산 유닛이 남아도 전체 성능은 제한된다.
    
- **Prefill-decode disaggregation 혹은 Disaggregated Serving - Handbook , vLLM , SGLang , Dynamo , llm-d**
    - LLM 추론의 두 가지 주요 단계인 사전 채우기와 디코딩을 서로 다른 하드웨어 리소스에서 실행하는 서비스 아키텍처
        - 각 단계에 서로 다른 컴퓨팅 및 메모리 요구 사항에 맞는 전용 리소스를 제공하는 것
        
        !image.png
        
    - **프리필과 디코드를 같은 위치에 배치할 때 발생하는 문제점**
        - 실제로는 여러 요청이 동시에 들어오는 경우가 많습니다. 각 요청에는 고유한 사전 채우기 및 디코딩 요구 사항이 있지만, 한 번에 하나의 단계만 실행될 수 있습니다. GPU가 연산 집약적인 사전 채우기 작업에 바쁘면 디코딩 작업은 대기해야 하므로 ITL이 증가하고, 반대의 경우도 마찬가지입니다.
        - 프리필은 주로 TTFT를 결정하고 디코딩은 ITL에 영향을 미치기 때문에, 이들을 **같은 위치에 배치하면 두 지표를 동시에 최적화하기 어렵습니다**.
        - **프리필과 디코딩을 같은 위치에 배치하면 지연 시간이 증가**합니다. (이미지 출처)
            
            !image.png
            
        
    - **아키텍처**
        
        !image.png
        
        - **전용 리소스 할당**
            - 사전 채우기 및 디코딩은 서로 다른 하드웨어에서 독립적으로 예약 및 확장할 수 있습니다.
            - 예를 들어, 워크로드에 프롬프트 중복이 많은 경우(예: 다중 턴 대화 또는 에이전트 워크플로) 키 값 캐시의 상당 부분을 재사용할 수 있습니다.
            - 결과적으로 사전 채우기에 필요한 컴퓨팅 요구량이 줄어들고 디코딩에 더 많은 리소스를 할당할 수 있습니다.
        - **병렬 실행**
            - 사전 채우기(prefill) 및 디코딩 단계가 더 이상 서로 간섭하지 않습니다.
            - 병렬로 실행하면 더욱 효율적으로 작동하여 동시성과 처리량이 향상됩니다.
            - 또한, 이러한 분리는 테일 레이턴시(tail latency)를 개선할 수 있습니다.
            - 기존 방식에서는 단일 사전 채우기 작업으로 인해 뒤에 있는 모든 디코딩 요청이 지연되어 P95 및 P99 레이턴시가 증가할 수 있었습니다.
        - **독립적인 튜닝**
            - TTFT 및 ITL 목표를 더 잘 충족하기 위해 사전 채우기 및 디코딩에 대해 다양한 최적화 기법(예: 텐서 병렬 처리 또는 파이프라인 병렬 처리)을 구현할 수 있습니다.
        
    - **P/D 분해가 항상 만능 해결책은 아닙니다 : 생략..**
    
- **The Prefill and Decode Phases**
    - LLM 서빙 분야에서 자주 언급되는 두 핵심 개념입니다. 성능 최적화와 확장성을 논할 때 필수적인 구분입니다.
        
        !Figure 2-12. LLM text generation의 prefill phase와 decode phase
        
        Figure 2-12. LLM text generation의 prefill phase와 decode phase
        
    - Prefill 단계 (프롬프트 처리) : prompt 전체를 한 번 처리해 첫 token을 만들고, 이후 decode에 쓸 KV cache를 채운다.
        - 사용자가 입력한 프롬프트 전체를 한 번에 처리하는 단계
        - 프롬프트의 모든 토큰에 대해 어텐션을 계산하므로 연산 집약적(compute-intensive) : 시퀀스 길이에 대해 2차(quadratic) 복잡도
        - 예: "Write a short introduction about the US capital city."라는 프롬프트를 받으면, 이 모든 토큰을 동시에(병렬로) 처리
    - Decode 단계 (토큰 단위 생성) : 생성된 token을 하나씩 처리하면서 다음 token을 반복 생성한다.
        - Prefill이 끝난 후, 토큰을 하나씩 생성하며 이 과정을 반복
        - 시퀀스는 계속 길어지지만, (KV 캐시 덕분에) 어텐션 계산은 보통 가장 최근 토큰에만 집중
        
    - **실측 비교** (그림 2-13, KV 캐시 사용 시) ← 이전 KV Cache 비교 실습
        
        !Figure 2-13. KV cache가 켜진 예제에서 prefill/decode phase의 token generation tim
        
        Figure 2-13. KV cache가 켜진 예제에서 prefill/decode phase의 token generation tim
        
        - 첫 번째 막대(=첫 토큰 생성 시간)가 **Prefill 단계**에 해당하며, 나머지에 비해 **압도적으로 오래 걸림** → 프롬프트 전체를 한 번에 처리해야 하기 때문
        - 이후 막대들(**Decode 단계**)은 짧고 일정한 시간을 보임 → **캐시된 정보를 활용해 새 토큰 하나만 처리**하기 때문
        
    - 왜 이 구분이 중요한가
        - Prefill = **연산 집약적**: 여러 프롬프트 **토큰을 병렬 처리하는 데서 오는 부담**
        - Decode = **메모리 집약적**: 모델 가중치를 반복적으로 로드해야 하고, KV 캐시 크기가 계속 커지는 데서 오는 부담
        
    - 즉 병목이 어느 단계에서 발생하는지에 따라 최적화 전략이 완전히 달라집니다.
    - 실무 시나리오 예시:
        - **긴 프롬프트** (예: 500페이지 이상 PDF 처리): **Prefill이 병목** → 프롬프트 처리 속도 최적화가 중요
        - **짧은 프롬프트 + 긴 생성** (예: 챗봇 응답, 스토리 생성): **Decode가 병목** → 토큰 생성 속도·메모리 관리가 중요
        
    - 지금까지는 모델을 직접 로드하고 토큰을 한 단계씩 생성하는 "밑바닥부터 구현하는 추론(from-scratch inference)" 방식을 실습했습니다.
    - 이는 LLM 내부 동작을 이해하는 데는 매우 유용하지만, 실제 프로덕션에서는 커스텀 파이프라인 대신 서빙 프레임워크를 사용하는 것이 일반적입니다.
    - 이후 절에서는 vLLM 서빙 프레임워크를 활용해 프로덕션 수준의 라이브러리로 LLM 추론을 실행하는 방법을 살펴봅니다.
    
- `도전과제` gpt 의 미니멀한 구현체를 python builtin function 만으로 구성한 구현체 따라해보기 - Blog, Code, Colab
- `도전과제` KV Cache, Prefill+Decode, P/D Disaggregation 학습 후 정리 해보기 + vLLM/SGLang 에서 실습 해보기

- 서빙 프레임워크로 LLM 실행 개요
    - 서빙 프레임워크란
        - **vLLM, SGLang** 같은 **모델 서빙 프레임워크**는 사전학습된 언어 모델을 로드해서 API(주로 REST 또는 gRPC)로 노출시켜, **실시간 또는 배치 추론을 처리하도록 설계된 전용 시스**템입니다.
        - 학습 프레임워크(PyTorch, TensorFlow): 모델 개발과 gradient 기반 학습에 초점
        - 서빙 프레임워크: 효율적이고, 확장 가능하며, 지연시간이 낮은 추론에 최적화
    - 서빙 프레임워크가 제공하는 **핵심 기능** : 단순히 추론을 실행하는 것 이상으로, 다음과 같은 필수 기능들을 제공합니다.
        - **KV 캐시 재사용을 통한 효율적인 디코딩** (앞서 직접 구현해본 개념이 프레임워크 내부에 최적화되어 내장됨)
        - **요청 스케줄링** (배치/마이크로배치 처리)
        - **다중 사용자 동시 처리**(concurrency) 지원
        - 토큰 스트리밍, 요청 취소·중단 처리
    - 왜 직접 구현하지 않고 **프레임워크를 쓰는가**
        - vLLM 같은 잘 설계된 서빙 프레임워크는 Paged Attention, Speculative Decoding 같은 최신 연구 성과를 지속적으로 통합하면서도, 저수준 인프라 문제는 추상화해서 감춰줍니다.
        - 덕분에 개발자는 모델 아키텍처마다 추론 로직을 다시 구현하거나 최신 논문을 일일이 쫓아다닐 필요 없이, 애플리케이션 개발 자체에 집중할 수 있습니다.
    - 이 절에서 할 일
    이제 vLLM을 사용해 LLM을 로드하고 서빙하는 방법을 실습합니다.
    - 앞 절에서 직접 구현했던 수동 추론 방식(토크나이징 → 반복 루프 → KV 캐시 직접 관리)과 비교하면서, 서빙 프레임워크를 사용했을 때의 실질적인 이점을 체감할 수 있습니다.
    
- https://github.com/orca3/llm-model-inference/blob/main/ch02/ch2_Run_LLM_With_vLLM.ipynb : **Serve the LLM (Qwen) with vLLM** by 구글 Colab
    - TS : vllm 버전 호환성 → 런타임 유형 변경(2025.07)
        
        ```python
        # 현재 환경의 CUDA 버전 확인
        import torch; print(torch.version.cuda)
        **12.8**
        ```
        
        !image.png
        
        ```python
        **# [6분] 5분 설치 -> 세션 재시작
        !pip install vllm==0.6.6.post1
        !pip install transformers**
        ```
        
    - **[2분]** vLLM은 LLM serving에 특화된 프레임워크로, PagedAttention, continuous batching, KV cache 관리 등을 제공한다.
        
        ```python
        import time
        from vllm import LLM, SamplingParams
        
        model_name = "Qwen/Qwen2.5-0.5B"
        
        # Load model with vLLM : vLLM 엔진을 초기화하며 모델을 로드.
        llm = LLM(model=model_name, dtype="float16")  # 가중치를 16비트로 로드해 메모리 절약
        
        # Define the prompt.
        prompt = """You are an expert AI historian writing a 
        detailed chapter for a book titled "The Evolution of 
        Human-AI Collaboration." … … Write in a formal tone, 
        with rich detail and examples in each era."""
        
        # Create inference parameters.
        inference_params = SamplingParams(temperature=0.8, top_p=0.95, max_tokens=128)
        
        # Run token (text) generation with prompt and inference parameters.
        **outputs = llm.generate**([prompt], inference_params)
        
        # Print the results.
        for output in outputs:
         print(f"Generated text: {output}")
        ```
        
        ```python
        /usr/local/lib/python3.11/dist-packages/huggingface_hub/utils/_auth.py:94: UserWarning: 
        The secret `HF_TOKEN` does not exist in your Colab secrets.
        To authenticate with the Hugging Face Hub, create a token in your settings tab (https://huggingface.co/settings/tokens), set it as secret in your Google Colab and restart your session.
        You will be able to reuse this secret in all of your notebooks.
        Please note that authentication is recommended but still optional to access public models or datasets.
          warnings.warn(
        config.json: 100%
         681/681 [00:00<00:00, 63.9kB/s]
        WARNING 08-01 22:08:49 config.py:2276] Casting torch.bfloat16 to torch.float16.
        INFO 08-01 22:09:04 config.py:510] This model supports multiple tasks: {'score', 'reward', 'generate', 'embed', 'classify'}. Defaulting to 'generate'.
        INFO 08-01 22:09:04 llm_engine.py:234] Initializing an LLM engine (v0.6.6.post1) with config: model='Qwen/Qwen2.5-0.5B', speculative_config=None, tokenizer='Qwen/Qwen2.5-0.5B', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, override_neuron_config=None, tokenizer_revision=None, trust_remote_code=False, dtype=torch.float16, max_seq_len=32768, download_dir=None, load_format=LoadFormat.AUTO, tensor_parallel_size=1, pipeline_parallel_size=1, disable_custom_all_reduce=False, quantization=None, enforce_eager=False, kv_cache_dtype=auto, quantization_param_path=None, device_config=cuda, decoding_config=DecodingConfig(guided_decoding_backend='xgrammar'), observability_config=ObservabilityConfig(otlp_traces_endpoint=None, collect_model_forward_time=False, collect_model_execute_time=False), seed=0, served_model_name=Qwen/Qwen2.5-0.5B, num_scheduler_steps=1, multi_step_stream_outputs=True, enable_prefix_caching=False, chunked_prefill_enabled=False, use_async_output_proc=True, disable_mm_preprocessor_cache=False, mm_processor_kwargs=None, pooler_config=None, compilation_config={"splitting_ops":["vllm.unified_attention","vllm.unified_attention_with_output"],"candidate_compile_sizes":[],"compile_sizes":[],"capture_sizes":[256,248,240,232,224,216,208,200,192,184,176,168,160,152,144,136,128,120,112,104,96,88,80,72,64,56,48,40,32,24,16,8,4,2,1],"max_capture_size":256}, use_cached_outputs=False, 
        tokenizer_config.json: 
         7.23k/? [00:00<00:00, 625kB/s]
        vocab.json: 
         2.78M/? [00:00<00:00, 64.0MB/s]
        merges.txt: 
         1.67M/? [00:00<00:00, 56.0MB/s]
        tokenizer.json: 
         7.03M/? [00:00<00:00, 108MB/s]
        generation_config.json: 100%
         138/138 [00:00<00:00, 12.4kB/s]
        INFO 08-01 22:09:09 selector.py:217] Cannot use FlashAttention-2 backend for Volta and Turing GPUs.
        INFO 08-01 22:09:09 selector.py:129] Using XFormers backend.
        INFO 08-01 22:09:10 model_runner.py:1094] Starting to load model Qwen/Qwen2.5-0.5B...
        INFO 08-01 22:09:11 weight_utils.py:251] Using model weights format ['*.safetensors']
        model.safetensors: 100%
         988M/988M [00:11<00:00, 127MB/s]
        INFO 08-01 22:09:23 weight_utils.py:296] No model.safetensors.index.json found in remote.
        Loading safetensors checkpoint shards: 100% Completed | 1/1 [00:01<00:00,  1.02s/it]
        INFO 08-01 22:09:25 model_runner.py:1099] Loading model weights took 0.9276 GB
        INFO 08-01 22:09:27 worker.py:241] Memory profiling takes 1.94 seconds
        INFO 08-01 22:09:27 worker.py:241] the current vLLM instance can use total_gpu_memory (14.56GiB) x gpu_memory_utilization (0.90) = 13.11GiB
        INFO 08-01 22:09:27 worker.py:241] model weights take 0.93GiB; non_torch_memory takes 0.11GiB; PyTorch activation peak memory takes 1.44GiB; the rest of the memory reserved for KV Cache is 10.63GiB.
        INFO 08-01 22:09:27 gpu_executor.py:76] # GPU blocks: 58059, # CPU blocks: 21845
        INFO 08-01 22:09:27 gpu_executor.py:80] Maximum concurrency for 32768 tokens per request: 28.35x
        INFO 08-01 22:09:33 model_runner.py:1415] Capturing cudagraphs for decoding. This may lead to unexpected consequences if the model is not static. To run the model in eager mode, set 'enforce_eager=True' or use '--enforce-eager' in the CLI. If out-of-memory error occurs during cudagraph capture, consider decreasing `gpu_memory_utilization` or switching to eager mode. You can also reduce the `max_num_seqs` as needed to decrease memory usage.
        Capturing CUDA graph shapes: 100%|██████████| 35/35 [00:36<00:00,  1.05s/it]INFO 08-01 22:10:10 model_runner.py:1535] Graph capturing finished in 37 secs, took 0.13 GiB
        
        INFO 08-01 22:10:10 llm_engine.py:431] init engine (profile, create kv cache, warmup model) took 45.60 seconds
        Processed prompts: 100%|██████████| 1/1 [00:01<00:00,  1.76s/it, est. speed input: 80.85 toks/s, output: 72.88 toks/s]
        **Generated text**: RequestOutput(request_id=0, prompt='You are an expert AI historian writing a detailed chapter for a book titled "The Evolution of Human-AI Collaboration."\n\nBegin by summarizing the early stages of artificial intelligence in the 1950s, touching on symbolic logic and rule-based systems. Then transition into the rise of machine learning, particularly deep learning in the 2010s.\n\nAfterward, describe how large language models like GPT transformed human-computer interaction, enabling applications in education, creative writing, customer support, and software development.\n\nFinally, reflect on the societal and ethical implications of AI, such as misinformation, bias, and the alignment problem.\n\nWrite in a formal tone, with rich detail and examples in each era.', prompt_token_ids=[2610, 525, 458, 6203, 15235, 42968, 4378, 264, 11682, 12453, 369, 264, 2311, 24849, 330, 785, 37221, 315, 11097, 6691, 40, 86587, 2217, 11135, 553, 28285, 4849, 279, 4124, 17628, 315, 20443, 11229, 304, 279, 220, 16, 24, 20, 15, 82, 11, 30587, 389, 35296, 12218, 323, 5912, 5980, 5942, 13, 5005, 9142, 1119, 279, 10000, 315, 5662, 6832, 11, 7945, 5538, 6832, 304, 279, 220, 17, 15, 16, 15, 82, 382, 6025, 1606, 11, 7512, 1246, 3460, 4128, 4119, 1075, 479, 2828, 23507, 3738, 11476, 11281, 16230, 11, 27362, 8357, 304, 6731, 11, 11521, 4378, 11, 6002, 1824, 11, 323, 3162, 4401, 382, 23949, 11, 8708, 389, 279, 58429, 323, 30208, 24154, 315, 15235, 11, 1741, 438, 74059, 11, 15470, 11, 323, 279, 17189, 3491, 382, 7985, 304, 264, 15908, 16232, 11, 448, 9080, 7716, 323, 10295, 304, 1817, 11385, 13], encoder_prompt=None, encoder_prompt_token_ids=None, prompt_logprobs=None, outputs=[CompletionOutput(index=0, text=" Avoid slang, jargon, and complex language. Create a sense of historical context to engage readers and maintain coherence in your narrative. Title: The Evolution of Human-AI Collaboration\n\nThe early stages of artificial intelligence (AI) in the 1950s were marked by the development of symbolic logic and rule-based systems. In the 1960s, these technologies were extended by the creation of artificial neural networks, which were inspired by the brain's structural organization.\n\nSymbolic logic and rule-based systems were the foundation of AI research in the 1950s. These systems were used to represent patterns and rules", token_ids=(34006, 79912, 11, 502, 70821, 11, 323, 6351, 4128, 13, 4230, 264, 5530, 315, 13656, 2266, 311, 16579, 12726, 323, 10306, 77825, 304, 697, 19221, 13, 10869, 25, 576, 37221, 315, 11097, 6691, 40, 86587, 271, 785, 4124, 17628, 315, 20443, 11229, 320, 15469, 8, 304, 279, 220, 16, 24, 20, 15, 82, 1033, 12864, 553, 279, 4401, 315, 35296, 12218, 323, 5912, 5980, 5942, 13, 758, 279, 220, 16, 24, 21, 15, 82, 11, 1493, 14310, 1033, 11577, 553, 279, 9688, 315, 20443, 29728, 14155, 11, 892, 1033, 14606, 553, 279, 8109, 594, 23759, 7321, 382, 15090, 292, 12218, 323, 5912, 5980, 5942, 1033, 279, 16266, 315, 15235, 3412, 304, 279, 220, 16, 24, 20, 15, 82, 13, 4220, 5942, 1033, 1483, 311, 4009, 12624, 323, 5601), cumulative_logprob=None, logprobs=None, finish_reason=length, stop_reason=None)], finished=True, metrics=RequestMetrics(arrival_time=1785622213.1038754, last_token_time=1785622213.1038754, first_scheduled_time=1785622213.1646004, first_token_time=1785622213.669608, time_in_queue=0.06072497367858887, finished_time=1785622214.9134955, scheduler_time=0.01973968800189141, model_forward_time=None, model_execute_time=None), lora_request=None, num_cached_tokens=0, multi_modal_placeholders={})
        **Time taken: 1.82 second**s
        ```
        
        - 보시다시피, **LLM()과 generate() 함**수는 복잡한 부분을 많이 **추상화해 LLM을 빠르게 실험할** 수 있게 해줍니다.
        - 단순함에도 불구하고, vLLM은 성능과 동작을 세밀하게 조정할 수 있는 다양한 설정 옵션을 제공해 특정 애플리케이션 요구에 맞출 수 있습니다.
        - 좀 더 고급 설정을 적용한 예시: model loading, PagedAttention, KV cache, chunked prefill, CUDA graph, sampling parameter
            
            ```python
            # Configure Model Loading
            model = LLM(
               model="Qwen/Qwen-7B",
               # Memory management
               swap_space=16,  # CPU swap space size in GB
               max_model_len=4096,  # Maximum model length
               # PagedAttention settings
               block_size=16,  # Block size for PagedAttention
               enable_prefix_caching=True,  # Enable prefix caching
               # KV cache management
               max_num_sequences=256,  # Maximum number of sequences
               max_sequence_length=4096,  # Maximum sequence length
               # Performance optimizations
               enable_chunked_prefill=True,  # Enable chunked prefill
               enable_cuda_graph=True,  # Enable CUDA graph
               # System settings
               worker_use_ray=False,  # Use Ray for distributed serving
               disable_custom_all_reduce=False,  # Disable custom all-reduce
            )
            
            # Configure Model Inference Parameters
            sampling_params = SamplingParams(
               temperature=0.7,  # Controls randomness (0.0 = deterministic)
               top_p=0.9,  # Nucleus sampling parameter
               top_k=50,  # Top-k sampling parameter
               max_tokens=100,  # Maximum tokens to generate
               stop=["\n", "###"],  # Stop sequences
               frequency_penalty=0.1,  # Frequency penalty
               presence_penalty=0.1,  # Presence penalty
               repetition_penalty=1.1,  # Repetition penalty
               skip_special_tokens=True,  # Skip special tokens in output
            )
            ```
            
        
    - **Performance Comparison: vLLM Versus Hugging Face Transformers**
        - Run Qwen model with standard (non-optimial) **HuggingFace library** and track the inference time.
        - Hugging Face pipeline은 개발과 실험에 편리하지만, serving 최적화 기능은 vLLM 같은 전용 프레임워크가 더 강하다.
        
        !세션 다시 시작 후, HF쪽만 실행해보자
        
        세션 다시 시작 후, HF쪽만 실행해보자
        
        ```python
        # Run model inference with Hugging Face library
        # Load model and tokenizer in Hugging Face library   
        tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-0.5B",
            trust_remote_code=True,
        )
        
        # **HF 표준 방식으**로 토크나이저와 모델을 로드. device_map="auto"는 사용 가능한 GPU/CPU에 자동으로 레이어를 배치.
        model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-0.5B",
            device_map="auto",
            trust_remote_code=True,
        )
        
        start_time_basic = time.time()
        
        # **HF의 고수준 pipeline API로 텍스트 생성**. 내부적으로는 model.generate()를 호출하는 래퍼.
        # Create the model prediction pipeline
        generator = pipeline('text-generation', model=model, tokenizer=tokenizer)
        # Generate prediction with prompt
        outputs_basic = generator(prompt, max_length=128, temperature=0.8, top_p=0.95)
        end_time_basic = time.time()
        ```
        
    - **왜 vLLM이 17배(1.12s vs 19.58s) 빠른가?** : 책 실습 결과 데이터 기반 설명
        - 같은 GPU, 같은 모델, 같은 프롬프트인데도 차이가 나는 건 추론 엔진 구조 자체가 다르기 때문입니다:
        1. **PagedAttention**: vLLM은 KV 캐시를 페이지 단위로 관리해 메모리 낭비 없이 효율적으로 재사용. HF generate()는 시퀀스마다 연속된 메모리를 통째로 할당해 비효율적.
        2. **CUDA Graph 캡처**: 앞서 로그에서 봤듯 vLLM은 초기화 시점에 실행 그래프를 미리 캡처(Capturing CUDA graphs)해서 커널 실행 오버헤드를 없앰. HF generate()는 매 토큰마다 Python 레벨에서 순수 eager 모드로 순회.
        3. **최적화된 커널**: **FlashAttention** 등 저수준 커널을 직접 사용(로그의 Using FlashAttention version 2). HF도 SDPA/FlashAttention을 쓸 수 있지만 기본 pipeline()은 튜닝 안 된 설정으로 도는 경우가 많음.
        4. **pipeline() 자체의 오버헤드**: 전/후처리, 텐서 변환 등 편의성 레이어가 매 호출마다 추가 비용 발생.
        5. **연속 배칭(continuous batching)** : 이 예시는 단일 프롬프트라 체감이 적지만, 동시 요청이 늘어날수록 vLLM은 요청을 동적으로 배치에 끼워 넣어 GPU를 계속 바쁘게 유지하는 반면 HF는 요청 단위로 순차 처리되어 격차가 더 커짐 ("performance gap only widens" 부분이 이걸 의미).
        
    - **실무 접근 권장**
        - 단순하게 시작한 뒤 병목을 측정하며 최적화하는 것이다.
        - 처음부터 복잡한 분산 serving을 설계하기보다, 단일 모델/단일 GPU 또는 단일 노드에서 기준 성능을 측정하고 KV cache, batching, precision, parallelism을 단계적으로 조정한다
    
- **[딥러닝 큐레이터 임커밋] Flash attention의 원리**: HBM, SRAM 동작 설명 포함 - Youtube
    
    !Figure 6-12. FlashAttention의 SRAM 기반 QKV 계산과 fused FlashAttention 성능 개선
    
    Figure 6-12. FlashAttention의 SRAM 기반 QKV 계산과 fused FlashAttention 성능 개선
    
    !https://www.chooblog.xyz/blog/kernel-tensor_core
    
    https://www.chooblog.xyz/blog/kernel-tensor_core
    
    !https://huggingface.co/learn/llm-course/chapter2/8
    
    https://huggingface.co/learn/llm-course/chapter2/8
    
    - 일단 스샷만
        
        !image.png
        
        !스크린샷 2026-06-24 오후 11.39.46.png
        
        !image.png
        
    
- **[딥러닝 큐레이터 임커밋] PagedAttention**: Paging the KV Cache in vLLM - Youtube *→ 해당 영상에 Flash attention2,3,4 도 정리해볼 것!*
    
    !*Figure 6-13. PagedAttention을 사용하는 generation process의 한 단계.*
    
    *Figure 6-13. PagedAttention을 사용하는 generation process의 한 단계.*
    
    - 서비스 시스템은 응답시간이 얼마나 오래 걸릴지 미리 알 수 없으므로, 2023년 이전 시스템들은 안전한 방식을 택했음.
    - 각 요청에 대해, 해당 요청이 도달할 수 있는 가장 긴 시퀀스 크기에 맞는 HBM의 연속된 영역 하나를 예약했습니다.
        
        !image.png
        
    - 예를 들어 토큰 예약 제한이 4096개이고, 실제 사용이 200이라고 가정해보겠습니다.
    - 나머지 3896개는 요청이 완료될 때까지, 낭비가 발생합니다 = **내부 단편화라고 함**
        
        !image.png
        
    - **두번째 유형의 단편화 :** 길이가 다른 요청들로 **예약 사이의 여유 공간이 낭비**가 발생 ***⇒ 외부 단편화!***
    - 새로운 요청이 전체 빈 공간에 들어갈 수 있는 **연속된 빈 공간이 없을 수 있음!**
        
        !image.png
        
    - vLLM팀은 **KV cache 에 실제 사용량이 20% ~ 38.2%** 비중이었다고 함. ***⇒ 나머지는 낭비!***
        
        !image.png
        
    - 운영체제는 이미 수십 년 전에 이 문제를 해결했음. 해당 방법을 거의 그대로 적용했음.
        
        !image.png
        
    - 2023년에 발표된 **Paged Attention : 캐시를 16 or 32개 토큰으로 구성된 고정 크기 블록으로 나눔.**
        
        !image.png
        
    - 모든 요청에 블록 테이블을 제공함. 이 테이블은 논리적 블록을 물리적 블록 식별자에 매핑합니다.
        
        !image.png
        
    - **논리적으로 어텐션 커널은 테이블을 따라가며 하나의 연속된 시퀀스를 인식합니다.**
        
        !스크린샷 2026-06-25 오전 12.31.04.png
        
    - **이제 내부 단편화는 요청 당 최대 하나의 부분 블록으로 줄어듭니다.**
        
        !image.png
        
    - 그리고 **외부 단편화**는 크기가 동일하고 어떤 블록이든 사용할 수 있기 때문에 **완전히 사라집니다.**
    - 어텐션 커널은 여전히 동일한 함수를 계산합니다. 표를 따라 각 블록을 수집할 뿐입니다.
    - 새로운 점은 바이트가 저장되는 위치와 이를 찾기 위해 필요한 블록 테이블 간접 참조 방식입니다.
        
        !image.png
        
    - 이렇게 확보된 메모리는 곧바로 처리량 증가로 직결됩니다.
    - 이제 더 많은 동시 요청을 동일한 HBM에 저장할 수 있습니다 ⇒ 따라서, vLLM은 동일한 지연 시간에서 기존 서비스템보다 **2~4배 높은 처리량을 제공**합니다.
        
        !image.png
        
    - 블록 테이블은 또 다른 이점도 제공합니다.
    - 하나의 프롬프트에 대해 여러 후보 후속 답변을 동시에 탐색하는데, 이런한 전략을 빔 검색 beam search 이라고 합니다.
        
        !image.png
        
        - 두 경우 모두 테이블이 동일한 물리적 블록을 가리킬 수 있다.
        - 블록은 시퀀스가 분기되어 해당 블록에 기록될 때만 복사됩니다.
        
        !스크린샷 2026-06-25 오전 12.43.45.png
        
    - **빔 검색 시 공유되는 부분은 캐시의 최대 55%에 달함** ⇒ 절약된 메모리는 배치 크기에 직접적인 영향을 미칩니다.
    - 결과 : basic 1.3배, beam search 2.3배
        
        !image.png
        
    
- **PagedAttention 설명 추천** : vLLM의 놀라운 속도 비결, KV Prefix Sharing - Youtube , OS-메모리-소개(Page)
- (추천) GPU에서 Attention은 실제로 어떻게 실행되는가 : 커널 Launch부터 Tensor Core까지 (Feat. FlashAttention-2) - Blog
- `도전과제` ’Flash Attention, PagedAttention’ 등 vLLM과 SGLang 에서 제공되는 최적화 기능 정리 + 실습 해보기

### LLM Streaming Serving Basics

- **왜 스트리밍이 필요한가?**
    - 앞서 쓴 llm.generate([prompt], inference_params)는 동기(sync) + 블로킹(blocking) 방식입니다.
    - 모델이 내부적으로는 토큰을 한 개씩 순차 생성하지만(디코딩 단계의 autoregressive 특성), API 호출은 전체 출력이 완성될 때까지 기다렸다가 한 번에 반환합니다.
    - → 챗봇처럼 실시간 대화가 필요한 서비스에서는 사용자가 응답을 몇 초~몇 분간 못 보고 기다려야 해서 UX가 나빠짐.
    - 해결책 : 스트리밍 - 토큰이 생성되는 즉시 하나씩(또는 작은 청크 단위로) 클라이언트에 바로 전달하는 방식.
- https://github.com/orca3/llm-model-inference/blob/main/ch02/ch2_Streaming.ipynb :  by 구글 Colab
    - TS : vllm 버전 호환성 → 런타임 유형 변경(2025.07)
        
        ```python
        **# [6분] 5분 설치 -> 세션 재시작
        !pip install vllm==0.6.6.post1
        !pip install --quiet transformers tiktoken**
        ```
        
    - Let’s look at how to enable streaming generation with vLLM using a simple code example:
        
        ```python
        **# [2분]** Initialize the vLLM async streaming engine arguments
        engine_args = AsyncEngineArgs(
            model="Qwen/Qwen2.5-0.5B",
            dtype="float16",
            .. .. ..
        )
        
        # Create the vLLM async streaming engine
        engine = **AsyncLLMEngine**.from_engine_args(engine_args)
        
        # Define the async function to generate text in streaming mode
        **async def generate_text(prompt: str, max_tokens: int = 100):**
            try:
                # Define sampling parameters
                sampling_params = SamplingParams(
                    temperature=0.0,
                    max_tokens=max_tokens,
                    stop=["\n"],  # Stop at newline
                )
        
                # Generate text
                request_id = "test-request"  # Unique ID for this request
                # Generate tokens in streaming mode
                results_generator = engine.generate(
                    prompt=prompt,
                    sampling_params=sampling_params,
                    request_id=request_id
                )
        
                # Process the results
                final_output = None
                async for request_output in results_generator:
                    final_output = request_output
                    # Print each token as it's generated
                    for chunk in request_output.outputs:
                        print(chunk.text, end="", flush=True)
                        # We could yield return the token chunk here
                        # if it’s a web service
                return final_output
        ```
        
        ```python
        request_id = "any_id"
        await generate_text(prompt, 10000, requtest_id)
        
        ```
        
        !image.png
        
    - v**LLM 코드의 스트리밍 버전**에서 가장 큰 차이점은 표준 LLM 클래스 대신 **AsyncLLMEngine 클래스**를 사용해 모델을 초기화한다는 점입니다.
        - syncLLMEngine에서는 generate() 함수가 비동기 스트림 객체(AsyncStream)를 반환하는데, 이를 통해 async for 루프를 사용해 새로 생성된 토큰을 하나씩 가져올 수 있습니다.
        - 예를 들어, results_generator에서 async for request_output 같은 방식입니다.
    - 스트리밍의 또 다른 장점은 출력이 원하지 않는 방향으로 가고 있을 경우 중간에 생성을 취소할 수 있다는 점입니다.
        - vLLM에서는 특정 생성 요청과 연관된 고유 식별자인 request_id를 사용해 engine.abort(request_id)를 호출함으로써 이를 구현할 수 있습니다.
        - 이 기능은 관련 없거나 잘못된 완성을 방지해 사용자 경험을 향상시킬 뿐만 아니라, 효율성과 비용 관리가 중요한 운영 환경에서 특히 중요한 컴퓨팅 자원 절약에도 기여합니다.
    - 실무 고려 사항
        - Streaming은 TTFT를 낮게 느끼게 만들지만, backend의 총 decode 비용이 사라지는 것은 아니다.
        - 따라서 frontend UX와 backend capacity planning을 분리해서 봐야 한다
        
    - LLM 스트리밍을 더 깊이 탐구하고 싶다면, streaming.py 에 실습 예제를 준비해 두었습니다.
        - https://github.com/orca3/llm-model-inference/blob/main/ch02/streaming.py : LLM 스트리밍
            
            ```python
            # pip install vllm
            # python streaming.py
            
            import asyncio
            from vllm.engine.arg_utils import AsyncEngineArgs
            from vllm.engine.async_llm_engine import AsyncLLMEngine
            from vllm.sampling_params import SamplingParams
            
            # Initialize the vLLM async streaming engine arguments
            engine_args = AsyncEngineArgs(
                model="Qwen/Qwen2.5-0.5B",
                dtype="float16",
                tensor_parallel_size=1,      # Number of GPUs to use
                gpu_memory_utilization=0.9,  # GPU memory utilization
                max_num_batched_tokens=32768, # Maximum number of tokens to process in a batch
                max_num_seqs=256,           # Maximum number of sequences to process
                disable_log_requests=True,   # Disable request logging
                disable_log_stats=True,      # Disable stats logging
            )
            
            # Create the vLLM async streaming engine
            engine = AsyncLLMEngine.from_engine_args(engine_args)
            
            # Define the async function to generate text in streaming mode
            async def generate_text(prompt: str, max_tokens: int = 100):
                try:
                    # Define sampling parameters
                    sampling_params = SamplingParams(
                        temperature=0.0,
                        max_tokens=max_tokens,
                        stop=["\n"],  # Stop at newline
                    )
            
                    # Generate text
                    request_id = "test-request"  # Unique ID for this request
                    # Generate tokens in streaming mode
                    results_generator = engine.generate(
                        prompt=prompt,
                        sampling_params=sampling_params,
                        request_id=request_id
                    )
            
                    # Process the results
                    final_output = None
                    async for request_output in results_generator:
                        final_output = request_output
                        # Print each token as it's generated
                        for output in request_output.outputs:
                            print(output.text, end="", flush=True)
                        print()  # Newline at the end of each output
            
                    return final_output
                except asyncio.CancelledError:
                    # Handle cancellation gracefully
                    print("\nGeneration was cancelled")
                    return None
                finally:
                    # Always clean up
                    try:
                        await engine.abort(request_id)
                    except:
                        pass
            
            # Example of the streamingusage:
            prompt = "What is the capital of US?"
            res = asyncio.run(generate_text(prompt))
            print(res.outputs[0].text)
            ```
            
            ```python
            **# 실행
            source venv/bin/activate && python streaming.py 
            
            # 출력**
            INFO 08-02 07:03:38 [model.py:623] Resolved architecture: Qwen2ForCausalLM
            WARNING 08-02 07:03:38 [model.py:2123] Casting torch.bfloat16 to torch.float16.
            INFO 08-02 07:03:38 [model.py:1788] Using max model len 32768
            INFO 08-02 07:03:38 [scheduler.py:252] Chunked prefill is enabled with max_num_batched_tokens=32768.
            INFO 08-02 07:03:38 [vllm.py:1109] Asynchronous scheduling is enabled.
            INFO 08-02 07:03:38 [kernel.py:295] Final IR op priority after setting platform defaults: IrOpPriorityConfig(rms_norm=['native'], fused_add_rms_norm=['native'])
            (EngineCore pid=6113) INFO 08-02 07:03:41 [core.py:116] Initializing a V1 LLM engine (v0.26.0) with config: model='Qwen/Qwen2.5-0.5B', speculative_config=None, tokenizer='Qwen/Qwen2.5-0.5B', skip_tokenizer_init=False, tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=False, dtype=torch.float16, max_seq_len=32768, download_dir=None, load_format=auto, tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1, decode_context_parallel_size=1, dcp_comm_backend=ag_rs, disable_custom_all_reduce=False, quantization=None, quantization_config=None, enforce_eager=False, enable_return_routed_experts=False, kv_cache_dtype=auto, device_config=cuda, structured_outputs_config=StructuredOutputsConfig(backend='auto', disable_any_whitespace=False, disable_additional_properties=False, reasoning_parser='', reasoning_parser_plugin='', enable_in_reasoning=False), observability_config=ObservabilityConfig(show_hidden_metrics_for_version=None, otlp_traces_endpoint=None, collect_detailed_traces=None, kv_cache_metrics=False, kv_cache_metrics_sample=0.01, cudagraph_metrics=False, enable_layerwise_nvtx_tracing=False, enable_mfu_metrics=False, enable_mm_processor_stats=False, enable_logging_iteration_details=False, jit_monitor_mode='warn', jit_monitor_verbose=False), seed=0, served_model_name=Qwen/Qwen2.5-0.5B, enable_prefix_caching=True, enable_chunked_prefill=True, pooler_config=None, compilation_config={'mode': <CompilationMode.VLLM_COMPILE: 3>, 'debug_dump_path': None, 'cache_dir': '', 'compile_cache_save_format': 'binary', 'backend': 'inductor', 'custom_ops': ['none'], 'ir_enable_torch_wrap': True, 'splitting_ops': ['vllm::unified_attention_with_output', 'vllm::unified_mla_attention_with_output', 'vllm::mamba_mixer2', 'vllm::mamba_mixer', 'vllm::short_conv', 'vllm::linear_attention', 'vllm::plamo2_mamba_mixer', 'vllm::qwen_gdn_attention_core', 'vllm::gdn_attention_core_xpu', 'vllm::olmo_hybrid_gdn_full_forward', 'vllm::kda_attention', 'vllm::sparse_attn_indexer', 'vllm::rocm_aiter_sparse_attn_indexer', 'vllm::deepseek_v4_attention', 'vllm::hpc_rope_norm_forward', 'vllm::unified_kv_cache_update', 'vllm::unified_mla_kv_cache_update'], 'compile_mm_encoder': False, 'cudagraph_mm_encoder': False, 'encoder_cudagraph_token_budgets': [], 'encoder_cudagraph_max_vision_items_per_batch': 0, 'encoder_cudagraph_max_frames_per_batch': None, 'compile_sizes': [], 'compile_ranges_endpoints': [32768], 'inductor_compile_config': {'enable_auto_functionalized_v2': False, 'size_asserts': False, 'alignment_asserts': False, 'scalar_asserts': False, 'combo_kernels': True, 'benchmark_combo_kernel': True}, 'inductor_passes': {}, 'cudagraph_mode': <CUDAGraphMode.FULL_AND_PIECEWISE: (2, 1)>, 'cudagraph_num_of_warmups': 1, 'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512], 'cudagraph_copy_inputs': False, 'cudagraph_specialize_lora': True, 'use_inductor_graph_partition': False, 'pass_config': {'fuse_norm_quant': False, 'fuse_act_quant': False, 'fuse_attn_quant': False, 'enable_sp': False, 'fuse_gemm_comms': False, 'fuse_allreduce_rms': False, 'enable_qk_norm_rope_fusion': False, 'fuse_rope_kvcache_cat_mla': False, 'fuse_act_padding': False, 'fuse_qk_norm_rope_kvcache': False}, 'max_cudagraph_capture_size': 512, 'dynamic_shapes_config': {'type': <DynamicShapesType.BACKED: 'backed'>, 'evaluate_guards': False, 'assume_32_bit_indexing': False}, 'local_cache_dir': None, 'fast_moe_cold_start': False, 'static_all_moe_layers': []}, kernel_config=KernelConfig(ir_op_priority=IrOpPriorityConfig(rms_norm=['native'], fused_add_rms_norm=['native']), enable_flashinfer_autotune=True, enable_cutedsl_warmup=True, enable_bf16x3_router_gemm=False, moe_backend='auto', linear_backend='auto')
            (EngineCore pid=6113) INFO 08-02 07:03:42 [parallel_state.py:1615] world_size=1 rank=0 local_rank=0 distributed_init_method=tcp://192.168.254.150:58641 backend=nccl
            (EngineCore pid=6113) INFO 08-02 07:03:42 [parallel_state.py:1946] rank 0 in world size 1 is assigned as DP rank 0, PP rank 0, PCP rank 0, TP rank 0, EP rank N/A, EPLB rank N/A
            (EngineCore pid=6113) INFO 08-02 07:03:42 [gpu_worker.py:378] Using V2 Model Runner
            (EngineCore pid=6113) INFO 08-02 07:03:43 [model_runner.py:284] Loading model from scratch...
            (EngineCore pid=6113) INFO 08-02 07:03:43 [cuda.py:482] Using FLASH_ATTN attention backend out of potential backends: ['FLASH_ATTN', 'FLASHINFER', 'TRITON_ATTN', 'FLEX_ATTENTION'].
            (EngineCore pid=6113) INFO 08-02 07:03:43 [flash_attn.py:776] Using FlashAttention version 2
            (EngineCore pid=6113) INFO 08-02 07:03:44 [weight_utils.py:574] No model.safetensors.index.json found in remote.
            (EngineCore pid=6113) INFO 08-02 07:03:44 [weight_utils.py:869] Filesystem type for checkpoints: EXT4. Checkpoint size: 0.92 GiB. Available RAM: 57.97 GiB.
            (EngineCore pid=6113) INFO 08-02 07:03:44 [weight_utils.py:892] Auto-prefetch is disabled because the filesystem (EXT4) is not a recognized network FS (NFS/Lustre). If you want to force prefetching, start vLLM with --safetensors-load-strategy=prefetch.
            Loading safetensors checkpoint shards:   0% Completed | 0/1 [00:00<?, ?it/s]
            Loading safetensors checkpoint shards: 100% Completed | 1/1 [00:00<00:00,  7.53it/s]
            Loading safetensors checkpoint shards: 100% Completed | 1/1 [00:00<00:00,  7.52it/s]
            (EngineCore pid=6113) 
            (EngineCore pid=6113) INFO 08-02 07:03:44 [default_loader.py:430] Loading weights took 0.15 seconds
            (EngineCore pid=6113) INFO 08-02 07:03:45 [model_runner.py:305] Model loading took 0.93 GiB and 2.174401 seconds
            (EngineCore pid=6113) INFO 08-02 07:03:45 [topk_topp_sampler.py:55] Using FlashInfer for top-p & top-k sampling.
            (EngineCore pid=6113) INFO 08-02 07:03:46 [backends.py:1094] Using cache directory: /root/.cache/vllm/torch_compile_cache/0f8b20bdea/rank_0_0/backbone for vLLM's torch.compile
            (EngineCore pid=6113) INFO 08-02 07:03:46 [backends.py:1155] Dynamo bytecode transform time: 0.98 s
            (EngineCore pid=6113) INFO 08-02 07:03:46 [backends.py:292] Directly load the compiled graph(s) for compile range (1, 32768) from the cache, took 0.648 s
            (EngineCore pid=6113) INFO 08-02 07:03:46 [decorators.py:311] Directly load AOT compilation from path /root/.cache/vllm/torch_compile_cache/torch_aot_compile/6a46140b0a23b906656d44ed53ba1af3cf3097e1b27cacfe1f21c0dbc85fb58f/rank_0_0/model
            (EngineCore pid=6113) INFO 08-02 07:03:46 [monitor.py:53] torch.compile took 1.74 s in total
            (EngineCore pid=6113) INFO 08-02 07:03:47 [monitor.py:81] Initial profiling/warmup run took 0.11 s
            (EngineCore pid=6113) INFO 08-02 07:03:47 [gpu_worker.py:560] Available KV cache memory: 11.94 GiB
            (EngineCore pid=6113) INFO 08-02 07:03:47 [kv_cache_utils.py:2177] GPU KV cache size: 1,043,072 tokens
            (EngineCore pid=6113) INFO 08-02 07:03:47 [kv_cache_utils.py:2178] Maximum concurrency for 32,768 tokens per request: 31.83x
            (EngineCore pid=6113) INFO 08-02 07:03:47 [cutedsl_warmup.py:101] Skipping CuTeDSL warmup because no compile units were requested.
            Capturing CUDA graphs (PIECEWISE): 100%|█████████████████████████████████████████████████████████████████████████| 51/51 [00:00<00:00, 65.56it/s]
            Capturing CUDA graphs (FULL): 100%|██████████████████████████████████████████████████████████████████████████████| 35/35 [00:00<00:00, 71.38it/s]
            (EngineCore pid=6113) INFO 08-02 07:03:49 [model_runner.py:747] Graph capturing finished in 1 secs, took 0.40 GiB
            (EngineCore pid=6113) INFO 08-02 07:03:49 [gpu_worker.py:857] Free memory on device (15.32/15.55 GiB) on startup. Desired GPU memory utilization is (0.9, 13.99 GiB). Actual usage is 0.93 GiB for weight, 1.06 GiB for peak activation, 0.07 GiB for non-torch memory, and 0.4 GiB for CUDAGraph memory. Replace gpu_memory_utilization config with `--kv-cache-memory=12227975783` (11.39 GiB) to fit into requested memory, or `--kv-cache-memory=13651129344` (12.71 GiB) to fully utilize gpu memory. Current kv cache memory in use is 11.94 GiB.
            (EngineCore pid=6113) INFO 08-02 07:03:49 [jit_monitor.py:79] Kernel JIT monitor activated; monitored JIT compilations during inference will use mode=warn.
            (EngineCore pid=6113) INFO 08-02 07:03:50 [core.py:340] init engine (profile, create kv cache, warmup model) took 5.07 s (compilation: 1.74 s)
            (EngineCore pid=6113) INFO 08-02 07:03:50 [kernel.py:295] Final IR op priority after setting platform defaults: IrOpPriorityConfig(rms_norm=['native'], fused_add_rms_norm=['native'])
            WARNING 08-02 07:03:50 [input_processor.py:282] Passing raw prompts to InputProcessor is deprecated and will be removed in v0.18. You should instead pass the outputs of Renderer.render_cmpl() or Renderer.render_chat().
             **The
             The capital
             The capital of
             The capital of the
             The capital of the United
             The capital of the United States
             The capital of the United States is
             The capital of the United States is Washington
             The capital of the United States is Washington,
             The capital of the United States is Washington, D
             The capital of the United States is Washington, D.C
             The capital of the United States is Washington, D.C.**
             The capital of the United States is Washington, D.C.
             The capital of the United States is Washington, D.C.
            (EngineCore pid=6113) INFO 08-02 07:03:50 [core.py:1313] [shutdown] EngineCore: trigger received signal=SIGTERM
            (EngineCore pid=6113) INFO 08-02 07:03:50 [core.py:1432] [shutdown] EngineCore: start mode=abort timeout=0s
            (EngineCore pid=6113) INFO 08-02 07:03:50 [core.py:1463] [shutdown] EngineCore: request processing complete; starting resource teardown
            (EngineCore pid=6113) INFO 08-02 07:03:50 [core.py:1326] [shutdown] EngineCore: exiting busy loop
            WARNING 08-02 07:03:51 [core_client.py:702] [shutdown] MPClient: engine core exited unexpectedly; starting cleanup
            INFO 08-02 07:03:51 [core_client.py:655] [shutdown] MPClient: start timeout=default
            INFO 08-02 07:03:51 [core_client.py:657] [shutdown] MPClient: stopping engine manager
            INFO 08-02 07:03:51 [core_client.py:659] [shutdown] MPClient: engine manager stopped
            INFO 08-02 07:03:51 [core_client.py:660] [shutdown] MPClient: cleaning up background resources
            INFO 08-02 07:03:51 [core_client.py:662] [shutdown] MPClient: complete
            Exception ignored in: <function AsyncLLM.__del__ at 0x7f47d19c14e0>
            Traceback (most recent call last):
              File "/root/llm-model-inference/ch02/venv/lib/python3.12/site-packages/vllm/v1/engine/async_llm.py", line 257, in __del__
              File "/root/llm-model-inference/ch02/venv/lib/python3.12/site-packages/vllm/v1/engine/async_llm.py", line 261, in shutdown
            TypeError: 'NoneType' object is not callable
            ```
            
    - 다음 장에서는 웹 서비스 환경에서 LLM 스트리밍을 구현하는 방법을 보여주며, 사용자와 직접 상호작용하는 애플리케이션에서 실시간 대화를 가능하게 하는 방법을 다룰 것입니다.
    

### LLM Batch Serving Basics

- **왜 배치가 필요한가**
    
    !Figure 2-14. Batch LLM inference는 여러 input sequence와 output sequence를 병렬로 처리한다
    
    Figure 2-14. Batch LLM inference는 여러 input sequence와 output sequence를 병렬로 처리한다
    
    - 지금까지의 예제는 **프롬프트를 한 번에 하나씩 처리**했습니다. 프로토타입 단계에서는 문제없지만, 실무 시나리오(문서 10만 건 요약, PDF 5천 개 인덱싱, 동시 사용자 2만 명 챗봇)에서는 요청을 하나씩 순차 처리하면 GPU가 대부분의 시간 동안 놀게 되어 확장성이 없습니다.
    - 배치란 **여러 입력 요청을 묶어서 모델의 한 번의 forward pass에 동시에 통과**시키는 것입니다.
    - 왜 **트랜스포머는 배치가 특히 효과적**인가
        - 행렬곱(matmul)과 어텐션 연산은 시퀀스 차원으로 **병렬화 가능**
        - **모델 가중치는 모든 요청이 공유**하므로, **배치 크기를 늘려도 가중치를 다시 읽어올 필요 없음**(메모리 대역폭 재사용)
        - GPU는 원래 대규모 병렬 연산에 최적화된 하드웨어라서, **배치로 묶으면 그만큼 GPU 코어를 놀리지 않고 꽉 채워 씀**
        - ⇒ 그래서 여러 요청을 한 번에 처리해도 오버헤드가 크게 늘지 않고, GPU 활용률(utilization)이 크게 올라감!
    
- https://github.com/orca3/llm-model-inference/blob/main/ch02/ch2_Batching.ipynb : by 구글 Colab
    - Batch serving은 여러 prompt를 한 번에 묶어 처리해 GPU utilization을 높이는 방식이다. LLM serving framework는 여러 request의 prefill/decode를 효율적으로 섞어 처리할 수 있어야 한다.
    - TS : vllm 버전 호환성 → 런타임 유형 변경(2025.07)
        
        ```python
        **# [6분] 5분 설치 -> 세션 재시작
        !pip install vllm==0.6.6.post1
        !pip install --quiet transformers tiktoken**
        ```
        
    - Let’s look at how to enable streaming generation with vLLM using a simple code example:
        
        ```python
        import time
        from vllm import LLM, SamplingParams
        
        # Load model with vLLM
        llm = LLM(
            model="Qwen/Qwen2.5-0.5B",
            dtype="float16",
            trust_remote_code=True,
            max_model_len=2048
        )
        
        import torch
        import gc
        import time
        from vllm import LLM, SamplingParams
        from transformers import pipeline
        
        # Prompts for batch generation, 4 input sequences # **4개의 서로 다른 프롬프트!**
        prompts = [
            "What is the meaning of life?",
            "Write a short story about a robot learning to love.",
            "Explain quantum physics in simple terms.",
            "Translate 'Hello, world!' into Spanish."
        ]
        
        sampling_params = SamplingParams(
            temperature=0.8,
            top_p=0.95,
            max_tokens=100
        )
        
        start_time = time.time()
        
        **# 배치 처리 :  리스트 전체(prompts, 4개)를 한 번에 generate()에 넘김** → vLLM이 내부적으로 4개 시퀀스를 하나의 배치로 묶어 GPU에서 동시 처리.
        # process four input sequences (prompts) together in one batch
        vllm_outputs = llm.generate(prompts, sampling_params)
        end_time = time.time()
        vllm_time = end_time - start_time
        
        print(f"\nvLLM generation time for 4 prompts in a batch: {vllm_time:.4f} seconds")
        
        **# 순차 처리: 매번 리스트 길이로 generate()가 독립적으로 실행되고, 각 호출 안에서 Prefill 1회와 여러 번의 Decode Forward가 수행됩**
        # process prompt one by one
        start_time = time.time()
        for prompt in prompts:
            vllm_outputs = llm.generate([prompt], sampling_params)
        end_time = time.time()
        vllm_time = end_time - start_time
        
        print(f"\nvLLM generation time for 4 prompts one by one: {vllm_time:.4f} seconds")
        ```
        
        !스크린샷 2026-08-02 오후 6.07.20.png
        
        ```python
        Processed prompts: 100%|██████████| 4/4 [00:01<00:00,  2.95it/s, est. speed input: 25.86 toks/s, output: 226.07 toks/s]
        vLLM generation time for 4 prompts in a **batch: 1.3777 seconds**
        
        Processed prompts: 100%|██████████| 1/1 [00:00<00:00,  1.24it/s, est. speed input: 8.70 toks/s, output: 124.30 toks/s]
        Processed prompts: 100%|██████████| 1/1 [00:00<00:00,  1.28it/s, est. speed input: 14.16 toks/s, output: 128.73 toks/s]
        Processed prompts: 100%|██████████| 1/1 [00:00<00:00,  1.32it/s, est. speed input: 10.57 toks/s, output: 128.10 toks/s]
        Processed prompts: 100%|██████████| 1/1 [00:00<00:00, 11.02it/s, est. speed input: 99.38 toks/s, output: 66.24 toks/s]
        vLLM generation time for 4 prompts **one by one: 2.4753 seconds**
        ```
        
    - 결과 : **순차 처리보다 → 배치 처리가 약 2.2배 처리량 향상**
        - 배치: 1.0626초 (4개 동시)
        - 순차: 2.3865초 (4개 합산)
        
        | 구분 | 배치 처리 | 순차 처리 |
        | --- | --- | --- |
        | `generate()` 호출 수 | 1회 | 4회 |
        | 동시에 처리하는 요청 | 최대 4개 | 1개 |
        | Prefill | 여러 입력을 묶을 수 있음 | 각각 따로 |
        | Decode | 여러 시퀀스 함께 처리 | 한 시퀀스씩 |
        | GPU 활용률 | 일반적으로 높음 | 낮을 수 있음 |
        | 전체 처리량 | 일반적으로 높음 | 낮을 수 있음 |
        | 개별 요청 완료 시점 | 긴 요청 영향 가능 | 각 요청이 차례로 완료 |
        | 스케줄링 오버헤드 | 상대적으로 적음 | 반복 발생 |
        
    - 주목할 점은 이론상 "완벽한 병렬화"라면 거의 4배 가까이 빨라져야 할 것 같지만, 실제로는 2.2배에 그쳤다는 것입니다. 이는:
        - 프롬프트 길이가 서로 다르기 때문 (배치 내 가장 긴 시퀀스에 맞춰 패딩/스케줄링 필요)
        - max_tokens=100이라 출력 길이도 프롬프트마다 다르게 끝날 수 있어 완전한 병렬 효율은 안 나옴
        - 이 예제가 GPU를 포화시킬 만큼 큰 배치(4개는 작음)가 아니라서, 배치 크기를 늘릴수록 상대적 이득은 더 커짐
        
    - Batching은 throughput을 높이는 강력한 방법이지만, 요청별 latency와 fairness에 영향을 줄 수 있다.
    - production에서는 batch size, max batched tokens, scheduling policy, queue time을 함께 튜닝해야 한다.
        
        
    - **Continuous Batching 예고**
        - 정적 배치(static batching, 지금 예제처럼 4개를 고정으로 묶어 한꺼번에 끝날 때까지 처리)의 한계는, 배치 안에서 짧은 응답이 먼저 끝나도 GPU 슬롯이 비지 않고 배치 전체가 끝날 때까지 기다려야 한다는 점입니다.
        - Continuous batching(6장에서 상세히 다룸)은 이 문제를 해결합니다: 요청이 완료되는 즉시 그 자리에 새 요청을 동적으로 끼워 넣어, GPU가 쉬는 시간 없이 계속 바쁘게 유지됩니다. Anyscale의 2023년 연구에서는 이 기법으로 최대 23배 처리량 향상과 p50 지연시간 대폭 감소를 보고했습니다.
        - 즉 이 섹션의 흐름은: 단일 처리(느림) → 정적 배치(2.2배 개선, 하지만 여전히 비효율) → 연속 배치(다음 장에서 다룰 진짜 프로덕션급 기법, 최대 23배)로 이어지는 성능 최적화 스토리를 보여주는 것입니다.
    
- (참고) Concurrency and Batch Sizing : Static vs Dynamic vs Continuous batching
    - 핵심 주제: 오토스케일링을 위해 "인스턴스 하나가 동시에 몇 개의 요청을 처리할 수 있는가"를 알아야 한다
        - 트래픽 기반 오토스케일링(traffic-based autoscaling)을 제대로 운영하려면, 각 인스턴스(replica)가 얼마나 많은 동시 요청(concurrent traffic)을 소화할 수 있는지 정확히 알아야 합니다. 이걸 알아야 "언제 인스턴스를 늘리고 줄일지" 판단할 수 있기 때문입니다.
        
    - **Static batching** : 배치가 꽉 찰 때까지 기다린 후 추론 시작, 먼저 들어온 요청이 배치가 찰 때까지 오래 대기해야 함
        
        !image.png
        
    - Dynamic batching : 배치가 꽉 차거나, 설정된 시간(timeout)이 지나면 추론 시작, static의 대기시간 문제를 시간 제한으로 완화
        
        !image.png
        
    - Continuous batching : 추론을 끊임없이 돌리면서, 슬롯이 비면 새 요청을 바로 끼워 넣음, 토큰 단위로 배칭 — 이전 대화에서 본 vLLM의 continuous batching이
        
        !image.png
        
    - vLLM, SGLang, TensorRT-LLM(TensorRT-LLM에서는 "in-flight batching"이라 부름) 같은 추론 엔진들이 이 continuous batching을 구현해서, static batching 대비 지연시간(latency)을 최소화합니다.
        
        
    - 배치 크기(Batch Size)의 트레이드오프 : 배치 크기 ↑ → 처리량(throughput) ↑, 하지만 개별 사용자의 지연시간(latency) ↓ (나빠짐)
        - 배치를 크게 잡을수록 GPU가 한 번에 더 많은 요청을 처리해 전체 처리량은 늘어남
        - 하지만 한 요청이 배치 안의 다른 요청들과 묶여서 처리되므로, 개별 요청 입장에서는 응답이 더 오래 걸림
        - 그래서 정답은 없고, 모델·인스턴스·지연시간 목표·예산에 맞춰 여러 배치 크기로 성능 테스트를 해서 적정선을 찾아야 함
        
    - 오토스케일링과의 고려사항 : 이 트레이드오프가 오토스케일링 설정에 두 레벨로 반영
        1. 오토스케일링 설정 레벨: concurrency target (인스턴스 하나가 목표로 하는 동시 처리 요청 수)
        2. 레플리카(인스턴스) 레벨: batch size (실제 인스턴스가 처리하는 배치 크기)
        - 이 둘은 서로 일치해야 합니다 (concurrency target = batch size로 맞춰야 함).
    - 스케일링 판단 로직
        - 활성 레플리카들이 모두 최대 동시성(max concurrency)에 도달 → 레플리카를 더 띄워야 할 시점 (scale up)
        - 레플리카들이 절반만 찬 배치(half-full batch)로 계속 요청을 처리 중 → 레플리카를 줄여야 할 시점 (scale down)
    
- `도전과제` ’Streaming Serving , Batch Serving’ 동작이 가능한 이유와 내부 동작 정리해보기

- **Summary** : "이론(Transformer/어텐션) → 저수준 실습(KV 캐시, prefill/decode) → 실전 도구(vLLM) → 성능 전략(streaming/batch)"
    1. 이론 기반 (Transformer 아키텍처)
        - 디코더 전용(decoder-only) 모델에 집중
        - 어텐션 메커니즘과 자기회귀(autoregressive) 토큰 생성 : 즉 모델이 이전에 생성한 토큰을 다시 입력으로 받아 다음 토큰을 하나씩 예측하는 방식
    2. 실습 (스크래치 구현)
        - KV 캐싱(KV caching): 이전 토큰들의 Key/Value를 재계산하지 않고 캐시에 저장해 재사용 → 디코딩 속도 향상
        - Prefill / Decode 단계:
            - Prefill = 입력 프롬프트 전체를 한 번에 처리해 KV 캐시를 채우는 단계 (연산 집약적, compute-bound)
            - Decode = 토큰을 하나씩 순차 생성하는 단계 (메모리 대역폭 집약적, memory-bound)
            - 이 둘의 특성 차이가 LLM 서빙 성능 최적화의 핵심 포인트
    3. 실전 서빙 프레임워크 (vLLM)
        - 스크래치 구현에서 vLLM 같은 프로덕션급 서빙 프레임워크로 전환
        - 저수준 복잡도를 추상화하면서도 훨씬 뛰어난 성능 제공 → 최소한의 오버헤드로 확장 가능한 서비스 구축 가능
    4. 실전 전략 두 가지
        - 스트리밍(streaming): 토큰이 생성되는 즉시 클라이언트에 전달 → 체감 지연시간(latency) 감소
        - 배치(batch): 여러 요청을 묶어 처리 → 처리량(throughput) 증대 (바로 이전 대화에서 다룬 내용)
    - 다음 장 예고
        - 3장에서는 이 서빙 역량들을 실제 웹 서비스로 감싸는 방법
        - API 설계, 아키텍처 결정, 운영 모범 사례(operational best practices) 를 다룬다고 예고하고 있습니다.
    

### 1주차 과제

- **1주차 스터디**에서 학습한 내용 혹은 **LLM 관련 내용(혹은 도전과제)**을 **간략히 정리**하여 **공개된 링크에 글 작성** 후 해당 링크를 **과제제출표**에 공유 🙇🏻‍♂️🙇🏻‍♀️
    - **작성 도구** : 블로그, Github, 개인 홈페이지, 개인 Youtube, ‘페이스북/링크드인 공개 게시 글’ 등
    - **정리 내용(예시)**
        - 해당 주차 스터디에서 학습한 내용을 요약 정리 작성
        - 해당 주차 스터디에서 다룬 주제 기술 1개를 별도 조사 학습해서 정리
        - LLM 서빙 관련 운영 경험 중 기술 내용 위주로 정리
        - 최근 LLM 서빙 관련 새로운 기술에 대한 분석 정리
    

`멤버 작성 과제 추천`

- **서진호**님이 ‘추론 엔지니어링의 부상(1~3편)’ 내용으로 이해하기 쉽게 정리해주셨네요.
    - https://synabreu.github.io/opensource/추론-엔지니어링의-부상(1)//)
    - https://synabreu.github.io/opensource/추론-엔지니어링의-부상(2)//)
    - https://synabreu.github.io/opensource/추론-엔지니어링의-부상(3)//)
    
- **최병민**님이 ‘Cloud Run RTX PRO 6000 GPU에서 vLLM으로 Gemma 4 추론 실행, 성능 측정’ 내용 정리를 해주셨네요. 좋은 글 감사합니다.
    
    https://atlantic-andesaurus-8b9.notion.site/Cloud-Run-RTX-PRO-6000-GPU-vLLM-Gemma-4-3af4c2420ac480aea1b3df3393928525
    
    ```python
    # Cloud Run 배포 : `--load-format runai_streamer`로 Model Streamer를 사용하고, Gemma 4의 tool call/reasoning parser를 지정한다.
    
    CONTAINER_ARGS=(
      "vllm" "serve" "$GCS_MODEL_LOCATION"
      "--served-model-name" "$MODEL_NAME"
      "--enable-log-requests" "--enable-chunked-prefill" "--enable-prefix-caching"
      "--generation-config" "auto"
      "--enable-auto-tool-choice" "--tool-call-parser" "gemma4"
      "--reasoning-parser" "gemma4"
      "--dtype" "bfloat16" "--quantization" "$QUANTIZATION_TYPE"
      "--kv-cache-dtype" "$KV_CACHE_DTYPE"
      "--max-num-seqs" "$MAX_NUM_SEQS"
      "--gpu-memory-utilization" "$GPU_MEM_UTIL"
      "--tensor-parallel-size" "$TENSOR_PARALLEL_SIZE"
      "--load-format" "runai_streamer" "--port" "8080" "--host" "0.0.0.0"
    )
    if [[ "$MAX_MODEL_LEN" != "" ]]; then
      CONTAINER_ARGS+=("--max-model-len" "$MAX_MODEL_LEN")
    fi
    export CONTAINER_ARGS_STR="${CONTAINER_ARGS[*]}"
    ```
    
- **손훈서**님이 ‘Attention, Transformer’ 를 간결하고 이해하기 쉽게 정리 해주시네요. 다들 읽어 보시기 바랍니다.
    - https://blog.sonhs.com/AI/attention/
    - https://blog.sonhs.com/AI/transformer/
        
        !https://blog.sonhs.com/AI/transformer/
        
        https://blog.sonhs.com/AI/transformer/
        
    
- **배효성**님이 1주차 스터디 내용을 도식화와 함께 정리해주셨네요.
    - https://insumnia.tistory.com/33
    - https://insumnia.tistory.com/34
    
- **박기범**님이 ‘K8s 기반 GPU 인프라 아키텍처 및 GPU Operator 구성’ 정리를 해주셨습니다.
    - https://grand-cadmium-a17.notion.site/K8s-GPU-GPU-Operator-3b2fe752ea0280cc8752f455f468e25f
    
- **김진웅**님이 ‘Transformer 완벽 이해 가이드’ 와 ‘LLM 서빙 기초’ 를 각각 실습 코드와 함께 이해하기 쉽게 설명 정리해주셨네요.
    - https://ddii.dev/deep-learning/transformer-explainer/
    
- **신유진**님이 b200 서버에서 서빙 경험을 ‘vLLM GPT-OSS-120B 실설정 기반으로 개념 이해하기’ 주제 정리와 최근 겪었던 이슈를 정리해주셨네요. 좋은 글 감사합니다.
    - https://app.notion.com/p/vLLM-GPT-OSS-120B-3b17b79f4e4980b7ae32ee8962d8cdf6
    
    ```python
    # GPT-OSS-120B 설정을 다시 읽어보기
    command: ["vllm", "serve", "openai/gpt-oss-120b",
      "--tensor-parallel-size", "4",         # 1장: 120B를 GPU 4장에 쪼개 담기 위해
      "--block-size", "128",                 # 3장: KV캐시를 관리하는 페이지(블록) 크기
      "--max-model-len", "131072",           # 2장: 모델이 지원하는 최대 컨텍스트(128K) 그대로 사용
      "--max-num-batched-tokens", "32768",   # 4장: 한 스텝에 처리할 토큰 예산
      "--max-num-seqs", "512",               # 4장: 한 스텝에 동시 처리할 요청 개수 상한
      "--gpu-memory-utilization", "0.9",     # GPU 메모리의 90%까지 vLLM이 쓰도록 허용
      "--kv-cache-dtype", "fp8",             # 5장: KV캐시를 fp8로 압축 저장
      "--moe-backend", "flashinfer_cutlass", # 6장: MoE 전용 최적화 커널
      "--quantization_config.moe.activation", "mxfp8",  # 5장+6장: MoE 연산을 fp8 계열로 가속
      "--max-cudagraph-capture-size", "2048",# 7장: CUDA Graph로 캡처할 배치 크기 상한
      "--enable-prefix-caching",             # 3장의 응용: 반복되는 프롬프트 앞부분 KV캐시 재사용
      "--enable-auto-tool-choice",           # 모델이 툴 호출 여부를 스스로 판단하게 허용
      "--tool-call-parser", "openai",        # 툴콜 출력을 OpenAI API 포맷으로 파싱
    ]
    
    # 위에서 배운 개념들이 실제로 겪은 이슈 중 연결되는걸 정리해봤습니다.
    # 개념만 보면 추상적인데, 실제 장애 사례로 보면 왜 이 옵션들이 필요했는지 훨씬 체감됩니다.
    
    ### startupProbe 타임아웃 → 120B 모델 로딩 시간 문제
    
    **증상**: gpt-oss-120b처럼 큰 모델을 올릴 때, 컨테이너가 뜨고 나서 실제로 요청을 받을 수 있는
    상태가 되기까지 시간이 오래 걸리는데, k8s의 헬스체크가 그 시간을 못 기다려주고 "이 파드 죽었다"고
    판단해 재시작시켜버려서 영원히 못 뜨는 재시작 루프에 빠지는 문제.
    
    **원인**: 1장에서 본 TP=4 구조상, GPU 4장에 모델 가중치를 나눠 로드하고 GPU끼리 초기 통신
    설정까지 마쳐야 서빙 가능한 상태가 되는데, 이 과정 자체가 수 분 이상 걸릴 수 있음.
    기본 `startupProbe` 설정은 이렇게 오래 걸리는 걸 감안하지 않은 값이었음.
    
    **해결**: `startupProbe`에 `periodSeconds: 30`, `failureThreshold: 60`을 추가해서
    최대 30분까지 로딩을 기다려주도록 조정. (본문 `values.yaml`에 이미 반영되어 있는 설정)
    
    ### NVFP4 MoE 커널 호환성 이슈 (MIG 환경)
    
    **증상**: MIG(Multi-Instance GPU, GPU 한 장을 여러 개의 작은 논리적 GPU로 쪼개 쓰는 기능) 환경에서
    NVFP4 양자화를 쓰는 MoE 커널이 정상 동작하지 않는 문제.
    
    **배경 연결**: 5장(양자화)과 6장(MoE)에서 봤듯, MoE 레이어 연산을 가속하려고 fp8 계열
    양자화 포맷을 쓰는데, 이런 저정밀도 커널들은 특정 GPU 아키텍처/드라이버 조합에서만 지원됩니다.
    MIG로 GPU를 분할하면 물리 GPU 한 장을 여러 논리 단위로 쪼개는 만큼, 최신 양자화 커널이
    기대하는 하드웨어 조건과 어긋나는 경우가 생길 수 있음.
    
    **대응**: MIG 프로파일 구성을 재점검하고, 커널 호환성이 확인된 조합(MIG 미사용 풀 GPU 등)으로
    서빙 방식을 조정.
    
    ### XID 94 에러 / unhealthy GPU
    
    **증상**: GPU가 갑자기 응답하지 않거나 unhealthy 상태로 빠지면서, k8s가 해당 노드의 GPU를
    스케줄링 대상에서 제외해버리는 현상. `XID 94`는 NVIDIA 드라이버가 GPU 하드웨어/펌웨어
    레벨에서 감지한 오류 코드 중 하나.
    
    **배경 연결**: TP=4처럼 GPU 여러 장이 긴밀하게 통신하는 워크로드(7장의 NCCL all-reduce 등)에서는,
    GPU 한 장만 문제가 생겨도 그 GPU와 연결된 전체 서빙 인스턴스가 영향을 받습니다. 즉 GPU 헬스
    문제가 단일 GPU 장애로 끝나지 않고 TP 그룹 전체의 장애로 번지기 쉬운 구조.
    
    **대응**: XID 에러 발생 시 해당 노드/GPU를 격리하고, 드라이버·펌웨어 버전 점검 및 재시작으로 복구.
    
    ### InfiniBand ConnectX-7 / BlueField-3 펌웨어 버전 감사
    
    **배경 연결**: 1장에서 "TP는 GPU 간 통신 속도에 매우 민감하다"고 짚었던 부분과 직결됩니다.
    GPU 간 통신(NVLink)뿐 아니라, 노드 간 또는 스토리지 연결에 쓰이는 InfiniBand 네트워크 카드의
    펌웨어 버전이 오래되거나 불일치하면 통신 성능 저하나 불안정성으로 이어질 수 있어서,
    전체 노드들의 ConnectX-7/BlueField-3 펌웨어 버전을 감사(점검)하고 통일하는 작업을 진행.
    ```
    
- **신호승**님이 스터디 내용을 상세히 정리해주셨네요.
    - https://lotshin.tistory.com/41
    - https://lotshin.tistory.com/42
    
- **조원준**님이 ‘트랜스포머를 Go로 직접 만들어보며 이해한 것 + 훈련 포함’ 주제로 각 과정을 go 코드로 직접 구현 후 정리해주셨네요. 그외 각 과정에 동작 설명을 비유와 함께 쉽게 작성해주셨네요. 다들 꼭 읽어보시기 바랍니다.
    - https://velog.io/@victorjo/트랜스포머를-Go로-직접-만들어보며-이해한-것
    
    !image.png
    
    !image.png
    
    !image.png
    
    !image.png
    
- **황주원**님이 스터디 내용을 깔끔하게 정리해주셨네요.
    - https://juwon8891.github.io/vllm/week1-llm-basics-model-serving/
    
- **박규리**님이 ‘CPU vs GPU 구조’, ‘Transformer 구조’를 잘 정리해주셨네요. 좋은 글 감사합니다.
    - https://velog.io/@_gyullbb/1편.-CPU-vs-GPU-구조-왜-딥러닝은-GPU에서-동작할까
    - https://velog.io/@_gyullbb/2편.-Transformer-구조
    
- **유동주**님이 ‘AMD Radeon AI PRO R9700(CUDA 대신 → AMD ROCm)’ GPU 환경에서 vLLM 실습(측정) 정리를 해주셨네요.
    - https://github.com/Aiden-Yoo/llm-serving-study/blob/main/week01/README.md
    - https://github.com/Aiden-Yoo/llm-serving-study/blob/main/week01/experiments/results/latest.md
    1. Qwen3-4B BF16으로 ROCm·PyTorch·vLLM 동작 확인
    2. 같은 모델과 고정된 prompt 집합으로 기준 성능 측정
    3. KV Cache, 입력·출력 길이, 배칭, prefix caching 설정을 하나씩 변경
    4. 결과가 안정되면 기존 Q8 GGUF 또는 추가 양자화 모델로 범위 확장
    
- **이기연**님이 어텐션의 발전 내용인 ‘MHA, MQA, GQA’ 정리를 해주셨네요.
    - https://app.notion.com/p/MHA-MQA-GQA-3b5ba7ee496f80c8b45dc6d6a03cdb4a
    
    !image.png
    
    !image.png
    
- **박준희**님이 ‘기초 수학 정리’ 부터 ‘챕터 1, LLM, 챕터2’ 내용 정리를 ‘동적 적용 그래프’를 포함해서 친절하게 작성해주셨네요. 작성하시는데 상당한 시간이 소요되었을것 같네요. 귀한 정리 감사합니다. 다른 분들 꼭 읽어보시기 바랍니다.
    - 트랜스포머 모델을 이해하기 위한 기초 수학 정리 - Blog
    - CH1 정리 - Blog
    - CH2 정리 - Blog
    - LLM 기초 동작 원리 - Blog
    
    !image.png
    
    !image.png
    
- **송이레**님이 ‘AI 개요, 트랜스포머 개요와 동작’을 상세한 설명과 함께 작성해주셨네요.
    - AI 개요: 가중치, 행렬, 그리고 학습과 GPU - Blog
    - LLM과 트랜스포머 개요 - Blog
    - Transformer: Transformer Explainer - Blog
    - Transformer: 임베딩 - Blog
    - Transformer: 트랜스포머 블록과 셀프 어텐션 레이어 - Blog
    - **Transformer: 셀프 어텐션 계산 해부*** - Blog
    
    !image.png
    

### 도전 과제

- `도전과제` [Branch Education] CPU 동작 - Youtube vs GPU 동작 - Youtube ← 비교 정리 해보기
- `도전과제` Attention Is All You Need (트랜스포머 아키텍처)를 학습하고 직접 주요 동작을 정리 해보기
- `도전과제` Transformer Explainer를 사용하여 직접 각 동작 과정을 정리 해보기 - Site
- `도전과제` Why LLMs Use 75% Less Memory - GQA & MQA Explained in 8 Min - Youtube : 해당 영상 학습 후 동작 정리
- `도전과제` ipynb 실습을 자신의 로컬 PC에 주피터 노트북 설치 후 실행 해보기
- `도전과제` 1주차 학습 내용과 관련된 주제를 **Inference Engineering(2026).pdf** 내용에서 발췌해서 정리 해보기
- `도전과제` **’밑바닥부터 만들면서 배우는 LLM’ 책** 제공 실습으로 LLM 추론/학습 후 정리 해보기 - Code , Youtube
- `도전과제` gpt 의 미니멀한 구현체를 python builtin function 만으로 구성한 구현체 따라해보기 - Blog, Code, Colab
- `도전과제` KV Cache, Prefill+Decode, P/D Disaggregation 학습 후 정리 해보기 + vLLM/SGLang 에서 실습 해보기
- `도전과제` ’Flash Attention, PagedAttention’ 등 vLLM과 SGLang 에서 제공되는 최적화 기능 정리 + 실습 해보기
- `도전과제` ’Streaming Serving , Batch Serving’ 동작이 가능한 이유와 내부 동작 정리해보기