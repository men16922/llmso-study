# 도서 레퍼런스

## 주교재 — Hands-On LLM Serving and Optimization

| 항목 | 내용 |
|---|---|
| 저자 | Chi Wang, Peiheng Hu |
| 출판 | O'Reilly Media, 2026.4 |
| 분량 | 374p |
| 공식 사이트 | https://orca3.github.io/llm-model-inference/ |
| 예제 코드 | https://github.com/orca3/llm-model-inference |
| 스터디 범위 | 1~5주차 (CH1 ~ CH10) |

> 구매 필수는 아닙니다.

### 목차 (스터디 주차 매핑)

| 주차 | CH | 제목 | 다루는 내용 |
|---|---|---|---|
| **1주** | 1 | Introduction to Model Serving and Optimization | 모델 해부·라이프사이클, 서빙 개념, 서빙 패러다임(엣지/단일 모델/멀티 모델), 플랫폼 |
| **1주** | 2 | Large Language Model Serving | 트랜스포머 구조, 자기회귀 생성, 디코더 온리, 어텐션, **KV cache**, **prefill/decode**, vLLM 사용법 |
| **2주** | 3 | Model-Serving System Design: A Deep Dive | 단일/멀티 모델 서비스 구축, **배칭**, 스트리밍, NVIDIA Triton, 비용·지연 최적화 |
| **2주** | 4 | Model Serving Best Practices | 에이전틱 시스템, **RAG**, 엔터프라이즈 아키텍처, 오픈소스 vs 클라우드, 성능 측정 |
| **3주** | 5 | Challenges When Serving LLMs | 최적화의 중요성, 가속기 사양, **모델 로딩 병목**, KV cache 사이징, prefill/decode 분석 |
| **3주** | 6 | Essential LLM Optimization Techniques | 배칭 전략, 어텐션 스케일링, **커널 퓨전**, 모델 압축, **prefix caching** |
| **4주** | 7 | Advanced LLM Optimization Techniques | **Speculative decoding**, 분산 추론, **prefill-decode disaggregation**, long-context KV 캐싱 |
| **4주** | 8 | LLM Serving Frameworks | **vLLM 내부 구조**, TensorRT-LLM, SGLang, llama.cpp, 프레임워크 선택 기준 |
| **5주** | 9 | LLM Optimization in Practice | **Qwen3-14B** 단계별 최적화 실습, 하드웨어 점검, 양자화 |
| **5주** | 10 | Advancements in LLM Serving | 시맨틱 캐싱, 프로파일링, 멀티모달 서빙, 엣지 AI, **multi-LoRA 서빙**, 강화학습 활용 |

### 흐름

```
CH1~2  개념 정립     서빙이란 무엇인가 + LLM은 왜 다른가 (KV cache / prefill·decode)
CH3~4  시스템 설계   배칭·스트리밍·Triton → RAG/에이전틱까지 확장한 아키텍처
CH5~6  병목과 기본기  무엇이 느린가 → 배칭·커널퓨전·압축·prefix cache로 해결
CH7~8  심화와 도구   speculative·분산·PD 분리 → vLLM/TRT-LLM/SGLang 비교
CH9~10 현장 적용     Qwen3-14B 실전 최적화 → 멀티모달·multi-LoRA 등 최신 방향
```

---

## 추가 참고 도서

### 밑바닥부터 만들면서 배우는 LLM

| 항목 | 내용 |
|---|---|
| 출간 | 2025.9 (한국어판) |
| 원서 | *Build a Large Language Model (From Scratch)* — Sebastian Raschka, Manning |
| 링크 | [교보문고](https://product.kyobobook.co.kr/detail/S000217570241) · [Youtube](https://youtu.be/R80Gfde4cpg) · [원서](https://www.manning.com/books/build-a-large-language-model-from-scratch) |
| 언제 유용한가 | 트랜스포머 내부를 코드로 직접 만들어 보고 싶을 때. 교재 CH2(LLM 서빙)의 배경 지식을 바닥부터 채워줌 |

### AI Systems Performance Engineering

| 항목 | 내용 |
|---|---|
| 출간 | 2025.12 |
| 링크 | [Amazon](https://www.amazon.com/Systems-Performance-Engineering-Optimizing-Inference/dp/B0F47689K8) · [Github](https://github.com/cfregly/ai-performance-engineering) |
| 언제 유용한가 | 3~4주차(CH5~8) 성능 최적화 심화. 프로파일링·병목 분석 관점 |

### CUDA for Deep Learning

| 항목 | 내용 |
|---|---|
| 상태 | MEAP (2026.10 출간 예정) |
| 링크 | [Manning](https://www.manning.com/books/cuda-for-deep-learning) |
| 언제 유용한가 | 커널 퓨전·CUDA 레벨 최적화(CH6)를 더 파고들 때 |
