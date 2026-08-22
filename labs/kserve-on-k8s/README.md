# KServe on k3s — vLLM 서빙과 그 짝

3주차 「서빙 최적화, 설정부터 만지면 안 되는 이유」의 **계층 비용 짝 ③** 입니다.

목적은 하나입니다. **KServe라는 계층이 처리량에서 얼마를 가져가는가.** 그러려면 KServe만 다르고 나머지는 같은 두 구성이 필요합니다.

| 파일 | 무엇 |
|---|---|
| `isvc-qwen.yaml` | KServe `InferenceService` — `kserve-vllmserver` 런타임 |
| `vllm-v0200-direct.yaml` | **짝** — 같은 이미지·같은 인자, KServe 없이 Deployment 하나 |

두 구성 다 `vllm/vllm-openai:v0.20.0`을 쓰고 `max_model_len=4096` · `gpu_memory_utilization=0.85` · `max_num_seqs=64`로 맞췄습니다. 짝이 맞았다는 확인은 기동 로그가 해 줍니다 — 양쪽 모두 `GPU KV cache size: 247,024 tokens` / `Maximum concurrency ... 60.31x`입니다.

## 설치

Istio·Knative가 없는 k3s이므로 **RawDeployment 모드**를 씁니다.

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# 1. cert-manager (KServe 필수 의존)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml
kubectl -n cert-manager wait --for=condition=Available deployment --all --timeout=300s

# 2. KServe — ⚠️ 네임스페이스를 직접 만들어야 한다 (kserve.yaml이 만들지 않는다)
kubectl create namespace kserve
kubectl apply --server-side -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve.yaml

# 3. RawDeployment로 전환 — 기본값은 Serverless라 Istio/Knative 없이는 영원히 Ready=False
kubectl -n kserve patch configmap inferenceservice-config --type merge \
  -p '{"data":{"deploy":"{\"defaultDeploymentMode\":\"RawDeployment\"}"}}'
kubectl -n kserve rollout restart deployment/kserve-controller-manager
kubectl -n kserve rollout status deployment/kserve-controller-manager --timeout=300s

# 4. ServingRuntime 목록 (kserve-vllmserver가 여기 들어 있다)
kubectl apply --server-side -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve-cluster-resources.yaml
kubectl get clusterservingruntime
```

## 배포

```bash
kubectl apply -f isvc-qwen.yaml
kubectl -n llm-serving-lab get isvc qwen -w
```

`READY=True`가 되면 파드 IP로 바로 칩니다. ClusterIP·port-forward 없이 되는 이유는 **KServe가 요청 경로에 없기 때문**입니다 — vLLM 자신의 HTTP 서버가 그대로 노출됩니다.

```bash
POD_IP=$(kubectl -n llm-serving-lab get pod -l serving.kserve.io/inferenceservice=qwen \
  -o jsonpath='{.items[0].status.podIP}')
curl -s "http://$POD_IP:8080/v1/models"
```

## 측정

```bash
cd ../wsl2-vllm-baseline
python3 benchmark.py --base-url "http://$POD_IP:8080" \
  --scenarios short --concurrency 1,2,4,8,16,32,64 \
  --requests-per-level 100 --warmup 1 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 \
  --output results/c3-kserve-vllm-seqs64.json
```

GPU가 한 장이므로 짝을 재려면 KServe를 먼저 내립니다.

```bash
kubectl delete -f isvc-qwen.yaml
# nvidia-smi로 VRAM 반환 확인 후
kubectl apply -f vllm-v0200-direct.yaml
```

## 결과 (c=64, 각 지점 100요청 1회)

| 구성 | 처리량 | TTFT p95 | goodput | `vllm:*` 메트릭 |
|---|---|---|---|---|
| 짝 (KServe 없음) | 2,714.2 tok/s | 0.296s | 100% | 66개 |
| KServe | 2,654.0 tok/s | 0.310s | 100% | **66개 (그대로)** |
| **차이** | **−2.2%** | — | — | — |

동시성 1~32에서는 부호가 왔다 갔다 합니다(+0.2% ~ +6.6%). **잡음과 구별되지 않는 수준**이고, 그게 이 계층의 성격입니다.

## 막히는 곳 다섯

전부 겪었고 매니페스트 주석에 남겨 뒀습니다.

1. **네임스페이스** — `kserve.yaml`이 만들지 않습니다. 먼저 `kubectl create namespace kserve`.
2. **기본 모드가 Serverless** — Istio·Knative가 없으면 `Ready=False`에서 멈춥니다. 위 3번으로 전환.
3. **번들 런타임과 이미지 불일치** — `kserve-vllmserver`는 `python`을 실행하는데 `vllm/vllm-openai:v0.20.0`에는 `python3`만 있습니다.
   ```
   exec: "python": executable file not found in $PATH
   ```
   `command`를 덮어씁니다. 같은 맥락으로 vLLM 0.20.0에는 `--disable-log-requests`가 없습니다(→ `--no-enable-log-requests`).
4. **HF 캐시 심볼릭 링크** — `snapshots/<hash>/` 안의 파일은 `../../blobs/<sha>`를 가리키는 링크입니다. 그 폴더만 `storageUri`로 가리키면 subPath 마운트가 링크를 끊습니다.
   ```
   Invalid repository ID or local directory specified: '/mnt/models'
   ```
   **캐시 루트째 마운트하고 `--model`로 스냅샷 경로**를 줍니다.
5. **`runtimeClassName: nvidia`** — WSL2 k3s에서 GPU 파드에 필수입니다. 빠지면 `Failed to infer device type`.

그리고 **GPU 1장에서는 롤링 업데이트가 스스로 안 풀립니다.** 새 파드가 GPU를 기다리는데 옛 파드가 쥐고 있어 교착합니다.

```bash
# 최신 리비전이 아닌 ReplicaSet을 0으로 내린다
kubectl -n llm-serving-lab get rs -l serving.kserve.io/inferenceservice=qwen
kubectl -n llm-serving-lab scale rs/<옛-rs> --replicas=0
```

## 참고

- [KServe — Raw Kubernetes Deployment](https://kserve.github.io/website/latest/admin/kubernetes_deployment/)
- 측정 원본: `../wsl2-vllm-baseline/results/c3-kserve-vllm-seqs64.json` · `b-direct-v0200-seqs64.json` · `metrics-kserve.txt` · `metrics-direct-v0200.txt` · `b-direct-v0200-startup.txt`
