# 영상 레퍼런스

노션의 **"스터디 전 시청 권장 영상"**(필수)과 **"추천 Youtube"** 토글(선택) 전체를 정리했습니다.
👍🏻 = 노션 원문에서 꼭 미리 보라고 표시된 영상, `*` = 원문의 강조 표시.

- [Part 1. 사전 시청 권장 (필수)](#part-1-사전-시청-권장-필수) — 22편
- [Part 2. 추천 Youtube (선택)](#part-2-추천-youtube-선택) — 채널 6개 + 영상 60여 편

---

# Part 1. 사전 시청 권장 (필수)

## 1. 하드웨어 기초 — CPU / GPU / 메모리

| 영상 | 채널 | 길이 | 링크 |
|---|---|---|---|
| 👍🏻 인공지능의 작동방식, 초거대 AI는 어떻게 미래를 바꿀까? | bRd 3D | 15분 | [Youtube](https://youtu.be/p-DkRe-EJiY) |
| CPU는 어떻게 작동할까 | bRd 3D | — | [Youtube](https://youtu.be/Fg00LN30Ezg) |
| GPU는 어떻게 작동할까 | bRd 3D | — | [Youtube](https://youtu.be/ZdITviTD3VM) |
| 👍🏻 왜 컴퓨터는 한 가지 종류의 메모리만 사용하지 않을까요? | Branch Education | 27분 | [Youtube](https://youtu.be/TfhL5kBiQVI) |

**왜 보나**: LLM 추론 성능은 결국 *메모리 대역폭*과 *연산 유닛*의 싸움입니다. 메모리 계층(SRAM/HBM/DRAM) 개념이 뒤에 나올 KV cache, Flash Attention, 메모리 벽(memory wall) 이해의 전제입니다.

## 2. 트랜스포머 / 어텐션 원리

| 영상 | 채널 | 길이 | 링크 |
|---|---|---|---|
| 👍🏻 LLM 설명 (요약버전) | 3Blue1Brown 한국어 | 8분 | [Youtube](https://youtu.be/HnvitMTkXro) · [arXiv](https://arxiv.org/abs/1706.03762) |
| 👍🏻 트랜스포머, ChatGPT가 트랜스포머로 만들어졌죠 — DL5 | 3Blue1Brown 한국어 | 27분 | [Youtube](https://youtu.be/g38aoGttLhI) |
| 👍🏻 그 이름도 유명한 어텐션, 이 영상만 보면 이해 완료! — DL6 | 3Blue1Brown 한국어 | 26분 | [Youtube](https://youtu.be/_Z3rXeJahMs) |
| 수많은 정보는 LLM 모델 속 어디에 저장되어있는걸까? — DL7 | 3Blue1Brown 한국어 | 22분 | [Youtube](https://youtu.be/zHQLPJ8-9Qc) |
| 👍🏻 Attention/Transformer 시각화로 설명 | 딥러닝 큐레이터 임커밋 | 30분 | [Youtube](https://youtu.be/6s69XY025MU) |
| 언어 모델 개념 이해하기 | 딥러닝 큐레이터 임커밋 | 10분 | [Youtube](https://youtu.be/fn2xwgvQD7c) |

## 3. 추론(Inference) 핵심 개념 — 서빙 최적화 직결

| 영상 | 채널 | 길이 | 링크 |
|---|---|---|---|
| 👍🏻 **KV cache** | 딥러닝 큐레이터 임커밋 | 8분 | [Youtube](https://youtu.be/sq3XGM1qdQY) |
| 👍🏻 **LLM prefill** 설명 | 딥러닝 큐레이터 임커밋 | 5분 | [Youtube](https://youtu.be/Vuu27UTFUZ8) |
| 👍🏻 **Flash Attention**의 원리 | 딥러닝 큐레이터 임커밋 | 7분 | [Youtube](https://youtu.be/4Tw_ytMYHLI) |

**왜 보나**: prefill / decode 구분과 KV cache는 LLM 서빙 시스템(연속 배칭, PagedAttention, prefill-decode 분리 등)을 이해하는 최소 전제입니다. 3편은 짧으니 반드시 보는 것을 권장.

## 4. 추론 엔지니어링 심화 — [PY] Technical Explainer Videos

| 영상 | 길이 | 링크 |
|---|---|---|
| 2조 개 매개변수를 가진 LLM을 훈련시키는 데 필요한 엔지니어링 | 28분 | [Youtube](https://youtu.be/yn4GGAtZ7QE) |
| LLM 추론의 공학적 배경: **메모리 벽** | — | [Youtube](https://youtu.be/ENkuf_2zbkc) |
| LLM 추론의 공학적 원리: **GPU 내부 들여다보기** | — | [Youtube](https://youtu.be/cbEhkd4ZeKs) |
| LLM 추론의 공학: **커널과 메모리** | — | [Youtube](https://youtu.be/30IRJQ49M2g) |
| LLM 추론의 엔지니어링: **양자화(Quantization)** | — | [Youtube](https://youtu.be/1JWnEze9V5g) |
| LLM 추론의 공학적 원리: **병렬 처리** | — | [Youtube](https://youtu.be/Kjq2vCIH3S8) |
| LLM 추론의 엔지니어링: **Mixture of Experts (MoE)** | — | [Youtube](https://youtu.be/gskjdulkP00) |

**왜 보나**: 4주차(CH7~8 고급 최적화)에서 다룰 양자화 · 병렬 처리(TP/PP/EP) · MoE 서빙의 배경 지식과 그대로 겹칩니다.

### 추천 시청 순서

```
1) 하드웨어 기초 (메모리 계층) ─── 27분 + α
        ↓
2) 트랜스포머/어텐션 (3B1B DL5·DL6) ─ 53분
        ↓
3) 추론 핵심 3종 (prefill → KV cache → Flash Attention) ─ 20분  ★ 최우선
        ↓
4) 추론 엔지니어링 심화 (메모리 벽 → GPU 내부 → 커널/메모리 → 양자화 → 병렬 → MoE)
```

시간이 부족하면 **3번 그룹(20분) → 2번 요약본(8분) → 1번 메모리 편(27분)** 순으로 보세요.

---

# Part 2. 추천 Youtube (선택)

노션 "추천 Youtube" 토글 전체. Part 1과 겹치는 영상은 ★로 표시했습니다.

## 채널 바로가기

| 채널 | 성격 | 링크 |
|---|---|---|
| bRd 3D | 3D 시각화 하드웨어 설명 (한국어) | [Youtube](https://www.youtube.com/@bRd3D) |
| Branch Education | 3D 시각화 하드웨어 설명 (영어) | [Youtube](https://www.youtube.com/@BranchEducation/videos) |
| 3Blue1Brown 한국어 | 수학·딥러닝 시각화 | [Youtube](https://www.youtube.com/@3Blue1BrownKR) |
| [PY] Technical Explainer | LLM 추론 엔지니어링 심화 | [Youtube](https://www.youtube.com/@thecommitlog/videos) |
| 딥러닝 큐레이터 임커밋 | 짧고 정확한 개념 시각화 (한국어) | [Youtube](https://www.youtube.com/@%EC%9E%84%EC%BB%A4%EB%B0%8B/videos) |
| Visual AI | 트랜스포머 내부 시각 해설 (영어) | [Youtube](https://www.youtube.com/@VisualAIOfficial/videos) |

## bRd 3D

| 영상 | 링크 |
|---|---|
| CPU는 어떻게 작동할까?* ★ | [Youtube](https://youtu.be/Fg00LN30Ezg) |
| GPU는 어떻게 작동할까* ★ | [Youtube](https://youtu.be/ZdITviTD3VM) |
| 인공지능의 작동방식, 초거대 AI는 어떻게 미래를 바꿀까?* ★ | [Youtube](https://youtu.be/p-DkRe-EJiY) |
| 양자컴퓨터는 어떻게 작동할까? | [Youtube](https://youtu.be/8GummfGLBc0) |

## Branch Education

| 영상 | 링크 |
|---|---|
| CPU는 어떻게 작동하나요? | [Youtube](https://youtu.be/16zrEPOsIcI) |
| How do Graphics Cards Work? Exploring GPU Architecture | [Youtube](https://youtu.be/h9Z4oGN89MU) |
| 왜 컴퓨터는 한 가지 종류의 메모리만 사용하지 않을까요?* ★ | [Youtube](https://youtu.be/TfhL5kBiQVI) |

## 3Blue1Brown 한국어

| 영상 | 링크 |
|---|---|
| LLM 설명 (요약버전)* ★ | [Youtube](https://youtu.be/HnvitMTkXro) |
| 뉴럴네트워크라는걸 들어 보셨다면 보셔야 할 영상 — DL1 | [Youtube](https://youtu.be/wrguEHxk_EI) |
| 백프로파게이션 개념적으로 이해하기 — DL3 | [Youtube](https://youtu.be/tkH7KgLZc0E) |
| 백프로파게이션 두번째: 실제 계산 — DL4 | [Youtube](https://youtu.be/HKqdFQfXVhw) |
| 트랜스포머, ChatGPT가 트랜스포머로 만들어졌죠 — DL5* ★ | [Youtube](https://youtu.be/g38aoGttLhI) |
| 그 이름도 유명한 어텐션 — DL6 ★ | [Youtube](https://youtu.be/_Z3rXeJahMs) |
| 수많은 정보는 LLM 모델 속 어디에 저장되어있는걸까? — DL7 ★ | [Youtube](https://youtu.be/zHQLPJ8-9Qc) |

## [PY] Technical Explainer Videos

LLM 추론 엔지니어링을 주제별로 파고드는 채널. Part 1의 7편 외에 아래가 추가로 있습니다.

| 영상 | 링크 |
|---|---|
| The Engineering Behind LLM Inference: **Quantization** ★ | [Youtube](https://youtu.be/1JWnEze9V5g) |
| The Engineering Behind LLM Inference: **Kernels and Memory*** ★ | [Youtube](https://youtu.be/30IRJQ49M2g) |
| LLM 추론의 엔지니어링: **Mixture of Experts** ★ | [Youtube](https://youtu.be/gskjdulkP00) |
| LLM 추론의 공학적 원리: **병렬 처리** ★ | [Youtube](https://youtu.be/Kjq2vCIH3S8) |
| LLM 추론의 공학적 원리: **GPU 내부 들여다보기*** ★ | [Youtube](https://youtu.be/cbEhkd4ZeKs) |
| LLM 추론의 공학적 배경: **메모리 벽*** ★ | [Youtube](https://youtu.be/ENkuf_2zbkc) |
| **프롬프트 캐싱**이 장기 컨텍스트 LLM 에이전트를 실용화한 방법 | [Youtube](https://youtu.be/H-k7oYjwruM) |
| 2조 개 매개변수를 가진 LLM을 훈련시키는 데 필요한 엔지니어링* ★ | [Youtube](https://youtu.be/yn4GGAtZ7QE) |
| AI 에이전트에 대한 재고찰: 하네스 엔지니어링의 부상 | [Youtube](https://youtu.be/Xxuxg8PcBvc) |
| 기계적 해석 가능성: LLM 역설계 | [Youtube](https://youtu.be/tDzqCDEYc0A) |
| AI 비디오 생성의 내부 구조: 기술적 분석 | [Youtube](https://youtu.be/t6f-XJhTL4Q) |
| 인공지능이 이미지를 생성하는 방법 (확산 모델 설명) | [Youtube](https://youtu.be/7juab9uDvJ4) |
| 재귀적 언어 모델이란 정확히 무엇일까요? | [Youtube](https://youtu.be/b8r4l-Xanlw) |
| 클로드 코드의 내부: AI 에이전트의 아키텍처 | [Youtube](https://youtu.be/ofLvTNZEHVk) |
| 인공지능이 추론하는 법을 배우는 방법: DeepSeek과 o1 | [Youtube](https://youtu.be/uUTTeGVB6z8) |
| AI 프롬프트의 전체 여정 | [Youtube](https://youtu.be/nmBqcRl2tmM) |
| LLM은 이미지를 어떻게 이해하는가? | [Youtube](https://youtu.be/PuodF4pq79g) |
| 즉각적인 AI 응답의 이면에 숨겨진 엔지니어링 | [Youtube](https://youtu.be/SyFcoaIVad4) |

## 딥러닝 큐레이터 임커밋 — 시각화로 쉽게 설명

노션에서 번호가 붙어 있는 시리즈입니다. **[0]~[5] 순서대로 보면 서빙 최적화 개념이 한 번에 잡힙니다.**

| 영상 | 링크 |
|---|---|
| [0] Attention/Transformer 시각화로 설명* ★ | [Youtube](https://youtu.be/6s69XY025MU) |
| [1] **KV cache*** ★ | [Youtube](https://youtu.be/sq3XGM1qdQY) |
| [2] **LLM prefill** 설명* (KV 캐시 설명 포함) ★ | [Youtube](https://youtu.be/Vuu27UTFUZ8) |
| softmax에 숨어있던 잡기술 | [Youtube](https://youtu.be/SAHGsTbZGyA) |
| [3] **Flash attention의 원리*** (HBM/SRAM 동작 포함) ★ | [Youtube](https://youtu.be/4Tw_ytMYHLI) |
| [4] 시각화로 이해하는 **터보퀀트*** (KV 캐시 포함) | [Youtube](https://youtu.be/ye0oQfvWhoc) |
| [5] **Speculative decoding** 설명 | [Youtube](https://youtu.be/v5al_cwvkJQ) |
| 언어 모델 개념 이해하기 ★ | [Youtube](https://youtu.be/fn2xwgvQD7c) |
| 시각화로 이해하는 Diffusion 언어 모델 | [Youtube](https://youtu.be/JV0Fix2OB4Y) |
| 최신 LLM 구조의 기본기 (Multihead Attention, **GQA**) | [Youtube](https://youtu.be/vEKhXxSlclY) |

## Visual AI (영어)

| 영상 | 링크 |
|---|---|
| Self-Attention Explained: How Transformers Actually Work | [Youtube](https://youtu.be/vkhPtpUiLd8) |
| Multi-Head Attention Explained Visually | [Youtube](https://youtu.be/42L1q1Z4Ojc) |
| Why Transformers Need Positional Encoding \| Sin & Cos | [Youtube](https://youtu.be/42y3XeOnH78) |
| How Does the Transformer Encoder Actually Work? | [Youtube](https://youtu.be/Zub3YvvUoR4) |
| Causal Attention Explained Visually | [Youtube](https://youtu.be/4qstqQH9ehY) |
| How GPT Actually Works: Transformer Decoder Explained | [Youtube](https://youtu.be/KE9fqU4EG4o) |
| **Why LLMs Waste 99% of Compute — And How KV Cache Fixes It** | [Youtube](https://youtu.be/HmWQhBjbtLE) |
| **How do LLMs shrink the KV cache by 75%? GQA vs MQA** (10분) | [Youtube](https://youtu.be/yzONjmXM8As) |
| Cross-Attention Explained: How Transformers Translate | [Youtube](https://youtu.be/NYqJoypFncY) |
| Essential Machine Learning and AI Concepts Animated | [Youtube](https://youtu.be/PcbuKRNtCUc) |

## 기타 / 실무 사례 ★ 운영 관점

| 영상 | 비고 | 링크 |
|---|---|---|
| GPT explained in 15min | | [Youtube](https://youtu.be/7gkaWaDEpHg) |
| [Paper Review] Attention is All You Need (Transformer) | 논문 리뷰 | [Youtube](https://youtu.be/x_8cp4Vdnak) |
| [Lablup Conf 5th] **NHN Cloud - HPC 구축의 모든 것** (정민) | 국내 사례 | [Youtube](https://youtu.be/PcVh0_8k_Ys) |
| [Lablup Conf 5th] **LLM 서빙토크: 싸고 빠르게 돌리는 LLM 꿀팁** (박배성) | 국내 사례 | [Youtube](https://youtu.be/O00dArdImoI) |
| [SC25] 10-day GPUaaS Rollout: CSP Deployment Use Cases | | [Youtube](https://youtu.be/WBYW8JCK6To) |
| [SC25] Case Study: K-AI HPC Implementation | | [Youtube](https://youtu.be/eWRoS-IUyvI) |
| "밑바닥부터 만들면서 배우는 LLM" (길벗, 2025) 동영상 묶음 | 도서 부록 | [Youtube](https://youtu.be/R80Gfde4cpg) |
| **End-To-End LLM DevOps Project w/ Docker, Kubernetes, vLLM** | AWS EC2 g4dn.xlarge에 vLLM 서빙 | [Youtube](https://youtu.be/cm2tZm8lGSg) · [Github](https://github.com/vishakhasadhwani/llm-deployment-demo) |
| **Ray를 활용한 GPU Util 100% MLOps**: 배치처리부터 모델 서빙까지 | 네이버TV | [Video](https://tv.naver.com/v/80335756) |
| **대규모 AI 서비스 운영을 위한 Kubernetes GPU 클러스터 도입기** | 국내 사례 | [Youtube](https://youtu.be/cUn5KjNGiuI) |
| **MLXP: Kubernetes LLM Serving 최적화 기술 도입기** | 국내 사례 | [Youtube](https://youtu.be/sgEEs5yvYGs) |
| Kubernetes에서 GPU 사용: NVIDIA에 요청할 때 실제로 무슨 일이? | | [Youtube](https://youtu.be/nu6bLhuvlWM) |
| (추천영상) **Kubernetes 기반 GPU 지원 플랫폼** | [GPU on K8s PDF](./pdfs.md) 웨비나 | [Youtube](https://youtu.be/eBbjSfxwL30) |
| 테크톡톡 2026 \| ML Engineer — LLM 서빙, 띄우는 것과 잘 띄우는 것 사이 | 국내 사례 | [Youtube](https://youtu.be/Z6JfgjIauSw) |

> 마지막 "기타/실무 사례" 블록은 **과제 소재**로 특히 쓸 만합니다 — 국내 기업의 실제 GPU 클러스터·LLM 서빙 도입기가 모여 있습니다.
