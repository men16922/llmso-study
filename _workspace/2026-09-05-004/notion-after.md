**FP8을 켜자 처리량이 33.7% 늘었습니다. 늘어난 KV 캐시 공간을 다시 줄여도 이득은 남았습니다.** 동시에 실행한 요청 수는 같았고 토큰 간 간격은 짧아졌습니다. 이 글은 그 차이를 대조 실험과 프로파일링으로 좁혀 간 기록입니다.
CloudNet@ LLMSO 스터디 5주차 과제로, CH9의 실전 최적화와 CH10의 성능 프로파일링을 연결했습니다. 실험 환경은 **RTX 4080 Laptop 12GB·Qwen2.5-1.5B·vLLM v0.23.0**입니다. 두 장의 전체 내용을 요약하기보다, 양자화로 얻은 성능 향상의 원인 하나를 깊이 살펴봤습니다.
## 1. 양자화가 빨라지는 두 경로
양자화를 켜면 모델이 차지하는 메모리가 줄어듭니다. 남는 공간에 더 많은 요청을 담을 수 있고, 가중치를 읽고 계산하는 경로도 바뀔 수 있습니다. 처리량이 올랐다는 사실만으로는 어느 변화가 효과를 냈는지 알기 어렵습니다.
여기서 **KV 예산**은 이전 토큰의 계산 결과를 보관할 수 있는 캐시 용량입니다. **ITL**은 사용자가 받는 토큰 사이의 시간 간격이고, **GEMM**은 모델의 선형 계층에서 수행하는 행렬 곱셈입니다. BF16과 FP8은 각각 16비트와 8비트 부동소수점 형식입니다.
![FP8 양자화의 두 후보 경로. KV 캐시 공간 증가와 토큰 처리시간 단축을 나누고 예산 축소 실험으로 확인한다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/2799733d-e98b-4d96-b982-c7c516718f01/fig-w5-fp8-paths.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666BGUS6G2%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T061520Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjED0aCXVzLXdlc3QtMiJGMEQCIDqaItC9CO0khx6ARLIpIEjX%2Feq3N0FUz6VNbWbzaD04AiAeoDiSIo2qTo0qTXLEzq5ZraEz0Ze%2FmG6l7z3INlPXbCr%2FAwgGEAAaDDYzNzQyMzE4MzgwNSIMTUAkW7rqV9l7wMaXKtwDOHAQ5uEbAhu3vhr%2FZAWDoK%2FY%2FLUmP7Pkm279C3Nw3LERIT6lqAi61FH84BFzsYUNbTDn2WOW5gDfj0Ewxvpfg4gJRKWwaHJBeNp0MhQuYwBsNNZpp6wnVnf%2F6gQ1MeLP9fxkiXiIcy6vnEmjcidnJzDrcvY%2BFDizsgnbT4DaNLIpjBp%2FATmP74mEFDJK%2Fz4l63cqkArS7TKXnvNNKnuyCeeqM9zSBPyYGAY8lztwAg0wqwZuC6VlQBe3d6k1TKulBvYM%2FQ4A6fxStDdCGS7dcRpWKhWl1pGzFGWC%2BeqT%2Fz8WeqWGRSYVI%2Fsp8E7YR83dKZEIiHegmmW54CL8ux0Ew9aBG9CK4oHQOvFMzMOLsvCaCZ7MWJ9mr9bNSvQvZOJN1WNo7T6kcXAv2zRNVIZgueaaTF3MCjuDegafqg4DRNoY%2BWVsYhZXKCvk%2BHIpkYQvqWDfijRpiI0jxnmjHCmpjEYk7iedlJ0dMFthQ4id%2Fx2iZ9DkFckG25F15iI0IDxJkYsZqXzLUc8i3tDzgNwgPaZQGVfHwFfJ%2F8pOiIWC7jCxyVGtHabSWJwZnSdrhPeOd0kJVs5qey5D1t%2FV2SWx9EL52TrqRrYasDVlu9tfCCv80gURdnhN%2BACu%2BXIws7nu1AY6pgECgFK4IuODH65h%2BZsMDjjwN6PzqE0hviCbs6514Z2xx6Q9hdJ%2B6BRpD9dJ1J9P4Arn1TmsmlrghXmjaFWqVxGenCwdQl4CTWGGFET%2Fv0KWZKHcpImkS0xqTN3K6MG%2FtC64dVIZEw9WoZ9T64TY%2BfPxLTc4vdJ8qSdhva0pGDyDnfgH7ToZmaaUe%2BUqUQ6H8DkzEy37mrCulh3KJJnmOk%2BLlZG3Zu40&X-Amz-Signature=0666a836659ee8660a0a3fae42d4dfae0998a45aa4e75c1666d9f68a4f706f94&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*두 경로는 함께 작동할 수 있습니다. 이번에는 KV 예산 증가가 반드시 필요했는지부터 확인했습니다.*
CH9의 Qwen3-14B AWQ 사례에서는 모델 메모리를 줄여 KV 캐시를 확보한 뒤 처리량이 2.7배 늘었습니다. 같은 스터디 자료의 RTX 4070 계열·Qwen3-4B 참고 실습에는 별도의 Nsight 분석이 있습니다. 모델과 측정 조건이 다른 두 사례를 하나의 결과로 합치지는 않았습니다.
제 실험은 GPU·모델·양자화 방식이 모두 다릅니다. 교재 사례를 그대로 재현하거나 반박하는 대신, **내 환경에서도 늘어난 KV 예산이 이득의 원인인지** 확인했습니다.
## 2. KV 예산을 되돌려도 이득은 남았다
비교의 중심은 세 구성입니다. BF16 기준 구성, FP8 기본 구성, 그리고 FP8을 유지한 채 KV 예산을 BF16에 가깝게 줄인 구성입니다. 세 구성 모두 짧은 입력에서 최대 512토큰을 생성하는 `decode` 워크로드를 동시성 16으로 실행했습니다.
![BF16 1689.3, FP8 2258.8, KV 예산을 줄인 FP8 2261.0 tok/s. 세 구성의 처리량 평균과 표준편차 비교](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/4d15b37c-947c-42f6-b502-29b34c55f85d/fig-w5-fp8-ablation.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666BGUS6G2%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T061520Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjED0aCXVzLXdlc3QtMiJGMEQCIDqaItC9CO0khx6ARLIpIEjX%2Feq3N0FUz6VNbWbzaD04AiAeoDiSIo2qTo0qTXLEzq5ZraEz0Ze%2FmG6l7z3INlPXbCr%2FAwgGEAAaDDYzNzQyMzE4MzgwNSIMTUAkW7rqV9l7wMaXKtwDOHAQ5uEbAhu3vhr%2FZAWDoK%2FY%2FLUmP7Pkm279C3Nw3LERIT6lqAi61FH84BFzsYUNbTDn2WOW5gDfj0Ewxvpfg4gJRKWwaHJBeNp0MhQuYwBsNNZpp6wnVnf%2F6gQ1MeLP9fxkiXiIcy6vnEmjcidnJzDrcvY%2BFDizsgnbT4DaNLIpjBp%2FATmP74mEFDJK%2Fz4l63cqkArS7TKXnvNNKnuyCeeqM9zSBPyYGAY8lztwAg0wqwZuC6VlQBe3d6k1TKulBvYM%2FQ4A6fxStDdCGS7dcRpWKhWl1pGzFGWC%2BeqT%2Fz8WeqWGRSYVI%2Fsp8E7YR83dKZEIiHegmmW54CL8ux0Ew9aBG9CK4oHQOvFMzMOLsvCaCZ7MWJ9mr9bNSvQvZOJN1WNo7T6kcXAv2zRNVIZgueaaTF3MCjuDegafqg4DRNoY%2BWVsYhZXKCvk%2BHIpkYQvqWDfijRpiI0jxnmjHCmpjEYk7iedlJ0dMFthQ4id%2Fx2iZ9DkFckG25F15iI0IDxJkYsZqXzLUc8i3tDzgNwgPaZQGVfHwFfJ%2F8pOiIWC7jCxyVGtHabSWJwZnSdrhPeOd0kJVs5qey5D1t%2FV2SWx9EL52TrqRrYasDVlu9tfCCv80gURdnhN%2BACu%2BXIws7nu1AY6pgECgFK4IuODH65h%2BZsMDjjwN6PzqE0hviCbs6514Z2xx6Q9hdJ%2B6BRpD9dJ1J9P4Arn1TmsmlrghXmjaFWqVxGenCwdQl4CTWGGFET%2Fv0KWZKHcpImkS0xqTN3K6MG%2FtC64dVIZEw9WoZ9T64TY%2BfPxLTc4vdJ8qSdhva0pGDyDnfgH7ToZmaaUe%2BUqUQ6H8DkzEy37mrCulh3KJJnmOk%2BLlZG3Zu40&X-Amz-Signature=67b3bf5e41e2de4d4244b658fd5f443f12baff226313dfe9b500eb86ac6ccf8c&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*막대는 구성별 3회 측정 평균, 오차 막대는 ±1σ입니다. KV 예산을 줄인 뒤에도 FP8 두 구성의 처리량은 비슷했습니다.*
<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>KV 수용량 지표</td>
<td>처리량 (tok/s)</td>
<td>ITL p50 (ms)</td>
</tr>
<tr>
<td>BF16 기본</td>
<td>59.50x</td>
<td>1,689.3</td>
<td>9.7</td>
</tr>
<tr>
<td>FP8 기본</td>
<td>70.20x</td>
<td>2,258.8</td>
<td>7.3</td>
</tr>
<tr>
<td>FP8 · KV 예산 축소</td>
<td>60.95x</td>
<td>2,261.0</td>
<td>7.3</td>
</tr>
</table>
KV 수용량 지표는 기동 로그의 `Maximum concurrency`입니다. 최대 길이 4,096토큰인 요청을 기준으로 용량을 환산한 값입니다. 실제 실행 중인 요청 수와는 다릅니다. 예산 축소 구성은 기준보다 **2.4% 큰 수준**까지 맞췄습니다. 완전히 같은 예산은 아닙니다.
FP8 기본의 처리량 이득은 **+33.7%**, 예산을 줄인 구성은 **+33.8%**였습니다. 둘의 평균 차이는 약 0.1%로 각 구성의 반복 측정 변동보다 작았습니다. 이 조건에서는 늘어난 KV 예산을 줄여도 처리량 이득이 사라지지 않았습니다. 다만 3회 측정과 예산 오차만으로 기여도를 정확히 0%라고 단정할 수는 없습니다.
이를 뒷받침하는 별도 실험도 있습니다. BF16에서 KV 예산만 64,048→243,696토큰으로 **3.80배** 늘렸지만, 같은 `decode` 부하의 처리량 변동은 약 **0.5%**였습니다. 예산이 늘수록 빨라지는 추세는 없었습니다. 짧은 입력과 동시 요청 16개에 필요한 KV 공간은 가장 작은 구성에도 충분했습니다.
## 3. 같은 요청 수에서 토큰 간격이 짧아졌다
ITL p50은 9.7ms에서 7.3ms로 **24.7%** 줄었습니다. 처리량만 오른 것이 아니라 사용자에게 토큰이 도착하는 간격도 짧아졌습니다. ITL에는 서버 밖의 지연도 포함되므로 이 값만으로 GPU의 어느 연산이 빨라졌다고 판단하지는 않았습니다.
Prometheus에서도 BF16과 FP8에 같은 `decode` 부하를 3분씩 가했습니다. 두 구간 모두 실행 요청 16개, 대기 요청 0개, 선점 0회였습니다. 생성 처리량은 **1,703.6→2,269.3 tok/s(+33.2%)**로 늘었습니다. 이 관측은 더 많은 요청을 동시에 실행해서만 얻은 이득이라는 설명과 맞지 않습니다.
그다음 PyTorch Profiler로 커널 시간을 살펴봤습니다. CH10의 프로파일링은 서비스 지표, 실행 타임라인, 개별 커널을 대조하며 병목을 좁히는 접근입니다. 이번 환경에는 Nsight 바이너리가 없어 PyTorch Profiler와 Prometheus까지만 사용했습니다.
기록된 GPU 커널 시간의 총합은 BF16이 503.1ms, FP8이 622.8ms였습니다. FP8이 더 길어 보이지만 수집한 스텝 수가 달랐습니다. 기록에 남은 58스텝과 98스텝으로 각각 나눠 봤습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>비교 기준</td>
<td>BF16</td>
<td>FP8</td>
</tr>
<tr>
<td>GPU 커널 시간 합계</td>
<td>503.1ms</td>
<td>622.8ms</td>
</tr>
<tr>
<td>기록된 스텝 수</td>
<td>58</td>
<td>98</td>
</tr>
<tr>
<td>합계 ÷ 스텝 수</td>
<td>**8.67ms**</td>
<td>**6.36ms**</td>
</tr>
</table>
**기록된 스텝 수로 환산한 커널 시간 합계는 약 26.7% 줄었습니다.** ITL의 감소 방향과도 같습니다. 다만 커널 시간의 합계는 중첩 실행이나 CPU 대기까지 반영한 실제 스텝의 경과시간과 같지 않습니다.
기존 역할별 집계에서는 GEMM 감소가 두드러졌습니다. 그러나 표의 ‘스텝당’ 값이 위 계산보다 약 28배 작아, 레이어 수까지 나눈 집계로 추정됩니다. 원본 트레이스와 집계 코드가 현재 검토본에 없어 역할별 수치는 부록에 보존하고 잠정 근거로만 취급했습니다.
여기까지의 근거로는 **KV 예산 증가만으로 설명되지 않는 처리시간 단축**이 있었다고 해석할 수 있습니다. 가중치 읽기 비용과 FP8 계산 경로가 후보입니다. W8A8은 가중치뿐 아니라 활성화도 8비트로 처리하므로, 이득 전부를 메모리 대역폭에 돌리려면 추가 계측이 필요합니다. [vLLM의 FP8 W8A8 설명](https://docs.vllm.ai/en/v0.23.0/features/quantization/llm_compressor/fp8/#online-dynamic-quantization)
## 4. KV 예산이 부족하면 결과가 달라진다
앞의 결과가 KV 캐시 용량은 중요하지 않다는 뜻은 아닙니다. 긴 입력을 처리하는 `prefill` 부하에서 예산을 더 낮추자 처리량이 떨어졌습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>BF16 구성</td>
<td>KV 예산</td>
<td>프롬프트 처리량 (tok/s)</td>
<td>TTFT p50</td>
<td>선점</td>
</tr>
<tr>
<td>util 0.85</td>
<td>243,696토큰</td>
<td>12,686</td>
<td>4.448초</td>
<td>0회</td>
</tr>
<tr>
<td>util 0.33</td>
<td>10,144토큰</td>
<td>8,306</td>
<td>7.679초</td>
<td>4회</td>
</tr>
</table>
이 비교는 `prefill` 동시성 64에서 입력 토큰 처리량을 잰 별도 실험입니다. 앞의 `decode` 생성 처리량과 직접 비교하지 않습니다. 예산이 부족한 구성에서는 프롬프트 처리량이 **34.5% 감소**했고 첫 토큰까지 기다리는 시간은 약 **1.7배**가 됐습니다.
KV 사용률만으로는 이런 상태를 구분하기 어려웠습니다. 중간 구성인 `util=0.45`는 사용률이 0.995까지 올라도 처리량이 유지됐습니다. 사용률과 함께 선점 증가, 대기 요청, TTFT를 봐야 합니다. 선점이 없다는 이유만으로 모든 병목이 사라졌다고 판단할 수도 없습니다.
프리필·디코드와 동시성 1·4·16·64를 조합한 별도 비교에서는 FP8의 평균 처리량이 여덟 조건 모두 높았습니다. 개선 폭은 **+11.1%\~+35.4%**였으며 높은 동시성에서 작아졌습니다. 다만 구성별 2회 측정이고 동시성 64는 변동이 커 이 결과를 FP8이 항상 유리하다는 근거로 삼지는 않았습니다.
이 글은 12GB GPU 한 장과 1.5B 모델에서 얻은 성능 기록입니다. **응답 품질은 평가하지 않았고, Nsight Compute로 메모리 대역폭과 연산 병목을 분리하지도 않았습니다.** 더 큰 모델, AWQ·GPTQ·FP4, 다중 GPU에는 별도 측정이 필요합니다.
## 5. 운영에 적용할 때 확인할 것
양자화 전후의 처리량만 비교하면 함께 바뀐 조건을 놓치기 쉽습니다. 이번 실험에서 남긴 확인 순서는 세 가지입니다.
1. **같은 부하에서 비교합니다.** 입력·출력 길이, 동시성, 모델과 서버 설정을 고정하고 반복 측정의 변동을 함께 기록합니다.
2. **원인으로 의심한 조건을 되돌립니다.** KV 예산이 후보라면 FP8을 유지한 채 예산을 줄여 봅니다. 예산이 실제로 부족해졌는지도 선점·대기·TTFT로 확인합니다.
3. **지표와 프로파일러의 설명이 맞는지 대조합니다.** 처리량·ITL로 차이를 확인한 뒤 커널 집계의 단위와 수집 구간을 확인합니다. 운영 도입 전에는 응답 품질도 별도로 평가합니다.
**이번 환경에서는 KV 예산을 BF16 수준에 가깝게 줄여도 FP8의 처리량 이득이 남았고, 토큰 간격도 짧아졌습니다.** 남는 메모리가 곧 처리량 증가의 원인은 아니었습니다. 다음 검증은 같은 작업량의 트레이스를 다시 집계해, 가중치를 읽는 비용과 계산 경로의 변화를 구분하는 것입니다.
---
## 상세 데이터와 재현 안내
본문은 기존 측정 기록을 재정리한 것입니다. 아래 표와 화면은 근거를 확인하기 위한 자료입니다. 현재 검토한 체크아웃에는 5주차 원시 결과·트레이스·자동 실행 스크립트가 없어, 이번 개정에서는 기록 간 산술과 출처를 검증했습니다. GPU 실험을 새로 실행한 결과는 아닙니다.
<details>
<summary>A. 실험 환경과 세 구성의 전체 결과</summary>
	<table fit-page-width="true" header-row="true">
<tr>
<td>항목</td>
<td>값</td>
</tr>
<tr>
<td>GPU</td>
<td>NVIDIA GeForce RTX 4080 Laptop, 12,282 MiB</td>
</tr>
<tr>
<td>커널</td>
<td>6.18.33.1-microsoft-standard-WSL2</td>
</tr>
<tr>
<td>k3s</td>
<td>v1.36.2+k3s1</td>
</tr>
<tr>
<td>이미지</td>
<td>`vllm/vllm-openai:v0.23.0` (전 실험 동일)</td>
</tr>
<tr>
<td>모델</td>
<td>`Qwen/Qwen2.5-1.5B-Instruct`</td>
</tr>
	</table>
	전 구성에서 `max_model_len=4096`, `max_num_seqs=64`를 고정했습니다. 양자화에는 같은 BF16 체크포인트에 `--quantization fp8`을 적용했습니다. W8A8 경로에서는 가중치와 활성화의 정밀도가 함께 바뀝니다. KV 캐시 정밀도를 바꾸는 실험은 아닙니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>워크로드</td>
<td>입력</td>
<td>출력</td>
<td>특징</td>
</tr>
<tr>
<td>**`decode`**</td>
<td>짧은 입력</td>
<td>512토큰</td>
<td>새 내용을 길게 생성하는 디코드 지배 워크로드</td>
</tr>
<tr>
<td>**`prefill`**</td>
<td>같은 문단을 24회 반복한 긴 문맥</td>
<td>64토큰</td>
<td>입력을 되짚는 프리필 지배 워크로드</td>
</tr>
	</table>
	중심 비교인 F1b는 구성별 3회 측정입니다. 표의 σ는 처리량의 표준편차입니다. ITL은 원기록의 초 단위를 유지했고, 본문에서는 읽기 쉽게 ms로 환산했습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>util</td>
<td>Maximum concurrency</td>
<td>처리량 (tok/s, 3회)</td>
<td>σ</td>
<td>vs BF16</td>
<td>ITL p50 (s)</td>
</tr>
<tr>
<td>① BF16 기본</td>
<td>0.85</td>
<td>59.50x</td>
<td>1,689.3</td>
<td>3.3</td>
<td>—</td>
<td>0.0097</td>
</tr>
<tr>
<td>② FP8 기본</td>
<td>0.85</td>
<td>70.20x</td>
<td>2,258.8</td>
<td>6.5</td>
<td>+33.7%</td>
<td>0.0073</td>
</tr>
<tr>
<td>③ **FP8 · KV 예산 축소**</td>
<td>0.7656</td>
<td>**60.95x**</td>
<td>**2,261.0**</td>
<td>12.5</td>
<td>**+33.8%**</td>
<td>0.0073</td>
</tr>
	</table>
	기존 원고의 ‘재현 편차 0.38%’는 산식이 남아 있지 않아 판단 근거에서 제외했습니다. 표의 평균과 표준편차로 계산한 BF16 변동계수는 `3.3 / 1,689.3 × 100 ≈ 0.20%`입니다. 표준편차와 최댓값·최솟값의 차이는 다른 통계량이므로 바꿔 쓸 수 없습니다.
	양자화 전후 기동 로그와 성능 요약은 다음과 같습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td></td>
<td>BF16</td>
<td>FP8</td>
<td>차이</td>
</tr>
<tr>
<td>Available KV cache memory</td>
<td>6.51 GiB</td>
<td>7.68 GiB</td>
<td>+1.17 GiB</td>
</tr>
<tr>
<td>GPU KV cache size</td>
<td>243,696 토큰</td>
<td>287,536 토큰</td>
<td>+43,840</td>
</tr>
<tr>
<td>Maximum concurrency</td>
<td>59.50x</td>
<td>70.20x</td>
<td>**+18.0%**</td>
</tr>
<tr>
<td>decode c=16 처리량</td>
<td>1,689.3 tok/s</td>
<td>2,258.8 tok/s</td>
<td>**+33.7%**</td>
</tr>
	</table>
	KV 예산을 맞출 때는 기동 로그의 실측값을 보고 `gpu_memory_utilization`을 조절했습니다. 기존 기록의 조정 과정입니다.
	```plain text
attempt 1: conc=70.20x -> next util=0.7204
attempt 2: conc=55.99x -> next util=0.7656
attempt 3: conc=60.95x -> 성립 (기준 59.50x 대비 오차 2.4%, ±5% 이내)
	```
	마지막 예산은 기준보다 2.4% 컸습니다. ‘동결’은 정확한 일치를 뜻하는 표현으로 읽힐 수 있어 본문에서는 ‘KV 예산 축소’로 표기했습니다.
	```bash
# 기동 로그에서 Maximum concurrency 숫자만 꺼낸다
read_conc() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' \
    | tail -1 | grep -oE '[0-9.]+x$' | tr -d 'x'
}
	```
</details>
<details>
<summary>B. KV 예산 스윕과 부족 구간</summary>
	BF16에서 `gpu_memory_utilization`만 바꾼 F1a 결과입니다. `decode`는 생성 처리량, `prefill`은 프롬프트 처리량을 비교합니다. 서로 다른 지표의 절댓값을 비교하지 않습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>util</td>
<td>KV 예산 (토큰)</td>
<td>Maximum concurrency</td>
<td>decode c=16 (tok/s)</td>
<td>prefill c=64 프롬프트 (tok/s)</td>
</tr>
<tr>
<td>0.45</td>
<td>64,048</td>
<td>15.64x</td>
<td>1,679.9</td>
<td>12,976</td>
</tr>
<tr>
<td>0.55</td>
<td>108,960</td>
<td>26.60x</td>
<td>1,685.4</td>
<td>12,328</td>
</tr>
<tr>
<td>0.65</td>
<td>153,872</td>
<td>37.57x</td>
<td>1,676.3</td>
<td>12,661</td>
</tr>
<tr>
<td>0.75</td>
<td>198,784</td>
<td>48.53x</td>
<td>1,680.6</td>
<td>12,655</td>
</tr>
<tr>
<td>0.85</td>
<td>243,696</td>
<td>59.50x</td>
<td>1,677.2</td>
<td>12,481</td>
</tr>
<tr>
<td>**범위**</td>
<td>**3.80배**</td>
<td>**3.80배**</td>
<td>**변동 0.5%**</td>
<td>**변동 5.3%**</td>
</tr>
	</table>
	변동은 `(최댓값 − 최솟값) / 최솟값 × 100`으로 계산하면 decode 약 0.54%, prefill 약 5.26%입니다. 표의 0.5%와 5.3%는 이를 반올림한 값입니다. prefill 최솟값은 `util=0.55`에서 나왔습니다.
	decode의 KV 수요는 요청당 약 550토큰에 동시성 16을 곱한 약 8,800토큰으로 추산했습니다. 가장 작은 예산 64,048토큰에도 여유가 있습니다. 다만 이 계산은 입력·출력 길이를 이용한 대략적인 수요이며 실제 점유량과 같지는 않습니다.
	prefill은 기록된 프롬프트 2,028토큰과 출력 최대 64토큰을 기준으로 동시성 64의 수요가 약 134,000토큰입니다. 예산보다 많은 요청이 있어도 대기와 배칭 방식에 따라 처리량은 유지될 수 있습니다. 이 결과만으로 연산 병목을 확정하지는 않았습니다.
	더 작은 예산을 탐색한 F1d 결과입니다. F1a와 별도 실행이므로 같은 설정의 수치가 조금 다릅니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>util</td>
<td>KV 예산 (토큰)</td>
<td>Maximum concurrency</td>
<td>prefill c=64 프롬프트 (tok/s)</td>
<td>TTFT p50 (s)</td>
<td>KV 사용률 최대</td>
<td>선점</td>
</tr>
<tr>
<td>0.33</td>
<td>10,144</td>
<td>2.48x</td>
<td>**8,306**</td>
<td>**7.679**</td>
<td>0.998</td>
<td>**4회**</td>
</tr>
<tr>
<td>0.36</td>
<td>23,616</td>
<td>5.77x</td>
<td>11,833</td>
<td>5.193</td>
<td>0.961</td>
<td>0</td>
</tr>
<tr>
<td>0.40</td>
<td>41,584</td>
<td>10.15x</td>
<td>12,828</td>
<td>4.699</td>
<td>0.990</td>
<td>0</td>
</tr>
<tr>
<td>0.45</td>
<td>64,048</td>
<td>15.64x</td>
<td>12,814</td>
<td>4.738</td>
<td>0.995</td>
<td>0</td>
</tr>
<tr>
<td>0.85</td>
<td>243,696</td>
<td>59.50x</td>
<td>12,686</td>
<td>4.448</td>
<td>0.439</td>
<td>0</td>
</tr>
	</table>
	`util=0.33`과 0.85를 비교하면 프롬프트 처리량은 34.5% 감소하고 TTFT p50은 약 1.73배가 됩니다. 선점은 이 측정 구간에서 4회였습니다. 뒤의 3분 대시보드 실험에서 기록한 19회와는 다른 실행입니다.
	처음 계획한 `util=0.90`에서는 다음 기동 오류가 났습니다.
	```plain text
ValueError: Free memory on device cuda:0 (10.79/11.99 GiB) on startup is less than
desired GPU memory utilization (0.9, 10.79 GiB).
	```
	기동 시 가용 메모리가 요청량에 못 미쳐 이 랩톱에서는 상한을 0.85로 두었습니다. 오류만으로 다른 프로세스별 메모리 점유량까지 구분할 수는 없습니다.
</details>
<details>
<summary>C. 워크로드와 동시성에 따른 차이</summary>
	F1c는 prefill·decode와 동시성 1·4·16·64를 조합해 BF16과 FP8을 각각 2회 측정했습니다. 아래 처리량은 기존 기록의 tok/s 값을 보존했습니다. 이 표의 prefill 열은 F1a·F1d의 ‘프롬프트 처리량’과 같은 지표라고 가정하지 않습니다. 원시 결과의 집계 필드를 확인하기 전에는 동일 행의 BF16·FP8 비교에만 사용합니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>워크로드</td>
<td>동시성</td>
<td>BF16 (tok/s)</td>
<td>FP8 (tok/s)</td>
<td>차이</td>
<td>ITL 변화</td>
</tr>
<tr>
<td>`decode`</td>
<td>1</td>
<td>115.7</td>
<td>155.7</td>
<td>**+34.6%**</td>
<td>−24.0%</td>
</tr>
<tr>
<td>`decode`</td>
<td>4</td>
<td>449.1</td>
<td>608.0</td>
<td>**+35.4%**</td>
<td>−23.9%</td>
</tr>
<tr>
<td>`decode`</td>
<td>16</td>
<td>1,295.8</td>
<td>1,740.7</td>
<td>**+34.3%**</td>
<td>−24.8%</td>
</tr>
<tr>
<td>`decode`</td>
<td>64</td>
<td>4,759.5</td>
<td>5,476.5</td>
<td>**+15.1%**</td>
<td>−12.9%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>1</td>
<td>111.9</td>
<td>149.4</td>
<td>**+33.5%**</td>
<td>−24.2%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>4</td>
<td>410.6</td>
<td>533.2</td>
<td>**+29.8%**</td>
<td>−25.7%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>16</td>
<td>1,065.2</td>
<td>1,327.6</td>
<td>**+24.6%**</td>
<td>−32.0%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>64</td>
<td>2,861.7</td>
<td>3,179.0</td>
<td>**+11.1%**</td>
<td>−19.2%</td>
</tr>
	</table>
	여덟 조건의 평균은 모두 FP8 쪽이 높았지만 특히 동시성 64는 반복 변동이 큰 구간입니다. 두 칸의 기록된 재현폭은 각각 1.9%와 4.4%였고, 기존 실습에서는 같은 동시성에서 최대 10% 변동도 기록했습니다. 따라서 이 표는 효과의 범위를 살피는 보조 결과입니다.
	배치가 커지면 가중치 읽기 비용이 더 많은 토큰에 나뉘는 설명을 생각해 볼 수 있습니다. 다만 동시성은 실제 배치 크기와 항상 같지 않고 FP8은 계산 경로도 바꿉니다. 관측한 추세만으로 대역폭의 기여도를 계산하지는 않았습니다.
</details>
<details>
<summary>D. 프로파일러 집계의 단위와 확인 범위</summary>
	기존 기록에는 어텐션 커널 호출 수가 BF16 1,624회, FP8 2,744회로 남아 있습니다. 모델 28층에서 매 스텝 같은 어텐션 커널이 한 번씩 호출됐다는 전제를 두면 각각 58스텝과 98스텝입니다. 이 전제와 호출 필터는 원본 트레이스로 다시 확인해야 합니다.
	본문의 계산은 `503.1ms / 58 ≈ 8.67ms`, `622.8ms / 98 ≈ 6.36ms`입니다. 기존 역할별 표의 합계는 여기에 28을 더 나눈 값과 거의 같습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>역할</td>
<td>BF16 (기존 집계값)</td>
<td>FP8 (기존 집계값)</td>
<td>차이</td>
</tr>
<tr>
<td>**GEMM — 선형 계층**</td>
<td>279.54 us</td>
<td>202.21 us</td>
<td>**−27.7%**</td>
</tr>
<tr>
<td>**어텐션 · KV 캐시**</td>
<td>14.79 us</td>
<td>14.78 us</td>
<td>**−0.1%**</td>
</tr>
<tr>
<td>복사·형변환</td>
<td>7.25 us</td>
<td>7.24 us</td>
<td>−0.2%</td>
</tr>
<tr>
<td>정규화·활성화</td>
<td>5.51 us</td>
<td>0.08 us</td>
<td>−98.6%</td>
</tr>
<tr>
<td>그 외</td>
<td>2.68 us</td>
<td>2.66 us</td>
<td>−0.7%</td>
</tr>
<tr>
<td>**합계**</td>
<td>**309.77 us**</td>
<td>**226.96 us**</td>
<td>**−26.7%**</td>
</tr>
	</table>
	위 표는 원래 ‘스텝당’으로 표기돼 있던 수치입니다. `503.1ms / 58 / 28 ≈ 309.79µs`, `622.8ms / 98 / 28 ≈ 226.97µs`이므로 레이어·스텝 정규화로 추정되지만, 현재는 집계 코드가 없어 단위를 확정하지 않았습니다. 이 표의 절댓값은 실제 한 스텝의 지연시간으로 읽으면 안 됩니다.
	같은 집계 기준이라는 전제에서 GEMM 감소는 약 27.7%이며 전체 감소분에서 GEMM이 차지하는 비중은 `(279.54 − 202.21) / (309.77 − 226.96) ≈ 93.4%`입니다. 따라서 기존 요약의 ‘전부 선형 계층’이라는 표현은 성립하지 않습니다. 커널 융합에 따라 역할 분류도 달라질 수 있어 각 연산이 실제로 줄인 시간과 같다고 보지는 않았습니다.
	기록된 커널 이름은 다음과 같습니다.
	```plain text
BF16 : void cutlass::Kernel2<cutlass_80_wmma_tensorop_bf16_...>
FP8  : void cutlass::Kernel2<enable_sm89_to_sm90<cutlass::gemm...>>
	```
	FP8 쪽에는 `triton_red_fused__to_copy_abs_clamp_cutlass_scaled_mm...`도 기록돼 있습니다. 이름에서 융합 연산을 확인할 수 있지만, 정규화·활성화 비용이 정확히 어디로 이동했는지는 실행 이벤트와 분류 코드를 대조해야 합니다. 이름만으로 역양자화 비용이나 대역폭 병목까지 확정하지 않습니다.
	**도구 실행 기록**
	```plain text
$ kubectl -n llm-serving-lab exec <pod> -- sh -c "command -v nsys ncu"
NOT_FOUND
	```
	측정 이미지에서 `nsys`와 `ncu`를 찾지 못해 PyTorch Profiler를 사용했습니다. 환경 변수 방식으로 시도했을 때의 오류도 남아 있습니다.
	```plain text
WARNING [envs.py:2088] Unknown vLLM environment variable detected: VLLM_TORCH_PROFILER_DIR
$ curl -X POST .../start_profile
curl: (22) The requested URL returned error: 404
	```
	기록에 사용한 프로파일러 옵션은 다음과 같습니다.
	```plain text
--profiler-config.profiler=torch
--profiler-config.torch_profiler_dir=/root/.cache/huggingface/profiles
--profiler-config.torch_profiler_with_stack=false
--profiler-config.delay_iterations=20 --profiler-config.max_iterations=100
	```
	[vLLM v0.23.0 ProfilerConfig](https://docs.vllm.ai/en/v0.23.0/api/vllm/config/profiler/)에서 `delay_iterations`는 수집 전 건너뛸 엔진 iteration 수, `max_iterations`는 수집 상한입니다. 서로 다른 트레이스가 실제로 같은 작업량을 담았는지는 옵션 이름만으로 보장되지 않습니다.
	이번에는 PyTorch Profiler와 서비스 지표를 대조했습니다. Nsight Systems/Compute 실습은 완료하지 못했습니다.
</details>
<details>
<summary>E. Prometheus의 A·B·C 구간과 원본 화면</summary>
	15초 스크랩에서는 10\~20초 버스트의 최고점을 놓쳤습니다. 기존 실험의 KV 사용률 0.998이 대시보드에는 0.078까지만 남아, 이번에는 각 부하를 3분씩 실행했습니다. 이는 이 실험의 기록 방식이며 모든 환경에서 필요한 표준 시간은 아닙니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>구간</td>
<td>구성</td>
<td>워크로드</td>
<td>확인할 것</td>
</tr>
<tr>
<td>**A**</td>
<td>BF16 · util 0.85</td>
<td>`decode` c=16</td>
<td>KV 예산에 여유가 있는 상태</td>
</tr>
<tr>
<td>**B**</td>
<td>FP8 · util 0.85</td>
<td>`decode` c=16 (동일)</td>
<td>같은 부하에서 처리량만 오르는지</td>
</tr>
<tr>
<td>**C**</td>
<td>BF16 · util 0.33</td>
<td>`prefill` c=64</td>
<td>예산이 실제로 걸리는 상태</td>
</tr>
	</table>
	<table fit-page-width="true" header-row="true">
<tr>
<td>구간</td>
<td>생성 처리량 (tok/s)</td>
<td>동시 실행</td>
<td>대기</td>
<td>KV 사용률</td>
<td>누적 선점</td>
<td>GPU 사용률</td>
</tr>
<tr>
<td>**A** BF16 · `decode`</td>
<td>1,703.6</td>
<td>16</td>
<td>0</td>
<td>**0.031**</td>
<td>0</td>
<td>99%</td>
</tr>
<tr>
<td>**B** FP8 · `decode`</td>
<td>**2,269.3**</td>
<td>16</td>
<td>0</td>
<td>**0.028**</td>
<td>0</td>
<td>99%</td>
</tr>
<tr>
<td>**C** BF16 util 0.33 · `prefill`</td>
<td>224.0</td>
<td>**4**</td>
<td>**60**</td>
<td>**0.812**</td>
<td>**19**</td>
<td>99%</td>
</tr>
	</table>
	세 화면은 모두 9월 2일 20:48\~21:13 UTC를 표시합니다. 시작 시각 **21:01은 A**, **21:05는 B**, **21:09는 C**입니다. 사이의 공백은 서버를 재배포한 구간입니다.
	![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/9dbc0290-9df5-41ea-a425-63225044baec/proof-w5-08-dash-throughput.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666BGUS6G2%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T061520Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjED0aCXVzLXdlc3QtMiJGMEQCIDqaItC9CO0khx6ARLIpIEjX%2Feq3N0FUz6VNbWbzaD04AiAeoDiSIo2qTo0qTXLEzq5ZraEz0Ze%2FmG6l7z3INlPXbCr%2FAwgGEAAaDDYzNzQyMzE4MzgwNSIMTUAkW7rqV9l7wMaXKtwDOHAQ5uEbAhu3vhr%2FZAWDoK%2FY%2FLUmP7Pkm279C3Nw3LERIT6lqAi61FH84BFzsYUNbTDn2WOW5gDfj0Ewxvpfg4gJRKWwaHJBeNp0MhQuYwBsNNZpp6wnVnf%2F6gQ1MeLP9fxkiXiIcy6vnEmjcidnJzDrcvY%2BFDizsgnbT4DaNLIpjBp%2FATmP74mEFDJK%2Fz4l63cqkArS7TKXnvNNKnuyCeeqM9zSBPyYGAY8lztwAg0wqwZuC6VlQBe3d6k1TKulBvYM%2FQ4A6fxStDdCGS7dcRpWKhWl1pGzFGWC%2BeqT%2Fz8WeqWGRSYVI%2Fsp8E7YR83dKZEIiHegmmW54CL8ux0Ew9aBG9CK4oHQOvFMzMOLsvCaCZ7MWJ9mr9bNSvQvZOJN1WNo7T6kcXAv2zRNVIZgueaaTF3MCjuDegafqg4DRNoY%2BWVsYhZXKCvk%2BHIpkYQvqWDfijRpiI0jxnmjHCmpjEYk7iedlJ0dMFthQ4id%2Fx2iZ9DkFckG25F15iI0IDxJkYsZqXzLUc8i3tDzgNwgPaZQGVfHwFfJ%2F8pOiIWC7jCxyVGtHabSWJwZnSdrhPeOd0kJVs5qey5D1t%2FV2SWx9EL52TrqRrYasDVlu9tfCCv80gURdnhN%2BACu%2BXIws7nu1AY6pgECgFK4IuODH65h%2BZsMDjjwN6PzqE0hviCbs6514Z2xx6Q9hdJ%2B6BRpD9dJ1J9P4Arn1TmsmlrghXmjaFWqVxGenCwdQl4CTWGGFET%2Fv0KWZKHcpImkS0xqTN3K6MG%2FtC64dVIZEw9WoZ9T64TY%2BfPxLTc4vdJ8qSdhva0pGDyDnfgH7ToZmaaUe%2BUqUQ6H8DkzEy37mrCulh3KJJnmOk%2BLlZG3Zu40&X-Amz-Signature=c1d139fa85575107d638f87c5694426a5f3ec39d567b8e9789ecc63c9d72b320&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
	*A와 B의 실행 요청 수는 모두 16개입니다. 처리량 비교는 동일한 decode 부하인 A·B 사이에서만 합니다.*
	![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/7a73e637-179f-47a0-a1f6-1fd8a79d8698/proof-w5-07-dash-kv-preempt.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666BGUS6G2%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T061520Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjED0aCXVzLXdlc3QtMiJGMEQCIDqaItC9CO0khx6ARLIpIEjX%2Feq3N0FUz6VNbWbzaD04AiAeoDiSIo2qTo0qTXLEzq5ZraEz0Ze%2FmG6l7z3INlPXbCr%2FAwgGEAAaDDYzNzQyMzE4MzgwNSIMTUAkW7rqV9l7wMaXKtwDOHAQ5uEbAhu3vhr%2FZAWDoK%2FY%2FLUmP7Pkm279C3Nw3LERIT6lqAi61FH84BFzsYUNbTDn2WOW5gDfj0Ewxvpfg4gJRKWwaHJBeNp0MhQuYwBsNNZpp6wnVnf%2F6gQ1MeLP9fxkiXiIcy6vnEmjcidnJzDrcvY%2BFDizsgnbT4DaNLIpjBp%2FATmP74mEFDJK%2Fz4l63cqkArS7TKXnvNNKnuyCeeqM9zSBPyYGAY8lztwAg0wqwZuC6VlQBe3d6k1TKulBvYM%2FQ4A6fxStDdCGS7dcRpWKhWl1pGzFGWC%2BeqT%2Fz8WeqWGRSYVI%2Fsp8E7YR83dKZEIiHegmmW54CL8ux0Ew9aBG9CK4oHQOvFMzMOLsvCaCZ7MWJ9mr9bNSvQvZOJN1WNo7T6kcXAv2zRNVIZgueaaTF3MCjuDegafqg4DRNoY%2BWVsYhZXKCvk%2BHIpkYQvqWDfijRpiI0jxnmjHCmpjEYk7iedlJ0dMFthQ4id%2Fx2iZ9DkFckG25F15iI0IDxJkYsZqXzLUc8i3tDzgNwgPaZQGVfHwFfJ%2F8pOiIWC7jCxyVGtHabSWJwZnSdrhPeOd0kJVs5qey5D1t%2FV2SWx9EL52TrqRrYasDVlu9tfCCv80gURdnhN%2BACu%2BXIws7nu1AY6pgECgFK4IuODH65h%2BZsMDjjwN6PzqE0hviCbs6514Z2xx6Q9hdJ%2B6BRpD9dJ1J9P4Arn1TmsmlrghXmjaFWqVxGenCwdQl4CTWGGFET%2Fv0KWZKHcpImkS0xqTN3K6MG%2FtC64dVIZEw9WoZ9T64TY%2BfPxLTc4vdJ8qSdhva0pGDyDnfgH7ToZmaaUe%2BUqUQ6H8DkzEy37mrCulh3KJJnmOk%2BLlZG3Zu40&X-Amz-Signature=f4efa65e17b07dc63330026ede38b52712b46782b02aa42347e832c21997db5b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
	*C는 다른 prefill 부하입니다. 이 구간의 19회 선점을 앞선 F1d의 4회와 혼합하지 않습니다.*
	![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/84db0e6d-6713-41a0-a440-5cd9097a5471/proof-w5-09-dash-queue-gpu.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666BGUS6G2%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T061520Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjED0aCXVzLXdlc3QtMiJGMEQCIDqaItC9CO0khx6ARLIpIEjX%2Feq3N0FUz6VNbWbzaD04AiAeoDiSIo2qTo0qTXLEzq5ZraEz0Ze%2FmG6l7z3INlPXbCr%2FAwgGEAAaDDYzNzQyMzE4MzgwNSIMTUAkW7rqV9l7wMaXKtwDOHAQ5uEbAhu3vhr%2FZAWDoK%2FY%2FLUmP7Pkm279C3Nw3LERIT6lqAi61FH84BFzsYUNbTDn2WOW5gDfj0Ewxvpfg4gJRKWwaHJBeNp0MhQuYwBsNNZpp6wnVnf%2F6gQ1MeLP9fxkiXiIcy6vnEmjcidnJzDrcvY%2BFDizsgnbT4DaNLIpjBp%2FATmP74mEFDJK%2Fz4l63cqkArS7TKXnvNNKnuyCeeqM9zSBPyYGAY8lztwAg0wqwZuC6VlQBe3d6k1TKulBvYM%2FQ4A6fxStDdCGS7dcRpWKhWl1pGzFGWC%2BeqT%2Fz8WeqWGRSYVI%2Fsp8E7YR83dKZEIiHegmmW54CL8ux0Ew9aBG9CK4oHQOvFMzMOLsvCaCZ7MWJ9mr9bNSvQvZOJN1WNo7T6kcXAv2zRNVIZgueaaTF3MCjuDegafqg4DRNoY%2BWVsYhZXKCvk%2BHIpkYQvqWDfijRpiI0jxnmjHCmpjEYk7iedlJ0dMFthQ4id%2Fx2iZ9DkFckG25F15iI0IDxJkYsZqXzLUc8i3tDzgNwgPaZQGVfHwFfJ%2F8pOiIWC7jCxyVGtHabSWJwZnSdrhPeOd0kJVs5qey5D1t%2FV2SWx9EL52TrqRrYasDVlu9tfCCv80gURdnhN%2BACu%2BXIws7nu1AY6pgECgFK4IuODH65h%2BZsMDjjwN6PzqE0hviCbs6514Z2xx6Q9hdJ%2B6BRpD9dJ1J9P4Arn1TmsmlrghXmjaFWqVxGenCwdQl4CTWGGFET%2Fv0KWZKHcpImkS0xqTN3K6MG%2FtC64dVIZEw9WoZ9T64TY%2BfPxLTc4vdJ8qSdhva0pGDyDnfgH7ToZmaaUe%2BUqUQ6H8DkzEy37mrCulh3KJJnmOk%2BLlZG3Zu40&X-Amz-Signature=922f9c7610e9ecee5ff7ddd177d4f1e8629666daf5e2b5c26a2ca9139fee5db2&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
	*같은 GPU 사용률 99%에서도 대기 상태와 처리량은 다릅니다. 사용률 하나로 병목을 판정하지 않습니다.*
	지표 수집에서도 오류가 있었습니다. 다음 필터는 이름 뒤에 공백을 요구해 라벨이 붙은 실제 행을 놓쳤습니다.
	```bash
grep -E '^vllm:(num_requests_running|kv_cache_usage_perc) '   # 이름 뒤에 공백을 요구
	```
	```plain text
vllm:num_requests_running{engine="0",model_name="qwen2.5-1.5b"} 16.0
	```
	수집 파일이 비었다면 값이 0인지보다 행이 실제로 수집됐는지부터 확인합니다.
</details>
<details>
<summary>F. 지난주 결과를 함께 보면 어디까지 해석할 수 있을까</summary>
	[지난 글](https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234)의 추측 디코딩 결과를 KV 수용량 축에 함께 놓은 참고 그림입니다. 본문 핵심 비교와 달리 서로 다른 실험 시점의 결과를 포함합니다.
	![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/4116a99f-9119-4d22-916c-8c4446253084/fig-f1-kv-budget-curve.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666BGUS6G2%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T061520Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjED0aCXVzLXdlc3QtMiJGMEQCIDqaItC9CO0khx6ARLIpIEjX%2Feq3N0FUz6VNbWbzaD04AiAeoDiSIo2qTo0qTXLEzq5ZraEz0Ze%2FmG6l7z3INlPXbCr%2FAwgGEAAaDDYzNzQyMzE4MzgwNSIMTUAkW7rqV9l7wMaXKtwDOHAQ5uEbAhu3vhr%2FZAWDoK%2FY%2FLUmP7Pkm279C3Nw3LERIT6lqAi61FH84BFzsYUNbTDn2WOW5gDfj0Ewxvpfg4gJRKWwaHJBeNp0MhQuYwBsNNZpp6wnVnf%2F6gQ1MeLP9fxkiXiIcy6vnEmjcidnJzDrcvY%2BFDizsgnbT4DaNLIpjBp%2FATmP74mEFDJK%2Fz4l63cqkArS7TKXnvNNKnuyCeeqM9zSBPyYGAY8lztwAg0wqwZuC6VlQBe3d6k1TKulBvYM%2FQ4A6fxStDdCGS7dcRpWKhWl1pGzFGWC%2BeqT%2Fz8WeqWGRSYVI%2Fsp8E7YR83dKZEIiHegmmW54CL8ux0Ew9aBG9CK4oHQOvFMzMOLsvCaCZ7MWJ9mr9bNSvQvZOJN1WNo7T6kcXAv2zRNVIZgueaaTF3MCjuDegafqg4DRNoY%2BWVsYhZXKCvk%2BHIpkYQvqWDfijRpiI0jxnmjHCmpjEYk7iedlJ0dMFthQ4id%2Fx2iZ9DkFckG25F15iI0IDxJkYsZqXzLUc8i3tDzgNwgPaZQGVfHwFfJ%2F8pOiIWC7jCxyVGtHabSWJwZnSdrhPeOd0kJVs5qey5D1t%2FV2SWx9EL52TrqRrYasDVlu9tfCCv80gURdnhN%2BACu%2BXIws7nu1AY6pgECgFK4IuODH65h%2BZsMDjjwN6PzqE0hviCbs6514Z2xx6Q9hdJ%2B6BRpD9dJ1J9P4Arn1TmsmlrghXmjaFWqVxGenCwdQl4CTWGGFET%2Fv0KWZKHcpImkS0xqTN3K6MG%2FtC64dVIZEw9WoZ9T64TY%2BfPxLTc4vdJ8qSdhva0pGDyDnfgH7ToZmaaUe%2BUqUQ6H8DkzEy37mrCulh3KJJnmOk%2BLlZG3Zu40&X-Amz-Signature=0d847eef3cf1bc8b9cd29c4e30bf62fd8e11956d9daceb0d558bc0882565ec8f&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
	*이 그림에는 decode c=16만 있습니다. prefill 결과를 그린 그래프가 아닙니다. 가로축은 기동 로그의 Maximum concurrency이며 실제 동시 실행 요청 수가 아닙니다.*
	<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>Maximum concurrency</td>
<td>decode c=16 (tok/s)</td>
<td>선에서 벗어난 방향</td>
</tr>
<tr>
<td>BF16 기준</td>
<td>59.50x</td>
<td>1,689.3</td>
<td>선 위</td>
</tr>
<tr>
<td>FP8 기본</td>
<td>70.20x</td>
<td>2,258.8</td>
<td>**위로**</td>
</tr>
<tr>
<td>FP8 · KV 예산 축소</td>
<td>60.95x</td>
<td>2,261.0</td>
<td>**위로**</td>
</tr>
<tr>
<td>4주차 ngram</td>
<td>57.48x</td>
<td>1,356.2</td>
<td>**아래로**</td>
</tr>
<tr>
<td>4주차 draft-0.5B</td>
<td>34.38x</td>
<td>825.7</td>
<td>**아래로**</td>
</tr>
	</table>
	BF16 스윕에서 예산 변화의 영향이 작았다는 사실은, 지난주 draft 구성의 성능 하락을 KV 예산 감소만으로 설명하기 어렵게 만듭니다. 그러나 draft 모델은 연산과 스케줄링도 함께 바꾸므로 BF16 스윕만으로 그 구성의 KV 기여도가 정확히 0이라고 확정할 수는 없습니다.
	지난주에는 KV 예산이 42% 줄었다는 이유로 비교를 유보했습니다. 이번에는 그 차이가 얼마나 영향을 주는지 먼저 재는 쪽으로 판단을 바꿨습니다. 손해 전체를 추측 디코딩 탓으로 확정하려면 draft 구성에서도 예산을 통제한 비교가 추가로 필요합니다.
</details>
<details>
<summary>G. 재현에 필요한 자료와 실행 순서</summary>
	**재현 가능 범위**
	현재 저장소에는 기준선 배포 매니페스트, `redeploy.sh`, `benchmark.py`가 있습니다. 반면 원고가 참조하던 `results/f*`, `f-analysis.md`, `run_f1a2.sh`, `run_f1b.sh`, `run_f1c.sh`, `run_f1d.sh`, `run_f2.sh`, `run_f5.sh`는 현재 체크아웃에 없습니다. 아래 예시는 기존 측정값을 그대로 재생하는 명령이 아니라, 같은 대조 실험을 새로 구성하는 절차입니다. 원래의 요청 수·입력·반복별 결과를 확보해야 수치를 직접 대조할 수 있습니다.
	로컬 실행 자산과 환경 준비는 WSL2·K3s vLLM 기준선 실습 문서(`labs/wsl2-vllm-baseline/README.md`, 비공개 저장소)에 있습니다. GPU와 k3s가 준비된 측정 머신에서 저장소 루트를 기준으로 시작합니다. 기존 실습과 같은 containerd 이미지·모델 캐시를 사용합니다.
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
	프리필에서 KV 수요를 비교할 때는 모든 요청이 같은 접두사를 공유하는지도 통제합니다. 이 실습의 `--unique-prefix`는 요청별 식별자를 붙여 접두사 재사용의 영향을 줄이려는 옵션입니다. 프롬프트, 성공 요청 수, 실제 생성 토큰 수를 결과와 함께 보관합니다. 스트리밍 응답의 usage가 수집됐는지도 기록합니다.
	**후속 검증 순서**
	가장 먼저 필요한 것은 F1b 반복별 원시 결과와 F2 트레이스·집계 코드의 복구입니다. 커널 시간의 분모, 중복 이벤트와 겹친 실행, 실제 배치 크기를 확인합니다. 이 작업은 새 실험 없이도 집계 문제를 해결할 수 있습니다.
	그다음 같은 배치·같은 생성 길이를 유지한 BF16·FP8 프로파일링을 반복하면 커널 경로의 차이를 더 분명하게 설명할 수 있습니다. 메모리 대역폭이 원인이라고 좁혀 말하려면 Nsight Systems로 실행 구간을 확인하고 Nsight Compute에서 해당 커널의 메모리·연산 지표를 대조해야 합니다. 프로파일러를 켠 실행의 처리량은 일반 벤치마크와 분리합니다.
	운영 도입을 판단하려면 응답 품질도 확인해야 합니다. 실제 사용 과제를 대표하는 고정 입력과 평가 기준을 정해 BF16·FP8을 비교하고 성능 이득과 품질 변화를 함께 기록합니다. 추가 모델을 많이 나열하는 것보다 이 비교가 현재 글의 실용성을 높입니다.
</details>
## 참고 자료
- *LLM Optimization in Practice* (CH9) — 하드웨어·트래픽·평가 지표를 정한 뒤 기준선과 최적화 구성을 비교하는 실습. Qwen3-14B AWQ 사례와 스터디의 별도 RTX·Qwen3-4B Nsight 참고 실습을 구분했습니다.
- *Advancements in LLM Serving* (CH10) — 서비스 지표와 프로파일러를 대조해 병목을 좁히는 접근. 시맨틱 라우팅·멀티모달·엣지·Multi-LoRA·강화학습 서빙은 이번 글의 실험 범위에 포함하지 않았습니다.
- [vLLM v0.23.0 — FP8 W8A8와 온라인 양자화](https://docs.vllm.ai/en/v0.23.0/features/quantization/llm_compressor/fp8/) — 가중치·활성화 정밀도와 온라인 양자화 경로.
- [vLLM v0.23.0 — ProfilerConfig](https://docs.vllm.ai/en/v0.23.0/api/vllm/config/profiler/) — 수집 지연·iteration 상한 등 프로파일러 설정.
- 자체 실험 기록 — 본문과 부록의 결과표, Prometheus 원본 화면. 5주차 원시 결과와 트레이스는 현재 검토본에 포함되지 않았습니다.