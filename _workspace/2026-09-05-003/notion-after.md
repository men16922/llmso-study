**FP8 양자화로 처리량이 33.7% 올랐습니다. KV 예산, ITL, 커널 시간을 차례로 대조해 어디서 줄인 시간인지 추적했습니다.**
<callout color="blue_bg">
	**실험에서 확인한 세 가지**
	- **KV 예산을 늘려도 처리량은 달라지지 않았습니다.** `gpu_memory_utilization`만 바꿔 KV 예산을 **3.80배**(64,048 → 243,696 토큰) 늘렸는데 처리량은 **0.5%** 안에서 그대로였습니다.
	- **예산을 되돌려도 이득은 남았습니다.** FP8의 KV 예산을 BF16 수준으로 줄였는데 처리량 이득 **+33.8%**가 그대로였습니다. 예산의 기여분은 0%였습니다.
	- **줄어든 시간은 전부 선형 계층에 있었습니다.** 프로파일러로 스텝당 커널 시간을 나눠 보니 GEMM 경로가 **−27.7%**인데 어텐션·KV 캐시 경로는 **−0.1%**로 거의 같았습니다. Prometheus 대시보드에서도 결론이 같았습니다. 동시 실행 요청 수는 **양쪽 16개로 같은데** 처리량만 **+33.2%** 올랐습니다.
</callout>
운영에서는 어떤 기능을 켰는지보다 원인으로 본 조건을 되돌렸을 때 이득도 사라지는지 확인해야 합니다. 이득이 그대로라면 다른 경로를 찾아야 합니다.
---
<table_of_contents color="gray"/>
## 1. KV 예산의 영향을 분리하는 실험
[지난 글](https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234)에서는 최적화 기능의 이득이 손해로 뒤집히는 조건을 찾았습니다. 기준은 한 스텝의 토큰 예산이었습니다. 이번에는 처리량이 늘어난 원인을 살펴봤습니다.
CH9의 첫 줄에도 같은 질문이 나옵니다.
> *"처리량이 올랐다는 건 GPU가 더 빨리 계산해서인가, 아니면 그냥 덜 다시 계산해서인가?"*
같은 챕터에는 단서도 있습니다. 양자화 뒤 처리량은 2.7배가 됐지만 Nsight에서 잰 GEMM 커널 실행시간은 거의 같았습니다. 교재는 이 차이를 `메모리 여유 → KV 캐시 확보 → 배칭 촘촘 → 스케줄링 효율`의 흐름으로 해석합니다. 연산이 빨라진 결과가 아니라 메모리 여유가 만든 간접 효과라는 설명입니다.
양자화를 켜면 KV 예산과 처리량이 동시에 늘어납니다. ON/OFF 비교만으로는 둘이 원인과 결과인지, 함께 나타난 변화인지 가려낼 수 없습니다. 그래서 FP8은 그대로 두고 KV 예산만 BF16 수준으로 되돌렸습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>실험</td>
<td>바꾼 것</td>
<td>물은 것</td>
</tr>
<tr>
<td>**F1a** KV 예산 스윕</td>
<td>`gpu_memory_utilization`만 0.45\~0.85</td>
<td>처리량은 KV 예산의 함수인가</td>
</tr>
<tr>
<td>**F1b** 제거 실험</td>
<td>FP8의 KV 예산을 BF16과 같게 조임</td>
<td>예산을 되돌리면 이득이 사라지는가</td>
</tr>
<tr>
<td>**F1c** 워크로드 격자</td>
<td>프리필·디코드 × 동시성 1·4·16·64</td>
<td>양자화가 지는 구간이 있는가</td>
</tr>
<tr>
<td>**F2** 프로파일링</td>
<td>연산자·커널 단위 계측</td>
<td>줄어든 시간은 어느 연산에서 나왔는가</td>
</tr>
</table>
### 실험 환경 {toggle="true"}
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
	2주차부터 사용한 측정 환경을 그대로 썼습니다. 모든 구성에 `max_model_len=4096`과 `max_num_seqs=64`를 고정했습니다. 실험별 차이는 `EXTRA_ARGS` env의 플래그 하나와 `GPU_MEMORY_UTILIZATION` env뿐이며 매니페스트는 수정하지 않았습니다.
	양자화 구성에는 `--quantization fp8`만 추가했습니다. 이 옵션은 BF16 체크포인트를 기동할 때 W8A8로 바꾸므로 새 모델 파일이 필요하지 않습니다. 체크포인트, 이미지, 실행 경로는 같고 가중치 정밀도만 달랐습니다.
	측정 워크로드는 4주차와 같은 두 종류입니다.
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
### 비교 조건과 측정 편차
각 구성의 기동 로그에서 `Maximum concurrency`를 먼저 기록했습니다. 이 값은 정적 공식이 아니라 vLLM의 기동 시 프로파일링 결과라 같은 설정에서도 롤아웃마다 달라질 수 있습니다. 실제 예산을 확인하지 않고 처리량부터 비교하면 통제하지 않은 차이를 기능의 효과로 오해하게 됩니다.
측정 잡음도 먼저 구했습니다. BF16 기준 구성을 세 번 반복했을 때 재현 편차는 **0.38%**(σ 3.3 tok/s)였습니다. 뒤에서 근거로 삼는 **+33.8%**는 이 편차보다 약 90배 큽니다.
---
## 2. KV 예산을 3.8배 늘려도 처리량은 그대로였다
제거 실험에 앞서 KV 예산과 처리량의 관계부터 측정했습니다. 예산과 처리량의 관계를 알아야 양자화로 늘어난 처리량 중 예산이 기여한 몫을 구분할 수 있습니다.
다른 조건은 고정하고 `gpu_memory_utilization`만 다섯 값으로 바꿨습니다. 이 값은 매니페스트의 env라 재배포 명령 한 줄로 조절했습니다. 두 워크로드는 한 번의 배포에서 연달아 측정해 같은 파드와 같은 KV 예산을 쓰도록 맞췄습니다.
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
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/4116a99f-9119-4d22-916c-8c4446253084/fig-f1-kv-budget-curve.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4664NFDRYNJ%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T033227Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEDsaCXVzLXdlc3QtMiJHMEUCIAE7KeoPjK4fRtihAhJvfcJ8895afsKHo2IM4rdcyqc%2BAiEAto3uUkJBUo4MsA5UPgR1wmo%2Fi1NF%2BqdJXp1JAuTYymgq%2FwMIBBAAGgw2Mzc0MjMxODM4MDUiDA%2BSAZjs2dTMSq7NFSrcA3pZUUtrwG%2BsUkWOlDlUTqfkLUxkYQTBrer4Vz3L9Dw6L8pJv37hwkpY%2FJffzjbr0SpbSL4EOPXNSPrslZ%2Fx3jN%2FkAF%2BwTbDpYD57b55hs%2F2lLGZF5e1aFQfwdmpHe%2BqR8ucy%2FcwbNdZ3xVJkxA7yXApyTn2G5Zro0qdWcsTSGbfGrfIjxGYitXMYSMozYEAGsF%2BcGMmkpNAyia%2FFBdhOSsYL%2Fg0IP0Hrqyr6%2BUSlfKuBcgNxS1KSOTE5pUha5wm%2BMsYhF%2BLGjRLrW8UCSIDNyg1AOiiumbRCTDRFaBtB5MwkzW7w0YZ3chZNlxAMW84C4K6%2BPwpHN%2Bt7tGHJx99teLCoJR2aHfB4dCdEs7H2wqHhC3PkgTsivxjYThb8gqv8rAvOL6gYznn1F0zDolhJC1nMGB9MBNQjUNTyiHl0hv%2FLgmKoxQ3sAhujS3r2k7scBjDwDXfN7xo1%2FR4zkl%2BJMkLkLfn8AvloLcwvn4Hdl2YkfMTicB47xWmdLeMbfxWOIZXOpWSy4%2F1ZP%2FeUrMfd9SHSZC9GUriW7W00BBJ9Hr0obvatMghUfKJLe6RutQnccmbyF7msTTb1gDnogxrj%2BmXNebEQzmdYxosFI0slJpPoSJBP605s2%2BwKUVVMI6C7tQGOqUB4C1mUILD7S3Eb2AfxVJ%2BiMgGbYzHjOk8PHYluTHuYdSZYaEsbU74uJ3fAmeVqgCaviSPmLJx3cOXcq%2BXf17pFspFobczU93q2XYpL3XFzdesDFmsSKvV1qFH%2F9VE9y296V7qMm3K6PtNnOxdF%2FkQgplNZOACgo%2BfrlIq%2FXMCLEdmuid%2FkkvjZLHbEpKoVSHxO%2BwfGCL8aKJen%2FMtxxHiZMAD10v8&X-Amz-Signature=71d357e995ac971b375e3a9d47f9d1565b6d0d8a159c9dced516b0422f057f4e&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*KV 예산을 3.8배 늘려도 처리량은 그대로였다*
예산을 3.80배 바꿨을 때 decode 처리량의 변동은 약 0.5%였습니다. 기준 구성의 재현 편차인 0.38%보다 크지만 예산이 늘수록 처리량이 오르는 추세는 나타나지 않았습니다. prefill에서 벌어진 5.3%도 한 방향의 추세가 아니었습니다.
prefill 처리량의 최솟값은 `util=0.55`에서 나왔습니다. 예산이 가장 큰 0.85에서도 처리량은 늘지 않았습니다.
### 예산이 남아 있으면 처리량은 달라지지 않는다
요청에 필요한 KV 캐시와 전체 예산을 비교하면 이유를 알 수 있습니다.
`decode` 요청 하나는 프롬프트 약 40토큰과 출력 512토큰을 합쳐 약 550토큰의 KV를 씁니다. 동시성 16의 수요는 8,800토큰입니다. 예산이 가장 작은 `util=0.45`에서도 64,048토큰을 담을 수 있으므로 필요한 양보다 7배가 많습니다. 이미 남는 예산을 더 늘려도 처리량은 달라지지 않습니다.
`prefill`은 프롬프트가 2,028토큰입니다. 서버의 `vllm:prompt_tokens_total` 증가분으로 확인한 값입니다. 동시성 64의 수요는 약 134,000토큰으로 `util=0.45` 예산의 두 배를 넘지만 처리량은 그대로였습니다. 프리필이 연산 바운드라 GPU에 더 많은 요청을 담아도 초당 계산하는 토큰 수는 늘지 않습니다. 연산기는 이미 포화 상태라 대기열만 길어집니다.
> KV 예산은 **동시에 몇 개를 담을 수 있는가**를 정하지, **초당 몇 토큰을 계산하는가**를 정하지 않습니다.
예산이 이미 남는 구간에서는 교재가 설명한 *KV 확보 → 배칭 촘촘 → 처리량*의 효과가 나타나지 않았습니다. 이 조건이 뒤의 제거 실험을 해석하는 기준입니다.
### 예산을 2.48x까지 줄이자 선점이 발생했다
앞선 스윕이 예산 병목 구간에 닿지 않았을 가능성도 확인했습니다. `util`을 더 낮춰 처리량이 꺾이는 지점을 찾았습니다.
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
곡선은 2.48x에서 꺾였습니다. 예산이 프리필 요청 넷을 겨우 담는 수준까지 줄자 처리량은 **−35%**, TTFT는 1.7배가 됐습니다.
vLLM은 실행 중인 요청을 네 번 선점했습니다. 10.15x 이상에서는 다시 평평했습니다.
`util=0.45`에서는 KV 사용률이 **0.995**까지 올랐습니다. 캐시가 거의 가득 찼는데도 처리량은 예산이 네 배 넉넉한 `util=0.85`와 같았습니다.
> **KV 캐시가 꽉 찼다는 것 자체는 문제가 아닙니다.** 문제는 GPU를 계속 바쁘게 할 만큼의 요청을 담지 못할 때 시작됩니다. 그 신호는 사용률이 아니라 **선점(preemption)** 입니다.
### `util=0.90`에서 기동하지 못한 이유 {toggle="true"}
	처음에는 `util`을 0.90까지 올릴 계획이었지만 서버가 기동하지 않았습니다.
	```plain text
ValueError: Free memory on device cuda:0 (10.79/11.99 GiB) on startup is less than
desired GPU memory utilization (0.9, 10.79 GiB).
	```
	GPU 용량은 11.99 GiB지만 기동 시 사용 가능한 메모리는 10.79 GiB였습니다. 윈도우 데스크톱이 나머지 1.2 GiB를 사용하고 있었습니다. 이 랩톱에서는 0.85를 상한으로 두고 0.45를 하한에 추가해 스윕 범위를 확보했습니다.
---
## 3. KV 예산을 되돌려도 FP8의 이득은 남았다
FP8을 켰을 때 KV 예산과 처리량이 함께 늘었습니다.
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
교재의 설명대로라면 늘어난 KV 예산이 처리량 증가의 원인이어야 합니다. 이를 확인하려고 FP8의 `gpu_memory_utilization`을 낮춰 `Maximum concurrency`를 BF16 수준으로 맞춘 세 번째 구성을 만들었습니다.
목표값은 임의로 고르지 않았습니다. BF16의 59.50x를 기준으로 실측 예산을 선형 보정해 다음 `util`을 구한 뒤 서버를 다시 기동했습니다.
```plain text
attempt 1: conc=70.20x -> next util=0.7204
attempt 2: conc=55.99x -> next util=0.7656
attempt 3: conc=60.95x -> 성립 (기준 59.50x 대비 오차 2.4%, ±5% 이내)
```
판정 기준은 실험 전에 정했습니다. ③이 ① 수준으로 내려가면 이득은 메모리에서 왔다고 봅니다. ②와 비슷하면 다른 경로에서 왔다고 봅니다.
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
<td>③ **FP8 · 예산 동결**</td>
<td>0.7656</td>
<td>**60.95x**</td>
<td>**2,261.0**</td>
<td>12.5</td>
<td>**+33.8%**</td>
<td>0.0073</td>
</tr>
</table>
③의 처리량은 내려가지 않았습니다. 예산을 BF16 수준으로 되돌린 뒤에도 이득은 유지됐고 오차 범위에서는 ②와 구분되지 않았습니다. 재현 편차가 0.38%라 측정 잡음으로 설명할 수도 없습니다.
**양자화가 만든 +33.7% 가운데 KV 예산이 기여한 몫은 0%였습니다.**
### ITL로 확인한 스텝 실행시간
처리량만으로는 어디서 시간을 줄였는지 알 수 없습니다. 처리량은 다음 두 경로에서 모두 늘어납니다.
- **한 스텝에서 처리하는 요청 수 증가**: 배칭이 촘촘해진 경우
- **한 스텝의 실행시간 감소**: 같은 작업을 더 빨리 처리한 경우
두 경로는 **토큰 간 간격(ITL)** 으로 구분됩니다. 배칭만 촘촘해졌다면 같은 스텝에 더 많은 요청이 들어가므로 ITL은 유지되거나 늘어납니다. 사용자 한 명이 받는 토큰 간격이 짧아질 근거는 없습니다.
실제 ITL은 0.0097초에서 0.0073초로 24.7% 줄었습니다. 스텝 수가 아니라 스텝 하나의 실행시간이 줄었다는 결과입니다.
W8A8이 줄이는 것은 스텝마다 읽는 가중치의 바이트 수입니다. 디코드는 토큰을 하나 만들 때마다 모델 가중치 전체를 읽습니다. 1.54B 파라미터는 BF16에서 약 3.1 GB, 8비트에서 약 1.5 GB입니다. 배치가 작을 때 디코드의 병목은 연산기보다 이 **가중치 읽기 대역폭**에 있으므로 읽을 양이 절반에 가까워지면 스텝도 빨라집니다.
가중치가 줄면서 KV 예산도 늘었습니다. 기동 로그의 증가분은 **+1.17 GiB**로, 전체 가중치를 8비트로 바꾼 이론값(약 1.5 GB)보다 조금 작았습니다. vLLM이 임베딩과 출력 레이어까지 양자화하지는 않기 때문입니다.
예산 증가는 같은 원인에서 나온 부수 효과였습니다. F1b에서는 이 효과를 제거한 뒤에도 처리량 이득이 남았습니다.
---
## 4. FP8은 모든 워크로드에서 빨랐지만 이득의 크기는 달랐다
4주차의 추측 디코딩은 같은 서버에서도 **+194.8%와 −52.8%** 사이를 오갔습니다. 워크로드와 동시성이 달라지자 이득이 손해로 바뀌었습니다. FP8에서도 같은 반전이 나타나는지 보려고 프리필·디코드 × 동시성 1·4·16·64, 구성마다 2회 측정했습니다.
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
여덟 칸에서 모두 이득이 났습니다. 폭은 +11.1%에서 +35.4%였고 손해로 바뀐 칸은 없었습니다.
W4A16 방식은 compute-bound 구간에서 역양자화 비용이 이득보다 커질 수 있습니다. 그런 지점을 예상했지만 이번 구성에서는 나타나지 않았습니다. 적어도 측정한 범위에서는 FP8 양자화가 추측 디코딩처럼 손해로 뒤집히지 않았습니다.
### 동시성이 높을수록 이득은 줄었다
부호는 유지됐지만 동시성이 높아질수록 이득은 작아졌습니다.
- `decode`: 34.6% → 35.4% → 34.3% → **15.1%**
- `prefill`: 33.5% → 29.8% → 24.6% → **11.1%**
3장에서 살펴본 가중치 읽기 비용으로 설명할 수 있습니다. 양자화는 스텝마다 다시 읽는 가중치의 바이트 수를 줄입니다. 가중치를 읽는 비용은 배치 안의 모든 요청에 나뉩니다. 동시 요청이 하나일 때는 3.1 GB를 읽어 토큰 하나를 만듭니다. 64개일 때는 같은 3.1 GB로 64토큰을 만듭니다. 배치가 커질수록 전체 시간에서 가중치 읽기가 차지하는 비중과 양자화가 줄일 몫이 함께 작아집니다.
`prefill`의 이득이 더 빠르게 줄어든 이유도 같습니다. 프리필은 처음부터 연산 바운드라 가중치 읽기의 비중이 디코드보다 작습니다.
> 양자화의 이득은 **가중치 읽기가 전체 시간에서 차지하는 비중**만큼입니다. 그 비중이 큰 곳(작은 배치·디코드)에서 이득이 큽니다. 비중이 작은 곳(큰 배치·프리필)에서는 작습니다.
이득의 크기는 **메모리 대역폭이 병목인 정도**를 따라갔습니다. KV 예산과는 무관했습니다.
> 동시성 64의 두 칸은 재현폭이 각각 1.9%와 4.4%였습니다. 이 랩에서 c=64는 10%까지 흔들리는 것으로 알려져 있어 그 두 칸의 값은 추세를 읽는 데만 쓰고 결론의 근거로는 쓰지 않았습니다.
---
## 5. 커널별로 나눠 본 실행시간
처리량과 ITL만으로는 어느 연산에서 시간을 줄였는지 알 수 없습니다. CH10의 순서에 따라 지표에서 타임라인, 다시 커널로 분석 범위를 좁혔습니다.
### 프로파일러 실행 경로를 바로잡은 과정 {toggle="true"}
	처음에는 Nsight Systems → PyTorch Profiler → Nsight Compute의 세 계층을 계획했지만 첫 도구부터 사용할 수 없었습니다.
	```plain text
$ kubectl -n llm-serving-lab exec <pod> -- sh -c "command -v nsys ncu"
NOT_FOUND
	```
	`vllm/vllm-openai:v0.23.0` 이미지에는 Nsight 바이너리가 없었습니다. 권한을 조정해도 해결되지 않는 조건이라 vLLM이 직접 제공하는 **PyTorch Profiler**만 사용했습니다.
	문서에 적힌 `VLLM_TORCH_PROFILER_DIR`도 v0.23.0에서는 동작하지 않았습니다.
	```plain text
WARNING [envs.py:2088] Unknown vLLM environment variable detected: VLLM_TORCH_PROFILER_DIR
$ curl -X POST .../start_profile
curl: (22) The requested URL returned error: 404
	```
	소스(`vllm/config/profiler.py`)를 확인하니 v0.23.0에서는 프로파일러 설정이 환경 변수에서 `--profiler-config.*` CLI 플래그로 옮겨가 있었습니다. 앞쪽 iteration을 건너뛰고 정해진 개수만 담는 옵션도 함께 적용해 트레이스를 1 MB 아래로 제한했습니다.
	```plain text
--profiler-config.profiler=torch
--profiler-config.torch_profiler_dir=/root/.cache/huggingface/profiles
--profiler-config.torch_profiler_with_stack=false
--profiler-config.delay_iterations=20 --profiler-config.max_iterations=100
	```
### 총합 대신 스텝당 시간으로 비교했다
두 트레이스의 커널 시간을 그대로 더하면 다음 결과가 나옵니다.
<table fit-page-width="true" header-row="true">
<tr>
<td></td>
<td>BF16</td>
<td>FP8</td>
</tr>
<tr>
<td>총 GPU 커널 시간</td>
<td>503.1 ms</td>
<td>622.8 ms</td>
</tr>
</table>
이 합계만 보면 FP8이 24% 더 느립니다. 앞의 처리량과 ITL 결과에 어긋납니다.
두 트레이스가 담은 구간부터 달랐습니다. 어텐션 커널은 BF16에서 1,624회, FP8에서 2,744회 호출됐습니다. 28층 모델이므로 각각 58스텝과 98스텝에 해당합니다. 같은 iteration 수를 지정했어도 부하가 끝난 시점이 달라 실제 수집량은 같지 않았습니다. 비교 단위를 스텝당 시간으로 맞춰야 합니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>역할</td>
<td>BF16 (스텝당)</td>
<td>FP8 (스텝당)</td>
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
### GEMM 경로에서 줄어든 시간
스텝당 커널 시간은 −26.7%, 서버 밖에서 잰 ITL은 −24.7%였습니다. 서로 다른 계측의 감소 폭이 맞아떨어졌습니다.
시간 감소는 선형 계층에 집중됐습니다. GEMM 경로는 −27.7%였지만 어텐션·KV 캐시 경로는 −0.1%였습니다. KV 캐시는 여전히 BF16이고 양자화가 바꾼 곳은 가중치를 읽는 경로뿐입니다. 3장에서 KV 예산을 되돌린 뒤에도 이득이 남은 이유와 일치합니다.
정규화·활성화 시간이 −98.6% 줄었지만 연산 자체가 사라지지는 않았습니다. FP8 커널 목록에는 `triton_red_fused__to_copy_abs_clamp_cutlass_scaled_mm...`이 있습니다. 활성화를 8비트로 낮출 때 필요한 절댓값·클램프·스케일 계산이 정규화와 한 커널로 합쳐졌습니다. 역양자화 비용까지 GEMM 경로에 포함한 결과가 **−27.7%**입니다.
### Ada의 FP8 커널은 교재와 다른 결과를 만들었다
CH9은 Nsight 상세 분석에서 양자화 전후 GEMM 커널 실행시간이 거의 같았다고 적었습니다. 그 관측이 연산보다 메모리에서 원인을 찾은 교재 결론의 근거입니다.
이번 랩에서는 GEMM 경로가 27.7% 빨라졌고 전체 감소분도 거의 이 경로에서 나왔습니다. 교재와 다른 하드웨어·양자화 방식이 만든 차이는 커널 이름에 드러납니다.
```plain text
BF16 : void cutlass::Kernel2<cutlass_80_wmma_tensorop_bf16_...>
FP8  : void cutlass::Kernel2<enable_sm89_to_sm90<cutlass::gemm...>>
```
`sm89`는 Ada 세대 텐서코어를 뜻합니다. FP8은 기존 커널의 실행시간을 줄인 것이 아니라 8비트 입력을 네이티브로 받는 다른 커널을 사용했습니다. 교재의 GPU 세대와 W4A16 계열 방식은 가중치만 4비트로 저장하고 계산 직전에 되돌리므로 GEMM 실행시간이 유지될 수 있습니다. 이번 결과만으로 교재의 결론을 일반화해 반박할 수는 없습니다.
> **양자화 방식과 하드웨어에 따라 성능이 개선되는 경로가 달라집니다.** 가중치만 줄이면 메모리 사용량이 줄고, 계산 정밀도까지 낮추면 커널 실행시간도 줄어듭니다. 두 경우를 양자화라는 한 단어로 묶으면 원인을 잘못 짚게 됩니다.
프로파일러로 지표만으로는 알 수 없던 차이를 확인했습니다. 처리량과 ITL로는 속도가 달라졌다는 사실까지만 알 수 있습니다. 어느 경로가 빨라졌는지는 커널 시간을 나눈 뒤에야 알 수 있었습니다.
---
## 6. Prometheus에서도 같은 결론을 확인했다
앞선 결과는 벤치마크 클라이언트와 0.4초 간격의 서버 지표로 측정했습니다. 운영 대시보드인 Prometheus에서도 같은 차이가 보이는지 다시 확인했습니다.
기존 기록만으로는 부족했습니다. Prometheus의 스크랩 주기는 15초인데 앞선 부하는 10\~20초짜리 버스트였습니다.
F1d에서 **0.998**까지 오른 KV 사용률도 Prometheus에는 **0.078**까지만 남았습니다. 두 스크랩 사이에 사용률이 최고점에 도달했다가 내려간 탓입니다.
> 짧은 버스트는 **나중에 대시보드에서 확인하기 어렵습니다.** 같은 조건의 부하를 **스크랩 주기보다 충분히 길게** 실행해야 변화가 기록에 남습니다.
세 상태를 3분씩 다시 실행했습니다. 이미 확인한 현상이 모니터링 화면에도 나타나는지 기록했습니다.
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
<td>예산이 놀고 있는 상태</td>
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
### 동시 실행 요청 수는 같고 처리량만 33.2% 올랐다
세 구간의 지표를 같은 화면에서 비교했습니다.
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
세 캡처는 같은 25분 창을 보여 줍니다. 그래프 시간축 기준 9월 2일 20:48\~21:13, UTC입니다. 21:01·21:05·21:09에 시작한 구간이 차례로 A·B·C입니다. 구간 사이의 공백은 서버를 재배포한 시간입니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/7a73e637-179f-47a0-a1f6-1fd8a79d8698/proof-w5-07-dash-kv-preempt.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4664NFDRYNJ%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T033227Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEDsaCXVzLXdlc3QtMiJHMEUCIAE7KeoPjK4fRtihAhJvfcJ8895afsKHo2IM4rdcyqc%2BAiEAto3uUkJBUo4MsA5UPgR1wmo%2Fi1NF%2BqdJXp1JAuTYymgq%2FwMIBBAAGgw2Mzc0MjMxODM4MDUiDA%2BSAZjs2dTMSq7NFSrcA3pZUUtrwG%2BsUkWOlDlUTqfkLUxkYQTBrer4Vz3L9Dw6L8pJv37hwkpY%2FJffzjbr0SpbSL4EOPXNSPrslZ%2Fx3jN%2FkAF%2BwTbDpYD57b55hs%2F2lLGZF5e1aFQfwdmpHe%2BqR8ucy%2FcwbNdZ3xVJkxA7yXApyTn2G5Zro0qdWcsTSGbfGrfIjxGYitXMYSMozYEAGsF%2BcGMmkpNAyia%2FFBdhOSsYL%2Fg0IP0Hrqyr6%2BUSlfKuBcgNxS1KSOTE5pUha5wm%2BMsYhF%2BLGjRLrW8UCSIDNyg1AOiiumbRCTDRFaBtB5MwkzW7w0YZ3chZNlxAMW84C4K6%2BPwpHN%2Bt7tGHJx99teLCoJR2aHfB4dCdEs7H2wqHhC3PkgTsivxjYThb8gqv8rAvOL6gYznn1F0zDolhJC1nMGB9MBNQjUNTyiHl0hv%2FLgmKoxQ3sAhujS3r2k7scBjDwDXfN7xo1%2FR4zkl%2BJMkLkLfn8AvloLcwvn4Hdl2YkfMTicB47xWmdLeMbfxWOIZXOpWSy4%2F1ZP%2FeUrMfd9SHSZC9GUriW7W00BBJ9Hr0obvatMghUfKJLe6RutQnccmbyF7msTTb1gDnogxrj%2BmXNebEQzmdYxosFI0slJpPoSJBP605s2%2BwKUVVMI6C7tQGOqUB4C1mUILD7S3Eb2AfxVJ%2BiMgGbYzHjOk8PHYluTHuYdSZYaEsbU74uJ3fAmeVqgCaviSPmLJx3cOXcq%2BXf17pFspFobczU93q2XYpL3XFzdesDFmsSKvV1qFH%2F9VE9y296V7qMm3K6PtNnOxdF%2FkQgplNZOACgo%2BfrlIq%2FXMCLEdmuid%2FkkvjZLHbEpKoVSHxO%2BwfGCL8aKJen%2FMtxxHiZMAD10v8&X-Amz-Signature=0ae1273ad8fdc2fa1cc12efd6d2be9d45594c2c9bdf2b681335e2f940a603485&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*Prometheus — KV 캐시 사용률과 누적 선점*
A와 B에서 동시 실행 요청 수는 모두 16개였습니다. KV 사용률은 FP8 쪽이 오히려 조금 낮았습니다(0.031 → 0.028). 배치 크기가 같은데 생성 처리량은 **1,703.6에서 2,269.3으로 33.2% 올랐습니다.**
벤치마크 클라이언트에서는 **+33.7%**, 대시보드에서는 **+33.2%**로 비슷한 차이가 났습니다. 요청 수가 같으므로 배칭이 촘촘해졌다는 해석은 성립하지 않습니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/9dbc0290-9df5-41ea-a425-63225044baec/proof-w5-08-dash-throughput.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4664NFDRYNJ%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T033227Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEDsaCXVzLXdlc3QtMiJHMEUCIAE7KeoPjK4fRtihAhJvfcJ8895afsKHo2IM4rdcyqc%2BAiEAto3uUkJBUo4MsA5UPgR1wmo%2Fi1NF%2BqdJXp1JAuTYymgq%2FwMIBBAAGgw2Mzc0MjMxODM4MDUiDA%2BSAZjs2dTMSq7NFSrcA3pZUUtrwG%2BsUkWOlDlUTqfkLUxkYQTBrer4Vz3L9Dw6L8pJv37hwkpY%2FJffzjbr0SpbSL4EOPXNSPrslZ%2Fx3jN%2FkAF%2BwTbDpYD57b55hs%2F2lLGZF5e1aFQfwdmpHe%2BqR8ucy%2FcwbNdZ3xVJkxA7yXApyTn2G5Zro0qdWcsTSGbfGrfIjxGYitXMYSMozYEAGsF%2BcGMmkpNAyia%2FFBdhOSsYL%2Fg0IP0Hrqyr6%2BUSlfKuBcgNxS1KSOTE5pUha5wm%2BMsYhF%2BLGjRLrW8UCSIDNyg1AOiiumbRCTDRFaBtB5MwkzW7w0YZ3chZNlxAMW84C4K6%2BPwpHN%2Bt7tGHJx99teLCoJR2aHfB4dCdEs7H2wqHhC3PkgTsivxjYThb8gqv8rAvOL6gYznn1F0zDolhJC1nMGB9MBNQjUNTyiHl0hv%2FLgmKoxQ3sAhujS3r2k7scBjDwDXfN7xo1%2FR4zkl%2BJMkLkLfn8AvloLcwvn4Hdl2YkfMTicB47xWmdLeMbfxWOIZXOpWSy4%2F1ZP%2FeUrMfd9SHSZC9GUriW7W00BBJ9Hr0obvatMghUfKJLe6RutQnccmbyF7msTTb1gDnogxrj%2BmXNebEQzmdYxosFI0slJpPoSJBP605s2%2BwKUVVMI6C7tQGOqUB4C1mUILD7S3Eb2AfxVJ%2BiMgGbYzHjOk8PHYluTHuYdSZYaEsbU74uJ3fAmeVqgCaviSPmLJx3cOXcq%2BXf17pFspFobczU93q2XYpL3XFzdesDFmsSKvV1qFH%2F9VE9y296V7qMm3K6PtNnOxdF%2FkQgplNZOACgo%2BfrlIq%2FXMCLEdmuid%2FkkvjZLHbEpKoVSHxO%2BwfGCL8aKJen%2FMtxxHiZMAD10v8&X-Amz-Signature=7f39fd498ea0fa3ee945886b3ad5f299c5eeb2ac1c5455c0e24030932f4eb1b3&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*Prometheus — 생성 처리량과 동시 실행 요청 수*
C에서는 KV 사용률이 0.81까지 올랐고 담기지 못한 요청 **60개**가 대기했습니다. vLLM은 실행 중인 요청을 **19번** 선점했습니다. A와 B의 선점은 모두 0이었습니다. 예산이 실제 병목일 때 나타나는 신호입니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/84db0e6d-6713-41a0-a440-5cd9097a5471/proof-w5-09-dash-queue-gpu.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4664NFDRYNJ%2F20260905%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260905T033227Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEDsaCXVzLXdlc3QtMiJHMEUCIAE7KeoPjK4fRtihAhJvfcJ8895afsKHo2IM4rdcyqc%2BAiEAto3uUkJBUo4MsA5UPgR1wmo%2Fi1NF%2BqdJXp1JAuTYymgq%2FwMIBBAAGgw2Mzc0MjMxODM4MDUiDA%2BSAZjs2dTMSq7NFSrcA3pZUUtrwG%2BsUkWOlDlUTqfkLUxkYQTBrer4Vz3L9Dw6L8pJv37hwkpY%2FJffzjbr0SpbSL4EOPXNSPrslZ%2Fx3jN%2FkAF%2BwTbDpYD57b55hs%2F2lLGZF5e1aFQfwdmpHe%2BqR8ucy%2FcwbNdZ3xVJkxA7yXApyTn2G5Zro0qdWcsTSGbfGrfIjxGYitXMYSMozYEAGsF%2BcGMmkpNAyia%2FFBdhOSsYL%2Fg0IP0Hrqyr6%2BUSlfKuBcgNxS1KSOTE5pUha5wm%2BMsYhF%2BLGjRLrW8UCSIDNyg1AOiiumbRCTDRFaBtB5MwkzW7w0YZ3chZNlxAMW84C4K6%2BPwpHN%2Bt7tGHJx99teLCoJR2aHfB4dCdEs7H2wqHhC3PkgTsivxjYThb8gqv8rAvOL6gYznn1F0zDolhJC1nMGB9MBNQjUNTyiHl0hv%2FLgmKoxQ3sAhujS3r2k7scBjDwDXfN7xo1%2FR4zkl%2BJMkLkLfn8AvloLcwvn4Hdl2YkfMTicB47xWmdLeMbfxWOIZXOpWSy4%2F1ZP%2FeUrMfd9SHSZC9GUriW7W00BBJ9Hr0obvatMghUfKJLe6RutQnccmbyF7msTTb1gDnogxrj%2BmXNebEQzmdYxosFI0slJpPoSJBP605s2%2BwKUVVMI6C7tQGOqUB4C1mUILD7S3Eb2AfxVJ%2BiMgGbYzHjOk8PHYluTHuYdSZYaEsbU74uJ3fAmeVqgCaviSPmLJx3cOXcq%2BXf17pFspFobczU93q2XYpL3XFzdesDFmsSKvV1qFH%2F9VE9y296V7qMm3K6PtNnOxdF%2FkQgplNZOACgo%2BfrlIq%2FXMCLEdmuid%2FkkvjZLHbEpKoVSHxO%2BwfGCL8aKJen%2FMtxxHiZMAD10v8&X-Amz-Signature=813897fd6e2062d38afc5da214c03c04cbb6a5bc2dbe6026186d16cc5982e9d5&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*Prometheus — 대기 요청 수와 GPU 사용률*
### GPU 사용률 99%만으로는 병목을 알 수 없다
GPU 사용률은 세 구간 모두 99%였습니다. 예산이 남은 A와 요청 60개가 대기한 C를 이 값만으로는 구분할 수 없었습니다.
GPU 사용률만 보고 병목을 판단하면 이 차이를 놓칩니다.
> **GPU 사용률 99%만으로는 효율과 수용 한계를 판단할 수 없습니다.** 같은 99%에서 처리량이 1,703이기도 하고 2,269이기도 했습니다. 사용률로는 GPU가 동작 중인지 알 수 있지만 어떤 작업에 시간이 걸리는지는 알 수 없습니다.
---
## 7. 이전 실험까지 같은 KV 예산 축에 놓았다
앞 그림의 가로축은 KV 예산입니다. BF16 스윕으로 만든 점선은 평평합니다. 가로축만 움직인 구성에서는 처리량이 달라지지 않았습니다. 선 위아래로 벗어난 구성에서만 다른 효과가 나타났습니다.
4주차에 측정한 두 구성도 추가 측정 없이 같은 그림에 표시했습니다. 실습 환경과 이미지가 같고 워크로드도 같은 `decode` c=16이어서 함께 비교했습니다.
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
<td>FP8 · 예산 동결</td>
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
점선보다 위에 있는 구성에서는 스텝 실행시간이 줄었고, 아래에 있는 구성에서는 스케줄러의 처리 여력이 줄었습니다. 두 결과 모두 KV 예산의 차이로는 설명되지 않습니다.
### 지난주에 제외했던 구성도 비교할 수 있었다
4주차에는 draft 모델 구성을 본문 비교에서 제외했습니다. 이유는 이랬습니다.
> *12GB에 1.5B와 0.5B를 같이 올리는 순간 KV 예산의 42%가 사라집니다. 이 상태의 숫자는 "추측 디코딩의 값"이 아닙니다. 손해에서 추측 디코딩 탓과 KV가 좁아진 탓을 분리할 수 없기 때문입니다.*
이번 스윕 결과는 그 판단과 달랐습니다. draft 구성의 34.38x는 이번에 측정한 구간(15.64x \~ 59.50x) 안쪽이고 그 구간에서 `decode` c=16 처리량은 **0.5%** 안에서 움직였습니다. 예산이 42% 줄어든 것은 그 구성의 손해에 기여하지 않았습니다.
분리할 수 없다고 판단했던 두 원인은 사실 분리할 필요가 없었습니다. 예산 쪽 기여가 0이므로 관측된 −49.7%는 전부 추측 디코딩 방식 자체에서 비롯됐습니다. 지난주의 제외는 과했고 그 근거는 측정이 아니라 추정이었습니다.
비교에서 제외하는 기준도 다시 생각했습니다. "조건이 달라졌으니 비교할 수 없다"고 말하려면 그 조건이 실제로 결과를 움직이는지 먼저 재야 합니다. 영향도 모른 채 비교에서 빼면 쓸 수 있는 정보까지 버리게 됩니다.
---
## 8. 운영에서 성능 개선의 원인을 확인하는 순서
이번 실험은 조건이 결과를 실제로 움직이는지 먼저 재고 기능의 효과를 분리하는 순서로 진행했습니다. 이 순서를 거꾸로 적용하면 기능을 켰을 때 함께 일어난 변화까지 모두 그 기능의 효과로 오해하게 됩니다.
### 8-1. 예산이 병목인지부터 잰다
`kubectl logs`에서 기동 로그 두 줄부터 확인합니다.
```plain text
GPU KV cache size: 243,696 tokens
Maximum concurrency for 4,096 tokens per request: 59.50x
```
이 예산과 실제 워크로드의 KV 수요를 비교합니다. KV 수요는 요청당 (프롬프트 + 출력) 토큰 수에 동시 요청 수를 곱해 구합니다. 그 값이 예산의 절반에도 못 미치면 예산은 병목이 아닙니다. 위에서 쓴 `decode` 워크로드는 요청 16개가 512토큰씩 만들어도 8천 토큰대라 예산 243,696토큰의 4%가 채 되지 않습니다. 그래서 예산을 3.8배 늘려도 아무 일도 일어나지 않았습니다.
부하 중 서버 지표를 볼 때도 주의할 점이 있습니다. `vllm:kv_cache_usage_perc`가 1에 가까워졌다고 메모리가 모자란 것은 아닙니다. 2장의 측정에서 `util=0.45`는 사용률 **0.995**인데 처리량은 예산이 네 배 넉넉한 구성과 같았습니다. 캐시는 원래 있는 만큼 씁니다.
메모리가 실제로 모자란 신호는 `vllm:num_preemptions_total`입니다. 이 값이 오르면 vLLM이 실행 중인 요청을 선점하고 있는 상태이며, 그때부터 처리량이 떨어집니다. 측정에서도 선점이 0인 동안에는 사용률이 99%든 44%든 처리량이 같았습니다. 선점이 난 지점에서만 35% 떨어졌습니다(6장의 대시보드에도 같은 신호가 남아 있습니다).
`DCGM_FI_DEV_GPU_UTIL`만으로도 병목을 판단하기 어렵습니다. 6장의 세 구간은 GPU 사용률이 전부 99%였는데 처리량은 224에서 2,269까지 열 배 차이가 났습니다. 사용률로는 GPU가 동작 중인지만 알 수 있습니다.
### 8-2. 원인으로 지목한 조건만 되돌린다
관찰만으로는 원인을 지목할 수 없습니다. 기능을 켜면 여러 가지가 동시에 바뀌기 때문입니다. 원인이라고 생각하는 것 하나만 되돌려 놓고 이득이 사라지는지 보는 편이 훨씬 빠릅니다.
이번 실험에서는 `gpu_memory_utilization`만 바꿨습니다. 양자화 구성의 예산을 기준 구성과 같은 값으로 조이는 데 재기동 3회, 약 5분이 들었고 그것으로 결론이 났습니다.
### 8-3. 처리량과 ITL을 함께 본다
처리량 증가는 두 경로에서 옵니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>관측</td>
<td>처리량</td>
<td>ITL</td>
<td>해석</td>
</tr>
<tr>
<td>배칭이 촘촘해짐</td>
<td>증가</td>
<td>유지 또는 증가</td>
<td>같은 스텝에 요청이 더 들어감</td>
</tr>
<tr>
<td>스텝이 빨라짐</td>
<td>증가</td>
<td>**감소**</td>
<td>커널 실행·가중치 읽기 시간이 줄었음</td>
</tr>
</table>
처리량 숫자 하나만 보면 둘이 구분되지 않습니다. ITL이 같이 줄었다면 메모리를 더 준다고 해서 더 빨라지지 않습니다.
### 8-4. 모델 적재와 추론 속도를 구분한다
환경에 따라 양자화를 도입하는 목적도 다릅니다.
- **모델이 GPU에 안 들어가는 경우** — 양자화는 *성능 최적화*가 아니라 **적재 가능 여부**의 문제입니다. 켜는 것 말고 선택지가 없습니다.
- **이미 들어가고 예산도 남는 경우** — 여기서 잰 상황입니다. 이때 처리량이 늘어난 이유는 메모리 용량보다 **가중치 읽기 대역폭**에 있으며 효과는 배치가 작은 디코드에서 가장 큽니다.
두 경우의 기대치가 다르므로 도입 전에 어느 쪽인지부터 정해야 합니다.
### 8-5. 비교를 버리기 전에 달라진 조건의 영향을 잰다
지난주에 저는 KV 예산이 42% 줄었다는 이유로 구성 하나를 비교에서 뺐습니다. 이번 측정에서 그 구간의 예산 변화가 처리량에 미치는 영향이 0.5%였음이 드러났습니다. 제외할 필요가 없던 데이터였습니다.
조건이 달라져 비교할 수 없다는 판단도 검증이 필요합니다. 대개는 그 조건의 영향을 한 번 측정하는 편이 비용도 적게 듭니다.
---
## 9. 이 결과의 적용 범위 {toggle="true"}
	이 수치는 12GB GPU 한 장에 1.5B 모델을 올린 구성에서 나왔습니다. 그 조건이 결론의 유효 범위를 정합니다.
	KV 예산이 남았던 것은 이 GPU와 모델의 조합 때문입니다. 1.5B 모델은 가중치가 약 3 GB라 12GB 중 6.5 GB가 KV로 남습니다. 모델이 커지면 이 여유가 먼저 사라집니다. 예컨대 같은 GPU에 7B를 올리면 가중치만 14 GB라 애초에 올라가지 않고 양자화는 *처리량 최적화*가 아니라 **적재 가능 여부**의 문제가 됩니다. 그 구간에서는 교재가 설명한 성능 개선 경로가 나타날 가능성이 큽니다. 예산이 병목인 상태이기 때문입니다.
	이 글에서 검토한 것은 **교재의 설명을 조건 없이 적용해도 되는지**였습니다.
	재현할 수 없었던 것도 명시해 둡니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>못 한 것</td>
<td>이유</td>
</tr>
<tr>
<td>CH9 본편 재현 (Qwen3-14B · L40S 48GB · A100 x8)</td>
<td>AWS GPU 쿼터가 `0`이라 GPU 인스턴스를 띄울 수 없음</td>
</tr>
<tr>
<td>TP=2 · PP=2 · MoE 전문가 병렬 · 2노드</td>
<td>GPU 1장</td>
</tr>
<tr>
<td>NVLink vs PCIe 인터커넥트 비교</td>
<td>물리적으로 불가</td>
</tr>
<tr>
<td>GPTQ · AWQ 등 사전 양자화 체크포인트 비교</td>
<td>FP8이 첫 시도에 떠서 다운로드 0으로 끝냈음. 다른 방식은 미측정</td>
</tr>
	</table>
	CH9의 실험을 그대로 재현하지는 못했고, 같은 질문을 12GB 환경에서 검토했습니다.
	### CUDA GPU에서만 재현한 결과다
	애플 실리콘 같은 통합 메모리 장비에서는 같은 실험을 그대로 재현할 수 없습니다. 여기서 쓴 두 도구가 모두 CUDA 전용이기 때문입니다.
	- **프로파일러** — Nsight Systems·Nsight Compute도, vLLM이 여는 PyTorch Profiler 경로도 CUDA 커널을 전제로 합니다.
	- **양자화 커널** — `--quantization fp8`이 부르는 것은 Ada 텐서코어용 FP8 GEMM입니다. 그 커널이 없는 장비에서는 같은 플래그가 같은 일을 하지 않습니다.
	그래서 "가중치 읽기 대역폭이 이득의 자리였다"는 이번 결론은 CUDA GPU에서 잰 값입니다. 통합 메모리 장비는 대역폭 구조 자체가 달라 비중이 다르게 나올 수 있고 그것은 별도의 측정이 필요한 질문입니다.
	### FP4는 이 실험의 범위 밖이다
	이 기록은 FP8까지만 다뤘습니다. 실제 최전선은 Blackwell 세대의 FP4로 옮겨갔고 그 세대에서는 숫자가 달라질 것입니다.
	세대가 바뀌면 수치의 크기는 달라져도 확인할 질문은 남습니다. 정밀도를 한 단계 더 낮추면 스텝마다 읽는 바이트가 더 줄고 하드웨어에 해당 정밀도의 텐서코어가 있으면 사용하는 커널도 달라집니다. 5장에서 확인한 FP8의 변화와 같은 원리입니다. 그러니 FP4에서도 물어야 할 것은 같습니다. **이득이 KV 예산에서 왔는가, 아니면 가중치를 읽고 계산하는 경로에서 왔는가.** 3장의 제거 실험은 양자화 포맷이 달라져도 같은 방식으로 적용됩니다.
	측정 자체의 한계도 둘 있습니다.
	- `e2e`와 wall time은 출력 길이가 흔들리므로 세션 사이 비교에 쓰지 않았습니다. 비교는 전부 같은 세션 안에서 이뤄졌습니다.
	- 동시성 64 구간은 같은 설정을 두 번 재도 10%까지 흔들립니다. 그래서 c=64에서 나온 10%대 차이는 결론의 근거로 쓰지 않았습니다.
---
## 부록 {toggle="true"}
	### 부록 A. 예산 동결 구성을 만드는 방법
	KV 예산은 vLLM이 기동할 때 실제로 프로파일링해서 정하는 값입니다. 정적 공식으로는 나오지 않습니다. 가중치 크기가 달라지면 남는 메모리도 달라지므로 `gpu_memory_utilization`을 계산만으로 맞출 수 없습니다.
	목표 예산에 가까워지도록 값을 조절하고 서버를 다시 기동했습니다. 현재 예산과 목표 예산의 차이를 `util`에 대한 기울기로 나눠 다음 값을 정하고 다시 재서 남은 오차를 줄입니다.
	```bash
# 기동 로그에서 Maximum concurrency 숫자만 꺼낸다
read_conc() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' \
    | tail -1 | grep -oE '[0-9.]+x$' | tr -d 'x'
}
	```
	세 번 만에 오차 2.4%로 들어왔습니다. ±5%라는 기준은 4주차에 쓰던 것을 가져왔습니다.
	6장에서 확인했듯 예산 차이는 이 구간에서 처리량을 움직이지 않으므로 ±5%로 맞추지 않았어도 결론은 같았을 것입니다. 그래도 맞춘 이유는 제거 실험의 성격 때문입니다. 예산 차이가 원인일 수 있다는 반론을 데이터로 미리 확인하려면 예산이 실제로 중요한지와 무관하게 같은 값에 놓고 재는 편이 낫습니다.
	### 부록 B. 왜 FP8을 골랐나
	설계 단계에서는 FP8 → GPTQ → AWQ를 한 번씩 시도하기로 했는데 첫 번째에서 끝났습니다.
	`--quantization fp8`은 BF16 체크포인트를 기동 시점에 W8A8로 바꿉니다. 사전 양자화된 별도 체크포인트를 받지 않아 추가 다운로드가 0이고 모델 파일·이미지·실행 경로가 BF16 구성과 완전히 같습니다. 구성 간 차이를 **가중치 정밀도 하나**로 좁히려는 선택이었습니다. 사전 양자화 체크포인트를 쓰면 양자화 방식뿐 아니라 **캘리브레이션 데이터와 레이어별 적용 범위**까지 함께 달라져 관측된 차이의 원인을 구분하기 어려워집니다.
	RTX 4080은 Ada 세대라 FP8 텐서코어가 있습니다. 그보다 이전 세대 GPU에서는 이 경로가 그대로 재현되지 않습니다.
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
	`prefill` 스윕에 `--unique-prefix`가 붙는 이유가 있습니다. 요청 프롬프트가 전부 같으면 prefix caching이 이를 하나로 합쳐 KV 수요가 1/64로 줄어듭니다. KV 예산이 병목인지 확인하려면 먼저 프롬프트가 합쳐지지 않도록 해야 합니다.
	### 부록 D. 지표 하나를 잘못 읽을 뻔했다
	KV 예산이 병목인지 확인하려고 서버 지표를 0.5초 간격으로 수집했는데 첫 시도에서 수집 파일이 전부 비어 있었습니다. 필터를 이렇게 썼기 때문입니다.
	```bash
grep -E '^vllm:(num_requests_running|kv_cache_usage_perc) '   # 이름 뒤에 공백을 요구
	```
	실제 노출 형식은 이름 뒤에 라벨 블록이 붙습니다.
	```plain text
vllm:num_requests_running{engine="0",model_name="qwen2.5-1.5b"} 16.0
	```
	빈 파일은 지표가 0이라는 뜻이 아니라 수집에 실패했다는 뜻이었습니다. 4주차에도 `vllm:iteration_tokens_total`을 스텝당 스케줄된 토큰으로 잘못 읽은 적이 있어 지표를 근거로 쓸 때는 값을 보기 전에 **행이 실제로 잡혔는지**부터 확인하기로 했습니다.
	같은 종류의 실수가 이 글에서 두 번 더 있었습니다. 첫 번째는 5장의 트레이스를 처음에 총합끼리 비교했을 때입니다. 그러면 FP8이 시간을 24% 더 쓴 것으로 읽히는데 두 트레이스가 담은 구간이 58스텝과 98스텝이라 그렇습니다. 다른 하나는 6장의 대시보드를 되짚어 찍으려던 것입니다. 15초 스크랩으로는 10초짜리 버스트의 피크가 남지 않아 KV 사용률 0.998이 기록에는 0.078로만 있었습니다.
	셋 다 원인이 같습니다. 숫자가 무엇을 세는지, 어떤 간격으로 수집되는지 먼저 확인하지 않았습니다.
---
## 참고 자료
- CH9 *LLM Optimization in Practice* — 이 글의 질문("처리량이 올랐다는 건 GPU가 더 빨리 계산해서인가, 덜 다시 계산해서인가")과, 양자화 전후 GEMM 커널 시간이 거의 같았다는 관측
- CH10 *Advancements in LLM Serving* — Nsight Systems → PyTorch Profiler → Nsight Compute의 계층적 좁히기 순서
- [vLLM 문서 — Quantization](https://docs.vllm.ai/en/latest/features/quantization/index.html)
- [vLLM 문서 — Profiling vLLM](https://docs.vllm.ai/en/latest/contributing/profiling.html)
- 이 저장소의 측정 원본 — `labs/wsl2-vllm-baseline/results/f*` 및 분석 `f-analysis.md`
