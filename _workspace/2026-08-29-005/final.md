**vLLM의 Speculative Decoding(추측 디코딩), Chunked Prefill, Prefix Caching은 항상 성능을 향상시키지는 않았습니다. 같은 GPU에서도 워크로드와 동시성에 따라 성능이 좋아지기도 하고, 오히려 악화되기도 했습니다.**
<callout icon="🎯" color="blue_bg">
	**먼저 볼 세 가지 결론**
	- **추측 디코딩:** 같은 서버에서도 처리량이 **+194.8%** 늘거나 **−52.8%** 줄었습니다.
	- **수용률:** 처리량이 **−52.8%** 감소한 구간에서도 **100.0%**였습니다. 추측이 모두 맞아도 느려질 수 있습니다.
	- **공통 메커니즘:** 세 기능은 vLLM 스케줄러의 같은 **`token_budget`**을 서로 다른 방식으로 사용합니다. 기능 자체보다 워크로드와 예산의 여유가 결과를 결정했습니다.
</callout>
## 결과 한눈에 보기
<table fit-page-width="true" header-row="true">
<colgroup>
<col>
<col>
<col width="344">
</colgroup>
<tr>
<td>실험</td>
<td>결과</td>
<td>운영에서 볼 점</td>
</tr>
<tr>
<td>**추측 디코딩**</td>
<td>처리량 **+194.8% → −52.8%**</td>
<td>높은 수용률만으로는 부족하며 동시성까지 함께 봐야 함</td>
</tr>
<tr>
<td>**Chunked Prefill**</td>
<td>혼합 부하에서 디코드 TTFT 증가: 작은 청크 **+10.5%**, 큰 청크 **+188.9%**</td>
<td>청크는 진입 대기를 줄이지만 실행 중 ITL 간섭은 없애지 못함</td>
</tr>
<tr>
<td>**Prefix Caching**</td>
<td>프리픽스를 공유할 때 TTFT p50 **8.0배** 개선, 공유하지 않으면 차이 없음</td>
<td>서버 플래그보다 실제 요청의 프리픽스 공유 여부가 중요함</td>
</tr>
</table>
운영에서 확인해야 할 것은 **이 기능이 빠른가**가 아닙니다. **현재 워크로드를 처리한 뒤에도 최적화에 사용할 토큰 예산이 남아 있는가**를 봐야 합니다.
## 용어 정리 {toggle="true"}
	<table fit-page-width="true" header-row="true">
<tr>
<td>용어</td>
<td>의미</td>
<td>이 글에서 보는 핵심</td>
</tr>
<tr>
<td>**Speculative Decoding**<br>(추측 디코딩)</td>
<td>여러 후보 토큰을 미리 생성한 뒤 한 번에 검증해 디코드 스텝을 줄이는 기법</td>
<td>수용률뿐 아니라 동시성과 토큰 예산의 여유가 중요함</td>
</tr>
<tr>
<td>**Chunked Prefill**</td>
<td>긴 prefill을 여러 스텝으로 나눠 스케줄링하는 기법</td>
<td>새 요청의 TTFT는 줄일 수 있지만 실행 중 ITL 간섭까지 없애지는 못함</td>
</tr>
<tr>
<td>**Prefix Caching**</td>
<td>여러 요청이 공유하는 prefix의 계산 결과를 재사용하는 기법</td>
<td>실제 요청이 동일한 prefix를 공유할 때만 효과가 나타남</td>
</tr>
<tr>
<td>**TTFT**</td>
<td>Time To First Token. 요청 후 첫 토큰이 반환되기까지의 시간</td>
<td>새 요청이 얼마나 빨리 응답을 시작하는지 보여주는 지표</td>
</tr>
<tr>
<td>**ITL**</td>
<td>Inter-Token Latency. 생성 중 토큰 사이의 지연 시간</td>
<td>응답이 시작된 뒤 얼마나 매끄럽게 생성되는지 보여주는 지표</td>
</tr>
<tr>
<td>**`token_budget`**</td>
<td>vLLM 스케줄러가 한 스텝에서 배정할 수 있는 토큰 예산</td>
<td>세 최적화 기법의 손익을 연결하는 공통 메커니즘</td>
</tr>
	</table>
---
<table_of_contents color="gray"/>
## 1. 무엇을 어떻게 측정했나
[지난 글](https://atlantic-andesaurus-8b9.notion.site/LLM-3c44c2420ac48157aaebe78f971e05c9?pvs=74)에서는 서빙 구조가 엔진 설정의 효과를 제한한다는 점을 다뤘습니다. 이번 질문은 그다음입니다. **같은 서빙 구조에서도 최적화 기능의 이득은 언제 손해로 바뀌는가?**
CH7은 compute-bound와 memory-bound의 차이를 설명하고, CH8은 vLLM이 요청을 토큰 단위로 스케줄하는 방식을 다룹니다. 이 글에서는 두 내용을 실제 vLLM에 적용해 추측 디코딩, chunked prefill, prefix caching의 성능이 바뀌는 조건을 측정했습니다.
<table fit-page-width="true" header-row="true">
<colgroup>
<col>
<col width="340">
<col>
</colgroup>
<tr>
<td>실험</td>
<td>바꾼 조건</td>
<td>관찰한 지표</td>
</tr>
<tr>
<td>**추측 디코딩**</td>
<td>ngram 5토큰 ON/OFF, 워크로드와 동시성 변경</td>
<td>처리량, 수용률</td>
</tr>
<tr>
<td>**Chunked Prefill**</td>
<td>청크 512/8192, 프리필·디코드 혼합 부하</td>
<td>TTFT, ITL, 처리량</td>
</tr>
<tr>
<td>**Prefix Caching**</td>
<td>서버 ON/OFF × 클라이언트 공유/미공유</td>
<td>적중률, TTFT, 처리량</td>
</tr>
</table>
각 실험에서는 기능을 켜고 끄면서 이득이 사라지는 지점을 찾았습니다. 모든 실험은 동일한 이미지와 설정에서 진행했으며, 실험별로 플래그 하나만 변경했습니다. 이전 실험에서는 이미지마다 vLLM 버전이 달라 계층 비용을 7%p 잘못 계산할 뻔했기 때문에 이번에는 실행 환경부터 통제했습니다. 결과가 나온 뒤에는 vLLM 스케줄러 소스를 읽어 세 기능이 같은 조건의 영향을 받는 이유를 확인했습니다.
### 실험 환경
<table fit-page-width="true" header-row="true">
<colgroup>
<col>
<col width="396">
</colgroup>
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
모든 구성에 `max_model_len=4096`, `gpu_memory_utilization=0.85`, `max_num_seqs=64`를 적용했습니다. 실험별 차이는 매니페스트의 `EXTRA_ARGS` 환경 변수로 전달되는 **플래그 하나뿐**입니다. 재현 명령은 부록 C에 있습니다.
측정에는 두 종류의 워크로드를 사용했습니다.
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
<td>입력 내용을 되짚는 prefill 지배 워크로드</td>
</tr>
</table>
---
## 2. 추측 디코딩은 언제 손해로 바뀌었나
추측 디코딩(ngram, 5토큰)을 켜고 긴 입력의 내용을 반복적으로 활용하는 `prefill` 워크로드를 측정했습니다. 비교 대상은 추측 디코딩을 끈 기준 구성(vanilla)입니다. 각 지점에서 64개 요청을 보냈고 두 구성을 각각 세 번 다시 띄워 측정을 반복했습니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/2d69a4d7-39d2-4f00-a717-a5c49f53c08f/fig-e1b-spec-boundary.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466Y5SRQPTS%2F20260829%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260829T101704Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIGjqceBMTadiAnAkiXonV%2FwjnoyXYSjFiTqJnc6mHMn%2BAiEAlRuX8xo47ogo8FilznPvrE3g2m3ty5G7nw6aB5zfpMsq%2FwMIYhAAGgw2Mzc0MjMxODM4MDUiDP5hBonRvEwuRcDciircA4QTrHDH8G2tQ31LhDuAc0oMpGM4K5pvHSPQWvxj9sPyBSDTl%2F37ykB61abv7LTLDBqpkhXE6DhSfYF9MQwEUl5diDLlkvmEmk7Xy5CTvLoWPFdFr6bImlMXeookcYZjkOLrUyCqJU6XIid1Nqtv%2FrtFgwtQ5I%2BWUUItJ7PB5oxosO3j81OWU7ELhKA8f6rHWvpKdy0oZStlrQtmmAVaN3cfL5WeCQMNM1dewncMhRBhTqRUF4JS7V7yHJA4jrzmpBfztgprf5t1CvmVz8uWwY5kMRHaNIjTfMhJG5a3iFvXpj4veQeDXOyj4QF6yCJdADyrpwE7RSbwVo3nAtXADQkJ0v2ltBYJfzhNktQOoEY%2BIpTgsZp6YX0Qzr0kjoKZOFyymVAhhk0DYTYLiXFghGaeUqR9KCDkheRFyAdrpqkNbChfU727c4bLyFGpKZG5MfXjFvNdy0n3fzivvLKXsvLeXWt%2B%2FfOVJoeTU87X%2BloK1xo5GZ7hL7C5Q3L9LDyVEAVTn5w5U3i0xf89TukwnFNe5RP7EPQFnD0tE6eP7%2BlK%2Bx4wAeIthP1suQ31w8K6V3LQElI3ujjgN%2Fwheuzf4mwd0JyoFZZ9I0oZEgAXBOk63DROT63WlVoRLnLvMJ%2FDytQGOqUB%2FJldloJvrrTd8ufBO%2Bba8pdbdjzUnZcx3dzR52qtttrhW6050wrjaDHlQiK4J3aE1w4K7wVMa1mRkw1NsI2MDY%2BDe5sT7jXBVAfqRq5UlJOBcGm6%2FMQEFaL2xoO%2B2T3TqCxnGQQqmERevEmG7maE9GnSTu1Rn%2FrmMMKRB1M8DvyA4oW%2BXY0ZG%2FMXDut0Ol0JLjDZyT300SouQ5GS1Hfl2mGt%2FLhd&X-Amz-Signature=8188fbf9f13eaca0224aff7dc14a2f112d1e030a856117624389e3e9fdb7ea4b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>기준 구성 평균 (범위)</td>
<td>ngram 평균 (범위)</td>
<td>차이</td>
</tr>
<tr>
<td>1</td>
<td>111.3 (111.2\~111.3)</td>
<td>328.1 (327.1\~329.4)</td>
<td>**+194.8%**</td>
</tr>
<tr>
<td>16</td>
<td>1,336.6 (1,319.6\~1,347.3)</td>
<td>2,472.9 (2,341.5\~2,593.4)</td>
<td>**+85.0%**</td>
</tr>
<tr>
<td>24</td>
<td>1,650.5 (1,637.9\~1,671.0)</td>
<td>2,718.8 (2,639.1\~2,763.3)</td>
<td>**+64.7%**</td>
</tr>
<tr>
<td>32</td>
<td>2,145.1 (2,138.8\~2,152.4)</td>
<td>2,967.0 (2,934.2\~2,992.2)</td>
<td>**+38.3%**</td>
</tr>
<tr>
<td>48</td>
<td>2,145.1 (2,117.3\~2,164.6)</td>
<td>2,724.1 (2,689.6\~2,769.6)</td>
<td>**+27.0%**</td>
</tr>
<tr>
<td>64</td>
<td>2,918.3 (2,895.8\~2,943.2)</td>
<td>1,377.4 (1,312.3\~1,450.1)</td>
<td>**−52.8%**</td>
</tr>
</table>
*(단위 tok/s. 각 지점 64요청 × 3회.)*
동시성 48에서는 세 번 모두 이득이었고 64에서는 세 번 모두 손해였습니다. 정확한 전환점까지 찾은 것은 아니지만, 이 구성에서 이득이 손해로 바뀌는 경계가 **동시성 48과 64 사이**에 있다는 사실은 반복 측정으로 확인했습니다.
대조용 `decode` 워크로드에서는 기존 동일 조건 측정의 모든 구간이 손해였습니다. 동시성 1에서 −12.1%, 4에서 −11.9%, 16에서 −17.4%, 64에서 −28.6%였습니다. 같은 기능이라도 출력이 입력 조각과 잘 맞는지, 동시에 처리할 요청이 얼마나 많은지에 따라 방향이 달라졌습니다.
<callout icon="🔍" color="gray_bg">
	**구성 비교도 함께 검증했습니다.** ngram 구성의 KV cache는 235,440토큰(`Maximum concurrency 57.48x`)으로 기준 구성의 243,696토큰(59.50x)보다 3.4% 작았습니다. 처리량 변화 폭인 +194.8%\~−52.8%를 이 차이만으로 설명하기는 어렵습니다. 기동 로그에는 ngram 5토큰 설정과 함께 speculative decoding 설정 때문에 스텝당 스케줄 토큰이 2,048로 제한돼 성능이 떨어질 수 있다는 vLLM 경고도 남았습니다.
</callout>
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/f12797b9-a634-41af-ba40-12eb9db20b78/proof-w4-06-e1b-startup.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466Y5SRQPTS%2F20260829%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260829T101704Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIGjqceBMTadiAnAkiXonV%2FwjnoyXYSjFiTqJnc6mHMn%2BAiEAlRuX8xo47ogo8FilznPvrE3g2m3ty5G7nw6aB5zfpMsq%2FwMIYhAAGgw2Mzc0MjMxODM4MDUiDP5hBonRvEwuRcDciircA4QTrHDH8G2tQ31LhDuAc0oMpGM4K5pvHSPQWvxj9sPyBSDTl%2F37ykB61abv7LTLDBqpkhXE6DhSfYF9MQwEUl5diDLlkvmEmk7Xy5CTvLoWPFdFr6bImlMXeookcYZjkOLrUyCqJU6XIid1Nqtv%2FrtFgwtQ5I%2BWUUItJ7PB5oxosO3j81OWU7ELhKA8f6rHWvpKdy0oZStlrQtmmAVaN3cfL5WeCQMNM1dewncMhRBhTqRUF4JS7V7yHJA4jrzmpBfztgprf5t1CvmVz8uWwY5kMRHaNIjTfMhJG5a3iFvXpj4veQeDXOyj4QF6yCJdADyrpwE7RSbwVo3nAtXADQkJ0v2ltBYJfzhNktQOoEY%2BIpTgsZp6YX0Qzr0kjoKZOFyymVAhhk0DYTYLiXFghGaeUqR9KCDkheRFyAdrpqkNbChfU727c4bLyFGpKZG5MfXjFvNdy0n3fzivvLKXsvLeXWt%2B%2FfOVJoeTU87X%2BloK1xo5GZ7hL7C5Q3L9LDyVEAVTn5w5U3i0xf89TukwnFNe5RP7EPQFnD0tE6eP7%2BlK%2Bx4wAeIthP1suQ31w8K6V3LQElI3ujjgN%2Fwheuzf4mwd0JyoFZZ9I0oZEgAXBOk63DROT63WlVoRLnLvMJ%2FDytQGOqUB%2FJldloJvrrTd8ufBO%2Bba8pdbdjzUnZcx3dzR52qtttrhW6050wrjaDHlQiK4J3aE1w4K7wVMa1mRkw1NsI2MDY%2BDe5sT7jXBVAfqRq5UlJOBcGm6%2FMQEFaL2xoO%2B2T3TqCxnGQQqmERevEmG7maE9GnSTu1Rn%2FrmMMKRB1M8DvyA4oW%2BXY0ZG%2FMXDut0Ol0JLjDZyT300SouQ5GS1Hfl2mGt%2FLhd&X-Amz-Signature=46e145afa2bc8dee6f8020e036a69d4c1fc7d9aa78be6d0d308dfa86861e9416&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*기동 로그에서 기능이 실제로 켜졌는지와 두 구성을 같은 조건에서 비교했는지 확인했습니다. 기능이 켜지지 않은 경우와 기능을 켰지만 성능이 나쁜 경우는 구분해야 합니다.*
---
## 3. 추측이 모두 맞아도 느려질 수 있는 이유
처음에는 추측이 자주 틀려서 느려졌다고 생각했습니다. 추측 디코딩은 draft 토큰을 여러 개 만든 뒤 본 모델이 검증합니다. 틀린 토큰은 버려야 하므로 수용률이 낮으면 낭비되는 연산이 늘어납니다.
`decode` 측정은 이 설명과 맞았습니다. 동시성 1에서는 draft 토큰 720개 중 376개(52.2%), 동시성 64에서는 5,145개 중 2,532개(49.2%)만 채택됐습니다. 약 절반의 추측이 버려졌고 처리량도 전 구간에서 감소했습니다.
하지만 `prefill` 반복 실험에서는 전혀 다른 결과가 나왔습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>반복</td>
<td>draft 토큰</td>
<td>채택 토큰</td>
<td>수용률</td>
</tr>
<tr>
<td>1</td>
<td>19,300</td>
<td>19,300</td>
<td>**100.0%**</td>
</tr>
<tr>
<td>2</td>
<td>19,300</td>
<td>19,300</td>
<td>**100.0%**</td>
</tr>
<tr>
<td>3</td>
<td>19,300</td>
<td>19,300</td>
<td>**100.0%**</td>
</tr>
<tr>
<td>**합계**</td>
<td>**57,900**</td>
<td>**57,900**</td>
<td>**100.0%**</td>
</tr>
</table>
동시성 1부터 64까지 생성한 draft 토큰이 하나도 버려지지 않았습니다. 그럼에도 동시성 64의 처리량은 세 번 모두 감소했습니다. 기준 구성과 비교하면 −55.4%\~−50.3%, 평균 **−52.8%**였습니다. 추측이 맞는지만으로는 이 손해를 설명할 수 없습니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/e2a5dfd3-b045-487c-84a2-b4c19eb74505/proof-w4-05-e1b-acceptance.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466Y5SRQPTS%2F20260829%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260829T101704Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIGjqceBMTadiAnAkiXonV%2FwjnoyXYSjFiTqJnc6mHMn%2BAiEAlRuX8xo47ogo8FilznPvrE3g2m3ty5G7nw6aB5zfpMsq%2FwMIYhAAGgw2Mzc0MjMxODM4MDUiDP5hBonRvEwuRcDciircA4QTrHDH8G2tQ31LhDuAc0oMpGM4K5pvHSPQWvxj9sPyBSDTl%2F37ykB61abv7LTLDBqpkhXE6DhSfYF9MQwEUl5diDLlkvmEmk7Xy5CTvLoWPFdFr6bImlMXeookcYZjkOLrUyCqJU6XIid1Nqtv%2FrtFgwtQ5I%2BWUUItJ7PB5oxosO3j81OWU7ELhKA8f6rHWvpKdy0oZStlrQtmmAVaN3cfL5WeCQMNM1dewncMhRBhTqRUF4JS7V7yHJA4jrzmpBfztgprf5t1CvmVz8uWwY5kMRHaNIjTfMhJG5a3iFvXpj4veQeDXOyj4QF6yCJdADyrpwE7RSbwVo3nAtXADQkJ0v2ltBYJfzhNktQOoEY%2BIpTgsZp6YX0Qzr0kjoKZOFyymVAhhk0DYTYLiXFghGaeUqR9KCDkheRFyAdrpqkNbChfU727c4bLyFGpKZG5MfXjFvNdy0n3fzivvLKXsvLeXWt%2B%2FfOVJoeTU87X%2BloK1xo5GZ7hL7C5Q3L9LDyVEAVTn5w5U3i0xf89TukwnFNe5RP7EPQFnD0tE6eP7%2BlK%2Bx4wAeIthP1suQ31w8K6V3LQElI3ujjgN%2Fwheuzf4mwd0JyoFZZ9I0oZEgAXBOk63DROT63WlVoRLnLvMJ%2FDytQGOqUB%2FJldloJvrrTd8ufBO%2Bba8pdbdjzUnZcx3dzR52qtttrhW6050wrjaDHlQiK4J3aE1w4K7wVMa1mRkw1NsI2MDY%2BDe5sT7jXBVAfqRq5UlJOBcGm6%2FMQEFaL2xoO%2B2T3TqCxnGQQqmERevEmG7maE9GnSTu1Rn%2FrmMMKRB1M8DvyA4oW%2BXY0ZG%2FMXDut0Ol0JLjDZyT300SouQ5GS1Hfl2mGt%2FLhd&X-Amz-Signature=1a493c928f89c7f6284c90586359c87c55dccd545ce243298230a797ccc0d9bc&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*Prometheus 카운터도 다섯 draft 위치가 모두 11,580회 채택됐고, 전체 채택/생성 비율이 1임을 보여줍니다.*
처리량이 감소한 이유는 두 가지였습니다.
<table fit-page-width="true" header-row="true">
<colgroup>
<col>
<col width="343">
<col>
</colgroup>
<tr>
<td></td>
<td>왜 손해가 나나</td>
<td>어디서 나나</td>
</tr>
<tr>
<td>**원인 A**</td>
<td>추측이 틀려서 (수용률 \~50%)</td>
<td>`decode` 전 구간</td>
</tr>
<tr>
<td>**원인 B**</td>
<td>**수용률은 높지만 토큰 예산이 부족해서** (수용률 100%)</td>
<td>`prefill` 동시성 64</td>
</tr>
</table>
원인 B는 한 스텝의 토큰 예산으로 설명됩니다. 동시성 1에서는 작은 배치의 디코드 단계가 **memory-bound** 상태라 연산 유닛에 여유가 있습니다. 남는 연산 자원으로 draft 토큰 5개를 검증하고 모두 채택하면 디코드 스텝을 줄여 +194.8%의 이득을 얻습니다.
동시성 64에서는 배치 크기가 커지면서 GPU 연산 자원이 포화되어 **compute-bound** 상태에 가까워집니다. 이때 draft 토큰 5개를 스케줄하면 같은 스텝에서 처리할 다른 요청의 토큰 수가 줄어듭니다. 수용률이 100%여도 전체 처리량은 평균 −52.8% 감소했습니다.
높은 수용률은 추측 디코딩이 이득을 내기 위한 필요조건일 뿐 충분조건은 아닙니다. 한 스텝의 토큰 예산에 여유가 있어야 합니다.
---
## 4. Chunked Prefill과 Prefix Caching에도 조건이 있었다
chunked prefill과 prefix caching도 결국 같은 토큰 예산의 영향을 받았습니다.
### 4-1. 작은 청크는 TTFT를 줄였지만 ITL은 줄이지 못했다
긴 prefill과 긴 디코드가 같은 GPU에서 실행되면 한쪽이 토큰 예산을 많이 사용할수록 다른 쪽이 기다립니다. chunked prefill은 긴 prefill을 여러 스텝으로 나눠 이런 간섭을 완화합니다. `--max-num-batched-tokens`는 한 스텝에 배치할 토큰 수의 상한을 정합니다.
prefill 지배 요청을 배경 부하로 실행한 상태에서 디코드 지배 요청을 추가하고, 처리량·TTFT·ITL 변화를 측정했습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>청크</td>
<td>디코드 처리량</td>
<td>디코드 **TTFT**</td>
<td>디코드 **ITL**</td>
</tr>
<tr>
<td>**512**</td>
<td>−12.4%</td>
<td>**+10.5%**</td>
<td>**+16.3%**</td>
</tr>
<tr>
<td>**8192**</td>
<td>−13.9%</td>
<td>**+188.9%**</td>
<td>**+16.6%**</td>
</tr>
</table>
*(각 값은 같은 서버에서 "디코드 단독"과 "prefill 배경 부하와 동시" 사이의 차이.)*
<callout icon="🔍" color="gray_bg">
	두 청크의 ITL 손실이 거의 같아 먼저 플래그가 적용됐는지 확인했습니다. 기동 로그에는 `Chunked prefill is enabled with max_num_batched_tokens=512.`와 `=8192.`가 각각 남아 있었습니다. KV 예산 차이도 244,000 대 240,352로 1.5%에 그쳤습니다. 설정이 빠진 상태에서 나온 결과는 아닙니다.
</callout>
실험 전에는 청크를 작게 하면 ITL 지터가 줄고 prefill TTFT는 늘어날 것으로 예상했습니다. 실제 결과는 달랐습니다.
- **ITL 손실은 청크 크기와 거의 무관했습니다.** 512에서는 +16.3%, 8192에서는 +16.6%였습니다. 청크를 16배 줄여도 실행 중인 디코드 요청이 겪는 간섭은 그대로였습니다.
- **디코드 TTFT 손실은 18배 차이 났습니다.** 512에서는 +10.5%, 8192에서는 +188.9%였습니다. 청크가 크면 긴 prefill 하나가 한 스텝을 차지해 새 디코드 요청이 시작되지 못하고 기다립니다.
- 그 대신 배경 prefill 처리량은 3.1% 감소했습니다.
작은 청크는 새 요청이 시작되기까지의 대기를 줄였지만, 실행 중인 요청 사이의 간섭은 줄이지 못했습니다.
청크를 512까지 줄여도 ITL 손실 **+16.3%**는 남았습니다. prefill과 디코드가 같은 GPU를 쓰는 동안에는 서로의 실행을 방해하기 때문입니다. 이 간섭을 없애려면 prefill/decode 인스턴스를 물리적으로 나누는 PD 분리가 필요합니다. GPU 한 장으로 진행한 이번 실험에서는 PD 분리가 필요한 이유까지만 확인했습니다.
prefill과 디코드는 같은 토큰 예산을 나눠 씁니다. 청크 크기는 prefill 요청 하나가 한 번에 쓸 수 있는 몫만 제한합니다. 두 작업이 같은 예산을 두고 경쟁한다는 사실은 달라지지 않습니다.
### 4-2. 프리픽스를 공유해야 Prefix Caching이 작동했다
Prefix Caching은 서버에서 기능을 활성화하는 것만으로 효과가 발생하지 않습니다. 여러 요청이 실제로 동일한 prefix를 공유해야 합니다. 이를 확인하기 위해 **서버 캐시 ON/OFF × 클라이언트 prefix 공유/미공유**의 2×2 조건으로 측정했습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>서버 캐시</td>
<td>클라이언트</td>
<td>적중률</td>
<td>TTFT p50</td>
<td>TTFT p95</td>
<td>처리량</td>
</tr>
<tr>
<td>**ON**</td>
<td>**공유**</td>
<td>**97.9%**</td>
<td>**0.038초**</td>
<td>**0.042초**</td>
<td>**411.3**</td>
</tr>
<tr>
<td>ON</td>
<td>미공유</td>
<td>0.8%</td>
<td>0.148초</td>
<td>0.273초</td>
<td>219.0</td>
</tr>
<tr>
<td>OFF</td>
<td>공유</td>
<td>(메트릭 없음)</td>
<td>0.304초</td>
<td>0.471초</td>
<td>240.1</td>
</tr>
<tr>
<td>OFF</td>
<td>미공유</td>
<td>(메트릭 없음)</td>
<td>0.147초</td>
<td>0.269초</td>
<td>218.0</td>
</tr>
</table>
효과는 prefix를 공유한 경우에만 나타났습니다.
- 같은 클라이언트에서 서버 플래그만 바꾸면 TTFT p50은 **8.0배**, p95는 **11.3배** 개선됐고 처리량은 **+71%**였습니다.
- prefix를 공유하지 않았을 때는 캐시를 켜도 차이가 없었습니다. TTFT p50은 0.148초와 0.147초, 처리량은 219.0과 218.0으로 1% 안의 차이였습니다.
- 서버에서 캐시를 켜더라도 클라이언트 요청이 prefix를 공유하지 않으면 적중률은 **0.8%**에 그쳤습니다.
Prefix Caching의 효과는 서버 설정 자체보다 워크로드의 prefix 공유 특성에 의해 결정됩니다. 이번 실험에서는 캐시 활성화 자체의 손실은 관찰되지 않았지만, prefix를 공유하지 않는 워크로드에서는 성능 이득도 나타나지 않았습니다.
prefix caching은 적중한 prefix만큼 prefill 연산을 없앱니다. 요청을 처리하기도 전에 필요한 토큰 계산량이 줄어드는 셈입니다. 요청끼리 공유하는 prefix가 없다면 줄일 연산도 없습니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/4c3eb7e3-a493-4343-99ef-a0e8a8e0818f/proof-w4-03-e3-prefix-cache-hit.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466Y5SRQPTS%2F20260829%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260829T101704Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIGjqceBMTadiAnAkiXonV%2FwjnoyXYSjFiTqJnc6mHMn%2BAiEAlRuX8xo47ogo8FilznPvrE3g2m3ty5G7nw6aB5zfpMsq%2FwMIYhAAGgw2Mzc0MjMxODM4MDUiDP5hBonRvEwuRcDciircA4QTrHDH8G2tQ31LhDuAc0oMpGM4K5pvHSPQWvxj9sPyBSDTl%2F37ykB61abv7LTLDBqpkhXE6DhSfYF9MQwEUl5diDLlkvmEmk7Xy5CTvLoWPFdFr6bImlMXeookcYZjkOLrUyCqJU6XIid1Nqtv%2FrtFgwtQ5I%2BWUUItJ7PB5oxosO3j81OWU7ELhKA8f6rHWvpKdy0oZStlrQtmmAVaN3cfL5WeCQMNM1dewncMhRBhTqRUF4JS7V7yHJA4jrzmpBfztgprf5t1CvmVz8uWwY5kMRHaNIjTfMhJG5a3iFvXpj4veQeDXOyj4QF6yCJdADyrpwE7RSbwVo3nAtXADQkJ0v2ltBYJfzhNktQOoEY%2BIpTgsZp6YX0Qzr0kjoKZOFyymVAhhk0DYTYLiXFghGaeUqR9KCDkheRFyAdrpqkNbChfU727c4bLyFGpKZG5MfXjFvNdy0n3fzivvLKXsvLeXWt%2B%2FfOVJoeTU87X%2BloK1xo5GZ7hL7C5Q3L9LDyVEAVTn5w5U3i0xf89TukwnFNe5RP7EPQFnD0tE6eP7%2BlK%2Bx4wAeIthP1suQ31w8K6V3LQElI3ujjgN%2Fwheuzf4mwd0JyoFZZ9I0oZEgAXBOk63DROT63WlVoRLnLvMJ%2FDytQGOqUB%2FJldloJvrrTd8ufBO%2Bba8pdbdjzUnZcx3dzR52qtttrhW6050wrjaDHlQiK4J3aE1w4K7wVMa1mRkw1NsI2MDY%2BDe5sT7jXBVAfqRq5UlJOBcGm6%2FMQEFaL2xoO%2B2T3TqCxnGQQqmERevEmG7maE9GnSTu1Rn%2FrmMMKRB1M8DvyA4oW%2BXY0ZG%2FMXDut0Ol0JLjDZyT300SouQ5GS1Hfl2mGt%2FLhd&X-Amz-Signature=3d4f0a9cbc95a37b6d15ef046acd92b3f1c21b21cf290c74196f8ad409243b23&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*약 2,400토큰짜리 같은 prefix를 세 번 보낸 소규모 확인에서는 적중률 66.5%, 캐시된 프롬프트 토큰 4,800개가 기록됐습니다. 첫 요청은 캐시가 비어 있어 전부 미스이므로 세 번 중 한 번이 미스면 적중률 상한은 약 67%입니다. 본 측정의 97.9%와 차이가 나는 이유는 캐시 성능이 달라서가 아니라 표본에서 첫 미스가 차지하는 비중이 다르기 때문입니다.*
---
## 5. 세 기능은 같은 토큰 예산을 쓴다
실험만으로는 세 기능이 모두 조건에 따라 성능이 달라진다는 사실까지만 알 수 있습니다. 이유는 vLLM 스케줄러 소스에 있습니다. 스케줄러는 prefill과 디코드를 별도 단계로 구분하지 않고, 각 요청의 `num_computed_tokens`가 `num_tokens_with_spec`에 도달하도록 토큰을 배정합니다. 소스 주석에는 이 방식 하나로 chunked prefill, prefix caching, speculative decoding을 모두 처리한다고 적혀 있습니다.
스케줄러가 비교하는 값은 두 가지입니다.
- `num_computed_tokens` — **어디까지 계산했나**
- `num_tokens_with_spec` — **어디까지 계산해야 하나** (= 프롬프트 + 출력 + **draft 토큰**)
매 스텝에서 두 값의 차이만큼 토큰을 스케줄하고 세 기법은 이 차이의 상한·시작점·끝점에 각각 관여합니다.
**① chunked prefill — 한 스텝에서 쓸 수 있는 토큰 수**
```python
self.max_num_scheduled_tokens = ... else self.scheduler_config.max_num_batched_tokens
...
token_budget = self.max_num_scheduled_tokens     # 매 스텝 이 값으로 초기화
...
num_new_tokens = min(num_new_tokens, token_budget)   # RUNNING·WAITING 양쪽에서 동일
token_budget -= num_new_tokens                        # 쓴 만큼 깎는다
```
`--max-num-batched-tokens`로 지정한 값이 매 스텝의 `token_budget`이 됩니다. running 요청을 waiting 요청보다 먼저 처리하므로 긴 prefill이 예산을 대부분 사용하면 새 디코드 요청에 배정할 토큰이 줄어듭니다. 4-1에서 확인한 TTFT 18배 차이를 만드는 경로입니다.
**② prefix caching — 이미 계산한 토큰 수**
```python
if request.num_computed_tokens == 0:
    new_computed_blocks, num_new_local_computed_tokens = (
        self.kv_cache_manager.get_computed_blocks(request))
    ...
num_new_tokens = request.num_tokens - num_computed_tokens
```
캐시는 요청이 처음 스케줄될 때 조회됩니다. 적중한 토큰 수만큼 `num_computed_tokens`가 0이 아닌 값으로 시작하므로 스케줄러는 해당 토큰을 다시 계산하지 않습니다. 공유된 prefix가 없으면 적중값이 0이라 스케줄할 토큰 수도 줄지 않습니다.
**③ 추측 디코딩 — 앞으로 계산할 토큰 수**
```python
num_new_tokens = (
    request.num_tokens_with_spec        # ← draft 토큰이 여기 들어 있다
    + request.num_output_placeholders
    - request.num_computed_tokens
)
```
추측 디코딩도 별도 예산을 사용하지 않습니다. draft 토큰 5개를 추가하면 해당 요청의 `num_new_tokens`가 5만큼 늘고 같은 `token_budget`에서 차감됩니다.
이 흐름은 3절의 수용률 100%와 처리량 −52.8%가 함께 나타난 이유를 설명합니다. 예산에 여유가 있을 때는 draft 토큰 5개를 추가해도 다른 요청에 영향이 작지만 예산이 부족할 때는 같은 5개가 다른 요청에 배정할 토큰을 줄입니다.
---
## 6. 최적화별 손익을 가르는 조건
<table fit-page-width="true" header-row="true">
<tr>
<td>기법</td>
<td>이득이 나는 조건</td>
<td>이득이 사라지는 조건</td>
<td>이번 실험 결과</td>
</tr>
<tr>
<td>**추측 디코딩**</td>
<td>배치에 여유가 있으며 추측이 맞을 때</td>
<td>배치가 차면 **수용률 100%여도** 손해</td>
<td>+194.8% \~ **−52.8%**</td>
</tr>
<tr>
<td>**chunked prefill**</td>
<td>prefill과 디코드가 섞여 들어올 때 (진입 지연)</td>
<td>실행 중 간섭(ITL)은 줄지 않음</td>
<td>TTFT 손실 +10.5% 또는 +188.9%</td>
</tr>
<tr>
<td>**prefix caching**</td>
<td>요청들이 prefix를 실제로 공유할 때</td>
<td>공유가 없으면 효과 없음</td>
<td>TTFT p50 8.0배 개선 또는 차이 없음</td>
</tr>
</table>
세 기능 모두 켜는 것만으로는 이득이 생기지 않았습니다. 차이는 토큰 예산을 어떻게 쓰고 줄이느냐에서 나왔습니다.
- Speculative Decoding은 **남는 토큰 예산을 활용해 추가 후보 토큰을 검증합니다.**
- Chunked Prefill은 **하나의 prefill 요청이 토큰 예산을 과도하게 점유하지 않도록 제한합니다.**
- Prefix Caching은 **이미 계산된 토큰을 재사용해 필요한 계산량 자체를 줄입니다.**
---
## 7. 운영에서 무엇부터 확인할 것인가
서빙 구조를 정한 뒤에는 아래 순서로 최적화 기능을 검토할 수 있습니다.
### 7-1. 프리필과 디코드 비중을 확인한다
입력이 짧고 출력이 긴 디코드 지배 워크로드인지, 입력이 길고 출력이 짧은 prefill 지배 워크로드인지, 두 종류가 함께 들어오는지를 먼저 확인합니다. 이 구분이 없으면 세 기능의 효과를 예측하기 어렵습니다.
### 7-2. 프리픽스 공유 여부부터 확인한다
여러 요청이 긴 prefix를 공유한다면 Prefix Caching을 먼저 검토합니다. prefix를 공유한 조건에서는 TTFT p50이 8.0배 개선됐고, 공유하지 않은 조건에서는 캐시 ON/OFF 간 유의미한 차이가 나타나지 않았습니다. 적용 조건을 확인하기 쉽고 이번 실험에서 관찰된 부작용도 작았습니다.
### 7-3. 혼합 부하에서는 프리필 청크를 줄인다
prefill과 디코드 요청이 함께 들어오면 작은 청크로 새 디코드 요청의 진입 지연을 줄일 수 있습니다. 디코드 TTFT를 크게 줄이는 대신 배경 prefill 처리량은 약 3% 감소했습니다. 다만 ITL 간섭까지 없어지지는 않으므로 지속 간섭을 줄이려면 GPU를 분리해야 합니다.
### 7-4. 추측 디코딩은 수용률과 동시성을 함께 본다
추측 디코딩은 워크로드에서 추측이 잘 맞는지와 평소 동시성에서 토큰 예산이 남는지를 함께 확인합니다. 둘 중 하나가 충족되지 않으면 처리량이 감소할 수 있습니다.
특히 저부하 측정만으로 적용 여부를 결정하면 안 됩니다. `prefill` 워크로드에서는 동시성 48에서 평균 +27.0%였지만 64에서는 평균 −52.8%로 방향이 바뀌었습니다. 두 지점 모두 세 번 같은 방향이었으므로 용량 계획과 성능 검증에 고동시성 구간을 포함해야 합니다.
### 7-5. 결과를 워크로드별로 분리해 기록한다
합산 지표만 보면 원인을 잘못 해석하기 쉽습니다. 기존 측정의 전체 수용률 68.7%만 사용했다면 추측 실패가 모든 손해의 원인이라는 결론에 머물렀을 것입니다. 워크로드별로 분리하고 반복한 뒤에야 수용률 100%에서도 처리량이 평균 −52.8%인 반례를 확인했습니다.
측정 결과는 세 기법이 모두 조건부라는 사실을 보여줬고 스케줄러 소스는 그 조건이 같은 `token_budget`에서 나온다는 점을 설명했습니다. 지난 글에서 확인한 것처럼 서빙 구조가 설정의 상한을 정합니다. 그 상한 안에서는 워크로드와 토큰 예산을 확인한 뒤 최적화 기능을 적용해야 합니다.
---
## 8. 실험의 한계와 적용 범위 {toggle="true"}
	이 실험은 경계의 위치를 확정한 것이 아닙니다. **같은 기능도 워크로드와 자원 여유에 따라 결과가 뒤집히며, 그 경계를 실측해야 한다는 점**을 확인했습니다. 다음 제약 안에서 결과를 읽어야 합니다.
	1. **전환점은 구간으로만 확인했습니다.** E1은 각 지점에서 64요청을 세 번 측정했습니다. 동시성 48은 세 번 모두 이득, 64는 세 번 모두 손해였고 64의 변화 폭은 −55.4%\~−50.3%였습니다. 정확히 어디서 방향이 바뀌는지는 48과 64 사이를 더 잘게 측정해야 합니다.
	2. **나머지 실험은 반복 수가 적습니다.** E2는 각 셀 1회, E3는 공유 조건만 3회 반복(±2%)했습니다. 따라서 chunked prefill과 prefix caching 수치는 이 환경에서 관측된 효과 크기로 읽어야 합니다.
	3. **모델 1종·GPU 1장.** Qwen2.5-1.5B, RTX 4080 Laptop 12GB. 더 큰 모델이나 여러 장에서는 예산의 여유가 달라 뒤집히는 경계도 옮겨집니다.
	4. **draft 모델 구성은 본문 비교에서 제외했습니다.** 측정은 했지만(부록 D) KV 예산이 기준 구성보다 **−42.2%**였습니다. 처리량 손실이 추측 디코딩 때문인지 줄어든 KV 예산 때문인지 분리할 수 없었습니다.
	5. **prompt_lookup_min/max는 기본값입니다.** 평탄화 플래그가 없어 조이지 않았습니다. 수용률의 최선값은 아닐 수 있습니다.
	6. **멀티 GPU 항목은 측정하지 않았습니다.** TP/PP, 2노드, MoE Expert Parallel, 실제 PD 분리, SGLang·TensorRT-LLM 비교는 GPU 한 장으로 검증할 수 없습니다. 4-1의 chunked prefill 실험에서는 PD 분리가 필요한 이유까지만 확인했습니다.
	7. **WSL 환경.** 매 기동에 `pin_memory=False` 경고가 뜹니다. 모든 구성에 동일하게 걸리므로 구성 사이 비교는 성립하지만 절대 성능은 네이티브 리눅스보다 낮습니다.
	8. **세션 간 e2e·wall time 비교는 어렵습니다.** `temperature=0`인데도 생성 길이가 세션마다 달랐습니다(2주차 51.1토큰 → 이번 36.0토큰). 처리량·ITL은 토큰당 지표라 비교에 사용할 수 있지만 **e2e 비교에는 적합하지 않습니다.**
---
## 부록
본문에 사용한 결과는 측정 오류를 바로잡고 비교 조건을 다시 확인한 값입니다. 아직 설명하지 못한 값은 핵심 비교와 분리했고, 조건을 동일하게 맞출 수 없었던 Draft Model 결과는 본문에서 제외했습니다. 재현 명령은 마지막에 따로 정리했습니다.
### 부록 A. 간섭 0%는 최적화 효과가 아니라 측정 오류였다 {toggle="true"}
	Chunked Prefill의 첫 측정에서는 디코드 단독 처리량이 887.9 tok/s, prefill과 함께 실행했을 때가 888.1 tok/s였습니다. 간섭이 사실상 0%였지만 최적화가 완벽하게 작동한 결과는 아니었습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>단계</td>
<td>측정 조건</td>
<td>관측</td>
</tr>
<tr>
<td>최초 측정</td>
<td>prefill 12요청, 약 1초 실행</td>
<td>디코드와 겹친 시간이 짧아 간섭 0%</td>
</tr>
<tr>
<td>원인 확인</td>
<td>디코드는 약 5초 실행</td>
<td>두 부하가 실제로 경쟁한 시간이 부족했음</td>
</tr>
<tr>
<td>수정 측정</td>
<td>prefill 160요청, 디코드보다 6\~7초 더 실행</td>
<td>디코드 처리량 −12.4%</td>
</tr>
	</table>
	<callout icon="✅" color="green_bg">
		**판정:** 두 프로세스를 동시에 시작하는 것만으로는 혼합 부하가 되지 않습니다. 본문의 Chunked Prefill 결과에는 실행 구간이 실제로 겹쳤는지 확인한 수정 측정만 사용했습니다.
	</callout>
### 부록 B. 설명하지 못한 값은 핵심 비교와 분리했다 {toggle="true"}
	Prefix Caching 실험에는 원인을 설명하지 못한 값이 하나 남았습니다. 캐시를 끈 상태에서 공유 프롬프트의 TTFT p50이 미공유 프롬프트보다 두 배가량 길었습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>구분</td>
<td>비교</td>
<td>결과</td>
<td>판정</td>
</tr>
<tr>
<td>미해결 값</td>
<td>Cache OFF에서 공유·미공유 비교</td>
<td>0.304초 vs 0.147초</td>
<td>원인 미확인</td>
</tr>
<tr>
<td>본문 핵심 비교</td>
<td>같은 공유 프롬프트에서 Cache ON·OFF 비교</td>
<td>0.038초 vs 0.304초</td>
<td>클라이언트 조건이 같아 비교 유효</td>
</tr>
	</table>
	공유 조건을 연속 세 번 측정해도 0.305 / 0.307 / 0.311초(±2%)였고, 미공유 조건을 마지막에 실행해도 0.148초였습니다. 따라서 단순한 워밍업이나 측정 순서만으로는 설명되지 않았습니다. 두 프롬프트의 길이 차이는 약 13토큰으로 전체 약 1,600토큰의 1% 미만이었습니다.
	<callout icon="⚠️" color="yellow_bg">
		**판정:** 미해결 값은 Cache OFF 상태에서 프롬프트 종류에 따라 생긴 차이입니다. 본문의 8.0배 개선은 같은 공유 프롬프트를 두고 서버 캐시만 켜고 끈 비교에서 나왔으므로 핵심 A/B 비교는 유지됩니다. 다만 미해결 값의 원인은 추가 실험이 필요합니다.
	</callout>
### 부록 C. Draft Model은 비교 조건이 달라 제외했다 {toggle="true"}
	ngram은 입력에 나온 조각으로 다음 토큰을 예측하므로 별도 모델을 GPU에 올리지 않습니다. Draft Model 방식은 Qwen2.5-0.5B를 추가로 올려야 했고, 그 차이만으로 사용할 수 있는 KV Cache가 크게 줄었습니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>GPU KV Cache</td>
<td>Maximum concurrency</td>
<td>기준 구성 대비</td>
</tr>
<tr>
<td>기준 구성</td>
<td>243,696 tokens</td>
<td>59.50x</td>
<td>—</td>
</tr>
<tr>
<td>ngram</td>
<td>235,440 tokens</td>
<td>57.48x</td>
<td>−3.4%</td>
</tr>
<tr>
<td>Draft Model 0.5B</td>
<td>140,832 tokens</td>
<td>34.38x</td>
<td>−42.2%</td>
</tr>
	</table>
	1.5B 메인 모델과 0.5B Draft Model을 12GB GPU에 함께 올리자 KV Cache가 기준 구성보다 42.2% 줄었습니다. 이 상태에서는 성능 저하가 추측 디코딩 자체 때문인지, 줄어든 KV Cache 때문인지 분리할 수 없습니다. 따라서 Draft Model 결과는 본문의 직접 비교에서 제외했습니다.
	#### 상세 측정값 {toggle="true"}
		수용률은 **40.1%**였습니다. 아래 값은 관측 결과이지만 비교 조건이 달라 ngram과 Draft Model의 우열을 뜻하지는 않습니다.
		<table fit-page-width="true" header-row="true">
<tr>
<td>워크로드</td>
<td>c</td>
<td>기준 구성</td>
<td>ngram</td>
<td>Draft Model</td>
<td>Draft 차이</td>
<td>Draft goodput</td>
</tr>
<tr>
<td>`decode`</td>
<td>1</td>
<td>116.1</td>
<td>102.0</td>
<td>58.6</td>
<td>−49.5%</td>
<td>100%</td>
</tr>
<tr>
<td>`decode`</td>
<td>64</td>
<td>4,745.5</td>
<td>3,388.3</td>
<td>717.7</td>
<td>−84.9%</td>
<td>0.0%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>1</td>
<td>112.1</td>
<td>335.4</td>
<td>107.5</td>
<td>−4.1%</td>
<td>100%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>64</td>
<td>2,934.1</td>
<td>1,359.9</td>
<td>1,147.6</td>
<td>−60.9%</td>
<td>100%</td>
</tr>
		</table>
		운영에서 가장 심각한 값은 `decode` c=64의 goodput 0.0%였습니다. 64요청 모두 e2e SLO 30초를 넘겼고 p95는 45.6초였습니다. 같은 지점에서 기준 구성과 ngram의 goodput은 100%였습니다.
	<callout icon="⚠️" color="yellow_bg">
		**판정:** 이 결과를 Draft Model 방식 자체의 열세로 일반화하면 안 됩니다. 이번 실험이 보여주는 것은 메모리가 빠듯한 GPU에서는 별도 모델이 KV Cache와 동시성 한도에 미치는 영향을 먼저 분리해야 한다는 점입니다.
	</callout>
### 부록 D. 재현 방법
재현할 때는 세 가지만 지키면 됩니다.
1. 같은 이미지와 공통 설정을 유지합니다.
2. 실험별 플래그 하나만 변경합니다.
3. 기동 로그, Prometheus Target, 결과 JSON을 함께 확인합니다.
#### 전체 재현 명령 {toggle="true"}
	```bash
# 공통 — 2주차 기준선과 같은 k3s 배포. 실험 플래그는 EXTRA_ARGS 하나로만 들어간다.
source labs/wsl2-vllm-baseline/redeploy.sh
redeploy MAX_MODEL_LEN=4096 GPU_MEMORY_UTILIZATION=0.85 MAX_NUM_SEQS=64 EXTRA_ARGS=''
	```
	```bash
# E1 — vanilla와 ngram을 각각 세 번 재기동하고 64요청으로 경계를 측정한다.
bash labs/wsl2-vllm-baseline/run_e1b.sh
	```
	```bash
# E2 — chunked prefill. prefill을 배경 부하로 깔고 그 한가운데서 디코드를 잰다(부록 A).
redeploy EXTRA_ARGS='--max-num-batched-tokens 512'
python3 benchmark.py --scenarios prefill --concurrency 8 --requests-per-level 160 \
  --warmup 0 --output results/e2-mnbt512-prefill-mixed.json &
sleep 2
python3 benchmark.py --scenarios decode --concurrency 8 --requests-per-level 8 \
  --warmup 0 --output results/e2-mnbt512-decode-mixed.json &
wait
	```
	```bash
# E3 — prefix caching. 서버 ON/OFF × 클라이언트 공유 ON/OFF = 2x2.
redeploy EXTRA_ARGS='--no-enable-prefix-caching'      # 또는 '' (ON)
python3 benchmark.py --scenarios prefill --concurrency 4 --requests-per-level 64 \
  --output results/e3-cacheoff-shared.json
python3 benchmark.py --scenarios prefill --concurrency 4 --requests-per-level 64 \
  --unique-prefix --output results/e3-cacheoff-unique.json
	```
	**플래그 이름은 추측하지 말고 확인하세요.** `vllm serve --help=all`입니다. 그냥 `--help`는 그룹 이름만 보여줍니다. v0.23.0은 `--speculative-config` JSON 대신 평탄화된 `--spec-method` / `--spec-model` / `--spec-tokens`를 제공합니다.
E1 스크립트는 동시성 1·16·24·32·48·64를 순회하고, 각 지점에서 64개 요청을 보냅니다. 결과는 `results/e1b-vanilla-r*.json`과 `results/e1b-ngram-r*.json`에 저장됩니다. 구성별 기동 로그와 Prometheus 카운터도 함께 남기므로 처리량, 기능 활성화 여부, 수용률을 같은 실행에서 대조할 수 있습니다.
#### 설정과 측정 경로 검증
같은 매니페스트를 플래그만 바꿔 재기동했을 때 ngram 구성의 KV 예산은 235,440토큰과 57.48배, chunked prefill 512 구성은 244,000토큰과 59.57배로 동일하게 관측됐습니다. 기동 로그에서 기능 플래그와 KV 예산을 확인하고, Prometheus Target이 `UP`인 상태에서 서버 카운터를 수집했습니다.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/acd63c07-5d6f-479e-9ed0-9c2442f4112f/proof-w4-01-prom-target-vllm-up.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466Y5SRQPTS%2F20260829%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260829T101704Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIGjqceBMTadiAnAkiXonV%2FwjnoyXYSjFiTqJnc6mHMn%2BAiEAlRuX8xo47ogo8FilznPvrE3g2m3ty5G7nw6aB5zfpMsq%2FwMIYhAAGgw2Mzc0MjMxODM4MDUiDP5hBonRvEwuRcDciircA4QTrHDH8G2tQ31LhDuAc0oMpGM4K5pvHSPQWvxj9sPyBSDTl%2F37ykB61abv7LTLDBqpkhXE6DhSfYF9MQwEUl5diDLlkvmEmk7Xy5CTvLoWPFdFr6bImlMXeookcYZjkOLrUyCqJU6XIid1Nqtv%2FrtFgwtQ5I%2BWUUItJ7PB5oxosO3j81OWU7ELhKA8f6rHWvpKdy0oZStlrQtmmAVaN3cfL5WeCQMNM1dewncMhRBhTqRUF4JS7V7yHJA4jrzmpBfztgprf5t1CvmVz8uWwY5kMRHaNIjTfMhJG5a3iFvXpj4veQeDXOyj4QF6yCJdADyrpwE7RSbwVo3nAtXADQkJ0v2ltBYJfzhNktQOoEY%2BIpTgsZp6YX0Qzr0kjoKZOFyymVAhhk0DYTYLiXFghGaeUqR9KCDkheRFyAdrpqkNbChfU727c4bLyFGpKZG5MfXjFvNdy0n3fzivvLKXsvLeXWt%2B%2FfOVJoeTU87X%2BloK1xo5GZ7hL7C5Q3L9LDyVEAVTn5w5U3i0xf89TukwnFNe5RP7EPQFnD0tE6eP7%2BlK%2Bx4wAeIthP1suQ31w8K6V3LQElI3ujjgN%2Fwheuzf4mwd0JyoFZZ9I0oZEgAXBOk63DROT63WlVoRLnLvMJ%2FDytQGOqUB%2FJldloJvrrTd8ufBO%2Bba8pdbdjzUnZcx3dzR52qtttrhW6050wrjaDHlQiK4J3aE1w4K7wVMa1mRkw1NsI2MDY%2BDe5sT7jXBVAfqRq5UlJOBcGm6%2FMQEFaL2xoO%2B2T3TqCxnGQQqmERevEmG7maE9GnSTu1Rn%2FrmMMKRB1M8DvyA4oW%2BXY0ZG%2FMXDut0Ol0JLjDZyT300SouQ5GS1Hfl2mGt%2FLhd&X-Amz-Signature=a8617b0536846073f8ab3ca2d5561b73a0c245e05fea9d95642f12276c12b09b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*vLLM의 **`/metrics`**를 Prometheus가 실제로 수집하는지 확인한 화면입니다. Target이 **`UP`**인 상태에서만 서버 측 카운터를 해석했습니다.*
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/eeef7fb9-3b5e-41fb-a9a2-a57ab85b6202/proof-w4-04-gpu-kv-two-boots.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466Y5SRQPTS%2F20260829%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260829T101704Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIGjqceBMTadiAnAkiXonV%2FwjnoyXYSjFiTqJnc6mHMn%2BAiEAlRuX8xo47ogo8FilznPvrE3g2m3ty5G7nw6aB5zfpMsq%2FwMIYhAAGgw2Mzc0MjMxODM4MDUiDP5hBonRvEwuRcDciircA4QTrHDH8G2tQ31LhDuAc0oMpGM4K5pvHSPQWvxj9sPyBSDTl%2F37ykB61abv7LTLDBqpkhXE6DhSfYF9MQwEUl5diDLlkvmEmk7Xy5CTvLoWPFdFr6bImlMXeookcYZjkOLrUyCqJU6XIid1Nqtv%2FrtFgwtQ5I%2BWUUItJ7PB5oxosO3j81OWU7ELhKA8f6rHWvpKdy0oZStlrQtmmAVaN3cfL5WeCQMNM1dewncMhRBhTqRUF4JS7V7yHJA4jrzmpBfztgprf5t1CvmVz8uWwY5kMRHaNIjTfMhJG5a3iFvXpj4veQeDXOyj4QF6yCJdADyrpwE7RSbwVo3nAtXADQkJ0v2ltBYJfzhNktQOoEY%2BIpTgsZp6YX0Qzr0kjoKZOFyymVAhhk0DYTYLiXFghGaeUqR9KCDkheRFyAdrpqkNbChfU727c4bLyFGpKZG5MfXjFvNdy0n3fzivvLKXsvLeXWt%2B%2FfOVJoeTU87X%2BloK1xo5GZ7hL7C5Q3L9LDyVEAVTn5w5U3i0xf89TukwnFNe5RP7EPQFnD0tE6eP7%2BlK%2Bx4wAeIthP1suQ31w8K6V3LQElI3ujjgN%2Fwheuzf4mwd0JyoFZZ9I0oZEgAXBOk63DROT63WlVoRLnLvMJ%2FDytQGOqUB%2FJldloJvrrTd8ufBO%2Bba8pdbdjzUnZcx3dzR52qtttrhW6050wrjaDHlQiK4J3aE1w4K7wVMa1mRkw1NsI2MDY%2BDe5sT7jXBVAfqRq5UlJOBcGm6%2FMQEFaL2xoO%2B2T3TqCxnGQQqmERevEmG7maE9GnSTu1Rn%2FrmMMKRB1M8DvyA4oW%2BXY0ZG%2FMXDut0Ol0JLjDZyT300SouQ5GS1Hfl2mGt%2FLhd&X-Amz-Signature=b8402a9c5ba4af262880c70ba59502bdf4250a3099bbc6b9017c2cbf73ccda5c&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
*GPU 메모리는 모델 가중치를 올릴 때 약 3.8GB, KV cache를 할당한 뒤 약 10.4GB로 두 단계에 걸쳐 증가했습니다. 앞 파드가 메모리를 반납한 뒤 다음 파드가 기동되는 흐름도 함께 확인할 수 있습니다.*
---
## 참고 자료
- [vLLM — Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode.html)
- [vLLM — Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html)
- [vLLM — Optimization and Tuning](https://docs.vllm.ai/en/latest/configuration/optimization.html)
- vLLM V1 스케줄러 소스: `vllm/v1/core/sched/scheduler.py` (v0.23.0)
<empty-block/>
<!-- HUMANIZE-SUMMARY
원본 글자수: 33,542자
윤문본 글자수: 31,999자
변경률: 약 18% (Notion 블록 이동·접기 구조 변경 포함 추정)
카테고리별 탐지: A-15 5→0, B-1 4→1, C-2 3→1, C-10 1→0, E-1 3→0, J-1 2→2(수치 강조로 의도적 보존)
자체검증: 6/6 통과
등급: A — S1 잔존 0건, S2 잔존 2건 이하, 추정 변경률 10~25%
주요 변경:
- 용어 정리 선행 → 핵심 결과 뒤의 접기 블록
- "세 가지 반전" → "먼저 볼 세 가지 결론"
- 네 역할이 섞인 부록 → 측정 오류·미해결 값·제외 실험·재현 방법으로 분리
- 긴 재현 명령과 상세 측정표 → 독립 접기 블록
- 혼용된 prefill·prefix 표기 → 한국어 본문과 기술 용어의 역할을 구분
-->

