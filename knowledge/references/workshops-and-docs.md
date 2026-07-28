# 워크숍 · 공식 문서 · 도구

## 6주차 — [AWS Workshop] Generative AI on Amazon EKS

| 항목 | 내용 |
|---|---|
| 워크숍 | https://catalog.workshops.aws/genai-on-eks/en-US |
| 코드 | https://github.com/aws-samples/sample-genai-on-eks |
| 권장 인스턴스 | [g6e.2xlarge](https://instances.vantage.sh/aws/ec2/g6e.2xlarge) — NVIDIA L40S 48GB, 8 vCPU, 64GB RAM |
| 일정 | 2026-09-06 (일) |

### 제공되는 것

- **Terraform** — EKS Auto Mode 클러스터, VPC, 모델 저장용 S3, Amazon Managed Prometheus, Grafana 대시보드, IAM 역할
- **Manifests** — 추론 워크로드용 Kubernetes 매니페스트

### 사전 준비

| 항목 | 비고 |
|---|---|
| AWS CLI v2+ | |
| Terraform v1.3+ | |
| kubectl | |
| **GPU 인스턴스 쿼터** | 계정에 미리 신청 필요 — 승인에 시간이 걸릴 수 있음 |
| 권장 배경 지식 | ML 프레임워크 기초, 쿠버네티스 기초, Python |

> 배포 상세는 저장소의 `terraform/README.md` 참조.

### 주의

Terraform으로 EKS 클러스터 + GPU 노드 + Managed Prometheus까지 올라갑니다. 실습 후 `terraform destroy`로 **반드시 정리**하세요. 정리하지 않으면 GPU 노드·NAT Gateway·LoadBalancer·EBS 비용이 계속 발생합니다.

관련 배경 자료: [pdfs.md](./pdfs.md) → "2. GPU-Enabled Platforms on Kubernetes V2" (커널 수준부터 본 K8s GPU 동작 원리, 202p)

---

## 7주차 — llm-d

| 항목 | 내용 |
|---|---|
| 공식 문서 | https://llm-d.ai/docs |
| 일정 | 2026-09-13 (일) |

**llm-d**는 쿠버네티스용 **오픈소스 추론 서빙 스택**입니다. 단일 노드 엔진을 클러스터 규모 시스템으로 확장하는 것이 목표입니다.

### 특징

- **엔진 비종속** — vLLM, SGLang 등 여러 모델 서버 지원 (하나에 락인되지 않음)
- **하드웨어 유연성** — NVIDIA, AMD, 커스텀 가속기
- **Well-Lit Paths** — 검증된 배포 레시피 (Helm 차트, Kustomize 매니페스트, 튜닝 파라미터, 모니터링 구성)
- **고급 워크로드** — 에이전틱 파이프라인, 멀티모달, 배치 처리, 고처리량 서빙

### 문서 구성

1. **Getting Started** — 퀵스타트, 가속기 지원 현황
2. **Well-Lit Paths** — Foundations(최적화, 라우팅, 캐싱, 스케일링) / Workloads(에이전틱, 멀티모달, 배치)
3. **Concepts & Architecture**
4. **Operations & Monitoring**
5. **Infrastructure & Environments**
6. **API References**

### 배경

Red Hat, Google Cloud, IBM Research, CoreWeave, NVIDIA가 참여하는 **CNCF Sandbox** 프로젝트.

> 교재 CH7의 **prefill-decode disaggregation**, CH8의 **vLLM 내부 구조**를 읽고 오면 llm-d의 설계 의도가 훨씬 잘 보입니다.

---

## 인터랙티브 학습 도구

### Transformer Explainer

| 항목 | 내용 |
|---|---|
| 사이트 | https://poloclub.github.io/transformer-explainer/ |
| 한국어 해설 | https://junhan-ai.tistory.com/590 |

GPT-2를 브라우저에서 직접 돌리며 토큰이 임베딩 → 어텐션 → 출력 확률로 흘러가는 과정을 시각적으로 따라갈 수 있습니다. 1주차 CH2(LLM 서빙) 전에 5분만 만져봐도 어텐션 개념이 잡힙니다.

### Attention Is All You Need

원논문: [arXiv:1706.03762](https://arxiv.org/abs/1706.03762)

---

## 실습 환경

| 자료 | 링크 |
|---|---|
| Google Colab (무료 GPU) | https://developers.google.com/colab |
| g6e.2xlarge 사양·요금 | https://instances.vantage.sh/aws/ec2/g6e.2xlarge |

---

## 코드 저장소 모음

| 저장소 | 용도 |
|---|---|
| [orca3/llm-model-inference](https://github.com/orca3/llm-model-inference) | **주교재 예제 코드** |
| [aws-samples/sample-genai-on-eks](https://github.com/aws-samples/sample-genai-on-eks) | 6주차 AWS 워크숍 Terraform/매니페스트 |
| [elizabetht/100-days-of-inference](https://github.com/elizabetht/100-days-of-inference) | Inference Engineering 실습 부록 |
| [cfregly/ai-performance-engineering](https://github.com/cfregly/ai-performance-engineering) | AI Systems Performance Engineering 예제 |
