# (따라하며 확인하는) GPU 가상화: HAMi 설치 및 사용

원문: [노션 서브페이지](https://gasidaseo.notion.site/GPU-HAMi-39750aec5edf8030871ff0b3bcff0389) 🛁
공식 문서: [project-hami.io](https://project-hami.io/) · [Github](https://github.com/Project-HAMi/HAMi)

## 한 줄 요약

**HAMi**(Heterogeneous AI Computing Virtualization Middleware)는 K8s GPU 가상화 미들웨어로, **소프트웨어 수준에서 GPU 연산(Compute)과 메모리(VRAM) 격리**를 제공합니다. 하드웨어 격리인 **MIG를 지원하지 않는 GPU 카드에서도** 격리가 가능한 것이 핵심 가치입니다.

### ⚠️ 중요한 한계 (실습에서 실제로 확인된 것)

> SW 격리 특성상 **완벽한 격리가 제공되지 않습니다.** 원문 실습에서도 **GPU 연산(Compute) 제한은 거의 되지 않았습니다.**
>
> (추정 원인) 하드웨어 격리(MIG)가 아닌 **유저스페이스 격리**이므로 '상한 초과 판단 시간 + 이후 통제 실행·적용 시간'이 필요하고, 그 사이에는 대응이 어렵습니다.

메모리(VRAM) 격리는 hard limit으로 잘 동작하지만, **compute 격리는 신뢰하기 어렵다**는 것이 실습의 결론입니다.

---

## 아키텍처 — 4개 구성요소의 조합

HAMi는 **Device Plugin + Scheduler Extender + MutatingWebhook + CUDA API 후킹**을 결합해 소프트웨어 기반 vGPU를 구현합니다.

| 구성요소 | 역할 |
|---|---|
| **MutatingWebhook** | `schedulerName` 자동 교체 |
| **Scheduler Extender** | Filter/Bind 단계에서 VRAM·compute 잔여량 기반 스케줄링. 기본 K8s 스케줄러는 GPU 개수(정수)만 확인하므로, 확장을 통해 GPU의 풍부한 정보 기반으로 스케줄링 |
| **Device Plugin** | vGPU 리소스 등록, `libvgpu.so` / `ld.so.preload` 주입 |
| **HAMi-Core** (`libvgpu.so`) | 컨테이너 내부에서 CUDA/NVML 호출을 가로채 실제 VRAM·compute 사용량 제한 |

### HAMi-Core가 실제로 제한하는 방식 ★

| 자원 | 방식 |
|---|---|
| **VRAM** | `cuMemAlloc` 계열을 인터셉트해 quota 초과 시 즉시 `CUDA_ERROR_OUT_OF_MEMORY` 반환 |
| **Compute** | `cuLaunchKernel` 앞단에서 rate_limiter가 전역 카운터(`g_cur_cuda_cores`)를 소비하고, 백그라운드 watcher가 실측 사용률로 보충량을 재계산 |

## 주요 특징

| 분류 | 내용 |
|---|---|
| **Device Sharing** | 다양한 이기종 AI 컴퓨팅 장치(GPU, NPU, 기타 가속기) 호환. 여러 컨테이너가 동시에 장치 공유 |
| **Memory Management** | 컨테이너 내부 메모리 사용량 엄격 제한, 동적 할당, MB 단위 또는 전체 대비 백분율 지정 |
| **Device Specification** | 특정 유형 장치 요청, UUID로 특정 장치 타겟팅 |
| **Ease of Use** | 워크로드에 **투명하게 적용** — 컨테이너 내부 코드 변경 불필요 |

```yaml
resources:
  limits:
    nvidia.com/gpu: 1        # requesting 1 vGPU
    nvidia.com/gpumem: 3000  # 각 vGPU가 3000m 장치 메모리 사용
```

## 프로젝트 근황

| 시점 | 내용 |
|---|---|
| ’26.7.2 | HAMi, **CNCF 인큐베이팅 단계 진입** |
| ’26.6.20 | **NVIDIA KAI Scheduler에 HAMi-Core가 채택됨** |
| ’26.5.11 | HAMi **v2.9.0** 릴리스 — DRA Generally Available, Scheduler Ecosystem 확장 |

### KAI Scheduler와의 역할 분담

- **KAI 스케줄러** = "누가 어떤 GPU를 언제 사용할지" 결정 → **스케줄링 계층**
- **HAMi** = "일단 할당되면 그 이상 받을 수 없다"를 보장 → **격리 계층**

---

## 실습 목차

### 1. HAMi 설치

가이드: [hami-isolation-k3s](https://project-hami.io/tutorials/labs/hami-isolation-k3s)

**사전 준비**

| 항목 | 요구 버전 |
|---|---|
| NVIDIA drivers | >= 440 |
| nvidia-docker | > 2.0 |
| container runtime | default runtime이 `nvidia`로 설정 (containerd/docker/cri-o) |
| Kubernetes | >= 1.18 |
| kernel | >= 3.10 |
| helm | > 3.0 |

- HAMi 스케줄러가 관리할 수 있게 **GPU 노드에 레이블 지정**
- Helm으로 HAMi 설치 → `/usr/local/vgpu/libvgpu.so`
- HAMi WebUI 설치 (Helm)
- (옵션) HAMi device plugin 메트릭용 Grafana 대시보드 설정

> 전제 환경: [PC에 GPU 설정 및 사용 by Docker/K8S](./gpu-setup-docker-k8s.md)

### 2. GPU Partitioning with HAMi

가이드: [gpu-partitioning](https://project-hami.io/tutorials/labs/gpu-partitioning)

| Step | 내용 |
|---|---|
| 1 | HAMi 리소스 유형 이해하기 |
| 2 | **Two Pods Sharing One GPU** — MIG 미지원 GPU에서 하나의 GPU를 공유하는 두 Pod 배포 |
| 3 | **The VRAM Ceiling** — 상한 제한 |
| 4 | **OOM 테스트로 메모리 격리 증명** — vGPU 메모리 hard limit 동작 확인 ✅ |
| 5 | **`gpucores`로 Compute 제한** — SM 30% 할당 설정 → **실제 거의 100% 사용됨. HW 제한이 아닌 SW 제한의 한계 확인** ⚠️ |

### 3. Run vLLM on HAMi GPU 할당

가이드: [hami-vllm](https://project-hami.io/tutorials/labs/hami-vllm)

**모델 선정이 실습의 핵심 포인트**:

| 항목 | 내용 |
|---|---|
| 공식 튜토리얼 | A10(24GB)에서 Qwen2.5-7B-Instruct(BF16, 가중치만 14~16GiB)를 22GB gpumem으로 서빙 |
| 문제 | 16GB 카드에 그대로 적용하면 **가중치만으로 카드를 거의 다 채워** KV 캐시/컨텍스트 여유가 없어 실패 위험 |
| **권장** | **Qwen/Qwen2.5-7B-Instruct-AWQ (4bit 양자화)** — 가중치 약 5.5GB → gpumem 14000MiB로 잡아도 KV 캐시/컨텍스트에 **약 8GB+ 여유** 확보. 같은 모델 패밀리라 튜토리얼과 동일 스펙 비교 가능 |

- Deploy vLLM with HAMi Resources
- Test Inference: NodePort **30003** 사용

> 이 "가중치 + KV 캐시 예산 계산" 자체가 교재 CH5(KV cache 사이징)의 실제 사례입니다.

### 4. Volcano vGPU with Gang Scheduling and Queues

가이드: [volcano-vgpu-gang-queue](https://project-hami.io/tutorials/labs/volcano-vgpu-gang-queue)

**목표**: Volcano Scheduler(gang scheduling + queue 단위 리소스 제한) + HAMi-core 기반 vGPU를 결합해 검증

- 컨테이너에 HAMi-core memory/compute limit이 주입되는지
- `minAvailable` 기반 Gang이 **partial start를 막는지**
- Queue capability가 node capacity와 **별개로** vGPU 사용량을 제한하는지

| Step | 내용 |
|---|---|
| 0 | Volcano 1.15.0 설치 |
| 1 | Baseline 기록 (K8s, GPU driver, Volcano 상태) |
| 2 | Volcano vGPU Scheduling 활성화 |
| 3 | Volcano vGPU Device Plugin 설치 (내부적으로 **HAMi-core 엔진 사용**) |
| 4 | Single vGPU Pod 검증 |
| 5 | Two-Worker Gang 실행 |
| 6 | Gang Scheduling이 Partial Start를 막는지 검증 |
| 7 | Queue-Level vGPU Limit 검증 |

### 5. 작성 예정 항목

| 주제 | 상태 | 링크 |
|---|---|---|
| HAMi Resource Isolation + KAI Scheduler | 정리 예정 | [HAMi Blog](https://project-hami.io/blog/hami-core-adopted-by-nvidia-kai-scheduler) · [KAI docs](https://github.com/kai-scheduler/KAI-Scheduler/blob/main/docs/gpu-sharing/hami/README.md) · [hami-dra](https://project-hami.io/tutorials/labs/hami-dra) |
| Kueue + HAMi vGPU | 추가 작성 예정 | [kueue-hami-vgpu](https://project-hami.io/tutorials/labs/kueue-hami-vgpu) |
| GPU Topology-Aware Scheduling on Fake GPUs | 추가 작성 예정 | [topology-aware-scheduling](https://project-hami.io/tutorials/labs/topology-aware-scheduling) |

---

## 스터디 연결

- [GPU-Enabled Platforms on Kubernetes PDF](../references/pdfs.md) **CH4 — HAMi: The Software Enforcement Revolution** (Compute Throttling, 토큰 버킷)과 정확히 대응합니다. 이론은 PDF, 실습은 이 문서.
- [toss의 MIG 도입기](https://toss.tech/article/toss-securities-gpu-mig)와 비교하면 **HW 격리(MIG) vs SW 격리(HAMi)** 트레이드오프가 잘 드러납니다.
- [AI Factory Operations Lab](./ai-factory-ops-lab.md) Lesson 1C에서도 HAMi를 다룹니다 (fake GPU 환경).
