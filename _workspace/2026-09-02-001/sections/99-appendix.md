## 부록

### 부록 A. 예산 동결 팔을 만드는 방법

KV 예산은 정적 공식이 아니라 **vLLM이 기동할 때 실제로 프로파일링해서 정하는 값**입니다. 가중치 크기가 달라지면 남는 메모리도 달라지므로, `gpu_memory_utilization`을 계산만으로 맞출 수 없습니다.

그래서 목표값을 겨냥해 재기동하는 방식으로 찾았습니다. 현재 예산과 목표 예산의 차이를 `util`에 대한 기울기로 나눠 다음 값을 정하고, 다시 재서 남은 오차를 줄입니다.

```bash
# 기동 로그에서 Maximum concurrency 숫자만 꺼낸다
read_conc() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' \
    | tail -1 | grep -oE '[0-9.]+x$' | tr -d 'x'
}
```

세 번 만에 오차 2.4%로 들어왔습니다. ±5%라는 기준은 4주차에 쓰던 것을 그대로 가져왔습니다.

한 가지 짚어 둘 것이 있습니다. 6장에서 적었듯 **예산 차이는 이 구간에서 처리량을 움직이지 않으므로**, ±5%로 맞추지 않았어도 결론은 같았을 것입니다. 그래도 맞춘 이유는 제거 실험의 성격 때문입니다 — *"예산이 달라서 그런 것 아니냐"* 는 반론을 데이터로 미리 닫아 두려면, 예산이 실제로 중요한지와 무관하게 **같은 자리에 놓고** 재는 편이 낫습니다.

### 부록 B. 왜 FP8을 골랐나

설계 단계에서는 FP8 → GPTQ → AWQ를 한 번씩 시도하기로 했는데 첫 번째에서 끝났습니다.

`--quantization fp8`은 **BF16 체크포인트를 기동 시점에 W8A8로 바꿉니다.** 사전 양자화된 별도 체크포인트를 받지 않으므로,

- 추가 다운로드가 0이고,
- 모델 파일·이미지·실행 경로가 BF16 팔과 완전히 같으며,
- 팔 사이에서 달라지는 것이 **가중치 정밀도 하나**로 좁혀집니다.

세 번째가 중요합니다. 사전 양자화 체크포인트를 쓰면 양자화 방식뿐 아니라 **캘리브레이션 데이터와 레이어별 적용 범위**까지 함께 달라져, 관측된 차이를 무엇에 귀속시킬지가 다시 흐려집니다.

RTX 4080은 Ada 세대라 FP8 텐서코어를 갖고 있습니다. 그보다 이전 세대 GPU에서는 이 경로가 그대로 재현되지 않습니다.

### 부록 C. 재현 절차

```bash
# 공통 — 2주차 기준선과 같은 k3s 배포. 이미지는 containerd에 이미 있는 것을 쓴다
# (docker run으로 받으면 ~10GB를 새로 받고, 2주차와 다른 저울이 된다).
kubectl apply -f k8s/vllm-baseline.yaml
source redeploy.sh

# F1a — KV 예산 스윕. 배포 한 번에 두 워크로드를 이어 잰다.
./run_f1a2.sh          # util 0.45 ~ 0.85, decode c=16 + prefill c=64(--unique-prefix)

# F1b — 제거 실험. 예산 동결 팔의 util은 스크립트가 찾는다.
./run_f1b.sh           # bf16 / quant / quant-frozen, 팔마다 3회

# F1c — 워크로드 격자. 4주차 E1과 같은 격자다.
./run_f1c.sh           # prefill,decode x c=1,4,16,64, 팔마다 2회

# F1d — 예산을 더 내려 꺾이는 점을 찾는다. 부하 중 서버 지표를 0.4초 간격으로 모은다.
./run_f1d.sh           # util 0.33 ~ 0.85, prefill c=64

# F2 — PyTorch Profiler. v0.23.0에서는 환경 변수가 아니라 --profiler-config.* 를 줘야
# /start_profile 이 열린다(5장 참조). 스크립트가 그 플래그를 붙인다.
./run_f2.sh

# F5 — 대시보드 증거용 부하. 구간마다 3분씩 태워 15초 스크랩에 남긴다.
./run_f5.sh
```

`prefill` 스윕에 `--unique-prefix`가 붙는 이유가 있습니다. 요청 프롬프트가 전부 같으면 prefix caching이 이를 하나로 합쳐 **KV 수요가 1/64로 줄어듭니다.** 예산이 실제로 걸리는지 보려면 그 합치기를 먼저 막아야 합니다.

### 부록 D. 지표 하나를 잘못 읽을 뻔했다

예산이 실제로 걸렸는지 확인하려고 서버 지표를 0.5초 간격으로 긁었는데, 첫 시도에서 수집 파일이 전부 비어 있었습니다. 필터를 이렇게 썼기 때문입니다.

```bash
grep -E '^vllm:(num_requests_running|kv_cache_usage_perc) '   # 이름 뒤에 공백을 요구
```

실제 노출 형식은 이름 뒤에 라벨 블록이 붙습니다.

```
vllm:num_requests_running{engine="0",model_name="qwen2.5-1.5b"} 16.0
```

**빈 파일은 "지표가 0"이 아니라 "안 잡혔다"였습니다.** 4주차에도 `vllm:iteration_tokens_total`을 스텝당 스케줄된 토큰으로 잘못 읽은 적이 있어, 지표를 근거로 쓸 때는 값을 보기 전에 **행이 실제로 잡혔는지**부터 확인하기로 했습니다.

같은 종류의 실수가 이 글에서 두 번 더 있었습니다. 하나는 5장의 트레이스를 처음에 **총합끼리** 비교한 것입니다 — 그러면 FP8이 시간을 24% 더 쓴 것으로 읽히는데, 두 트레이스가 담은 구간이 58스텝과 98스텝이라 그렇습니다. 다른 하나는 5-B장의 대시보드를 **되짚어 찍으려던 것**입니다 — 15초 스크랩으로는 10초짜리 버스트의 피크가 남지 않아, KV 사용률 0.998이 기록에는 0.078로만 있었습니다.

셋 다 원인이 같습니다 — **숫자를 보기 전에 그 숫자가 무엇을 세고 있는지, 어떤 간격으로 세는지 확인하지 않은 것**입니다.

---

## 참고 자료

- CH9 *LLM Optimization in Practice* — 이 글의 질문("처리량이 올랐다는 건 GPU가 더 빨리 계산해서인가, 덜 다시 계산해서인가")과, 양자화 전후 GEMM 커널 시간이 거의 같았다는 관측
- CH10 *Advancements in LLM Serving* — Nsight Systems → PyTorch Profiler → Nsight Compute의 계층적 좁히기 순서
- [vLLM 문서 — Quantization](https://docs.vllm.ai/en/latest/features/quantization/index.html)
- [vLLM 문서 — Profiling vLLM](https://docs.vllm.ai/en/latest/contributing/profiling.html)
- 이 저장소의 측정 원본 — `labs/wsl2-vllm-baseline/results/f*` 및 분석 `f-analysis.md`
