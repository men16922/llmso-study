# 워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식

**추측 디코딩·chunked prefill·prefix caching을 비교해 각 기법이 이득을 내는 조건을 분리해 측정**

> **핵심 결과**<br>- 추측 디코딩의 처리량은 워크로드와 동시성에 따라 **+199.3%에서 −53.7%까지** 달라졌습니다. 같은 기법도 부하 조건이 바뀌면 이득이 손해로 뒤집혔습니다.<br>- 처리량이 **−53.7%** 감소한 구간에서도 수용률은 **100.0%**였습니다. 추측이 모두 맞아도 한 스텝의 토큰 예산이 부족하면 다른 요청의 실행 기회를 줄여 손해가 납니다.<br>- 세 기법은 vLLM 스케줄러의 같은 **`token_budget`**에 각각 다른 방식으로 관여합니다. 기능을 켜기 전에 워크로드가 어떤 자원을 쓰는지와 토큰 예산에 여유가 있는지를 먼저 확인해야 합니다.

---

<table_of_contents color="gray"/>
## 1. 무엇을 확인하려 했나

[지난 글](./%EC%84%9C%EB%B9%99%20%EC%B5%9C%EC%A0%81%ED%99%94%2C%20%EC%84%A4%EC%A0%95%EB%B6%80%ED%84%B0%20%EB%A7%8C%EC%A7%80%EB%A9%B4%20%EC%95%88%20%EB%90%98%EB%8A%94%20%EC%9D%B4%EC%9C%A0.md)에서는 서빙 구조가 엔진 설정의 효과를 제한한다는 점을 확인했습니다. 먼저 서빙 구조를 선택하고 그 안에서 설정을 조정해야 한다는 결론이었습니다.

이번에는 같은 서빙 구조 안에서 최적화 기법의 효과가 언제 달라지는지 살펴봤습니다. vLLM은 추측 디코딩, chunked prefill, prefix caching처럼 목적이 서로 다른 기능을 제공합니다. 각 기능의 이름만 보면 켜는 편이 유리해 보이지만 실제 효과는 워크로드와 부하 조건에 따라 달라질 수 있습니다.

<table fit-page-width="true" header-row="true">
<tr>
<td>기법</td>
<td>하는 일</td>
<td>기대 효과</td>
</tr>
<tr>
<td>**추측 디코딩**</td>
<td>다음 토큰 여러 개를 먼저 생성하고 본 모델이 한 번에 검증</td>
<td>한 스텝에서 여러 토큰 생성</td>
</tr>
<tr>
<td>**chunked prefill**</td>
<td>긴 프리필을 여러 청크로 나눠 디코드와 같은 스텝에 배치</td>
<td>프리필과 디코드의 간섭 완화</td>
</tr>
<tr>
<td>**prefix caching**</td>
<td>앞부분이 같은 요청들의 KV를 재사용</td>
<td>반복되는 프리필 연산 제거</td>
</tr>
</table>

교재 CH7은 이 기법들을 설명하기에 앞서 **compute-bound인가 memory-bound인가**를 묻습니다. 이 구분이 최적화 효과를 판단하는 공통 기준입니다.

이번 측정의 목적은 세 기법을 켜고 끄며 이득이 사라지는 조건을 찾고 그 조건이 하나의 기준으로 설명되는지 확인하는 것입니다. 모든 실험은 같은 이미지와 설정에서 진행했고 실험별로 플래그 하나만 바꿨습니다. 지난주에는 이미지마다 vLLM 버전이 달라 계층 비용을 7%p 잘못 계산할 뻔했기 때문에 이번에는 실행 환경부터 통제했습니다.

### 실험 환경

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

모든 구성에 `max_model_len=4096`, `gpu_memory_utilization=0.85`, `max_num_seqs=64`를 적용했습니다. 실험마다 다른 것은 매니페스트의 `EXTRA_ARGS` env로 들어가는 **플래그 하나뿐**입니다. 재현 명령은 부록 C에 있습니다.

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
<td>입력 내용을 되짚는 프리필 지배 워크로드</td>
</tr>
</table>

---

## 2. 추측 디코딩은 워크로드와 동시성에 따라 결과가 뒤집혔다

추측 디코딩(ngram, 5토큰)을 켜고 두 워크로드에서 측정했습니다. ngram 추측은 출력이 입력에 나온 조각을 되풀이할 때 수용률이 높아집니다. `decode`만 측정하면 기능의 효과와 워크로드 부적합을 구분할 수 없으므로 `prefill`을 함께 비교했습니다.

![추측 디코딩의 vanilla 대비 처리량 — prefill 워크로드는 동시성 1에서 +199%로 출발해 16까지 이득을 유지하다가 64에서 −53.7%로 0% 선 아래로 내려가고, decode 워크로드는 전 구간 0% 선 아래에서 동시성이 오를수록 더 내려간다](./figures/fig-e1-spec-decode.svg)

각 결과는 같은 서버에서 추측 디코딩을 끈 vanilla 구성과 비교했습니다.

<table fit-page-width="true" header-row="true">
<tr>
<td>워크로드</td>
<td>동시성</td>
<td>vanilla</td>
<td>ngram</td>
<td>차이</td>
</tr>
<tr>
<td>`decode`</td>
<td>1</td>
<td>116.1</td>
<td>102.0</td>
<td>**−12.1%**</td>
</tr>
<tr>
<td>`decode`</td>
<td>4</td>
<td>450.6</td>
<td>397.0</td>
<td>−11.9%</td>
</tr>
<tr>
<td>`decode`</td>
<td>16</td>
<td>1,641.8</td>
<td>1,356.2</td>
<td>−17.4%</td>
</tr>
<tr>
<td>`decode`</td>
<td>64</td>
<td>4,745.5</td>
<td>3,388.3</td>
<td>**−28.6%**</td>
</tr>
<tr>
<td>`prefill`</td>
<td>1</td>
<td>112.1</td>
<td>335.4</td>
<td>**+199.3%**</td>
</tr>
<tr>
<td>`prefill`</td>
<td>4</td>
<td>413.1</td>
<td>1,050.9</td>
<td>+154.4%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>16</td>
<td>1,375.2</td>
<td>2,519.8</td>
<td>+83.2%</td>
</tr>
<tr>
<td>`prefill`</td>
<td>64</td>
<td>2,934.1</td>
<td>1,359.9</td>
<td>**−53.7%**</td>
</tr>
</table>

*(단위 tok/s. 각 지점 8요청 1회.)*

결과를 바꾼 조건은 두 가지였습니다. 워크로드에 따라 같은 플래그와 서버에서도 한쪽은 3배가 되고 다른 쪽은 12% 손해였습니다. 동시성이 높아지면 3배가 나던 `prefill`도 동시성 64에서 절반 이하로 떨어졌습니다. 그래프에서는 초록 선이 0% 선 아래로 내려갑니다.

> **구성 비교가 성립하는지도 확인했습니다.** ngram 구성의 KV cache는 235,440토큰(`Maximum concurrency 57.48x`)으로 vanilla의 243,696토큰(59.50x)보다 3.4% 작았습니다. 위 표의 차이는 +199%~−54%이므로 KV cache의 3.4% 차이만으로 설명되지 않습니다. `vllm:spec_decode_*` 메트릭 8종이 ngram 구성에서만 나타나는 것도 확인했습니다. 기능이 켜지지 않은 상태와 기능을 켰지만 효과가 없는 상태를 구분하기 위한 점검입니다.

---

## 3. 수용률만으로는 손해를 설명할 수 없었다

첫 가설은 추측이 자주 틀려서 처리량이 감소한다는 것이었습니다. 추측 디코딩은 draft 토큰을 여러 개 생성한 뒤 본 모델이 검증합니다. 맞은 토큰은 사용하고 처음 틀린 토큰부터 버리므로 수용률이 낮을수록 낭비되는 연산이 늘어납니다.

`vllm:spec_decode_num_accepted_tokens_total / num_draft_tokens_total`로 계산한 전체 수용률은 **68.7%**였습니다. 그러나 두 워크로드를 합친 값이라 처리량 차이의 원인을 설명하지 못했습니다. 시나리오별로 카운터 증분을 분리했습니다.

<table fit-page-width="true" header-row="true">
<tr>
<td>워크로드</td>
<td>동시성</td>
<td>draft 토큰</td>
<td>채택</td>
<td>**수용률**</td>
<td>draft당 채택</td>
</tr>
<tr>
<td>`decode`</td>
<td>1</td>
<td>720</td>
<td>376</td>
<td>**52.2%**</td>
<td>2.61 / 5</td>
</tr>
<tr>
<td>`decode`</td>
<td>64</td>
<td>5,145</td>
<td>2,532</td>
<td>**49.2%**</td>
<td>2.46 / 5</td>
</tr>
<tr>
<td>`prefill`</td>
<td>1</td>
<td>400</td>
<td>400</td>
<td>**100.0%**</td>
<td>5.00 / 5</td>
</tr>
<tr>
<td>`prefill`</td>
<td>64</td>
<td>3,200</td>
<td>3,200</td>
<td>**100.0%**</td>
<td>5.00 / 5</td>
</tr>
</table>

`decode`에서는 약 절반의 draft 토큰만 채택됐습니다. 나머지 연산을 버려야 하므로 동시성 1처럼 GPU에 여유가 있는 구간에서도 처리량이 늘지 않았습니다.

![Prometheus에서 vllm:spec_decode_num_accepted_tokens_per_pos_total을 조회한 화면. draft 위치 0부터 4까지 채택 수가 113, 80, 62, 60, 60으로 뒤로 갈수록 줄고, 아래 쿼리의 전체 수용률은 0.6147로 나온다](./screenshots/proof-w4-02-e1-spec-decode-accept.jpg)

*재현 확인(2026-08-28). 표는 08-27 본 측정값이고 캡처는 같은 구성을 다시 띄워 요청 12개를 보낸 결과라 수용률이 61.5%로 다릅니다. 이 화면에는 위치별 채택 수가 113 / 80 / 62 / 60 / 60으로 감소하는 형태가 나타납니다. draft 토큰 5개 가운데 뒤쪽 토큰일수록 채택될 가능성이 낮아 `decode`의 draft당 채택 수가 5가 아니라 2.5 근처에 머뭅니다.*

`prefill` 동시성 64에서는 다른 결과가 나왔습니다. 처리량은 **−53.7%**였지만 draft 토큰 3,200개 중 3,200개가 모두 채택돼 수용률은 **100.0%**였습니다. 추측 실패만으로는 이 구간의 손해를 설명할 수 없었습니다.

워크로드별 수용률을 분리하면서 처리량이 감소한 원인도 둘로 나뉘었습니다.

<table fit-page-width="true" header-row="true">
<tr>
<td></td>
<td>왜 손해가 나나</td>
<td>어디서 나나</td>
</tr>
<tr>
<td>**원인 A**</td>
<td>추측이 틀려서 (수용률 ~50%)</td>
<td>`decode` 전 구간</td>
</tr>
<tr>
<td>**원인 B**</td>
<td>**맞아도 쓸 자리가 없어서** (수용률 100%)</td>
<td>`prefill` 동시성 64</td>
</tr>
</table>

원인 B는 한 스텝의 토큰 예산으로 설명됩니다. 동시성 1의 디코드는 가중치를 읽는 시간이 대부분인 **memory-bound** 상태라 연산 유닛에 여유가 있습니다. 남는 연산 자원으로 draft 토큰 5개를 검증하고 모두 채택하면 디코드 스텝 5개를 한 번에 줄여 +199%의 이득을 얻습니다.

동시성 64에서는 배치가 GPU를 채워 **compute-bound** 상태에 가까워집니다. 이때 draft 토큰 5개를 스케줄하면 같은 스텝에서 처리할 다른 요청의 토큰 수가 줄어듭니다. 수용률이 100%여도 전체 처리량은 −53.7% 감소했습니다.

높은 수용률은 추측 디코딩이 이득을 내기 위한 필요조건일 뿐 충분조건은 아닙니다. 한 스텝의 토큰 예산에 여유가 있어야 합니다.

---

## 4. 같은 토큰 예산으로 나머지 기법을 해석했다

추측 디코딩에서 확인한 토큰 예산을 기준으로 chunked prefill과 prefix caching의 결과도 해석했습니다.

### 4-1. 청크는 진입 지연을 줄이고 지속 간섭은 줄이지 못한다

긴 프리필과 긴 디코드가 같은 GPU에서 실행되면 한쪽이 토큰 예산을 많이 사용할수록 다른 쪽이 기다립니다. chunked prefill은 긴 프리필을 여러 스텝으로 나눠 이런 간섭을 완화합니다. `--max-num-batched-tokens`는 한 스텝에 배치할 토큰 수의 상한을 정합니다.

프리필 지배 요청을 배경 부하로 실행한 상태에서 디코드 지배 요청을 보내 디코드 지표가 얼마나 변하는지 측정했습니다.

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

*(각 값은 같은 서버에서 "디코드 단독"과 "프리필 배경 부하와 동시" 사이의 차이.)*

> ITL 손실이 두 청크에서 거의 같길래 **플래그가 조용히 무시된 것부터 의심했습니다.** 기동 로그를 보니 실제로 적용돼 있었습니다. `Chunked prefill is enabled with max_num_batched_tokens=512.` / `=8192.` KV 예산도 244,000 대 240,352로 1.5% 차이뿐입니다. 무효 측정이 아니라 실제 관측입니다.

예상과 달랐습니다. 계획에는 "청크를 작게 하면 ITL 지터가 줄고 프리필 TTFT는 늘어야 한다"고 적어 뒀는데 실제로는:

- **ITL 손실은 청크와 사실상 무관합니다** — +16.3% vs +16.6%. 청크를 16배 줄여도 한 번 돌기 시작한 디코드가 겪는 지속 간섭은 그대로입니다.
- **디코드 TTFT는 18배 갈립니다** — +10.5% vs +188.9%. 큰 청크는 긴 프리필 하나가 한 스텝을 통째로 차지하게 두므로 새로 도착한 디코드 요청이 진입하지 못하고 기다립니다.
- 대가는 배경 프리필 처리량 −3.1%뿐이었습니다.

청크가 사는 것은 진입 지연이고 못 사는 것은 지속 간섭입니다.

**이것이 PD 분리를 설명합니다.** 청크를 512까지 줄여도 ITL **+16.3%**는 남습니다. 같은 GPU에 프리필과 디코드가 함께 있는 한 서로를 미는 것 자체는 없어지지 않습니다. 없애려면 물리적으로 떼어야 하고 그게 prefill/decode 인스턴스를 분리하는 PD 분리입니다. GPU 한 장에서는 그 동기까지만 실측으로 보일 수 있습니다.

예산의 언어로 옮기면 프리필과 디코드는 **같은 예산을 놓고 경쟁**합니다. 청크는 프리필 하나가 한 번에 가져갈 수 있는 몫을 제한할 뿐 예산이 하나라는 사실을 바꾸지 못합니다.

### 4-2. prefix caching은 2×2 중 한 칸에서만 작동했다

캐시는 서버가 켠다고 되는 게 아닙니다. 요청들이 실제로 앞부분을 나눠 써야 합니다. **서버 캐시 ON/OFF × 클라이언트 공유 ON/OFF = 2×2**로 갈랐습니다.

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

한 칸만 다릅니다.

- **같은 클라이언트에서 서버 플래그만 바꾼 비교**(ON+공유 vs OFF+공유): TTFT p50이 **8.0배**, p95가 **11.3배**, 처리량 **+71%**. 이게 캐시의 값어치입니다.
- **공유가 없으면 캐시는 이득도 손해도 아닙니다** — ON+미공유 0.148초 vs OFF+미공유 0.147초. 처리량 219.0 vs 218.0. 오버헤드가 1% 안입니다.
- 서버가 켜도 클라이언트가 안 나누면 적중률 **0.8%**로 아무 일도 일어나지 않습니다.

캐시는 서버 설정이 아니라 워크로드의 성질입니다. 켜 두는 건 손해가 아니지만 켰다고 이득이 생기지도 않습니다.

예산의 언어로 옮기면 캐시 적중은 연산을 **아예 없앱니다.** 적중한 만큼 프리필이 사라지므로 그 요청은 처음부터 할 일이 줄어든 상태로 출발합니다. 공유가 없으면 지울 게 없습니다.

![Prometheus에서 vllm:prefix_cache_hits_total이 4800으로, 아래 쿼리의 적중률이 66.46%로 표시된 화면](./screenshots/proof-w4-03-e3-prefix-cache-hit.jpg)

*재현 확인(2026-08-28). 약 2,400토큰짜리 같은 프리픽스를 세 번 보내 적중률 66.5%·캐시된 프롬프트 토큰 4,800개를 확인했습니다. 본 측정의 97.9%보다 낮은 건 첫 요청이 통째로 미스이기 때문입니다 — 3회 중 1회가 미스면 상한이 약 67%입니다. 적중률은 이렇게 **표본이 작을수록 눌립니다.** 캐시가 덜 들은 게 아니라 나눠 쓸 요청이 아직 적은 것입니다.*

---

## 5. 세 기법이 이득을 내는 조건

<table fit-page-width="true" header-row="true">
<tr>
<td>기법</td>
<td>이득이 나는 조건</td>
<td>이득이 사라지는 조건</td>
<td>실측 폭</td>
</tr>
<tr>
<td>**추측 디코딩**</td>
<td>배치에 여유가 있고 **그리고** 추측이 맞을 때</td>
<td>배치가 차면 **수용률 100%여도** 손해</td>
<td>+199% ~ **−53.7%**</td>
</tr>
<tr>
<td>**chunked prefill**</td>
<td>프리필과 디코드가 섞여 들어올 때 (진입 지연)</td>
<td>지속 간섭(ITL)은 안 줄어듦</td>
<td>TTFT 18배 차이, ITL 무차별</td>
</tr>
<tr>
<td>**prefix caching**</td>
<td>요청들이 프리픽스를 실제로 공유할 때</td>
<td>공유가 없으면 무효 (손해도 아님)</td>
<td>8배 ~ **차이 없음**</td>
</tr>
</table>

세 줄이 같은 말을 합니다. 어느 것도 켜면 이득이 아니고 조건이 셋 다 예산 이야기입니다.

- 추측 디코딩은 **예산이 남을 때** 그 남는 자리를 씁니다.
- chunked prefill은 **하나가 예산을 독식하지 못하게** 막습니다.
- prefix caching은 **예산에서 할 일 자체를 뺍니다.**

---

## 6. vLLM 스케줄러에서 확인한 공통 원리

측정 결과만으로 확인되는 것은 세 기법이 모두 조건부라는 사실까지입니다. 같은 조건에 영향을 받는 이유는 vLLM 스케줄러 소스에서 확인했습니다. `vllm/v1/core/sched/scheduler.py`의 `schedule()` 앞에는 다음 주석이 있습니다.

> "There's no "decoding phase" nor "prefill phase" in the scheduler. Each request just has the `num_computed_tokens` and `num_tokens_with_spec`. (…) At each step, the scheduler tries to assign tokens to the requests so that each request's `num_computed_tokens` can catch up its `num_tokens_with_spec`. **This is general enough to cover chunked prefills, prefix caching, speculative decoding**, and the "jump decoding" optimization in the future."

스케줄러는 프리필과 디코드를 별도의 단계로 구분하지 않습니다. 각 요청에서 다음 두 값을 비교합니다.

- `num_computed_tokens` — **어디까지 계산했나**
- `num_tokens_with_spec` — **어디까지 계산해야 하나** (= 프롬프트 + 출력 + **draft 토큰**)

매 스텝에서 두 값의 차이만큼 토큰을 스케줄하고 세 기법은 이 차이의 상한·시작점·끝점에 각각 관여합니다.

**① chunked prefill — 한 걸음의 보폭 상한**

```python
self.max_num_scheduled_tokens = ... else self.scheduler_config.max_num_batched_tokens
...
token_budget = self.max_num_scheduled_tokens     # 매 스텝 이 값으로 초기화
...
num_new_tokens = min(num_new_tokens, token_budget)   # RUNNING·WAITING 양쪽에서 동일
token_budget -= num_new_tokens                        # 쓴 만큼 깎는다
```

`--max-num-batched-tokens`로 지정한 값이 매 스텝의 `token_budget`이 됩니다. running 요청을 waiting 요청보다 먼저 처리하므로 긴 프리필이 예산을 대부분 사용하면 새 디코드 요청에 배정할 토큰이 줄어듭니다. 4-1에서 확인한 TTFT 18배 차이를 만드는 경로입니다.

**② prefix caching — 출발선**

```python
if request.num_computed_tokens == 0:
    new_computed_blocks, num_new_local_computed_tokens = (
        self.kv_cache_manager.get_computed_blocks(request))
    ...
num_new_tokens = request.num_tokens - num_computed_tokens
```

캐시는 요청이 처음 스케줄될 때 조회됩니다. 적중한 토큰 수만큼 `num_computed_tokens`가 0이 아닌 값으로 시작하므로 스케줄러는 해당 토큰을 다시 계산하지 않습니다. 공유된 프리픽스가 없으면 적중값이 0이라 스케줄할 토큰 수도 줄지 않습니다.

**③ 추측 디코딩 — 결승선**

```python
num_new_tokens = (
    request.num_tokens_with_spec        # ← draft 토큰이 여기 들어 있다
    + request.num_output_placeholders
    - request.num_computed_tokens
)
```

추측 디코딩도 별도 예산을 사용하지 않습니다. draft 토큰 5개를 추가하면 해당 요청의 `num_new_tokens`가 5만큼 늘고 같은 `token_budget`에서 차감됩니다.

이 흐름은 3절의 수용률 100%와 처리량 −53.7%가 함께 나타난 이유를 설명합니다. 예산에 여유가 있을 때는 draft 토큰 5개를 추가해도 다른 요청에 영향이 작지만 예산이 부족할 때는 같은 5개가 다른 요청에 배정할 토큰을 줄입니다.

---

## 7. 실험의 한계 {toggle="true"}

	1. **c=64 재현 잡음.** 지난주 실측으로 동시성 64는 재현 측정에서 10%까지 흔들립니다(32 이하는 1.3% 안). E1의 −53.7%와 −28.6%는 그 범위를 크게 벗어나지만 10%대 차이는 결론의 근거로 쓰지 않았습니다.
	2. **반복 1회.** E3의 공유 조건 3회 반복(±2%)을 빼면 각 셀은 1회 측정입니다.
	3. **모델 1종·GPU 1장.** Qwen2.5-1.5B, RTX 4080 Laptop 12GB. 더 큰 모델이나 여러 장에서는 예산의 여유가 달라 뒤집히는 경계도 옮겨집니다. 이 글이 주장하는 것은 경계의 위치가 아니라 **경계가 있다는 것과 그 축이 무엇인가**입니다.
	4. **draft 모델 구성은 vanilla와 같은 저울에 못 올렸습니다.** 재기는 했고(부록 D) KV 예산이 **−42.2%**라 손해에서 "추측 디코딩 탓"과 "KV가 좁아진 탓"을 분리할 수 없습니다. 그래서 본문의 세 가격표에는 넣지 않았습니다.
	5. **`prompt_lookup_min/max`는 기본값.** 평탄화 플래그가 없어 조이지 않았습니다. 수용률의 최선값은 아닐 수 있습니다.
	6. **멀티 GPU 항목 전부 제외.** TP/PP, 2노드, MoE Expert Parallel, 실제 PD 분리, SGLang·TensorRT-LLM 비교는 GPU 한 장으로는 원천 봉쇄입니다. 4-1의 chunked prefill이 PD 분리의 **동기까지만** 대신합니다.
	7. **WSL 환경.** 매 기동에 `pin_memory=False` 경고가 뜹니다. 모든 구성에 동일하게 걸리므로 구성 사이 비교는 성립하지만 절대 성능은 네이티브 리눅스보다 낮습니다.
	8. **세션 간 `e2e`·wall time 비교 불가.** `temperature=0`인데도 생성 길이가 세션마다 달랐습니다(2주차 51.1토큰 → 이번 36.0토큰). 처리량·ITL은 토큰당 지표라 안전하지만 **`e2e`는 아닙니다.**

---

## 8. 워크로드를 확인한 뒤 최적화를 적용한다

지난 글에서는 서빙 구조를 먼저 선택하고 그 안에서 엔진 설정을 조정했습니다. 이번 결과를 더하면 각 최적화 기능은 다음 순서로 검토합니다.

### 8-1. 프리필과 디코드 비중을 확인한다

입력이 짧고 출력이 긴 디코드 지배 워크로드인지, 입력이 길고 출력이 짧은 프리필 지배 워크로드인지, 두 종류가 함께 들어오는지를 먼저 확인합니다. 이 구분이 없으면 세 기능의 효과를 예측하기 어렵습니다.

### 8-2. 프리픽스 공유 여부부터 확인한다

여러 요청이 긴 프리픽스를 공유한다면 prefix caching을 먼저 검토합니다. 공유하면 8배의 이득이 있고 공유하지 않으면 켜 둬도 손해가 없습니다. 적용 조건을 확인하기 쉽고 손해도 작았습니다.

### 8-3. 혼합 부하에서는 프리필 청크를 줄인다

프리필과 디코드 요청이 함께 들어오면 작은 청크로 새 디코드 요청의 진입 지연을 줄일 수 있습니다. 디코드 TTFT를 크게 줄이는 대가로 프리필 처리량 3%를 냈습니다. 다만 ITL 간섭까지 없어지지는 않으므로 지속 간섭을 줄이려면 GPU를 분리해야 합니다.

### 8-4. 추측 디코딩은 수용률과 동시성을 함께 본다

추측 디코딩은 워크로드에서 추측이 잘 맞는지와 평소 동시성에서 토큰 예산이 남는지를 함께 확인합니다. 둘 중 하나가 충족되지 않으면 처리량이 감소할 수 있습니다.

특히 저부하 측정만으로 적용 여부를 결정하면 안 됩니다. `prefill` 워크로드에서는 동시성 16까지 +83%였지만 64에서 −53.7%로 방향이 바뀌었습니다. 용량 계획과 성능 검증에 고동시성 구간을 포함해야 합니다.

### 8-5. 결과를 워크로드별로 분리해 기록한다

합산 지표만 보면 원인을 잘못 해석하기 쉽습니다. 전체 수용률 68.7%만 사용했다면 추측 실패가 모든 손해의 원인이라는 결론에 머물렀을 것입니다. 워크로드별로 분리한 뒤에야 수용률 100%에서도 처리량이 −53.7%인 반례를 확인했습니다.

측정 결과는 세 기법이 모두 조건부라는 사실을 보여줬고 스케줄러 소스는 그 조건이 같은 `token_budget`에서 나온다는 점을 설명했습니다. 지난 글에서 확인한 것처럼 서빙 구조가 설정의 상한을 정합니다. 그 상한 안에서는 워크로드와 토큰 예산을 확인한 뒤 최적화 기능을 적용해야 합니다.

---

## 부록 {toggle="true"}

	### 부록 A. 간섭이 0으로 나온 것은 측정 설계가 틀렸기 때문이다

	chunked prefill 첫 측정에서 간섭이 **정확히 0**으로 나왔습니다. 디코드 단독 887.9 tok/s, 프리필과 동시 실행 888.1 tok/s.

	기뻐할 뻔했습니다. "청크 512면 간섭이 없다"는 깔끔한 결론이니까요. 그런데 숫자가 너무 깨끗했습니다.

	원인은 **겹치지 않았던 것**입니다. 프리필 부하는 12요청이라 1초 만에 끝나는데 디코드는 5초를 돕니다. 동시에 띄우긴 했는데 겹치는 구간이 거의 없었습니다. 간섭을 재려는 실험에서 간섭할 기회 자체를 안 준 것입니다.

	프리필을 160요청짜리 배경 부하로 바꾸고 그것이 자리를 잡은 뒤 그 한가운데서 디코드를 재도록 고쳤습니다. **배경 부하가 디코드보다 몇 초 더 돌았는지를 매 회 기록해** 겹쳤다는 것을 숫자로 남깁니다(6~7초). 그러자 −12.4%가 나왔습니다.

	교훈: "동시에 실행한다"로는 부족하고 "지속 시간을 맞춘다"까지 해야 합니다. 그리고 **0에 가까운 깨끗한 결과는 측정 실패의 징후일 때가 많습니다.**

	> 참고로 `benchmark.py`는 시나리오를 **순차로** 돕니다(시나리오마다 별도 executor). `--scenarios prefill,decode`로는 애초에 안 섞입니다. 두 프로세스를 동시에 띄우는 것이 코드 수정 없는 유일한 방법이었습니다.

	### 부록 B. 설명하지 못한 관측 하나

	E3의 2×2에서 설명 못 한 칸이 있습니다. **캐시를 끈 서버에서 공유 프롬프트(0.304초)가 미공유 프롬프트(0.147초)보다 TTFT가 2배 느립니다.** 캐시가 꺼져 있는데 공유 여부가 왜 영향을 주는지 모르겠습니다.

	순서 효과를 의심했습니다. 공유 쪽이 늘 롤아웃 직후 첫 측정이었으니 워밍업 비용을 뒤집어썼을 수 있습니다. 그래서 같은 서버에서 공유 조건을 **연속 3회** 돌렸습니다: 0.305 / 0.307 / 0.311초(±2%). 미공유를 맨 마지막에 돌려도 0.148초였습니다. 워밍업이 아닙니다.

	프롬프트 차이는 앞에 붙는 `request-id=<hex32>` 약 13토큰뿐이고 전체가 ~1,600토큰이라 1% 미만입니다. e2e와 처리량은 오히려 공유 쪽이 낫습니다.

	**원인 미확인으로 남깁니다.** 다만 글의 결론에는 영향이 없습니다. 4-2의 헤드라인은 같은 클라이언트에서 서버 플래그만 바꾼 비교라 통제가 유지됩니다. 모르는 것을 아는 척하는 것보다 어디까지가 통제된 비교인지 밝히는 편이 낫다고 판단했습니다.

	### 부록 C. 재현 절차

	같은 이미지 하나를 플래그만 바꿔 다시 띄우는 것이 전부입니다.

	```bash
	# 공통 — 2주차 기준선과 같은 k3s 배포. 실험 플래그는 EXTRA_ARGS 하나로만 들어간다.
	source labs/wsl2-vllm-baseline/redeploy.sh
	redeploy MAX_MODEL_LEN=4096 GPU_MEMORY_UTILIZATION=0.85 MAX_NUM_SEQS=64 EXTRA_ARGS=''
	```

	```bash
	# E1 — 추측 디코딩. 구성마다 기동 로그(KV 예산)와 메트릭 존재를 먼저 확인할 것.
	redeploy EXTRA_ARGS='--spec-method ngram --spec-tokens 5'
	curl -s localhost:8000/metrics | grep spec_decode     # 비어 있으면 안 켜진 것 — 측정 금지
	python3 benchmark.py --scenarios decode,prefill --concurrency 1,4,16,64 \
	  --requests-per-level 8 --output results/e1-ngram.json
	```

	```bash
	# E2 — chunked prefill. 프리필을 배경 부하로 깔고 그 한가운데서 디코드를 잰다(부록 A).
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

	측정 원본과 상세 분석은 `labs/wsl2-vllm-baseline/results/`의 `e-analysis.md`, 스케줄러 소스 해부는 `e4-scheduler-notes.md`에 있습니다.

	#### 재현이 되는지 실제로 확인했습니다 (2026-08-28)

	측정 다음 날, 같은 매니페스트를 플래그만 바꿔 두 번 다시 띄웠습니다. **기동 로그의 KV 예산이 한 자리도 틀리지 않고 같았습니다.**

	<table fit-page-width="true" header-row="true">
	<tr>
	<td>구성</td>
	<td>08-27 본 측정</td>
	<td>08-28 재현</td>
	</tr>
	<tr>
	<td>ngram 추측 디코딩</td>
	<td>235,440 tokens / 57.48x</td>
	<td>**235,440 tokens / 57.48x**</td>
	</tr>
	<tr>
	<td>chunked prefill 512</td>
	<td>244,000 tokens / 59.57x</td>
	<td>**244,000 tokens / 59.57x**</td>
	</tr>
	</table>

	KV 예산은 정적 공식이 아니라 **기동 시 프로파일링 결과**라 롤아웃마다 흔들릴 수 있습니다(2주차에는 같은 설정에서 59.50x와 28.77x로 갈린 적이 있습니다). 그게 이번에는 소수점까지 재현됐다는 뜻이고 구성 사이의 예산 차이를 근거로 쓴 본문의 논증이 그만큼 단단해집니다.

	![Prometheus Target health 화면. serviceMonitor/monitoring/vllm-baseline/0이 1/1 up이고 엔드포인트 10.42.0.64:8000/metrics의 상태가 UP으로 표시된다](./screenshots/proof-w4-01-prom-target-vllm-up.jpg)

	*측정 체인 확인 — vLLM의 `/metrics`를 Prometheus가 실제로 긁고 있습니다. 이게 UP이 아니면 이 글의 서버 측 숫자는 전부 무의미합니다.*

	![Prometheus에서 DCGM_FI_DEV_FB_USED를 25분 구간으로 조회한 그래프. 0에서 약 3.8GB로 올랐다가 10.4GB로 한 번 더 오르는 계단이 11시 15분과 11시 19분에 두 번 나타난다](./screenshots/proof-w4-04-gpu-kv-two-boots.jpg)

	*재현 두 번이 GPU 메모리에 그대로 찍혔습니다. 계단이 두 번인 이유는 **모델 가중치 로드(약 3.8GB) → KV 캐시 할당(약 10.4GB)** 이 순서로 일어나기 때문입니다. 두 번째 기동에서 앞 파드가 메모리를 완전히 반납한 뒤에야 다음이 올라간 것도 보입니다 — GPU 1장에서 롤링 업데이트가 교착하는 이유가 이 그림에 있습니다.*

	### 부록 D. draft 모델 구성을 같은 저울에 못 올린 이유

	추측 디코딩에는 두 방식이 있습니다. **ngram**은 입력에 나온 조각을 되풀이해 찍고, **draft 모델**은 작은 모델(여기서는 Qwen2.5-0.5B)에게 찍게 합니다. 본문은 ngram만 다뤘는데, draft 구성도 재기는 했습니다. 결과가 본문에 못 들어간 이유를 적습니다.

	**KV 예산에서 이미 갈렸습니다.**

	<table fit-page-width="true" header-row="true">
	<tr>
	<td>구성</td>
	<td>GPU KV cache</td>
	<td>Maximum concurrency</td>
	<td>vanilla 대비</td>
	</tr>
	<tr>
	<td>vanilla</td>
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
	<td>**draft 0.5B**</td>
	<td>**140,832 tokens**</td>
	<td>**34.38x**</td>
	<td>**−42.2%**</td>
	</tr>
	</table>

	12GB에 1.5B와 0.5B를 같이 올리는 순간 KV 예산의 **42%가 사라집니다.** 이 상태의 숫자는 "추측 디코딩의 값"이 아닙니다. 손해에서 추측 디코딩 탓과 KV가 좁아진 탓을 분리할 수 없기 때문입니다.

	측정값 자체는 이렇습니다. 수용률은 **40.1%**였습니다.

	<table fit-page-width="true" header-row="true">
	<tr>
	<td>워크로드</td>
	<td>c</td>
	<td>vanilla</td>
	<td>ngram</td>
	<td>draft</td>
	<td>draft 차이</td>
	<td>draft goodput</td>
	</tr>
	<tr>
	<td>`decode`</td>
	<td>1</td>
	<td>116.1</td>
	<td>102.0</td>
	<td>58.6</td>
	<td>**−49.5%**</td>
	<td>100%</td>
	</tr>
	<tr>
	<td>`decode`</td>
	<td>64</td>
	<td>4,745.5</td>
	<td>3,388.3</td>
	<td>717.7</td>
	<td>**−84.9%**</td>
	<td>**0.0%**</td>
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

	**그런데 이 구성이 본문의 축을 오히려 강화합니다.** 같은 "추측 디코딩"인데 두 방식이 예산에 정반대로 작용하기 때문입니다.

	- **ngram은 예산을 안 뺏습니다.** 모델을 추가하지 않으니 KV가 그대로고 남는 자리만 씁니다. 그래서 `prefill` 저동시성에서 3배가 납니다.
	- **draft 모델은 예산 자체를 42% 줄이고 시작합니다.** 그래서 어느 워크로드·어느 동시성에서도 이득이 없습니다. ngram이 3배를 내던 `prefill` c=1에서조차 −4.1%입니다.

	조건이 "예산이 남는가"라면, **예산을 먹고 들어가는 방식은 출발부터 집니다.**

	운영 관점에서 가장 무거운 숫자는 처리량이 아니라 **`decode` c=64의 goodput 0.0%**입니다. 64요청 전부가 e2e SLO(30초)를 놓쳤습니다(p95 45.6초). vanilla와 ngram은 같은 지점에서 100%였습니다. **12GB에서 1.5B에 0.5B draft를 얹는 구성은 고동시성에서 서비스가 안 되는 수준입니다.**

	> 더 큰 GPU라면 결론이 달라질 수 있습니다. KV 예산에 여유가 있으면 draft 모델의 −42%가 그만큼 아프지 않고 수용률 40%가 ngram보다 나은 워크로드도 있을 것입니다. **이 부록이 말하는 것은 draft 방식이 나쁘다는 게 아니라, 예산이 빠듯한 GPU에서는 예산을 먹는 방식이 먼저 탈락한다는 것입니다.**

---

## 참고 자료

- [vLLM — Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode.html)
- [vLLM — Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html)
- [vLLM — Optimization and Tuning](https://docs.vllm.ai/en/latest/configuration/optimization.html)
- vLLM V1 스케줄러 소스: `vllm/v1/core/sched/scheduler.py` (v0.23.0)
- 실측 원본: `labs/wsl2-vllm-baseline/results/` (`e1-*`, `e2-*`, `e3-*`, `e-analysis.md`, `e4-scheduler-notes.md`)
