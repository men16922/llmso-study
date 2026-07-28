# 00. 스터디 개요 및 커리큘럼

## 목적

LLM 서비스 제공(서빙) 및 최적화에 대한 지식 **학습 + 실습 따라해보기**.

## 운영 방식

| 항목 | 내용 |
|---|---|
| 모임장 | 서종호 (gasida) — Cisco CCIEx3 + 조력자들 · [LinkedIn](https://www.linkedin.com/in/gasida99/) |
| 형태 | 온라인 강의 형태, 2시간 진행 (분량에 따라 30분 추가 가능) |
| 일시 | 매주 일요일 저녁 20:30 ~ 22:30 (+α) |
| 기간 | 2026-08-02 ~ 2026-09-13, **총 7주** |
| 결석 시 | 불가피한 사정으로 참석 못할 경우 **녹화 영상**으로 대체 시청 |
| 주최 | CloudNet@ |

> 일정과 내용은 일부 수정될 수 있음.

## 주차별 커리큘럼

노션의 주차 표기(CH 번호)에 **교재 실제 챕터 제목**을 매핑한 표입니다.

| 주차 | 날짜 (일) | 노션 표기 | 교재 실제 챕터 | 핵심 키워드 |
|---|---|---|---|---|
| 1주차 | 08-02 | CH1, CH2 — 모델 서빙/최적화 소개 | Introduction to Model Serving and Optimization / Large Language Model Serving | 서빙 패러다임, 트랜스포머, **KV cache**, **prefill·decode**, vLLM |
| 2주차 | 08-09 | CH3, CH4 — 서빙 시스템 설계/모범 사례 | Model-Serving System Design / Model Serving Best Practices | **배칭**, 스트리밍, Triton, RAG, 에이전틱, 성능 측정 |
| 3주차 | 08-16 | CH5, CH6 — 핵심 과제, 필수 최적화 | Challenges When Serving LLMs / Essential LLM Optimization Techniques | 모델 로딩 병목, KV cache 사이징, **커널 퓨전**, **prefix caching** |
| 4주차 | 08-23 | CH7, CH8 — 고급 최적화, 서빙 프레임워크 | Advanced LLM Optimization Techniques / LLM Serving Frameworks | **speculative decoding**, 분산 추론, **PD disaggregation**, vLLM 내부, TensorRT-LLM, SGLang |
| 5주차 | 08-30 | CH9, CH10 — 실제 적용, 새로운 방향 | LLM Optimization in Practice / Advancements in LLM Serving | **Qwen3-14B 최적화 실습**, 양자화, 시맨틱 캐싱, 멀티모달, **multi-LoRA** |
| 6주차 | 09-06 | [AWS Workshop] Generative AI on Amazon EKS | — | EKS Auto Mode, Terraform, Prometheus/Grafana, GPU 노드 |
| 7주차 | 09-13 | llm-d | — | K8s 네이티브 분산 추론, Well-Lit Paths |

챕터별 상세 목차는 [references/books.md](./references/books.md) 참조.

### 챕터 흐름 한눈에 보기

```
CH1~2   개념 정립      서빙이란 무엇인가 + LLM은 왜 다른가 (KV cache / prefill·decode)
CH3~4   시스템 설계    배칭·스트리밍·Triton → RAG/에이전틱까지 확장한 아키텍처
CH5~6   병목과 기본기  무엇이 느린가 → 배칭·커널퓨전·압축·prefix cache로 해결
CH7~8   심화와 도구    speculative·분산·PD 분리 → vLLM/TRT-LLM/SGLang 비교
CH9~10  현장 적용      Qwen3-14B 실전 최적화 → 멀티모달·multi-LoRA 등 최신 방향
──────────────────────────────────────────────────────────────
6주차   AWS EKS 위에서 GenAI 서빙 실습   ─ 쿠버네티스 기반 운영
7주차   llm-d — 분산 LLM 추론 스택       ─ 최신 오픈소스
```

## 관련 문서

- 실습 환경 준비 → [01-environment-setup.md](./01-environment-setup.md)
- 과제 규정 → [02-assignments.md](./02-assignments.md)
- 저작권 정책 · 슬랙/ZOOM 준비 · 질문하는 법 → [03-study-rules.md](./03-study-rules.md)
- 서브페이지 실습 가이드 정리 → [subpages/](./subpages/)
- **모든 자료·링크·PDF** → [references/](./references/)
