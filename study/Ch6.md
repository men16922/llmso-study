- `질문` ***→ 학습을 하시고 스스로 아래 질문에 답변을 해보시기 바랍니다!***
    - "GPU에 더 많은 일을 시키면서, 동시에 불필요한 계산·메모리 사용·데이터 이동은 어떻게 줄일 것인가?”
    - Prefill(compute-bound)과 Decode(memory-bound)라는 성격이 다른 두 워크로드를 하나의 배치 안에서 어떻게 공존시킬 것인가?
    - 모델 품질을 얼마나 희생해야, 얼마만큼의 서빙 성능(지연시간·처리량·메모리)을 얻을 수 있는가?
    
- **챕터 6 소개 : 필수 LLM 최적화 기법**
    - **배경**
        - 이전 장들에서는 LLM을 서빙용으로 최적화하는 것이 왜 중요한지, 그리고 어떤 어려움이 있는지를 보여드렸습니다. 이제부터 두 개 장에 걸쳐 핵심 LLM 최적화 기법들을 하나씩 깊이 있게 다룰 예정이며, 이를 통해 여러분은 자신의 서빙 요구사항에 맞게 언제, 어떻게, 왜 이 기법들을 사용해야 하는지 판단할 수 있는 지식을 갖추게 됩니다.
        - 이번 6장에서는 대부분의 최적화 개념을 이해하고 최적화 목표의 상당 부분을 달성하는 데 도움이 되는 필수(essential) 기법들에 집중합니다. 더 고급 기법들과 업계 트렌드는 7장으로 미룹니다.
    - **이 장에서 다루는 내용:**
        1. 요청 배칭 및 스케줄링(Request batching and scheduling)
            - 목적: 더 나은 병렬성과 GPU 활용률(utilization) 달성
        2. 어텐션 최적화(Attention optimization)
            - 목적: 더 나은 연산 효율성, 필요 연산량 감소, 더 나은 메모리 관리 달성
        3. 모델 압축(Model compression)
            - 목적: 더 작은 모델, 더 적은 메모리 이동, 그리고/또는 더 적은 연산량 달성
        4. 프리픽스 캐싱(Prefix caching)
            - 이전 프롬프트를 캐싱해서 재사용하는 기법
            - 이를 효율적으로 수행하는 방법과 높은 캐시 히트율(cache-hit rate)을 얻는 방법까지 포함
    - **5장 배운 개념 ⇒ 6장 학습 예정**
        - GPU 활용률·산술 강도(compute-bound vs memory-bound) ⇒ 배칭/스케줄링으로 GPU를 더 바쁘게(포화) 만들어 활용률↑
        - Prefill이 compute-bound, Decode가 memory bandwidth-bound ⇒ 어텐션 최적화로 연산량 자체를 줄이거나 메모리 접근 패턴 개선
        - 모델 크기 = 파라미터 수 × 정밀도(bytes) ⇒ 모델 압축(양자화 등)으로 메모리 사용량·이동량 직접 감소
        - KV 캐시가 모델보다 커질 수 있음(예: 32GB > 14GB) ⇒ 프리픽스 캐싱으로 반복되는 프롬프트의 KV 캐시를 재사용해 낭비 감소
    
- **핵심 요약** : LLM serving의 핵심 최적화 기법
    - LLM serving의 핵심 최적화 4가지 기법 - GPU에 더 많은 일을 시키되, 불필요한 계산·메모리 사용·데이터 이동은 어떻게 줄일 것인가?
        
        !mermaid-diagram.png
        
        - **Batching and scheduling**: GPU idle time을 줄이고 throughput을 높인다.
        - **Attention and kernel optimization**: attention 계산과 memory movement를 줄인다. (KV Cache와 HBM↔SRAM 데이터 이동을 줄임)
        - **Model compression**: 모델 자체를 작고 빠르게 만든다. quantization, distillation, pruning으로 memory footprint와 연산 비용을 줄인다.
        - **Prefix caching**: 이전 Prompt 계산 결과를 재사용한다. 반복 prefix를 재사용해 prefill 비용을 줄인다.
    - 최적화는 하나의 설정으로 끝나지 않는다. TTFT, TPOT/ITL, throughput, GPU memory, accuracy, operational complexity 사이의 trade-off를 함께 측정해야 한다.
    
- [**추천 영상/PY**] The full LLM Inference Engineering series playlist 재생목록 - Youtube
    - [PY] 01 - LLM 추론의 공학적 배경: 메모리 벽 - Youtube
    - [PY] 02 - LLM 추론의 공학적 원리: GPU 내부 들여다보기 - Youtube
    - [PY] 03 - LLM 추론의 공학: 커널과 메모리 - Youtube
    - **[PY] 04 - LLM 추론의 엔지니어링: 양자화(Quantization)** - Youtube
    - **[PY] 05 - LLM 추론의 공학적 원리: 병렬 처리** - Youtube
    - **[PY] 06 - LLM 추론의 엔지니어링: 전문가 혼합(Mixture of Experts) 모델** - Youtube
    - **[PY] 07 - LLM 추론의 공학: 프로덕션 환경에서의 서빙** - Youtube
    - [PY] 08 - LLM 추론의 공학적 원리: 추측적 디코딩과 긴 컨텍스트 - Youtube
    - [PY] 09 - The Engineering Behind LLM Inference: The Whole Stack - Youtube
    

### Request Batching and Scheduling-Level Optimizations

- 들어가며 : 배치 및 스케줄링 수준 최적화 요청하기
    - 2장에서는 서빙을 **오프라인 서빙**과 **실시간 온라인 서빙**으로 나누었습니다. 실시간 온라인 서비스에서는 사용자가 요청을 보낼 때마다 요청을 받지만, 오프라인 서비스에서는 요청이 이미 준비되어 있어 한 번에 모두 묶어서 큰 텐서 입력으로 만들어 모델에 넣을 수 있습니다. 즉, 하나씩 보내는 대신에요.
        - **오프라인 서빙(offline serving)**: 요청들이 이미 다 확보된 상태 → 하나로 배칭(batching)해서 큰 텐서 입력으로 만들어 한꺼번에 모델에 투입 가능
        - **실시간 온라인 서빙(real-time online serving)**: 사용자가 보내는 대로 요청이 하나씩 들어옴
    - 서빙 중 요**청을 묶어서 처리하면 응답 속도가 느려질 수 있지**만, **더 높은 처리량을 달성**할 수 있습니다. 왜 그런지 이해하기 위해, 5장에서 배운 **산술 강도라는 개념을 활용해 좀 더 깊이** 들어가 봅시다.
        - 여러 요청을 배치로 묶으면 → 행렬의 M 차원(배치 크기)이 커짐 → 산술 강도가 올라감 → GPU 연산 유닛을 더 잘 활용(포화)할 수 있게 됨 → 동일한 GPU로 훨씬 더 많은 토큰/요청을 처리 가능
    - **요지**: 배칭은 단순히 "여러 요청을 한꺼번에 처리하는 것" **이상의 의미**가 있습니다 → 개별 요청 하나로는 **낭비되던 GPU 연산력을, 여러 요청을 묶어 행렬 크기를 키움으로써 산술 강도를 높여 실제로 활용**하게 만드는 것이 핵심 원리입니다.
    
- **Why Do We Need Batching in Real-Time Serving?** 실시간 서빙에서 배칭이 왜 필요한가요? - Youtube
    - Prefill vs Decode 복습 (2장/5장 연결)
    - **Prefill 단계**: 모델이 입력 프롬프트를 이해하는 단계. **입력 프롬프트의 토큰들은 병렬**로 처리될 수 있어 (5장에서 분석했듯) **높은 산술 강도**를 달성 → compute-bound 워크로드
    - **Decode 단계**: LLM이 **한 번에 토큰 하나씩 생성**하는 단계. **자기회귀적**(autoregressive) 특성 때문에 decode는 memory bandwidth-bound입니다 - 토큰 하나를 생성하기 위해 수십억 개 파라미터 전체를 훑어야 하므로, **GPU 메모리 대역폭 관점에서 매우 비효율적**입니다 (그림 6-1).
        
        !Figure 6-1. Prefill은 input prompt token을 한 번에 처리하고, decode는 새 token을 하나씩 생성한다
        
        Figure 6-1. Prefill은 input prompt token을 한 번에 처리하고, decode는 새 token을 하나씩 생성한다
        
    - **배칭이 어떻게 이 문제를 해결하는가?**
        - GPU 연산력을 온전히 활용하려면 배칭(batching)으로 **요청을 더 추가해서 함께 처리**하면 됩니다.
        - 이 절에서는 **최대 배치 크기 3을 가정**합니다.
    - **예시**
        
        !Figure 6-2. 세 request를 decode batch로 묶으면 세 개의 새 token을 함께 생성할 수 있다
        
        Figure 6-2. 세 request를 decode batch로 묶으면 세 개의 새 token을 함께 생성할 수 있다
        
        - prompt1, prompt2, prompt3 **세 개의 입력 프롬프트를 하나로 배칭**해서 모델에 전달
        - Decode 단계는 여전히 반복(iteration)당 토큰 하나씩 생성하지만, 요청들을 배칭했기 때문에 **한 번의 반복에서 세 개의 새 토큰을 동시에 생성**할 수 있음 - 각 요청당 하나씩 (그림 6-2)
        - 이를 통해 **산술 강도가 인위적으로 상승**합니다: **모델 가중치는 여전히 한 번만 읽지만**, 그 한 번의 읽기로 더 많은 계산을 수행하고 더 많은 토큰을 생성하게 됩니다.
        
        !https://www.youtube.com/watch?v=9gmHwe5-j0E&t=102s
        
        https://www.youtube.com/watch?v=9gmHwe5-j0E&t=102s
        
    - **배칭 적용 시 효과**
        - **Prefill : 효과가 제한적**. 이미 입력 토큰 전체를 병렬로 처리하고 있어서, 입력 프롬프트가 아주 작지 않은 이상(대략 1,024 토큰 미만이 아닌 이상) prefill 자체만으로도 GPU 연산 능력을 이미 포화시킴 → 배칭으로 얻는 추가 병렬성의 효과는 미미함
        - **Decode : 특히 효과적**. 한 번에 토큰 하나씩만 생성하는 구조이므로, 여러 요청을 묶으면 전체 처리량이 상승하고 GPU FLOPS 활용률이 개선됨
        
    - **요지**
        - **배칭**의 핵심 원리는 **"모델 가중치를 한 번 읽을 때 그 대가로 최대한 많은 연산(토큰 생성)을 뽑아내는 것"**입니다.
        - 이는 특히 memory bandwidth-bound인 decode 단계에서 강력한 효과를 발휘하며, 이미 compute-bound인 prefill 단계에서는 상대적으로 얻을 게 적습니다.
        - 이것이 바로 5장에서 배운 산술 강도 개념이 실전 최적화 기법(배칭)으로 직결되는 지점입니다.
    
- `도전과제` ’vLLM 혹은 SGLang’ 에서 (연속) **배칭 ON vs 배칭 효과 무력화** `max_num_seqs=1` 시 서빙 처리 성능과 지연시간 측정 후 정리
- **Dynamic Batching in Online Inference** 온라인 추론에서의 동적 배칭
    - **Static Batching의 문제** - Youtube
        - 온라인 서비스에서는 **요청이 언제 들어올지 알 수 없습니다.**
        - Max Batch가 10이라고 해서 무조건 10개가 찰 때까지 기다리면:
            - Request 1~9 : 바로 도착
            - Request 10 : 5분 후 도착
        - 앞의 9명이 5분이나 기다릴 수 있습니다. ⇒ 오프라인 사용 사례에는 적합하지만, 온라인 추론에는 부적합합니다!
        
    - **해결** : 그래서 **Dynamic Batching**은 두 개를 함께 사용 - Max Batch Size + **Max Delay Time (최대 대기 시간)**
        - 배치 크기(batch size) : 최대 배치 크기, 선호 배치 크기, 최대 시퀀스 수 등으로도 불림, 모델에 보내기 전 함께 묶을 수 있는 요청 수의 상한
        - 최대 지연 시간(max delay time) : 다른 요청들이 배치를 채울 때까지 기존 요청들을 대기시킬 수 있는 최대 시간
        - “10명이 차면 바로 출발하고, **10명이 안 차더라도 5분이 지나면 출발**한다.”
        
        !mermaid-diagram (1).png.png)
        
        - 대기 중인 요청 수가 최대 배치 크기에 도달 → 최대 지연 시간이 아직 안 지났어도 즉시 전송
        - 최대 지연 시간에 도달 → 배치에 요청이 단 하나뿐이더라도 즉시 전송
        
    - **파라미터 튜닝 방향** : 목표: 지연시간 SLA를 지키는 선에서 배치 크기를 최대한 높게 유지
        - 배치 크기(max batch size)
            - 너무 높이면: 처리 지연시간 증가 + GPU/CPU 메모리 사용량 증가 → 결국 OOM(메모리 부족) 위험
        - 최대 지연 시간(max delay time)
            - 너무 길게 설정 + 높은 배치 크기 조합 → 이미 도착한 요청들이 오래 대기하게 됨
            - 너무 짧게 설정 → 배치를 제때 채우지 못해 실제 처리되는 배치 크기가 줄어듦 (배칭 효과 반감)
    - **요지**
        - 동적 배칭은 정적 배칭(효율적이지만 느림)과 배칭 없음(빠르지만 비효율적) 사이의 실전 절충안으로, max_num_seqs(=최대 배치 크기)와 max_delay_time 두 파라미터를 워크로드의 지연시간 SLA와 처리량 목표에 맞게 튜닝하는 것이 핵심입니다.
        - 바로 앞서 논의한 vLLM의 continuous batching도 이 동적 배칭 철학의 발전된 구현체(요청 도착·완료 시점마다 배치를 계속 재구성)라고 볼 수 있습니다.
        
    - **하지만 LLM에서는 이것만으로도 부족합니다!**
    - Traditional inference에서는 효과적이지만, LLM은 request마다 output 길이가 달라 batch 내부의 sequence가 서로 다른 시점에 끝난다.
    
- **Continuous Batching for LLM Online Inference** LLM 온라인 추론을 위한 연속 배칭
    - **동적 배칭의 한계: LLM만의 독특한 문제**
        - 동적 배칭은 대부분의 전통적인 ML 서빙에는 잘 작동하지만, LLM은 더 크고 독특한 문제를 안고 있습니다:
        - **입력·출력 길이가 요청마다 크게 다름** → 배치 안 요청들이 처리 완료까지 걸리는 시간이 제각각
        - 동적 배칭에서는 배치의 **전체 완료 시간이 가장 길고 느린 요청에 의해 결정**됨 (배치 안 모든 요청이 끝나야 결과 반환)
        - 그림 6-3: 요청 길이가 제각각이면, **짧은 요청들이 가장 긴 요청 하나가 끝날 때까지 대기** → **큰 GPU 유휴 시간(idle time) 발생**
        
        !Figure 6-3. 세 request 길이가 다르면 짧은 request가 긴 request 종료를 기다리며 GPU idle time이 생긴다
        
        Figure 6-3. 세 request 길이가 다르면 짧은 request가 긴 request 종료를 기다리며 GPU idle time이 생긴다
        
    - 나룻배 비유 설명
        - 이번엔 배가 강 건너 각자의 집까지 직접 데려다줘야 한다고 가정.
        - 사는 곳까지 거리가 제각각이라, 배는 가장 먼 집까지 데려다준 뒤에야 다음 그룹을 태우러 돌아올 수 있음 → 탑승 인원이 갈수록 줄어드는(낮은 적재율로 운행) 비효율 발생
        
    - **해법: 연속 배칭(Continuous Batching)** = inflight batching, iterative batching이라고도 불림
        - 동적 배칭: 고정된 배치 크기나 시간 창을 기다렸다가 배치 단위로 처리
        - 연속 배칭: 정해진 배치 크기·시간을 기다리지 않고, **요청을 백엔드 모델에 즉시 추가하고 그때그때 유동적으로 그룹핑**
        - 핵심 동작: 배치 내 실행 중인 요청 하나가 끝나는 즉시 → 대기열에 있던 요청이 바로 그 자리에 추가됨
        
        !Figure 6-4. Continuous batching은 request 완료 시 새 request를 추가해 GPU idle time을 줄인다
        
        Figure 6-4. Continuous batching은 request 완료 시 새 request를 추가해 GPU idle time을 줄인다
        
        - 처음에 요청 1, 2, 3이 처리 시작
        - 요청 1이 끝나면 → 새로 도착한 요청 4가 즉시 추가
        - 요청 2가 끝나면 → 요청 5 추가
        - 요청 5가 끝나면 → 요청 6 추가
        - (동적 배칭이었다면 4, 5, 6 모두 요청 3이 끝날 때까지 대기해야 했을 것)
        
        !https://www.youtube.com/watch?v=9gmHwe5-j0E&t=394s
        
        https://www.youtube.com/watch?v=9gmHwe5-j0E&t=394s
        
    - 비유 업데이트: **10인승 배 1척 → 1인승 배 10척**
        - 사람이 도착하는 즉시 배 한 척이 바로 출발
        - 목적지(거리)가 제각각이어도 낭비 없음 - 데려다주고 돌아오면 바로 다음 사람을 태움
        
    - **연속 배칭에서 튜닝해야 할 파라미터**
        - max delay time은 더 이상 인위적으로 설정할 필요 없음 (**동적 배칭과의 차이점**)
        - 하지만 **최대 배치 크기(max batch size)는** 여전히 관리·튜닝 필요
            - 값이 클수록 더 많은 요청을 병렬 처리 가능
            - 단, 이 파라미터는 절대 상한선(upper bound) 역할만 함 - 연속 배칭 과정에서 이 값을 넘지 않도록 제한
    - 추가 파라미터: **최대 배칭 토큰 수 (max number of batched tokens)**
        - 최대 배치 크기 = 요청(request) 레벨 제어 → 동시에 처리하는 요청 개수의 상한
        - **최대 배칭 토큰 수 = 토큰(token) 레벨의 더 세밀한 제어**
        - 왜 필요한가: **LLM 요청은 입력 길이가 천차만별이기 때문**
            - 예: "20토큰짜리 요청 10개"와 **"100,000토큰짜리 요청 2개"는 완전히 다른 워크로드**
            - 요청 개수 제한만으로는 토큰 길이 차이를 반영하지 못해 배치가 너무 가볍거나 너무 무거워질 수 있음
    - **3개 파라미터의 관계**
        - `max batch size` (예: 3) : 한 번에 배치로 함께 처리할 수 있는 최대 요청 개수 ⇒  `--max-num-seqs`
        - `max model length` (=max context size, 5장에서 다룸) : 요청 하나의 토큰 길이가 넘을 수 없는 모델 자체의 컨텍스트 상한 ⇒ `--max-model-len`
        - `max number of tokens` : 스케줄러가 배치 전체에서 허용하는 총 토큰 수의 상한 - 매우 긴 요청 몇 개가 이 한도에 빨리 도달하면, 스케줄러는 더 이상 새 요청을 배치에 추가하지 않음 ⇒ `--max-num-batched-tokens`
        
        !Figure 6-5. Max batch size, max number of tokens, max model length의 관계
        
        Figure 6-5. Max batch size, max number of tokens, max model length의 관계
        
    - **단계별 실제 제약 조건**
        - **Prefill 단계**: 입력이 훨씬 길기 때문에 최대 토큰 수(**max number of tokens**)가 핵심 제약
        - **Decode 단계**: 병렬성은 보통 최대 배치 크기(**max batch size**)에 의해 제한됨
        - *최대 토큰 수를 너무 낮게 설정하면 안 됨 - prefill 단계에서 GPU에 충분한 토큰을 병렬로 공급하지 못해 GPU 연산력을 다 포화시키지 못하게 됩니다.*
        
    - **Example 6-1. vLLM에서 파라미터 설정하기**
        
        ```bash
        vllm serve \
          Qwen/Qwen2.5-7B-Instruct \
          **--max-num-batched-tokens 4096 \
          --max-num-seqs 128
          --max-model-len 1024**
        ```
        
        - `--max-num-batched-tokens 4096` : 최대 배칭 토큰 수, 한 iteration에서 배치 전체가 소비할 수 있는 총 토큰 수의 상한
        - `--max-num-seqs 128` : 최대 (동시) 배치 크기, 한 iteration에서 동시에 처리할 수 있는 요청 개수의 상한
        - `--max-model-len 1024` : 스케줄러가 배치 전체에서 허용하는 총 토큰 수의 상한
    
- `도전과제` ’vLLM 혹은 SGLang’ 에 ‘max batch size, max model length, max number of tokens’ 기본값 확인 및 변경 후 서빙 성능 측정 비교
- **Continuous Batching with Chunked Prefill** 청크 프리필을 이용한 연속 배칭 - Youtube
    - 문제 제기: **Prefill과 Decode는 서로 다른 워크로드**
    - 연속 배칭은 요청마다 길이가 다른 문제는 해결했지만, LLM 서빙의 또 다른 독특한 측면을 간과하고 있습니다: prefill과 decode는 서로 완전히 다른 성격의 워크로드입니다.
        - Prefill: 산술 강도가 높아 배칭의 도움을 크게 필요로 하지 않음
        - Decode: 산술 강도가 낮아 배칭의 이득을 크게 받음
        
        !Figure 6-6. Prefill과 decode가 완벽히 정렬된 happy path
        
        Figure 6-6. Prefill과 decode가 완벽히 정렬된 happy path
        
    - 그림 6-6에서 보여준 시나리오는 사실 "체리피킹된 이상적인 경우"였습니다 - 모든 요청의 입력 길이·출력 길이가 동일하고 시작 시점도 같은 경우. 이 경우 iteration 1에서 세 요청의 prefill이 함께 배칭되고, iteration 2에서 세 요청의 decode가 함께 배칭됩니다.
        - *체리 피킹(Cherry Picking)은 케이크 위에서 가장 맛있는 체리만 쏙 골라 먹듯, 자신에게 유리하고 득이 되는 것만 골라 취하고 불리한 것은 버리는 행위*
        
    - **실제 상황: 요청은 무작위로, 다른 시점에 도착한다**
    - 핵심 질문: **요청 1이 이미 decode 중인데 요청 2가 도착해 prefill을 시작하고 싶다면? decode를 우선할까, prefill을 우선할까?** 아니면 같은 iteration에 함께 배칭할 수 있을까?
    - **방안 1 : Prefill과 Decode를 함께 배칭하지 않음 (그림 6-7)**
        
        !Figure 6-7. Prefill을 우선하고 decode와 함께 batch하지 않는 continuous batching
        
        Figure 6-7. Prefill을 우선하고 decode와 함께 batch하지 않는 continuous batching
        
        - Prefill과 Decode를 섞은 하이브리드 워크로드는 더 복잡한 GPU 커널이 필요하므로, 우선 이 방법부터 검토
        - 요청 1이 prefill(iteration 1) → decode(iteration 2) 진행 중, 요청 2·3이 도착
        - **보통 prefill을 우선함** : prefill이 TTFT(첫 토큰까지의 시간)를 결정하는 중요한 지연시간 지표이기 때문(특히 챗봇 같은 대화형 서비스에서 중요)
        - 하지만 iteration 3에서 요청 **2·3의 prefill을 처리하는 동안 → 요청 1은 완전히 유휴(idle) 상태로 대기**
        - **요청 2·3의 프롬프트가 길면 → 요청 1의 종단 지연시간(end-to-end latency)과 토큰 간 지연시간(inter-token latency)에 큰 타격**
        
    - **방안 2 : Prefill과 Decode를 함께 배칭 (그림 6-8)**
        
        !Figure 6-8. Iteration 3에서 decode와 prefill을 함께 batch하는 continuous batching
        
        Figure 6-8. Iteration 3에서 decode와 prefill을 함께 batch하는 continuous batching
        
        - **요청 1의 두 번째 decode 스텝을 iteration 3에 넣어, 요청 2·3의 prefill과 같은 배치 iteration에서 함께 실행**
        - **그래도 큰 도움은 안 됨**: 토큰 하나를 디코딩하는 것은 prefill을 끝내는 것보다 훨씬 빠르기 때문, 특히 **입력 프롬프트가 길 경우 지연이 여전히 두드러짐**
        
        !https://www.youtube.com/watch?v=9gmHwe5-j0E&t=611s
        
        https://www.youtube.com/watch?v=9gmHwe5-j0E&t=611s
        
    - **해법: 청크 프리필(Chunked Prefill)**
        
        !Figure 6-9. Chunked prefill을 사용하는 continuous batching
        
        Figure 6-9. Chunked prefill을 사용하는 continuous batching
        
        - **긴 입력 프롬프트를 더 작은 청크(chunk)로 나누는 기법**
        - 그림 6-9: 기존의 긴 prefill 막대가 **decode 박스와 비슷한 크기(이상적으로는 처리 시간도 비슷)의 여러 작은 prefill 조각으로 분할**됨
        - Chunked prefill은 긴 prefill을 여러 chunk로 쪼개 decode와 interleave할 수 있게 한다.
        - 요청 2·3이 배치에 합류하면(iteration 5): 요청 1은 계속 decode 진행, 나머지 두 요청은 자신만의 작은 청크 단위 prefill을 시작
        - iteration 10: 요청 2는(prefill이 요청 3보다 짧아서) 자연스럽게 decode로 전환
        - Chunked prefill은 긴 prompt가 많은 workload에서 TTFT와 fairness를 개선할 수 있지만, scheduler 복잡도와 memory 관리 부담이 증가한다.
        
        !https://www.youtube.com/watch?v=9gmHwe5-j0E&t=611s
        
        https://www.youtube.com/watch?v=9gmHwe5-j0E&t=611s
        
    - **효과와 트레이드 오프 → 결국 use case와 SLA 요구사항에 따라 선택해야 하는 트레이드오프**
        - ITL(토큰 간 지연시간) : 개선됨 - decode 박스가 더 이상 긴 prefill에 막혀 대기하지 않음
        - TTFT(첫 토큰까지 시간) : 악화됨 - prefill 단계에 더 많은 작업(오버헤드)이 추가됨
        - 종단 지연시간(end-to-end latency) : 개선 안 됨, 오히려 여러 작은 prefill 스텝을 계산하는 오버헤드로 약간 악화되는 경우가 많음
        - 처리량(throughput) : 보통 개선됨 — 유휴 시간의 빈틈을 채워 배치 효율성이 좋아지고 GPU를 더 잘 활용
        
    - **튜닝 파라미터: 청크 크기 (얼마나 잘게 쪼갤 것인가)**
        - 원래의 긴 prefill을 몇 개의 작은 prefill로 나눌지, 즉 작은 prefill 작업 하나가 처리할 토큰 수를 결정해야 함
        - 이는 앞서 다룬 최대 배칭 토큰 수(max number of batched tokens) 설정의 일부
        
        | 청크 크기 설정 | 결과 |
        | --- | --- |
        | 극단적으로 크게 (예: max model leghth까지) | 사실상 청킹을 전혀 안 하는 것과 같음 |
        | 극단적으로 작게 | 오버헤드 증가 — 한 iteration에서 충분한 토큰을 배칭하지 못해 GPU 연산력을 포화시키지 못함 |
        | 이상적 | 오버헤드도 크지 않고, 청크 프리필의 목적(빈틈 채우기)도 훼손하지 않는 중간값 |
    - **vLLM 문서에서 chunked prefill 관련 파라미터**
        - `--enable-chunked-prefill` : 청크 프리필 기능 자체를 켜고 끄는 스위치 , 기본값(True)
        - `--max-num-batched-tokens` : 청크 하나(=한 iteration)가 처리할 최대 토큰 수(실질적인 ‘청크 크기’ 역할) , 기본값(컨텍스트에 따라 자동 설정)
        - 어떻게 동작하는가
            - "enable_chunked_prefill이 True면, prefill 요청은 **남은 max_num_batched_tokens**를 기준으로 더 작은 청크로 나뉜다."
            - 즉, 별도의 "청크 크기" 전용 파라미터는 따로 없고, 지난 대화에서 다룬 --max-num-batched-tokens 값 자체가 청크 크기를 결정합니다.
            - 긴 prefill을 이 값 이하 단위로 잘라서 여러 iteration에 걸쳐 처리하는 방식입니다.
        - 실행 예시
            
            ```bash
            vllm serve Qwen/Qwen2.5-7B-Instruct \
              **--enable-chunked-prefill \**
              **--max-num-batched-tokens 2048 \**
              --max-num-seqs 3 \
              --max-model-len 1024
            ```
            
        
    - 업계 현황 및 다음 방향
        - 연속 배칭(continuous batching): 이 책을 쓰는 시점 기준, 몇 년간 프로덕션 LLM 서빙의 업계 표준
        - 청크 프리필과 그 변형들: 긴 컨텍스트 워크로드 처리 등에서 매우 인기 있는 기법
        - 더 고급 기법 **Prefill-Decode 분리(disaggregation)**: prefill과 decode 작업을 완전히 다른 GPU, 심지어 다른 노드로 분리하는 방식 → 7장에서 기초를 다진 후 다룰 예정
    - 요지:
        - 연속 배칭만으로는 prefill(compute-bound)과 decode(memory bandwidth-bound)라는 성격이 다른 두 워크로드가 섞일 때 생기는 지연 문제를 완전히 해결하지 못합니다.
        - 청크 프리필은 긴 prefill을 잘게 쪼개 decode와 나란히 배치함으로써 ITL을 개선하고 처리량을 높이지만, 그 대가로 TTFT가 다소 희생되는 트레이드오프 기법이며, 청크 크기(=max number of batched tokens와 연동)를 워크로드 특성에 맞게 튜닝하는 것이 핵심입니다.
    
- `도전과제` ’vLLM 혹은 SGLang’ 에 **Chunked Prefill** ON vs Off 와 `--max-num-batched-tokens` 튜닝 후 성능 측정 비교

### Scaling Attention and Kernel Optimization

- 들어가며 : 스케일링 어텐션과 커널 최적화
    - (2장 복습) LLM 서빙 중 트랜스포머 블록의 두 가지 주요 구성요소: **⇒ 어텐션(attention) 측면을 어떻게 확장(scale)에 집중!**
        - 어텐션(attention) 레이어
        - 피드포워드 레이어(FFN, MLP)
        
    - 이 절에서 다룰 순서
        - KV 캐시 크기 축소 방법
        - 커스텀 GPU 커널이 어텐션 연산과 메모리 접근을 어떻게 개선하는지
        
    - **어텐션의 진화: MHA → MQA → GQA → MLA**
        - 어텐션 메커니즘은 LLM의 핵심 돌파구지만, GPT-3를 구동한 원래의 멀티헤드 어텐션(MHA) 공식이 더 이상 유일하거나 가장 효율적인 방식은 아닙니다.
        - 프로덕션 워크로드와 LLM의 높은 연산 비용이 모델에서 더 많은 성능을 짜내야 하는 압박으로 이어졌고, 이것이 다음 기법들을 낳았습니다:
            - MQA (Multi-Query Attention)
            - GQA (Grouped-Query Attention)
            - MLA (Multi-head Latent Attention) - 가장 최신 기법
        - 이들의 공통 목표: **모델 품질을 유지하면서 KV 캐시 크기를 대폭 줄이는 것(slash)**
        
    - 어텐션을 실행하는 GPU 커널의 진화
        - 시간이 지나며 커널은 다음 순서로 발전:
            - 범용 커널 퓨전(generic kernel fusion) → 어텐션에 특화되고 하드웨어에 맞춰 튜닝된, 캐시를 인식하는(cache-aware) 커널
        - 먼저 커널 퓨전(kernel fusion) 개념을 이해한 뒤, FlashAttention 같은 구체적인 커널들을 살펴볼 예정
    - 마지막: PagedAttention
        - KV 캐시가 GPU 메모리에 저장되는 방식을 관리하는 새로운 메커니즘을 도입해 높은 메모리 활용률을 달성하는 혁신 기법
        
    - **요지**: 이 절은 앞으로 다룰 세 가지 큰 흐름을 미리 안내하는 도입부
        - 어텐션 알고리즘 자체의 변형(MQA/GQA/MLA)으로 KV 캐시 크기를 줄이고,
        - GPU 커널 최적화(커널 퓨전 → FlashAttention 등)로 어텐션 연산·메모리 접근 효율을 높이고,
        - PagedAttention으로 KV 캐시의 GPU 메모리 저장 방식 자체를 재설계
        
    - 책 원문 번역
        - 2장에서 언급했듯이, LLM이 동작할 때 트랜스포머 블록의 두 가지 주요 구성 요소는 어텐션 층과 피드포워드 층(FFN, 다층 퍼셉트론 또는 MLP 층이라고도 함)입니다. 이 섹션에서는 LLM 서비스에서 어텐션 측면을 확장하는 방법에 중점을 둡니다. 먼저 KV 캐시 크기를 줄이는 것부터 시작하고, 이어서 커스텀 GPU 커널이 어텐션 계산과 메모리 접근을 어떻게 향상시키는지 논의하겠습니다.
        - 어텐션 메커니즘은 LLM의 혁신을 이끄는 핵심입니다. 하지만 GPT-3를 구동하는 원래의 멀티헤드 어텐션 공식만이 대규모로 쿼리, 키, 값들을 활용하는 유일하거나 가장 효율적인 방법은 아닙니다. LLM의 높은 연산량과 비용 때문에 모델 성능을 더 끌어올려야 했고, 이로 인해 멀티 쿼리 어텐션(MQA), 그룹 쿼리 어텐션(GQA), 그리고 최신 기술인 멀티 헤드 잠재 어텐션(MLA)이 등장해 KV 캐시 크기를 크게 줄이면서도 모델 품질을 유지하려고 노력하고 있습니다.
        - 어텐션 최적화를 살펴본 후에는 어텐션을 실행하는 GPU 커널에 대해 논의하겠습니다. 시간이 지나면서 이 커널들은 일반적인 커널 융합에서 주의(attention)에 특화되고 하드웨어에 최적화되며 캐시를 고려하는 커널로 발전해 왔습니다. 먼저 커널 퓨전의 개념을 이해하고, 그 다음에 FlashAttention과 같은 특정 커널들에 대해 살펴보겠습니다.
        - 장 마지막에는 또 다른 핵심 혁신인 페이지드 어텐션(PagedAttention)을 살펴볼 텐데, 이는 GPU 메모리에 KV 캐시를 저장하는 방식을 새롭게 설계해 메모리 활용도를 높이는 메커니즘입니다.
    
- 추천영상 : 어텐션 메커니즘 관련
    - [딥러닝 큐레이터 임커밋] 최신 LLM 구조의 기본기GQA Group Query Attention) - Youtube
    - [딥러닝 큐레이터 임커밋] Deepseek의 MLA 서커스 이해하기 - Youtube
    - [Visual AI] LLM이 메모리를 75% 적게 사용하는 이유 - GQA & MQA 8분 만에 완벽 이해하기 - Youtube
    - [Visual AI] Kimi K3 아키텍처 해설: 세계 최대 오픈 웨이트 AI 모델의 작동 원리 - Youtube
    - 모델 구조 공부하시는 분들께 권하는 리포트, Kimi K3 - Youtube
- **Scalable Attention Mechanisms** 확장 가능한 어텐션 메커니즘 - Blog
    - KV 캐시 축소가 중요한 이유
        - **Decode 단계**에서는 **매 iteration마다 KV 캐시가 HBM에서 온칩 레지스터·공유 메모리로 계속 전송**됩니다.
        - KV 캐시가 작을수록:
            - GPU 메모리 대역폭 부담이 줄어듦 (5장에서 배운 내용)
            - GPU 메모리 공간을 덜 차지 → 더 큰 배치 크기로 더 많은 요청을 병렬 처리 가능 → 처리량 향상
            - 제한된 GPU 메모리 안에서 더 긴 컨텍스트도 서빙 가능
        
    - **네 가지 어텐션 방식 비교**
        
        !Figure 6-10. MHA, MQA, GQA, MLA 비교
        
        Figure 6-10. MHA, MQA, GQA, MLA 비교
        
        1. **MHA (Multi-Head Attention)**
            - 많은 초기 모델의 기반이 되는 원래 버전
            - 쿼리 하나당 별도의 고유한 키·값 헤드가 필요
            - 결과적으로 네 방식 중 KV 캐시가 가장 크고 가장 비효율적
        2. **MQA (Multi-Query Attention)**
            - **모든 쿼리가 단 하나의 키·값 헤드를 공유**
            - 예: 7B 모델은 보통 어텐션 헤드 32개, 70B 모델은 64개
                - MHA라면 KV도 각각 32개, 64개 필요
                - **MQA는 단 1개만 필요**
                - **→ KV 캐시 크기를 32배, 64배까지 줄일 수 있음 (엄청난 절감)**
            - 단점: 너무 공격적인 설계 때문에 **모델 정확도가 크게 저하**되는 것으로 밝혀짐
            - MHA 대비 MQA 사용 시 KV 캐시 메모리 1/4로 절감
                
                !https://www.youtube.com/watch?v=yzONjmXM8As
                
                https://www.youtube.com/watch?v=yzONjmXM8As
                
        3. **GQA (Grouped-Query Attention)**
            - MQA의 정확도 문제를 완화하기 위해 등장, 성능과 정확도의 균형을 목표로 함
            - 쿼리 헤드를 여러 그룹으로 묶고, **각 그룹이 동일한 키·값을 공유**
                
                !image.png
                
            - MHA(연산 효율 낮음)와 MQA(정확도 손실 큼) 사이의 좋은 절충안으로 입증되어, 현재 많은 모델 아키텍처에서 채택 중
            - KV 캐시 메모리 사용 비교 : **MHA 100% vs GQA 50% vs MQA 25%**
                
                !image.png
                
            - 추론 속도 비교 ← 캐시 메모리 뿐 아니라, 추론 시 속도에도 이점!
                
                !image.png
                
        4. **MLA (Multi-head Latent Attention)** - DeepSeek이 도입, 가장 최신
            - 단순히 **KV 개수를 줄이는 것이 아니라**, **영리한 방식으로 압축(compress)**한다는 점이 핵심 차이
            - **head를 줄이는 대신 latent를 캐싱한다**
            - DeepSeek 원 논문 주장: "KV 캐시 크기는 그룹 2.25개짜리 GQA와 동등하지만, 성능은 MHA보다 더 강력하다"
        5. **Hybrid Attention**: KDA와 Gated MLA 3:1 결합 - Kimi K3 도입 - Youtube
            
            [[노토랩X수도리무브] Kimi K3 이해하기.pdf](attachment:0a4913ce-c849-4e19-91dd-982b2e0bc76d:노토랩X수도리무브_Kimi_K3_이해하기.pdf)
            
            - Linear Attention / Recurrent State : 제곱에 비례하는 계산량을 줄이기 위해, 중간 상태를 Memory 형태로 압축
            - DeltaNet : Recurrent State는 누적하지만 완화하지 못하므로 기존 성분을 제거하고 추가
            - Gated DeltaNet : 문맥 경계 등을 잘 처리할 수 있도록, 전역적으로 감쇠시키는 단계를 추가
            - **Kimi Delta Attention** : 채널별 감쇠 게이트
            - **Gated MLA**: MLA + Gated Attention
                - KV Cache 효율을 높이는 MLA By DeepSeek V2 : Key와 Value를 압축하여, 전체 KV 캐시 효율을 극대화
                - Gated Attention By Qwen 3 Next : Attn Sink를 피하기 위해 MLA가 가져온 결과를 Sigmoid Gate에 넣어 선택적으로 통과
        - **Attention 발전 방향 : 기본 어텐션은 너무 비싸서 Long Context 계산이 어렵다**
            - 계산에서 오는 오버헤드를 어떻게 줄일까?
            - 계산량/메모리를 줄이도록 **중간 상태를 압축하거나, 범위를 줄이자**
                - Linear Attn, Recurrent State (Mamba) / Sliding-Window Attention 계열
            - 압축하면 정보가 충돌하거나 희석되는데?
                - DeltaNet / Gated DeltaNet으로 중간중간 수정
            - 압축으로 손실되는 정보를 어떻게 보완하지?
                - 평소에는 Linear로 작업하다가, 중간중간에 전역 Attn을 섞어주자
        - **모델이 어떤 방식을 쓰는지 config.json으로 확인하기**
            
            ```bash
            # MHA는 attention head와 key/value head 수가 같다.
            Llama2 (MHA) — num_attention_heads = num_key_value_heads
            "num_attention_heads": 32,
            "num_hidden_layers": 32,
            "num_key_value_heads": 32,
            
            # GQA/MQA 계열은 key/value head 수를 줄여 KV cache memory를 절감한다
            **Llama3 (GQA) — num_key_value_heads가 축소됨**
            "num_attention_heads": 32,
            "num_hidden_layers": 32,
            "num_key_value_heads": 8,
            **→ KV 헤드 하나를 32 ÷ 8 = 4개의 어텐션 헤드가 공유**
            ```
            
        
    - **마무리: 이 진화가 시사하는 것**
        - 이 모든 발전은 **모델 아키텍처 레벨**에서 일어납니다 → 즉, **어텐션 방식**(MHA/MQA/GQA/MLA)의 선택은 결국 어떤 모델 계열·구체적인 모델이 내 use case에 가장 잘 맞는가라는 총체적인 결정(holistic decision)의 일부입니다.
        - 이러한 아키텍처 발전은 모델 개발 트렌드의 중요한 변화를 보여줍니다: 초점이 더 이상 모델 품질 향상에만 있지 않고, 점점 더 모델을 제품화(productize)하는 것으로 옮겨가고 있습니다.
        - LLM이 AI 시스템의 필수 요소가 되어가면서, 성공의 핵심은 강력할 뿐 아니라 실용적이고, 확장 가능하며, 실제 시스템에서 서빙하기에 충분히 비용 효율적인 아키텍처를 설계하는 것입니다.
    - **요지**:
        - MHA → MQA → GQA → MLA로 이어지는 흐름은 모두 "모델 품질을 최대한 유지하면서 KV 캐시(=메모리 대역폭·용량 부담)를 얼마나 줄일 수 있는가"라는 단일한 목표를 향한 진화입니다.
        - config.json의 num_key_value_heads 값 하나만 봐도 그 모델이 어떤 방식을 채택했는지, 그리고 KV 캐시가 얼마나 절감되는지 즉시 가늠할 수 있다는 점이 실전에서 유용한 포인트입니다.
    
- `도전과제` ’vLLM 혹은 SGLang’ 에서 ‘MHA vs GQA vs MQA vs MLA’ 어텐션 모델 별 추론 처리 속도와 모델 품질 측정 비교
- **Kernel Fusion and Custom Attention Kernels** 커널 융합과 커스텀 어텐션 커널
    - 커널(Kernel)이란?
        - 커널: **GPU에서 실행되는 작고 특화된 프로그램**으로, 행렬 곱셈·소프트맥스 등 LLM과 딥러닝 모델에 **필수적인 연산을 수행**
        - 모델 아키텍처·하드웨어·워크로드에 맞게 적절히 최적화되고 특화된 GPU 커널을 쓰면 GPU 활용률, 추론 속도, 처리량이 크게 향상됩니다.
        
    1. **커널 퓨전(Kernel Fusion)**
        - ML 전반 및 LLM에서 널리 쓰이는 핵심 커널 최적화 기법
        - 여러 개별 연산(예: 곱셈 + 덧셈)을 하나로 합쳐서, **메모리와 연산 유닛 사이의 데이터 이동 오버헤드를 최소화**
        - **레지스터·공유 메모리에 이미 있는 데이터를 재사용** → GPU 글로벌 메모리에 다시 쓰고 다시 읽는 왕복(round trip)이 불필요해짐
        - 그림 6-11: 커널 퓨전 없이는 중간 단계마다 메모리에 쓰고 읽기를 반복하지만, 퓨전을 적용하면 한 번에(in one go) 변환이 이뤄짐
        
        !Figure 6-11. Kernel fusion 전후 memory/compute interaction 비교
        
        Figure 6-11. Kernel fusion 전후 memory/compute interaction 비교
        
    2. **FlashAttention**
        - 핵심 아이디어
            - 어텐션은 빈번한 읽기·쓰기 때문에 GPU 메모리 대역폭에 병목이 걸립니다.
            - FlashAttention의 핵심: 알고리즘을 하드웨어를 인식하도록(hardware-aware / memory I/O aware) 설계해서 이 메모리 병목에 맞서는 것.
        - **어떻게 작동하는가**
            
            !Figure 6-12. FlashAttention의 SRAM 기반 QKV 계산과 fused FlashAttention 성능 개선
            
            Figure 6-12. FlashAttention의 SRAM 기반 QKV 계산과 fused FlashAttention 성능 개선
            
            - GPU 메모리 계층: **HBM**(가장 크지만 가장 느림) vs **SRAM/레지스터**(작지만 빠름)
            - FlashAttention의 목표: 느린 GPU 글로벌 메모리(HBM)에 큰 행렬을 통째로 구체화(materialize)하지 않는 것
            - 대신 큰 행렬을 더 작은 조각들로 나누는 타일링(tiling / blocking) 기법 사용
            - 모든 연산이 SRAM(더 빠른 메모리)이나 레지스터에서 이루어지도록 하고, **최종 출력만 HBM에 저장**
            - 그림 6-12: QKV 행렬 곱셈과 변환을 타일 단위로 반복(loop)하며 SRAM 안에서 수행
        - 추가 최적화
            - 어텐션 연산 전체를 하나로 퓨전, 여기에 온라인 소프트맥스(online softmax) 같은 핵심 아이디어를 더해 현존 최고 수준의 어텐션 커널 중 하나를 달성
            - 현재 많은 서빙 프레임워크에서 사용 중
        - **FlashAttention 2, 3의 발전**
            - 핵심 아이디어는 유지하되, GEMM(General Matrix Multiply) 계산과 소프트맥스 계산을 오버랩(중첩)시키는 등의 **기법 추가**
            - 특히 H100 같은 신세대 GPU에서 GPU 활용률을 더 개선
            
        - **커널 최적화, 실무자를 위한 조언**
            - 커널 최적화는 GPU 아키텍처, CUDA, 성능 프로파일링, 컴파일러 등 다방면 전문성이 필요한 큰 연구 영역 → 이 장의 범위를 넘어섬
            - 핵심 메시지: LLM을 서빙할 때는 **효율적인 커널을 활용**하는 것이 실무적으로 중요하다는 점만 기억하면 됩니다.
            - 다른 최적화된 커널들: FlashInfer, xFormers, Triton(Triton Inference Server와는 다른 개념이니 혼동 주의)
        - **실전 예시: vLLM에서 FlashInfer 커널 사용하기**
            
            ```bash
            # vLLM에서 FlashInfer 커널 사용하기
            pip install vllm==0.8.5.post1
            pip install flashinfer-python==0.2.2
            export VLLM_ATTENTION_BACKEND=FLASHINFER
            export VLLM_USE_FLASHINFER_SAMPLER=1
            export VLLM_FLASHINFER_FORCE_TENSOR_CORES=1
            
            # vLLM CLI
            ## --attention-backend FLASH_ATTN : 어텐션 백엔드를 FlashAttention으로 명시 지정 # 미지정 시 하드웨어에 맞게 자동 선택(auto-detect)
            ## flash_attn_version (config, 2/3/4) : FlashAttention 버전을 강제 지정, 기본값(None:자동 감지)
            ## 대부분의 경우 명시적으로 지정할 필요 없음 — vLLM이 GPU 세대(예: Hopper vs Ampere)와 모델 구조에 맞춰 자동으로 최적 백엔드를 고름
            ### H100/H200 (Hopper) : FlashAttention 3이 자동 선택되는 경우가 많음
            ### A100/A40 (Ampere 이하) : FlashAttention 2 또는 FlashInfer가 선택됨
            vllm serve Qwen/Qwen2.5-7B-Instruct \
              **--attention-backend FLASH_ATTN** \
              --max-model-len 4096 \
              --max-num-batched-tokens 8192 \
              --max-num-seqs 128 \
              --enable-chunked-prefill
              
            
            # SGLang에서는 플래그 하나로:
            --attention-backend {flashinfer|fa3|triton|torch_native|FlashMLA}
            ```
            
        - **어떤 커널을 골라야 하나?**
            - 커널·하드웨어·LLM 입출력의 복잡성과 다양성 때문에 명확한 정답을 제시하기 어려움 → 보통 실험을 통해 찾아야 함
            - 다행히 vLLM, SGLang 같은 서빙 백엔드는 기본값을 자동으로 선택하는 내장 로직을 갖고 있음
                - 예(집필 시점 기준): SGLang은 Hopper가 아닌 GPU(A100, A40 등)에는 FlashInfer, Hopper 아키텍처(H100, H200, H20)에는 FlashAttention3를 기본값으로 사용
            - 실전 팁: 처음에는 권장 기본값으로 시작하고, 다른 최적화 기회들을 먼저 시도한 뒤, 추가 성능 향상이 필요할 때 다른 커널을 실험하는 것이 좋음
        
    3. **PagedAttention**
        - 문제: KV 캐시 메모리 관리의 어려움
            - **서빙 중 새 KV 캐시를 계속 생성·저장하고 오래된 캐시는 축출(evict)**
            - 최신 LLM이 **더 긴 컨텍스트를 지원하면서 KV 캐시는 점점 더 커짐**
            - **입력 길이는 요청마다 다르고, 출력 길이는 사전에 알 수 없음** → 스케줄링이 매우 까다로움
            - 전통적 방식: 메모리 공간을 미리 할당(preallocate)하지만 대부분 다 쓰이지 않음 → **심각한 메모리 파편화(fragmentation)**와 낮은 실사용률 발생
        - **해법: PagedAttention (+ vLLM)**
            - 운영체제의 페이징(paging) 기법에서 영감을 얻음:
                - **메모리를 고정 크기 블록(페이지)**으로 나눠서, 흩어진 여유 공간도 쉽게 할당하고 연속된 메모리 없이도 긴 시퀀스를 처리 가능하게 함
            - (참고) vLLM이 GPU 메모리에 KV 캐시를 블록 단위로 저장·관리하는 근본 메커니즘이라서 별도의 on/off 없음
            - **동작 방식:**
                - KV 캐시를 고정 크기 블록들로 분할
                - 룩업 테이블(block table)을 이용해 쿼리 키를 특정 블록에 매핑
                - KV 캐시가 연속된 메모리에 저장될 필요가 없음 - 필요할 때 블록을 개별적으로 접근
                
                !Figure 6-13. PagedAttention을 사용하는 generation process의 한 단계
                
                Figure 6-13. PagedAttention을 사용하는 generation process의 한 단계
                
                - 프롬프트+생성 결과 전체가 물리 메모리상 연속된 공간에 저장되지 않음
                - 블록 7 → 블록 1 → 블록 3, 세 개의 흩어진 블록에 나눠 저장
                - 각 블록은 최대 4개 토큰 저장 가능 (마지막 블록은 아직 생성 중이라 2개만 채워짐)
                - 블록 테이블(block table): 요청한 데이터가 어느 물리 블록에 있는지 찾는 룩업 테이블
        - **효과 : 원 논문 인용**
            - PagedAttention 없이는 "KV 캐시 메모리의 20.4%~38.2%만 실제 토큰 상태를 저장하는 데 쓰임”
            - PagedAttention을 적용하면 "KV 캐시 메모리 낭비가 거의 0에 가까움”
        - 메모리 파편화를 획기적으로 줄인 덕분에, PagedAttention과 그 변형들은 연속 배칭(continuous batching)과 마찬가지로 거의 모든 LLM 서빙에서 기본적으로 활성화되는 표준 기능이 됨
        
    - **요지**: 이 절은 어텐션 연산을 빠르게 만드는 세 층위의 최적화를 다룹니다.
        1.  커널 퓨전(메모리 왕복 제거)
        2. FlashAttention(타일링으로 SRAM 안에서 연산, HBM 접근 최소화)
        3. PagedAttention(OS 페이징 방식으로 KV 캐시 메모리 파편화 제거). 
        - 셋 다 결국 5장에서 배운 **"GPU 메모리 대역폭이 병목"이라는 근본 문제**를, 각자 다른 층위(연산 융합·타일링·메모리 관리)에서 공략하는 기법들입니다.
    
- `도전과제` ’vLLM 혹은 SGLang’ 에서 ‘**FlashInfer 커널(FlashAttention, 2/3/4)**’ 설정 및 성능 측정 비교

### Model Compression

- 들어가며 : **모델 압축** - **양자화**, 증류, 가지치기
    - **왜 모델을 압축해야 하는가?**
        - LLM은 놀라운 능력을 열어줬지만, 그 방대한 크기 자체가 실제 프로덕션 환경에서 많은 문제를 일으킵니다.
        - 고성능 GPU를 확보하는 것은 비용이 많이 들고 어려운 일입니다.
        - 이 크고 비싼 모델들을 소비자에게 전달하려면 → **모델을 영리하게(smartly) 줄여야** 합니다.
        - 모델 압축 기법은 무모한 편법이 아니라, 모델 크기와 **연산량을 줄이면서도 성능을 유지**하는 **검증된 프로덕션 전략**입니다.
        
    - 모델 압축의 3대 카테고리
        
        ```mermaid
        flowchart TD
        
            BIG["Large LLM"]
        
            Q["Quantization<br/>숫자 Precision 감소"]
        
            D["Distillation<br/>큰 Teacher → 작은 Student"]
        
            P["Pruning<br/>불필요 Weight 제거"]
        
            Q --> SMALL1["작은 Memory<br/>적은 Data Movement"]
        
            D --> SMALL2["더 작은 Model"]
        
            P --> SMALL3["Parameter 감소"]
        
            BIG --> Q
            BIG --> D
            BIG --> P
        ```
        
        1. **양자화 (Quantization)**
            - 모델 파라미터의 **정밀도를 높은 비트에서 낮은 비트 형식으로 축소**
            - 더 많은 파라미터를 메모리에 욱여넣고, **행렬 연산 속도를 높이는 것**이 목적
            - (5장에서 배운 FP32 → FP16 → INT8/FP8 정밀도 축소 개념과 직결됩니다)
        2. **증류 (Distillation)**
            - 크고 강력한 "교사(teacher)" 모델의 지식을 **더 작고 빠른 "학생(student)" 모델로 전이**
            - **학생 모델이 교사의 행동을 모방하도록 학습**
        3. 가지치기 (Pruning)
            - **불필요한(redundant) 가중치나 어텐션 헤드를 외과적으로(surgically) 제거**
            - 이 과정에서 모델 용량 중 얼마나 많은 부분이 저활용(underused)되고 있었는지가 드러남
        
    - **세 기법 중 왜 양자화에 집중하는가**
        - 양자화가 **실용성 측면에서 단연 돋보**입니다:
            - 빠르고, 효과적이며
            - 일반적으로 모델 훈련 파이프라인의 수정이 거의/전혀 필요 없음
        - 이러한 장점 덕분에 양자화는 **프로덕션 환경에서 LLM을 압축·가속하는 가장 대표적인 선택지**가 되었습니다.
        - 실제로 양자화된 모델은 생각보다 훨씬 널리 쓰이고 있으며, 특히:
            - 낮은 지연시간과 높은 처리량이 요구되는 상황
            - 자원이 제한된 엣지 디바이스에서 모델을 구동해야 하는 상황 에서 두드러집니다.
        - → 이런 영향력과 보편성 때문에, 이 절에서는 다른 두 기법보다 양자화에 더 많은 시간을 할애할 예정입니다.
    - **요지:**
        - 6장 앞부분에서 다룬 배칭(요청을 어떻게 묶을지), 어텐션 최적화(연산·메모리 접근을 어떻게 빠르게 할지)가 "서빙 방식"을 다뤘다면, 이 절부터는 **"모델 자체의 크기를 줄이는 것"으로 최적화**의 층위가 이동합니다.
        - 양자화·증류·가지치기 중에서도 양자화가 실무에서 가장 실용적이고 즉시 적용 가능한 기법이라는 점이 이 절의 핵심 방향 설정입니다.
    
- [추천영상/PY] The Engineering Behind LLM Inference: Quantization **양자화** - Youtube
- **Quantization 양자화** - Blog
    - **양자화란?**
        
        !https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-quantization
        
        https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-quantization
        
        - 모델 파라미터(가중치, 활성화, KV 캐시)의 **정밀도**를 고정밀 부동소수점(FP32, FP16/BF16)에서 **저비트 표현**(FP8/INT8, FP4/INT4)으로 낮추는 과정.
        - 본질적으로 모델 데이터의 **정확도를 낮추는** 대신 **서빙 성능**을 얻는 트레이드오프입니다.
            
            !해상도가 떨어짐.
            
            해상도가 떨어짐.
            
        
    - **양자화 오차 (Quantization Error)** : 정밀도를 낮추면서 두 가지 오차가 발생
        - **반올림 오차(rounding error)**
            - 발생 원인 : 원래 값을 낮은 정밀도 포맷에 정확히 표현 못해 가장 가까운 값으로 반올림
            - 예시 : FP32의 7.6 → INT8로는 소수 표현 불가 → 8로 반올림 → 오차 0.4
        - **클램핑 오차(clamping error)**
            - 발생 원인 : 값이 대상 포맷의 표현 범위를 넘어서 최대/최소값으로 강제 절단
            - 예시 : FP8 범위가 ±448이라면, 1,000 → 448로 클램핑
        - 클램핑은 4,096이 448이 되는 것처럼 **심각한 왜곡을 유발**할 수 있어, 최신 양자화 기법은 **하드 클램핑을 피하고 스케일링(scaling) 전략**을 사용
        - **스케일링**: 원본 데이터의 **값 범위를 압축하는 스케일 팩터를** 적용해, **저정밀 포맷의 표현 가능 범위 안에 더 많은 값**이 들어오도록 함 (대표 전략: 대칭 스케일링, 비대칭 스케일링)
        
    - **숫자 저장 방식 Storing numbers** : 부동소수점 포맷 Floating-point (FP) format
        - **Total bits** = 1 sign bit + mantissa bits + exponent bits
        - **부호 비트**: 양수/음수
        - **가수부**(mantissa): 정밀도(디테일 수준) 결정
        - **지수부**(exponent): 표현 가능한 스케일(값의 크기) 결정
            
            
        - 표 6-1. 주요 부동소수점 포맷 비교
            
            !Figure 6-14. FP32, BF16, FP16의 precision과 range 비교.
            
            Figure 6-14. FP32, BF16, FP16의 precision과 range 비교.
            
            - **FP32**: 풀 정밀도, 훈련의 표준 포맷 (넓은 범위 + 좋은 정밀도)
            - **FP16 vs BF16**: 둘 다 16비트지만 지수부 vs 가수부에 비트를 어떻게 배분하느냐가 다름
                - BF16은 지수부가 FP16보다 많음(8 vs 5) → 정밀도는 다소 희생하지만 범위는 훨씬 넓음
                - BF16과 FP32는 지수부 비트 수가 동일(8비트) → 값의 범위가 동일 → FP32→BF16 변환은 클램핑 위험 없이 정밀도 손실만 발생 → 딥러닝 훈련에 특히 적합
            - 현재 대부분의 LLM 체크포인트는 FP16 또는 BF16으로 제공됨 (FP32는 덜 흔함)
            
            | **Precision format** | **Total bits 총 비트** | **Sign bit 부호** | **Exponent 지수부** | **Mantissa 가수부** | **Approx. range level 대략 범위** |
            | --- | --- | --- | --- | --- | --- |
            | FP32 | 32 | 1 | 8 | 23 | ±10³⁸ |
            | BF16 | 16 | 1 | 8 | 7 | ±10³⁸ |
            | FP16 | 16 | 1 | 5 | 10 | ±10⁻⁵ (좁은 범위) |
    - **양자화된 수 표현**
        - 이제 전체 크기 데이터 형식을 살펴봤으니, **양자화된 숫자 형식**들을 살펴보겠습니다. **양자화된 수 표현에는 두 가지 유형**이 있습니다.
        - INT8과 INT4 같은 정수 기반 표현과, FP8과 FP4 같은 부동소수점 기반 표현이 그것인데, 이 책을 집필하는 동안에도 이 두 가지가 더 널리 사용되고 있습니다.
        - 이 두 형식의 가장 큰 차이는 **데이터 포인트를 분배하는 방**식에 있습니다.
        - **정수 기반 형식에서는 데이터 분포가 완전히 균일**하여, 데이터 포인트가 전체 값 범위에 고르게 분포하고 **숫자의 정밀도도 변하지 않습니**다.
        - 반면 **부동소수점은 비균일한 분포**를 가지는데, 즉 0 근처에 데이터가 많고 매우 크거나 작은 값 주변에는 데이터가 적습니다.
        - FP 형식과 정수 기반 형식 간 데이터 밀도 차이는 F**P 숫자 값이 로그 단위**이기 때문입니다. FP 숫자의 값(FP8 형식)은 다음과 같습니다:
            - Value = (−1)sign × (1 + mantissa) × 2exponent – bias
            - 값 = (-1) 부호 × (1 + 가수) × 2 지수 – 바이어스
        - 지수를 키우면 표현 가능한 숫자들 사이의 간격도 함께 늘어납니다. 예를 들어, 1.0에서 2.0 사이에서는 1.01, 1.001 같은 많은 값을 표현할 수 있지만, 1,000,000에서 2,000,000 사이에서는 가장 작은 스텝 크기가 128 이상으로 훨씬 커집니다(그림 6-15 참고).
            
            !Figure 6-15. INT8과 FP8 format의 data point distribution
            
            Figure 6-15. INT8과 FP8 format의 data point distribution
            
        - **정수 기반 vs 부동소수점 기반 저비트 포맷** : INT8과 FP8은 표현 방식과 error 특성이 다르다
            - **정수 기반(INT8, INT4)**: 데이터 분포가 완전히 균일 - 전체 범위에 걸쳐 값이 균등하게 분포
            - **부동소수점 기반(FP8, FP4)**: 비균일 분포 - 0 근처에 데이터 포인트가 밀집, 극단값 근처는 성김
                - 이유: FP 값은 로그적(logarithmic) 성격
            - 지수가 커질수록 표현 가능한 값 사이의 간격도 커짐 (1.0~2.0 사이는 촘촘, 1,000,000~2,000,000 사이는 듬성)
            - 모델 파라미터(가중치, 활성화)의 실제 데이터 분포에 따라 어느 포맷이 정확도 유지에 더 유리한지 달라짐
        
    - **양자화가 서빙에 도움이 되는 이유 3가지**
        1. **데이터 크기(모델 크기) 감소**
            - ~7 billion parameters × 2 bytes/parameter = 14 billion bytes = 14 GB
            - → INT8로 양자화하면 즉시 7GB로 절반 감소
            - GPU 메모리가 부족할 때 큰 이득
            - 여러 노드가 아니라 하나의 노드/GPU 안에 모델을 넣을 수 있게 됨 → 노드 간 통신 회피
            - 절감된 메모리 공간이 KV 캐시용으로 확보되어 더 많은 동시 요청 처리 가능
        2. **데이터 이동량 감소 → 지연시간 개선**
            - 5장에서 배웠듯, GPU 메모리 대역폭이 특히 decode 단계의 핵심 병목
            - 모델을 작게 만들면 → 필요한 데이터 이동량 자체가 줄어듦 → 추론 지연시간 크게 감소
        3. **연산 속도 향상** : 표 6-2. H100의 정밀도별 FLOPS
            - 비트 수를 절반으로(16→8) 줄이면 대체로 FLOPS가 2배로 뜀 (4비트도 마찬가지)
            
            | 정밀도 | FLOPS |
            | --- | --- |
            | FP64 | 34 teraFLOPS |
            | FP64 Tensor Core | 67 teraFLOPS |
            | FP32 | 67 teraFLOPS |
            | TF32 Tensor Core | 989 teraFLOPS |
            | BFLOAT16 Tensor Core | 1979 teraFLOPS |
            | FP16 Tensor Core | 1979 teraFLOPS |
            | FP8 Tensor Core | 3958 teraFLOPS |
            | INT8 Tensor Core | 3958 TOPS |
        - **요약** : **양자화는 모델 크기 축소 + 데이터 이동량 감소 + 연산 속도 향상**, 이 세 가지를 동시에 제공합니다.
        
    - **Weight-only vs Weight-and-Activation 양자화**
        - 표기법: **W4A16**(가중치 4비트, 활성화 16비트), **W8A8**(가중치·활성화 모두 8비트)
        - **Weight-only 양자화**
            - 가중치만 양자화, 활성화는 그대로
            - **실행 시점에 저비트 값**을 다시 **고비트로 역양자화(dequantize)**해야 함
            - **이득**: 모델 크기·데이터 이동량 감소
            - **손해**: **연산 자체는 빨라지지 않**음 (**역양자화 오버헤드까지 약간 추가**됨)
            - 역양자화를 피하는 방법: **혼합 정밀도 커널**(mixed-precision kernel) 사용
                - Ampere(A100): Marlin 커널
                - Hopper(H100): Machete 커널
                - 예: INT4 행렬 × FP16 행렬을 역양자화 없이 한 번에 곱셈 → 서빙 엔진에서 기본적으로 자동 활성화되는 경우 많음
        - **Weight-and-Activation 양자화**
            - 모델 크기·데이터 이동량 감소는 물론, **활성화까지 양자화**하므로 **compute-bound 워크로드에서 더 높은 FLOPS 달성 가능**
            - **더 복잡함**: 스케일링을 언제 계산할지 선택 필요
                - 동적 스케일링(dynamic scaling): 추론 중 실시간 계산 → 정확도는 좋지만 성능은 낮음
                - 정적 스케일링(static scaling): 배포 전 캘리브레이션 데이터셋으로 미리 계산 → 성능 우수
        - **프로덕션에**서 가장 흔한 조합
            - Weight-only: W4A16 (GPTQ 또는 AWQ 방식)
            - Weight-and-activation: W8A8 (과거 INT8, 최근엔 FP8로 이동 중)
        - 표 6-3. W4A16 vs W8A8 비교
            
            
            | 항목 | W4A16 | W8A8 |
            | --- | --- | --- |
            | 모델 크기/데이터 이동량 감소 | 75% (원본의 1/4) | 50% (원본의 1/2) |
            | 연산 FLOPS | 변화 없음 | 2배 |
            | Prefill(compute-bound) | 변화 없음 | 개선 |
            | Decode(memory bandwidth-bound) | 개선 (저배치에서 강함) | 개선 (고배치에서 강함) |
            | 적합한 상황 |  긴 생성, 지연시간 민감, 저배치 | 긴 컨텍스트, 고처리량, 고배치 |
        - **어떤 양자화 전략을 선택할까**
            - 모델이 커서 단일 GPU/노드에 담기 위해 4배 압축이 필요한 경우 → W4A16
            - 고배치 상황에서는 연산 효율 개선(activation 양자화)의 이득이 메모리 절감보다 더 크게 작용 → decode 단계 병목이 memory-bound → compute-bound로 전환됨
            - 실전 원칙: W8A8만으로 지연시간 SLA를 만족할 수 있다면, W4A16 없이 유효 배치 크기를 최대한 높여 모델 인스턴스당 처리량을 늘려 비용 절감을 추구
        - **데이터 포맷의 최근 변화**
            - 과거 W8A8은 주로 INT8(±127 고정 범위로 클램핑) 사용
            - 최근에는 FP8 변형(E4M3, E5M2)으로 많이 이동
                - NVIDIA 2022년 논문: FP8 E4M3는 캘리브레이션 없이도 FP16 대비 최소한의 정확도 손실로 성능 개선 가능
                - E4M3가 추론에서 더 흔히 쓰임 - E5M2보다 정밀도가 더 높음(단, 동적 범위는 더 좁아 스케일링 필요할 수 있음)
        - **표 6-4. FP8 변형 비교**
            
            
            | **Precision format** | **Total bits** | **Sign bit 부호** | **Exponent 지수부** | **Mantissa 가수부** |
            | --- | --- | --- | --- | --- |
            | FP8 (E4M3) | 8 | 1 | 4 | 3 |
            | FP8 (E5M2) | 8 | 1 | 5 | 2 |
        - **하드웨어 호환성 주의**
            - 모든 GPU가 FP8을 지원하는 것은 아님 → NVIDIA GPU 중 Hopper, Blackwell만 FP8 지원. A100 등 구세대 GPU에서는 FP8의 기대 성능을 온전히 얻기 어려움.
        
    
- **[실습]** **Hands-on quantization** : 원본 모델 vs GPTQ W4A16 vs FP8 W8A8 비교 - 벤치마크 (Qwen2.5-7B-Instruct, vLLM) - Colab
    - Qwen2.5-7B-Instruct 모델 : 이미 **quantized model이 Hugging Face에 올라와 있는 경우 이를 활용**할 수 있다
        
        !Figure 6-16. Hugging Face에서 제공되는 quantized model variants
        
        Figure 6-16. Hugging Face에서 제공되는 quantized model variants
        
    - vLLM으로 원본 모델을 실행하는 기본 예시
        
        ```python
        hf_model_id = "Qwen/Qwen2.5-7B-Instruct"
        !vllm serve {hf_model_id}
        ```
        
    - nvidia-smi 확인
        
        !image.png
        
    - (참고) 직접 GPTQ quantization을 수행하는 예시
        
        ```python
        from transformers import AutoModelForCausalLM, AutoTokenizer, GPTQConfig
        
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
        dataset = [
            "Gptq is an easy-to-use model quantization library with user-friendly APIs, "
            "based on the GPTQ algorithm."
        ]
        gptq_config = GPTQConfig(bits=4, dataset=dataset, tokenizer=tokenizer)
        
        quantized_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-7B-Instruct",
            device_map="auto",
            quantization_config=gptq_config
        )
        ```
        
    - **Performance Analysis**
    - Figure 6-17. Original, GPTQ-Int4, FP8 모델의 TTFT 비교
        
        !image.png
        
    - Figure 6-18. Original, GPTQ-Int4, FP8 모델의 TPOT/ITL 비교
        
        !image.png
        
    - Figure 6-19. Original, GPTQ-Int4, FP8 모델의 request throughput 비교
        
        !image.png
        
    - 결과 해석은 단순하지 않다.
        - Quantization은 memory footprint를 줄이지만, kernel 지원이 부족하면 latency 개선이 제한될 수 있다.
        - Weight-only INT4는 memory 절감이 크지만 activation/compute 경로의 이점은 제한될 수 있고, FP8은 hardware support가 좋을 때 강력하다.
    - **저동시성(low concurrency) 상황**
        - **GPTQ W4A16이 최고 성능** - 원본 대비 지연시간·처리량 약 300% 개선
        - FP8 W8A8도 약 150% 개선
        - **이유**: 저배치에서는 병목이 GPU 메모리 대역폭이고, **GPTQ는 가중치를 INT4(4배 축소)로 줄여 여기서 크게 빛남**
        - 챗봇, AI 에이전트 플로우처럼 **지연시간이 핵심**인 use case → **W4A16 추천**
    - **고동시성(high concurrency) 상황**
        - **GPTQ W4A16의 약점 노출** - weight-only라 연산은 여전히 16비트, 역양자화 오버헤드까지 더해져 **TTFT가 원본보다도 느려짐**
        - **FP8 W8A8이 훨씬 우수** - **활성화까지 양자화**되어 연산 자체가 빨라짐
        - 실전 팁: W8A8 지연시간이 SLA를 충족한다면, 배치를 더 밀어붙여 처리량을 극대화하는 것이 비용 절감의 핵심
    
- **타 양자화 기법** : KV 캐시 / 어텐션 양자화 , GGUF 양자화 , 정확도 트레이드오프, 양자화 인식 훈련
    - **KV 캐시 / 어텐션 양자화**
        - 지금까지 다룬 양자화는 주로 **FFN(피드포워드) 레이어에 집중**, **KV 캐시는 보통 고정밀도로 남겨둠**
        - **KV 캐시 양자화의 이점**: GPU 메모리 확보 → 배치 크기↑ → 처리량↑, 프리픽스 캐싱(이 장 후반부에서 다룸)에도 유리
        - **주의**: KV 캐시만 양자화해서는 지연시간이 크게 줄지 않음 - 어텐션 계산 자체가 여전히 고정밀도면 FLOPS 이득이 없고, 역양자화 필요
        - **완전한 이득을 위해서는 양자화된 어텐션 커널과 함께 사용**해야 함
        - **실전 순서**: 먼저 weight/activation 양자화(예: FP8) → 긴 컨텍스트나 높은 decode 부하 대응이 필요하면 FP8 KV 캐시 양자화 + FP8 어텐션 커널 추가
        - KV cache quantization과 attention quantization은 long-context와 high-concurrency serving에서 memory pressure를 줄이는 데 유용하다
        
    - **GGUF 양자화** - Github , Docs
        - 매우 다른 종류의 양자화 - GPU 대신 **CPU/Apple Silicon(Metal)**에서 로컬로 LLM을 구동하는 데 특화 (필요시 일부만 GPU로 오프로드)
        - 고사양 GPU가 없는 환경을 위한 다양한 정밀도 레벨 지원
        
        !image.png
        
    - **정확도 트레이드오프 Accuracy trade-offs**
        - 양자화의 가장 큰 트레이드오프: **모델 정확도 ↔ 서빙 성능(처리량/지연시간)**
        - 다행히 GPTQ W4A16, AWQ, FP8(W8A8)은 실전 정확도 지표에서 **손실이 미미함이 많은 연구로 검증**됨 (그림 6-20, Neural Magic)
        - 역으로, 양자화로 얻은 성능 여유를 이용해 더 큰 모델을 양자화해서 배포하는 것도 가능 (예: FP8 12B 모델 ≈ FP16 8B 모델과 비슷한 지연시간이지만 처리량·정확도는 더 좋음)
            
            !Figure 6-20. Model size와 quantization method별 OpenLLM Leaderboard score 비교
            
            Figure 6-20. Model size와 quantization method별 OpenLLM Leaderboard score 비교
            
        - **패턴**
            - 모델이 클수록 가중치/KV 캐시 양자화에 더 민감해짐 (정확도 손실 위험 ↑)
            - KV 캐시 양자화는 정확도에 비교적 덜 침습적이지만 성능 개선 폭도 작음 → KV 캐시 공간·ITL 문제가 있을 때만 고려
        - **정확도 평가 도구**
            
            ```python
            lm_eval --model {hf|vllm|sglang} \
              --model_args Qwen/Qwen2-7B-Instruct \
              --tasks gsm8k_cot \
              --device cuda:0 \
              --batch_size auto
            ```
            
        - **현재 연구는 FP4, FP6, W4A8 등 더 낮은 비트로 나아가는 중(Blackwell 세대)**
            - per-tensor/per-channel 스케일링, outlier-aware 클리핑 등으로 정확도 유지를 시도 중이며, 조만간 프로덕션에 등장할 전망
    - **양자화 인식 훈련(Quantization-Aware Training, QAT)**
        - 실무에서는 PTQ가 QAT보다 훨씬 대중적 - 사용이 쉽고 정확도도 준수하기 때문 (훈련 파이프라인 접근 없이도 가능)
        - QAT는 4비트급의 공격적 압축처럼 단순 반올림으로는 모델이 망가지는 경우 신뢰할 수 있는 유일한 선택지가 되기도 함
            
            
            |  | PTQ (Post-Training Quantization) | QAT (Quantization-Aware Training) |
            | --- | --- | --- |
            | 적용 시점 | 훈련 완료 후, 정적 가중치에 적용 | 훈련/파인튜닝 중 양자화 효과를 시뮬레이션 |
            | 난이도 | 훨씬 낮음 (변환 + 일부 캘리브레이션) | 훨씬 높음 (훈련 파이프라인에 추가 연산 필요) |
            | 8비트 이상 정확도 | 좋음 | 좋음 |
            | 4비트 이상 정확도 | 보통 허용 불가 | 더 좋고 허용 가능 |
            | 유연성 | 다양한 하드웨어에 커스텀 튜닝·배포 용이 | 양자화 스킴에 종속되어 추가 파인튜닝·타 하드웨어 배포 유연성 낮음 |
        - **실전 사례: OpenAI GPT-OSS**
            - FP4 E2M1(MXFP4 포맷) 기반 **QAT 사용해 모델을 공격적으로 압축**
            - **OpenAI 발표**: gpt-oss-120b는 단일 80GB GPU에서 효율적으로 실행되며 OpenAI o4-mini와 핵심 추론 벤치마크에서 근접한 성능. gpt-oss-20b는 16GB 메모리 엣지 디바이스에서도 실행 가능, o3-mini와 유사한 성능
            - 모델 크기 추정 (FP4 = 파라미터당 0.5바이트)
                - ~117 billion parameters × 0.5 bytes/parameter = 58.5 billion bytes = 58.5 GB < 80 GB
                - ~21 billion parameters × 0.5 bytes/parameter = 10.5 billion bytes = 10.5 GB < 16 GB
            - **실제로는 MoE(Mixture-of-Experts) 레이어만 FP4로 양자화됨**(7장에서 다룸) - 하지만 전체 파라미터의 90% 이상이 MoE 레이어라 이 추정은 여전히 유효
            - **장점**: 양자화 완료된 상태로 배포되어 별도의 양자화 알고리즘·정밀도 선택 과정 불필요
            - **단점(하드웨어 종속성)**:
                - Blackwell(B200): **NVFP4(E2M1), MXFP4 등 4비트 부동소수점을 네이티브로 지원** → 최적의 배포 환경
                - Hopper(H100/H200): FP8 Tensor Core 중심 설계, 네이티브 FP4는 아니지만 커스텀 소프트웨어 레벨 혼합 정밀도 커널로 여전히 실용적
                - **Ampere(A100/A10) 이하: FP4 지원이 부실** → 이 경우 GPT-OSS 대신 Qwen 같은 다른 아키텍처를 골라 직접 양자화하는 것이 나을 수 있음
            
- **Distillation 증류**
    - 왜 증류(Distillation)가 특별한가
        - 모델 압축의 세 기법(양자화, 증류, 가지치기) 중 저자들이 지연시간·처리량 개선에 **가장 큰 잠재력**이 있다고 보는 것이 바로 모델 증류(distillation)입니다.
        - 양자화·가지치기와의 결정적 차이: 원본 모델의 크기를 줄이는 것이 아니라, **완전히 새로운 작은 모델을 훈련**시킵니다.
        - 크고 원본인 "교사(teacher)" 모델에 인코딩된 지식을 더 작은 "학생(student)" 모델로 전이하는 방식이며, 이 과정에서 학생 모델은 교사 모델을 모방(mimic)하도록 학습됩니다.
        
    - 증류 파이프라인 (그림 6-21)
        
        !Figure 6-21. Teacher model에서 student model을 학습시키는 distillation pipeline
        
        Figure 6-21. Teacher model에서 student model을 학습시키는 distillation pipeline
        
        - 교사 모델이 생성한 출력을 이용해 훨씬 작은 학생 모델을 훈련
        - 교사 모델의 출력은 최종 출력 토큰("hard label")에만 국한되지 않고, 예측 확률 분포의 로짓(logits)이나 손실(loss)까지 포함될 수 있음
        - **중요**: 증류된 학생 모델을 만들려면 **원본 교사 모델에 대한 완전한 접근(full access)이 필요** - 단순히 API로 출력 토큰만 받아오는 것으로는 불가능
        
    - **실전 사례: DeepSeek의 증류 모델**
        - **원본 DeepSeek R1**: 6,710억(671B) 파라미터, MoE 아키텍처 (7장에서 다룰 예정)
        - DeepSeek는 Llama·Qwen 계열의 **오픈소스 dense 모델로 증류한 여러 모델을 공개 (**15억~700억 파라미터 범위)
        - 서빙 관점에서: 모델 크기를 10배 이상 축소 → 서빙 지연시간·처리량에서 엄청난 개선 가능
    - 표 6-6. 원본 R1 vs 700억 파라미터 증류 모델 벤치마크 비교
        - **파라미터가 10배 가까이 줄었음에도 벤치마크 성능 하락은 크지 않은 편입니다!**
        
        | **Benchmark** | **DeepSeek-R1-671B** | **DeepSeek-R1-Distill-Llama-70B** |
        | --- | --- | --- |
        | MATH-500 pass@1 | 97.3 | 94.5 |
        | GPQA Diamond pass@1 | 71.5 | 65.2 |
        | LiveCodeBench (Pass@1) | 65.9 | 57.5 |
    - 양자화 vs 증류: 어떤 것을 먼저 시도해야 하나
        
        
        |  | 양자화 | 증류 |
        | --- | --- | --- |
        | 정확도 하락 |  낮음 (보통 3% 이하) | 양자화보다 훨씬 큼 |
        | 속도 향상 | 1.5배~3배 | 훨씬 큼, 대신 정확도 트레이드오프 존재 |
        | 사용 난이도 | Post-training 양자화는 매우 쉬움 - 원본 모델 가중치만 있으면 됨 | 이미 증류된 모델이 없으면 훨씬 어려움 -훈련 비용이 원본 모델 훈련 비용의 최대 10%에 달할 수 있음, 보통 원본 모델을 훈련한 연구진이 직접 수행 |
    - 실전 가이드 (저자들의 일반적 권장 순서)
        1. 먼저 저비용·쉬운 해법부터 시작
        2. 예: DeepSeek-R1-671B와 DeepSeek-R1-Distill-Llama-70B 중 하나를 배포하려 한다면:
            - 이미 증류된 모델이 존재한다면 → 먼저 그 모델을 평가해서 정확도 기준을 충족하는지 확인 → 충족하면 그 증류 모델을 채택
            - 증류 모델을 이미 채택했다면, 그 위에 양자화를 추가로 적용해 서빙 성능을 더 끌어올리고 비용을 절감 가능
            - 증류 모델이 준비되어 있지 않은 경우(실제로 대부분 이런 상황) → 양자화를 먼저 시도해야 함 — 증류는 비용이 크고 정확도 손실도 더 크기 때문
    - 요지:
        - 증류는 가장 큰 성능 개선 잠재력을 지녔지만, 직접 수행하기엔 비용과 난이도가 매우 높은 기법입니다.
        - 따라서 실무에서는 "이미 만들어진 증류 모델이 있는가?"를 먼저 확인하고, 없다면 훨씬 저렴하고 쉬운 양자화부터 적용하는 것이 합리적인 순서라는 것이 이 절의 핵심 메시지입니다.
        - 즉, 증류와 양자화는 경쟁 관계가 아니라 상호 보완적(증류된 모델에 양자화를 추가 적용 가능)이라는 점도 중요합니다.
    
- **Pruning 가지치기**
    - 세 번째 압축 기법, 가장 덜 대중적
        - 모델 압축의 마지막 기법은 가지치기(pruning)로, 이 책 집필 시점(2025년 중반) 기준 프로덕션에 적용하기 위해 아직 더 많은 연구와 작업이 필요해서 세 기법 중 가장 덜 대중적입니다.
    - 핵심 아이디어
        - 모델은 보통 과도하게 파라미터화(overparameterized)되어 있으므로, 불필요한(redundant) 부분을 가지치기하면 더 나은 압축을 달성하고 결과적으로 서빙 성능을 개선할 수 있다는 것.
    - 가지치기의 두 유형
        - 구조적 가지치기(structured pruning) : 모델의 특정 섹션(구획) 전체를 제거
        - 비구조적 가지치기(unstructured pruning) : 개별 가중치를 더 유연하게 제거
        
    - **Pruning은 중요도가 낮은 weight, channel, neuron, attention head 등을 제거해 모델을 작게 만드는 방법이다.**
        
        !Figure 6-22. 2:4 structured sparsity pattern과 compression
        
        Figure 6-22. 2:4 structured sparsity pattern과 compression
        
        - 원본 행렬(왼쪽)에서 연속된 4개 값마다 2개를 0으로 처리(흰색으로 표시)
        - 희소성 비율 = 2:4 = 50% (녹색으로 표시된 값만 남김)
        - 압축 후 행렬(오른쪽)은 여전히 연산을 위한 밀집(dense) 행렬 형태로 재구성됨
    - **하드웨어 지원**
        - NVIDIA GPU 아키텍처(Ampere, Hopper)는 이런 구조적 희소성을 가속하는 스파스 텐서 코어(sparse Tensor Cores)를 탑재
        - 50% 희소성은 행렬 곱셈 속도를 직접적으로 2배까지 끌어올릴 수 있음 → 상당한 성능 향상
    

### Prefix Caching

- **RadixAttention**
    - Prefix caching은 여러 request가 동일하거나 유사한 prefix를 공유할 때 prefill 결과를 재사용하는 기법이다. System prompt, instruction, static context, RAG document prefix가 반복되는 agent/RAG workload에서 특히 유용하다.
    - RadixAttention
        
        !Figure 6-23. 두 request가 동일 prefix를 공유하는 radix tree 예시
        
        Figure 6-23. 두 request가 동일 prefix를 공유하는 radix tree 예시
        
        - RadixAttention은 prefix를 radix tree로 관리해 공통 prefix를 효율적으로 찾고 cache hit를 높인다.
    - 유사하지만 완전히 같지 않은 prompt들은 prefix cache hit가 달라질 수 있다.
        
        ```python
        Prompt 1: Hi, what is the weather like today?
        Prompt 2: Hi, what is the weather like now?
        Prompt 3: What is the weather like today?
        ```
        
    - 정적 context가 반복되는 prompt는 prefix caching에 적합하다.
        
        ```python
        <system>
        You are a helpful assistant.
        <context>
        Document: {puts the relevant static context here each time}
        <user>
        {dynamic questions from user}
        ```
        
    - RAG에서는 retrieved chunk의 순서가 바뀌면 prefix cache hit가 떨어질 수 있다.
        
        ```python
        Document 1: <retrieved_text_chunk_1>
        Document 2: <retrieved_text_chunk_2>
        Document 3: <retrieved_text_chunk_5>
        Document 4: <retrieved_text_chunk_7>
        ```
        
        ```python
        Document 1: <retrieved_text_chunk_5>
        Document 2: <retrieved_text_chunk_7>
        Document 3: <retrieved_text_chunk_1>
        Document 4: <retrieved_text_chunk_2>
        ```
        
    - User/session id를 prefix 앞쪽에 넣으면 사용자별 cache isolation에는 좋지만, 전체 cache sharing은 줄어들 수 있다.
        
        ```python
        <system>
        You are a helpful assistant.
        <id> {user id or session id}
        <context>
        Document: {puts the relevant static context here each time}
        <user>
        {dynamic questions from user}
        ```
        
    
- **Prefix Cache Best Practices**
    - Stable system prompt를 앞쪽에 둔다.
    - RAG document ordering을 안정적으로 유지한다.
    - 사용자별 personalization 정보가 cache sharing을 방해하지 않도록 위치를 신중히 정한다.
    - Cache hit rate, TTFT 개선, memory pressure를 함께 측정한다.
    - Multi-replica serving에서는 cache-aware routing을 고려한다
        
        
    - **Scaling Prefix Cache**
    - 여러 model instance가 있을 때 request를 아무 replica로나 보내면 prefix cache hit가 낮아질 수 있다. Cache-aware router는 request prefix와 model instance의 cache 상태를 보고 hit 가능성이 높은 instance로 라우팅한다.
        
        !Figure 6-24. Prefix cache hit rate를 높이기 위한 cache-aware routing
        
        Figure 6-24. Prefix cache hit rate를 높이기 위한 cache-aware routing
        
    
- Summary
    - 이번 장에서는 실제 배포 환경에서 LLM 서비스 성능을 최적화하기 위한 다양한 기법들을 자세히 살펴보았습니다.
    - 이 장은 온라인 요청 처리 및 스케줄링 기법을 탐구하는 것으로 시작되었습니다. 여러 입사 요청을 배치로 집계함으로써 모델은 이를 더 효율적으로 처리할 수 있어 산술 집약도와 전체 처리량을 최적화합니다. 동적 배칭은 일반적인 머신러닝 작업에서 흔히 사용되는 전략입니다. 더 발전된 기법인 연속 배칭은 LLM을 직접 다루며, 동적 배칭보다 우선적으로 새로운 요청을 지속적으로 배치에 추가해 GPU 유휴 시간을 줄입니다. 현재 LLM 온라인 서비스에서는 연속 배치가 기본적인 해결책으로 사용되고 있습니다. 게다가 TTFT와 ITL의 균형을 맞추고 전체 처리량을 향상시키기 위해, 매우 긴 문맥과 대화형 사용 사례를 처리할 수 있도록 청킹된 프리필을 활성화하고 조정할 수 있습니다.
    - 다음으로, 주의 계산을 어떻게 향상시킬 수 있는지 살펴보았습니다. 이를 위한 한 가지 방법은 MHA에서 MQA, GQA로 진화하는 과정에서 정확성을 유지하면서 여러 헤드에 동일한 KV를 공유해 KV 캐시 크기를 줄이는 것입니다. 또 다른 방법은 DeepSeek의 MLA와 같은 스마트 컴프레션을 수행하는 것입니다. 그다음 우리는 커널 최적화가 어텐션 계산 성능을 어떻게 향상시킬 수 있는지 설명했는데, 예를 들어 계산 중 메모리로 왕복하는 횟수를 줄이기 위해 커널 융합을 수행하는 방식이 있습니다. 또한 타일링 같은 기법을 활용해 알고리즘이 현저한 메모리 사용(HBM)을 현명하게 피하는 FlashAttention도 살펴보았습니다. 대신 하드웨어 IO 사양과 제한에 따른 HBM 병목 현상을 피하기 위해 데이터를 SRAM에 보관합니다. 마지막으로, 계산을 위한 커널과 비교적 독립적인 PagedAttention은 KV 캐시를 페이지라는 작은 블록으로 나누어 메모리 단편화를 줄이고 GPU 메모리 접근을 최적화하는 데 중점을 둡니다. 이는 현재 LLM 서비스를 위한 KV 캐시 관리의 기본 선택 사항입니다.
    - 모델 서빙 성능을 더욱 향상시키기 위해, 모델 압축은 일부 정확도를 희생하는 대신 크기를 크게 줄이고 실행 성능을 개선합니다. 산업 현장에서 가장 흔히 쓰이는 기법은 양자화, 특히 사후 학습 양자화(PTQ)로, 모델 학습이 끝난 후 모델 가중치를 높은 비트 형식에서 낮은 비트 형식으로 양자화하는 것입니다. 우리는 양자화 기법과 저비트 포맷, 그리고 이들의 장단점에 대해 논의했습니다. 또한, 큰 모델이 작은 모델을 가르칠 수 있는 모델 증류와, 모델 내 불필요하고 중요하지 않은 가중치를 줄이는 모델 가지치기 같은 다른 모델 압축 기법들도 간단히 살펴보았습니다.
    - 마지막으로, LLM 전용 요청 캐싱 방법인 프리픽스 캐싱이 부분적으로 본 요청을 재사용하는 데 어떻게 도움이 되는지 보여드렸습니다. 이를 통해 저장 공간을 절약하고 계산량을 줄이며 매우 빠른 TTFT를 실현할 수 있습니다. 프리픽스 캐싱은 멀티턴 채팅과 긴 문맥 처리가 필요한 상황에서 뛰어난 성능을 발휘하며, 이는 현대 LLM 애플리케이션에서 점점 더 중요해지고 있습니다.
    - 이제 특히 단일 GPU에서 실행되는 소형 LLM을 효율적으로 지원할 수 있는 필수 지식을 갖추게 되었습니다. 다음 장에서는 분산 방식으로 대규모 LLM을 운영하는 데 도움이 되는 고급 주제들을 다루고, 단일 모델 복제본에 집중하는 대신 시스템으로서 LLM을 개선하는 방법을 살펴보겠습니다.

### 3주차 과제

- **3주차 스터디**에서 학습한 내용 혹은 **LLM 관련 내용(혹은 도전과제)**을 **간략히 정리**하여 **공개된 링크에 글 작성** 후 해당 링크를 **과제제출표**에 공유 🙇🏻‍♂️🙇🏻‍♀️
    - **작성 도구** : 블로그, Github, 개인 홈페이지, 개인 Youtube, ‘페이스북/링크드인 공개 게시 글’ 등
    - **정리 내용(예시)**
        - 해당 주차 스터디에서 학습한 내용을 요약 정리 작성
        - 해당 주차 스터디에서 다룬 주제 기술 1개를 별도 조사 학습해서 정리
        - LLM 서빙 관련 운영 경험 중 기술 내용 위주로 정리
        - 최근 LLM 서빙 관련 새로운 기술에 대한 분석 정리

### 도전 과제

- `도전과제` ’vLLM 혹은 SGLang’ 에서 (연속) **배칭 ON vs 배칭 효과 무력화** `max_num_seqs=1` 시 서빙 처리 성능과 지연시간 측정 후 정리
- `도전과제` ’vLLM 혹은 SGLang’ 에 ‘max batch size, max model length, max number of tokens’ 기본값 확인 및 변경 후 서빙 성능 측정 비교
- `도전과제` ’vLLM 혹은 SGLang’ 에 **Chunked Prefill** ON vs Off 와 `--max-num-batched-tokens` 튜닝 후 성능 측정 비교
- `도전과제` ’vLLM 혹은 SGLang’ 에서 ‘MHA vs GQA vs MQA vs MLA’ 어텐션 모델 별 추론 처리 속도와 모델 품질 측정 비교
- `도전과제` ’vLLM 혹은 SGLang’ 에서 ‘**FlashInfer 커널(FlashAttention, 2/3/4)**’ 설정 및 성능 측정 비교