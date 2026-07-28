# 05. 1주차 예습 노트 — CH1·CH2

**스터디 1주차: 2026-08-02 (일) 20:30** · 범위 **CH1 모델 서빙 소개 + CH2 LLM 서빙**

교재가 없어도 따라갈 수 있도록, 대응하는 [Inference Engineering PDF](./references/pdf/inference-engineering-2026.pdf)를 직접 읽고 **1주차에 나올 개념만** 추려 정리했습니다. 괄호 안 쪽수는 그 PDF 기준이며, 더 깊게 보고 싶을 때 펼치면 됩니다.

| 교재 | 대응 자료 |
|---|---|
| CH1 Introduction to Model Serving and Optimization | Inference Engineering **CH0 Inference** (p.17) |
| CH2 Large Language Model Serving | Inference Engineering **CH2 Models** (p.41), 특히 **2.2**(p.48)·**2.4**(p.63) |

---

## 1. 추론(Inference)이란 어디에 있는 단계인가

생성형 AI 모델의 생애주기는 두 단계입니다.

| 단계 | 내용 |
|---|---|
| **Training** | 데이터로부터 모델 가중치를 학습 |
| **Inference** | **프로덕션에서 모델을 서빙** ← 이 스터디의 전부 |

지난 10년 ML 붐에서 수많은 엔지니어가 두 단계를 모두 익혔지만, **고전 ML의 추론은 상대적으로 단순**했습니다. XGBoost 모델을 가벼운 CPU와 단순한 소프트웨어 스택으로 돌리면 됐습니다.

> 반면 **생성형 AI의 추론은 복잡합니다.** 가중치를 가져와 GPU에 얹는다고 대규모 프로덕션에 쓸 만큼 빠르고 안정적이 되지 않습니다. (p.17)

## 2. 추론 스택의 3계층 ★ CH1의 뼈대

| 계층 | 책임 |
|---|---|
| **Runtime** | **단일 GPU 인스턴스에서 단일 모델**의 성능 최적화 |
| **Infrastructure** | 클러스터·리전·클라우드를 넘나드는 **확장**, 사일로 없이 높은 가동률 유지 |
| **Tooling** | 엔지니어에게 **적절한 추상화 수준**을 제공해 제어와 생산성의 균형 |

세 계층이 함께 맞물려야 미션 크리티컬한 대규모 추론이 가능합니다.

**Runtime 계층이 의존하는 소프트웨어 스택**: CUDA → PyTorch → 추론 엔진(vLLM, SGLang, TensorRT-LLM). 여기에 **FlashAttention** 같은 저수준 커널이 상당한 성능 이득을 줍니다.

### Runtime의 5가지 성능 기법 ★ 스터디 전체의 지도

이 5개가 사실상 **CH5~8의 목차**입니다. 1주차에 이름만 익혀두면 이후가 편합니다.

| 기법 | 한 줄 정의 | 나중에 다룰 곳 |
|---|---|---|
| **Batching** | 들어오는 요청을 병렬 실행하되 **토큰 단위로 엮어** 처리량을 올림 | CH3, CH6 |
| **Caching** | 어텐션 결과인 **KV cache를 프리픽스가 겹치는 요청 간 재사용** | CH6 (prefix caching) |
| **Quantization** | 모델 일부의 **정밀도를 낮춰** 더 많은 연산을 쓰고 메모리 부담을 줄임 | CH6, CH9 |
| **Speculation** | draft 토큰을 만들어 검증해 **디코드 1회 forward에 2개 이상** 토큰 생성 | CH7 |
| **Parallelism** | 큰 모델을 **여러 GPU로** 가속 | CH7 |

## 3. LLM이 토큰을 만드는 방식 ★ CH2의 핵심

> LLM은 **자기회귀(autoregressive) 토큰 생성 모델**입니다. 이전 토큰 전부를 근거로 **한 번에 하나씩** 새 토큰을 만듭니다. (p.46)

### 토큰과 토크나이저

- 토큰 = 텍스트 덩어리를 나타내는 **숫자**. 현대 LLM은 **서브워드 토큰화**를 써서 토큰 하나가 단어이거나 단어의 일부
- **토크나이저에는 신경망이 없습니다.** 문자열 ↔ 숫자의 단순 매핑일 뿐
- **Vocabulary** = 토큰과 문자열의 전체 매핑. 대부분 모델이 **10만 개 이상**
- 최신 모델일수록 효율적인 토큰화를 씁니다 — **출력에 필요한 토큰이 적을수록 종단간 추론이 빠름**

### 세 개의 시퀀스

| 시퀀스 | 내용 |
|---|---|
| **Input** | 프롬프트, 대화, 컨텍스트, 함수 등 입력 |
| **Reasoning** | (선택) 추론 모델의 **중간 사고 출력** |
| **Output** | 모델이 생성한 응답 |

셋을 합친 길이가 **컨텍스트 윈도우**로 제한되고, 요청은 `max_tokens`로 출력을 더 제한할 수 있습니다.

### Chat Template — 실무에서 자주 깨지는 지점

입력은 하나의 문자열이지만, LLM은 **역할이 있는 멀티턴 대화 / 툴 콜용 함수 시그니처 / 멀티모달 입력**을 받도록 학습됩니다. 이것들을 **단일 시퀀스로 합치는 게 chat template**인데:

> 모델마다 **미묘하게 다르고**, 추론 엔진이 이를 **정확히 구현해야** 합니다. (p.47)

체크리스트에 넣어두세요 — 모델을 바꿨는데 품질이 이상하면 chat template을 먼저 의심합니다.

## 4. Prefill과 Decode ★ 1주차에서 가장 중요

토큰화 이후, 추론은 두 단계로 나뉩니다.

| 단계 | 하는 일 |
|---|---|
| **Prefill** | 입력 시퀀스를 처리해 **각 입력 토큰의 어텐션을 계산**하고 그 값을 **KV cache에 저장** |
| **Decode** | 모델을 forward pass 하며 **토큰을 하나씩 생성** |

이 구분이 왜 중요한지는 다음 장에서 드러납니다.

## 5. 병목 — 왜 최적화 방법이 갈리는가 ★★

GPU에는 두 가지 자원이 있습니다.

| 자원 | 단위 |
|---|---|
| **Compute** | 초당 부동소수점 연산 수 (FLOPS) |
| **Memory bandwidth** | 초당 옮길 수 있는 바이트 수 |

완벽히 최적화된 시스템이라면 연산이 메모리를 기다리며 놀지 않고, 메모리 대역폭도 연산을 기다리며 놀지 않습니다. 현실에는 **한쪽이 포화인데 다른 쪽은 놀고 있는 불균형** = 병목이 있습니다.

> **병목을 찾는 것이 성능 개선의 첫 단계입니다.** 어떤 연산이 메모리 대역폭에 묶여 있다면, **연산 최적화를 아무리 해도 빨라지지 않습니다.** 반대도 마찬가지입니다. (p.61)

### 추론 시스템의 전형적 병목

| 작업 | 병목 |
|---|---|
| **LLM prefill** (KV cache 구축) | **compute bound** |
| **LLM decode** (토큰 생성) | **memory bound** |
| 이미지·비디오 생성 | compute bound |

**그래서 배칭이 통합니다**: 여러 요청을 묶으면 **같은 메모리 트래픽으로 더 많은 연산**을 하므로, decode의 memory bound 성격이 완화됩니다.

### ops:byte ratio — 숫자로 판단하기

GPU마다 연산 속도와 메모리 대역폭이 정해져 있고, 둘의 비가 **ops:byte ratio**입니다.

> **H100, FP16 기준**
> 연산 **989 TFLOPS** ÷ 대역폭 **3.35 TB/s** ≈ **295**
>
> → H100에서 FP16 추론이 완벽히 균형을 이루려면 **메모리에서 1바이트 읽을 때마다 295번의 부동소수점 연산**을 해야 합니다. (p.62)

이 수치보다 연산량이 적으면 memory bound, 많으면 compute bound입니다. **3주차 CH5(핵심 과제)의 계산이 전부 여기서 출발**합니다.

---

## 스터디 중 확인할 질문

강의를 들으며 아래가 채워지는지 보세요. 안 채워지면 그게 곧 질문거리입니다.

- [ ] 배칭이 decode의 memory bound를 완화한다면, **배치를 무한정 키우면 왜 안 되나?** (힌트: TTFT)
- [ ] KV cache는 요청마다 쌓이는데, **동시 요청 수의 상한**은 무엇이 정하나?
- [ ] prefill이 compute bound라면 **긴 프롬프트 요청이 다른 요청을 얼마나 방해**하나?
- [ ] 내가 쓸 GPU의 ops:byte ratio는 얼마이고, **내 워크로드는 어느 쪽**인가?

## 용어 체크 — 1주차 끝나고 설명할 수 있어야

`Training/Inference` · `Runtime/Infrastructure/Tooling` · `토큰` · `서브워드 토큰화` · `vocabulary` · `컨텍스트 윈도우` · `chat template` · `자기회귀 생성` · **`prefill`** · **`decode`** · **`KV cache`** · `compute bound` · `memory bound` · `ops:byte ratio` · `배칭` · `양자화` · `speculative decoding` · `병렬화`

## 더 볼 것

| 목적 | 자료 |
|---|---|
| 영상으로 먼저 (20분) | [prefill 5분](https://youtu.be/Vuu27UTFUZ8) → [KV cache 8분](https://youtu.be/sq3XGM1qdQY) → [Flash attention 7분](https://youtu.be/4Tw_ytMYHLI) |
| 손으로 만져보기 | [Transformer Explainer](https://poloclub.github.io/transformer-explainer/) |
| KV cache 수식·메모리 계산 | [deep-dives.md](./references/deep-dives.md) → KV Cache (chooblog) |
| 원문 더 읽기 | `python3 tools/search_index.py --outline inference-engineering --depth 3` |

```bash
# 궁금한 개념의 위치를 바로 찾기
python3 tools/search_index.py "ops:byte"
python3 tools/search_index.py "prefill decode"
```

> 이 노트는 **Inference Engineering PDF를 읽고 1주차 범위만 추린 것**이며, 교재(Hands-On LLM Serving and Optimization) 자체의 서술과는 다를 수 있습니다. 스터디에서 다루는 내용이 우선입니다.
