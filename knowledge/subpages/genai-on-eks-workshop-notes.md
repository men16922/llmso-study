# [Old] Generative AI on Amazon EKS 워크숍 실습 정리

원문: [노션 서브페이지](https://gasidaseo.notion.site/Old-Generative-AI-on-Amazon-EKS-35950aec5edf805ab1b6d078fd652236) 🏷️
워크숍: [catalog.workshops.aws/genai-on-eks](https://catalog.workshops.aws/genai-on-eks/ko-KR) (한국어 버전도 있음)
참고 후기: [AEWS 4기 9주차 실습 정리](https://infralogbook.tistory.com/23)

> **"[Old]"** 는 이전 회차(AEWS 4기) 기준 정리라는 뜻입니다. **6주차(2026-09-06) 실습의 예습 자료**로 쓰기 좋습니다. 워크숍 내용은 개정될 수 있습니다.

## 한 줄 요약

Amazon EKS 위에서 **프로덕션 수준의 LLM 워크로드를 배포·관리**하는 워크숍. GPU 노드를 세세히 관리하는 대신 **EKS Auto Mode**가 필요 시 GPU 노드를 프로비저닝하고, **vLLM과 Ray**로 추론 워크로드를 실행하는 흐름입니다.

사용 모델: **Ministral-3-8B-Instruct-2512** (S3에 준비)

## 전체 구성

```
실습 환경 배포 (Self-paced)   Quota 증설 → ODCR → Terraform
        ↓
소개 Introduction              EKS Auto Mode + GPU 노드 프로비저닝, SOCI Snapshotter
        ↓
추론 Inference                 vLLM 모델 로딩 → LLM 추론 모니터링 (AMP/Grafana)
        ↓
고급 Advanced                  Ray로 추론 스케일링 → Strands Agents (Agentic AI)
        ↓
리소스 제거
```

---

## 1. 실습 환경 배포 (Self-paced)

| 단계 | 내용 |
|---|---|
| **EC2 Service Quota 증설** | `On-Demand G and VT instances` — 계정에 미리 신청 필요 |
| **ODCR 생성** | GPU 인스턴스용 **On-Demand Capacity Reservation** — 실습 시점에 용량을 확보해 두는 것 |
| **Terraform 배포** | VPC, EKS Auto Mode 클러스터, S3, Amazon Managed Prometheus, Grafana |

> ⚠️ Quota 증설은 승인에 시간이 걸리므로 **6주차 전에 미리** 신청하세요. ODCR은 예약 시점부터 과금되니 실습 직전에 생성하고 끝나면 반드시 해제.

## 2. 소개 (Introduction)

Amazon EKS에서 생성형 AI 워크로드 실행에 필요한 구성이 올바른지 확인하는 섹션입니다.

| 확인 항목 | 내용 |
|---|---|
| 워크숍 인프라 | VPC + EKS Auto Mode 클러스터 사전 구성 확인 |
| 기본 클러스터 구성 | EKS Auto Mode 노드 풀(시스템, 범용) |
| 핵심 구성 요소 | **Bottlerocket 최적화 기능이 내장된 NVIDIA 장치 플러그인**과 GPU 노드 풀 |
| 관측 | Managed Prometheus + Self-Managed Add-ons (kube-prometheus-stack, grafana operator) |
| EKS Add-ons | 필수 Add-on을 AWS 측에서 관리 |
| **LLM Model Download Job** | Ministral-3-8B-Instruct-2512를 S3 버킷에 다운로드하는 Job 리소스 |

### LLM 추론을 위한 GPU 인프라 최적화

- **EKS Auto Mode GPU Node Provisioning** — Auto Mode를 사용한 고성능 LLM 추론용 GPU 인프라 최적화
- **EKS Auto Mode는 GPU 인스턴스의 경우 NVIDIA Device Plugin이 내장**되어 있음 (별도 설치 불필요)
- **SOCI Snapshotter** — 컨테이너 이미지 지연 로딩으로 대용량 추론 이미지의 기동 시간 단축

> Device Plugin을 직접 설치하는 [PC GPU 실습](./gpu-setup-docker-k8s.md)과 대조하면, 관리형 서비스가 무엇을 대신해 주는지 명확해집니다.

## 3. 추론 (Inference on Amazon EKS)

- **vLLM 모델 로딩**
- **LLM 추론 워크로드 모니터링** — AWS 관리형 Prometheus(AMP) + Grafana

## 4. 고급 (Advanced AI on Amazon EKS)

### 4-1. vLLM 및 Ray를 사용한 LLM 추론 스케일링 ★

vLLM과 분산 컴퓨팅 프레임워크 **Ray**를 결합한 고급 확장 기법. 여러 추론 요청을 효율적으로 처리하고 분산 워크로드를 모니터링합니다.

| 단계 | 내용 |
|---|---|
| 아키텍처 | 확장 가능한 LLM inference 관련 아키텍처 확인 |
| S3 CSI Driver | Add-on 확인 (S3의 모델을 파드에 마운트) |
| ConfigMap | vLLM 서빙 동작을 위한 **vLLM Serving Script ConfigMap** 작성 |
| **RayService** | RayService with vLLM on EKS |
| Ray 대시보드 | Ray Dashboard 확인 |
| Open WebUI | Chat with Mistral by Open WebUI Application |
| 모니터링 | Ray Monitoring Grafana 대시보드 |

참고: [Ray Serve 공식 문서](https://docs.ray.io/en/latest/serve/index.html)

### 4-2. Strands Agents (Agentic AI)

**Strands Agents SDK**로 EKS에 지능형 에이전트를 배포. LLM이 과거 상호작용을 기억하고, 의사 결정을 내리고, **시간·날씨 서비스 같은 도구**를 사용해 위치 기반 쿼리에 응답하도록 구성합니다.

| 단계 | 내용 |
|---|---|
| SDK 기초 | Strands Agents SDK — AI Agent를 더 쉽게 만들기 위한 오픈소스 agent harness SDK |
| Building the agent | 에이전트 생성 |
| Agent in action | 에이전트 테스트 |

> 교재 **CH4(Model Serving Best Practices)** 의 에이전틱 시스템·RAG 파트와 대응합니다.

## 5. 실습 환경 제거

섹션 실습 완료 후 리소스 삭제 → 전체 환경 제거 단계 수행.

> 💸 **GPU 노드 + ODCR + NAT Gateway + LoadBalancer + AMP**가 모두 과금 대상입니다. 반드시 끝까지 정리하세요.

---

## 스터디 연결

- **6주차(09-06)** 본 실습의 예습 자료
- [workshops-and-docs.md](../references/workshops-and-docs.md) — 현재 회차 워크숍 정보
- [GPU-Enabled Platforms on Kubernetes PDF](../references/pdfs.md) — K8s GPU 동작 원리 배경
- 관련 영상: [Ray를 활용한 GPU Util 100% MLOps](https://tv.naver.com/v/80335756) ([videos.md](../references/videos.md))
