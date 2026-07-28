# 노션 서브페이지 정리

메인 노션 페이지에 링크된 **서브페이지 내용을 직접 열어 정리**한 문서들입니다.

> ⚠️ 원문 노션은 **멤버 전용**이며, 스터디 규칙상 **외부 공개·전파 금지**입니다. 이 폴더는 개인 학습용 정리입니다. ([03-study-rules.md](../03-study-rules.md) 참조)

## 정리 완료

| 문서 | 원문 | 한 줄 |
|---|---|---|
| [gpu-setup-docker-k8s.md](./gpu-setup-docker-k8s.md) | 🛣️ [노션](https://gasidaseo.notion.site/PC-GPU-by-Docker-K8S-39750aec5edf806d8070d580fac38917) | 로컬 PC → 컨테이너 → K8s 단계별 GPU 인식/실행 실습. **OCI 훅·Device Plugin 내부 동작**까지 |
| [gpu-interconnect-bandwidth.md](./gpu-interconnect-bandwidth.md) | [노션](https://gasidaseo.notion.site/GPU-Network-1-GPU-Interconnect-Bandwidth-38750aec5edf80428383e33957b728cf) | 메모리 대역폭 병목(**메모리 장벽 4.7배**)과 NVLink/NVSwitch/PCIe 토폴로지 |
| [hami-gpu-virtualization.md](./hami-gpu-virtualization.md) | 🛁 [노션](https://gasidaseo.notion.site/GPU-HAMi-39750aec5edf8030871ff0b3bcff0389) | SW 기반 GPU 가상화. **VRAM 격리는 되지만 compute 격리는 안 됐다**는 실습 결론 |
| [nccl-communication.md](./nccl-communication.md) | [노션](https://app.notion.com/p/gasidaseo/NCCL-GPU-Cluster-Communication-Model-3aa50aec5edf807c89b1d273875d1f07) | 분산 학습의 **Ring AllReduce(ReduceScatter + AllGather)** 단계별 추적 |
| [nvidia-ai-infrastructure.md](./nvidia-ai-infrastructure.md) | 🚒 [노션](https://app.notion.com/p/gasidaseo/NVIDIA-AI-Infrastructure-3a450aec5edf802eadaff3b99cffc9fa) | NVIDIA AI 인프라 **6계층 스택 지도** |
| [ai-factory-ops-lab.md](./ai-factory-ops-lab.md) | 📡 [노션](https://gasidaseo.notion.site/AI-Factory-Operations-Lab-39850aec5edf804c9baced1427bf5490) | **가짜 GPU로 하는** 스케줄링·큐·관측·추론 서빙 실습 (정리 중) |
| [genai-on-eks-workshop-notes.md](./genai-on-eks-workshop-notes.md) | 🏷️ [노션](https://gasidaseo.notion.site/Old-Generative-AI-on-Amazon-EKS-35950aec5edf805ab1b6d078fd652236) | **6주차 예습** — EKS Auto Mode + vLLM + Ray + Strands Agents |
| [aws-interconnect.md](./aws-interconnect.md) | [노션](https://app.notion.com/p/gasidaseo/AWS-AWS-3aa50aec5edf8018aef9c4db2b0e05cd) | AWS **EFA/SRD/ENI** — 클라우드에서의 인터커넥트 |

## 링크만 (별도 정리 불필요)

| 페이지 | 사유 |
|---|---|
| [(참고) 그림으로 배우는 생성형 AI](https://app.notion.com/p/gasidaseo/AI-3aa50aec5edf80db917dd1316f3a71a7) | 도서 요약 페이지(6장). 생성형 AI 일반 개론이라 서빙 커리큘럼과 직접 관련은 낮음 → [아래 목차](#참고-그림으로-배우는-생성형-ai) |
| [Transformer Explainer](https://poloclub.github.io/transformer-explainer/) | 외부 인터랙티브 도구 → [workshops-and-docs.md](../references/workshops-and-docs.md) |
| 1주차 스터디 노션 | **작성 후 공개 예정** (2026-08-02 이후) |
| 과제 제출표 | **작성 예정** → [02-assignments.md](../02-assignments.md) |

### (참고) 그림으로 배우는 생성형 AI

도서 요약 페이지의 목차:

```
Chapter 1. 생성형 AI, 세상 모든 곳에 한꺼번에 나타나다
Chapter 2. 생성형 AI의 활용
Chapter 3. 생성형 AI 활용 사례
Chapter 4. 에이전트형 시스템 구축
Chapter 5. 생성형 AI 애플리케이션의 아키텍처
Chapter 6. 책임 있는 생성형 AI 애플리케이션 구축
```

생성형 AI 자체가 처음이라면 CH1~2를, 교재 CH4(에이전틱·RAG)를 보강하려면 CH4~5를 참고하세요.

---

## 주제 지도

```
GPU 단일 노드      gpu-setup-docker-k8s  ·  hami-gpu-virtualization
      ↓
GPU 인터커넥트      gpu-interconnect-bandwidth  ·  nccl-communication  ·  aws-interconnect
      ↓
스택 전체 조망      nvidia-ai-infrastructure
      ↓
플랫폼 운영         ai-factory-ops-lab
      ↓
클라우드 실습       genai-on-eks-workshop-notes  →  6주차
```

## 읽는 순서 추천

1. **[gpu-setup-docker-k8s](./gpu-setup-docker-k8s.md)** — GPU가 컨테이너/K8s에 어떻게 노출되는지 (기초)
2. **[gpu-interconnect-bandwidth](./gpu-interconnect-bandwidth.md)** — 왜 메모리·인터커넥트가 병목인지 (교재 CH5의 배경)
3. **[ai-factory-ops-lab](./ai-factory-ops-lab.md) Lesson 4** — TTFT/goodput을 직접 측정 (교재 CH3·CH5 체감)
4. **[genai-on-eks-workshop-notes](./genai-on-eks-workshop-notes.md)** — 6주차 직전에
5. 나머지는 필요할 때 참조
