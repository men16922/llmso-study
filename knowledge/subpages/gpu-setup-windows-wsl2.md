# (Windows 랩탑판) PC에 GPU 설정 및 사용 by Docker / K8S

원문 실습: [`gpu-setup-docker-k8s.md`](./gpu-setup-docker-k8s.md) — Ubuntu 24.04 Server **베어메탈** 기준
이 문서: 같은 실습을 **Windows 11 + WSL2 + GeForce RTX 4080 Laptop (12GB)** 에서 바로 따라 할 수 있게 옮긴 것

> ⚠️ **원문은 WSL을 명시적으로 비권장합니다.** GPU-PV(Paravirtualization) 구조라 PCIe 패스스루가 아니고 기능 제한이 있기 때문입니다. 그럼에도 이 문서를 쓰는 이유는 ① 1~5단계는 WSL2에서 그대로 재현되고 ② **어디서 깨지는지가 오히려 GPU 노출 구조를 이해하는 좋은 재료**이기 때문입니다. 재현 불가 항목은 [§9](#9-원문-대비-재현-불가-항목)에 모아뒀습니다.

---

## 원문과 달라지는 지점 한눈에

| 원문 (Ubuntu 베어메탈) | 여기 (Windows + WSL2) |
|---|---|
| Ubuntu 24.04 **Server** 설치 | WSL2에 Ubuntu 24.04 배포판 설치 |
| **Secure Boot 끄기** | **불필요** — 커널 모듈을 직접 올리지 않음 |
| 리눅스용 **NVIDIA Driver 설치** | **설치 금지** ★ — Windows 드라이버를 WSL이 그대로 씁니다 |
| 디바이스 파일 `/dev/nvidia0` | **`/dev/dxg`** ★ — 이 차이가 GPU-PV의 정체 |
| K3s 바로 설치 | K3s 전에 **systemd 활성화** 필요 |
| DCGM Exporter 전체 메트릭 | **상당수 메트릭 미지원** |
| MIG / GPU Operator | **불가** |

---

## 0. 사전 확인 (Windows 쪽, 5분)

PowerShell에서:

```powershell
# 1) WSL 버전 — 2.0 이상 권장
wsl --version

# 2) NVIDIA 드라이버 — Windows에 이미 깔려 있어야 함 (GeForce Game Ready / Studio 아무거나)
nvidia-smi
```

`nvidia-smi`가 12GB(12288MiB 내외)를 보여주면 준비 완료입니다. 안 나오면 [NVIDIA 드라이버](https://www.nvidia.com/download/index.aspx)를 먼저 설치하세요. **CUDA Toolkit은 Windows에 설치할 필요 없습니다.**

### 랩탑 필수 설정

| 항목 | 이유 |
|---|---|
| **전원 어댑터 연결** | 배터리 모드는 TGP가 깎여 클럭이 내려갑니다. 측정값이 흔들립니다 |
| Windows 설정 → 시스템 → 디스플레이 → 그래픽 → **고성능** | dGPU 고정 |
| 브라우저·Teams 등 종료 | 12GB 중 일부를 디스플레이·앱이 이미 씁니다 |

### WSL2 메모리 상한 설정

WSL2는 기본적으로 호스트 RAM의 50%를 가져갑니다. K3s + 모델 로딩까지 하면 부족할 수 있으니 `%USERPROFILE%\.wslconfig`를 만드세요:

```ini
[wsl2]
memory=24GB          # 호스트 RAM에 맞춰 조정 (32GB 머신 기준)
processors=8
swap=8GB
```

```powershell
wsl --shutdown        # 설정 반영
```

---

## 1. WSL2 + Ubuntu 24.04 설치

원문 §1의 "Ubuntu 24.04 Server 설치"에 대응합니다. **Secure Boot 끄는 단계는 없습니다** — WSL2는 Microsoft 커널을 쓰고 우리가 커널 모듈을 올리지 않기 때문입니다.

```powershell
wsl --install -d Ubuntu-24.04
wsl -l -v                      # VERSION이 2인지 확인
```

`VERSION`이 1이면 `wsl --set-version Ubuntu-24.04 2`로 올리세요.

이후 명령은 모두 **WSL 안의 Ubuntu 셸**에서 실행합니다.

---

## 2. GPU 인식 확인 — ★ 드라이버를 설치하지 마세요

원문 §2는 리눅스에 NVIDIA Driver를 설치하고 `nvidia.ko` 커널 모듈과 `/dev/nvidia0`을 확인합니다. **WSL2에서는 이 단계를 건너뜁니다.**

Windows 호스트 드라이버가 WSL 안으로 필요한 것들을 직접 투영해주기 때문입니다.

```bash
# 드라이버 설치 없이 이미 동작합니다
nvidia-smi

# 이게 어디서 오는지 확인 — WSL 전용 shim
which nvidia-smi          # → /usr/lib/wsl/lib/nvidia-smi
ls -l /usr/lib/wsl/lib/   # libcuda.so, libnvidia-ml.so 등이 여기 있음
```

### ★ 원문과 결정적으로 다른 지점 — 디바이스 파일

원문은 "애플리케이션이 GPU와 통신할 때 실제로 여는 파일은 `/dev/nvidia0`"이라고 설명합니다. WSL2에서 직접 확인해보세요:

```bash
ls /dev/nvidia*     # → No such file or directory
ls -l /dev/dxg      # → 이게 있습니다
```

**`/dev/nvidia0`이 없고 `/dev/dxg`가 대신 있습니다.** WSL2는 PCIe 디바이스를 패스스루하지 않고, `dxgkrnl`이라는 Windows 그래픽 커널 인터페이스를 반가상화(GPU-PV)해서 넘겨줍니다. 즉 리눅스 커널이 GPU를 직접 잡는 게 아니라 **Windows에게 대신 요청**하는 구조입니다.

> 원문이 WSL을 비권장하는 이유가 이 한 줄로 설명됩니다. 뒤에서 MIG·DCGM이 막히는 것도 전부 여기서 파생됩니다. **이 확인 결과는 과제 글에 그대로 쓸 만합니다.**

### CUDA Toolkit 설치 (선택) — ★ 함정 주의

`nvcc`가 필요하면 설치하되, **반드시 `cuda-toolkit` 패키지만** 설치하세요.

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

sudo apt-get install -y cuda-toolkit-12-6     # ✅ 툴킷만
# sudo apt-get install -y cuda               # ❌ 절대 금지 — 리눅스 드라이버를 끌고 와 GPU가 죽습니다
```

레포지토리 경로가 `wsl-ubuntu`인 점을 확인하세요. 일반 `ubuntu2404` 경로를 쓰면 드라이버 패키지가 딸려옵니다.

### 동작 확인 — `verify_gpu.py`

원문의 4096×4096 행렬곱 검증에 대응합니다.

```bash
sudo apt-get install -y python3-pip python3-venv
python3 -m venv ~/gpuenv && source ~/gpuenv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu126
```

```python
# ~/verify_gpu.py
import torch, time

assert torch.cuda.is_available(), "CUDA를 못 찾습니다"
print("GPU:", torch.cuda.get_device_name(0))
print("VRAM:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1), "GB")

a = torch.randn(4096, 4096, device="cuda")
b = torch.randn(4096, 4096, device="cuda")

for _ in range(10):                      # 워밍업 — 랩탑은 특히 중요
    torch.matmul(a, b)
torch.cuda.synchronize()

t0 = time.time()
for _ in range(200):
    torch.matmul(a, b)
torch.cuda.synchronize()
dt = time.time() - t0

flops = 2 * 4096**3 * 200
print(f"{dt:.2f}s, {flops/dt/1e12:.1f} TFLOPS")
```

다른 WSL 터미널에서 부하를 보며 실행하세요:

```bash
watch -n 0.5 'nvidia-smi --query-gpu=utilization.gpu,memory.used,clocks.sm,power.draw,temperature.gpu --format=csv'
```

> **랩탑에서 꼭 볼 것**: 30초 이상 돌리면 `clocks.sm`이 떨어지고 TFLOPS가 같이 내려갑니다. 발열 스로틀링입니다. 데이터센터 GPU에는 없는 현상이라, 측정할 때는 반드시 **클럭·전력을 함께 기록**하세요.

---

## 3. Docker + NVIDIA Container Toolkit

원문 §3에 대응합니다. **Docker Desktop이 아니라 WSL 안에 직접 설치**하는 걸 권장합니다 — 뒤에서 K3s가 containerd를 직접 다뤄야 해서 Docker Desktop은 방해가 됩니다.

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo service docker restart
```

### 동작 확인 — OCI 훅이 실제로 하는 일 보기

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

**순정 `ubuntu` 이미지에 `nvidia-smi`가 있을 리 없는데 동작합니다.** 원문 §3이 설명하는 4가지 주입(디바이스 마운트 / 드라이버 라이브러리 / 환경변수 / cgroup) 중 2번이 눈에 보이는 순간입니다.

WSL2에서 실제로 뭐가 들어갔는지 직접 확인해보세요:

```bash
# 환경변수 주입 확인 (3번)
docker run --rm --gpus all ubuntu env | grep NVIDIA

# 라이브러리 주입 확인 (2번)
docker run --rm --gpus all ubuntu ls /usr/lib/x86_64-linux-gnu/ | grep -E 'libcuda|libnvidia-ml'

# ★ 디바이스 마운트 확인 (1번) — 원문과 다른 결과가 나옵니다
docker run --rm --gpus all ubuntu ls /dev/ | grep -E 'nvidia|dxg'
```

마지막 명령에서 원문은 `nvidia0`, `nvidiactl`, `nvidia-uvm`이 나오지만 **여기서는 `dxg`가 나옵니다.** toolkit이 WSL 환경을 감지해 `/dev/dxg`와 `/usr/lib/wsl/lib`를 대신 마운트한 것입니다. 원문 §3의 메커니즘 자체는 동일하되 **주입 대상만 바뀐 것**입니다.

---

## 4. K3s 설치 — ★ WSL2 전용 사전 작업

원문 §4는 Docker를 지우고 K3s를 깝니다. WSL2에서는 그 전에 **systemd를 켜야** 합니다. K3s가 systemd 서비스로 동작하기 때문입니다.

```bash
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[boot]
systemd=true
EOF
```

PowerShell에서 재시작:

```powershell
wsl --shutdown
```

다시 들어와서 확인:

```bash
systemctl is-system-running     # running 또는 degraded 면 OK
```

### K3s 설치

> 원문은 여기서 Docker를 삭제합니다. 실습 목적상 **Docker를 남겨두고 K3s를 함께 써도 무방**합니다 (K3s는 자체 containerd를 씁니다). 원문 그대로 하려면 `sudo apt-get remove -y docker-ce docker-ce-cli containerd.io`.

```bash
curl -sfL https://get.k3s.io | sh -

sudo chmod 644 /etc/rancher/k3s/k3s.yaml
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc
source ~/.bashrc

kubectl get nodes
```

### K3s가 nvidia 런타임을 잡았는지 확인

원문이 언급하는 "K3s의 컨테이너 런타임 자동 발견"이 동작했는지 봅니다:

```bash
grep -A3 nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml
```

`nvidia` 런타임 항목이 안 보이면 toolkit 설치 후 K3s를 재시작하세요:

```bash
sudo nvidia-ctk runtime configure --runtime=containerd \
  --config=/var/lib/rancher/k3s/agent/etc/containerd/config.toml
sudo systemctl restart k3s
```

RuntimeClass를 만들어 둡니다:

```bash
kubectl apply -f - <<'EOF'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
EOF
```

---

## 5. NVIDIA Device Plugin 설치

원문 §4 후반 — "K8s는 GPU를 전혀 모르므로 통역사를 심는다"에 대응합니다.

```bash
kubectl create ns gpu-operator

kubectl apply -n gpu-operator -f \
  https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.17.1/deployments/static/nvidia-device-plugin.yml
```

### 동작 확인 — 원문의 4단계를 로그로 추적

```bash
# 3단계 "GPU 탐색" — NVML 호출 결과
kubectl logs -n gpu-operator -l name=nvidia-device-plugin-ds | grep -i found

# 2·4단계 "kubelet 등록 / ListAndWatch"
kubectl logs -n gpu-operator -l name=nvidia-device-plugin-ds | grep -i registered
```

원문이 말한 `Registered device plugin for 'nvidia.com/gpu' with Kubelet`이 이 로그입니다. 이 줄이 뜬 순간이 gRPC 스트림이 열린 시점입니다.

노드에 자원이 잡혔는지 확인:

```bash
kubectl get node -o jsonpath='{.items[0].status.allocatable}' | tr ',' '\n' | grep nvidia
# → "nvidia.com/gpu":"1"
```

원문의 결과와 동일하게 나와야 합니다:

```yaml
status:
  capacity:
    nvidia.com/gpu: '1'
  allocatable:
    nvidia.com/gpu: '1'
```

---

## 6. GPU 파드 기동 및 확인

원문 §5에 대응합니다.

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: gpu-check
spec:
  runtimeClassName: nvidia
  restartPolicy: Never
  containers:
  - name: cuda
    image: nvidia/cuda:12.6.0-base-ubuntu24.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

kubectl logs gpu-check
```

### 원문 §5의 흐름을 실제로 관찰하기

파드가 뜨는 동안 kubelet ↔ Device Plugin의 `Allocate` 호출을 봅니다:

```bash
sudo journalctl -u k3s -f | grep -iE 'allocate|nvidia.com/gpu'
```

핵심은 원문이 강조한 이 문장입니다 — **Device Plugin은 "어떤 GPU를 줄지"만 정하고, 실제 `/dev` 마운트는 컨테이너 런타임(toolkit)이 합니다.** 위 §3에서 Docker로 확인한 4가지 주입이 여기서는 containerd → runc의 prestart 훅에서 똑같이 일어납니다.

파드 안에서 직접 확인:

```bash
kubectl exec gpu-check -- ls /dev/ | grep -E 'nvidia|dxg'   # dxg
kubectl exec gpu-check -- env | grep NVIDIA
```

정리:

```bash
kubectl delete pod gpu-check
```

---

## 7. 모니터링 — DCGM Exporter (부분 동작)

원문 §6에 대응하지만 **여기가 WSL2에서 가장 많이 깨지는 구간**입니다.

```bash
# kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install kps prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# DCGM Exporter
helm repo add gpu-helm-charts https://nvidia.github.io/dcgm-exporter/helm-charts
helm repo update
helm install dcgm gpu-helm-charts/dcgm-exporter -n monitoring \
  --set runtimeClassName=nvidia
```

```bash
kubectl -n monitoring port-forward svc/dcgm-exporter 9400:9400
curl -s localhost:9400/metrics | grep -E '^DCGM_FI_DEV' | head -20
```

### ⚠️ 기대치 조정

WSL2의 GPU-PV 구조상 **DCGM이 하드웨어 카운터에 직접 접근하지 못해 상당수 메트릭이 0이거나 아예 나오지 않습니다.** 특히:

| 메트릭 종류 | WSL2 |
|---|---|
| `DCGM_FI_DEV_GPU_UTIL`, `FB_USED` (기본) | 대체로 나옴 |
| `DCGM_FI_PROF_*` (프로파일링: SM Activity, Tensor Active 등) | **대부분 미지원** |
| XID 에러, 온도·전력 일부 | 불안정 |

DCGM이 아예 뜨지 않으면 **Grafana 대시보드 12239 실습은 건너뛰고**, 대신 `nvidia-smi` 폴링을 Prometheus에 직접 넣는 방식으로 대체하세요. 원문의 Alert Rule 3종(`HighGpuTemperature` 85℃/5분, `GpuXidError` 1분, `HighGpuMemoryUsage` VRAM 90%/10분)은 규칙 자체는 그대로 쓸 수 있습니다.

> **이 실패 자체가 과제 소재입니다.** "가상화 계층이 하나 끼면 관측성이 어디서부터 무너지는가"는 6주차 EKS 실습과 대비하기 좋은 주제입니다.

---

## 8. 이어서 — vLLM 띄우기 (12GB 기준)

원문 실습에는 없지만, 1주차 과제로 이어가려면 여기까지 온 환경에서 바로 할 수 있습니다.

```bash
docker run --rm --gpus all -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85
```

### VRAM 12GB에서 고를 수 있는 모델

가용 VRAM은 약 10.5GB(프레임워크·컨텍스트 제외)이고, **KV cache 자리를 남겨야** 합니다.

| 모델 | 정밀도 | 가중치 | 판정 |
|---|---|---|---|
| Qwen2.5-1.5B-Instruct | FP16 | ~3GB | ◎ 배칭 실험용 |
| Qwen2.5-3B / Llama-3.2-3B | FP16 | ~7GB | ○ |
| **Llama-3.1-8B-Instruct-AWQ** | **INT4** | **~5GB** | **◎ 가장 균형** |
| 7~8B | FP16 | 15GB | ✕ |

### 측정 포인트 (1주차 CH1~2 연결)

[`05-week1-prep.md`](../05-week1-prep.md) §5의 "스터디 중 확인할 질문"을 그대로 실험으로 바꿀 수 있습니다.

```bash
# 서버측 메트릭 — 클라이언트 왕복 지연이 섞이지 않음
curl -s localhost:8000/metrics | grep -E 'time_to_first_token|time_per_output_token|num_requests'
```

| 재볼 것 | 확인되는 것 |
|---|---|
| 프롬프트 길이 ↑ → TTFT | prefill이 compute bound |
| 출력 길이 ↑ → 토큰당 지연 | decode는 입력 길이와 무관 |
| `--max-num-seqs` 스윕 | 배칭의 처리량 ↔ TTFT 교환 |
| 동시 요청 ↑ → OOM 지점 | **KV cache가 동시성 상한을 정한다** |

Llama-3.1-8B(32층, KV헤드 8, head_dim 128, FP16) 기준 **토큰당 KV = 128 KB**입니다. KV에 5GB를 주면 총 4만 토큰 ≈ 요청당 2048토큰일 때 동시 20요청. 실측 OOM 지점과 이 계산을 맞춰보는 것이 과제의 핵심이 됩니다.

---

## 9. 원문 대비 재현 불가 항목

정직하게 정리합니다. **뒷주차 주제 중 이 환경에서 안 되는 것들:**

| 항목 | 왜 |
|---|---|
| **MIG** (GPU 분할) | 하드웨어 기능. 데이터센터 GPU(A100/H100)에만 있고, GeForce는 애초에 미지원 |
| **NVIDIA GPU Operator** | 드라이버 컨테이너를 올리려 하는데 WSL2는 드라이버를 직접 관리하지 않음 |
| **NVLink / NCCL 멀티 GPU** | GPU 1장. [`nccl-communication.md`](./nccl-communication.md)는 읽기 전용 |
| **HAMi GPU 가상화** | [`hami-gpu-virtualization.md`](./hami-gpu-virtualization.md)의 전제가 베어메탈 |
| **DCGM 프로파일링 메트릭** | §7 참조 |
| **PCIe 대역폭 측정** | 패스스루가 아니라 GPU-PV |

→ 이 항목들이 필요해지는 시점(4~6주차)에는 클라우드 GPU 인스턴스나 Colab으로 옮기세요. [`01-environment-setup.md`](../01-environment-setup.md)

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| WSL에서 `nvidia-smi` 실패 | Windows 드라이버 미설치 또는 구버전. Windows에서 먼저 `nvidia-smi` 확인 |
| CUDA 설치 후 GPU가 죽음 | `cuda` 메타패키지로 리눅스 드라이버가 깔린 것. `sudo apt-get remove --purge '^nvidia-.*'` 후 `cuda-toolkit-12-6`만 재설치 |
| `systemctl` 이 "not been booted with systemd" | `/etc/wsl.conf` 설정 후 `wsl --shutdown` 안 한 것 |
| K3s 파드가 GPU를 못 봄 | containerd에 nvidia 런타임 미등록. §4의 `nvidia-ctk runtime configure` 재실행 후 `systemctl restart k3s` |
| Device Plugin이 GPU 0개 보고 | 파드에 `runtimeClassName: nvidia` 누락 |
| vLLM OOM | `--gpu-memory-utilization` 낮추기, `--max-model-len` 줄이기, 더 작은 모델 또는 AWQ |
| 벤치마크 수치가 계속 느려짐 | 발열 스로틀링. `clocks.sm` 확인, 워밍업 후 측정, 어댑터 연결 |
| WSL이 RAM을 다 먹음 | `%USERPROFILE%\.wslconfig`의 `memory=` 설정 |

---

## 출처

- 실습 구조·개념 설명: 노션 서브페이지 [(따라하며 확인하는) PC에 GPU 설정 및 사용 by Docker / K8S](https://gasidaseo.notion.site/PC-GPU-by-Docker-K8S-39750aec5edf806d8070d580fac38917) (멤버 전용)
- 원문 요약본: [`gpu-setup-docker-k8s.md`](./gpu-setup-docker-k8s.md)
- 참고 자료: [GPU-Enabled Platforms on Kubernetes](../references/pdfs.md) CH1 Foundations
- WSL2 관련 명령·제약: 개인 정리 (원문에 없는 내용)

> ⚠️ 원문 노션은 외부 공개·전파 금지입니다. 이 문서는 개인 학습용 재구성이며 그대로 외부에 공개하지 마세요. → [`03-study-rules.md`](../03-study-rules.md)
