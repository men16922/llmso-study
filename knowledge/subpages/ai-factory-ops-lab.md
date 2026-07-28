# AI Factory Operations Lab

원문: [노션 서브페이지](https://gasidaseo.notion.site/AI-Factory-Operations-Lab-39850aec5edf804c9baced1427bf5490) 📡 (**정리 중**)
실습 가이드 출처: [ld-singh.github.io/ai-factory-ops-lab](https://ld-singh.github.io/ai-factory-ops-lab/)

## 한 줄 요약

**가짜 GPU(fake-gpu-operator)와 kind 클러스터**로 실제 GPU 없이 GPU 플랫폼 운영을 실습하는 레슨 모음. 스케줄링 → 공유 → 관측 → 추론 서빙 순으로 이어집니다.

> 실물 GPU 없이 스케줄링·큐·관측 실습이 가능한 것이 큰 장점입니다. Lesson 4(추론 서빙)만 실제 GPU 또는 CPU 모델이 필요합니다.

## 레슨 구성

| Lesson | 주제 | 상태 |
|---|---|---|
| 1 | Kubernetes GPU Scheduling | ✅ |
| 1B | Queue-Based GPU Scheduling with **KAI Scheduler** | ✅ |
| 1C | GPU Sharing & Fractional GPUs with **HAMi** | ✅ |
| 2 | Slurm GPU Workload Management | 작성 예정 |
| 3 | **GPU Observability** | ✅ |
| 4 | **Inference Serving** | ✅ |
| 5 | BCM-Style Cluster Lifecycle (Conceptual) | 작성 예정 |
| 6 | Real GPU (the one-rental capstone) | 작성 예정 |

---

## Lesson 1 — Kubernetes GPU Scheduling

| Step | 내용 |
|---|---|
| 1 | Stand Up the Simulated Fleet — 시뮬레이션 GPU 플릿 구성 |
| 2 | Deploy the Four Scenarios — `gpu-demo` 네임스페이스에 4가지 workload 배포 |
| 3 | **Triage Like Production** — Pending pod 분석 (3가지 케이스) |

## Lesson 1B — Queue-Based GPU Scheduling with KAI Scheduler

| 단계 | 내용 |
|---|---|
| 설치 | KAI Scheduler 설치, namespace + **queue hierarchy** 생성 |
| Exercise A | **Quota enforcement** (validated) |
| Exercise B | **Borrowing Idle Capacity** — `team-prod`가 idle GPU를 borrow해 quota 이상 배포 시도 → 상한 제한 기능 확인 |
| Exercise C | **Reclaim** |
| Exercise D | **Gang Scheduling** — all-or-none 동작 재현 (podgroup 추가) |
| Exercise E | **Priority** — 높은 우선순위에 쫓기면서 gang의 all-or-none 원자성 + 능동적(active) preemption 동작 확인 |

## Lesson 1C — GPU Sharing & Fractional GPUs with HAMi

환경: **kind k8s + fake-gpu-operator + HAMi** (노드 등록)

| Exercise | 내용 |
|---|---|
| 1 | **a fractional request is placed** — 1개 GPU를 더 작게 나눠서 할당 |
| 2 | **an over-request stays Pending** — 단일 GPU VRAM보다 큰 VRAM 요청 파드 배포 시도 |
| 3 | **the placement decision** — 배치 결정(점수) 확인 |

> 실제 HAMi 실습은 [HAMi 서브페이지](./hami-gpu-virtualization.md) 참조. 이쪽은 fake GPU 기반이라 부담 없이 스케줄링 동작만 확인할 수 있습니다.

## Lesson 3 — GPU Observability

| Step | 내용 |
|---|---|
| 0 | kind 클러스터 + **가짜 GPU fleet** 생성 |
| 1 | 모니터링 스택 설치 — `kube-prometheus-stack` + **fake DCGM exporter** + ServiceMonitor + **알림규칙 6개** + **Grafana 대시보드 2개** |
| 2 | synthetic(가짜) exporter 이해 |
| 3 | Prometheus / Grafana 열기 |
| 4 | **Break it on purpose** — 장애 주입 후 Alert 확인 |

GPU 관련 Metrics 정리 포함.

## Lesson 4 — Inference Serving ★ 스터디 주제와 가장 직결

**Docker(Ollama)만 있으면 되는 독립 실습**

실습 환경: NVIDIA **RTX 4070 Ti (VRAM 16GB)**, 모델 **Qwen2.5-3B-Instruct**

| Step | 내용 |
|---|---|
| Setup | serve the CPU model |
| 1 | **Baseline Trade-off** — 동시성 1→10→100→1000 스윕, **tok/s vs ttft_p95 / goodput%** 트레이드오프 관찰 |
| 2 | **In-flight Load Steals Latency** — 짧은 요청 단독 실행 vs 긴 요청 8개가 도는 중 실행, **TTFT 경합** 관찰 |
| 3 | **Separate Prefill from Decode** — 입력 길이 vs 출력 길이가 TTFT/e2e에 미치는 영향 분리 |
| 4 | **overload 케이스** — concurrency를 올려 서버가 못 버티는 지점(**goodput 붕괴**) 찾기 |
| 5 | **Turn it into a capacity plan** — 용량 산정으로 전환 |

CPU 모델 버전은 동시성 1→2→4→8로 축소해 동일 실험을 반복합니다.

> **왜 중요한가**: 교재 CH5(핵심 과제)와 CH3(배칭)에서 다루는 **prefill/decode 분리**, **TTFT vs 처리량 트레이드오프**, **goodput** 개념을 직접 측정으로 체감할 수 있는 실습입니다. GPU 한 장 또는 CPU만으로도 가능합니다.

---

## 스터디 연결

- Lesson 1·1B → [GPU-Enabled Platforms on Kubernetes PDF](../references/pdfs.md) CH3(Orchestrating GPU Sharing, KAI-Scheduler)
- Lesson 1C → [HAMi 서브페이지](./hami-gpu-virtualization.md)
- Lesson 3 → [PC GPU 설정 실습](./gpu-setup-docker-k8s.md) 6단계(DCGM Exporter), PDF CH5(Monitoring)
- Lesson 4 → 교재 CH3·CH5 / [Inference Engineering PDF](../references/pdfs.md) CH1.4(Measuring Latency and Throughput)
