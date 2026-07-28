# (따라하며 확인하는) PC에 GPU 설정 및 사용 by Docker / K8S

원문: [노션 서브페이지](https://gasidaseo.notion.site/PC-GPU-by-Docker-K8S-39750aec5edf806d8070d580fac38917) 🛣️
참고 문서: [`references/pdfs.md`](../references/pdfs.md) → GPU-Enabled Platforms on Kubernetes

## 한 줄 요약

**로컬 PC → 컨테이너 → 쿠버네티스** 단계별로 GPU 인식·실행을 확인하는 실습 가이드. 단순 설치 절차가 아니라 **GPU가 OS·컨테이너·K8s 안에서 어떤 경로로 노출되는지 구조**를 설명합니다.

```
로컬 PC          드라이버 로우레벨 (디바이스 노드, 커널 모듈, DKMS)
   ↓
컨테이너          Docker / NVIDIA Container Toolkit의 OCI 훅 메커니즘
   ↓
쿠버네티스        Device Plugin gRPC 프로토콜, CDI 스펙 파일 내부
   ↓
모니터링          Prometheus / Grafana / DCGM 기반 GPU 모니터링·알림
```

## 실습 순서

1. GPU 카드가 장착된 PC에 **Ubuntu 24.04 Server** 설치
2. **NVIDIA Driver** 설치 및 확인
3. **Docker** 설치 → **NVIDIA Container Toolkit** 설치 및 확인
4. Docker 삭제 → **K3s** 설치 → **NVIDIA device plugin for Kubernetes** 설치 및 확인
5. 파드 기동 및 확인
6. **kube-prometheus-stack** 설치 → **DCGM Exporter** 설치 및 확인

> 참고: NVIDIA **GPU Operator**는 Driver, Container Toolkit, Device Plugin, DCGM Exporter, MIG Manager를 한 번에 관리합니다.

---

## 1. Ubuntu 설치 시 주의점

- **24.04 권장** — 26.04도 나왔지만 K8s 생태계 다수 툴이 24.04까지만 지원 (’26.7.8 기준)
- **Desktop보다 Server** — 실습에 최대 리소스를 쓰기 위함
- **Secure Boot 끄기** (필수) — UEFI 펌웨어가 부팅 시 신뢰되지 않은 커널 모듈 로드를 허용해야 함
- **WSL 환경은 비권장** — GPU-PV(Paravirtualization) 구조로 PCIe 패스스루가 아닌 가상화, 기능 제한

## 2. NVIDIA Driver — GPU 코드가 실행되는 경로

설치 후 확인할 것: 커널 모듈 `nvidia.ko.zst`, CUDA Driver API 라이브러리 `libcuda.so`, 장치 파일 `/dev/nvidia0`

```
유저 프로세스
  → system call
  → Linux Kernel (GPU 처리를 NVIDIA 드라이버에 위임)
  → NVIDIA 커널 모듈 (nvidia.ko, nvidia-uvm.ko 등)
  → GPU가 이해하는 실제 명령으로 번역·전달
```

애플리케이션이 GPU와 통신할 때 실제로 여는 디바이스 파일: **`/dev/nvidia0`**

**동작 확인**: `verify_gpu.py`로 4096×4096 GPU 행렬곱 실행 → `nvidia-smi`로 GPU-Util 100% / 메모리 사용량 실시간 확인

## 3. NVIDIA Container Toolkit — OCI 훅이 끼어드는 지점 ★

`runc`가 네임스페이스로 컨테이너를 격리시키려는 **찰나(컨테이너 프로세스 START 직전)** 에 toolkit이 훅으로 끼어들어 4가지를 순서대로 수행합니다.

| # | 작업 | 내용 |
|---|---|---|
| 1 | **GPU device mounts** | `/dev/nvidia0`, `/dev/nvidiactl`, `/dev/nvidia-uvm` 디바이스 노드를 컨테이너 안으로 bind-mount. 격리 원칙상 원래 보이면 안 되는 파일에 **강제로 구멍을 뚫는 것** |
| 2 | **NVIDIA driver libraries** | `libcuda.so`, `libnvidia-ml.so` 등을 호스트에서 컨테이너 파일시스템으로 복사/마운트. → `docker run --gpus all ubuntu nvidia-smi`가 **순정 ubuntu 이미지에서도 동작하는 이유** |
| 3 | **환경변수 주입** | `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES`. `--gpus all` 플래그가 실제로는 이 환경변수 설정으로 변환됨 |
| 4 | **Device cgroup** | 커널 cgroup 장치 컨트롤러 규칙을 수정해 지정된 GPU major/minor 번호에만 접근 허용. 마운트만으로는 커널이 여전히 막을 수 있어 **cgroup 레벨 허가가 별도로 필요** |

## 4. K8s가 GPU를 인식하는 과정 — Device Plugin ★

> 쿠버네티스는 CPU/메모리는 커널 cgroup으로 태생적으로 이해하지만, **GPU는 전혀 모릅니다.**
> 그래서 "GPU를 대신 알려주는 통역사"인 **Device Plugin**을 심어야 합니다.

| 단계 | 내용 |
|---|---|
| 1. **DaemonSet 배포** | 모든 GPU 노드에 `nvidia-device-plugin` 하나씩. `privileged: true` + `hostPath: /dev`로 호스트 `/dev` 전체를 볼 권한을 받아 `/dev/nvidia0`를 찾아냄 (현재는 최소권한 원칙으로 필요한 접근권만 부여) |
| 2. **kubelet에 등록** | 플러그인이 뜨자마자 각 노드 kubelet에 "나는 GPU 담당"이라고 자기소개(등록) |
| 3. **GPU 탐색** | 플러그인이 직접 NVML(`libnvidia-ml.so`)을 호출해 GPU 개수를 스스로 찾음 ("FOUND 1 GPU!") |
| 4. **ListAndWatch 보고** | kubelet이 물으면 `ListAndWatch` gRPC 스트림으로 계속 스트리밍. **heartbeat처럼 유지되는 이유**: GPU가 고장 나거나 빠지면 즉시 알려 스케줄링에서 빼야 하기 때문 |

결과로 노드에 다음이 찍힙니다:

```yaml
status:
  capacity:
    nvidia.com/gpu: '1'
  allocatable:
    nvidia.com/gpu: '1'
```

이제 파드가 `resources.limits.nvidia.com/gpu: 1`을 요청하면, 스케줄러가 이를 CPU/메모리처럼 **"숫자가 있는 자원"** 으로 취급해 GPU 노드에 배치합니다.

## 5. GPU 파드가 실제로 뜨는 전체 흐름 ★

| 단계 | 내용 |
|---|---|
| 1. kubelet이 계속 폴링 | `ListAndWatch` gRPC 스트림으로 지속 폴링. 로그의 `Registered device plugin for 'nvidia.com/gpu' with Kubelet`이 이 채널이 열린 순간 |
| 2. **Allocate API 호출** | 새 파드가 `nvidia.com/gpu: 1`을 요청하면 kubelet이 Device Plugin에 allocate 호출. `AllocateRequest{DeviceIDs:["GPU-abc123"]}` → `AllocateResponse{Devices:[...], Envs:{...}}` |
| 3. **CRI/CNI/CSI로 위임** | 실제 컨테이너를 만드는 건 Device Plugin이 아니라 kubelet. CRI(컨테이너 + **GPU 마운트 정보 전달**), CNI(네트워크), CSI(볼륨) |
| 4. **CRI 내부에서 GPU 주입** | containerd → containerd-shim → runc 파이프라인 중 **prestart/createRuntime 훅** 지점에서 NVIDIA Container Toolkit이 위 4가지(마운트/라이브러리/환경변수/cgroup) 처리 |

> **핵심**: Device Plugin은 "어떤 GPU를 줄지 결정"만 하고, 실제 `/dev` 마운트 같은 물리적 작업은 **컨테이너 런타임(toolkit)** 이 합니다.

참고: runtime hook 관련 **CDI**(Container Device Interface) 스펙

## 6. 모니터링 — DCGM Exporter

- `kube-prometheus-stack` 설치
- **DCGM Exporter** (NVIDIA GPU Telemetry) 설치 — Helm, Grafana 대시보드 ID **12239**
- GPU 부하 발생 후 메트릭 확인

### 참고: Prometheus Alert Rule 예시

| 알림 | 조건 |
|---|---|
| `HighGpuTemperature` | 85℃ 초과 5분 |
| `GpuXidError` | XID 에러 발생 1분 |
| `HighGpuMemoryUsage` | VRAM 90% 초과 10분 |

---

## 스터디 연결

- **6주차 AWS EKS 실습** 전에 읽으면 실습 중 GPU 파드가 뜨는 과정을 이해하기 쉽습니다.
- [HAMi 서브페이지](./hami-gpu-virtualization.md)의 전제 환경이 이 문서입니다.
- [GPU-Enabled Platforms on Kubernetes PDF](../references/pdfs.md) CH1(Foundations)과 내용이 대응합니다 — 실제로 이 서브페이지의 도식 다수가 해당 자료 출처입니다.
