- `질문` ***→ 학습을 하시고 스스로 아래 질문에 답변을 해보시기 바랍니다!***
    1. 에이전트(Agentic) 워크플로우가 등장하면서 모델 서빙에 대한 요구사항이 근본적으로 어떻게 달라지는가? (단일 요청-응답 구조와 달리 제어 루프 안에서 반복 호출되는 것이 서빙 시스템에 어떤 부담을 주는가?)
    2. 엔터프라이즈급 LLM 서빙 플랫폼의 계층형 아키텍처(Public API, 모델 선택/오케스트레이션, 리소스 관리, Core Inference, 모델 최적화 등)는 각 레이어가 어떤 역할과 트레이드오프를 가지며, 이를 오픈소스 스택(Kubernetes/Ray Serve)으로는 어떻게 구현하는가?
    3. "직접 구축 vs 클라우드 벤더 사용"은 이분법이 아니라 스펙트럼이라는 관점에서, 어떤 기준(사용 편의성, 비용, 커스터마이징, 트래픽 규모)으로 그 위치를 선택해야 하며, 이 선택의 타당성을 판단하기 위해 어떤 성능 지표(Latency: E2E/TTFT/ITL, Throughput: RPS·TPS)를 측정해야 하는가?
    
- `실습 환경 참고` : 로컬 PC로 실습가능(GPU 없이 실습 가능), AWS 계정(Bedrock API) 필요  + (옵션/실습:Kuberay) GPU 노드 1대 필요
- **챕터 4 소개**
    - 2~3장: 모델이 내부적으로 어떻게 동작하는지, 서빙 시스템을 밑바닥부터 어떻게 만드는지 ⇒ 4장:**실제 프로덕션 LLM 애플리케이션 서빙 시스템**
    - 실제 LLM 앱은 단순 request-response 한 번으로 끝나지 않고 에이전트 워크플로우 안에 내장되기 때문에, "모델 서빙"은 순수 추론 문제가 아니라 시스템 아키텍처 문제가 된다.
    - **4장의 4개 구성 요소**
        1. **에이전트 애플리케이션**
            - "에이전트 챕터"라서가 아니라, 에이전트가 요즘 LLM 기반 시스템을 만드는 기본 패턴이기 때문에 다룹니다.
            - 지식 어시스턴트, 코파일럿, 워크플로우 자동화, 추론 엔진 등 대부분이 에이전트형 구조를 따르고, 사용자 요청 하나가 여러 번의 LLM 호출·검색·도구 실행·반복 추론을 촉발합니다.
            - 이게 서빙 요구사항을 근본적으로 바꿉니다:
                - 토큰 사용량 증가
                - 체인으로 연결된 호출들에서 tail latency 증폭
                - 동적인 연산 패턴
                - 모델·도구 간 오케스트레이션 필요
            - 책 후반부에 나올 캐싱·배칭·메모리 관리·스케줄링·병렬화 같은 최적화 기법들이 전부 이 "에이전트 워크로드" 처리를 위함
        2. **계층형 레퍼런스 아키텍처**
            - 엔터프라이즈 LLM 서빙 플랫폼을 위한 상위 구조. "프로덕션급 시스템"을 가르는 요소들을 다룹니다. 예) 관측성 등.
        3. **빌드 vs 클라우드 선택**
            - 이분법이 아니라 스펙트럼으로 접근. 판단할 수 있는 사고 틀을 제공
        4. **핵심 성능 지표**
            - latency, throughput 등, 이 장의 모든 아키텍처 결정을 판단하는 잣대이자 이후 최적화 챕터(6~9장)의 토대가 되는 지표들.
        
    - **학습 목표 (챕터 종료 시점)**
        - 에이전트 워크플로우가 서빙 요구사항을 어떻게 바꾸는지 인식
        - 엔터프라이즈급 계층형 서빙 아키텍처와 그 트레이드오프 이해
        - 빌드 vs 클라우드 스펙트럼에서 실전 의사결정 프레임워크로 판단
        - 무엇을 측정해야 의도적으로 성능을 개선할 수 있는지 파악
    

### Model Serving in an Agentic World

- 에이전트 모델 서빙이 다른점 소개
    - 핵심 전환점
        - 앞선 챕터들(2~3장)에서는 **모델을 독립적인 예측 엔진으**로 다뤘습니다. **요청 하나에 추론 한 번, 응답 반환**.
        - 이번 절부터는 모델이 에이전트 시스템 안에 내장되면서 이 전제가 깨집니다:
            - **모델이 요청당 한 번이 아니라, 제어 루프(control loop) 안에서 반복 호출됨**
            - 그 루프 안에서 정보를 검색하고, 중간 결과를 추론하고, 도구를 실행하고, 출력을 다듬는 과정을 거쳐야 최종 답변이 나옴
    - 구조적 복잡도
        - 에이전트 하나만으로도 정교한 작업을 수행할 수 있지만, 실무에서는 여러 에이전트가 서로 위에 쌓이거나(build on top of one another), 협업하거나, 기능별로 특화되는 에이전트 네트워크/플랫폼 형태로 조직되는 경우가 많습니다.
        - 이런 계층 구조는 뛰어난 자율성을 주지만, 그만큼 설계·운영상 난제(특히 서빙 관점에서)를 만듭니다.
    - 서빙에 미치는 구체적 영향 : **사용자 상호작용 한 번이 다음을 촉발할 수 있습니다**
        - 다중 LLM 호출
        - 더 긴 컨텍스트 윈도우
        - 검색 연산 (RAG)
        - 메모리 재사용 (CAG)
    - 이 모든 게 토큰 사용량을 늘리고, 체인으로 연결된 호출들에서 지연시간을 증폭시키고, 트래픽 패턴을 더 동적으로 만듭니다.
    - 결과적으로 서빙 = 모델을 효율적으로 실행하는 것을 넘어, **오케스트레이션·메모리 관리·시스템 레벨 조정까지 지원**해야 하는 일이 됩니다.
    - 책 원문 번역
        - 이 섹션에서는 샘플 에이전트를 사용해 LLM을 활용하여 소프트웨어와 서비스가 상호작용하면서 동시에 자율적으로 작동하는 에이전트형 사용자 경험을 만드는 방법을 보여줍니다.
        - 이전 장들에서는 모델을 독립적인 예측 엔진으로 제공하는 데 초점을 맞췄지만, 현대의 LLM 활용에서는 모델이 에이전트 시스템 내부에 점점 더 깊이 통합되고 있습니다. 이러한 시스템에서는 모델이 요청당 한 번만 호출되는 것이 아닙니다. 대신, 정보를 수집하고 중간 결과를 분석하며 도구를 실행하고 출력물을 다듬은 뒤 최종 답변을 내놓는 제어 루프 내에서 반복적으로 호출될 수 있습니다. 이러한 변화는 모델 서비스 시스템에 요구되는 조건을 근본적으로 바꾸고 있습니다.
        - 에이전트는 강력하면서도 복잡합니다. 하나의 에이전트가 복잡한 작업을 수행할 수 있지만, 실제로는 여러 에이전트가 서로 위에 쌓이거나 협력하거나 각기 다른 기능을 전문으로 하는 에이전트 네트워크나 플랫폼으로 구성되는 경우가 많습니다. 이러한 계층적 아키텍처는 뛰어난 자율성을 가능하게 하지만, 특히 모델 서빙 측면에서 설계와 운영에 상당한 도전 과제를 동반합니다.
        - 예를 들어, 하나의 사용자 상호작용이 여러 번의 LLM 호출, 더 긴 컨텍스트 윈도우, 검색 연산(RAG), 또는 메모리 재사용(CAG)을 유발할 수 있습니다. 이러한 행위는 토큰 사용량을 증가시키고, 체인된 호출 간 지연 시간을 늘리며, 더 동적인 트래픽 패턴을 만듭니다. 따라서 서비스는 단순히 모델을 효율적으로 실행하는 것을 넘어서, 오케스트레이션, 메모리 관리, 시스템 수준의 조정을 지원해야 합니다.
        - 에이전트 개발 맥락에서 모델 서빙을 이해하는 데 도움을 주기 위해, 여기서는 기본 개념에 중점을 둡니다. 기본적인 에이전트를 예로 들어, 모델 서빙이 에이전트 자율성의 핵심 메커니즘을 어떻게 지원하는지 보여줍니다. 이 기초를 바탕으로 스스로 더 고급스럽고 다중 에이전트 시스템을 탐구하고 이해할 수 있는 역량이 향상될 것입니다.
    
- 에이전트의 정의
    - **에이전트의 정의** : 다음이 가능한 자율적인 LLM 기반 시스템으로 정의
        1. 상위 수준 목표를 이해
        2. 그 목표를 달성할 방법을 추론
        3. 외부 도구나 데이터 소스를 선택·호출
        4. 중간 결과를 바탕으로 적응·반복
        5. 사람 개입을 최소화(또는 아예 없이) 최종 결과물 산출
        
    - 에이전트 유형 예시
        - 리서치 에이전트: 논문을 읽고, 핵심 발견을 추출해 문헌 리뷰를 종합
        - 코딩 에이전트: 코드를 생성·리뷰·테스트·디버깅하고, 저장소로부터 배포까지 관리
        - 비즈니스 운영 에이전트: 데이터 입력을 자동화하고, 보고서를 생성해 이해관계자에게 배포
        
    - 핵심 차이: **전통적 어시스턴트 vs LLM 에이전트**
    - 규칙 기반 챗봇 같은 전통적 시스템은 개발자가 미리 짜둔 워크플로우나 사용자의 단계별 지시에 의존합니다.
    - 반면 LLM 기반 에이전트는 다음 능력 덕분에 복잡한 워크플로우를 독립적으로 실행할 수 있습니다:
        - 자연어 지시 해석
        - 추론 및 행동 계획
        - 도구 선택 및 사용
        - 환경/사람의 피드백에 적응
        - 컨텍스트와 사용자 선호도 유지
    - 즉 차이의 본질은 자율성입니다 : "무엇을 어떻게 할지"까지 시스템 스스로 판단한다는 점.
    
- Knowledge Agent : PDF 파일들을 질의·분석하는 지식 에이전트 코드 구현
    - **설계 특징**
        - 이식성(portability) 최우선
            - 로컬 모델 호스팅이나 별도 DB 없이, **OpenAI API(LLM 추론 + 임베딩 둘 다)**를 쓰고 **모든 정보는 인메모리에 저장**
        - 지식 베이스 = 로컬 PDF 폴더
            - **knowledge_files/에 PDF를 넣어두면 에이전트가 기동 시 자동으로 처리**합니다.
    - **지원 기능**
        1. 문서 질의(direct query) : 예: "5-level paging이 뭐고 어떻게 동작하나?"
        2. 복잡한 질문을 위한 지능형 플래닝
        3. 요약(summarization)
        4. 문서 간 분석/비교 : 예: "DB 쿼리 최적화와 자료구조 최적화를 상세 비교해줘"
    - **실행** : **python agent.py로 대화형 CLI**처럼 질문을 던지고 답을 받는 방식
        
        
    - 이 절에서는 실제 예를 통해 모델 서빙이 PDF 파일에서 정보를 조회하고 분석하도록 설계된 지식 에이전트를 어떻게 구동할 수 있는지 설명합니다.
    - 이 샘플 에이전트는 의도적으로 단순하지만, 모델 서빙 위에 에이전트를 구축하는 일반적인 아키텍처 패턴을 잘 보여줍니다.
    - 간단하게 하기 위해 이 지식 에이전트를 "Knowledge Agent"라고 부르겠습니다
    - 이식성을 극대화하기 위해 Knowledge Agent는 로컬 모델 호스팅과 데이터베이스를 사용하지 않습니다.
    - 대신, 그것은 **Open에 의존**합니다.
    - LLM 추론과 임베딩을 위한 AI의 API이며, 모든 정보를 메모리에 저장합니다.
    - 소스 코드와 설정 지침은 이 책의 GitHub 저장소 내 KnowledgeAgent 폴더에서 확인할 수 있습니다.
    - 이 장의 나머지 내용을 읽기 전에, 먼저 이 지침을 읽고 본인의 컴퓨터에 Knowledge Agent를 설치해 예제를 따라 해 보세요.
    - 더 깊이 이해하려면 직접 샘플 에이전트를 실행해 보고 다양한 유형의 질문을 시도해 보길 권장합니다.
    - 샘플 지식 에이전트는 문서 질의, 복잡한 질문에 대한 지능형 계획, 요약, 문서 분석을 지원합니다.
    - 지식 베이스는 로컬의 knowledge_files 폴더에 저장된 PDF 파일들로 구성되어 있습니다.
    - 이 **폴더에 본인의 PDF를 추가하면, 에이전트가 시작 시 자동으로 처리**합니다:
        
        ```bash
        ~/llm-model-serving/ch04/KnowledgeAgent/ **ls knowledge_files**
          5-Level Paging and 5-Level EPT.pdf
          A Brief Introduction to the SAL.pdf
          A Brief Tutorial on Database Queries.pdf
          ...
        ```
        
    - 에이전트가 실행되면 다양한 질문을 할 수 있습니다. 예를 들어 다음과 같은 직접 정보 쿼리가 될 수 있습니다:
        - "5단계 페이징이란 무엇이며 어떻게 작동하나요?"
        - "패트리샤는 무엇을 시도하며, 그것들은 어떻게 최적화되나요?"
        
    - 또한 다음과 같은 고급 요약 및 분석 작업일 수도 있습니다:
        - "이 기술들은 현대 컴퓨팅 시스템과 어떻게 관련이 있나요?"
        - "데이터베이스 쿼리 최적화와 데이터 구조 최적화 간의 상세 비교를 작성하십시오."
        
    - 다음 예시는 에이전트가 로컬에서 실행되는 모습을 보여줍니다:
        
        ```bash
        ~/llm-model-serving/ch04/KnowledgeAgent/ **python agent.py**
        Your question: **What are the main types of database queries discussed in the tutorial?**
        Response:
        This tutorial by Lutz Hamel explores the key tools used in modern
        relational database systems: database queries, data mining, and OLAP
        ...
        ```
        
    - 추가 예제는 README의 Example Queries 섹션에서 확인할 수 있습니다.
    
- **[옵션/실습]** Knowledge Agent - README.md **⇒ OpenAI API 키 필요**
    - **OpenAI API를 백엔드로 쓰는 RAG 기반 지식 에이전트 데모. 로컬 모델 없이 PDF 문서를 질의/분석.**
    - 구성 요소
        - `agent.py`(오케스트레이터) → `rag_system.py`(PDF 처리·임베딩·벡터 검색), `llm_manager.py`(OpenAI API/토큰 관리),
        - `planner.py`(LLM 기반 실행 계획 수립), `actions.py`(질의/요약/분석 등 액션 실행), `config.py`(중앙 설정).
        - 아키텍처는 **User Query → Agent → OpenAI API**로 단순하고, Agent가 내부적으로 4개 컴포넌트를 조율하는 구조.
        
        ```bash
        ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
        │   User Query    │───▶│     Agent       │───▶│   OpenAI API    │
        └─────────────────┘    └─────────────────┘    └─────────────────┘
                                      │
                                      ▼
                               ┌─────────────────┐
                               │   Components    │
                               │                 │
                               │ • **RAG System**    │
                               │ • LLM Manager   │
                               │ • Planner       │
                               │ • Actions       │
                               └─────────────────┘
        ```
        
    - **"5-Level Paging이 무엇인가?” 질문 시**
        
        ```mermaid
        sequenceDiagram
        
            participant U as User
            participant A as Agent
            participant P as Planner
            participant R as RAG
            participant L as LLM
        
            U->>A: 질문
        
            A->>P: 어떤 작업이 필요한가?
        
            P->>L: 실행 계획 생성 요청
            L-->>P: 검색 → 분석 → 요약
        
            P-->>A: 실행 계획
        
            A->>R: 관련 PDF 내용 검색
            R-->>A: 관련 Chunk
        
            A->>L: 질문 + 관련 문서
        
            L-->>A: 분석 결과
        
            A-->>U: 최종 답변
        ```
        
        - Agent는 관련 PDF 내용을 검색하고, 필요한 문맥을 LLM에게 전달해서 답을 만듭니다.
        - 이 Agent는 문서 질의, 요약, 분석, 여러 문서 간 비교 등을 지원하도록 설계되어 있습니다.
        - 여기서 중요한 것은 **LLM이 혼자 모든 것을 하는 게 아니라는 것**입니다.
            - *LLM = 생각하고 답을 생성*
            - *RAG = 필요한 자료 찾기*
            - *Planner = 작업 순서 결정*
            - *Agent = 전체 조정*
    - **테스트**
        - test_agent.py : 구조 검증, API 불필요
        - test_rag_system.py : 실제 RAG 파이프라인, API 필요
        - test_api_key.py : 키 유효성 진단
    - **비용/보안**
        - 임베딩 : ~$0.01–0.05/1000페이지, LLM 호출 : ~$0.10–0.50/쿼리 *← 실제 과금 발생*
        - .env는 절대 커밋 금지, 키 로테이션 권장
        
    - **Step 1: Setup Environment**
        
        ```bash
        # Clone the repository
        git clone <repository-url>
        cd KnowledgeAgent
        
        # Create and activate virtual environment
        python -m venv venv
        
        # On macOS/Linux:
        source venv/bin/activate
        
        # On Windows:
        # venv\Scripts\activate
        
        # Install dependencies in virtual environment
        pip install -r requirements.txt
        
        # Create environment file
        cp env_example.txt .env
        
        # Edit **.env** with your OpenAI API key
        OPENAI_API_KEY=your-actual-api-key-here
        ```
        
    - **python test_api_key.py 실행** : 소액 과금(최소 completion 1건 + embedding 1건 + 모델 목록 조회)이 발생, 키가 실제로 동작하는지 확인
        
        ```bash
        **python test_api_key.py**
        *...
        ✅ Valid OpenAI API key format
        
        🧪 Test 1: Testing completion API...
        ✅ Completion test passed: Hello, API test successful!
        
        🧪 Test 2: Testing embeddings API...
        ✅ Embeddings test passed: 1536 dimensions
        
        🧪 Test 3: Testing model access...
        ✅ GPT-4 available: True
        ✅ text-embedding-3-small available: True
        
        🎉 All API tests passed!*
        
        # API 키가 실제로 정상 동작합니다.
        - Completion API: 정상 응답 ("Hello, API test successful!")
        - Embeddings API: 정상 (1536차원 벡터)
        - 모델 접근 권한: GPT-4, text-embedding-3-small 둘 다 사용 가능
        ```
        
    - **python test_rag_system.py** 실행 : OpenAI API + 실제 PDF로 검증하는 통합 테스트 - 총 11개 테스트 메서드
        
        ```bash
        **테스트 분류**
        ...
        
        **11/11 전부 통과했습니다.
        ...**
        ```
        
    - **agent.py** : 4개 컴포넌트(RAGSystem, LLMManager, Planner, ActionExecutor)를 조율하는 Facade 역할의 오케스트레이터.
        
        ```bash
        # 코드 분석
        Agent.__init__: Config → RAGSystem/LLMManager/Planner/ActionExecutor 순으로 생성. 
        이 시점에 LLMManager 내부에서 OpenAI 클라이언트가 만들어지므로, 여기서부터 API 키가 필요합니다.
        
        # process_query(query, use_planning=True) — 핵심 진입점, 두 경로가 있습니다:
        - 플래닝 경로 (기본값): Planner.create_plan()이 LLM(GPT)에게 "이 질문에 어떤 액션들을 어떤 순서로 실행할지" JSON으로 계획을 짜게 시킵니다 ({"plan": [...], "reasoning": ..., "estimated_steps": ...}). 사용 가능한 액션은 4개뿐:
          - query_rag_with_context (RAG 검색 + 답변)
          - generate_profile_based_response (사용자 프로필 반영 답변)
          - generate_summary (요약)
          - generate_analysis (심층 분석)
        
        # LLM 응답 파싱이 실패하면 _create_fallback_plan()이 키워드 매칭("what/how"→RAG 1스텝, "summarize"→RAG+요약 2스텝, "analyze/compare"→RAG+분석 2스텝)으로 대체 계획을 만듭니다 — 플래닝 자체가 실패해도 완전히 멈추지 않는 방어적 설계입니다.
        - 비플래닝 경로 (use_planning=False): 플래닝을 건너뛰고 query_rag_with_context 하나만 바로 실행 — 빠르고 저렴한 대신 다단계 추론은 없음.
        _execute_action_sequence: 계획된 액션들을 순서대로 실행하면서 앞 액션의 결과(50자 이상일 때만)를 다음 액션의 context로 체이닝합니다. 즉 ["query_rag_with_context", "generate_summary"] 계획이면, 1단계는 RAG로 검색한 문서를 컨텍스트로 답변을 생성하고, 2단계는 그 답변 자체를 컨텍스트로 삼아 요약합니다 (원본 문서를 다시 검색하는 게 아님). 액션 단위로 try/except가 걸려 있어 한 스텝이 실패해도 에러 문자열만 결과에 남기고 나머지 스텝은 계속 진행됩니다.
        
        # 주의할 조용한 실패 지점: validate_action_prerequisites()는 len(self.rag_system.documents) > 0만 확인하는데, build_knowledge_base()를 먼저 호출하지 않으면(문서가 0개면) 모든 액션이 에러 없이 조용히 스킵되고 results가 빈 리스트로 나옵니다 — process_query가 success: True에 final_response: "No response generated"를 반환하므로, 겉보기엔 "성공했는데 답이 없다"는 헷갈리는 상태가 될 수 있습니다.
        
        # 최상위 안전망: process_query 전체가 try/except로 감싸져 있어 어떤 예외든 success: False + 에러 메시지 dict로 변환되고, interactive_mode()는 이 dict만 보고 성공/실패를 분기해 출력합니다 — 에이전트 프로세스 자체가 죽지 않습니다.
        
        # main(): .env 재로드(사실 config.py import 시 이미 한 번 로드되므로 약간 중복이지만, override=True라 최신값 보장 목적) → Agent() 생성 → build_knowledge_base()(PDF 42청크 임베딩, 실제 비용 발생 — 앞서 테스트에서 본 것과 동일) → interactive_mode() 진입.
        ```
        
    - **python agent.py** 로 실제 질의 : ***응답 하나에 실제로 발생한 API 호출 4회 확인!***
        
        ```bash
        #
        cd ch04/KnowledgeAgent
        source venv/bin/activate
        **python agent.py**
        ----------------------
        # .env 로드 메시지 확인
        # PDF 4개를 42청크로 임베딩 (임베딩 API 호출)
        # Your question: 프롬프트가 뜨면 자연어로 질문 입력
        # 내부적으로 플래닝 LLM 호출 1회 + 액션당 LLM 호출 1~2회가 실행된 뒤 ✅ Response:로 최종 답변 출력
        # quit 입력 시 종료
        
        # 첫번째 질문
        *💬 Your question:* **"What is 5-level paging and how does it work?"**
        *🔄 Processing...
        INFO:__main__:Processing query: What is 5-level paging and how does it work?
        INFO:planner:Creating plan for query: What is 5-level paging and how does it work?
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"**
        INFO:planner:Created plan: {'plan': ['generate_summary', 'generate_analysis'], 'reasoning': 'The plan begins with generating a concise summary to explain 5-level paging clearly, followed by an analysis to provide a detailed understanding of how it works. This approach ensures both a quick overview and an in-depth explanation.', 'estimated_steps': 2}
        INFO:__main__:Execution plan: {'plan': ['generate_summary', 'generate_analysis'], 'reasoning': 'The plan begins with generating a concise summary to explain 5-level paging clearly, followed by an analysis to provide a detailed understanding of how it works. This approach ensures both a quick overview and an in-depth explanation.', 'estimated_steps': 2}
        INFO:__main__:Action sequence: ['generate_summary', 'generate_analysis']
        INFO:__main__:Executing action 1/2: generate_summary
        INFO:actions:Executing action: generate_summary
        INFO:actions:Executing generate_summary action
        INFO:rag_system:Searching for query: What is 5-level paging and how does it work?
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"**
        INFO:rag_system:Found 5 relevant documents
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"**
        INFO:actions:Successfully generated summary
        INFO:__main__:Action generate_summary completed successfully
        INFO:__main__:Executing action 2/2: generate_analysis
        INFO:actions:Executing action: generate_analysis
        INFO:actions:Executing generate_analysis action
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"**
        INFO:actions:Successfully generated analysis
        INFO:__main__:Action generate_analysis completed successfully
        
         Response:
        Certainly! Here is a comprehensive analysis of 5-level paging based on the provided context:
        
        ---
        
        ### 1. **Overview of 5-Level Paging**
        
        **Definition:**
        5-level paging is an architectural enhancement introduced to extend the virtual address space beyond the traditional limits imposed by 4-level paging. It adds an additional hierarchical level (PML5) to the paging structure, thereby increasing the maximum linear address size from 48 bits to 57 bits.
        ...*
        ```
        
        ```bash
        # 실행 흐름 추적
        
        1) 지식 베이스 빌드: PDF 4개 → 42청크, 임베딩 API 1회 호출 — 이전 test_rag_system.py 실행 때와 동일한 패턴입니다.
        
        2) 플래닝 단계 (Planner.create_plan, chat/completions 1회 호출):
        plan: ['generate_summary', 'generate_analysis']
        reasoning: "요약으로 개요를 먼저 주고, 분석으로 상세 설명을 이어가겠다"
        여기서 주목할 점 — 이 질문("What is X and how does it work?")은 _create_fallback_plan()의 키워드 규칙대로라면 "what"/"how"에 매칭돼 ["query_rag_with_context"] 1스텝으로 처리됐어야 합니다. 하지만 실제로는 LLM 플래너가 살아있었기 때문에(폴백으로 안 떨어짐) generate_summary + generate_analysis 2스텝이라는, 하드코딩된 휴리스틱과는 다른 독자적 판단을 내렸습니다. "LLM 기반 플래닝이 규칙 기반보다 더 똑똑한 선택을 한다"는 걸 실제 로그로 확인한 셈입니다.
        
        3) 액션 1/2 — generate_summary:
        - context가 비어있으므로 rag_system.get_context_for_query() 호출 → 쿼리 임베딩 1회(POST .../embeddings) → 관련 문서 5개 검색
        - 검색된 컨텍스트로 요약 프롬프트 생성 → chat/completions 1회 → 요약 텍스트 생성
        
        4) 액션 2/2 — generate_analysis:
        - 로그를 보면 이 단계 직전에 embeddings 호출이 없습니다 — chat/completions 딱 1번만 있습니다. 이게 바로 지난번 코드 분석에서 짚었던 컨텍스트 체이닝이 실제로 일어난 증거입니다: generate_summary의 결과(50자 초과)가 context로 재사용되면서, generate_analysis는 원본 문서를 다시 검색하지 않고 방금 생성된 요약문 자체를 입력 삼아 분석을 작성했습니다.
        
        5) 최종 출력의 함정: process_query는 results-1만 final_response로 반환하고, interactive_mode()는 그것만 화면에 찍습니다. 즉 1단계(generate_summary)의 실제 출력 텍스트는 화면에 전혀 안 보였고, 내부적으로 2단계의 입력 재료로만 소비됐습니다 — 사용자는 최종 분석 결과만 봤지만, 실제로는 "먼저 요약 → 그 요약을 바탕으로 분석"이라는 2단계 추론이 뒤에서 일어난 것입니다.
        
        **# 응답 하나에 실제로 발생한 API 호출**
        ┌───────────────────────────┬──────┐
        │           호출             │ 횟수  │
        ├───────────────────────────┼──────┤
        │ chat/completions (**플래**닝)   │ 1    │
        ├───────────────────────────┼──────┤
        │ embeddings (**쿼리 검색**)      │ 1    │
        ├───────────────────────────┼──────┤
        │ chat/completions (**요약**)    │ 1    │
        ├───────────────────────────┼──────┤
        │ chat/completions (**분석**)    │ 1    │
        ├───────────────────────────┼──────┤
        │ **합계**                       │ **4회**  │
        └───────────────────────────┴──────┘
        ***INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"**
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"**
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"**
        **INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"***
        
        # 사용자가 던진 질문은 단 하나인데, 실제로는 LLM 호출 3번 + 임베딩 1번이 연쇄적으로 일어났습니다
        이게 정확히 4장 도입부에서 읽으셨던 "단일 사용자 상호작용이 다중 LLM 호출·토큰 사용량 증가를 촉발한다"는 서술의 실제 사례입니다. 
        단순 request-response 서빙과 달리, 이 한 번의 질의를 처리하는 데 서빙 백엔드가 4번의 왕복을 감당해야 했다는 뜻이고,
        이게 tail latency가 체인 호출마다 누적되는 이유이기도 합니다.
        
        # 응답 품질
        결과물은 PML5, 57비트 주소, canonical address 규칙, EPT, CR4.LA57 활성화 등 실제 Intel 문서(knowledge_files/5-Level Paging...pdf)의
        기술적 세부사항을 정확히 반영하고 있고, "Examples from the Context" 섹션에서 원문을 직접 인용하는 형태까지 보여줘서
        RAG grounding이 정상적으로 동작하고 있음을 확인할 수 있습니다.
        ```
        
        ```bash
        # 두번째 질문
        *💬 Your question:* **"Compare the optimization techniques mentioned across all documents"**
        ...
        ```
        
    
- (참고) RAG 동작 - 악분님, 상세 , 베이스라인 RAG 구현: 같은 검색, 다른 응답
    - **RAG와 Model Customization의 관계**
        - RAG는 외부 지식 주입에 강하다.
            - 최신 정보나 사내 문서를 빠르게 반영할 수 있다.
            - vector database만 갱신하면 모델 재학습 없이 지식을 갱신할 수 있다.
            - context window 제한 때문에 관련도 높은 조각만 넣는 방식이 중요하다.
                
                !An example of RAG pipeline
                
                An example of RAG pipeline
                
                ![https://ryusstory.tistory.com/entry/도메인-특화-LLM을-위한-세-가지-접근법-프롬프트-RAG-파인튜닝](attachment:92a284a2-f75b-469f-a4c6-a0fe130927e7:image.png)
                
                https://ryusstory.tistory.com/entry/도메인-특화-LLM을-위한-세-가지-접근법-프롬프트-RAG-파인튜닝
                
                - RAG는 knowledge base를 문서 처리와 embedding model을 통해 vector database에 저장하고, 사용자 질의 시 semantic similarity로 관련 context를 찾아 LLM 입력에 주입한다.
        
    - RAG 동작 단계
        
        !https://docs.aws.amazon.com/ko_kr/prescriptive-guidance/latest/retrieval-augmented-generation-options/what-is-rag.html
        
        https://docs.aws.amazon.com/ko_kr/prescriptive-guidance/latest/retrieval-augmented-generation-options/what-is-rag.html
        
    - **핵심: LLM 입장에서는 input이 길어질 뿐 - Blog**
        - RAG를 처음 접하면 “검색된 문서가 LLM 내부의 Q 행렬에 들어간다”거나 “RAG의 query와 attention의 Q는 같다”는 직관을 갖기 쉽다. *틀렸다*.
        - LLM 입장에서 RAG는 **단순히 prompt 텍스트가 길어진 것일 뿐**이다. 외부에서 검색했든, 사람이 직접 붙여넣었든, LLM은 구분하지 못한다. 아래 흐름을 보자.
        
        !https://malwareanalysis.tistory.com/930
        
        https://malwareanalysis.tistory.com/930
        
        !image.png
        
        ```python
        사용자 query: "회색 정장에 어울리는 셔츠 추천해줘"
                                    ↓
                 [embedding model — RAG 전용, 예: text-embedding-ada-002]
                                    ↓
                          query 벡터 (1536차원)
                                    ↓
                      [Vector DB — cosine similarity 검색]
                                    ↓
                top-5 문서 (셔츠 카탈로그 row 5개의 텍스트)
                                    ↓
        ─────────────────────────────────────────────────
        여기부터는 그냥 "텍스트 합치기" — 행렬 주입이 아님
        
        prompt = f"""
        {retrieved_doc_1_text}
        {retrieved_doc_2_text}
        ...
        {retrieved_doc_5_text}
        
        Question: 회색 정장에 어울리는 셔츠 추천해줘
        """
        ─────────────────────────────────────────────────
                                    ↓
                        [LLM (gpt-3.5-turbo 등)]
                                    ↓
                                  토큰화
                                    ↓
                    X (입력 임베딩 행렬, row가 그만큼 늘어남)
                                    ↓
                       평소와 똑같은 self-attention
                                    ↓
                                   응답
        ```
        
        - *비유하자면, RAG는 **오픈북 시험**이다. 매 시험(요청)마다 책(외부 DB)에서 찾아서 답안(prompt)에 첨부한다. 반대 방향의 접근인 Fine-tuning(파인튜닝)은 **암기** — 가중치에 지식을 내재화하는 방식이다.*
        
- Knowledge Agent의 구조 Design
    - 먼저 Knowledge Agent의 구조를 살펴보겠습니다. 그림 4-1은 그 주요 구성 요소들을 시각적으로 개괄적으로 보여줍니다.
        
        !Figure 4-1. Knowledge Agent system overview
        
        Figure 4-1. Knowledge Agent system overview
        
    - Knowledge Agent는 두 개의 OpenAI 모델로 역할 분리 동작
        - **text-embedding-3-small**: 텍스트를 의미를 담은 숫자 벡터로 변환 ***⇒ Emdedding***
            - 시맨틱 검색·검색(retrieval)·콘텐츠 매칭에 쓰임.
            - 방금 실행 로그에서 본 POST .../embeddings 호출들이 전부 이 모델 (PDF 42청크 벡터화, 사용자 쿼리 벡터화).
        - **gpt-4.1-nano**: 에이전트의 추론 및 언어 생성 엔진 ***⇒ LLM***
            - 지시를 해석하고, 다음 행동을 계획하고, 자연어 응답을 만듭니다
            - 로그의 POST .../chat/completions 호출 3번(플래닝 1 + 요약 1 + 분석 1) 이 모델.
        
    - 모델 외에도 Knowledge Agent는 다음과 같은 핵심 구성 요소들로 이루어져 있습니다:
        
        ```bash
        사용자 질문 → **Agent.process_query()**
                      ├─ **Planner** (gpt-4.1-nano) → 실행 계획 수립
                      └─ **ActionExecutor 순차 실행**
                            ├─ **RAGSystem** (text-embedding-3-small) → 관련 문서 검색
                            └─ **LLMManager** (gpt-4.1-nano) → 각 액션별 응답 생성
        ```
        
        - *Knowledge Agent (orchestrator)* : 모든 구성 요소를 조정하는 중앙 컨트롤러
            - 전체를 조율하는 중앙 컨트롤러 : process_query()가 플래닝 → 액션 실행 → 최종 응답까지 지휘
        - *Retrieval-augmented generation (RAG) system* : PDF를 처리하고, 임베딩을 생성하며, 벡터 검색을 수행합니다
            - PDF 처리(42청크로 분할), 임베딩 생성, 벡터 검색(search()) 수행
        - *Planner* : 사용자 쿼리를 위한 지능적인 실행 계획을 생성하기 위해 LLM을 활용합니다
            - LLM을 활용해 지능형 실행 계획 수립
            - "What is 5-level paging...” 질문에 generate_summary → generate_analysis 2단계 계획을 LLM 스스로 결정
        - *Actions (executor)* : 질의, 요약, 분석과 같은 특정 작업을 수행합니다
            - 질의/요약/분석 등 구체적 작업 실행 : 순차 실행되며 앞 결과를 다음 컨텍스트로 체이닝
        
    - Agent는 보통 다음 구성 요소를 가진다.
        - **LLM manager**: planning과 generation을 담당한다.
        - **Action registry**: agent가 호출 가능한 action 목록을 관리한다.
        - **RAG component**: 문서 검색과 context retrieval을 수행한다.
        - **Workflow executor**: plan에 따라 action을 순서대로 실행한
    
- The Agent’s Internal Workflow 에이전트의 내부 워크플로우
    - 이제 Knowledge Agent의 내부 로직을 살펴보겠습니다. 그림 4-2는 사용자 쿼리를 처리하는 워크플로우를 보여줍니다.
    - 그래프에 나타난 'LLM 서빙'은 액션 시나리오에 따라 동일한 LLM 모델일 수도, 서로 다른 모델일 수도 있다는 점에 유의하세요.
        
        !Figure 4-2. Knowledge Agent가 사용자 query에 응답하는 내부 workflow
        
        Figure 4-2. Knowledge Agent가 사용자 query에 응답하는 내부 workflow
        
    - 그림 4-2에 나와 있는 9단계 워크플로우를 단계별로 살펴보겠습니다:
    1. **사용자 질문 입력** : 예를 들어, "데이터베이스 쿼리 최적화와 데이터 구조 최적화 간의 상세 비교를 작성해 주세요.”
    2. **Agent → Planner 호출**해서 실행 계획 설계 요청 : 에이전트는 먼저 실행 계획을 설계하기 위해 자신의 **Planner** 컴포넌트를 **호출**합니다.
    3. **Planner → LLM 호출** :질문과 에이전트의 가용 액션들을 바탕으로 **실행 계획** 생성. 이 예시에서는 **3단계 실행 계획**이 나옴:
        
        ```bash
        {
          "plan": ["**query_rag_with_context**", "**generate_analysis**", "**generate_summary"**],
          "reasoning": "First, retrieving relevant contextual information ensures a comprehensive understanding...",
          "estimated_steps": 3
        }
        ```
        
        - ***3단계 sequential plan** : query_rag_with_context, generate_analysis, generate_summary*
            - ***RAG로 context를 찾고, analysis를 만들고, summary를 생성하는 순서***
    4. **ActionExecutor**가 **순서대로 실행(3단계)** 시작 : 먼저 action_query_rag_with_context를 처리.. (*actions.py 참고)*
    5. **1단계 query_rag_with_context**: RAG 시스템이 지식 베이스에서 관련 문서를 찾고(시맨틱 검색), 그 문서를 컨텍스트로 LLM이 답변을 생성. 
        
        ```bash
        Document 1 (Source: A Brief Tutorial on Database Queries, Data Mining, and OLAP ...):
        A Brief Tutorial on Database Queries, Data Mining, and OLAP
        ...
        ```
        
        - *RAG로 가져온 문서는 **analysis prompt에 들어간다***
    6. **2단계 generate_analysis**: 사용자 질문 + 5단계의 결과를 컨텍스트로 LLM에 전달해 더 심층적인 비교 분석 생성
    7. LLM이 질문과 컨텍스트를 바탕으로 심층 비교 분석을 만들어냄
    8. **3단계 generate_summary**: 직전 단계(분석)의 결과를 LLM에게 요약시켜 마무리
    9. Agent가 모든 **액션 출력을 종합해 최종 결과를 사용자에게 반환**
    
- Agent Autonomy 에이전트 자율성
    - **핵심 대비**: 절차적 실행 vs 목표 주도 자율성
        - 전통적 애플리케이션: 고정된 로직 + 사전 정의된 워크플로우로 명령을 절차적으로 실행
        - LLM 기반 에이전트: 사용자 의도를 해석 → 접근 방식을 스스로 선택 → 여러 도구를 통합 → 최소한의 개입으로 결과 전달 (= 목표 주도 자율성)
        
    - **액션(Actions) 정의**
        - 자율성을 가능케 하는 건 **재사용 가능**한 **이산적(discrete) 액션 집합**입니다.
            - *인공지능(AI)과 강화학습에서 선택할 수 있는 **행동(Action)의 가짓수가 딱 떨어지게 셀 수 있는 경우**를 말합니다.*
            - *연속적이지 않고 **서로 명확하게 구분**되는 유한한 개수의 행동들로 구성됩니다.*
                - *예시) 비디오 게임: 조이스틱 조작 (예: '점프', '공격', '왼쪽 이동', '오른쪽 이동')*
        - 이 샘플 에이전트에서는 각 액션이 "**LLM 호출 + 특화된 프롬프트 템플릿**"으로 구현됩니다.
        - 예시로 든 **create_analysis_prompt**는 우리가 이미 actions.py의 generate_analysis()에서 확인한 그 **프롬프트 생성 로직**입니다.
            
            ```python
            # 사용자의 쿼리와 이를 뒷받침하는 맥락을 바탕으로 구조화된 분석을 생성합니다:
            # Analysis prompt는 질문과 context를 결합해 LLM이 근거 기반 분석을 하도록 만든다.
            
            def **create_analysis_prompt**(self, query: str, context: str) -> str:
                prompt = f"""
            You are an expert analyst. Please provide a detailed
            analysis of the following question based on the
            provided context.
            
            Question: {query}
            
            Context:
            {context}
            
            Please provide:
            1. A comprehensive analysis
            2. Key insights and findings
            3. Relevant examples from the context
            4. Any limitations or gaps in the available information
            
            Analysis:
            """
                return prompt
            ```
            
            - *이 샘플 에이전트는 의도적으로 LLM 호출만 쓰는 단순한 구조를 유지합니다*
        - 에이전트의 액션이 **LLM 프롬프트에 국한되지 않는다!**
            - 도구 호출: 웹 검색, API 질의, DB 명령 실행
            - 시스템 연산: 파일 관리, 워크플로우 트리거, 외부 서비스 상호작용
            - 추론 단계: 사용자에게 직접 노출되지 않는 중간 계산/계획 서브루틴
    
    - **LLM 기반 플래닝** Planning with LLMs
        - Planner가 사전 정의된 워크플로우 대신 L**LM에게 고수준 지시를 해석**시켜 **서브태스크로 분해하고 최적 실행 경로를 결정**하게 함으로써,
        - **사용자**가 "PDF 파싱, 관련 섹션 찾기, 결과 요약" 같은 걸 **수동으로 안 해도 되게 만듭니**다.
            
            ```python
            # Planning 단계는 available actions를 기반으로 LLM에게 plan을 생성시키고 JSON response를 파싱한다.
            
            def create_plan(self, query: str) -> Dict[str, Any]:
              planning_prompt = self.llm_manager.create_planning_prompt(
                 query,
                 self.available_actions
              )
              plan_response = self.llm_manager.generate_response(
                 planning_prompt,
                 temperature=0.3
              )
              plan = self._parse_plan_response(plan_response)
              return plan
            ```
            
        
    - **Model Context Protocol (MCP**) : 도구 사용을 위한 대표적 표준화 접근법
        - LLM이 환경에서 사용 가능한 도구를 발견(discover)하고,
        - 구조화된 입력으로 호출(call)하고,
        - 결과를 추론 과정에 다시 반영하는 일관된 인터페이스 제공.
        - 도구 정의를 에이전트 핵심 로직과 분리해 개발을 단순화하고,
        - ad-hoc 프롬프트 엔지니어링의 취약성(brittleness) 문제를 완화.
        - *Model Context Protocol(MCP)은 agent가 외부 tool, data source, application과 표준 방식으로 연결되도록 돕는 프로토콜이다.*
        - *Agentic workflow가 늘어날수록 tool interface와 permission boundary가 중요해진다.*
    
- Retrieval-Augmented Generation (RAG) : 질문할 때 필요한 자료를 찾아서 LLM에게 같이 넣어주는 방법
    - RAG가 필요한 이유 : LLM 단독의 3가지 한계:
        1. 지식이 고정적 : 학습 데이터 컷오프 이후 정보 없음
        2. 환각(hallucination) : 그럴듯하지만 사실과 다른 내용 생성 가능
        3. 전문/최신 정보 부족 : 도메인 특화 지식 갭
        - ***RAG는 쿼리 시점에 외부 지식을 검색해 LLM에 주입함으로써 이 문제를 완화**합니다.*
        - *모델 내부 학습 데이터에만 의존하지 않고, **도메인 특화·최신 정보로 응답을 보강**합니다.*
        - *RAG는 L**LM이 자체 parameter memory만 의존하지 않고,** 외부 문서에서 관련 context를 검색해 답변하도록 만드는 방식이다.*
        
    - 그림 4-3은 기본 RAG 시스템의 두 가지 주요 워크플로우를 보여줍니다.
        
        !Figure 4-3. 기본 RAG system은 index building workflow와 query/retrieval workflow로 구성된다
        
        Figure 4-3. 기본 RAG system은 index building workflow와 query/retrieval workflow로 구성된다
        
    - **Index-building workflow 인덱스 빌딩 워크플로우 (오프라인 프로세스) : 먼저 PDF를 미리 처리합니다.**
    - 문서 정제/파싱 → 청킹(보통 ~1000토큰) → 청크별 임베딩 계산(사전에 대량으로, 벌크 배치 추론) → 벡터 DB에 저장.
    - 인덱스 빌딩 워크플로우(그림 4-3의 A 부분)는 **오프라인 데이터 처리 과정**으로, 일반적으로 **주기적으로 실행되도록 예약**됩니다.
        - *우리 샘플 에이전트는 이걸 단순화해서 매번 agent.py 기동 시 인메모리로 다시 빌드합니다.*
        - *우리가 테스트를 4번 돌릴 때마다 42개 청크를 매번 재임베딩했던 바로 그 이유*
    - 먼저 HTML이나 PDF 같은 형식의 **원시 지식 문서를 정제하고 파싱**하여 **일반 텍스트로 변환**합니다. 이 텍스트는 보통 각각 약 1,000 토큰 단위로 나누어진 **덩어리들로 분할**됩니다.
    - **청킹**(큰 콘텐츠를 더 작은 덩어리로 나누는 것)은 **단순한 임베딩 전처리 단계 이상**입니다. 이는 **검색의 세분화 정도**(시스템이 한 번에 고려할 수 있는 텍스트 양)를 **정의**하며, **오프라인 배치 추론**이 이루어지는 **단계 역할**을 합니다.
    - 전체 문서를 필요할 때마다 임베딩하는 대신, **시스템이 각 청크별 임베딩을 대량으로 미리 계산**해 쿼리 시점에 훨씬 빠르고 효율적으로 검색할 수 있게 합니다.
    - 청킹이 완료되면 각 구간은 임베딩 모델을 사용해 조**밀한 벡터 표현으로 인코딩**됩니다. 이렇게 생성된 청크 임베딩은 **벡터 데이터베이스에 인덱싱**되어 저장되며, 온라인 쿼리 과정에서 **효율적인 유사도 검색의 기반**이 됩니다.
        
        
    - **Fine (Small) Versus Coarse (Large) Chunking ‘작은 청킹’과 ‘큰 청킹’ 비교 트레이드오프**
        - 작은 청크: 검색 정밀도 ↑, 단 문맥 손실 위험
        - 큰 청크: 문맥 풍부, 단 관련 없는 내용 섞여 정밀도 ↓ (dilution)
        - *최적값은 도메인과 LLM 컨텍스트 윈도우에 따라 달라진다*
        
    - **Query/retrieval workflow 질의/검색 워크플로우(온라인 프로세스)**
    - 쿼리 텍스트 임베딩 → 벡터 DB에서 코사인 유사도로 최근접 벡터 검색 → 관련 청크 반환 → LLM에 쿼리+청크를 함께 전달해 답변 생성.
    - 쿼리 워크플로우(그림 4-3의 파트 B)는 고객이 상담원과 상호작용할 때 **실시간으로 이루어지는 온라인 프로세스**입니다.
    - 에이전트가 쿼리를 받으면, 먼저 임베딩 모델을 사용해 쿼리 텍스트의 임베딩 벡터를 얻습니다.
    - 그다음 코사인 유사도 같은 지표를 사용해 데이터베이스 내에서 쿼리 벡터와 가장 가까운 벡터들을 찾아냅니다.
    - 에이전트는 선택된 벡터를 사용해 벡터 데이터베이스에서 가장 관련성 높은 문서 조각을 찾아내고, 이를 사용자 쿼리와 함께 LLM에 전달해 답변을 생성하도록 합니다.
    - 그림 4-3은 단순하고 '기본적인’ RAG 파이프라인을 보여주지만, 실제 운영 환경의 RAG 시스템은 청킹, 랭킹, 중복 제거, 다중 소스 검색 같은 추가적인 복잡성을 포함합니다.
    - *Online 과정에서는 user query를 embedding하고, vector search로 관련 chunk를 찾고, 그 chunk를 prompt context로 넣어 LLM response를 생성한다.*
    - *텍스트를 작은 chunk로 나누는 이유는 retrieval 단위의 정확도를 높이고, context window를 효율적으로 쓰기 위해서다.*
        
        
    - **Why Split Text into Small Chunks? 왜 텍스트를 작은 덩어리로 나눌까요? 왜 청킹이 필요한가?**
        - *LLM은 입출력 합산 토큰 수에 상한(컨텍스트 윈도우)이 있기 때문에, 문서 전체가 아니라 가장 관련성 높은 청크 몇 개만 골라 보내야 합니다*
        - LLM은 입력과 출력 토큰을 포함해 한 번에 처리할 수 있는 **최대 토큰 수에 제한**이 있습니다. 이는 **맥락을 담을 공간이 제한적**이라는 뜻입니다.
        - 그 공간을 **컨텍스트 윈도우**라고 합니다. 이러한 제약을 고려해 RAG는 추출한 텍스트를 더 작고 이해하기 쉬운 조각들로 나누어, LLM에 전달되는 문맥은 **관련성이 높은 일부 조각만 전송합**니다.
    
- Cache-Augmented Generation (CAG) : 미리 긴 Context를 LLM에 입력해 계산하고, 해당 Knowledge의 Context/KV Cache를 재사용
    - 이전 섹션에서는 RAG가 외부 지식 소스를 통합하여 언어 모델을 어떻게 향상시키는지 살펴보았습니다. 강력한 만큼 RAG는 몇 가지 과제도 함께 가져옵니다.
    - **RAG의 한계**
        - **추가 지연시간**: LLM 호출 전에 검색 단계가 끼어듦, "쿼리 임베딩 → 코사인 유사도 검색" 과정 자체가 지연 요인
        - **선택 오류 위험**: 제한된 토큰 안에서 "가장 관련 있는" 문서만 골라야 하는데, 잘못 고를 수 있음
        - **시스템 복잡도**: 임베딩·인덱스·벡터 DB를 구축/유지해야 하는 부담
            
            
    - **CAG의 등장 배경: 커진 컨텍스트 윈도우**
        - Claude Sonnet 4(2025년 8월 기준) 같은 모델이 100만 토큰 컨텍스트를 지원하게 되면서, "몇 개만 골라 넣는다"는 RAG의 전제 자체가 흔들립니다.
        - 지식 베이스 전체(또는 상당 부분)를 통째로 컨텍스트에 넣을 수 있다면, 굳이 복잡한 검색 시스템 없이도 LLM의 고질적 한계(정적 지식, 환각, 도메인 갭)를 해결할 수 있다는 것.
        
    - **CAG란**
        - *쿼리 시점에 검색하는 대신, 지식을 미리 LLM의 KV 캐시에 프리로드해두고 추론 시 그 캐시된 컨텍스트로 바로 답하는 방식입니다.*
        - *→ 검색 지연 제거 + 시스템 복잡도 감소, 그러면서도 외부 지식 기반 응답은 유지.*
        - 캐시 증강 생성(CAG)은 최신 LLM의 확장된 문맥 창을 활용해 **지식을 모델의 KV 캐시에 직접 미리 로드**합니다.
        - CAG는 질의 시점에 검색을 수행하는 대신, 관련 자원을 미리 로드해 두어 **추론 중에 캐시된 문맥을 활용해 답변을 생성**할 수 있도록 합니다.
        - 이 방법은 검색 지연을 없애고 시스템 복잡성을 줄이면서도, LLM이 외부 지식에 기반해 답변을 생성할 수 있도록 합니다.
        
    - 그림 4-4는 **RAG 시스템과 CAG 시스템을 비교**합니다.
        
        !Figure 4-4. RAG와 CAG 비교
        
        Figure 4-4. RAG와 CAG 비교
        
        - RAG: 쿼리마다 매번 동적으로 검색 프로세스 실행
        - CAG: 지식 문서를 한 번 캐시에 로드해두면, 이후 쿼리는 그 캐시된 컨텍스트로 바로 응답
        
    - RAG에서는 모든 쿼리가 동적으로 문맥을 찾기 위한 검색 과정을 촉발하는 반면, CAG에서는 지식 문서가 LLM 캐시에 로드되면 문맥 내 외부 지식을 활용해 쿼리에 직접 답변합니다.
    - 이러한 개선은 그림 4-5에 나타난 것처럼 에이전트 설계를 크게 단순화합니다.
        
        !Figure 4-5. CAG를 사용하는 agent workflow
        
        Figure 4-5. CAG를 사용하는 agent workflow
        
    - **CAG의 대가**
        - 큰 컨텍스트 윈도우 + 캐시 관리는 메모리/연산 요구량을 늘립니다 → 이걸 최적화하는 기법은 7장에서 다룸
        
    - 결론: RAG vs CAG, 양자택일이 아니다
        - **RAG는 동적 검색과 최신성**에 강하고, **CAG는 반복 query나 고정 knowledge set에서 latency를 줄이는 데 유리**하다.
        - RAG = 검색으로 외부 지식을 프롬프트에 확장 → 답변 품질(지식 접지·최신성) 개선
        - CAG = 이미 계산된 컨텍스트를 재사용해 중복 KV 캐시 연산 감소 → 서빙 효율(지연시간·처리량·비용) 개선
        - *RAG로 입력을 보강하고, CAG로 실행을 최적화하는 조합*
    
- Agent가 Model Serving을 사용하는 방식 How Agents Use Model Serving
    - **autonomous agents 자율 에이전트**는 작업을 완료하기 위해 여러 모델과 도구를 조율해야 하는 경우가 많습니다. 대표적인 구성 요소는 다음과 같습니다:
        - LLM : 추론, 계획, 대화 생성
        - 임베딩 모델 : 검색, 유사도 매칭, 시맨틱 매칭
        - 비전/음성 모델 : 멀티모달 인식
        - 태스크 전용 모델 : 코드 생성, 분류, 요약
        - 외부 도구 : API, DB, 서비스 (필요시 호출)
        
    - 현대 에이전트의 핵심 기능 중 하나는 **도구 호출**입니다. 툴 호출은 네 단계로 이루어진 과정입니다:
        
        ```mermaid
        sequenceDiagram
        
            participant U as User
            participant A as Agent
            participant L as LLM
            participant T as Tool
        
            U->>A: 질문
        
            A->>L: 질문 + 사용 가능한 Tool
        
            L-->>A: Tool 선택 + JSON arguments
        
            A->>T: Tool 실행
        
            T-->>A: Result
        
            A->>L: Tool Result 전달
        
            L-->>A: 다음 판단 / 최종 답변
        
            A-->>U: Answer
        ```
        
        1. LLM이 사용자 요청과 사용 가능한 도구들을 놓고 추론
        2. 선택한 도구에 필요한 입력을 인코딩한 구조화된 출력(보통 JSON)을 생성
        3. 에이전트가 그 도구 호출을 실제로 실행
        4. 결과를 다시 LLM에 넣고, 작업이 끝날 때까지 반복(iterate)
        - *이 패턴 덕분에 에이전트는 순수 텍스트 생성을 넘어 정밀한 도구 실행과 추론을 결합할 수 있습니다.*
        
    - 이 모든 모델·도구는 결국 **HTTP/gRPC API 같은 모델 서빙 서비스**를 통해 **온디맨드로 호출**됩니다.
    - 에이전트가 상호작용형·실시간으로 동작하기 때문에, 고**성능·저지연·비용 효율적인 서빙**이 **에이전트 애플리케이션 성공의 핵심 조건**입니다.
    - 이제 에이전트 기반 애플리케이션에서 모델과 도구가 어떻게 사용되는지 살펴보았으니, 이 장의 나머지 부분에서는 실제 서비스에 사용되는 프로덕션급 모델 구축을 위한 다양한 접근법을 탐구할 것입니다.

### LLM Serving in Enterprise Systems: An Overview

- 들어가며
    - 이 섹션에서는 Open과 같은 주요 공급업체들이 채택한 추상적인 계층형 아키텍처를 소개합니다.
    - 핵심 메시지: **"모델 실행"과 "엔터프라이즈 서빙"은 다른 문제다!**
        - 지금까지(2~4장 앞부분) 우리가 만든 것들 “단일 모델 서빙, 멀티모델 서빙(Triton 포함), 샘플 RAG 에이전트” 은 모두 "모델을 호스팅하고 실행한다"는 좁은 의미의 서빙이었습니다.
        - 이 절은 그 위에 실제 대규모 프로바이더가 추가로 감당해야 하는 것들을 나열합니다:
            - 인증(authentication)
            - 과금 정책(pricing)
            - 리소스 관리
            - 네트워킹
            - 최적화
            - 실험(experimentation, 즉 A/B 테스트 등)
            - 관측성(observability)
            - 온콜 지원
        
    - 위와 같은 아키텍처링이 어려운 이유 : 기술적인 것보다 조직적인 것에 가깝습니다
        - 서로 다른 책임을 가진 여러 팀이 병목이나 과도한 상호 의존성 없이 하나의 진화하는 시스템에 동시에 기여할 수 있어야 함
        - 빠른 반복(iteration)과 안정성 사이의 균형
        - 이 모든 걸 비용, 신뢰성, 사용자 경험이라는 제약 안에서 해내야 함
        - *즉, 서빙 아키텍처를 잘 설계한다는 건 단순히 "레이턴시를 줄이는 기술"의 문제가 아니라, "어떤 레이어를 누가 소유하고, 레이어 간 경계를 어떻게 그어야 여러 팀이 서로 발목 잡지 않고 일할 수 있는가"라는 조직 설계 문제이기도 하다.*
        
    - 그림 4-6은 실제로 **계층형 엔터프라이즈 모델 서빙 아키텍처**가 어떻게 구성되는지를 보여줍니다.
    - 이러한 개념적 관점은 각 계층에서 발생하는 고유한 요구사항과 과제를 부각시킵니다.
        
        !Figure 4-6. Enterprise-level model serving system architecture
        
        Figure 4-6. Enterprise-level model serving system architecture
        
    
- 계층형 엔터프라이즈 모델 서빙 아키텍처
    
    !Figure 4-6. Enterprise-level model serving system architecture
    
    Figure 4-6. Enterprise-level model serving system architecture
    
- 레이어: 1. Public API
    - 공개 API는 고객, 개발자, 그리고 내부 서비스가 LLM 시스템과 상호작용하는 주요 외부 인터페이스입니다.
    - 네트워킹, 인증, 가격 책정, 속도 제한, 요청 라우팅을 관리합니다.
    - 역할: 고객/개발자/내부 서비스가 접하는 외부 인터페이스. 네트워킹·인증·과금·rate limiting·요청 라우팅 관리
        
        ```python
        # 외부 고객이 만나는 입구입니다.
        Internet
           ↓
        **Authentication
        Rate Limit
        Tenant
        Billing
        Routing**
           ↓
        LLM
        
        # 주요 고민은:
        수많은 연결 처리
        인증
        Quota
        과금
        DDoS/보안
        Global Routing
        ```
        
    - 핵심 난제:
        - *High concurrency* 수백만 동시 연결 처리 (고동시성)
        - *Fair usage and monetization* 쿼터/어뷰징 방지/정확한 과금 (공정 사용·수익화)
        - *Low-latency global access* 지역 라우팅·캐싱으로 최근접 리전 서빙 (저지연 글로벌 접근)
        - *Security* 인증·테넌트 격리·네트워크 공격 방어 (보안)
    
- 레이어: 2. Resource Management
    - 이 계층은 모델, 사용 사례, 고객 워크로드를 여러 리전에서 서비스하기 위해 필요한 인프라 하드웨어 자원(예: CPU, GPU, 메모리, 디스크, 네트워킹)을 관리합니다.
    - 예산 검토와 비용 배분은 여기에서 자주 통합됩니다.
    - 역할: CPU/GPU/메모리/디스크/네트워킹 같은 인프라 하드웨어를 리전 전반에서 관리, 예산/비용 배분 통합
        
        ```python
        # GPU를 관리하는 층 : 예)
        GPU Cluster
        H100
        H200
        B200
        L40S
        ...
        
        # 여기서 고민하는 것은:
        누구에게 GPU를 줄 것인가?
        몇 대가 필요한가?
        GPU가 놀고 있지는 않은가?
        중요 고객 요청을 우선 처리할 것인가?
        ```
        
    - 핵심 난제:
        - *Capacity planning* 수요 예측 및 과다 프로비저닝 방지(용량 계획)
        - *GPU utilization* 데이터센터 전반의 이기종 GPU 풀 고가동률 유지(GPU 활용률)
        - *Customer prioritization* 중요 워크로드에 쿼터/예약을 강제하면서 저우선순위는 선점 가능하게 스케줄링(고객 우선순위)
    
- 레이어: 3. Model Selection & Orchestration
    - 오케스트레이션 계층은 각 요청에 어떤 모델을 사용할지 결정하며, 정확도, 지연 시간, 비용의 균형을 맞춥니다.
    - 단일 모델 선택을 넘어서, 이 계층은 예측 디코딩을 적용하거나 모델 패밀리 간 라우팅을 수행하는 등 여러 모델을 동시에 조율할 수 있습니다.
    - 역할: 요청마다 어떤 모델(들)을 쓸지 결정, 정확도/지연/비용 균형. 여러 모델을 함께 오케스트레이션(**스펙큘레이티브 디코딩 speculative decoding** , **모델 패밀리 model families 간 라우팅** 등)도 여기서.
        
        ```python
        # 모든 질문에 가장 비싼 모델을 쓰면 비용이 많이 듭니다.
        예를 들어: "1+1?" 에 거대한 Reasoning Model을 쓸 필요는 없습니다.
        
        # 그래서 아래 처럼 선택합니다.
        단순 질문
         ↓
        Small Model
        
        복잡한 Reasoning
         ↓
        Large Model
        
        # 여기에는 세 요소의 Trade-off가 있습니다
        Quality
        Latency
        Cost
        ```
        
    - 핵심 난제:
        - *Cost–quality trade-offs* 모든 작업에 최대 모델이 필요한 건 아님(예: OpenAI가 기본값으로 gpt-4o-mini 사용) → 쿼리를 이해해서 triaging해야 함(비용-품질 트레이드오프)
        - *Load balancing* 모델 풀 전반에 트래픽 분산(로드 밸런싱)
        - *Latency-sensitive use cases* 지연에 민감한 케이스엔 더 작고 빠른 모델이나 스펙큘레이티브 디코딩 적용
            - *스펙큘레이티브 디코딩 = ch07에서 상세히 다룰 예정*
    
- 레이어: 4. Distributed Serving
    - 이 계층은 LLM 모델 실행을 위한 분산 인프라를 구축합니다.
    - 이는 일반적으로 두 가지 그룹으로 나뉘는데, 대형 모델을 위한 분산 모델 호스팅과 불필요한 계산을 줄이기 위한 분산 캐싱(예: KV 캐싱, 프롬프트 캐싱, 시맨틱 캐싱)입니다.
    - 역할: 분산 실행 인프라 구성:
        - (a) 대형 모델을 위한 분산 호스팅
        - (b) KV 캐시·프롬프트 캐시·시맨틱 캐시 같은 분산 캐싱으로 중복 연산 감소 *= ch07의 LMCache 실습과 직결*
        
        ```python
        # 모델이 커지면 GPU 하나에 안 들어갑니다.
        예:
        Model Weight = 160 GB
        GPU VRAM = 80 GB
        
        # 그러면 최소한 여러 GPU로 나눠야 합니다.
        GPU 0
        GPU 1
        
        # 이 Layer에서는 아래를 관리합니다
        Multi-GPU
        Multi-Node
        KV Cache
        Prompt Cache
        Cache-aware Routing
        ```
        
    - 핵심 난제:
        - *Hardware limitations* 모델 크기가 단일 GPU 메모리 초과(하드웨어 한계)
        - *Multi-GPU and multi-node coordination* 멀티GPU/멀티노드가 요청 컨텍스트를 효율적으로 공유해 SLA 유지(코디네이션)
        - *Caching for efficiency* KV-캐시 인식 라우팅으로 중복 추론 감소(캐싱 효율)
    
- 레이어: 5. Core Inference
    - 역할: 모델이 실제로 실행되는 곳. vLLM/Triton/TensorRT-LLM/SGLang 같은 서빙 프레임워크 + FlashAttention/GEMM/PagedAttention 같은 최적화 커널을 웹 엔드포인트로 노출
        
        ```python
        # 실제 Model 계산이 일어나는 부분
        # 예로 든 Framework는:
        vLLM
        Triton
        TensorRT-LLM
        SGLang
        
        # 최적화가 사용
        FlashAttention
        GEMM
        PagedAttention
        
        # 쉽게 말하면 아래에서 vLLM 이하의 실제 추론 Engine 영역입니다.
        Application
             ↓
        Orchestration
             ↓
        **vLLM**
             ↓
        **CUDA Kernel**
             ↓
        **GPU**
        ```
        
    - 핵심 난제: (3장에서 이미 상세히 다룸)
        - 모델별 dependency와 framework가 다를 수 있다.
        - model load/unload가 latency spike를 만든다.
        - hot model과 cold model의 traffic 차이가 크다.
        - 모델 cache eviction 정책이 성능과 비용에 직접 영향을 준다.
        - 보안, 격리, observability가 single-model보다 복잡하다.
        - ***Cold start latency***
        - ***Hot model scaling***
    
- 레이어: 6. Model Optimization
    - 이 레이어는 처음부터 다시 학습하지 않고도 모델의 성능과 효율을 향상시키기 위해 다양한 모델 최적화 기법을 적용하는 데 중점을 둡니다.
    - 역할: 재학습 없이 성능/효율을 높이는 다양한 최적화 기법 적용
    - 핵심 난제: (5, 6, 7, 9장에서 다룸)
        - ch06(양자화), ch07(스펙큘레이티브 디코딩, LMCache), ch09(Qwen3-14B 종단간 최적화)
    
- 레이어: 7. Model & 마무리
    - 역할: 실제 학습된 모델을 서빙 시스템에 공급:
        - 모델을 내부 학습 파이프라인이나 외부 소스에서 운영 환경으로 이동시킵니다
        - 모델을 기능(음성, 추론, 비디오)과 목적(샌드박스, 실험, 실제 운영)에 따라 분류합니다
        - 모델이 발전함에 따라 추적과 버전 관리를 담당합니다
        
    - 이 분야가 발전함에 따라 새로운 모델과 기술이 시스템 설계를 재편할 것입니다.
    - 하지만 API, 오케스트레이션, 추론, 최적화 같은 관심사를 분리하는 계층형 아키텍처 패턴은 여전히 필수적입니다.
    - 서로 다른 역할을 맡은 팀들이 독립적으로 혁신하고 최적화하면서도 통합된 서비스 플랫폼에 기여할 수 있게 합니다.

### Building with an Open Source Stack

- **오픈 소스 스택으로 개발하기 개요** : Kubernetes 위에 전체 스택을 올린다!
    - 이 절에서는 우리가 선호하는 오픈 소스 소프트웨어 구성 요소들을 사용해 엔터프라이즈 모델 서비스 시스템을 구현하는 방법을 다룹니다.
    - 목표는 단일한 해결책을 제시하는 것이 아니라, 실용적인 설계 선택을 보여주고 여러분이 직접 **서빙 플랫폼**을 만들 수 있는 출발점을 제공하는 데 있습니다.
        
        
    - 먼저, 그림 4-7은 시스템에 대한 간단한 개요를 제공합니다.
        
        !Figure 4-7. Open source stack으로 model serving 구현
        
        Figure 4-7. Open source stack으로 model serving 구현
        
    - 이 설계(그림 4-7)의 근간은 Kubernetes입니다. 컨테이너화된 애플리케이션의 배포·스케일링·관리를 자동화하는 오픈소스 플랫폼인데, 저자들이 이걸 선택한 이유는 두 가지입니다:
        1. 핵심 기능 자체: 배포/스케일링/관리 자동화
        2. 거대한 생태계: 그 위에 쌓인 메트릭, 로깅, 네트워킹, 인가(authorization), 하드웨어 관리 등 부가 기능들
        - *이 두 가지 덕분에 Kubernetes는 AWS·GCP·Azure 같은 클라우드 프로바이더와 OpenAI·Anthropic 같은 파운데이션 모델 벤더 모두의 백본으로 널리 채택됐다.*
        
    - Kubernetes + 생태계가 담당하는 것 (그림 4-7)
        - 리소스 관리
        - 네트워킹
        - 트래픽 라우팅 및 로드 밸런싱
        - 서비스 호스팅 및 스케일링
        - 서비스 메트릭 및 모니터링
        
        !mermaid-diagram.png
        
    - Kubernetes 한 층이 사실상 레이어 1(Public API)의 라우팅/네트워킹 부분과 레이어 2(Resource Management) 전체를 실제 오픈소스 컴포넌트로 구현해주는 기반 계층 역할을 합니다
    
- **Implementing Public API 퍼블릭 API 구현하기**
    - Public API 레이어의 4가지 난제(고동시성, 공정 사용/수익화, 저지연 글로벌 접근, 보안)를 실제 FastAPI + Kubernetes 코드로 구현하는 예시
        - API layer는 tenant 인증, rate limit, routing, request validation을 담당한다
        
    1. FastAPI 채팅 **엔드포인트** + **인증 의존성** 주입
        
        ```python
        @app.post("**/v1/chat/completions**")
        async def chat(req: ChatReq, idp=**Depends(require_auth)**):
            await **rate_limit**(idp["tenant"])
            # select model, route traffic based on tenant information
        ```
        
        - FastAPI의 Depends()로 인증 로직(require_auth)을 엔드포인트에 선언적으로 주입합니다
        - 라우트 핸들러 코드 자체는 "인증된 테넌트 정보(idp)를 받아 요율 제한(rate_limit)을 걸고, 그 테넌트 정보로 모델 선택/트래픽 라우팅을 한다"는 비즈니스 로직에만 집중할 수 있습니다.
        
    2. **인증 방식** : JWT 또는 API 키
        - 사용자 요청을 인증하고 승인하기 위해 JWT 토큰이나 API 키 중 하나를 사용.
        - 이 과정에서 플랫폼은 쿼터 집행, 트래픽 라우팅, 모델 선택과 같은 후속 단계에 필수적인 고객 메타데이터도 함께 가져옵니다:
        
        ```python
        # authorize request either with JWT or api_key
        async def require_auth(api_key=Depends(**verify_api_key**), claims=Depends(**verify_jwt**)):
            if not api_key and not claims:
                raise HTTPException(401, "Missing API key or JWT")
            tenant = claims.get("tenant") if claims else await rds.hget(f"keys:{api_key}", "tenant")
            if not tenant: raise HTTPException(403, "Unknown tenant")
            return {**"tenant": tenant**, "claims": claims, "api_key": api_key}
        ```
        
        - JWT 경로: **verify_jwt**가 Authorization: Bearer ... 헤더를 파싱해 RSA 공개키(JWK)로 서명 검증 + audience/만료(verify_exp) 확인 → 토큰 클레임에서 바로 tenant 추출
        - API 키 경로: **verify_api_key**로 받은 키를 Redis(rds.hget)에서 조회해 tenant를 역참조
        - 둘 다 없으면 401(인증 정보 없음), 있어도 테넌트를 못 찾으면 403(알 수 없는 테넌트)
        - 두 인증 방식 모두 최종적으로 "테넌트 식별"이라는 같은 목적지로 수렴하는 게 핵심입니다.
        - 이후 단계(쿼터 강제, 트래픽 라우팅, 모델 선택)가 전부 이 tenant 값 하나에 의존하기 때문입니다.
        
    3. **Kubernetes HPA** (고동시성 대응) : 파드 오토스케일링
        
        ```python
        apiVersion: autoscaling/v2
        kind: **HorizontalPodAutoscaler**
        metadata: { name: enterprise-model-api-hpa }
        spec:
          **scaleTargetRef:** { apiVersion: apps/v1, 
              kind: Deployment, name: **enterprise-model-api** }
          **minReplicas: 3
          maxReplicas: 15**
          metrics:
          - type: Resource
            resource: { name: **cpu**, target: { type: Utilization, **averageUtilization: 70** } }
        ```
        
        - enterprise-model-api deployment 의 평균 CPU 사용률이 70%를 넘으면 Kubernetes가 자동으로 인스턴스를 3개→최대 15개까지 수평 확장합니다.
        
    4. **Ingress 레벨 rate limiting** (공정 사용/어뷰징 방지)
        
        ```python
        apiVersion: networking.k8s.io/v1
        kind: **Ingress**
        metadata:
          name: api-ingress
          annotations:
            kubernetes.io/ingress.class: nginx
            # rate limit the traffic to 50 request per second max : 초당 50개 요청 제한
            **nginx.ingress.kubernetes.io/limit-rps: "50"
            nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"**
            nginx.ingress.kubernetes.io/proxy-body-size: "8m"
        spec:
          rules:
          - host: api.yourorg.example
            http:
              paths:
              - path: /
                pathType: Prefix
                backend: {service: { name: enterprise-model-api, port: { number: 80 } } }
        ```
        
        - Nginx(또는 Envoy) 인그레스가 초당 50건, 버스트는 5배(순간적으로 최대 250건)까지만 허용하도록 트래픽을 제한합니다.
        - (참고) rate limiting이 두 레이어에서 이중으로 걸려 있습니다
            1. 애플리케이션 코드 안의 rate_limit(idp["tenant"])(테넌트별 세밀한 쿼터)
            2. 인그레스의 limit-rps(전체 서비스 단위의 거친 방어선)
            - *이건 흔한 "defense in depth" 패턴:*
                - *인그레스 레벨 제한은 애플리케이션 코드까지 도달하기 전에 대량 어뷰징/DDoS성 트래픽을 값싸게 걸러내고,*
                - *애플리케이션 레벨 제한은 테넌트별 계약(쿼터)을 정교하게 강제합니다.*
    
- **Implementing Model Selection 모델 선택 구현하기**
    - Public API 다음으로, 모델 선택 단계에 대해 살펴보겠습니다. 요구사항에 따라 모델 선택 로직을 어디에 둘 것인가?
        - **Public API**, **별도의 서비스(미들웨어)**, 또는 **정적 라우팅 설정**에 **구현**할 수 있습니다.
        
    - 간소화된 예시에서는 모델 선택 로직이 **Public API** 서비스의 채팅 엔드포인트(`/v1/chat/completions`) 내에 **구현**되어 있습니다.
    - 들어오는 요청의 **토큰 크기에 따라 시스템**은 다음 두 가지 중 하나를 수행합니다:
        - **요청을 선택한 모델 백엔드로 직접 전달**합니다
        - **speculative decoding 추측 디코딩** 방식을 사용해, **더 빠르고 저렴한 모델**이 여러 미래 토큰을 생성하면, 느리지만 더 정확한 모델이 대량으로 이를 검증합니다. 이 방법은 중복된 단계별 생성을 피하고 지연 시간을 크게 개선합니다.
        - *(우리는 7장에서 추측적 디코딩을 더 자세히 탐구할 것입니다.)*
    - `chat() 엔드포인트`에 추가된 로직 : 들어온 요청의 토큰 크기 기준으로 두 경로 중 하나를 택하는 "기초 분류기"입니다:
        
        ```python
        @app.post("/v1/chat/completions")
        async def chat(req: ChatReq, idp=Depends(require_auth)):
            await rate_limit(idp["tenant"])
            # choose the right model for the given request
            ep = choose_endpoint(req.model, idp["tenant"])
        	
            # basic classifier: use speculation for long outputs, else direct
            if **req.model.draft_enabled** and **req.max_new_tokens > 1024**:
                draft_ep = config.get_draft_endpoint(req.model)
                # use draft model for generation, target model for validation
                gen = **speculative_decode**(req, 
                         endpoint_draft=draft_ep, 
                         endpoint_target=ep)
            else: # simple pass-through stream 
                 gen = passthrough(ep)
        ```
        
        - **max_new_tokens > 1024(긴 출력)** + 해당 모델이 **스펙큘레이티브 디코딩을 지원**(draft_enabled)하면 → 스펙큘레이티브 디코딩:
            - 빠르고 저렴한 드래프트 모델이 여러 토큰을 미리 생성하고, 느리지만 정확한 타겟 모델이 그걸 한꺼번에(bulk) 검증.
            - 한 토큰씩 순차 생성하는 중복 작업을 피해 지연시간을 크게 줄입니다.
            - 임계값(1024토큰) 의미?
                - *스펙큘레이티브 디코딩은 두 모델을 동시에 돌리는 오버헤드가 있는데, 생성할 토큰 수가 많을수록 드래프트 모델의 속도 이득이 그 오버헤드를 상쇄하고도 남기 때문입니다.*
                - *즉 짧은 응답엔 오히려 손해일 수 있어서, 출력 길이로 두 전략을 분기하는 게 합리적인 휴리스틱입니다.*
        - **그 외**: 그냥 선택된 엔드포인트로 패스스루 passthrough 스트리밍 → **simple pass-through stream**
            
            
    - `choose_endpoint()` : 엔드포인트 라우팅 정책 - 우선 순위 순서, 개별 클라이언트에 맞춘 라우팅
        
        ```python
        def choose_endpoint(model: str, tenant: str):
            cfg = load_routes()
        
            # policy example: tenant allow-list, cost class, region, canary
            route = cfg["**models**"].get(model) or cfg["**aliases**"].get(model)
            **if not route**: raise HTTPException(**404**, f"Unknown model {model}")
        
            # weighted canary
            if "canary" in route and **random() < float(route["canary"]["weight"]):**
                return route["canary"]["url"]
        
            # tenant override
            route_over = (route.get("tenants") or {}).get(tenant)
            if route_over: return route_over["url"]
            return route["url"]
        ```
        
        1. **모델/별칭 조회** : 없으면 404
        2. **가중치 기반 카나리(canary) 라우팅**: 
            - random() < weight 확률로 **신규/실험 버전 엔드포인트로 트래픽 일부를 흘려보냄**.
            - 이 체크가 테넌트 오버라이드보다 먼저 실행된다는 점에 주목
            - 즉 카나리 샘플링은 전체 트래픽(전용 라우팅을 가진 테넌트 포함)에서 무작위로 뽑히도록 설계돼 있어서, 카나리 배포가 특정 고객군에 편향되지 않고 대표성 있는 샘플을 확보합니다.
        3. **테넌트별 오버라이드** : 특정 고객에게 전용 엔드포인트(예: 전용 파인튜닝 모델, 전용 용량)가 지정돼 있으면 그걸 사용
        4. **기본 라우트로 폴백**
    
- **Implementing a Model Serving Endpoint 모델 서빙 엔드포인트 구현하기**
    - 모델 호스팅 계층에서는 단일 모델 서비스와 멀티 모델 서비스가 이 단계에서 이루어집니다. 직접 구현하려면, 앞서 그림 3-7과 3-8에서 소개된 설계를 따라 vLLM, NVIDIA Triton, Kubernetes, FastAPI 같은 도구를 활용해 만들 수 있습니다.
    - 인스턴스 서빙을 위한 확장성과 네트워크 관리가 부담스럽다면, **온라인 추론 API 구축을 위한 확장 가능**하고 **프레임워크에 구애받지 않는 모델 서빙 라이브러리**인 **Ray Serve**를 사용할 수 있습니다.
    - 다음 몇 개의 섹션에서는 Ray Serve를 사용해 단일 모델 및 멀티 모델 호스팅을 구현하는 방법을 보여드리겠습니다.
        - *3장에서 직접 만들었던 모델 호스팅 레이어를 ⇒ Ray Serve 프레임워크로 구현 시 달라지는 점 소개*
        
    - **Single-model hosting on Ray : 단일 모델 호스팅 (Ray + vLLM)**
        
        ```python
        # Ray Serve 안에서 vLLM을 이용해 Qwen 모델을 서비스하는 예
        HTTP Request
             ↓
        Ray Serve
             ↓
        QwenVLLM Replica
             ↓
        vLLM AsyncLLMEngine
             ↓
        GPU
        
        # 예제에서는 Qwen 서비스를 3 Replica × GPU 1개로 배포
        Ray Serve
        Replica 1 → GPU 1
        Replica 2 → GPU 2
        Replica 3 → GPU 3
        ```
        
        - 먼저, 서빙 로직을 담을 QwenVLLM이라는 파이썬 클래스를 만드세요. 먼저 vLLM에서 모델(Qwen3)을 초기화해보겠습니다:
        
        ```python
        **class QwenVLLM:**
            **def __init__(self):**                     # vLLM의 AsyncLLMEngine을 한 번 초기화
                args = AsyncEngineArgs(
                    model="**Qwen3-Thinking-2507**",
                    tensor_parallel_size=1,
                    trust_remote_code=True,
                    max_num_batched_tokens=4096,
                    gpu_memory_utilization=0.9,
                )
                self.engine = **AsyncLLMEngine**.from_engine_args(args)
                
            **async def __call__(**self, http_request): # HTTP 요청 진입점 역할
                ...
                return await self.generate_text(text, ...)
        ```
        
        - `__init__`에서 vLLM의 AsyncLLMEngine을 한 번 초기화하고, `__call__`이 HTTP 요청 진입점 역할을 합니다.
        - single_model_llm_serving에서 만든 **ModelWorker**(모델을 한 번 로드하고 generate()로 요청 처리)와 개념적으로 동일한 패턴.
        - 다만 **수동 배칭/큐잉을 직접 구현**했던 반면, 여기선 **vLLM의 AsyncLLMEngine**에 그 일을 통째로 **위임**합니다.
        
    - 그 다음 요청을 처리하는 **모델의 진입점**과 **실행 로직**을 정의합니다:
        
        ```python
        **class QwenVLLM:**
            # entry point for the generation/prediction request.   
            **async def __call__(**self, http_request: Request) -> str:
                """
                Accepts a raw JSON body:
                  { "text": "Explain KV cache simply.", 
                 "max_new_tokens": 200, "temperature": 0.7 }
                Returns the generated string.
                """
                body = await http_request.json()
                text = body["text"]
                max_new = body.get("max_new_tokens", 256)
                temp = body.get("temperature", 0.7)
                return await self.generate_text(
                    text,
                    max_new_tokens=max_new,
                    temperature=temp
                )
        
            **async def generate_text(**
                self,
                text: str,
                max_new_tokens: int = 256,
                temperature: float = 0.7) -> str:
                ...
                
                # run vLLM engine to execute Qwen model 
                async for out in self.engine.generate(prompt, params, request_id=req_id):
                
                    # For vLLM with stream=True, incremental delta is here:
                    delta = out.outputs[0].text_delta
                    if delta:
                        chunks.append(delta)
                return "".join(chunks).strip()
        ```
        
    - 모델 서빙 코드를 구현한 후에는 QwenVLLM 클래스에 decorator `@serve.deployment`을 추가해 **Ray Serve에서 호스팅**할 수 있습니다.
    - 이 선언이 설정되면, 서비스 배포 시 **Ray가 자동으로 컴퓨팅 리소스를 할당**하고 **Qwen 모델 서비스를 위한 서비스를 배포**합니다.
    - 다음 코드는 Ray가 Qwen3 모델을 세 개의 서비스 인스턴스로 제공하도록 지시하며, **각 인스턴스에 전용 GPU가 할당**됩니다:
        
        ```python
        # Create Ray Serve instance for hosting Qwen3 model
        **@serve.deployment**(
            name="**qwen_vllm**",
            # declare the number of service instances for the model
            **num_replicas=3,**
            # needs a GPU for speed
            ray_actor_options={"num_cpus": 0.5, **"num_gpus": 1**},  
        )
        **class QwenVLLM**:
         .. .. ..
        ```
        
        - **데코레이터 decorator 하나**로 **"레플리카 3개, 각각 GPU 1개씩"이라는 선언**이 끝입니다.
        - 지난 절에서 본 Kubernetes HPA YAML(minReplicas/maxReplicas/CPU 임계값)이 하던 일을, **Ray Serve는 파이썬 데코레이터 한 줄**로 대체합니다 → 리소스 프로비저닝과 배포를 Ray가 자동으로 처리!
        
    - **Multi-model hosting on Ray : 멀티모델 호스팅 (Ray의 "model multiplexing")**
        - *Ray Serve의 multiplexing을 사용하면 request header의 model id에 따라 모델을 lazy load하고 replica별 cache를 유지할 수 있다.*
        
        ```python
        # 세 모델을 두 개 Serving Replica에서 운영
        DistilBERT
        BERT
        RoBERTa
        ```
        
    - 챕터3에서 직접 만든 것 vs Ray Serve 대응 기능
        
        ```python
        ┌───────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────┐
        │   **직접 만든 것 (ch03/multi_model_serving)**                │                       **Ray Serve의 대응 기능**                           │
        ├───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
        │ **ModelManager**(OrderedDict LRU, max_models=2)           │ **@serve.multiplexed(**max_num_models_per_replica=2)                   │
        ├───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
        │ ModelEngine.create_worker() — 요청 시점에 없으면 새로 로드   │ **load_model(model_id)** — await self.load_model(model_id)로 요청마다 확인 │
        ├───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
        │ **config/models.json** (model_id → 모델명 매핑)              │ **MODEL_REGISTRY dict (model_id → HF repo)**                           │
        ├───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
        │ server.py의 **model_id 필드로 라우팅**                        │ **HTTP 헤더 ray_serve_multiplexed_model_id**                            │
        └───────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘
        ```
        
    - 비슷한 입력 타입을 가진 모델 그룹을 공유 서비스에서 호스팅해야 할 경우, Ray Serve는 서비스 **인스턴스(레플리카) 풀에서 여러 모델을 제공**하는 **모델 멀티플렉싱 기능을 제공**합니다.
    - `serve.multiplexed`와 `serve.get_multiplexed_model_id` API를 사용하면 Ray에서 단일 모델 호스팅 서비스를 **다중 모델 호스팅으로 확장**할 수 있습니다. 두 개의 서비스 인스턴스를 사용해 **Ray Serve에서 세 개의 서로 다른 감성 모델을 호스팅**하는 간단한 예제를 보여드리겠습니다.
    - 먼저, 추론 요청에 따라 모델을 실시간으로 불러와 실행하는 **모델 실행 로직을 정의**합니다:
        
        ```python
        @serve.deployment(
            num_replicas=2,  # two instances/replicas
            ray_actor_options={"num_cpus": 1} # resources per replica
        )
        **class MultiModelService:**
           # entry point for model inference requests
           async def __call__(self, request: Request):
               # Pick the model id for this request
               model_id = _**serve.get_multiplexed_model_id(**)
               
               # load model and run model inference
               tokenizer, model = await self.**load_model**(model_id)
               inputs = tokenizer(text, return_tensors="pt")
               with torch.no_grad():
                   logits = model(**inputs).logits
                   probs = torch.softmax(logits, dim=-1).tolist()[0]
        
               return JSONResponse({
                   "model_id": model_id,
                   "label_probs": probs,  # [neg, pos] for SST-2 style models
               })
        ```
        
    - **MultiModelService 클래스**의 `__call__` 함수에서 볼 수 있듯이, 멀티 모델 추론 코드의 구현은 단일 모델 서빙 코드와 매우 유사합니다.
    - 주요 차이점은 단일 모델 서빙에서는 **init** 함수에서 모델을 미리 로드하지만, 멀티 모델 호스팅에서는 요청마다 다른 모델을 요구할 수 있기 때문에 `await self.load_model(model_id)`를 사용해 실시간으로 요청된 모델을 불러오려고 시도한다는 점입니다.
    - 이 방법의 단점은 **요청마다 모델을 로드해야 하므로 추가적인 지연이 발생**한다는 점입니다. 이를 완화하기 위해 **모델 로딩 함수**(load_model)에 `serve.multiplexed` 주석을 달아주세요. 이 설정은 Ray Serve가 가능한 경우 **캐싱 메커니즘을 적용**하고, **메모리 같은 자원이 제한**될 때 **모델 교체를 관리**하도록 합니다.
        
        
    - 다음 예제들은 **멀티플렉싱이 활성화된 상태에서 모델 로딩 로직을 어떻게 향상**시킬 수 있는지 보여줍니다:
        
        ```python
        # Example registry: map model_id -> HF repo 
        # This model source could be S3 or any other storage
        MODEL_REGISTRY = {
           "distilbert-sst2": "distilbert-base-uncased-finetuned-sst-2-english",
           "bert-sst2": "textattack/bert-base-uncased-SST-2",
           "roberta-sst2": "roberta-base-openai-detector", 
        }
        
        @serve.deployment(ray_actor_options={"num_cpus": 1})
        **class MultiModelService:**
        
           # enable multi model support and 
           # set model replica count for each model
           **@serve.multiplexed(max_num_models_per_replica=2)**  # Ray Serve는 자체 LRU 캐싱을 프레임워크가 대신 관리
           async def load_model(self, model_id: str) \ 
                   -> Tuple[AutoTokenizer, torch.nn.Module]:
               """
               Lazily load & cache a model per model_id on this replica.
               Ray Serve will LRU-evict when cached models
                 exceed max_num_models_per_replica.
               """
               repo = MODEL_REGISTRY[model_id]
        
               tokenizer = await asyncio.to_thread(\
                      AutoTokenizer.from_pretrained, repo)
               model = await asyncio.to_thread(\     
                      AutoModelForSequenceClassification.from_pretrained,\
                      repo)
               model.eval()
               return tokenizer, model
        ```
        
        !mermaid-diagram (1).png.png)
        
        - 챕터 3 단일 모델은 __init__에서 미리 로드, 멀티모델은 요청마다 load_model()을 시도 단점 →  "매 요청마다 로드하면 지연시간이 늘어난다”
        - Ray Serve는 이걸 @serve.multiplexed 데코레이터 하나로 해결 ⇒ 자체 LRU 캐싱을 프레임워크가 대신 관리
            - *max_num_models_per_replica를 넘으면 자동으로 축출(evict)합니다.*
            - *즉 우리가 손으로 짠 ModelManager의 로직을 Ray가 프레임워크 기능으로 내장해서 제공하는 셈입니다.*
        
    - **예측 요청 prediction request** 시 호출할 모델 ID를 지정하기 위해 HTTP 헤더인 `ray_serve_multiplexed_model_id`를 사용할 수 있습니다. Ray는 백엔드에서 트래픽 라우팅, 부하 분산, 자원 관리를 담당할 것입니다.
        
        
    - 예를 들어, 다음 curl 요청은 **Ray Serve의 distilbert-sst2 모델 호스트**에 **감성 예측 요청**을 보냅니다:
        
        ```python
        # curl -d '{"model_id": "...", "input_data": "..."}' 형태로 body에 모델 ID를 넣었던 것과 달리, 
        # Ray는 HTTP 헤더로 모델을 지정하고 라우팅/로드밸런싱/리소스 관리를 백엔드에서 알아서 처리합니다.
        
        curl -s -X POST "http://127.0.0.1:8000/**SentimentService**" \
          -H 'content-type: application/json' \
          -H 'ray_serve_multiplexed_model_id: **distilbert-sst2**' \
          -d '{"text":"**I absolutely loved this!**"}'
        ```
        
    - 나만의 서빙 스택을 만드는 것은 어렵지 않습니다
        - 시스템이 많은 움직이는 요소들을 포함하는 것처럼 보일 수 있지만, 이 장에서 소개한 대부분의 구성 요소들은 이미 실제 운영 환경에서 충분히 검증되었습니다.
        - **인프라 관리를 위해 Kubernetes**를, **모델 호스팅을 위해 Ray Serve** 또는 Triton Inference Server를, **분산 LLM 서비스**와 **최적화**(예: 커널 수준 가속 및 캐싱)를 위해 **vLLM을 활용**하면 견고하고 유연한 서빙 스택을 구축할 수 있습니다.
        - 자체 구현한 미들웨어 마이크로서비스에 가벼운 맞춤 로직만 추가하면, 완전한 엔터프라이즈급 서비스 솔루션을 직접 구축하는 것도 충분히 가능합니다.
        - 여기서 소개한 라이브러리와 프레임워크들은 수년간의 사용을 통해 성숙해졌기 때문에, 참고할 만한 강력한 구현체들이 많이 있습니다.
        - 또한 AI 코딩 어시스턴트는 반복적이고 통합적인 작업을 처리함으로써 개발 속도를 크게 높일 수 있습니다.
    

### (옵션/실습) Ray Serve on K8s

- `도전과제` : 로컬 PC 에 kind(k8s)로 RayService 배포 테스트 해보기 - Guide
- 사전 준비 : 참고 - (따라하며 확인하는) PC에 GPU 설정 및 사용 by Docker / K8S
    - **GPU 1대 이상 장착한 서버(권장)** *or CPU-Only*
        - *Train a PyTorch model on Fashion MNIST with CPUs on Kubernetes (CPU-Only) - Docs*
        - *Serve a MobileNet image classifier on Kubernetes (CPU-Only) - Docs*
    - K8s(or K3s) + NVIDIA GPU Operator - Docs
    - kube-prometheus-stack + DCGM Exporter - Docs + 그라파나 대시보드 추가 (12239)
    
- **Ray** : Python/**AI 애플리케이션**을 단일 머신에서 클러스터로 자동 확장할 수 있게 해주는 **오픈소스 통합 분산 컴퓨팅 프레임워크** - Docs
    - 구조
        
        !image.png
        
        - **Ray Core** — 기반 레이어. @ray.remote로 함수(Task)나 클래스(Actor)를 손쉽게 분산 실행
        - Ray Data — 대규모 병렬 데이터 처리/ETL (ray.data.read_csv, map_batches 등)
        - Ray Train — PyTorch/TensorFlow 등 프레임워크 위에서 분산 학습 자동화
        - Ray Tune — 대규모 병렬 하이퍼파라미터 튜닝 (몇 줄로 멀티노드 서치)
        - **Ray Serve** — 학습된 모델을 HTTP 엔드포인트로 프로덕션 서빙
        - Ray RLlib — 산업 수준 강화학습 알고리즘(PPO, DQN 등)
    - 배포
        - AWS/GCP/Azure/Kubernetes에 클러스터 배포 가능(ray submit cluster.yaml example.py --start)
        - 관리형 서비스로 Anyscale도 존재
    - 운영
        - Ray Dashboard(localhost:8265)로 실시간 모니터링
        - ray summary tasks로 CLI 상태 확인
    
- **Ray Serve** : 학습된 모델을 HTTP 엔드포인트로 프로덕션 서빙 - Docs
    - 여러 개의 Deployment를 조합해 하나의 Application을 만들고, 그중 하나가 Ingress로서 HTTP 요청을 받아 나머지 Deployment들을 DeploymentHandle로 호출하는 구조
    - Deployment (배포)
        - Ray Serve의 기본 단위. 비즈니스 로직이나 ML 모델을 담고 요청을 처리.
        - @serve.deployment 데코레이터로 정의, 런타임에 여러 개의 replica(각각 별도 Ray Actor)로 확장 가능.
            
            ```python
            @serve.deployment
            class MyFirstDeployment:
                def __init__(self, msg):
                    self.msg = msg
                def __call__(self):
                    return self.msg
            ```
            
    - Application (애플리케이션)
        - 하나 이상의 Deployment로 구성된 업그레이드 단위(배포/롤백을 애플리케이션 단위로 관리).
        - 그중 하나의 Deployment가 모든 인바운드 트래픽을 받는 "수신자" 역할을 함.
    - Ingress Deployment (진입점 배포)
        - serve.run()에 전달되는 최상위 Deployment.
        - HTTP 요청 처리 로직 담당 — Starlette request를 직접 받거나 FastAPI와 통합 가능.
        - 필요시 다른 Deployment로 요청을 라우팅.
    - DeploymentHandle (배포 핸들)
        - Deployment 간 통신을 위한 Python 네이티브 API.
        - 한 Deployment 생성자에 다른 Deployment를 넘기면 런타임에 Handle로 바뀌어 비동기 호출 가능.
            
            ```python
            @serve.deployment
            class Ingress:
                def __init__(self, hello_handle: DeploymentHandle):
                    self._hello_handle = hello_handle
            ```
            
    - 연결 흐름
        1. 각 Deployment를 .bind()로 서로 연결(의존성 주입)
        2. serve.run(ingress.bind(...))로 실행하면 Ingress가 HTTP 엔드포인트가 되고, 내부적으로 다른 Deployment들을 DeploymentHandle을 통해 호출
    
- **Ray Serve (Serving LLMs)** : 분산 LLM 서빙에 특화한 레이어 - Docs
    - vLLM 같은 추론 엔진을 Ray Serve의 배포 프리미티브(Deployment/Replica/…) 위에서 수평 확장시켜, 분산 LLM 서빙에 특화한 레이어
        
        !image.png
        
    - **핵심 구성 요소**
        1. **OpenAiIngress**
            - FastAPI 기반 진입점. OpenAI 호환 엔드포인트 제공, 요청 라우팅, 모델 멀티플렉싱(LoRA 어댑터 관리 포함) 담당.
        2. **LLMServer**
            - 실제 추론 엔진(vLLM 등) 인스턴스를 감싸는 Ray Serve 배포 단위. 세 가지 운영 모드 지원:
                - 독립형(standalone) — 레플리카마다 독립적으로 요청 처리
                - 배포 내 조율 — 데이터 병렬 어텐션(MoE 전문가 계층 조율)
                - 배포 간 조율 — prefill-decode 분리(단계별로 별도 확장/다른 GPU 타입 사용 가능)
        3. **Ray Serve Primitives**
            - Deployment(확장 단위), Replica(Ray Actor), DeploymentHandle(레플리카 간 RPC 통신)을 그대로 재사용.
    - **요청 처리 흐름**
        - 클라이언트 → OpenAiIngress(라우팅) → DeploymentHandle(RPC) → LLMServer Replica(가능하면 같은 노드 우선 배치) → vLLM 엔진(GPU) → 응답
        - 같은 노드의 레플리카를 우선 라우팅해서 크로스노드 오버헤드를 최소화하는 게 특징입니다.
    - **지원 기능**
        - 데이터 병렬 어텐션: 여러 엔진이 MoE 전문가 계층을 나눠 처리 → 고처리량 MoE 모델에 유리
        - Prefill-Decode 분리: 프리필/디코드를 독립적으로 스케일링, 단계별로 다른 GPU 배정 가능
        - 커스텀 라우팅: 캐시 지역성/세션 친화성 기반 라우팅으로 반복 프롬프트 워크로드 최적화
        - 오토스케일링 조율: Ingress:LLMServer = 2:1 비율 권장, target_ongoing_requests로 컴포넌트별 스케일 균형 유지
        
    - **Network topology and RPC patterns**
        
        !image.png
        
    
- **Ray Cluster** : Head Node 1개 + Worker Node N개로 구성된 분산 시스템 - Docs
    
    !ray-cluster.svg
    
    - **Head Node**
        - 워커 노드와 동일한 프로세스를 실행하면서, 추가로 클러스터 전체를 관리하는 싱글톤 프로세스들을 담당
            - Autoscaler (오토스케일러)
            - GCS (Global Control Store) — 클러스터 메타데이터 관리
            - Ray 드라이버 프로세스 (사용자가 제출한 스크립트 실행)
    - **Worker Node**
        - 클러스터 관리 기능은 전혀 없고, 오직 사용자 코드(Task/Actor) 실행만 담당하는 순수 연산 노드
    - Autoscaler
        - Head Node에서 돌아가는 프로세스
        - 리소스 요청량을 감지해 워커 노드를 자동으로 늘리고(필요시), 유휴 노드는 자동으로 제거
    - **Ray Jo**
        
        !ray-job-diagram.png
        
        - 하나의 스크립트에서 시작된 Task/Object/Actor 전체 묶음 = 하나의 애플리케이션 단위
        - 사용자가 Job을 Head Node에 제출 → Autoscaler가 필요 리소스만큼 워커 노드를 확보 → 실제 연산은 Worker Node들에 분산되어 실행
    - **요청 흐름**
        - 사용자 → Job 제출 (Head Node) → Autoscaler가 Worker Node 확보/조정 → Worker Node들에서 Task/Actor 병렬 실행
    
- **Ray Cluster on Kubernetes (KubeRay)** : Kubernetes 위에서 Ray 클러스터를 운영하는 공식 권장 방식(**Operator**) - Docs
    - KubeRay는 Kubernetes 위에서 Ray 클러스터를 운영하는 공식 권장 방식(Operator)입니다.
    - **Ray 헤드/워커 노드**를 Kubernetes **파드**로 관리하며, Kubernetes-네이티브한 방식으로 Ray의 생명주기를 제어합니다.
        
        !image.png
        
    - **핵심 특징**
        - 자동 스케일링: 워크로드에 따라 Ray 파드를 자동 증감 (단, 이전에 검토한 것처럼 GPU 등 물리 리소스 한계 내에서만 의미가 있음)
        - 이기종 컴퓨팅 지원: CPU/GPU 등 다양한 노드 타입 혼합 구성 가능
        - 멀티 클러스터: 하나의 k8s 클러스터 안에서 서로 다른 Ray 버전의 클러스터를 동시에 운영 가능(격리)
    - **3+1개 커스텀 리소스(CRD)**
        
        ```python
        ┌────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
        │    CRD     │                                                      용도                                                      │
        ├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ **RayCluster** │ Head/Worker 파드로 구성된 Ray 클러스터 자체의 생명주기 관리 (기본 단위)                                                    │
        ├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ **RayJob**     │ RayCluster를 생성해서 단일 Job을 실행하고 완료되면 정리하는 배치 작업용 (필요시 클러스터 자동 삭제)                               │
        ├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ **RayService** │ RayCluster 위에 Ray Serve 애플리케이션을 얹어 운영 — 무중단 업그레이드, 헬스체크 기반 고가용성 지원                             │
        ├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ **RayCronJob** │ (추가 지원) RayJob을 크론 스케줄로 반복 실행                                                                           │
        └────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
        ```
        
    
- **RayService** vs RayCluster **-** Quickstart
    - 구성 요소
        - RayCluster: Manages resources in a Kubernetes cluster.
        - Ray Serve Applications: Manages users’ applications.
    - **What does the RayService provide? - Docs**
        - Ray 클러스터와 Ray Serve 애플리케이션에 대한 Kubernetes 네이티브 지원
            - Kubernetes 설정을 사용해 Ray 클러스터와 Ray Serve 애플리케이션을 정의한 후에는 kubectl을 사용해 클러스터와 애플리케이션을 생성할 수 있습니다.
        - Ray Serve 애플리케이션의 인플레이스 업데이트
        - Ray 클러스터를 위한 무중단 업그레이드
        - 고가용성 서비스
        
    - RayCluster vs **RayService** 비교
        - 목표는 "vLLM을 독립형 모드로 서빙해서 OpenAI 호환 엔드포인트를 노출"하는 것이므로, **RayService가 적합!**
        
        ```python
        ┌──────────────────────┬───────────────────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
        │         항목          │                                 RayCluster                                            │                                        **RayService**                                         │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 역할 범위              │ Head+Worker 파드로 구성된 Ray 클러스터 자체만 관리                                             │ **RayCluster 생성 + 그 위에 Ray Serve 앱까지 함께 관리**                                                                 │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 배포 방식              │ helm install raycluster kuberay/ray-cluster (문서 예시) 또는 RayCluster CR 직접 apply      │ 단일 매니페스트에 **rayClusterConfig + serveConfigV2를 함께 기술**                                                       │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 워크로드 접속           │ head pod에 kubectl exec 하거나, dashboard(8265) port-forward 후 ray job submit           │ Serve용 k8s Service(-serve-svc)로 바로 HTTP 요청                                                                     │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ Serve 앱              │ 없음 — Serve를 쓰려면 사용자가 직접 serve run/serve deploy로 수동 배포·갱신해야 함                │ 자동 관리 — Serve 설정만 바꾸면 무중단 in-place 업데이트, RayCluster 스펙이 바뀌면 새 클러스터를 만들어 트래픽을     │
        │ 라이프사이클             │                                                                                       │ 무중단 컷오버                                                                                                        │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 헬스체크/HA            │ Ray 자체 기능에 한정, k8s 레벨에서 Serve 상태 인지 못함                                         │ /-/routes 기반 헬스체크로 k8s가 Serve 상태까지 파악, 장애 시 컨트롤러가 복구                                         │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 적합한 용도             │ 배치 작업(ray job submit), 대화형 실험, Ray Data/Train/Tune처럼 HTTP 서빙이 필요 없는           │ **프로덕션 모델 서빙(우리가 하려는 vLLM OpenAI 호환 엔드포인트)에 정확히 맞는 용도**                                     │
        │                      │  워크로드                                                                               │                                                                                                                      │
        ├──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ GPU 워커 설정          │ 사용자가 workerGroupSpec에 nvidia.com/gpu: 1 직접 기술                                     │ 동일하게 rayClusterConfig.workerGroupSpecs에 직접 기술 — 이 부분은 두 리소스가 차이 없음                             │
        └──────────────────────┴───────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
        ```
        
        1. **RayCluster만 쓰면 Serve 앱을 우리가 직접 serve run으로 올리고, 파드가 죽었을 때 재배포도 수동으로 챙겨야 함** — 단일 GPU/단일 노드라 운영 자동화의 이점이 더 큼
        2. **RayService는 무중단 업데이트/헬스체크를 컨트롤러가 대신해줘서, Serve 설정(모델 교체, replica 수 변경)을 바꿀 때 kubectl apply 한 번이면 됨**
        3. GPU 워커 스펙 작성 난이도는 둘이 동일하므로 RayCluster를 골라야 할 이유가 없음
    
- **Ray Cluster on Kubernetes (KubeRay) :** KubeRay Operator Installation 설치 - Docs
    - KubeRay Operator Installation 설치 - Docs
        
        ```python
        # 사전 확인된 전제조건 (이미 충족됨)
        - k3s v1.36.2+k3s1, helm v3.20.0
        - nvidia.com/gpu: 1이 노드에 정상 노출 (방금 설치한 nvidia-device-plugin)
        - storageClass local-path 기본 제공
        
        # 설치 명령 (공식 문서 기준)
        
        # 1. KubeRay helm repo 추가
        helm repo add kuberay https://ray-project.github.io/kuberay-helm/
        helm repo update kuberay
        
        # 2. 최신 버전 확인 (문서엔 1.6.0이 명시돼있지만 실행 시점에 재확인 권장)
        helm search repo kuberay/kuberay-operator --versions | head -5
        
        # 3. operator 설치 — 전용 namespace로 분리
        kubectl create namespace kuberay-system
        helm install kuberay-operator kuberay/kuberay-operator \
          --version 1.6.0 \
          -n kuberay-system
        
        # (참고: --create-namespace 옵션으로 2,3단계를 한 번에 처리 가능)
        - chart 이름: kuberay/kuberay-operator
        - CRD는 helm install에 포함되어 자동 설치됨 (RayCluster, RayJob, RayService, RayCronJob) — 별도 kubectl apply -f crds/ 불필요
        - 문서 기본 예시는 namespace 지정이 없어 default에 설치되지만, 우리는 지난 검토에서 정한 대로 kuberay-system으로 분리하는 걸 권장
        ```
        
    - KubeRay Operator 설치 후 검증
        
        ```python
        # operator pod 상태
        **kubectl get deploy -n kuberay-system -owide**
        NAME               READY   UP-TO-DATE   AVAILABLE   AGE   CONTAINERS         IMAGES                            SELECTOR
        kuberay-operator   1/1     1            1           80s   kuberay-operator   quay.io/kuberay/operator:v1.6.2   app.kubernetes.io/instance=kuberay-operator,app.kubernetes.io/name=kuberay-operator
        
        **kubectl get pods -n kuberay-system**
        NAME               READY   UP-TO-DATE   AVAILABLE   AGE
        kuberay-operator   1/1     1            1           77s
        
        # CRD 설치 확인
        **kubectl get crd | grep ray.io**
        rayclusters.ray.io                             2026-08-09T09:57:38Z
        raycronjobs.ray.io                             2026-08-09T09:57:38Z
        rayjobs.ray.io                                 2026-08-09T09:57:38Z
        rayservices.ray.io                             2026-08-09T09:57:39Z
        
        kubectl explain rayclusters.ray.io
        kubectl explain rayclusters.ray.io.spec
        kubectl explain rayservices.ray.io.spec
        kubectl explain rayservices.ray.io.spec
        
        # operator 로그로 이상 없는지 확인
        kubectl logs -n kuberay-system -l app.kubernetes.io/name=kuberay-operator --tail=30
        
        ```
        
    
- **Serve a Large Language Model using Ray Serve LLM on Kubernetes - Docs**
    - **실습 소개**
        - This guide provides a step-by-step guide for deploying a Large Language Model (LLM) using Ray Serve LLM on Kubernetes.
        - Leveraging **KubeRay, Ray Serve, and vLLM**, this guide deploys the `Qwen/Qwen2.5-7B-Instruct` model from Hugging Face, enabling scalable, efficient, and OpenAI-compatible LLM serving within a Kubernetes environment.
        - See Serving LLMs for information on Ray Serve LLM.
        
    - **사전 준비**
        - A Hugging Face account and a Hugging Face access token with read access to gated repositories.
        - In your RayService custom resource, set the `HUGGING_FACE_HUB_TOKEN` environment variable to the Hugging Face token to enable model downloads.
        - A Kubernetes cluster with GPUs.
        
    1. Create a Kubernetes cluster with GPUs : Skip
    2. Install the KubeRay operator : Skip
    3. Create a Kubernetes Secret containing your Hugging Face access token
        
        ```python
        #
        **curl -o ray-service.llm-serve.yaml https://raw.githubusercontent.com/ray-project/kuberay/master/ray-operator/config/samples/ray-service.llm-serve.yaml
        cat ray-service.llm-serve.yaml | tail
        ...**
        apiVersion: v1
        kind: Secret
        metadata:
          name: hf-token
        type: Opaque
        stringData:
          hf_token: **<your-hf-access-token-value>**
        ```
        
    4. Deploy a RayService
        - Secret : hf-token
        - RayService : vllm-service
        - NodePort Service : vllm-service-nodeport (30005)
        
        ```python
        # 공식 문서 대비 조정한 부분
        - 모델: Qwen/Qwen2.5-7B-Instruct-AWQ, quantization: awq 명시 (AWQ 커널 강제 사용), dtype: auto(체크포인트 권장값 따름)
        - gpu_memory_utilization: 0.85 — AWQ라 가중치 4~5GB뿐이라 KV캐시용으로 넉넉하게 확보
        - max_model_len: 4096 — VRAM 여유가 생겨 문서 예제(1024)보다 실용적인 길이로 상향(필요시 더 늘릴 수 있음)
        - nvidia.com/gpu: 4→1, num-gpus: "4"→"1", max_replicas: 4→1 — 물리 GPU 1장에 맞게 축소
        - worker CPU/메모리도 32/32Gi → 8/24Gi로 축소 (노드가 16 vCPU/64GB라 이 정도면 모니터링 스택과 공존 가능)
        
        apiVersion: ray.io/v1
        kind: **RayService**
        metadata:
          **name: vllm-service
          namespace: kuberay**
        spec:
          **serveConfigV2:** |
            applications:
              - name: llms
                import_path: ray.serve.llm:build_openai_app
                route_prefix: "/"
                **args:
                  llm_configs:**
                    - **model_loading_config:**
                        model_id: **qwen2.5-7b-instruct-awq**
                        model_source: **Qwen/Qwen2.5-7B-Instruct-AWQ**
                      engine_kwargs:
                        dtype: auto
                        **quantization: awq**
                        max_model_len: 4096
                        gpu_memory_utilization: 0.85
                      **deployment_config:
                        autoscaling_config:**
                          min_replicas: 1
                          max_replicas: 1        # 물리 GPU 1장 고정
                          target_ongoing_requests: 16
                        max_ongoing_requests: 32
          **rayClusterConfig:**
            **headGroupSpec:**
              rayStartParams:
                num-gpus: "0"
              template:
                spec:
                  containers:
                    - name: ray-head
                      image: **rayproject/ray-llm:2.52.0-py311-cu128**  # vLLM+CUDA 포함
                      resources:
                        limits:   {cpu: "2", memory: "5Gi"}
                        requests: {cpu: "2", memory: "4Gi"}
                      ports:
                        - containerPort: 8000   # Serve
                        - containerPort: 8080   # Metrics
                        - containerPort: 6379   # GCS
                        - containerPort: 8265   # Dashboard
                        - containerPort: 10001  # Client
            **workerGroupSpecs:**
              - groupName: gpu-group
                replicas: 1
                minReplicas: 1
                **maxReplicas: 1**                  # 물리 GPU 1장뿐이라 고정
                rayStartParams:
                  **num-gpus: "1"**
                template:
                  spec:
                    **containers:**
                      - name: ray-worker
                        image: **rayproject/ray-llm:2.52.0-py311-cu128**
                        resources:
                          limits:   {cpu: "8", memory: "24Gi", nvidia.com/gpu: 1}
                          requests: {cpu: "8", memory: "24Gi", nvidia.com/gpu: 1}
                        env:
                          - name: HUGGING_FACE_HUB_TOKEN
                            valueFrom:
                              secretKeyRef:
                                name: hf-token
                                key: hf_token
        ```
        
    5. 배포 후 확인
        - AWQ 모델 다운로드(HF Hub)만으로도 4~5GB, 최초 로딩 시간이 몇 분 걸릴 수 있음
            - 진행상황은 kubectl logs -n kuberay <worker-pod> -f 로 확인
        
        ```python
        # 배포 및 확인 명령
        **kubectl apply -f vllm-service.yaml**  
        kubectl get rayservice -n kuberay
        kubectl get pods -n kuberay -w
        kubectl describe rayservices.ray.io vllm-service -n kuberay   # applicationStatuses가 HEALTHY/RUNNING 될 때까지 대기
        
        # 컨테이너 이미지 확인
        **crictl images | grep -i ray**
        docker.io/rayproject/ray-llm                             2.52.0-py311-cu128        3d6cdf97592a7       11.6GB
        quay.io/kuberay/operator                                 v1.6.2                    0e5759fe13013       30.3MB
        
        # 허깅페이스 토큰 확인
        **kubectl get secret -n kuberay hf-token -o yaml | grep hf_token**
          *hf_token: aGZfU3...*
        
        # 파드 확인 : vLLM 엔진 사용 - 워커 컨테이너에 vllm 0.11.0 설치 확인
        ## Serve replica 로그: Using executor class: vllm.v1.executor.ray_distributed_executor.RayDistributedExecutor → Started vLLM engine.
        **kubectl get pods -n kuberay**
        NAME                                        READY   STATUS    RESTARTS   AGE
        vllm-service-g6qjt-gpu-group-worker-wh275   1/1     Running   0          11m
        vllm-service-g6qjt-head-ps2zr               1/1     Running   0          11m
        
        #
        **kubectl get rayservice -n kuberay**
        NAME           SERVICE STATUS   NUM SERVE ENDPOINTS
        vllm-service   Running          2
        
        **kubectl describe rayservices.ray.io vllm-service -n kuberay**
        ...
        Status:
          Active Service Status:
            Application Statuses:
              Llms:
                Serve Deployment Statuses:
                  LLMServer:qwen2_5-7b-instruct-awq:
                    Status:  HEALTHY
                  Open Ai Ingress:
                    Status:    HEALTHY
                Status:        RUNNING
            Ray Cluster Name:  vllm-service-g6qjt
            Ray Cluster Status:
              Available Worker Replicas:  1
          ...
              Head:
                Pod IP:               10.42.0.30
                Pod Name:             vllm-service-g6qjt-head-ps2zr
                Service IP:           10.42.0.30
                Service Name:         vllm-service-g6qjt-head-svc
              Last Update Time:       2026-08-09T10:38:00Z
              Max Worker Replicas:    1
              Min Worker Replicas:    1
              Observed Generation:    1
              Ready Worker Replicas:  1
              State:                  ready
        
        #
        **kubectl describe rayclusters.ray.io -n kuberay**
        **kubectl get rayclusters.ray.io -n kuberay**
        NAME                 DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   STATUS   AGE
        vllm-service-g6qjt   1                 1                   10     28Gi     1      ready    13m
        ****
        **kubectl get rayclusters.ray.io -n kuberay -owide**
        NAME                 DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   TPUS   STATUS   AGE   HEAD POD IP   HEAD SERVICE IP
        vllm-service-g6qjt   1                 1                   10     28Gi     1      0      ready    13m   10.42.0.30    10.42.0.30
        
        # nvidia-smi
        **nvidia-smi**
        ...
        +-----------------------------------------------------------------------------------------+
        | Processes:                                                                              |
        |  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
        |        ID   ID                                                               Usage      |
        |=========================================================================================|
        |    0   N/A  N/A           34359      C   ...RayWorkerWrapper.__ray_call__      14902MiB |
        +-----------------------------------------------------------------------------------------+
        
        # 외부 노출 (NodePort 30005)
        kubectl get pods -n kuberay --show-labels | grep head
        apiVersion: v1
        kind: Service
        metadata:
          name: vllm-service-nodeport
          namespace: kuberay
        spec:
          type: NodePort
          selector:
            ray.io/node-type: head
            ray.io/cluster: <배포 후 확인한 실제 RayCluster 이름>
          ports:
            - name: serve
              port: 8000
              targetPort: 8000
              nodePort: 30005
        ```
        
    6. 요청 테스트
        
        ```python
        curl -s http://192.168.254.150:30005/v1/chat/completions \
          -H 'Content-Type: application/json' \
          -d '{
            "model": "**qwen2.5-7b-instruct-awq"**,
            "messages": [{"role":"user","content":"**안녕, 너는 어떤 모델이야?**"}]
          }' | jq
        {
          "id": "chatcmpl-6f6bb20c-c9b9-420f-a0b8-48dde2bc06db",
          "object": "chat.completion",
          "created": 1786272184,
          "model": "qwen2.5-7b-instruct-awq",
          "choices": 
            {
              "index": 0,
              "message": {
                "role": "assistant",
                "content": "**안녕하세요! 저는 Alibaba Cloud에서 만든 Qwen이라는 언어 모델입니다. 대형 언어 모델로, 다양한 주제에 대해 대화할 수 있고 정보를 제공하는 데 도움을 줄 수 있습니다. 무엇을 도와드릴까요?"**,
        ...
        
        ```
        
    7. View the Ray dashboard - [Docs
        
        ```python
        # ray dashboard svc(vllm-service-dashboard-nodeport)를 nodeport 30006 설정
        **kubectl get svc -n kuberay vllm-service-dashboard-nodeport**
        NAME                              TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
        vllm-service-dashboard-nodeport   NodePort   10.43.195.216   <none>        8265:**30006**/TCP   8s
        
        ```
        
        !image.png
        
        !image.png
        
    8. (옵션) 프로메테우스 메트릭 노출 설정 - Docs → 프로메테우스 확인 ⇒ 그라파나 대시보드 추가 - Docs
        
        ```python
        # 계획 요약
        ┌────────────────────┬───────────────────────────────────────────────────────────────────────────────┬───────────────────────┐
        │        구분        │                                     내용                                      │       다운타임        │
        ├────────────────────┼───────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
        │ A. Prometheus      │ PodMonitor 2개(head/worker), operator ServiceMonitor                          │ 없음                  │
        │ 스크레이프 설정    │                                                                               │                       │
        ├────────────────────┼───────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
        │ B. Grafana         │ kuberay 공식 대시보드 5종 ConfigMap으로 자동                                  │ 없음                  │
        │ 대시보드 추가      │ 로드(default/serve/serve-deployment/serve_llm/operator)                       │                       │
        ├────────────────────┼───────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
        │ C. Grafana         │ Grafana allow_embedding+익명 Viewer 접근 허용 (helm upgrade)                  │ Grafana 파드          │
        │ embedding 설정     │                                                                               │ 재시작(수 초)         │
        ├────────────────────┼───────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
        │ D. Ray Dashboard   │ head에 RAY_GRAFANA_HOST/RAY_GRAFANA_IFRAME_HOST/RAY_PROMETHEUS_HOST 추가      │ vLLM 서빙 수 분 중단  │
        │ 연동 env 추가      │                                                                               │ 예상 (위 리스크)      │
        └────────────────────┴───────────────────────────────────────────────────────────────────────────────┴───────────────────────┘
        
        **# A. PodMonitor (namespace: monitoring)**
        apiVersion: monitoring.coreos.com/v1
        kind: PodMonitor
        metadata:
          name: ray-head-monitor
          namespace: monitoring
          labels: {release: kube-prometheus-stack}
        spec:
          jobLabel: ray-head
          namespaceSelector: {matchNames: [kuberay]}
          selector: {matchLabels: {ray.io/node-type: head}}
          podMetricsEndpoints:
            - port: metrics
              relabelings:
                - {action: replace, sourceLabels: [__meta_kubernetes_pod_label_ray_io_cluster], targetLabel: ray_io_cluster}
        ---
        apiVersion: monitoring.coreos.com/v1
        kind: PodMonitor
        metadata:
          name: ray-workers-monitor
          namespace: monitoring
          labels: {release: kube-prometheus-stack}
        spec:
          jobLabel: ray-workers
          namespaceSelector: {matchNames: [kuberay]}
          selector: {matchLabels: {ray.io/node-type: worker}}
          podMetricsEndpoints:
            - port: metrics
              relabelings:
                - {action: replace, sourceLabels: [__meta_kubernetes_pod_label_ray_io_cluster], targetLabel: ray_io_cluster}
        (우리 환경엔 as-metrics/dash-metrics 포트가 없고 metrics(8080) 하나뿐이라 그것만 스크레이프, namespaceSelector도 문서 예시의 default 대신 실제 kuberay로 지정)
        
        helm upgrade kuberay-operator kuberay/kuberay-operator --version 1.6.2 -n kuberay-system \
          --set metrics.serviceMonitor.enabled=true \  --set metrics.serviceMonitor.selector.release=kubB. Grafana 대시보드 (kuberay 공식 JSON, ConfigMap+s 확인한 sidecar가 grafana_dashboard: "1" 라벨을 전네임스페이스에서 자동 로드)- default_grafana_dashboard.json, serve_grafana_dasent_grafana_dashboard.json,serve_llm_grafana_dashboard.json(우리 vLLM 서빙에  Ray-Operator.json
        - (train/data 대시보드는 우리가 안 쓰는 워크로드라 스코프에서 제외)
        
        **# B. Grafana 대시보드 (kuberay 공식 JSON, ConfigMap+sidecar 방식 — 이미 DCGM 때 확인한 sidecar가 grafana_dashboard: "1" 라벨을 전 네임스페이스에서 자동 로드)**
        - default_grafana_dashboard.json, serve_grafana_dashboard.json, serve_deployment_grafana_dashboard.json, serve_llm_grafana_dashboard.json(우리 vLLM 서빙에 정확히 맞는 대시보드), KubeRay-Operator.json
        - (train/data 대시보드는 우리가 안 쓰는 워크로드라 스코프에서 제외)
        
        **# C. Grafana 설정 변경 (helm upgrade, 기존 values 파일에 추가)**
        grafana:
          grafana.ini:
            security:
              allow_embedding: true
            auth.anonymous:
              enabled: true
              org_role: Viewer
        보안 참고: 이렇게 하면 30002 포트(사설망 192.168.254.0/24 내부)에 접근 가능한 누구나 로그인 없이 Grafana를 **조회(Viewer)**할 수 있게 됩니다. 편집/설정 변경은 불가능하지만, 인증 없는 열람이 가능해지는 정책 변화입니다.
        
        **# D. head env 추가**
        env:
          - {name: RAY_GRAFANA_HOST, value: "http://kube-pritoring:80"}
          - {name: RAY_GRAFANA_IFRAME_HOST, value: "http://
          - {name: RAY_PROMETHEUS_HOST, value: "http://kubeus.monitoring:9090"}
        ```
        
    9. 확인
        - 프로메테우스 메트릭 노출 추가 확인
            
            !image.png
            
            !image.png
            
        - 그라파나 대시보드 확인
            
            !image.png
            
            - **Serve LLM Dashboard**
            
            !image.png
            
            !image.png
            
            !image.png
            
            !image.png
            
        
    10. 부하 테스트, 반복 호출 - Benchmarks
        
        !image.png
        
        !image.png
        
        !image.png
        
        !image.png
        
        ```python
        # 부하 테스트 실행 계획 (검토용)
        
        # 방식
        - 별도 패키지 설치 없이 Python 표준 라이브러리 스크립트로 /v1/chat/completions에 반복 호출
        - 서버(192.168.254.150) 로컬에서 localhost:30005로 직접 호출(네트워크 홉 제거, 순수 서빙 부하만 측정)
        - 클라이언트 측에서는 요청/응답 시간, 성공/실패 수, 처리량(req/s) 정도만 최소 집계 — 서버 측 상세 지표(큐 길이, GPU 사용률, replica 상태)는 이미 구축된 Grafana(Serve Dashboard, Serve Deployment Dashboard, DCGM 대시보드)로 실시간 관찰
        
        # 부하 파라미터 (권장 초기값 — 조정 가능)
        ┌─────────────────┬───────────────────────────────────┬─────────────────────────────────────────────────────────────────────┐
        │      항목       │                값                 │                                이유                                 │
        ├─────────────────┼───────────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
        │ 동시 요청       │ 8                                 │ deployment_config.max_ongoing_requests: 32 이내로, replica가        │
        │ 수(workers)     │                                   │ 1개뿐이라 과도한 동시성은 큐잉만 유발                               │
        ├─────────────────┼───────────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
        │ 총 실행 시간    │ 5분                               │ 짧게 트렌드만 확인하는 용도                                         │
        ├─────────────────┼───────────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
        │ 요청당 프롬프트 │ 고정된 짧은 문장(재현성)          │ 매번 다른 응답 길이면 지표 해석이 어려움                            │
        ├─────────────────┼───────────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
        │ max_tokens      │ 64                                │ 응답을 짧게 제한해 한 사이클이 오래 걸리지 않게                     │
        ├─────────────────┼───────────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
        │ 요청 간 처리    │ 각 워커가 응답 오면 즉시 다음     │ 가장 단순한 "반복 호출" 방식                                        │
        │                 │ 요청 발사(closed-loop)            │                                                                     │
        └─────────────────┴───────────────────────────────────┴─────────────────────────────────────────────────────────────────────┘
        
        # 스크립트 개요
        import concurrent.futures, json, time, urllib.request
        
        URL = "http://localhost:30005/v1/chat/completions"
        PAYLOAD = json.dumps({
            "model": "qwen2.5-7b-instruct-awq",
            "messages": [{"role": "user", "content": "Explain Kubernetes in one sentence."}],
            "max_tokens": 64,
        }).encode()
        
        def call():
            t0 = time.time()
            req = urllib.request.Request(URL, data=PAYLOAD, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    r.read()
                return time.time() - t0, True
            except Exception:
                return time.time() - t0, False
        
        def worker(stop_at):
            results = []
            while time.time() < stop_at:
                results.append(call())
            return results
        
        stop_at = time.time() + 300  # 5분
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(worker, stop_at) for _ in range(8)]
            all_results = [r for f in futures for r in f.result()]
        
        latencies = [r[0] for r in all_results]
        success = sum(1 for r in all_results if r[1])
        print(f"total={len(all_results)} success={success} avg_latency={sum(latencies)/len(latencies):.2f}s "
              f"p95={sorted(latencies)[int(len(latencies)*0.95)]:.2f}s throughput={len(all_results)/300:.2f} req/s")
        
        # 관찰 포인트 (테스트 도는 동안 Grafana에서 확인)
        - Serve Dashboard(30002) — 전체 QPS, 레이턴시 분포
        - Serve Deployment Dashboard — LLMServer replica의 ongoing/queued requests (replica 1개라 큐가 어떻게 쌓이는지가 핵심 관찰 포인트)
        - DCGM 대시보드 — GPU 사용률/온도/전력이 idle(0%) → 부하 중 어떻게 변하는지
        
        # 리스크 / 확인 필요 사항
        - 5분/동시 8이면 GPU가 계속 100%에 가깝게 유지될 수 있음 — 같은 노드에서 도는 monitoring 스택엔 영향 미미하지만, GPU 온도/전력이 튀는 건 정상입니다
        - 스크립트는 서버에 파일로 저장(/root/load_test.py) 후 실행 — 이건 파일 생성이라 CLAUDE.md 정책상 사전 승인 대상으로 분류하겠습니다
        ```
        
        ```python
        # 부하 테스트 결과
        
        ┌─────────────────┬────────────────────────────────────┐
        │      지표       │                 값                 │
        ├─────────────────┼────────────────────────────────────┤
        │ 총 요청         │ 1177건                             │
        ├─────────────────┼────────────────────────────────────┤
        │ 성공/실패       │ 1177 / 0 (100%)                    │
        ├─────────────────┼────────────────────────────────────┤
        │ 평균 지연시간   │ 2.05s                              │
        ├─────────────────┼────────────────────────────────────┤
        │ p50 / p95 / p99 │ 2.02s / 2.10s / 2.10s              │
        ├─────────────────┼────────────────────────────────────┤
        │ 처리량          │ 3.92 req/s                         │
        ├─────────────────┼────────────────────────────────────┤
        │ GPU (부하 중)   │ 사용률 99%, 전력 201.5W, 온도 66°C │
        ├─────────────────┼────────────────────────────────────┤
        │ GPU (종료 후)   │ 즉시 idle 복귀 (0%, 52W)           │
        └─────────────────┴────────────────────────────────────┘
        
        해석: p50~p99 편차가 거의 없어(2.02s~2.10s) 동시 8요청 수준에서는 큐잉 지연이나 성능 저하 없이 매우 안정적으로 처리됐습니다. 
             처리량(3.92 req/s)이 "동시성 8 ÷ 평균지연 2.05s"와 정확히 맞아떨어져, GPU가 병목점 역할을 하며 예측 가능한 속도로 요청을 소화하고 있음을 보여줍니다. 
             실패 0건으로 replica 1개·AWQ 양자화 구성이 이 정도 부하는 여유롭게 감당한다는 것도 확인했습니다.
        ```
        
    11. 실습 리소스 제거
    

### Building with a Cloud Vendor

- 클라우드 벤더와 함께 구축하기 소개
    - **오픈소스 스택**(Kubernetes + Ray Serve + vLLM)을 직접 조립해본 앞 절과 대비해서, 이번엔 **완전 관리형 클라우드**를 살펴봅니다.
    - 이 절의 접근 방식
        - **AWS SageMaker**를 예시로 삼아, **퍼블릭 클라우드**에서 **모델 서빙 시스템**을 만드는 **6가지 방법**을 소개할 예정
            
            
            | 단계 | 방식 | 자유도 | 운영 부담 |
            | --- | --- | --- | --- |
            | 1 | Bedrock | 낮음 | 매우 낮음 |
            | 2 | SageMaker JumpStart | 조금 높음 | 낮음 |
            | 3 | Bring Your Own Model | 중간 | 중간 |
            | 4 | Bring Your Own Code | 높음 | 높음 |
            | 5 | Bring Your Own Serving Image | 매우 높음 | 매우 높음 |
            | 6 | Build Your Own Infrastructure | 최고 | 최고 |
        - **배열 순서**는 완전 관리형(fully managed) → 가장 커스터마이징 가능한 방식 이동
        - **중요한 스코프 제한**:
            - SageMaker를 단계별로 조작하는 법(하우투 튜토리얼)을 가르치려는 게 아니라, 클라우드 벤더들이 서빙 옵션을 설계하는 근본 논리를 이해시키는 게 목적.
            - SageMaker는 하나의 구체적 예시일 뿐이고, 이 논리를 이해하면 다른 벤더(GCP Vertex AI, Azure ML 등)의 유사한 스펙트럼도 스스로 판단할 수 있게 하려는 의도입니다
    - 이 절부터는 "Docker 이미지"와 "Docker 컨테이너"를 같은 의미로 혼용하겠다고 미리 밝힙니다.
    - 둘 다 "모델 서빙 서비스 + 그 실행 환경"을 가리키는 말로 통일해서 쓰겠다는 것.
    
- **AWS SageMaker**를 예시로 삼아, **퍼블릭 클라우드**에서 **모델 서빙 시스템**을 만드는 **6가지 방법 - Amazon SageMaker**
    
    
    | 단계 | 방식 | 자유도 | 운영 부담 |
    | --- | --- | --- | --- |
    | 1 | Bedrock | 낮음 | 매우 낮음 |
    | 2 | SageMaker JumpStart | 조금 높음 | 낮음 |
    | 3 | Bring Your Own Model | 중간 | 중간 |
    | 4 | Bring Your Own Code | 높음 | 높음 |
    | 5 | Bring Your Own Serving Image | 매우 높음 | 매우 높음 |
    | 6 | Build Your Own Infrastructure | 최고 | 최고 |
- **[실습] Option 1: Fully Managed Foundation-Model Serving - Amazon Bedrock , Colab**
    - **Amazon Bedrock**은 간단한 **API를 통해 파운데이션 모델을 제공하는 완전 관리형 서비스**입니다. 여기서 소개하는 옵션 중 **가장 커스터마이징이 적지만 사용하기는 가장 쉽습**니다. Bedrock을 사용하면 **직접 모델 학습이나 호스팅을 관리할 필요가 없습니**다.
    - 아마존 타이탄 Titan, Anthropic Claude, Stability AI의 Stable Diffusion 같은 **모델** 베드락 지원을 선택한 뒤, **API를 호출**해 예측 결과를 가져오면 됩니다.
        
        !image.png
        
    - Bedrock은 AWS와 Anthropic, Cohere 같은 서드파티 모델 제공업체의 여러 파운데이션 모델을 기본 제공하며, 별도의 인프라 구축이나 관리 없이 바로 사용할 수 있습니다. 최소한의 설정으로 AI 기능을 애플리케이션이나 프로토타입에 빠르게 통합하는 데 이상적입니다.
    - Bedrock의 가격 모델은 '사용한 만큼 지불하는(pay-as-you-go)' 방식으로, 보통 시간 단위가 아니라 **요청 수나 출력 토큰 수에 따라 요금**을 부과합니다. 즉, 이 모델들에 대해 계정 내에서 서버를 직접 운영하지 않으며, AWS가 내부적으로 확장과 컴퓨팅 자원을 관리한다는 뜻입니다.
    - 그 결과 Bedrock은 DevOps 관련 부담이 전혀 없는데, 프로비저닝하거나 확장해야 할 서버도 없고, 빌드해야 할 모델 컨테이너도 없습니다. 대신 AWS가 제공하는 모델과 구성에 제한을 받으며, **커스터마이징도 비교적 제한적**이라는 단점이 있습니다. 예를 들어, **모델의 아키텍처나 학습 방식을 변경할 수 없으며,** **중간 정도의 미세 조정이나 프롬프트 맞춤화만 가능**합니다.
    - **Bedrock을 사용하는 데는 단 세 단계**만 필요합니다:
    1. AWS 계정(**오레곤 리전 us-west-2**)에서 **Bedrock API 키** 생성 : 
        
        !스크린샷 2026-08-09 오전 5.43.36.png
        
    2. Bedrock 모델 카탈로그에서 모델 선택 : Anthropic
        - Anthropic은 모델을 호출하기 전에, 계정당 한 번 또는 조직 관리 계정에서 한 번 사용 사례 세부 정보를 제출하도록 최초 사용자에게 요구합니다. 제출하신 정보는 Anthropic과 공유됩니다.
            
            !스크린샷 2026-08-09 오전 6.07.33.png
            
        - 모델 선택
            
            !image.png
            
        - 모델 ARNC 확인
            
            ```python
            **aws bedrock list-foundation-models --region us-west-2 | grep modelArn | wc -l**
                 112
            
            **aws bedrock list-foundation-models --region us-west-2 | grep modelArn**     
            aws bedrock list-foundation-models --region us-west-2 | grep -E 'modelArn|modelId'
            
            **aws bedrock list-foundation-models --region us-west-2 | grep -E 'modelArn|modelId' | grep amazon**
            ...
            ```
            
        
    3. Bedrock 클라이언트 초기화 + API 호출
        - https://github.com/orca3/llm-model-inference/blob/main/ch04/bedrock/aws_bedrock_examples.ipynb
        - Bedrock API Key 입력 : `os.environ['AWS_BEARER_TOKEN_BEDROCK'] = **"bedrock-api-key-YmVkcm9ja..**`
        - 모델 ID 변경 : `model_id = "**amazon.nova-lite-v1:0**”`
            
            !스크린샷 2026-08-09 오전 6.19.05.png
            
            ```python
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = **"..."**
            
            client = boto3.client(
               service_name="bedrock-runtime",
               region_name="us-west-2"
            )
            
            model_id = "**amazon.nova-lite-v1:0**"
            messages = [{"role": "user", "content": [
                {"text": "**Hello! Can you tell me about Amazon Bedrock?**"}
            ]}]
            
            response = client.converse(
               modelId=model_id,
               messages=messages,
            )
            ```
            
    - **제약 사항**
        - Bedrock은 파운데이션 모델을 위한 서버리스 관리형 추론 환경입니다. AWS SDK나 HTTPS 엔드포인트로 고수준 API를 호출하면:
            - GPU 인스턴스 프로비저닝
            - 모델 가중치 로딩
            - 추론 실행
            - 결과 반환
        - 이 전부를 AWS 인프라가 눈에 안 보이게 처리합니다.
            - “OpenAI 같은 외부 AI API를 호출하는 것과 개념적으로 같지만, 여러분의 AWS 환경 안에서 이뤄지는 AWS 서비스 호출"
        - **그래서 못 하는 것 3가지:**
            - 인스턴스 타입 선택 불가
            - 컨테이너/코드 커스터마이징 불가
            - 새 모델을 Bedrock에 배포하는 것 자체가 불가능 : 자체 프로프라이어터리 모델이나 남들이 안 올려둔 파인튜닝 버전은 Bedrock으로 못 씀
    - **언제 적합한가**
        - 적합: 챗봇/텍스트/이미지 생성기 같은 걸 인프라 관리 없이 빠르게 프로토타입할 때, 사전학습 모델로 충분할 때
        - 부적합: 자체 커스텀 모델을 배포해야 하거나, 정교한 추론 로직이 필요할 때 → 이런 경우는 뒤에 나올 더 커스터마이징 가능한 옵션(Option 2 이후)을 봐야 함
    
- [실습Skip] **Option 2: One-Click Foundation-Model Deployment - Amazon SageMaker JumpStart** , Colab
    - 또 다른 **no-code/low-code** 모델 호스팅 방식으로는 **Amazon SageMaker JumpStart** 아마존 세이지메이커 점프스타트가 있습니다.
    - AWS Bedrock과 마찬가지로, SageMaker JumpStart는 사전 학습된 모델과 간편한 배포 방식을 갖춘 모델 허브를 제공합니다.
    - 또한 Cohere, Falcon, Llama, Stable Diffusion 같은 AWS가 선별한 기초 모델과 Hugging Face 허브의 모델들을 포함한 방대한 모델 카탈로그를 제공합니다.
    - Bedrock vs JumpStart 비교
        
        ```python
        ┌──────────────────────┬──────────────────────────┬────────────────────────────────────────────────────────────────────────┐
        │                      │         Bedrock          │                               **JumpStart**                                │
        ├──────────────────────┼──────────────────────────┼────────────────────────────────────────────────────────────────────────┤
        │ 모델이 어디서 도는가      │ AWS가 완전히 숨긴 인프라      │ **여러분의 SageMaker 계정/인프라**                                         │
        ├──────────────────────┼──────────────────────────┼────────────────────────────────────────────────────────────────────────┤
        │ 과금                  │ 요청/토큰당 (서버 없음)       │ **시간당 인스턴스 요금 (직접 엔드포인트 호스팅)**                          │
        ├──────────────────────┼──────────────────────────┼────────────────────────────────────────────────────────────────────────┤
        │ 인프라 관리 부담         │ 거의 없음                  │ **조금 더 있음** — 인스턴스 타입(g5.48xlarge, g6e.48xlarge 등)을 직접 선택 │
        └──────────────────────┴──────────────────────────┴────────────────────────────────────────────────────────────────────────┘
        ```
        
        - JumpStart와 Bedrock의 가장 큰 차이점은 JumpStart가 최소한의 코딩으로 미리 선택된 모델들을 자신의 SageMaker 인프라에 배포할 수 있게 해준다는 점입니다.
        - 모델을 한 번의 클릭으로 배포할 수 있는 방식으로 자주 설명되며, SageMaker Studio UI와 SageMaker SDK를 통해 프로그래밍 방식으로도 사용할 수 있습니다.
        - "원클릭 배포"라고 불릴 만큼 쉽지만, Bedrock과 달리 **여러분 계정에 실제 엔드포인트가 뜬다**는 게 본질적 차이입니다.
        
    - 자신의 AWS 계정에서 모델을 호스팅하는 경우, **SageMaker가 관리하는 인스턴스는 시간당 요금을 지불**하게 됩니다. 즉, 이제 직접 모델 엔드포인트를 호스팅하기 때문에 인프라 관리가 조금 더 필요하다는 뜻입니다. **g5.48xlarge, g6e.48xlarge와 같은 서버 인스턴스 유형을 선택**할 수 있습니다.
    - 파운데이션 모델 → 사용 가능한 모델 : Open-Weight Model - Docs
        
        !image.png
        
    - 다음 예시에서는 Bedrock보다 인프라에 대해 더 많은 설정을 할 수 있는데, 예를 들어 모델 서빙 인스턴스 수, 로깅 레벨, 서버 인스턴스 유형 등이 있습니다:
        
        ```python
        # Define the model ID and version
        model_id = "**huggingface-llm-mistral-7b-instruct"**
        version = "*"  # Use the latest version
        
        # Create a JumpStartModel instance with hardware configurations
        model = JumpStartModel(
           model_id=model_id,
           model_version=version,
           instance_type=**"ml.g5.2xlarge**",  # Specify the instance type
           role=sagemaker_execution_role, # Specify the execution role
           env={ # Example environment variable
               "SAGEMAKER_MODEL_SERVER_WORKERS": "1",  
               "SAGEMAKER_CONTAINER_LOG_LEVEL": "20"
           },
           # Add other configurations as needed.
        )
        
        # Deploy the JumpStart model
        predictor = model.deploy(
           initial_instance_count=1,
           endpoint_name="my-mistral-endpoint",
           role=sagemaker_execution_role, 
           sagemaker_session=sess
        )
        
        # Send prediction request
        response = predictor.predict({"inputs": "Hello, world!"})
        ```
        
        - 모델 배포(deploy())라는 단계가 새로 생겼습니다!
        - 인스턴스 타입, 워커 수, 로그 레벨 같은 인프라 설정을 직접 지정하고, 그 결과로 나온 predictor 객체로 추론을 요청하는 2단계 구조입니다.
        
    - **Limitations** : 많이 자동화됐지만 여전히 한계는 있다
        - 내부적으로는 표준 SageMaker 추론 인프라를 쓰되 설정을 대신 자동화해주는 것뿐이라, **커스터마이징 여지는 제한적**입니다:
            - 모델마다 파인튜닝/평가 지원 여부가 다름 (배포 전용인 것도 있음)
            - **인스턴스 선택이 모델별로 고정됨** (아무 인스턴스나 못 씀)
            - **전처리/배칭 같은 기본 추론 동작 커스터마이징 불가**
            - **요청 payload 스키마/content type 조정 불가**
            - **CUDA/PyTorch 버전 선택 불가**
            - 컨텍스트 길이·배치 크기를 JumpStart가 이미 설정해버려서 **최적화 기법 적용이 어려움**
        - 즉 "**인스턴스는 내가 고르지만, 그 안에서 뭘 하는지는 여전히 AWS가 정한 대로**"라는 게 이 옵션의 본질
        - Bedrock보다 한 단계 더 열려있지만, 여전히 원클릭 자동화가 감춘 디테일이 많습니다.
        
    - **언제 쓰나**
        - 적합: 유명한 사전학습 모델(BERT 텍스트 분류, Stable Diffusion 이미지 생성 등)을 내 AWS 환경에 빠르게 띄우고 싶을 때, 컨테이너 설정이나 추론 코드를 직접 안 짜고 싶은 no-code/low-code 사용자. SageMaker 모범 사례를 따라 엔드포인트를 구성해주기 때문에 SageMaker 학습 도구로도 유용하다고 언급됩니다.
        - 부적합: 추론 로직을 완전히 통제해야 하거나, JumpStart가 지원 안 하는 모델을 서빙해야 할 때 → 다음에 나올 더 커스터마이징 가능한 SageMaker 옵션으로 이어짐
    
- [실습Skip] **Option 3: Bring Your Own Model 직접 모델 가져오기 - Deep Learning Containers (DLCs)** , Colab , Colab2
    - JumpStart나 Bedrock 모델 카탈로그에 없는 자체 모델을 더 자유롭게 서비스하려면, AWS SageMaker가 제공하는 다양한 **사전 빌드된 서빙용 Docker 이미지인 딥러닝 컨테이너(DLC)**를 활용해 별도의 추론 코드를 작성하지 않고도 모델을 배포할 수 있습니다.
        
        
    - **DLC란**
        - 프레임워크별(TensorFlow, PyTorch, HuggingFace Transformers) 사전빌드된 서빙 Docker 이미지 + SageMaker 내장 알고리즘 컨테이너(DJL 등)입니다.
        - 핵심 캐치프레이즈: "bring-your-own-model"이지 "bring-your-own-code"는 아니다.
            - 학습시킨 모델 아티팩트는 직접 가져오되, 서빙 코드는 컨테이너가 이미 알아서 처리합니다.
            - 모델 artifact는 직접 가져오지만 serving image와 runtime은 vendor 기본 이미지를 활용한다.
    - **JumpStart와의 차이**
        - JumpStart는 컨테이너/설정을 자동 선택해주지만,
        - DLC는 어떤 컨테이너(서빙 프레임워크)를 쓸지 직접 지정합니다.
            - PyTorch/Transformers 정확한 버전을 고를 수 있고, JumpStart 큐레이션 목록에 없는 모델도 배포 가능.
            - 대신 그 컨테이너가 뭘 요구하는지는 사용자가 이해하고 있어야 합니다.
            - 이 기능은 최소한의 코딩으로 맞춤형 모델(예: 직접 만든 PyTorch 모델)이나 오픈소스 기반 모델(예: Hugging Face Hub에 있는 모델 배포)에 활용할 수 있습니다.
        
    - TorchServe를 이용해 PyTorch 모델을 호스팅하는 예제를 함께 살펴보겠습니다.
    - **예시 1 : PyTorch + TorchServe**
    - 첫 번째 단계는 사용 중인 프레임워크와 파이썬 버전에 맞는 **미리 빌드된 DLC를 선택**하는 것입니다.
    - 아래 코드를 사용해 **PyTorch 모델에 적합한 DLC 이미지를 검색**할 수 있습니다:
        
        ```python
        # Find the available serving image by searching model framework
        # and server instance type
        baseimage = sagemaker.image_uris.retrieve(
            framework="pytorch",
            region="",
            py_version="py310",
            image_scope="inference",
            version="2.0.1",
            instance_type="ml.g4dn.16xlarge",
        )
        ```
        
    - 다음으로, **AWS S3에 모델 파일 위치를 지정해 서빙 이미지와 모델 객체를 생성**합니다.
    - 모델 객체를 선택한 인스턴스 유형(예: g4dn.16xlarge)에 배포합니다.
    - model.deploy 함수는 AWS에서 리소스 제공과 서비스 배포를 담당합니다:
        
        ```python
        # Create the Model object  
        model = Model(
            model_data=f"{output_path}/mnist.tar.gz",
            image_uri=baseimage,
            predictor_cls=Predictor,
            name="mnist"
        )
        
        # Deploy model
        predictor = model.deploy(
            instance_type="**ml.g4dn.16xlarge**",
            initial_instance_count=1,
            endpoint_name="torchserve-endpoint-1",
            serializer=JSONSerializer(),
            deserializer=JSONDeserializer()
        )
        ```
        
        - *프레임워크/버전/인스턴스 타입에 맞는 DLC 이미지를 직접 검색해서 지정(image_uris.retrieve) → S3에 있는 학습된 모델 아티팩트를 그 이미지에 얹어 배포. JumpStart는 이 검색 단계가 자동이었는데, 여기선 명시적입니다.*
        
    - **예시 2 : LLM(Llama)을 LMI + vLLM으로 서빙 (우리 3장 실습과 직결!)**
    - 다음은 또 다른 예입니다. vLLM을 지원하는 DJL 서빙 프레임워크를 기반으로 한 AWS의 사전 빌드된 대형 모델 추론(LMI) 컨테이너를 사용해 Hugging Face의 오픈 소스 LLM(Llama)을 서비스하는 경우입니다:
        
        ```python
        # Create the SageMaker Model object. 
        # In this example we let LMI configure the deployment settings
        # based on the model architecture
        model = DJLModel(
          model_id="**meta-llama/Meta-Llama-3.1-8B-Instruct"**,
          env={
            "**HF_TOKEN": "",**
            # Add more serving configurations here
            # Example: set tensor parallel degree
            **"OPTION_TENSOR_PARALLEL_DEGREE": "4",** 
            # Example: specify serving loader as vLLM
            **"OPTION_SERVING_LOADER": "vllm",** 
            # Example: set max rolling batch size
            **"OPTION_MAX_ROLLING_BATCH_SIZE": "128",** 
          }
        )
        
        # Deploy your model to a SageMaker Endpoint
        # and create a Predictor to make inference requests
        endpoint_name = sagemaker.utils.name_from_base("llama-8b-endpoint")
        predictor = model.deploy(
            instance_type=**"ml.g5.12xlarge**",
            initial_instance_count=1,
            endpoint_name=endpoint_name)
        ```
        
        - **"OPTION_SERVING_LOADER": "vllm"** → 이전 single_model_llm_serving에서 /generate_vllm 엔드포인트로 직접 통합했던 **vLLM 엔진**입니다.
        - **OPTION_MAX_ROLLING_BATCH_SIZE**는 로그로 직접 관찰했던 "동시 요청이 하나의 배치로 합쳐지는" 연속 배칭(continuous batching) 설정이고,
        - **OPTION_TENSOR_PARALLEL_DEGREE**는 모델을 여러 GPU에 쪼개는 텐서 병렬화(우리는 tensor_parallel_size=1로 GPU 1개만 썼었죠).
        - 즉 AWS의 관리형 LMI 컨테이너 뒤에서 실제로 도는 엔진이 우리가 손으로 통합해본 것과 똑같은 vLLM이라는 걸 알 수 있습니다.
        - 다만 여기선 인프라 프로비저닝을 AWS가 대신 해줄 뿐입니다.
    - 이 방법은 JumpStart보다 더 명확한 설정이 필요합니다. 모델의 프레임워크에 맞는 적절한 DLC 컨테이너와 버전을 찾아 지정하고, 모델 아티팩트가 제대로 준비되어 있는지 확인해야 합니다. 그 대신 유연성을 얻게 되는데, 예를 들어 JumpStart의 단순화된 인터페이스로는 사용할 수 없는 최신 프레임워크 릴리스를 활용할 수 있습니다. 컨테이너가 구현을 제공하기 때문에 직접 서빙 코드를 작성할 필요는 없습니다.
        
        
    - **Limitations 한계**
        - **컨테이너 내부를 거의 통제 못 함**
            - 프레임워크/NVIDIA 드라이버/CUDA/Python/OS가 전부 **이미지 태그에 고정됨**(예: TF 2.19 + CUDA 12.2 + Ubuntu 22.04).
            - 라이브러리 버전을 섞으려면 직접 이미지를 빌드해야 함
        - **고정된 포트/HTTP 계약:**
            - 모든 DLC 컨테이너는 **8080 포트**에서 /invocations(POST), /ping(GET)을 구현해야 하고, 이걸 벗어나면 표준 경로를 이탈하는 것.
            - **기본 타임아웃(예: 60초)**도 적용됨 : 이건 사실상 "SageMaker가 강제하는 미니 Public API 레이어 계약"이라고 볼 수 있습니다
        - **입출력 포맷이 고정**:
            - 커스텀 전처리/후처리가 필요하면 Option 4(커스텀 추론 스크립트)로 가야 함
    
    - 언제 사용하나요
        - 흔한 프레임워크로 학습한 모델을 SageMaker 관리형 서비스로 빠르게 배포하되, 약간의 커스터마이징(정확한 프레임워크 버전 등)이 필요할 때 이상적:
        - 파인튜닝한 HF Transformers 모델(BERT, Qwen3 등) → HF 추론 DLC
        - TensorFlow SavedModel이나 PyTorch .pth → TorchServe/TF Serving 이미지
        
    - 컨테이너의 기본 예측 처리 방식을 그대로 받아들일 수 있으면 **추론 코드를 아예 안 짜도 되는 게 최대 장점**이고,
    - 그게 부족하면 다음 레벨(Option 4, 커스텀 추론 스크립트)로 넘어가야 한다고 예고합니다.
    
- [옵션/실습] SageMaker 없이 "SageMaker용으로 빌드된 서빙 컨테이너"만 떼어서 로컬 GPU PC에서 재현 - Docs
    - 필요 사항
        1. **AWS 계정(자격증명)**
            - DLC 이미지들은 완전 익명 공개가 아니라 Amazon ECR(대개 763104351884.dkr.ecr.<region>.amazonaws.com/... 같은 AWS 소유 리포지토리)에 있어서, 무료 티어 계정이라도 `aws ecr get-login-password | docker login ...`로 인증은 해야 풀(pull)이 됩니다.
            - 다만 SageMaker 서비스 자체를 켤 필요는 없고, ECR pull만 하면 되므로 별도 서빙 비용은 발생하지 않습니다(ECR 데이터 전송 비용 정도만 있을 수 있음).
        2. **Docker**
        3. 컨테이너가 GPU 사용을 위해 **NVIDIA 드라이버 + nvidia-container-toolkit**
            - 다만 지난 절 "Limitations"에서 봤듯 **CUDA/드라이버 버전이 이미지 태그에 고정**돼 있어서, **로컬 GPU 드라이버 버전과 이미지가 요구하는 CUDA 버전이 안 맞으면 실행이 안 될 수 있습니다** ⇒ 이건 로컬에서 직접 돌릴 때 특히 신경 써야 할 부분입니다.
            - *PyTorch 2.6.0 / Python 3.12 / CUDA 12.4 / Ubuntu 22.04 조합의 최신 안정 태그(v1.84)를 찾았습니다. 드라이버가 CUDA 13.2까지 지원하니 12.4는 문제없이 호환됩니다.*
        4. **SageMaker의 HTTP 계약 재현**
            - 컨테이너를 그냥 `docker run -p 8080:8080 ...`으로 띄우고, `curl -X POST http://localhost:8080/invocations`로 직접 요청을 보내면 됩니다.
            - model.deploy()가 클라우드에서 자동으로 하던 일(포트 매핑, 헬스체크 /ping 등)을 로컬에서는 직접 docker run으로 흉내내는 셈입니다.
        
    - 실습 by 클로드 코드
        
        
        | 항목 | 버전/태그 | 비고 |
        | --- | --- | --- |
        | DLC 이미지 | `763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-inference:2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.84` | PyTorch 2.6.0 / Python 3.12 / CUDA 12.4 / Ubuntu 22.04 |
        | TorchServe | 컨테이너 내장 버전 (토큰 인증 기본 활성화) | `ts/frontend/model-server.jar` |
        | torch / torchvision | 2.6.0+cu124 / 0.21.0+cu124 | 컨테이너 내부 |
        | GPU 드라이버 | 595.84 (CUDA 13.2) | 호스트 |
        | GPU | RTX 4070 Ti SUPER | `--gpus=1` 패스스루 |
        | 테스트 모델 | ResNet18 (torchvision 사전학습) | TorchScript로 변환 후 `.mar` 패키징 |
        
        !image.png
        
        ```python
        #
        docker pull 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-inference:2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.84
        docker images
        IMAGE                                                                                                              ID             DISK USAGE   CONTENT SIZE
        763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-inference:2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.84   f5c4556668fe       24.8GB         8.48GB
        
        # 기동
        docker run -d --name sm-pytorch-local --gpus=1 -p 8080:8080 -p 8081:8081 \
            763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-inference:2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.84
        
        # 확인
        ## TorchServe 엔진이 8080/8081에 바인딩되고 GPU(RTX 4070 Ti SUPER)도 컨테이너 안에서 정상 인식
        ## /ping 호출 시 SageMaker가 요구하는 정확한 JSON 에러 스키마(code/type/message)로 응답
        **docker ps**
        CONTAINER ID   IMAGE                                                                                                              COMMAND                  CREATED              STATUS              PORTS                                                             NAMES
        c4b5001133d6   763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-inference:2.6.0-gpu-py312-cu124-ubuntu22.04-sagemaker-v1.84   "python /usr/local/b…"   About a minute ago   Up About a minute   0.0.0.0:8080-8081->8080-8081/tcp, [::]:8080-8081->8080-8081/tcp   sm-pytorch-local
        
        # 모델 로딩 자체는 완전히 성공했습니다 - 정리하면: 달성한 것
        1. 가중치 다운로드: ResNet18 사전학습 가중치를 컨테이너 내부에서 직접 다운로드 (download.pytorch.org)
        2. TorchScript 변환: 최신 TorchServe가 요구하는 형식(순수 pickle 거부, TorchScript만 허용)에 맞게 torch.jit.trace로 재저장
        3. .mar 패키징: torch-model-archiver + 내장 image_classifier 핸들러로 아카이빙
        4. 컨테이너 재기동 시 자동 로드: WORKER_MODEL_LOADED 상태까지 정상 도달 (GPU 워커에 모델 상주 확인)
        
        # 실제 이미지로 진짜 추론을 호출해보겠습니다 — 앞서 Triton 테스트에서 썼던 cat1.jpg를 재사용
        **curl -s -X POST http://localhost:8080/predictions/resnet18 \
            -T /root/llm-model-inference/ch03/multi_model_serving/tests/images/cat1.jpg \
            -w "\nHTTP %{http_code}\n")**
        *{
          "282": 0.31849998235702515,
          "281": 0.2866626977920532,
          "285": 0.17126737534999847,
          "284": 0.017910882830619812,
          "728": 0.015849340707063675
        }
        HTTP 200*
        
        # 최종 결과 — SageMaker 없이, 완전히 로컬에서 end-to-end 성공
        {
          "TIGER CAT": 0.318,
          "TABBY": 0.287,
          "EGYPTIAN CAT": 0.171,
          "SIAMESE CAT": 0.018,
          "PLASTIC BAG": 0.016
        }
        
        # cat1.jpg를 고양이 관련 클래스 상위 3개(TIGER CAT / TABBY / EGYPTIAN CAT)에 87%가량 몰아준 정상적인 예측입니다.
        # 참고로 같은 이미지를 Triton DenseNet으로 돌렸을 때는 "EGYPTIAN CAT" 압도적 1위(logit 11.5)였는데, 
        # 이번엔 ResNet18이 조금 다른 확신도 분포를 보인 것도 흥미로운 대조점입니다 — 모델 아키텍처가 다르니 당연한 차이입니다.
        
        # 정리: 이번 세션에서 실제로 증명한 것
        1. aws ecr list-images로 실제 존재하는 태그를 조회해서 로컬 GPU 드라이버(CUDA 13.2)와 호환되는 이미지(CUDA 12.4)를 정확히 선택
        2. SageMaker 서비스 없이 docker pull + docker run만으로 진짜 SageMaker PyTorch 추론 컨테이너를 기동
        3. 컨테이너 내부에서 가중치 다운로드 → TorchScript 변환 → .mar 패키징 → 자동 로드까지 SageMaker의 model.deploy()가 클라우드에서 하던 일을 로컬 GPU에서 재현
        4. config.properties의 정확한 프로퍼티명(disable_token_authorization, 처음 추측했던 _check 접미사는 틀렸음)을 실제 jar 바이너리에서 직접 확인해 수정
        5. /ping, /models, /predictions/resnet18 전부 SageMaker의 표준 HTTP 계약 그대로 로컬에서 정상 응답
        
        ```
        
        ```python
        # docker logs ...
        Torchserve version: 0.12.0
        TS Home: /usr/local/lib/python3.12/site-packages
        Current directory: /
        Temp directory: /tmp
        Metrics config path: /usr/local/lib/python3.12/site-packages/ts/configs/metrics.yaml
        Number of GPUs: 1
        Number of CPUs: 16
        Max heap size: 6340 M
        Python executable: /usr/local/bin/python
        Config file: /home/model-server/config.properties
        Inference address: http://0.0.0.0:8080
        Management address: http://0.0.0.0:8081
        Metrics address: http://127.0.0.1:8082
        Model Store: /home/model-server/model-store
        Initial Models: resnet18=resnet18.mar
        Log dir: /logs
        Metrics dir: /logs
        Netty threads: 0
        Netty client threads: 0
        Default workers per model: 1
        Blacklist Regex: N/A
        Maximum Response Size: 6553500
        Maximum Request Size: 6553500
        Limit Maximum Image Pixels: true
        Prefer direct buffer: false
        Allowed Urls: [file://.*|http(s)?://.*]
        Custom python dependency for model allowed: false
        Enable metrics API: true
        Metrics mode: LOG
        Disable system metrics: true
        Workflow Store: /home/model-server/model-store
        CPP log config: N/A
        Model config: N/A
        System metrics command: default
        Model API enabled: false
        2026-08-08T22:33:26,650 [INFO ] main org.pytorch.serve.servingsdk.impl.PluginsManager -  Loading snapshot serializer plugin...
        2026-08-08T22:33:26,659 [INFO ] main org.pytorch.serve.ModelServer - Loading initial models: resnet18.mar
        2026-08-08T22:33:27,071 [DEBUG] main org.pytorch.serve.wlm.ModelVersionedRefs - Adding new version 1.0 for model resnet18
        2026-08-08T22:33:27,071 [DEBUG] main org.pytorch.serve.wlm.ModelVersionedRefs - Setting default version to 1.0 for model resnet18
        2026-08-08T22:33:27,071 [INFO ] main org.pytorch.serve.wlm.ModelManager - Model resnet18 loaded.
        2026-08-08T22:33:27,071 [DEBUG] main org.pytorch.serve.wlm.ModelManager - updateModel: resnet18, count: 1
        2026-08-08T22:33:27,075 [INFO ] main org.pytorch.serve.ModelServer - Initialize Inference server with: EpollServerSocketChannel.
        2026-08-08T22:33:27,075 [DEBUG] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerLifeCycle - Worker cmdline: [/usr/local/bin/python, /usr/local/lib/python3.12/site-packages/ts/model_service_worker.py, --sock-type, unix, --sock-name, /tmp/.ts.sock.9000, --metrics-config, /usr/local/lib/python3.12/site-packages/ts/configs/metrics.yaml]
        2026-08-08T22:33:27,101 [INFO ] main org.pytorch.serve.ModelServer - Inference API bind to: http://0.0.0.0:8080
        2026-08-08T22:33:27,101 [INFO ] main org.pytorch.serve.ModelServer - Initialize Management server with: EpollServerSocketChannel.
        2026-08-08T22:33:27,102 [INFO ] main org.pytorch.serve.ModelServer - Management API bind to: http://0.0.0.0:8081
        2026-08-08T22:33:27,102 [INFO ] main org.pytorch.serve.ModelServer - Initialize Metrics server with: EpollServerSocketChannel.
        2026-08-08T22:33:27,102 [INFO ] main org.pytorch.serve.ModelServer - Metrics API bind to: http://127.0.0.1:8082
        Model server started.
        2026-08-08T22:33:27,833 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - s_name_part0=/tmp/.ts.sock, s_name_part1=9000, pid=113
        2026-08-08T22:33:27,834 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Listening on port: /tmp/.ts.sock.9000
        2026-08-08T22:33:27,836 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Successfully loaded /usr/local/lib/python3.12/site-packages/ts/configs/metrics.yaml.
        2026-08-08T22:33:27,836 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - [PID]113
        2026-08-08T22:33:27,836 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Torch worker started.
        2026-08-08T22:33:27,836 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Python runtime: 3.12.12
        2026-08-08T22:33:27,837 [DEBUG] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - W-9000-resnet18_1.0 State change null -> WORKER_STARTED
        2026-08-08T22:33:27,839 [INFO ] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Connecting to: /tmp/.ts.sock.9000
        2026-08-08T22:33:27,842 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Connection accepted: /tmp/.ts.sock.9000.
        2026-08-08T22:33:27,843 [DEBUG] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Flushing req.cmd LOAD repeats 1 to backend at: 1786228407843
        2026-08-08T22:33:27,844 [INFO ] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Looping backend response at: 1786228407844
        2026-08-08T22:33:27,862 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - model_name: resnet18, batchSize: 1
        2026-08-08T22:33:28,781 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Enabled tensor cores
        2026-08-08T22:33:28,781 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - OpenVINO is not enabled
        2026-08-08T22:33:28,781 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - proceeding without onnxruntime
        2026-08-08T22:33:28,781 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Torch TensorRT not enabled
        2026-08-08T22:33:28,907 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - '/tmp/models/3b8ef2b0a6964bb2b2d7d7109d18c77c/index_to_name.json' is missing. Inference output will not include class name.
        2026-08-08T22:33:28,910 [INFO ] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Backend response time: 1066
        2026-08-08T22:33:28,910 [DEBUG] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - W-9000-resnet18_1.0 State change WORKER_STARTED -> WORKER_MODEL_LOADED
        2026-08-08T22:33:28,911 [INFO ] W-9000-resnet18_1.0 TS_METRICS - WorkerLoadTime.Milliseconds:1837.0|#WorkerName:W-9000-resnet18_1.0,Level:Host|#hostname:ac18ddce47c8,timestamp:1786228408
        2026-08-08T22:33:28,911 [INFO ] W-9000-resnet18_1.0 TS_METRICS - WorkerThreadTime.Milliseconds:2.0|#Level:Host|#hostname:ac18ddce47c8,timestamp:1786228408
        2026-08-08T22:33:35,488 [INFO ] pool-2-thread-2 ACCESS_LOG - /172.17.0.1:52976 "GET /ping HTTP/1.1" 200 3
        2026-08-08T22:33:35,489 [INFO ] pool-2-thread-2 TS_METRICS - Requests2XX.Count:1.0|#Level:Host|#hostname:ac18ddce47c8,timestamp:1786228415
        2026-08-08T22:33:35,501 [INFO ] epollEventLoopGroup-3-2 ACCESS_LOG - /172.17.0.1:42178 "GET /models HTTP/1.1" 200 0
        2026-08-08T22:33:35,502 [INFO ] epollEventLoopGroup-3-2 TS_METRICS - Requests2XX.Count:1.0|#Level:Host|#hostname:ac18ddce47c8,timestamp:1786228415
        2026-08-08T22:33:42,867 [INFO ] epollEventLoopGroup-3-3 TS_METRICS - ts_inference_requests_total.Count:1.0|#model_name:resnet18,model_version:default|#hostname:ac18ddce47c8,timestamp:1786228422
        2026-08-08T22:33:42,868 [DEBUG] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Flushing req.cmd PREDICT repeats 1 to backend at: 1786228422868
        2026-08-08T22:33:42,868 [INFO ] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Looping backend response at: 1786228422868
        2026-08-08T22:33:42,869 [INFO ] W-9000-resnet18_1.0-stdout MODEL_LOG - Backend received inference at: 1786228422
        2026-08-08T22:33:43,062 [INFO ] W-9000-resnet18_1.0-stdout org.pytorch.serve.wlm.WorkerLifeCycle - result=[METRICS]HandlerTime.Milliseconds:192.67|#ModelName:resnet18,Level:Model|#type:GAUGE|#hostname:ac18ddce47c8,1786228423,9ce280c2-af3a-4ed2-8306-ee9dc7b718f3, pattern=[METRICS]
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0 org.pytorch.serve.wlm.BatchAggregator - Sending response for jobId 9ce280c2-af3a-4ed2-8306-ee9dc7b718f3
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0 ACCESS_LOG - /172.17.0.1:52988 "POST /predictions/resnet18 HTTP/1.1" 200 196
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0-stdout MODEL_METRICS - HandlerTime.ms:192.67|#ModelName:resnet18,Level:Model|#hostname:ac18ddce47c8,requestID:9ce280c2-af3a-4ed2-8306-ee9dc7b718f3,timestamp:1786228423
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0-stdout org.pytorch.serve.wlm.WorkerLifeCycle - result=[METRICS]PredictionTime.Milliseconds:192.8|#ModelName:resnet18,Level:Model|#type:GAUGE|#hostname:ac18ddce47c8,1786228423,9ce280c2-af3a-4ed2-8306-ee9dc7b718f3, pattern=[METRICS]
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0 TS_METRICS - Requests2XX.Count:1.0|#Level:Host|#hostname:ac18ddce47c8,timestamp:1786228423
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0-stdout MODEL_METRICS - PredictionTime.ms:192.8|#ModelName:resnet18,Level:Model|#hostname:ac18ddce47c8,requestID:9ce280c2-af3a-4ed2-8306-ee9dc7b718f3,timestamp:1786228423
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0 TS_METRICS - ts_inference_latency_microseconds.Microseconds:194864.981|#model_name:resnet18,model_version:default|#hostname:ac18ddce47c8,timestamp:1786228423
        2026-08-08T22:33:43,063 [INFO ] W-9000-resnet18_1.0 TS_METRICS - ts_queue_latency_microseconds.Microseconds:110.92|#model_name:resnet18,model_version:default|#hostname:ac18ddce47c8,timestamp:1786228423
        2026-08-08T22:33:43,064 [DEBUG] W-9000-resnet18_1.0 org.pytorch.serve.job.RestJob - Waiting time ns: 110920, Backend time ns: 195595017
        2026-08-08T22:33:43,064 [INFO ] W-9000-resnet18_1.0 TS_METRICS - QueueTime.Milliseconds:0.0|#Level:Host|#hostname:ac18ddce47c8,timestamp:1786228423
        2026-08-08T22:33:43,064 [INFO ] W-9000-resnet18_1.0 org.pytorch.serve.wlm.WorkerThread - Backend response time: 195
        2026-08-08T22:33:43,064 [INFO ] W-9000-resnet18_1.0 TS_METRICS - WorkerThreadTime.Milliseconds:1.0|#Level:Host|#hostname:ac18ddce47c8,timestamp:1786228423
        ```
        
- **Option 4: Bring Your Own Code Script Mode(직접 서빙 코드 작성) - Large Model Inference (LMI) ,**
    - 커스터마이징 단계가 올라가면 다음 단계는 직접 서빙 코드를 작성하는 것입니다. AWS SageMaker에서는 추론을 위해 스크립트 모드를 사용해 이 작업을 수행합니다. 스크립트 모드에서는 기본 프레임워크는 SageMaker가 제공하는 컨테이너에 의존하지만, 모델 로딩과 예측 로직을 구현하는 진입점 스크립트를 직접 제공합니다.
    - 이 덕분에 훨씬 유연하게 사용할 수 있는데, 맞춤형 전처리와 후처리를 정의할 수 있고, 비표준 입출력 형식도 지원하며, 하나의 컨테이너 안에 여러 모델을 불러올 수도 있습니다. 단점은 이제 코드를 직접 작성하고 유지보수해야 한다는 점인데, 이전 옵션들은 별도의 추론 코드를 작성할 필요가 없었습니다.
        
        
    - **컨테이너는 여전히 AWS가 제공하는 걸 쓰되, 모델 로딩과 추론 로직만 직접 짜서 끼워넣는 방식.**
    - Option 3와의 핵심 차이
        - Option 3: 컨테이너의 기본 동작을 그대로 수용 → 서빙 코드 안 씀
        - Option 4: 컨테이너는 그대로(프레임워크/CUDA/Python 버전 등 여전히 고정) 쓰되, entry-point 스크립트를 직접 작성해서 전처리/후처리 커스터마이징, 비표준 입출력 포맷, 한 컨테이너에 여러 모델까지 가능
        - 대가는 명확합니다 → 이제부터 코드를 직접 쓰고 유지보수해야 함. 지금까지 옵션 1~3은 코드가 전혀 필요 없었죠.
        
    - 예를 들어, SageMaker의 Large Model Inference LMI 컨테이너를 사용해 자체 서빙 구현을 가진 LLM을 호스팅해 보겠습니다.
    - **첫 번째 단계는 모델별 서빙 구성을 정의**하는 것입니다. 다음 코드는 모델의 서빙 엔진과 위치를 모두 지정합니다:
        
        ```python
        **%%writefile my-own-llm/serving.properties**
        engine=Python
        option.tensor_parallel_degree=2
        option.rolling_batch=**vllm**  
        option.s3url=s3://sagemaker-us-west-2-/large-model-lmi/code/my-own-llm
        ```
        
        - option.rolling_batch=vllm : 여기도 우리가 3장에서 직접 통합했던 vLLM이 백엔드로 다시 등장합니다.
        - Option 3의 OPTION_SERVING_LOADER=vllm과 사실상 같은 개념인데, 여기선 **직접 짠 model.py와 결합해서 씁니다.**
        
    - 다음으로, **model.py 라는 파일에 코드를 로드**하고 실행하는 자체 **모델 서빙 모델을 구현**하고, 핸들 함수에서 **모델 서빙 실행 진입점을 구현:**
        - model.py : 실제 서빙 로직, 3개 함수로 구성
        
        ```python
        **%%writefile my-own-llm/model.py**
        import os
        # ...
        PAD_TOKEN_ID = 50256
        
        **# initialize model**
        **def initialize(properties):**
        
            model = AutoModel.from_pretrained(model_id)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            model.eval()
            .. .. 
        
        **# execute model**
        **def run_inference(input_texts, onnx_model, tokenizer):**
        
            max_batch_size = 128
            z = torch.empty([0,768]).to("cuda")
            for i in range(0, len(input_texts), max_batch_size):
                logging.info(f"Start Iteration: {i}")
        
                start_time = time.time()
                batch_dict = tokenizer(input_texts[i:i+max_batch_size],\
                     max_length=512, padding=True, truncation=True, \
                     return_tensors='pt').to("cuda")
                logging.info(f"After Tokenize Latency: {time.time() - start_time}")
        
                start_time = time.time()
                with torch.no_grad():
                    outputs = model(**batch_dict)
               
                # ... ..
                z = torch.cat((embeddings,z), 0)
            results = [{"embedding": embedding.tolist(), "index": idx} \
                for idx, embedding in enumerate(z)]
            return {"embeddings": results}
        
        **# model execution entry point
        def handle(inputs: Input) -> None:**
            logging.info("handle : Handle start...")
            global model, tokenizer
            if not model:
                logging.info("handle : initializing model")
                model,tokenizer = initialize(inputs.get_properties())
        
            if inputs.is_empty():
                logging.info("handle : inputs is empty")
                # Model server makes an empty call to warmup the model on startup
                return None
        
            # implement model request pre-process logic
            data = inputs.get_as_json()
            input_sentences = data["inputs"]
            # run model inference
            res = run_inference(input_sentences, model, tokenizer)
            logging.info("handle : Handle End")
            return Output().add_as_json(res)
        ```
        
        - **initialize(properties)**: 모델을 GPU에 로드
            - ModelWorker.__init__이 self.model.to(self.device)로 했던 것과 동일 패턴
        - **run_inference(input_texts, model, tokenizer)**:
            - max_batch_size=128로 잘라가며 토크나이즈(max_length, padding, truncation) → torch.no_grad()로 추론 → 결과 조립.
            - ModelWorker.generate()/generate_forward_batch()와 구조적으로 거의 동일
                - 수동 배칭 루프, 토크나이저 파라미터, torch.no_grad() 컨텍스트까지.
        - **handle(inputs)**: 실제 엔트리포인트. 여기서 주목할 프로덕션 패턴 하나:
            
            ```python
            if inputs.is_empty():
                # Model server makes an empty call to warmup the model on startup
                return None
            ```
            
            - 모델 서버가 **부팅 시 빈 입력으로 한 번 호출해서 모델을 미리 워밍업**시킵니다.
            - ch02에서 봤던 "콜드스타트/워밍업 전략" 논의가 실제 코드 레벨에서 이렇게 구현된다는 걸 보여주는 대목입니다.
            - 이후 로직은 우리 server.py의 /predict 핸들러와 동일한 흐름(JSON 파싱 → 추론 → 결과 반환)이지만, FastAPI 데코레이터 대신 DJL/LMI가 요구하는 handle() 단일 함수 시그니처(Input/Output 객체)로 구현합니다.
            
    - **패키징 :** mode.py, 모델 가중치, serving.properties 등 모델 설정 파일들을 하나의 파일로 묶어 S3 클라우드 저장소에 업로드.
        
        ```python
        # package model file
        %%sh
        tar czvf my-own-llm.tar.gz my-own-llm/
            
        # upload model file to S3
        s3_code_prefix = "large-model-lmi/code/my-own-llm" # increment the version
        bucket = sess.default_bucket()  # bucket to house artifacts
        code_artifact = sess.upload_data("my-own-llm.tar.gz", bucket, s3_code_prefix)
        ```
        
        - model.py + 가중치 + serving.properties를 tar로 묶어 S3에 업로드 → Option 3와 동일한 패턴(image_uris.retrieve → Model → model.deploy())으로 배포.
        - 유일한 차이는 model_data가 이번엔 순수 가중치가 아니라 우리 서빙 코드까지 포함된 아카이브라는 것.
            
            
    - **배포** : 커스터마이징된 서빙 코드와 설정이 포함된 모델 파일을 준비하면, 마지막 단계는 배포입니다.
        
        ```python
        # choose an LMI image.
        image_uri = image_uris.retrieve(
            framework="djl-deepspeed",
            region=sess.boto_session.region_name, 
            version="0.25.0"
        )
        
        # create model object
        model = Model(image_uri=image_uri, model_data=code_artifact, role=role)
        
        # deploy model to an endpoint
        predictor = model.deploy(initial_instance_count=1,
                     instance_type="ml.g5.2xlarge",
                     endpoint_name="my-own-llm-128")
        ```
        
        - 이는 옵션 3과 매우 유사하며, 서빙 이미지를 선택하고, **모델 객체를 생성한 뒤, 모델을 배포**하는 과정을 포함합니다:
        
    - 제약사항
        - 여전히 컨테이너에 베이킹된 프레임워크·Python/OS/CUDA 버전·서빙 라이브러리에 종속됩니다.
        - option.rolling_batch=vllm처럼 vLLM을 켤 수는 있어도, 그 vLLM의 정확한 버전/구성은 컨테이너가 정한 대로입니다.
            - 원하는 vLLM 버전을 직접 pip install해서 쓰는 자유는 없습니다.
        - 그리고 HTTP 인터페이스/요청 스키마 자체는 여전히 못 바꿉니다(Option 3의 8080 포트, /invocations//ping 계약 그대로).
        - 완전한 통제(선호 라이브러리를 원하는 버전으로, 런타임 스택 전체 커스터마이징, 자체 API 정의)가 필요하면 Option 5: Bring Your Own Serving Image로 가야 한다고 예고합니다.
        
    - 언제 쓰나
        - Option 3의 한계가 병목이 될 때:
        - 모델 자체는 지원되는 컨테이너에서 잘 돌아가지만, 입력 전처리가 컨테이너 기본 동작으로 안 되는 경우(커스텀 인코딩, 이미지 변환 등)가 대표적.
        - 반대로 출력 처리는 대체로 비슷한 패턴(필터링/포매팅)이면 되는 경우에 적합하다고 정리합니다.
    
- **Option 5: Bring Your Own Serving Image 직접 제공 이미지 가져오기**
    - 이 절은 클라우드 스펙트럼의 최고 커스터마이징 단계: 사실상 3장에서 우리가 직접 만든 것과 정확히 같은 패턴을 SageMaker 위에 얹는 옵션.
    - Option 5: Bring Your Own Serving Image 직접 제공 이미지 가져오기
        - 컨테이너 이미지를 통째로 직접 가져오는 방식입니다.
        - SageMaker는 여전히 배포(클러스터에 컨테이너 올리기)와 엔드포인트 URL 제공은 담당하지만, 컨테이너 내부는 100% 사용자 책임입니다:
        - 어떤 프로그래밍 언어든, 어떤 프레임워크든(SageMaker가 기본 지원 안 하는 것도) 사용 가능
        - 커스텀 추론 코드, 시스템 의존성, 네트워크 설정까지 자유
    - SageMaker가 보는 "블랙박스" 계약
        - SageMaker는 컨테이너를 HTTP 요청이 들어가고 응답이 나오는 특정 포트/경로를 지키는 블랙박스로만 취급합니다.
        - 이게 바로 우리가 지난 대화에서 실제로 씨름했던 /ping(GET), /invocations(POST), 포트 8080이라는 계약이고,
        - 로컬에서 SageMaker PyTorch DLC를 직접 기동하고 /ping·/predictions를 호출해봤던 게 바로 이 계약의 실체를 확인한 것.
        
    - **제약 사항**
        - 컨테이너를 직접 빌드·유지보수·업데이트해야 함, SageMaker의 헬스체크/추론 엔드포인트 요구사항 준수 책임도 전적으로 사용자
        - 테스트/디버깅도 더 복잡함 : Dockerfile 작성, 앱 구현, ECR에 푸시, 더 장황한 API 호출까지 직접 관리
        - **분산 서빙의 한계: 서빙 인스턴스 간 조율(분산 KV 캐싱, 프롬프트 캐싱, 요청 라우팅)이 필요하면 이 옵션으로는 부족** → Option 6로 가야 함 (다음 절에서 다룰 것으로 예상)
        
    - **언제 쓰나** : **SageMaker 기본 제공 컨테이너의 한계가 발목을 잡을 때 쓰는 탈출구:**
        - 모델이 SageMaker가 지원 안 하는 스택/서빙 프레임워크에 의존, 최신 버전이 아직 없음, 또는 대규모 커스터마이징이 필요
        - 모델 코드를 넘어서는 완전한 제어가 필요(시스템 레벨 최적화, 특정 리눅스 배포판)
        - 한 컨테이너 안에 여러 프로세스/서비스를 묶고 싶을 때 - 예: 가격/사용자 메타데이터 기반 전용 메트릭 수집 보조 서비스를 모델과 나란히 실행
    
- **Option 6: Build Your Own Serving Infrastructure 자체 서빙 인프라 구축하기**
    - Option 1~5와의 근본적 차이
        - Option 1(Bedrock)부터 Option 5(직접 컨테이너)까지 **전부 AWS의 서빙 스택(SageMaker의 엔드포인트 관리)을 어느 정도는 계속 활용**합니다
        - 컨테이너 내부를 100% 통제해도(Option 5), **배포·스케일링·엔드포인트 URL은 여전히 SageMaker가 관리**함.
    - **Option 6**은 그마저도 벗어나 **클라우드 인프라**(예: 관리형 Kubernetes = EKS) 위에 **처음부터 서빙 플랫폼 전체를 직접 짓는 것**입니다.
        - 서빙 이미지도 직접 만들고, 런타임도 직접 선택(Triton, vLLM, TensorRT-LLM, KServe, Ray Serve — 앞서 "오픈소스 스택" 절에서 정확히 이 조합으로 실습했던 그 목록입니다), GPU 노드 그룹에서 직접 돌립니다.
        
    - 무엇을 떠안게 되는가
        - 트래픽 관리, 오토스케일링, 보안, 관측성, 비용 통제 — 4장 초반의 그림 4-6에서 봤던 7개 레이어 전체를 사실상 직접 소유하게 됩니다.
        - Option 1→6으로 갈수록 AWS에 위임하던 레이어가 하나씩 사용자 책임으로 넘어오다가, Option 6에서는 (물리 GPU 하드웨어 자체를 제외한) 거의 모든 레이어를 직접 운영하게 되는 셈입니다.
        - 그래도 완전히 맨땅에서 시작하는 건 아니고, AWS의 관리형 프리미티브는 계속 활용 가능합니다:
        - 인프라: EKS, ALB/NLB, ECR, S3, EFS/EBS, IAM/IRSA, Karpenter/Cluster Autoscaler, CloudWatch
        - Kubernetes 애드온: Prometheus/Grafana(모니터링), OpenTelemetry(추적), Fluent Bit(로깅), CNI/NetworkPolicy(네트워킹), Gatekeeper/Kyverno(정책), Argo CD/Rollouts(배포)
        
    - **언제 쓰나 (4가지 시나리오)**
        - **서빙 런타임 완전 통제**: 커널, 배칭, 토크나이제이션, 커스텀 사이드카, 비표준 API(gRPC, SSE) - SageMaker의 고정된 /invocations 계약으로는 안 되는 것들
        - **공격적인 비용/성능 튜닝**: 스팟 GPU 활용, GPU 공유(MIG/MPS), 모델 빈패킹, TPS(초당 토큰) 기반 커스텀 오토스케일링
        - **엄격한 컴플라이언스/데이터 격리**: 프라이빗 클러스터, VPC 전용 egress, 테넌트별 격리, 커스텀 감사 추적
        - **최신 하드웨어/특수 최적화**: 스펙큘레이티브 디코딩, KV 캐시 샤딩, 고급 라우팅/로드밸런싱 - 매니지드 서비스에 아직 없는 최적화 기법
- **6단계를 자동차로 비유**
    - **Option 1 — Bedrock ⇒ 택시**
        
        ```python
        목적지만 말한다.
        차량 관리 신경 안 쓴다.
        ```
        
        - Model/GPU/Container 관리 없음.
        
    - **Option 2 — JumpStart ⇒ 렌터카**
        - 차종은 고를 수 있지만 많이 준비되어 있습니다.
        
    - **Option 3 — Bring Your Own Model ⇒ 엔진은 내 것이지만 차량 Platform은 AWS**
        - 미리 제공되는 DLC Container를 사용합니다.
        
    - **Option 4 — Bring Your Own Code ⇒ Container는 AWS가 제공하지만:**
        
        ```python
        # inference 코드를 직접 작성합니다. 
        preprocessing
        model loading
        prediction
        postprocessing
        
        ```
        
    - **Option 5 — Bring Your Own Serving Image ⇒ Docker Image까지 직접 만듭니다.**
        
        ```python
        # 아래를 원하는 대로 구성할 수 있습니다. SageMaker는 Container 실행과 Endpoint 등을 관리합니다.
        Docker
        CUDA
        Python
        vLLM
        Libraries
        Model
        Serving Code
        ```
        
    - **Option 6 — Build Your Own Infrastructure ⇒ 이제 거의 모든 것을 직접 합니다.**
        
        ```python
        EKS
        +
        GPU Nodes
        +
        vLLM
        +
        Triton
        +
        Ray Serve
        +
        Karpenter
        +
        Prometheus
        +
        Gateway
        ```
        
        - 이 단계에서 Serving runtime, Traffic, Autoscaling, Security, Observability, Cost control 등을 직접 책임진다
    
- **Comparing the Options 선택지 비교하기**
    - 모든 사람에게 딱 맞는 서빙 방법은 없습니다. 각 회사와 각 팀은 서로 다른 역량, 비즈니스 모델, 그리고 프로젝트 일정을 가지고 있습니다.
    - 특정 상황에서 어떤 옵션이 가장 적합한지 평가할 때, 보통 사용 편의성과 제어력 사이의 균형부터 고려하고, 그 다음 비용이나 성능 같은 여러 관점에서 평가를 진행합니다.
        1. 1차 기준: 사용 편의성 vs 통제권의 트레이드오프
        2. 그다음: 비용, 성능 등 다른 관점들로 추가 평가
        
    - 그림 4-8은 사용 편의성부터 시작해 사용 가능한 옵션들 중에서 선택할 수 있도록 안내하는 구조를 보여줍니다.
        
        !Figure 4-8. Ease of use 기준 serving option decision tree
        
        Figure 4-8. Ease of use 기준 serving option decision tree
        
        - 그림 4-8의 의사결정 트리가 사용 편의성부터 시작하는 이유는, AWS 서비스/컴포넌트를 많이 활용할수록 모델을 더 빨리 띄울 수 있기 때문입니다. →하지만 책은 곧바로 "개발 속도는 여러 요인 중 하나일 뿐, 운영/유지보수 비용도 똑같이 중요하다"고 설명합니다.
        
    - 흔한 패턴: 단순하게 시작 → 성숙하면서 커스터마이징 강화
        - 많은 팀이 아이디어 검증은 가장 단순한 옵션(Bedrock)으로 시작하고, 프로젝트가 성숙하거나 요구사항이 커지면 더 커스터마이징된 옵션으로 옮겨간다고 설명합니다.
    - 실제 사례: Qwen3 모델의 여정
        
        ```python
        ┌─────────────────────────┬────────────────────────────────────────────────┬─────────────────────────────┐
        │          단계            │                      옵션                       │          과금 방식             │
        ├─────────────────────────┼────────────────────────────────────────────────┼─────────────────────────────┤
        │ 초기(검증)                │ Option 1 (Bedrock)                             │ 입력 100만 토큰당 $0.10        │
        ├─────────────────────────┼────────────────────────────────────────────────┼─────────────────────────────┤
        │ 사용량(처리량) 증가         │ Option 2/3 (JumpStart/DLC, 자기 계정에 호스팅)      │ 서버 인스턴스 시간당 $1.172      │
        ├─────────────────────────┼────────────────────────────────────────────────┼─────────────────────────────┤
        │ 처리량↑·지연↓ 요구 심화      │ Option 4/5/6                                   │ 커스터마이징 수준에 따라          │
        └─────────────────────────┴────────────────────────────────────────────────┴─────────────────────────────┘
        ```
        
    - 손익분기점을 직접 계산해보면 — Bedrock의 토큰당 과금과 전용 인스턴스의 시간당 과금이 같아지는 처리량:
    - 즉 초당 약 3,255 토큰 이상을 꾸준히 처리한다면 Bedrock보다 전용 인스턴스를 직접 호스팅하는 게 더 저렴해지는 지점입니다(출력 토큰 과금·인스턴스 유휴시간 등은 단순화해서 제외한 근사치입니다).
    - 이런 손익분기점 계산이 바로 "언제 옵션을 갈아탈지" 판단하는 실전 방법론이고, 이 챕터 마지막에 나올 성능 지표(레이턴시/처리량) 장이 바로 이런 계산의 근거 데이터를 어떻게 측정하는지를 다룰 것으로 예고됩니다.

### Build or Buy? Understanding Strategies

- 직접 만들까요, 아니면 사서 쓸까요? 전략 이해하기
    - 많은 사람들이 자체 서비스 스택을 구축할지, 아니면 클라우드 벤더가 제공하는 서비스를 사용할지에 대해 논쟁하는 것을 들어왔습니다. 이 책의 두 저자는 10년 넘게 다양한 모델 서빙 시스템을 구축하고 유지해 왔으며, 이것이 단순한 이분법이 아님을 말씀드릴 수 있습니다. 건축과 임대 중 선택은 단순한 전환이 아니라 하나의 스펙트럼입니다!
    - 기본 원칙부터 서비스 스택을 구축하는 방법을 잘 이해할수록, 클라우드 공급업체의 관리형 옵션을 더 정확히 평가하고 숨겨진 트레이드오프를 발견하며 언제든지 얼마나 커스터마이징할지 결정할 수 있습니다. 그림 4-8의 의사결정 나무와 마찬가지로, 어느 한쪽이 아니라는 관점에서 통제의 정도를 생각하세요.
    - 실제로 대부분의 팀은 중간 정도 방식으로 운영하는데, 벤더 플랫폼을 사용하면서 커스텀 핸들러, 자동 스케일링 신호, 라우팅 로직, 비용 제어 같은 맞춤형 기능을 추가합니다. 완전한 '직접 구축'(BYO) 방식은 보통 제어, 대규모 비용 효율성, 또는 엄격한 규정 준수 요구사항 때문에 필요할 때만 적용됩니다. 예를 들어, 벤더 락인을 피하고 여러 클라우드 제공업체에서 시스템을 운영할 수 있도록 BYO를 선택할 수 있습니다.
    
- Why Knowing How to Build Helps: Even If You Won’t Build 직접 짓지 않더라도 건축하는 법을 아는 것이 왜 도움이 되는가
    - 클라우드 벤더를 사용한다면 모든 것을 직접 구축할 필요는 없지만, 자체 개발한 서빙 스택(2장과 3장에서 설명한 대로)을 이해하는 것이 매우 중요합니다. 이해를 바탕으로 다음을 할 수 있습니다:
    1. **벤더 기능 해독(Decode vendor features)**
        - 벤더가 제공하는 옵션 노브가 배칭·캐싱·양자화·어댑터 로딩 중 뭐에 대응하는지, 한계가 어디인지 알아볼 수 있게 됩니다.
        - AWS LMI 컨테이너의 OPTION_SERVING_LOADER=vllm, OPTION_TENSOR_PARALLEL_DEGREE, OPTION_MAX_ROLLING_BATCH_SIZE 같은 설정을 봤을 때 바로 "3장에서 직접 만졌던 vLLM의 텐서 병렬화·연속 배칭이구나"라고 알아본 게 정확히 이겁니다.
        - Ray Serve의 @serve.multiplexed를 봤을 때도 "이거 손으로 짠 ModelManager의 LRU 캐시랑 똑같은 기능이네"라고 즉시 대응시킬 수 있었죠.
        
    2. **트레이드오프 정량화(Quantify trade-offs)**
        - "bring your own model(Option 3) vs bring your own code(Option 4)" 같은 **벤더 기능/접근법 사이의 트레이드오프를 제대로 분석**할 수 있습니다.
        - 바로 직전 절에서 Bedrock(토큰당 과금)과 전용 인스턴스(시간당 과금)의 손익분기점을 초당 3,255토큰으로 실제 계산으로 확인
        
    3. **커스터마이징 (80/20 원칙)**
        - 벤더 기본값을 80%는 그대로 쓰고, 깊은 통제가 필요한 20%만 외과수술 하듯 정밀하게 교체.
        - SageMaker DLC 컨테이너 실습이 정확히 이 패턴이었습니다:
            - TorchServe 엔진, 포트 8080 계약, image_classifier 기본 핸들러는 그대로(80%) 받아들이고, 딱 필요한 두 곳만 수술했습니다
                1. 커스텀 모델(.mar) 주입
                2. config.properties의 토큰 인증 설정
                
    4.  **디버깅/트러블슈팅**
        - 벤더 솔루션은 블랙박스처럼 동작하고, 설정/내부 로직 문서가 부족하며, 로깅도 다 안 잡히는 게 흔한 골칫거리라고 명시합니다.
    
- Our Selection Strategy 선택 전략 : 변화에 적응하는 전략이 이긴다
    - 고객과 공급업체가 제공하는 서비스 방식을 계속 사용할지, 아니면 더 맞춤화된 솔루션으로 전환할지 논의할 때 저희가 실제로 매우 유용하게 활용하는 접근법을 소개합니다:
        - 예측 지연 시간과 처리량 같은 서비스 수준 목표(SLO)가 충족되고, 비용이 허용 가능하며, 기능 속도와 일정이 가장 중요하다면 벤더 관리 방식을 유지하세요.
        - 몇몇 모델 엔드포인트에 특별한 배치, 라우팅, 성능 튜닝 또는 테넌트별 격리가 필요할 때 하이브리드를 사용하세요.
        - 하드웨어, 런타임, 독립적인 네트워킹을 직접 제어해야 하거나, 서비스 비용이 높아 세밀한 튜닝이 필요할 때는 BYO를 선택하세요.
        - 볼륨이 낮은 속도로 안정되거나 시스템 복잡성이 성과를 내지 못한다면 벤더 관리 방식으로 다시 돌아가세요.
            
            
    - 서빙 시스템을 구축하는 방법을 배우면, 어느 시점에서든 얼마나 구축하고 커스터마이징할지 선택할 수 있습니다. **성공적인 전략은 유연합**니다.
    - **안정적인 API와 공유 텔레메트리를 유지**하고, 효과적인 부분을 맞춤화하며, 제품과 트래픽, 제약 조건이 **변화함에 따라 스펙트럼 상의 위치도 바뀔 것을 예상**해야 합니다.
    

### Measuring Performance in LLM Serving

- LLM 서빙 성능 측정하기 소개 : ***Latency* 지연 시간 , *Throughput* 처리량**
    - 이 장 전반에 걸쳐 우리는 에이전트 기반 워크플로우, 계층화된 엔터프라이즈 아키텍처, 그리고 빌드 대 클라우드 결정에 대해 논의했습니다.
    - 이러한 설계 선택이 LLM 서비스 시스템의 구조를 형성하지만, 궁극적으로는 측정 가능한 결과를 통해 평가되어야 합니다.
    - 프로덕션 시스템에서는 아키텍처의 우아함만으로는 부족하며, 성능이 실현 가능성, 사용자 경험, 그리고 서비스 비용을 결정합니다.
    - 그래서 성과 지표는 부수적인 것이 아니라, 방향을 제시하는 원칙인 것입니다.
        
        
    - 에이전트 시스템은 다단계 추론 체인 전반에 걸쳐 지연 시간을 증폭시킵니다.
    - 엔터프라이즈 플랫폼은 확장성과 비용 효율성 사이에서 균형을 맞춰야 합니다.
    - 빌드와 클라우드 중 선택은 종종 시스템이 예산 내에서 SLO를 충족할 수 있는지에 달려 있습니다.
    - 이 모든 경우에, 서빙 디자인이 의도한 대로 작동하는지 판단하기 위해 정량적 측정이 필요합니다.
        
        
    - 다음 두 장에서 보여줄 LLM 최적화 기법을 준비하기 위해, 우리는 현재 운영 중인 모델 서비스 시스템에서 일관되게 의존해 온 두 가지 중요한 지표를 소개합니다.
    - 이러한 측정값을 통해 아키텍처의 트레이드오프를 평가하고, 개선 사항을 벤치마킹하며, 최적화 기법의 영향을 수치화할 수 있습니다.
    - 그것들은 다음과 같습니다:
        - ***Latency* 지연 시간** : 처리 및 응답 생성에 필요한 시간
        - ***Throughput* 처리량** : 단위 시간당 처리되는 요청 수 또는 토큰 수
    
- Latency Metrics 지연 시간 지표 : 3개의 정밀한 지표 - **E2E 지연시간, TTFT, ITL/TPOT**
    - LLM 예측 실행 속도를 측정할 때 가장 중요한 세 가지 지표는 **엔드투엔드 지연 시간**, 첫 번째 토큰까지 걸리는 시간(**TTFT**), 그리고 출력 토큰당 시간(**TPOT**)입니다. 하나씩 살펴봅시다:
    - **End-to-end (E2E) latency 종단 간(E2E) 지연 시간**
        - E2E 지연 시간은 머신러닝과 비머신러닝 **워크로드 모두에 걸리는 전체 계산 시간을 측정**하는 비교적 일반적인 용어입니다.
        - LLM의 경우, 모델이 요청을 받은 시점부터 전체 응답을 생성해 완료하는 시점까지의 시간을 의미합니다.
        - E2E 지연 시간에는 필요에 따라 전체 서비스 지연 시간도 포함될 수 있는데, 이는 모델 실행 시간뿐만 아니라 요청 대기(대량 요청 처리 시), 네트워크 지연, 라우팅 시간, 확장 오버헤드 및 기타 다양한 시**스템 수준 요인을 포함한 추가 지연(처리 시간)**을 고려(포함)한 것입니다.
    - **Time to first token (TTFT) 첫 번째 토큰 발생 시간 (TTFT)**
        - TTFT는 모델이 **요청을 받은 시점부터 첫 번째 토큰을 발행하는 시점**까지 **경과한 시간을** 의미합니다.
        - 사용자 입장에서는 챗봇과 같은 사용 사례에서 LLM 모델의 응답 속도, 즉 **고객이 모델이 처음으로 출력한 토큰을 얼마나 빨리 확인**할 수 있는지를 의미합니다.
        - 또한 2장에서 다룬 **프리필 단계**와도 일치하는데, 이 단계에서는 모델이 입력 프롬프트를 처리하고, 전체 문맥에 주의를 기울이며, 이해한 뒤 출력을 생성할 준비를 합니다. 실제로 TTFT는 주로 모델 지연 시간을 논의할 때 사용됩니다.
            - *Prefill — 입력 프롬프트 전체를 처리하고 컨텍스트를 이해하는 단계*
    - **Inter-token latency (ITL) or time per output token (TPOT) 토큰 간 지연 시간(ITL) 또는 출력 토큰당 시간(TPOT)**
        - ITL(또는 TPOT)은 **첫 번째 토큰 이후에 발생하는 모든 토큰이 생성되는 데 걸리는 시간**을 측정합니다.
        - 이는 디코딩 단계(2장 참조)에 해당하며, 모델이 **보통 비교적 일정한 속도**로 토큰을 순차적으로 생성합니다.
            - *Decode — 순차적으로 토큰을 생성하는 단계*
        - 이 지표는 **LLM의 자기회귀 토큰 생성 효율성**을 이해하는 데 매우 중요합니다.
        - TTFT와 마찬가지로, ITL/TPOT도 모델 지연 시간을 논할 때 주로 관련이 있습니다.
        
    - 그림 4-9는 LLM 실행에서 전체 종단 간 지연 시간 내의 프리필 단계와 디코딩 단계에 TTFT와 ITL이 어떻게 대응되는지를 보여줍니다.
    - 토큰화와 디토큰화에 소요되는 시간도 그래프에 포함되어 있습니다.
        
        !Figure 4-9. LLM execution의 주요 latency metrics
        
        Figure 4-9. LLM execution의 주요 latency metrics
        
    - 이제 지연 시간 관련 개념이 명확해졌으니, 이를 계산하는 공식들을 살펴보겠습니다.
    - 가정: ITL 일정, 총 생성 토큰 수 N, 토크나이즈/디토크나이즈 시간은 무시(실제로도 모델 추론 대비 미미해서 보통 무시됨).
    - **종단 간 지연 시간 E2E 지연 시간의 공식**
        - `E2E latency = TTFT + ITL × (N – 1)`
        
    - **첫 번째 토큰 발생 시간 TTFT를 계산하는 공식**
        - TTFT = full tokenization of the input + prefill + decode first token + detokenize first token = prefill + decode first token
        - TTFT = 입력 전체 토큰화 + 프리필 + 첫 번째 토큰 디코딩 + 첫 번째 토큰 디토켄징 = 프리필 + 첫 번째 토큰 디코딩
        
    - **토큰 간 지연 시간 ITL을 계산**
        - ITL = decode one new token + detokenize the new token – detokenize the last token = decode one new token
        - ITL = 새 토큰 하나를 디코딩하고, 그 다음 새 토큰을 디토칸화합니다 – 마지막 토큰을 디토칸화하는 것 = 새 토큰 하나를 디코딩합니다
        
    - 실제 사용 사례에서는 E2E 지연, TTFT, ITL 세 가지 지연 지표 모두 중요하지만, 우선순위는 애플리케이션과 사용 사례에 따라 달라집니다.
    - 유스케이스별 우선순위
        - **에이전틱 워크플로우**(다운스트림 프로세스가 전체 출력에 의존) → **E2E가 최우선.**
            - KnowledgeAgent가 정확히 이 케이스였습니다
            - generate_analysis는 generate_summary의 완성된 전체 출력을 컨텍스트로 받아야 시작할 수 있었으니(체이닝 구조), 중간에 "첫 토큰만 빨리 나오는 것"은 아무 의미가 없고 각 단계의 E2E가 다음 단계를 블로킹했습니다.
        - **챗봇(스트리밍 응답)** → **TTFT가** 사용자 경험에 가장 큰 영향 — 응답성 그 자체
        - **출력이 매우 길 때** → **ITL도 중요해짐** — ITL이 높으면 응답이 "느릿느릿하다"고 체감됨
        
    - 다음 장들에서는 LLM 서비스 지연 시간을 개선하는 기법들을 살펴보겠습니다.
    - 하지만 모든 최적화 기법이 세 가지 지표를 동시에 향상시키는 것은 아닙니다.
    - 몇 가지 타협이 필요하기 때문에, 적절한 기법 선택은 사용 사례의 구체적인 요구사항에 따라 달라집니다.
    
- Throughput Metrics 처리량 지표 : **RPS/RPM , TPS**
    - 처리량은 LLM 서비스에서 핵심 지표 중 하나입니다. 이는 "시스템이 시간이 지남에 따라 몇 개의 예측을 처리할 수 있는가?"라는 질문에 답하기 위해 사용됩니다.
    - 이를 통해 서빙 시스템이 대규모로 결과를 제공하기 위해 자원을 얼마나 효율적으로 사용하는지 알 수 있습니다. 일반적으로 사용되는 처리량 지표는 다음과 같습니다:
        - **Requests per second (RPS) or requests per minute (RPM) 초당 요청 수(RPS) 또는 분당 요청 수(RPM)**
            - RPS와 RPM은 ML 작업뿐만 아니라 비ML 작업에서도 널리 사용되는 처리량 지표입니다.
            - 이 지표들은 모델이나 전체 서빙 인프라가 일정 시간 내에 처리할 수 있는 요청 수를 수치로 나타냅니다.
                - *일정 시간 동안 처리 가능한 요청 수*
            - 하지만 LLM 서비스 측면에서 RPS와 RPM은 LLM 서비스에 특화된 세부적인 부분에서 많은 단점이 있으며, 이에 대해서는 나중에 다루겠습니다.
        - **Tokens per second (TPS) 초당 토큰 수 (TPS)**
            - TPS는 LLM 생성에 특화된 처리량 지표입니다. 이는 서비스를 제공하는 모델이나 LLM이 초당 생성하는 출력 토큰 수를 측정합니다.
                - *초당 생성되는 출력 토큰 수 — 입력 토큰이나 입출력 합산은 포함 안됨*
            - 한 가지 기억할 점은 TPS는 생성된 토큰만 계산하며, 입력 토큰이나 입력·출력 토큰의 합계는 포함하지 않는다는 것입니다.
            - *TPS는 오직 생성된(출력) 토큰만 셉니다. 입력 토큰이나 "입력+출력" 합산이 아닙니다. 이 구분을 놓치면 벤치마크를 잘못 해석하기 쉽습니다.*
        
    - RPS/RPM과 TPS 모두 장단점이 있으며, **어느 쪽도 LLM 서비스 효율성을 완벽하게 단독으로 측정하는 지표는 아닙니다**. 왜 그런지 살펴봅시다.
    - **첫째, RPS와 RPM은 예측 요청 패턴에 민감한데, 요청별로 측정할 경우 긴 입력과 출력이 LLM 서비스 성능에 부정적인 영향을 줄 수 있기 때문**입니다.
        - 그 결과, RPS와 RPM은 입력 및 출력 길이, 그리고 동시 사용자 수와 같은 요소에 크게 좌우됩니다. *← 요청 패턴에 민감*
        - 즉, **서로 다른 트래픽 패턴을 가진 두 워크로드 간에 RPS/RPM을 직접 비교하는 것은 사실상 무의미**합니다. 공정한 비교가 아니기 때문입니다.
    - **둘째, TPS는 유용하지만 조작(**inflate)**될 수 있기 때문에 위험이 있습니다.** TPS는 LLM 분야에서 표준화된 지표이며, 많은 경우 토큰당 비용을 계산하는 데에도 활용됩니다. 하지만 인위적으로 부풀릴 수 있는 몇 가지 방법이 있습니다:
        - **입력 길이를 줄이면 TTFT가 크게 감소**하고, 이는 **요청당 작업 부하를 줄이는 효과**가 있습니다. **이로 인해 TPS가 실제보다 높게 보이게** 됩니다.
        - **더 크거나 최적화된 배치 요청도 TPS를 증가시킬 수 있습니다**. 모델 프로세스 병렬성을 극대화하기 위해 **배치 크기를 늘리거나, 배치 요청의 입력 및/또는 출력 길이를 균일**하게 만들면 **GPU 활용도가 향상되고 GPU 유휴 시간이 줄어들어 TPS가 개선**될 수 있습니다. 그 이유는 다음 두 장에서 설명하겠습니다.
    - **실전 시사점: 벤치마크를 곧이곧대로 믿지 말 것!**
        - 이 절이 은근히 경고하는 건, 벤더가 발표하는 TPS 숫자를 볼 때 "어떤 조건에서 측정했는가"를 따져봐야 한다는 것입니다.
        - 입력을 짧게 잘랐는지, 배치를 인위적으로 최적 구성했는지에 따라 같은 모델도 TPS가 크게 달라 보일 수 있습니다.
        - 이게 몇 절 전 "벤더 기능을 해독하는 능력"("Why Knowing How to Build Helps") 절에서 말한 능력이 바로 여기서 실전에 쓰이는 지점입니다.
        - 밑바닥을 알아야 벤더가 내미는 화려한 TPS 숫자 뒤에 숨은 측정 조건을 의심하고 검증할 수 있습니다.
    
- Best Practices for Performance Measurement 성능 측정을 위한 모범 사례
    - 지금까지 나온 모든 지표(E2E/TTFT/ITL, RPS/TPS)를 "어떻게 실전에서 신뢰할 수 있게 쓸 것인가"로 종합하는 9가지 실전 체크리스트
    1. **지연시간 vs 처리량 트레이드오프 파악**
        - 오프라인/배치 워크로드는 처리량(비용 절감)이, 챗봇/실시간 에이전트 같은 인터랙티브 워크로드는 지연시간(응답성)이 핵심 지표.
        - → 3장의 비용 최적화(3-11) vs 지연시간 최적화(3-12) 설계 대비가 이 원칙의 아키텍처 버전이었습니다.
    2. **유스케이스별 "충분히 좋은" 목표 설정**
        - 1초를 0.5초로 줄이는 게 체감상 의미 없다면, 그 노력을 처리량/비용 최적화로 돌리는 게 낫다는 것
        - 불필요한 과최적화를 막는 실용주의.
        - 앞서 계산한 Bedrock 손익분기점(초당 3,255토큰)도 "이 지점까지는 굳이 안 옮겨도 된다"는 이 원칙의 응용이었습니다.
    3. **E2E를 TTFT/ITL로 분해**
        - 출력 길이가 제한된 시스템이라면 TTFT가 ITL보다 더 중요할 수 있다는 예시. 바로 앞 두 절에서 정의한 개념을 실전에 적용하는 법입니다.
    4. **실제 트래픽 패턴을 최대한 그대로 시뮬레이션**
        - 긴 프롬프트+짧은 답변과 짧은 프롬프트+긴 답변은 완전히 다르게 동작함.
        - 그리고 트래픽은 절대 균일하지 않다(하루/계절별 변동, 버스트로 인한 큐잉 지연/요청 실패).
        - → 우리 KnowledgeAgent 테스트에서 README의 실제 예시 질문들(단순 질의 vs "여러 문서를 비교/분석"하는 복잡한 질의)을 그대로 썼던 게 이 원칙과 맞닿아 있습니다
    5. **실험의 일관성 유지**
        - 한 번에 한 노브만 — 너무 많은 걸 동시에 바꾸면 효과를 분리할 수 없음.
        - → 이건 제가 test_rag_system.py의 버그를 고칠 때 실제로 썼던 방법론입니다:
            - get_context_for_query에 딱 한 줄(빈 documents 체크)만 바꾸고 나머지는 그대로 둔 채 재실행해서 "11/11 통과"라는 명확한 인과관계를 확인했었죠.
    6. **하드웨어 활용률 모니터링**
        - GPU/CPU/메모리 사용량을 추적해서 병목이 모델 자체 때문인지 하드웨어 한계 때문인지 구분.
        - → 우리가 nvidia-smi로 GPU 인식을 반복 확인하고, ch03에서 "모델은 0.24GiB인데 vLLM의 gpu_memory_utilization=0.9 기본값 때문에 14.7GB를 점유한다"는 걸 발견했던 게 이 원칙의 실제 사례였습니다.
    7. **지표를 인위적으로 부풀리지 말 것** — 바로 전 절(TPS 조작 가능성)에서 다룬 경고의 재확인.
    8. **프로덕션에서 지속적으로 모니터링** — 배포 후에도 사용자 행동 변화로 인한 트래픽 급증/실패까지 계속 관찰해야 함.
    9. **테스트 스위트를 주기적으로 재실행**
        - 회귀 방지(새 업데이트가 지연/처리량을 악화시키지 않는지), 스케일링 테스트(블랙프라이데이 같은 피크 시뮬레이션), A/B 테스트(새 최적화 기법을 프로덕션 배포 전에 데이터 기반으로 비교).
        - → 저희가 test_models.py와 test_rag_system.py를 버그 수정 전후로 다시 돌려서 "정말 고쳐졌는지, 다른 게 깨지진 않았는지"를 확인했던 게 축소판 회귀 테스트였습니다.
    
- Summary
    - 이번 장에서는 2장과 3장(내부 추론과 단일/멀티 모델 설계)을 바탕으로, 에이전트 활용, 엔터프라이즈 아키텍처, 빌드와 클라우드 선택, 그리고 서비스 성능 최적화를 위한 지표 등 LLM 서비스 제공을 위한 프로덕션 모범 사례로 한 단계 더 나아갔습니다.
    1. 에이전틱 서빙: KnowledgeAgent(OpenAI 모델 + Planner + Actions)로 서빙이 어떻게 자율성을 뒷받침하는지 보여준 뒤, RAG vs CAG(컨텍스트/KV 캐시에 지식을 미리 로드) 트레이드오프 비교
    2. 엔터프라이즈 아키텍처: 독립적으로 진화 가능한 계층형 아키텍처(그림 4-6) + 이를 구현하는 오픈소스 Kubernetes 스택(그림 4-7)
    3. 빌드 vs 클라우드: 커스터마이징 정도가 점점 커지는 AWS 6가지 옵션 + 선택을 돕는 의사결정 트리. 핵심 테마는 "이분법이 아니라 스펙트럼"이라는 것 — 대부분 팀은 벤더 플랫폼 위에 표적 커스터마이징을 얹은 중간 지점에서 운영하고, 개발 편의성·비용·사용 패턴에 따라 그 균형점을 계속 옮겨간다는 것
    4. 성능 지표 표준화: 지연시간·처리량 두 핵심 지표 + 공정한 벤치마킹·현실적 트래픽 시뮬레이션·하드웨어 활용률 추적·회귀/스케일링 테스트 같은 베스트 프랙티스
    - 다음 장에서는 이 지표들을 구체적인 지연 시간, 처리량, 비용 개선으로 연결하는 방법을 알려드리겠습니다.
    

### 2주차 과제

- **2주차 스터디**에서 학습한 내용 혹은 **LLM 관련 내용(혹은 도전과제)**을 **간략히 정리**하여 **공개된 링크에 글 작성** 후 해당 링크를 **과제제출표**에 공유 🙇🏻‍♂️🙇🏻‍♀️
    - **작성 도구** : 블로그, Github, 개인 홈페이지, 개인 Youtube, ‘페이스북/링크드인 공개 게시 글’ 등
    - **정리 내용(예시)**
        - 해당 주차 스터디에서 학습한 내용을 요약 정리 작성
        - 해당 주차 스터디에서 다룬 주제 기술 1개를 별도 조사 학습해서 정리
        - LLM 서빙 관련 운영 경험 중 기술 내용 위주로 정리
        - 최근 LLM 서빙 관련 새로운 기술에 대한 분석 정리

### 도전 과제

- `도전과제` : 로컬 PC 에 kind(k8s)로 RayService 배포 테스트 해보기 - Guide