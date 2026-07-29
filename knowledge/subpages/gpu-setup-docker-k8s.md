# (따라하며 확인하는) PC에 GPU 설정 및 사용 by Docker / K8S

원문: [노션 서브페이지](https://gasidaseo.notion.site/PC-GPU-by-Docker-K8S-39750aec5edf806d8070d580fac38917) 🛣️
참고 문서: [`references/pdfs.md`](../references/pdfs.md) → GPU-Enabled Platforms on Kubernetes

> 💻 **Windows 랩탑에서 돌리려면 → [`gpu-setup-windows-wsl2.md`](./gpu-setup-windows-wsl2.md)**
> 이 문서는 **Ubuntu 24.04 Server 베어메탈** 기준입니다. WSL에서 그대로 따라 하면 §2 드라이버 설치에서 GPU가 깨집니다.

## 한 줄 요약

**로컬 PC → 컨테이너 → 쿠버네티스** 단계별로 GPU 인식·실행을 확인하는 실습. 단순 설치 절차가 아니라 **GPU가 OS·컨테이너·K8s 안에서 어떤 경로로 노출되는지 구조**를 확인합니다.

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

### 원문 실습 환경

| 항목 | 값 |
|---|---|
| GPU | GeForce RTX 4070 Ti SUPER (16GB, AD103) |
| CPU / RAM | 16 vCPU / 64GB |
| OS / 커널 | Ubuntu 24.04 / 6.8.0-134-generic |
| 드라이버 | nvidia-driver-595-open (NVIDIA-SMI 595.71.05, CUDA 13.2) |

> 아래 명령은 **root 셸 기준**입니다. 일반 사용자면 `sudo`를 붙이세요. 드라이버 버전·커널 버전은 본인 환경 값으로 바꿔야 합니다.

---

## 1. Ubuntu 설치 시 주의점

- **24.04 권장** — 26.04도 나왔지만 K8s 생태계 다수 툴이 24.04까지만 지원 ('26.7.8 기준)
- **Desktop보다 Server** — 실습에 최대 리소스를 쓰기 위함
- **Secure Boot 끄기** (필수) — UEFI 펌웨어가 부팅 시 신뢰되지 않은 커널 모듈 로드를 허용해야 함
- **WSL 환경은 비권장** — GPU-PV(Paravirtualization) 구조로 PCIe 패스스루가 아닌 가상화, 기능 제한

### Secure Boot 확인 · 해제

```bash
# 기본 상태 확인 (보통 활성화되어 있음)
mokutil --sb-state
# SecureBoot enabled

# BIOS/UEFI 진입 → Secure Boot Disable → 재부팅 후 다시 확인
mokutil --sb-state
# SecureBoot disabled
```

---

## 2. NVIDIA Driver — GPU 코드가 실행되는 경로

```
유저 프로세스
  → system call
  → Linux Kernel (GPU 처리를 NVIDIA 드라이버에 위임)
  → NVIDIA 커널 모듈 (nvidia.ko, nvidia-uvm.ko 등)
  → GPU가 이해하는 실제 명령으로 번역·전달
```

애플리케이션이 GPU와 통신할 때 실제로 여는 디바이스 파일: **`/dev/nvidia0`**

### 설치

```bash
# GPU 장착 확인
lspci | grep -i nvidia
# 01:00.0 VGA compatible controller: NVIDIA Corporation AD103 [GeForce RTX 4070 Ti SUPER] (rev a1)
# 01:00.1 Audio device: NVIDIA Corporation Device 22bb (rev a1)

# 권장 드라이버 확인 — recommended가 붙은 버전을 설치
ubuntu-drivers devices
# driver : nvidia-driver-595-open - distro non-free recommended

# 설치 후 재부팅
apt -y install nvidia-driver-595-open
reboot
```

### 확인 — 드라이버가 남긴 것들

```bash
nvidia-smi
```

**DKMS가 관리하는 커널 모듈 확인.** NVIDIA 드라이버는 커널 버전마다 모듈을 새로 빌드해야 해서 DKMS로 관리됩니다(`nvidia-dkms-595-open` 패키지 담당).

```bash
# 컴파일된 커널 모듈 바이너리
# .ko가 아니라 .ko.zst인 것은 zstd로 압축되어 있다는 뜻
ls -l /lib/modules/6.8.0-134-generic/updates/dkms/

# 현재 커널에 실제 로드되어 동작 중인 모듈
lsmod | grep nvidia

# 장치 파일 — 애플리케이션이 실제로 여는 파일
ls -l /dev/nvidia0
ls -l /dev/nvidia*

# 드라이버 패키지가 설치한 라이브러리
ls -l /usr/lib/x86_64-linux-gnu/libcuda*
ls -l /usr/lib/x86_64-linux-gnu/libnvidia*

# 드라이버 초기화 과정 커널 로그
dmesg | grep -i nvidia
```

### 동작 확인 — `verify_gpu.py`

```bash
# 파이썬 가상 환경 구성
apt install -y python3-venv python3-pip
python3 -m venv /root/gpu-test-venv
/root/gpu-test-venv/bin/pip install --upgrade pip
/root/gpu-test-venv/bin/pip install torch numpy   # ~2GB 다운로드, 몇 분 소요

/root/gpu-test-venv/bin/pip list
du -sh /root/gpu-test-venv/                       # 4.7G
```

```python
# /root/verify_gpu.py
import torch, time

assert torch.cuda.is_available(), "CUDA GPU를 찾을 수 없습니다"
device = torch.device("cuda")
print("GPU:", torch.cuda.get_device_name(0))

n = 4096
a = torch.randn(n, n, device=device)
b = torch.randn(n, n, device=device)

torch.cuda.synchronize()
start = time.time()
while time.time() - start < 5:
    c = a @ b
torch.cuda.synchronize()
elapsed = time.time() - start

print(f"GPU 행렬곱 {n}x{n} 반복 실행: {elapsed:.1f}초")
print("결과 checksum:", c.sum().item())
print("GPU 메모리 사용량(MB):", torch.cuda.memory_allocated() / 1024**2)
```

터미널 2개를 띄워 **부하와 모니터링을 동시에** 봅니다.

```bash
# 터미널 A — 모니터링
watch -n 0.5 nvidia-smi

# 터미널 B — 실행
/root/gpu-test-venv/bin/python /root/verify_gpu.py
```

원문 실행 결과:

```
GPU: NVIDIA GeForce RTX 4070 Ti SUPER
GPU 행렬곱 4096x4096 반복 실행: 9.9초
결과 checksum: -249784.453125
GPU 메모리 사용량(MB): 200.125
```

모니터링 쪽에서 **GPU-Util 100%**, `Pwr:Usage 284W / 285W`, Processes에 `/root/gpu-test-venv/bin/python`이 잡히는 것을 확인합니다.

---

## 3. NVIDIA Container Toolkit — OCI 훅이 끼어드는 지점 ★

`runc`가 네임스페이스로 컨테이너를 격리시키려는 **찰나(컨테이너 프로세스 START 직전)** 에 toolkit이 훅으로 끼어들어 4가지를 순서대로 수행합니다.

| # | 작업 | 내용 |
|---|---|---|
| 1 | **GPU device mounts** | `/dev/nvidia0`, `/dev/nvidiactl`, `/dev/nvidia-uvm` 디바이스 노드를 컨테이너 안으로 bind-mount. 격리 원칙상 원래 보이면 안 되는 파일에 **강제로 구멍을 뚫는 것** |
| 2 | **NVIDIA driver libraries** | `libcuda.so`, `libnvidia-ml.so` 등을 호스트에서 컨테이너 파일시스템으로 복사/마운트. → `docker run --gpus all ubuntu nvidia-smi`가 **순정 ubuntu 이미지에서도 동작하는 이유** |
| 3 | **환경변수 주입** | `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES`. `--gpus all` 플래그가 실제로는 이 환경변수 설정으로 변환됨 |
| 4 | **Device cgroup** | 커널 cgroup 장치 컨트롤러 규칙을 수정해 지정된 GPU major/minor 번호에만 접근 허용. 마운트만으로는 커널이 여전히 막을 수 있어 **cgroup 레벨 허가가 별도로 필요** |

### Docker 설치

```bash
# 1. 사전 패키지
apt install -y ca-certificates curl

# 2. GPG 키링 등록
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# 3. apt 저장소 등록
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" \
  > /etc/apt/sources.list.d/docker.list

# 4. 설치
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. 검증
docker --version
docker compose version
systemctl is-active docker containerd
docker run --rm hello-world
```

### NVIDIA Container Toolkit 설치

```bash
# 1. GPG 키 등록
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 2. apt 저장소 등록
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 3. 설치
apt update
apt install -y nvidia-container-toolkit

# 4. Docker 엔진에 nvidia 런타임 등록
#    → Docker가 컨테이너 실행 시 순정 runc 대신 nvidia-container-runtime을 호출하게 됨
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
```

등록 결과 확인 — `/etc/docker/daemon.json`:

```json
"runtimes": {
  "nvidia": {
    "args": [],
    "path": "nvidia-container-runtime"
  }
}
```

```bash
# 검증 : --gpus 는 컨테이너에 추가할 GPU 지정 ('all' = 전부)
docker run --rm --gpus all ubuntu nvidia-smi

# 추가 확인
nvidia-container-cli --version
nvidia-ctk --version
cat /etc/nvidia-container-runtime/config.toml
cat /var/run/cdi/nvidia.yaml
```

### 컨테이너 안에서 4가지 주입 직접 확인

```bash
docker run --rm -it --gpus all ubuntu bash
```

컨테이너 안에서:

```bash
# 순정 ubuntu에 nvidia-smi가 있을 리 없는데 동작한다 → toolkit이 호스트 것을 밀어준 것
nvidia-smi

# (1) 디바이스 노드가 들어와 있음
ls -l /dev/nvidia*

# (2) 드라이버 라이브러리가 들어와 있음
ls -l /usr/lib/x86_64-linux-gnu/libcuda*
ls -l /usr/lib/x86_64-linux-gnu/libnvidia*

# (3) toolkit이 주입한 환경변수
env | grep NVIDIA
```

---

## 4. Docker 삭제 → K3s 설치

### Docker 삭제

> K3s는 자체 containerd를 쓰므로 원문은 여기서 Docker를 걷어냅니다. 실습만 목적이면 남겨둬도 동작하지만, 네트워크(iptables) 충돌을 피하려면 원문대로 지우는 편이 깔끔합니다.

```bash
# 1. 상태 사전 확인
docker ps -a
docker images

# 2. 서비스 중지/비활성화
systemctl disable --now docker.service docker.socket containerd.service

# 3. 패키지 제거
apt purge -y docker-ce docker-ce-cli docker-buildx-plugin docker-ce-rootless-extras docker-compose-plugin containerd.io
apt autoremove -y --purge

# 4. 잔여 데이터/설정 삭제
rm -rf /var/lib/docker /var/lib/containerd /etc/docker /etc/containerd
rm -f /etc/apt/sources.list.d/docker.list /etc/apt/keyrings/docker.asc
groupdel docker
apt update

# 5. iptables/ip6tables 정리
for cmd in iptables ip6tables; do
  for table in filter nat mangle raw; do
    $cmd -t $table -F
    $cmd -t $table -X
  done
  $cmd -P INPUT ACCEPT; $cmd -P FORWARD ACCEPT; $cmd -P OUTPUT ACCEPT
done

# 6. 고아 브리지 인터페이스 삭제
ip link delete docker0
```

### K3s 설치

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --kube-controller-manager-arg=bind-address=0.0.0.0 \
  --kube-scheduler-arg=bind-address=0.0.0.0 \
  --kube-proxy-arg=metrics-bind-address=0.0.0.0 \
  --write-kubeconfig-mode=644" sh -
```

> `bind-address=0.0.0.0` 3개는 §6에서 **Prometheus가 컨트롤 플레인 메트릭을 긁어가게** 하려는 설정입니다. `--write-kubeconfig-mode=644`는 root가 아닌 사용자도 kubeconfig를 읽게 합니다.

```bash
# 설치된 바이너리 — crictl, ctr, kubectl이 전부 k3s 심볼릭 링크
tree -pug /usr/local/bin

# 시스템 데몬 정의
cat /etc/systemd/system/k3s.service

# 서비스 동작 확인
systemctl is-active k3s.service   # active
```

### K3s 확인 — nvidia 런타임 자동 발견 ★

```bash
kubectl cluster-info -v=6
cat /etc/rancher/k3s/k3s.yaml
kubectl get node -owide

# K3s는 컨테이너 런타임(nvidia, nvidia-cdi, nvidia-experimental 등)을 자동 발견해 적용함
grep nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml
# BinaryName = "/usr/bin/nvidia-container-runtime"

# 자동 감지 결과가 RuntimeClass로 등록되어 있음
kubectl get runtimeclass nvidia

# 단일 노드가 워크로드를 받을 수 있는지 taint 확인
kubectl describe node | grep -i '^Taints'
```

> **여기가 K3s의 편한 점**입니다. 일반 K8s라면 containerd 설정을 직접 고치고 RuntimeClass를 손으로 만들어야 하는데, K3s는 toolkit이 깔려 있으면 알아서 잡아줍니다.

---

## 5. NVIDIA Device Plugin — K8s가 GPU를 인식하는 과정 ★

> 쿠버네티스는 CPU/메모리는 커널 cgroup으로 태생적으로 이해하지만, **GPU는 전혀 모릅니다.**
> 그래서 "GPU를 대신 알려주는 통역사"인 **Device Plugin**을 심어야 합니다.

| 단계 | 내용 |
|---|---|
| 1. **DaemonSet 배포** | 모든 GPU 노드에 `nvidia-device-plugin` 하나씩 |
| 2. **kubelet에 등록** | 플러그인이 뜨자마자 각 노드 kubelet에 "나는 GPU 담당"이라고 자기소개 |
| 3. **GPU 탐색** | 플러그인이 직접 NVML(`libnvidia-ml.so`)을 호출해 GPU 개수를 스스로 찾음 |
| 4. **ListAndWatch 보고** | kubelet이 물으면 `ListAndWatch` gRPC 스트림으로 계속 스트리밍. **heartbeat처럼 유지되는 이유**: GPU가 고장 나거나 빠지면 즉시 알려 스케줄링에서 빼야 하기 때문 |

### 설치

```bash
# 1. Device Plugin YAML 다운로드
curl -sL https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.19.3/deployments/static/nvidia-device-plugin.yml \
  -o /root/nvidia-device-plugin.yml

# 2. runtimeClassName: nvidia 패치 (k3s가 자동 등록해둔 RuntimeClass를 쓰도록)
sed -i "30a\\      runtimeClassName: nvidia" /root/nvidia-device-plugin.yml

# 3. 적용
kubectl apply -f /root/nvidia-device-plugin.yml
```

> 직접 설치 대신 **Helm 설치도 권장**됩니다. 위 `sed` 삽입 위치(30행)는 해당 버전 기준이므로, 다른 버전을 쓰면 `spec:` 아래 들어갔는지 반드시 확인하세요.

### 확인 — 최소 권한으로 도는 것 관찰 ★

```bash
kubectl get ds -n kube-system nvidia-device-plugin-daemonset
kubectl get pod -n kube-system -l name=nvidia-device-plugin-ds
kubectl describe pod -n kube-system -l name=nvidia-device-plugin-ds
```

> **이 파드는 `/dev` 전체를 마운트하지도, `privileged: true`도 쓰지 않습니다.**
> 예전 방식은 호스트 `/dev` 전체를 볼 권한을 받았지만, 현재는 최소권한 원칙에 따라 필요한 접근권만 받습니다.

```yaml
Volumes:
  kubelet-device-plugins-dir:
    Type:          HostPath (bare host directory volume)
    Path:          /var/lib/kubelet/device-plugins
    HostPathType:  Directory
```

```bash
# kubelet ↔ 플러그인이 통신하는 소켓
ls -l /var/lib/kubelet/device-plugins
# kubelet.sock
# nvidia-gpu.sock      ← 플러그인이 등록하며 만든 소켓
# kubelet_internal_checkpoint

kubectl get pod -n kube-system -l name=nvidia-device-plugin-ds -o json | jq
```

securityContext에서 확인할 것:

```json
"securityContext": {
  "allowPrivilegeEscalation": false,   // setuid 등으로 스스로 권한 상승하는 것을 원천 차단
  "capabilities": { "drop": ["ALL"] }  // 커널 capability 전부 제거 — 일반 root보다도 제한적
},
"runtimeClassName": "nvidia"
```

### 노드에 GPU 자원이 잡혔는지

```bash
kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}'; echo
# 1

kubectl describe node
```

```yaml
Capacity:
  cpu:             16
  memory:          64916464Ki
  nvidia.com/gpu:  1
  pods:            110
Allocatable:
  nvidia.com/gpu:  1
```

이제 파드가 `resources.limits.nvidia.com/gpu: 1`을 요청하면, 스케줄러가 이를 CPU/메모리처럼 **"숫자가 있는 자원"** 으로 취급해 GPU 노드에 배치합니다.

---

## 6. GPU 파드가 실제로 뜨는 전체 흐름 ★

| 단계 | 내용 |
|---|---|
| 1. kubelet이 계속 폴링 | `ListAndWatch` gRPC 스트림으로 지속 폴링. 로그의 `Registered device plugin for 'nvidia.com/gpu' with Kubelet`이 이 채널이 열린 순간 |
| 2. **Allocate API 호출** | 새 파드가 `nvidia.com/gpu: 1`을 요청하면 kubelet이 Device Plugin에 allocate 호출. `AllocateRequest{DeviceIDs:["GPU-abc123"]}` → `AllocateResponse{Devices:[...], Envs:{...}}` |
| 3. **CRI/CNI/CSI로 위임** | 실제 컨테이너를 만드는 건 Device Plugin이 아니라 kubelet. CRI(컨테이너 + **GPU 마운트 정보 전달**), CNI(네트워크), CSI(볼륨) |
| 4. **CRI 내부에서 GPU 주입** | containerd → containerd-shim → runc 파이프라인 중 **prestart/createRuntime 훅** 지점에서 NVIDIA Container Toolkit이 §3의 4가지를 처리 |

> **핵심**: Device Plugin은 "어떤 GPU를 줄지 결정"만 하고, 실제 `/dev` 마운트 같은 물리적 작업은 **컨테이너 런타임(toolkit)** 이 합니다.

### 파드 기동

```bash
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
  namespace: default
spec:
  runtimeClassName: nvidia
  restartPolicy: Never
  containers:
  - name: gpu-test
    image: ubuntu:24.04
    command: ["sleep", "infinity"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

kubectl exec -it gpu-test -- bash
```

파드 안에서 — §3의 Docker 때와 **똑같은 것**을 확인합니다:

```bash
env | grep NVIDIA                                 # (3) 환경변수
nvidia-smi                                        # (2) toolkit이 호스트 것을 밀어줌
ls -l /dev/nvidia*                                # (1) 디바이스 노드
ls -l /usr/lib/x86_64-linux-gnu/libcuda*          # (2) 라이브러리
ls -l /usr/lib/x86_64-linux-gnu/libnvidia*

# GPU 코드도 직접 실행해보기
apt update && apt install -y python3-venv python3-pip
python3 -m venv /root/venv && /root/venv/bin/pip install torch numpy
```

```bash
kubectl delete pod gpu-test
```

토치가 미리 들어 있는 이미지를 쓰면 설치 없이 바로 됩니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
  namespace: default
spec:
  runtimeClassName: nvidia
  restartPolicy: Never
  containers:
  - name: gpu-test
    image: pytorch/pytorch:2.9.0-cuda12.8-cudnn9-runtime
    command: ["sleep", "infinity"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

### CDI — 훅이 무엇을 하는지 스펙 파일로 보기 ★

runtime hook의 실체는 **CDI(Container Device Interface)** 스펙 파일입니다.

```bash
# K3s는 이 경로 / 일반 K8s는 /etc/containerd/config.toml
cat /etc/nvidia-container-runtime/config.toml | grep -i cdi
# spec-dirs = ["/etc/cdi", "/var/run/cdi"]

cat /var/run/cdi/nvidia.yaml
```

`nvidia.yaml` 안에 §3의 4가지가 **선언적으로** 적혀 있습니다:

```yaml
kind: nvidia.com/gpu
devices:
- name: "0"
  containerEdits:
    deviceNodes:                       # (1) 디바이스 마운트
    - path: /dev/nvidia0
      major: 195
      fileMode: 438
      permissions: rwm
    - path: /dev/dri/card1
      ...
    hooks:                             # (2) 라이브러리 심볼릭 링크
    - hookName: createContainer
      path: /usr/bin/nvidia-cdi-hook
      args:
      - nvidia-cdi-hook
      - create-symlinks
      - --link
      - libcuda.so.1::/usr/lib/x86_64-linux-gnu/libcuda.so
      - --link
      - libcuda.so.595.71.05::/usr/lib/x86_64-linux-gnu/libcuda.so.1
      ...
    additionalGids: [44, 993]
```

GPU가 UUID로도 등록됩니다 (`name: GPU-eabaa66e-...`). Device Plugin이 `AllocateRequest`에 담아 보내는 `DeviceIDs`가 바로 이 이름입니다.

---

## 7. 모니터링 — kube-prometheus-stack + DCGM Exporter

### kube-prometheus-stack 설치

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# PC IP 지정 (컨트롤 플레인 메트릭 수집 대상)
MYPCIP=192.168.254.150

# K3s 기본 스토리지 클래스 확인
kubectl get sc      # local-path
```

파라미터 파일을 만듭니다. 핵심만 발췌하면:

```yaml
# monitor-values.yaml
prometheus:
  service:
    type: NodePort
    nodePort: 30001
  prometheusSpec:
    serviceMonitorSelectorNilUsesHelmValues: false
    retention: 7d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: local-path
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 20Gi

grafana:
  defaultDashboardsTimezone: Asia/Seoul
  adminPassword: prom-operator
  service:
    type: NodePort
    nodePort: 30002
  persistence:
    enabled: true
    type: pvc
    storageClassName: local-path
    size: 10Gi

# 컨트롤 플레인 컴포넌트 — K3s는 endpoints에 PC IP를 직접 지정해야 잡힘
kubeControllerManager:
  enabled: true
  endpoints: [192.168.254.150]
  service: { enabled: true, port: 10257, targetPort: 10257 }
  serviceMonitor: { enabled: true, https: true, insecureSkipVerify: true }
kubeScheduler:
  enabled: true
  endpoints: [192.168.254.150]
  service: { enabled: true, port: 10259, targetPort: 10259 }
  serviceMonitor: { enabled: true, https: true, insecureSkipVerify: true }
kubeProxy:
  enabled: true
  endpoints: [192.168.254.150]
  service: { enabled: true, port: 10249, targetPort: 10249 }
  serviceMonitor: { enabled: true }

# 단일 노드 K3s는 sqlite라 etcd가 없음
# --cluster-init 로 embedded etcd를 쓸 때만 true
kubeEtcd:
  enabled: false
```

```bash
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --version 87.5.1 \
  -f monitor-values.yaml --create-namespace --namespace monitoring

# 확인
helm list -n monitoring
kubectl get pod,svc,ingress,pvc -n monitoring
kubectl get prometheus,servicemonitors,alertmanagers -n monitoring
kubectl get crd | grep monitoring
```

```bash
open http://$MYPCIP:30001    # Prometheus
open http://$MYPCIP:30002    # Grafana — admin / prom-operator
```

### DCGM Exporter 설치

```bash
helm repo add nvidia https://nvidia.github.io/dcgm-exporter/helm-charts
helm repo update

helm upgrade --install dcgm-exporter nvidia/dcgm-exporter -n monitoring \
  --set runtimeClassName=nvidia \
  --set serviceMonitor.enabled=true
```

> `runtimeClassName=nvidia`가 필요한 이유는 Device Plugin 때와 같습니다 — **DCGM이 NVML로 GPU를 조회하려면 K3s가 등록해둔 nvidia RuntimeClass를 거쳐야** 합니다.

```bash
kubectl -n monitoring port-forward svc/dcgm-exporter 9400:9400

curl -s http://localhost:9400/metrics | head -50
curl -s http://localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL      # GPU 사용률(%)
curl -s http://localhost:9400/metrics | grep DCGM_FI_DEV_FB_USED       # 프레임버퍼 사용량(MiB)
curl -s http://localhost:9400/metrics | grep DCGM_FI_DEV_GPU_TEMP      # 온도(C)
curl -s http://localhost:9400/metrics | grep DCGM_FI_DEV_POWER_USAGE   # 전력(W)
curl -s http://localhost:9400/metrics | grep DCGM_FI_DEV_XID_ERRORS    # XID 에러
```

Grafana 대시보드 ID **12239**를 임포트하면 위 메트릭이 그려집니다.

### GPU 부하 발생 — nbody 벤치마크

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-load
spec:
  restartPolicy: Never
  runtimeClassName: nvidia
  containers:
  - name: cuda
    image: nvcr.io/nvidia/k8s/cuda-sample:nbody
    args: ["nbody", "-gpu", "-benchmark", "-numbodies=5000000"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

kubectl logs gpu-load -f     # 약 4분 소요
```

원문 결과 해석:

| 출력 | 의미 |
|---|---|
| `5,000,000 → 5,000,192` | GPU thread/block 효율을 위해 body 수를 **256의 배수**로 자동 상향 |
| `211,781 ms / 10 iterations` | 1 iteration당 약 21.18초 |
| `1,180.552 billion interactions/s` | 초당 약 **1.18조** 상호작용 |
| `23,611 GFLOP/s` | **FP32 단정밀도** 기준 |
| `Compute Capability 8.9` | RTX 4070 Ti SUPER = Ada Lovelace |
| 아키텍처가 "Ampere"로 표시됨 | 샘플 이미지가 SM 8.9 매핑 테이블을 최신으로 갖고 있지 않아 기본값(128 Cores/SM)으로 처리한 것. **버그 아님** |

> ⚠️ CUDA 샘플은 공식 벤치마크 도구가 아닙니다. 출력된 GFLOP/s는 **참고용**입니다.

### Prometheus Alert Rule

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-alert-rules
  namespace: monitoring
  labels:
    release: kube-prometheus-stack
spec:
  groups:
  - name: gpu.rules
    rules:
    - alert: HighGpuTemperature
      expr: DCGM_FI_DEV_GPU_TEMP > 85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "GPU temperature is high"
        description: "GPU temperature is above 85C for more than 5 minutes."
    - alert: GpuXidError
      expr: DCGM_FI_DEV_XID_ERRORS > 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "GPU XID error detected"
        description: "NVIDIA GPU XID error detected. Check dmesg and nvidia-smi."
    - alert: HighGpuMemoryUsage
      expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100 > 90
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "GPU memory usage is high"
        description: "GPU framebuffer memory usage is above 90% for more than 10 minutes."
EOF

kubectl get prometheusrule -n monitoring
```

---

## 실습 전체를 관통하는 한 가지

§3(Docker), §6(K8s 파드), §6의 CDI 스펙 — **세 곳에서 똑같은 4가지 주입**을 확인하게 됩니다.

```
docker run --gpus all      →  toolkit이 훅으로 주입
kubectl apply (gpu: 1)     →  Device Plugin이 "결정", toolkit이 "주입"
/var/run/cdi/nvidia.yaml   →  그 주입 내용이 선언적으로 적힌 스펙
```

`ls -l /dev/nvidia*`와 `env | grep NVIDIA`를 각 레이어에서 반복해 찍어보는 것이 이 실습의 핵심입니다.

---

## 스터디 연결

- **6주차 AWS EKS 실습** 전에 읽으면 실습 중 GPU 파드가 뜨는 과정을 이해하기 쉽습니다.
- [HAMi 서브페이지](./hami-gpu-virtualization.md)의 전제 환경이 이 문서입니다.
- [GPU-Enabled Platforms on Kubernetes PDF](../references/pdfs.md) CH1(Foundations)과 내용이 대응합니다 — 이 서브페이지의 도식 다수가 해당 자료 출처입니다.
- Windows 랩탑에서 실행하려면 → [`gpu-setup-windows-wsl2.md`](./gpu-setup-windows-wsl2.md)

> ⚠️ 원문 노션은 외부 공개·전파 금지입니다. 이 문서는 개인 학습용 정리이며 그대로 외부에 공개하지 마세요. → [`03-study-rules.md`](../03-study-rules.md)
