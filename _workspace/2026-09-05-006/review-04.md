**지표와 프로파일러의 설명이 맞는지 대조합니다.** 처리량·ITL로 차이를 확인한 뒤 커널 집계의 단위와 수집 구간을 확인합니다. 운영 도입 전에는 응답 품질도 별도로 평가합니다.

남는 메모리가 곧 처리량 증가의 원인은 아니었습니다. 다음 검증은 같은 작업량의 트레이스를 다시 집계해, 가중치를 읽는 비용과 계산 경로의 변화를 구분하는 것입니다.

</details>

<details>
<summary>지난주 결과를 함께 보면 어디까지 해석할 수 있을까</summary>

[지난 글](./켜면%20이득인%20최적화는%20없다.md)의 추측 디코딩 결과를 KV 수용량 축에 함께 놓은 참고 그림입니다. 본문 핵심 비교와 달리 서로 다른 실험 시점의 결과를 포함합니다.

![decode 동시성 16의 BF16 KV 스윕과 FP8 두 구성, 4주차 ngram 및 draft 결과를 함께 표시한 참고 그래프](./figures/fig-f1-kv-budget-curve.svg)

*이 그림에는 decode c=16만 있습니다. prefill 결과를 그린 그래프가 아닙니다. 가로축은 기동 로그의 Maximum concurrency이며 실제 동시 실행 요청 수가 아닙니다.*

| 구성 | Maximum concurrency | decode c=16 (tok/s) | 선에서 벗어난 방향 |
| --- | --- | --- | --- |
| BF16 기준 | 59.50x | 1,689.3 | 선 위 |
| FP8 기본 | 70.20x | 2,258.8 | **위로** |
| FP8 · KV 예산 축소 | 60.95x | 2,261.0 | **위로** |
| 4주차 ngram | 57.48x | 1,356.2 | **아래로** |
| 4주차 draft-0.5B | 34.38x | 825.7 | **아래로** |

BF16 스윕에서는 예산을 바꿔도 영향이 작았습니다. 이 결과에 비추어 보면 지난주 draft 구성이 느려진 이유를 KV 예산 감소만으로 설명하기는 어렵습니다. draft 모델을 쓰면 연산과 스케줄링도 함께 달라집니다. BF16 스윕만 보고 draft 구성에서 KV의 기여도가 정확히 0이라고 확정할 수는 없습니다.

지난주에는 KV 예산이 42% 줄었다는 이유로 비교를 유보했습니다. 이번에는 예산 차이가 얼마나 영향을 주는지부터 쟀습니다. 성능 손해 전부가 추측 디코딩 때문인지 확인하려면 draft 구성에서도 예산을 맞춰 비교해야 합니다.

</details>

<details>
<summary>재현에 필요한 자료와 실행 순서</summary>

**재현 가능 범위**

현재 저장소에는 기준선 배포 매니페스트, `redeploy.sh`, `benchmark.py`가 있습니다. 반면 원고가 참조하던 `results/f*`, `f-analysis.md`, `run_f1a2.sh`, `run_f1b.sh`, `run_f1c.sh`, `run_f1d.sh`, `run_f2.sh`, `run_f5.sh`는 현재 체크아웃에 없습니다. 아래 명령은 같은 대조 실험을 새로 구성하는 예시입니다. 기존 측정값을 그대로 재생하지는 못합니다. 수치를 직접 대조하려면 원래의 요청 수·입력·반복별 결과가 필요합니다.

로컬 실행 자산과 환경 준비는 [WSL2·K3s vLLM 기준선 실습](../labs/wsl2-vllm-baseline/README.md)에 있습니다. GPU와 k3s가 준비된 측정 머신에서 저장소 루트를 기준으로 시작합니다. 기존 실습과 같은 containerd 이미지·모델 캐시를 사용합니다.

```bash
cd labs/wsl2-vllm-baseline
source redeploy.sh

# 모델과 입력·출력 조건을 고정한 상태에서 BF16 기준 구성으로 재배포
redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=4096 \
  GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''

# 새로 측정할 때의 예시. 100은 이 예시의 요청 수이며 원실험 값이 아니다.
python3 benchmark.py --scenarios decode --concurrency 16 \
  --requests-per-level 100 --output results/recheck-bf16-1.json

# FP8 기본 구성. 재배포 성공과 기동 로그를 확인한 뒤 같은 부하를 실행
redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=4096 \
  GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS='--quantization fp8'
python3 benchmark.py --scenarios decode --concurrency 16 \
  --requests-per-level 100 --output results/recheck-fp8-1.json
```

구성마다 예열 후 반복 측정합니다. 세 번째 구성은 FP8을 유지하면서 `GPU_MEMORY_UTILIZATION`을 조절해 BF16의 실제 KV 예산에 가깝게 맞춥니다. 다른 장비에서는 이 글의 0.7656을 그대로 쓰지 않고 예산을 다시 맞춥니다. 기동 로그에서 다음 두 항목을 확인합니다.

```plain text
GPU KV cache size: 243,696 tokens
Maximum concurrency for 4,096 tokens per request: 59.50x
```
프리필의 KV 수요를 비교할 때는 요청끼리 같은 접두사를 공유하는지도 맞춰야 합니다. 이 실습의 `--unique-prefix` 옵션은 요청마다 식별자를 붙입니다. 접두사 재사용의 영향을 줄이려는 용도입니다. 프롬프트, 성공 요청 수, 실제 생성 토큰 수를 결과와 함께 보관합니다. 스트리밍 응답의 usage가 수집됐는지도 기록합니다.

**후속 검증 순서**

우선 F1b의 반복별 원시 결과와 F2 트레이스·집계 코드를 복구해야 합니다. 커널 시간을 무엇으로 나눴는지, 이벤트가 중복되거나 실행이 겹쳤는지, 실제 배치는 얼마나 컸는지 확인합니다. 새 실험을 하지 않아도 기존 집계의 문제를 풀 수 있습니다.

BF16·FP8의 배치와 생성 길이를 같게 맞춘 뒤 프로파일링을 반복하면 커널 경로의 차이를 더 분명하게 살펴볼 수 있습니다. 메모리 대역폭 때문인지 확인하려면 Nsight Systems에서 실행 구간을 먼저 봅니다. 이어 Nsight Compute로 해당 커널의 메모리·연산 지표를 대조해야 합니다. 프로파일러를 켠 실행의 처리량은 일반 벤치마크와 분리합니다.

운영 도입을 판단하려면 응답 품질도 확인해야 합니다. 실제 사용할 과제를 대표할 입력과 평가 기준을 고정합니다. 이 조건으로 BF16·FP8을 비교해 성능 이득과 품질 변화를 함께 기록합니다. 추가 모델의 결과를 많이 나열하기보다 이 비교를 갖추면 실제 도입을 판단하는 데 도움이 됩니다.

</details>

## 기록의 범위와 출처

이 글에는 기존 측정 기록을 다시 정리했습니다. 표와 화면에서 그 근거를 확인할 수 있습니다. 현재 체크아웃에는 5주차 원시 결과·트레이스·자동 실행 스크립트가 없습니다. 이번 개정에서는 남은 기록끼리 계산과 출처를 대조했습니다. GPU 실험을 새로 실행하지는 않았습니다.

<details>
<summary>참고 자료</summary>

- *LLM Optimization in Practice* (CH9) — 하드웨어·트래픽·평가 지표를 정한 뒤 기준선과 최적화 구성을 비교하는 실습. Qwen3-14B AWQ 사례와 스터디의 별도 RTX·Qwen3-4B Nsight 참고 실습을 구분했습니다.
- *Advancements in LLM Serving* (CH10) — 서비스 지표와 프로파일러를 대조해 병목을 좁히는 접근. 시맨틱 라우팅·멀티모달·엣지·Multi-LoRA·강화학습 서빙은 이번 글의 실험 범위에 포함하지 않았습니다.
- [vLLM v0.23.0 — FP8 W8A8와 온라인 양자화](https://docs.vllm.ai/en/v0.23.0/features/quantization/llm_compressor/fp8/) — 가중치·활성화 정밀도와 온라인 양자화 경로.
- [vLLM v0.23.0 — ProfilerConfig](https://docs.vllm.ai/en/v0.23.0/api/vllm/config/profiler/) — 수집 지연·iteration 상한 등 프로파일러 설정.
- 자체 실험 기록 — 본문과 상세 영역의 결과표, Prometheus 원본 화면. 5주차 원시 결과와 트레이스는 현재 검토본에 포함되지 않았습니다.

</details>



