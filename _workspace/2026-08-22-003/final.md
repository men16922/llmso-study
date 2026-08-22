**GPU 한 장짜리 LLM 서빙에서 병목을 분리해 확인한 실험 기록**
<callout icon="🎯" color="blue_bg">
	**핵심 요약**
	지난 실험에서는 vLLM의 `max_num_seqs`를 1에서 64로 늘렸을 때 처리량이 약 **23배** 증가했습니다. 이번에는 Ray Serve 위에서 같은 값을 16에서 64로 늘렸지만 처리량이 **822 → 852 tok/s(+3.7%)**에 머물렀습니다.
	원인을 확인하려고 같은 `ray-llm` 이미지에서 Ray Serve 유무만 바꿔 다시 측정했습니다. 동시성 64에서 직접 실행한 vLLM은 **2,837 tok/s**, Ray Serve 구성은 **852 tok/s**였습니다. 이 조건에서는 vLLM 엔진보다 Ray Serve가 포함된 서빙 계층 구간에서 먼저 병목이 나타났습니다.
	이 글에서 goodput은 **TTFT ≤ 0.5초와 E2E ≤ 10초를 모두 만족한 요청의 비율**입니다. 같은 부하에서 직접 vLLM은 **100%**, Ray Serve 구성은 **19%**였습니다.
</callout>
---
<table_of_contents color="gray"/>
## 1. 슬롯을 늘렸는데 왜 처리량은 그대로였을까
앞 편 [Continuous Batching이 처리량을 높이는 방식](https://app.notion.com/p/3bd4c2420ac4801899f7c33bb57f64ee)에서는 GPU 한 장에서 vLLM의 `max_num_seqs`만 바꿔가며 부하를 걸었습니다. 슬롯을 1에서 64로 늘리자 처리량은 113 → 2,627 tok/s로 약 **23배** 증가했습니다.
이번에는 vLLM 앞에 Ray Serve를 두고 같은 값을 16에서 64로 늘렸습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>slots=16</td>
<td>slots=64</td>
<td>변화</td>
</tr>
<tr>
<td>16</td>
<td>809</td>
<td>746</td>
<td>−7.8%</td>
</tr>
<tr>
<td>32</td>
<td>827</td>
<td>789</td>
<td>−4.6%</td>
</tr>
<tr>
<td>64</td>
<td>822</td>
<td>852</td>
<td>**+3.7%**</td>
</tr>
</table>
슬롯을 4배로 늘렸지만 처리량은 거의 달라지지 않았습니다. 동시성 16과 32에서는 오히려 감소했습니다. `max_num_seqs`가 정상적으로 반영됐는데도 결과가 달라졌다면, 엔진 밖에서 요청을 제한하는 구간이 있는지 확인해야 합니다.
> **이 글의 질문:** Ray Serve 구성에서는 왜 슬롯을 늘려도 처리량이 증가하지 않았을까?
---
## 2. 무엇을 비교했나
처리량이 멈춘 원인으로 Ray Serve 계층과 vLLM 엔진을 차례로 확인했습니다. Ray Serve가 요청을 충분히 공급하지 못했을 수도 있고, vLLM의 슬롯이나 KV Cache가 이미 한계에 도달했을 수도 있습니다.
Triton Dynamic Batching은 별도로 다뤘습니다. Triton은 같은 요청 경로에 포함된 계층이 아니라 다른 시스템에서 수행한 실험이기 때문입니다. Ray Serve의 병목을 판단하는 근거로는 쓰지 않고, 배칭 방식과 요청 도착률이 어떤 관계인지 확인하는 데만 사용했습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구분</td>
<td>확인할 질문</td>
<td>확인 방법</td>
<td>교재 연결</td>
</tr>
<tr>
<td>**가설 1. Ray Serve 계층**</td>
<td>서빙 계층이 vLLM보다 먼저 포화하는가</td>
<td>같은 엔진·같은 설정에서 Ray Serve 유무만 바꿔 측정</td>
<td>CH4 RayService 도전과제</td>
</tr>
<tr>
<td>**가설 2. vLLM 엔진 메모리**</td>
<td>슬롯이나 KV Cache가 동시 요청 수를 제한하는가</td>
<td>`max_model_len`·`max_num_seqs`·`gpu_memory_utilization` 스윕</td>
<td>CH5 「Estimating KV Cache Size」와 도전과제 2</td>
</tr>
<tr>
<td>**보조 실험. Dynamic Batching**</td>
<td>최대 배치 크기와 대기 시간의 효과가 부하에 따라 달라지는가</td>
<td>Triton에서 대기 시간과 동시성을 바꿔 측정</td>
<td>CH6 「Dynamic Batching in Online Inference」</td>
</tr>
</table>
먼저 Ray Serve 유무에 따른 차이를 비교하고, 이어서 KV Cache 설정을 확인합니다. Triton 결과는 마지막에 별도 실험으로 살펴봅니다.
<details>
<summary>실험 환경과 부하 조건</summary>
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
<td>드라이버</td>
<td>581.57</td>
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
<td>모델</td>
<td>`Qwen/Qwen2.5-1.5B-Instruct`</td>
</tr>
	</table>
	GPU가 한 장이라 세 실험은 서로 배타적입니다. 앞의 것을 완전히 내리고 `nvidia-smi`로 VRAM 반환을 눈으로 확인한 뒤 다음을 띄웠습니다.
	부하는 지난 편과 **같은 명령, 같은 시나리오**입니다. 짧은 프롬프트, 동시성 1·2·4·8·16·32·64, 각 100요청, 요청마다 프롬프트 앞에 고유 접두사를 붙여 캐시 효과를 배제했습니다.
	```bash
python3 benchmark.py --scenarios short --concurrency 1,2,4,8,16,32,64 \
  --requests-per-level 100 --warmup 1 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 --output results/c3-rayserve-short.json
	```
</details>
---
## 3. Ray Serve를 걷어내자 처리량이 3.3배 늘었다
### 3-1. 같은 엔진끼리 비교해야 했다
계층의 값을 재려면 **엔진이 같아야** 합니다. 그런데 Ray Serve LLM을 띄우는 `rayproject/ray-llm:2.44.1-py311-cu124` 이미지가 품은 vLLM은 **0.7.2**였습니다. 지난 편 기준선은 **0.23.0**입니다. 마이너 버전이 16개 벌어집니다.
이대로 두 값을 빼면 나오는 건 계층의 값이 아니라 계층과 엔진 버전 차이의 합계입니다.
그래서 구성을 하나 더 만들었습니다. **같은 ray-llm 이미지로, Ray 없이 vLLM만** 띄운 것입니다. 이미지가 같으니 엔진도 같고, 남는 변수가 계층 하나로 좁혀집니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>#</td>
<td>구성</td>
<td>이미지</td>
<td>vLLM</td>
<td>계층</td>
<td>이 구성이 하는 일</td>
</tr>
<tr>
<td>**A**</td>
<td>직접 vLLM (지난 편)</td>
<td>`vllm-openai:v0.23.0`</td>
<td>0.23.0</td>
<td>없음</td>
<td>기존 기준선</td>
</tr>
<tr>
<td>**B**</td>
<td>직접 vLLM (신규)</td>
<td>`ray-llm:2.44.1`</td>
<td>0.7.2</td>
<td>없음</td>
<td>**A와의 차 = 엔진 버전의 값**</td>
</tr>
<tr>
<td>**C**</td>
<td>Ray Serve</td>
<td>`ray-llm:2.44.1`</td>
<td>0.7.2</td>
<td>Ray Serve</td>
<td>**B와의 차 = 계층의 순수 값**</td>
</tr>
</table>
세 구성 모두 `max_model_len=4096` / `gpu_memory_utilization=0.85`로 맞췄습니다.
### 3-2. slots=16에서는 처리량이 32.6% 낮았다
먼저 지난 편과 같은 슬롯 16에서 쟀습니다.
**엔진 버전의 값 (A → B) — 계층은 양쪽 다 없음**
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>A (0.23.0)</td>
<td>B (0.7.2)</td>
<td>차이 %</td>
</tr>
<tr>
<td>1</td>
<td>108.8</td>
<td>104.7</td>
<td>−3.8%</td>
</tr>
<tr>
<td>8</td>
<td>780.2</td>
<td>692.6</td>
<td>−11.2%</td>
</tr>
<tr>
<td>16</td>
<td>1,333.1</td>
<td>1,200.9</td>
<td>**−9.9%**</td>
</tr>
<tr>
<td>32</td>
<td>1,391.0</td>
<td>1,201.2</td>
<td>−13.6%</td>
</tr>
<tr>
<td>64</td>
<td>1,340.0</td>
<td>1,186.1</td>
<td>−11.5%</td>
</tr>
</table>
**계층의 값 (B → C) — 같은 엔진, 계층만 다름**
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>B 직접</td>
<td>C Ray Serve</td>
<td>차이 %</td>
</tr>
<tr>
<td>1</td>
<td>104.7</td>
<td>93.3</td>
<td>−10.9%</td>
</tr>
<tr>
<td>4</td>
<td>385.1</td>
<td>339.5</td>
<td>−11.9%</td>
</tr>
<tr>
<td>8</td>
<td>692.6</td>
<td>594.2</td>
<td>−14.2%</td>
</tr>
<tr>
<td>16</td>
<td>1,200.9</td>
<td>809.1</td>
<td>**−32.6%**</td>
</tr>
<tr>
<td>32</td>
<td>1,201.2</td>
<td>827.3</td>
<td>−31.1%</td>
</tr>
<tr>
<td>64</td>
<td>1,186.1</td>
<td>821.6</td>
<td>−30.7%</td>
</tr>
</table>
A와 C를 그냥 빼면 −39.3%가 나옵니다. 갈라놓으면 계층 몫은 **32.6%**이고 나머지 약 10%는 엔진이 16개 버전 낡은 값이었습니다. 통제 변수를 하나 안 잡았으면 계층에 7%p를 잘못 씌울 뻔했습니다.
![서빙 계층이 처리량에서 가져가는 몫 — A(직접 0.23)와 B(직접 0.7)는 거의 붙어 가지만 C(Ray Serve)만 동시성 16부터 크게 아래로 갈라진다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/6962563b-7a15-4133-93c2-00351c799185/fig-c3-layer-throughput.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=f66ce28afcd17394b4974beccaa5059ba7058177ba18b1f0451ea89e9ca753e0&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
A와 B는 거의 붙어 갑니다. 엔진 버전 차이는 눈에 잘 안 띌 정도입니다. 갈라지는 건 C 하나뿐이고, 갈라지기 시작하는 지점이 **동시성 16**입니다.
### 3-3. slots=64에서는 차이가 70.0%까지 벌어졌다
여기까지로는 아직 부족합니다. 슬롯이 16이면 **엔진 자체가 1,200 tok/s에서 막힙니다.** 계층이 그보다 낮은 809에서 막는다는 것만 알 뿐, 엔진에 여유를 줬을 때 계층이 어디까지 따라오는지는 모릅니다.
그래서 **구성 B를 슬롯 64로 다시 띄웠습니다.** 구성 C의 슬롯 64와 같은 조건입니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>B 직접 (slots=64)</td>
<td>C Ray Serve (slots=64)</td>
<td>차이 %</td>
</tr>
<tr>
<td>1</td>
<td>104.6</td>
<td>97.6</td>
<td>−6.7%</td>
</tr>
<tr>
<td>4</td>
<td>384.8</td>
<td>336.2</td>
<td>−12.6%</td>
</tr>
<tr>
<td>8</td>
<td>700.9</td>
<td>567.3</td>
<td>−19.1%</td>
</tr>
<tr>
<td>16</td>
<td>1,201.5</td>
<td>745.8</td>
<td>−37.9%</td>
</tr>
<tr>
<td>32</td>
<td>1,853.1</td>
<td>788.8</td>
<td>−57.4%</td>
</tr>
<tr>
<td>64</td>
<td>**2,836.8**</td>
<td>**852.3**</td>
<td>**−70.0%**</td>
</tr>
</table>
![슬롯을 64로 열었을 때 계층이 있고 없고 — 직접 vLLM은 동시성 64에서 2,837 tok/s까지 오르고 Ray Serve는 852에서 평평해진다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/66b57317-d734-440d-bce7-fbe2177f9227/fig-c3-seqs64-throughput.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=c18ac67fff13f6c7a230ced498647a05298965a2d582e4205a776aafefad8f1c&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**여기서 갈립니다.** 같은 엔진, 같은 설정인데 동시성 64에서 **3.3배** 차이가 납니다.
같은 노브를 양쪽에서 돌려보면 더 분명합니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>슬롯 16 → 64, 동시성 64에서</td>
<td>처리량 변화</td>
</tr>
<tr>
<td>직접 vLLM</td>
<td>1,186 → 2,837 (**+139%**)</td>
</tr>
<tr>
<td>Ray Serve</td>
<td>822 → 852 (**+3.7%**)</td>
</tr>
</table>
**노브는 고장 나지 않았습니다.** 계층 없이 돌리면 그대로 듣습니다. 계층 아래서만 안 듣습니다.
지연은 더 벌어집니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>B 직접 TTFT p95</td>
<td>C Ray Serve TTFT p95</td>
<td>차이</td>
</tr>
<tr>
<td>1</td>
<td>0.027 s</td>
<td>0.068 s</td>
<td>+0.040 s</td>
</tr>
<tr>
<td>16</td>
<td>0.112 s</td>
<td>0.285 s</td>
<td>+0.173 s</td>
</tr>
<tr>
<td>32</td>
<td>0.190 s</td>
<td>1.698 s</td>
<td>+1.507 s</td>
</tr>
<tr>
<td>64</td>
<td>**0.330 s**</td>
<td>**4.006 s**</td>
<td>**+3.676 s**</td>
</tr>
</table>
동시성 64에서 직접은 TTFT p95가 **0.330초**로 SLO(0.5초) 안에 들어옵니다. goodput **100%**입니다. 같은 부하에서 Ray Serve는 4.006초, goodput **19%**입니다.
### 3-4. 서빙 계층의 영향은 부하에 따라 커졌다
**계층의 값은 고정 통행료가 아닙니다.** 엔진이 얼마나 달릴 수 있느냐에 따라 달라집니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>조건</td>
<td>엔진이 낼 수 있는 값</td>
<td>계층이 먹는 몫</td>
</tr>
<tr>
<td>슬롯 16 (엔진이 1,200에서 막힘)</td>
<td>1,186</td>
<td>30.7%</td>
</tr>
<tr>
<td>슬롯 64 (엔진이 2,837까지 감)</td>
<td>2,836.8</td>
<td>**70.0%**</td>
</tr>
</table>
엔진이 한가할 땐 계층이 통행료를 받고, 엔진에 여유를 줄수록 계층 자신이 천장이 됩니다. **엔진을 튜닝할수록 계층의 손해가 커진다**는 뜻이라, 엔진 최적화와 계층 선택은 따로 볼 문제가 아닙니다.
그리고 방법론 하나 — **비교를 성립시키는 데 15분이 더 들었습니다.** 구성 B를 만들지 않았다면 계층에 39.3%를 씌웠을 것이고, 슬롯 64로 다시 재지 않았다면 32.6%에서 멈췄을 겁니다. 실제 값은 70%였습니다.
---
## 4. KV Cache 설정은 동시성 상한만 바꿨다
계층이 범인이라는 게 밝혀졌지만, 두 번째 후보도 확인해야 소거가 끝납니다. **메모리가 동시 요청 수를 막고 있었던 건 아닌가.**
### 4-1. 세 설정값을 바꾼 이유
교재 CH5는 KV Cache 크기가 동시 요청 수의 상한을 정한다고 설명합니다. 공식 도전과제 2에서는 `max batch size`·`max model length`·`max number of tokens`를 바꿔 성능을 비교합니다. RayService의 `serveConfigV2 → engine_kwargs`에 그 셋이 그대로 노출돼 있어, 계층은 고정한 채 메모리만 흔들 수 있습니다.
RayService를 쓴 실무적 이유도 있습니다. `serveConfigV2`만 바뀌면 **파드를 갈지 않고 Serve 앱만 제자리에서 교체**합니다. 지난 편에서 `kubectl set env`로 재배포하다 13일 전 구버전이 떠 있어 변경이 조용히 무시된 사고가 있었는데, 여기서는 구조적으로 안 생깁니다. 실제로 스윕 네 번 동안 **파드 재시작 0회**였고 엔드포인트는 계속 살아 있었습니다.
### 4-2. 추정 동시성은 4.5배 달라졌다
<table fit-page-width="true" header-row="true">
<tr>
<td>#</td>
<td>`max_model_len`</td>
<td>`max_num_seqs`</td>
<td>`util`</td>
<td>활성화 피크</td>
<td>**KV 예산**</td>
<td>**`Maximum concurrency`**</td>
</tr>
<tr>
<td>1</td>
<td>4096</td>
<td>16</td>
<td>0.85</td>
<td>0.26 GiB</td>
<td>7.00 GiB</td>
<td>**64.02x**</td>
</tr>
<tr>
<td>2</td>
<td>4096</td>
<td>64</td>
<td>0.85</td>
<td>0.48 GiB</td>
<td>6.79 GiB</td>
<td>62.04x</td>
</tr>
<tr>
<td>3</td>
<td>16384</td>
<td>64</td>
<td>0.85</td>
<td>1.02 GiB</td>
<td>6.25 GiB</td>
<td>**14.28x**</td>
</tr>
<tr>
<td>4</td>
<td>4096</td>
<td>64</td>
<td>0.60</td>
<td>0.48 GiB</td>
<td>3.79 GiB</td>
<td>34.62x</td>
</tr>
</table>
노브가 상한을 **4.5배**(14.28 ↔ 64.02) 흔듭니다. 예상대로입니다.
### 4-3. 처리량은 ±17% 범위에 머물렀다
<table fit-page-width="true" header-row="true">
<tr>
<td>#</td>
<td>설정</td>
<td>`Maximum concurrency`</td>
<td>tok/s (c=16)</td>
<td>tok/s (c=32)</td>
<td>tok/s (c=64)</td>
</tr>
<tr>
<td>1</td>
<td>len4096 / seqs16 / 0.85</td>
<td>64.02x</td>
<td>809</td>
<td>827</td>
<td>822</td>
</tr>
<tr>
<td>2</td>
<td>len4096 / seqs64 / 0.85</td>
<td>62.04x</td>
<td>746</td>
<td>789</td>
<td>852</td>
</tr>
<tr>
<td>3</td>
<td>len16384 / seqs64 / 0.85</td>
<td>14.28x</td>
<td>878</td>
<td>948</td>
<td>**964**</td>
</tr>
<tr>
<td>4</td>
<td>len4096 / seqs64 / 0.60</td>
<td>34.62x</td>
<td>814</td>
<td>927</td>
<td>961</td>
</tr>
</table>
상한이 4.5배 갈리는데 처리량은 **822 \~ 964, ±17% 안**입니다. 게다가 상한이 가장 낮은 3번(14.28x)이 처리량은 가장 높습니다.
이유는 `Maximum concurrency`의 정의에 있습니다. 이 값은 모든 요청이 `max_model_len`을 꽉 채워 쓴다고 가정한 동시성 추정치입니다. 이 실험의 프롬프트는 짧아서 요청 하나가 실제로 쓰는 KV는 그 가정의 몇십분의 일입니다. 그러니 상한에 닿을 일이 없고, 상한을 낮춰도 아프지 않습니다.
**두 번째 후보는 소거됩니다.** 이 워크로드에서 메모리는 병목이 아니었습니다. 그리고 3장에서 슬롯 16 → 64가 계층 아래서 안 들었던 것도 메모리 탓이 아니었습니다 — 같은 노브가 계층 없이는 +139%를 냈으니까요.
### 4-4. KV Cache 예산은 기동할 때 측정된다
지난 편에 이런 걸 남겼습니다. *"같은 **`slots=64`**인데 **`Maximum concurrency`**가 59.50x / 28.77x로 갈렸다. 원인 미확인."*
위 표의 1번 → 2번을 보면 메커니즘이 보입니다. 가중치(2.89 GiB)도 `util`(0.85)도 그대로인데 KV 예산이 **7.00 → 6.79 GiB**로 줄었습니다. 줄어든 만큼이 활성화 피크로 갔습니다(0.26 → 0.48 GiB).
vLLM은 KV 예산을 이렇게 잡습니다.
```javascript
KV 예산 = 총 VRAM × util − 가중치 − 활성화 피크
```
그리고 **활성화 피크는 기동할 때 프로파일링을 한 번 돌려서 재는 값**입니다. 상수가 아닙니다. 슬롯을 늘리면 배치가 커지고, 배치가 커지면 중간 텐서가 커집니다. 그만큼 KV에 남는 몫이 깎입니다. 3번에서 컨텍스트를 4배로 늘렸을 때 활성화가 1.02 GiB까지 뛴 것도 같은 이유입니다.
다만 정직하게 적어두면, 이번에 관측한 변동은 **3% 수준**(64.02 → 62.04)이고 지난 편의 59.50 ↔ 28.77은 2배입니다. 이 메커니즘만으로는 설명이 안 됩니다. 직전 파드가 VRAM을 덜 돌려준 상태에서 다음이 떴다는 가설이 여전히 유력하고 **미확인으로 남습니다.**
한 가지 더 — 같은 설정(`len4096 / seqs64 / 0.85`)을 **계층 없이** 띄웠을 때도 `Maximum concurrency`는 **62.04x**로 똑같았습니다. 계층은 처리량을 70% 먹었지만 **KV 예산은 건드리지 않습니다.** 두 층이 서로 다른 자원을 쓴다는 확인입니다.
### 4-5. GQA에서는 KV 헤드 수로 계산해야 한다
위 표의 KV 예산이 맞는지 손으로 검산하려다 발견한 것입니다.
CH5는 KV cache 크기를 이렇게 계산합니다.
```javascript
토큰당 KV = 2(K,V) × 층 수 × 어텐션 헤드 수 × head_dim × 정밀도(바이트)
```
Llama-2-7b 예시로 `2 × 32 × 32 × 128 × 2 = 0.5 MB/token`.
**이 공식을 우리 모델에 그대로 넣으면 안 맞습니다.** 교재가 각주로 예고해 둔 그대로입니다. *"기본적인 멀티헤드 어텐션(MHA) 형태를 사용하는 Llama-2-7b를 사용하겠습니다"*, *"이후 장에서 MQA, GQA, MLA 등 KV 캐시를 축소하고 압축하는 다른 아이디어들을 소개할 예정"*. 그 "이후 장"이 이번 주 CH6이고, **Qwen2.5-1.5B가 바로 GQA**입니다.
`config.json`을 직접 열어 봤습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>항목</td>
<td>값</td>
</tr>
<tr>
<td>`num_hidden_layers`</td>
<td>28</td>
</tr>
<tr>
<td>`num_attention_heads`</td>
<td>**12**</td>
</tr>
<tr>
<td>`num_key_value_heads`</td>
<td>**2**</td>
</tr>
<tr>
<td>head_dim</td>
<td>128</td>
</tr>
<tr>
<td>dtype</td>
<td>bfloat16 (2바이트)</td>
</tr>
</table>
쿼리 헤드 12개가 KV 헤드 2개를 **6:1로 공유**합니다. KV cache는 K와 V만 저장하므로 세어야 하는 건 KV 헤드 수입니다.
<table fit-page-width="true" header-row="true">
<tr>
<td></td>
<td>공식</td>
<td>토큰당 KV</td>
</tr>
<tr>
<td>교재 그대로 (MHA 가정)</td>
<td>2 × 28 × **12** × 128 × 2</td>
<td>172,032 B = **168.0 KiB**</td>
</tr>
<tr>
<td>GQA 반영</td>
<td>2 × 28 × **2** × 128 × 2</td>
<td>28,672 B = **28.0 KiB**</td>
</tr>
</table>
**6배**입니다. 어느 쪽이 맞는지는 엔진이 기동 로그에 직접 찍어 줍니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>설정</td>
<td>KV 예산</td>
<td>요청당 KV</td>
<td>**GQA 손계산**</td>
<td>**로그 실측**</td>
<td>MHA 공식이었다면</td>
</tr>
<tr>
<td>len4096 / seqs16 / 0.85</td>
<td>7.00 GiB</td>
<td>112 MiB</td>
<td>64.0x</td>
<td>**64.02x**</td>
<td>10.7x</td>
</tr>
<tr>
<td>len4096 / seqs64 / 0.85</td>
<td>6.79 GiB</td>
<td>112 MiB</td>
<td>62.1x</td>
<td>**62.04x**</td>
<td>10.3x</td>
</tr>
<tr>
<td>len16384 / seqs64 / 0.85</td>
<td>6.25 GiB</td>
<td>448 MiB</td>
<td>14.3x</td>
<td>**14.28x**</td>
<td>2.4x</td>
</tr>
<tr>
<td>len4096 / seqs64 / 0.60</td>
<td>3.79 GiB</td>
<td>112 MiB</td>
<td>34.7x</td>
<td>**34.62x**</td>
<td>5.8x</td>
</tr>
</table>
**네 줄 모두 소수점 둘째 자리까지 맞습니다.** 교재 공식대로 계산했다면 "동시 요청 10개가 상한"이라고 결론냈을 자리에서 실제 상한은 64입니다. 자기 모델의 `num_key_value_heads`를 확인하지 않고 CH5 공식을 그대로 쓰면 GQA 모델에서 용량을 몇 배로 과대평가합니다.
---
## 5. Triton에서는 요청이 충분할 때만 배칭이 이득이었다
### 5-1. vLLM과 직접 비교하지 않았다
세 번째 후보는 "요청을 묶는 방식이 잘못됐나"입니다. 그런데 **vLLM에는 이 노브가 없습니다.** vLLM은 continuous batching만 하고, dynamic batching의 두 파라미터(최대 배치 크기·최대 대기 시간)를 노출하지 않습니다. 켜고 끄며 비교할 대상이 애초에 없습니다.
교재 CH6에는 「Dynamic Batching in Online Inference」 절이 통째로 있는데, 그걸 vLLM으로는 실측할 수 없다는 뜻입니다. 그래서 그 두 노브를 실제로 가진 **Triton**으로 옮겨, 다른 모델(`mobilenet_v2`)에서 **원리만** 확인했습니다.
> ⚠️ **이 실험은 앞의 두 층과 같은 저울이 아닙니다.** 모델도 서버도 지표도 다릅니다(mobilenet · Triton · inf/s). "이 배포의 천장이 셋 중 누구냐"를 겨루는 후보에서는 **빠집니다.** 대신 *"그래서 vLLM은 왜 이 방식을 안 쓰는가"* 에 답합니다.
### 5-2. 모델이 배치 축을 지원해야 했다
교재 실습의 `densenet_onnx`로는 이 실험을 **시작할 수조차 없습니다.** `config.pbtxt`가 이렇게 되어 있습니다.
```protobuf
max_batch_size : 0                       # 배칭 자체가 꺼짐
dims: [ 3, 224, 224 ]
reshape { shape: [ 1, 3, 224, 224 ] }    # 배치 차원 1을 억지로 끼워 넣는 중
```
그 ONNX는 **배치 축이 1로 고정**이라 `max_batch_size`를 켜면 모델이 로드를 거부합니다. `reshape`가 그 우회 흔적입니다. 그래서 배치 축을 연 모델을 새로 만들었습니다. 핵심은 export 한 줄입니다.
```python
torch.onnx.export(
    model, dummy, "model.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},   # ★ 이 한 줄
    opset_version=17,
)
```
> **서빙 계층만 봐서는 안 보이는 제약입니다.** 배칭을 켜려면 모델이 먼저 배치를 받아들여야 합니다. "설정에서 켜면 되는 기능"이 아니라 **모델 export 시점에 결정되는 성질**입니다.
### 5-3. 동시성 1에서는 손해였고 32에서는 이득이었다
`max_batch_size: 8` 고정, `max_queue_delay_microseconds`만 바꿔가며 각 조합에 동시성 1·8·32로 300요청씩.
<table fit-page-width="true" header-row="true">
<tr>
<td>대기 시간</td>
<td>**평균 배치 크기**</td>
<td>큐 대기 (ms/req)</td>
<td>연산 (ms/req)</td>
</tr>
<tr>
<td>**off (대조군)**</td>
<td>**1.00**</td>
<td>16.5</td>
<td>1.83</td>
</tr>
<tr>
<td>0</td>
<td>2.16</td>
<td>19.5</td>
<td>14.1</td>
</tr>
<tr>
<td>1 ms</td>
<td>2.03</td>
<td>34.1</td>
<td>15.6</td>
</tr>
<tr>
<td>5 ms</td>
<td>2.37</td>
<td>14.2</td>
<td>8.44</td>
</tr>
<tr>
<td>20 ms</td>
<td>2.39</td>
<td>10.1</td>
<td>6.59</td>
</tr>
</table>
평균 배치 크기는 `nv_inference_request_success / nv_inference_exec_count`를 구간 차분해서 구했습니다. 대조군이 **정확히 1.00**(960요청 / 960실행)으로 나와 비교가 성립합니다. 배칭을 켜면 배치가 2.0\~2.4로 올라가지만 `max_batch_size` 8은 못 채웁니다 — 대기 창이 닫히기 전에 8개가 도착하지 않았다는 뜻입니다.
**처리량 (inf/s)**
<table fit-page-width="true" header-row="true">
<tr>
<td>대기 시간</td>
<td>동시성 1</td>
<td>동시성 8</td>
<td>동시성 32</td>
</tr>
<tr>
<td>off</td>
<td>**352.1**</td>
<td>583.7</td>
<td>597.2</td>
</tr>
<tr>
<td>0</td>
<td>334.5</td>
<td>132.4</td>
<td>623.3</td>
</tr>
<tr>
<td>1 ms</td>
<td>255.9</td>
<td>99.8</td>
<td>402.6</td>
</tr>
<tr>
<td>5 ms</td>
<td>105.3</td>
<td>542.1</td>
<td>569.3</td>
</tr>
<tr>
<td>20 ms</td>
<td>**37.5**</td>
<td>558.3</td>
<td>**1,371.2**</td>
</tr>
</table>
`20 ms` 결과를 보면 차이가 분명합니다. 동시성 1에서 37.5 inf/s로 대조군의 9분의 1이고, 동시성 32에서 1,371 inf/s로 대조군의 2.3배입니다. 같은 설정, 같은 서버, 같은 모델입니다.
지연을 보면 이유가 분명합니다. 동시성 1일 때 p50:
<table fit-page-width="true" header-row="true">
<tr>
<td>대기 시간</td>
<td>p50 지연 (c=1)</td>
</tr>
<tr>
<td>off</td>
<td>2.40 ms</td>
</tr>
<tr>
<td>5 ms</td>
<td>9.32 ms</td>
</tr>
<tr>
<td>20 ms</td>
<td>**26.81 ms**</td>
</tr>
</table>
**대기 창을 그대로 다 기다리고 있습니다.** 동시성 1이면 같이 묶일 요청이 애초에 없으니 설정한 시간만큼 앉아 있다가 혼자 계산됩니다. 20 ms 설정에 p50 26.8 ms — 대기 20 ms + 연산 약 7 ms입니다.
(동시성 8의 `delay=0`·`1ms` 두 칸이 c=1·c=32보다 낮게 나온 건 곡선 모양과 어긋납니다. 재측정하지 못했으므로 **측정 잡음으로 보고 결론에 쓰지 않았습니다.**)
### 5-4. LLM이 Continuous Batching을 쓰는 이유
dynamic batching은 두 가지를 전제합니다.
1. 요청들이 **비슷한 시각에** 도착한다 → 5-3이 보여준 도착률 의존성
2. 요청들이 **비슷한 시간이 걸린다** → 배치를 통째로 묶었다 통째로 내보내니까
mobilenet은 둘째 전제를 완벽히 만족합니다. 이미지 크기가 같으면 연산량이 같습니다.
**LLM은 둘째 전제가 깨집니다.** 같은 배치에 20토큰짜리와 500토큰짜리가 섞이면 20토큰 요청은 끝나고도 500토큰이 끝날 때까지 배치 안에 붙잡혀 있습니다. 배치 전체가 가장 긴 요청에 인질로 잡힙니다.
continuous batching은 이 전제를 **버려서** 문제를 풉니다. 배치를 통째로 다루지 않고 iteration마다 끝난 것을 빼고 기다리던 것을 넣습니다. 지난 편의 23배가 그 값어치였습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>배칭 방식</td>
<td>평균 배치</td>
<td>이 시리즈에서</td>
</tr>
<tr>
<td>없음</td>
<td>1.00</td>
<td>(미수행 — 다음 편)</td>
</tr>
<tr>
<td>static</td>
<td>—</td>
<td>(미수행 — 다음 편)</td>
</tr>
<tr>
<td>**dynamic**</td>
<td>**1.00 → 2.4**</td>
<td>**이번 편 5장** (Triton, mobilenet)</td>
</tr>
<tr>
<td>**continuous**</td>
<td>—</td>
<td>지난 편 (vLLM, 23배)</td>
</tr>
</table>
---
## 6. 이번에는 어디에서 막혔나
처음 질문은 슬롯을 늘려도 처리량이 증가하지 않은 이유였습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>검토 대상</td>
<td>관측 결과</td>
<td>해석</td>
</tr>
<tr>
<td>**Ray Serve 계층**</td>
<td>같은 엔진·slots=64에서 직접 vLLM은 2,837 tok/s, Ray Serve 구성은 852 tok/s</td>
<td>이번 구성에서 먼저 포화한 구간</td>
</tr>
<tr>
<td>**vLLM 슬롯·KV Cache**</td>
<td>추정 동시성이 4.5배 달라지는 동안 처리량은 ±17% 범위</td>
<td>짧은 프롬프트를 사용한 이번 실험에서는 주 병목이 아님</td>
</tr>
<tr>
<td>**Dynamic Batching**</td>
<td>별도 Triton 실험에서 동시성에 따라 효과가 달라짐</td>
<td>원리 확인용 보조 결과이며 Ray Serve 병목 판정에서는 제외</td>
</tr>
</table>
이번 단일 레플리카 Ray Serve 구성에서는 vLLM 엔진보다 서빙 계층 구간에서 먼저 처리량이 멈췄습니다. slots=64 조건에서 Ray Serve 구성의 처리량은 직접 vLLM보다 **70.0% 낮았습니다.** 이 수치는 Ray Serve 전체의 일반적인 성능이 아니라, 이 글에 기록한 모델·GPU·배포 설정과 부하 조건에서 측정한 결과입니다.
---
## 7. 운영에서는 무엇을 확인해야 하나
### 처리량보다 SLO를 만족한 요청 수를 본다
이 GPU 한 장(12 GB)에서 Qwen2.5-1.5B를 4096 컨텍스트로 서빙할 때, **goodput 100%를 유지하는 동시 요청 수**는 이렇습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>c=16</td>
<td>c=32</td>
<td>c=64</td>
</tr>
<tr>
<td>직접 vLLM, slots=16</td>
<td>100%</td>
<td>16%</td>
<td>16%</td>
</tr>
<tr>
<td>Ray Serve, slots=16</td>
<td>100%</td>
<td>39%</td>
<td>16%</td>
</tr>
<tr>
<td>Ray Serve, slots=64</td>
<td>100%</td>
<td>48%</td>
<td>19%</td>
</tr>
<tr>
<td>**직접 vLLM, slots=64**</td>
<td>**100%**</td>
<td>**100%**</td>
<td>**100%**</td>
</tr>
</table>
같은 GPU인데 **동시 16명에서 64명까지** 갈립니다. `Maximum concurrency`가 보고한 64와 우연히 같은 숫자지만 근거는 다릅니다 — 저건 메모리가 허용하는 입장 제한이고, 이건 지연 목표까지 지키며 실제로 받아낸 수입니다.
용량 산정에 쓸 숫자는 **지연 목표를 걸고 실제로 재본 값**뿐입니다.
### 롤아웃마다 KV Cache 예산을 확인한다
- `Maximum concurrency`가 달라져도 에러는 나지 않습니다. KV 예산이 조용히 줄고 처리량 천장만 낮아집니다. 그래서 롤아웃마다 이 로그 줄을 파일로 남기는 규칙을 만들었습니다.
- **RayService는 지난 편의 재배포 사고를 구조적으로 막습니다.** `serveConfigV2`만 바뀌면 파드를 갈지 않고 Serve 앱만 교체합니다. 다만 반영됐는지는 반드시 확인해야 합니다 — 이번에도 `/v1/models` 응답과 기동 로그를 양쪽으로 봤습니다.
### 컨텍스트 길이는 실제 사용량으로 계산한다
컨텍스트 길이와 동시성은 **같은 KV 예산을 두고 경쟁**합니다. `max_model_len`을 4배로 늘리면 이론 동시성이 4분의 1이 됩니다(64.02x → 14.28x). 다만 워크로드가 실제로 그 길이를 안 쓰면 처리량에는 티가 안 납니다. **"열어둔 길이"가 아니라 "실제로 쓰는 길이"로 용량을 잡아야 합니다.**
### 계층을 추가하면 관측 경로도 달라진다
계층의 대가는 처리량만이 아니었습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td></td>
<td>Ray Serve</td>
<td>같은 엔진, Ray 없음</td>
</tr>
<tr>
<td>`:8000/metrics`</td>
<td>**404**</td>
<td>200</td>
</tr>
<tr>
<td>`vllm:*` 메트릭</td>
<td>**0개**</td>
<td>15개</td>
</tr>
<tr>
<td>대신 나오는 것</td>
<td>`ray_*` 184개 (워커/헤드 `:8080`)</td>
<td>—</td>
</tr>
</table>
**같은 vLLM 0.7.2인데 계층 유무로 갈립니다.** 지난 편의 서버 측 교차검증은 전부 그 메트릭에 기대고 있었습니다. `num_requests_running`이 천장을 치고 초과분이 `num_requests_waiting`으로 쌓이는 궤적을 **이 환경에서는 볼 수 없습니다.**
**계층이 주는 것**도 적어야 공평합니다. 무중단 롤아웃, 오토스케일링, 멀티 애플리케이션 라우팅, 대시보드. GPU 한 장에서는 첫 번째만 체감했지만 레플리카가 여럿인 환경에서는 값이 다를 수 있습니다. 이 실험이 말할 수 있는 건 **"가격이 얼마인가"까지**입니다.
### Triton은 모델 준비 단계부터 다르다
Triton은 **모델을 다시 export해야 했습니다**(5-2). 배칭을 켜려면 모델이 배치 축을 갖고 있어야 하고, 그건 서빙 설정이 아니라 모델 산출 시점의 결정입니다.
---
## 측정 근거 — 필요한 경우 확인
> ⚠️ **아래 화면은 본문 표를 만든 그 실행이 아닙니다.** 측정을 마치고 GPU를 내린 뒤, 같은 매니페스트로 **다시 띄워 찍은 확인용 재현**입니다(2026-08-22). 기동값이 본문과 같게 나오는지, 관측성 관련 주장이 실제 화면에서 성립하는지를 보이려는 것입니다. 숫자를 본문 표와 섞어 읽지 마세요.
### 배포가 실제로 떠 있다
![Ray Dashboard Serve 탭 — Controller HEALTHY, Proxy HEALTHY ×2, Application RUNNING ×1. llm 애플리케이션 아래 LLMDeployment:qwen2_5-1_5b가 replica 1개, LLMRouter가 replica 2개로 HEALTHY 상태](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/2485436b-e361-48ca-ac45-8bab1fc4cded/proof-w3-01-ray-serve-tab.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=eedf6947962ec99c5209e2750ad5fd15a55e47fd635a6d3781ef97f16a3ebd74&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
`LLMDeployment:qwen2_5-1_5b` replica 1개 + `LLMRouter` replica 2개입니다.
### GPU가 워커에만 붙어 있다
![Ray Dashboard Cluster 탭 — 노드 2개 ALIVE. head 노드는 GPU N/A, gpu-group-worker 노드만 GPU 0번이 83.0% · GRAM 10962MiB/12282MiB](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/2b829fa3-2102-4146-afa1-45b7d0759430/proof-w3-02-ray-cluster-gpu.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=3676b32f348ba91f8a035921a3e820720e259beaeefd9a4417ba651b71589b13&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
헤드는 `GPU N/A`, 워커만 83.0% / `10962MiB/12282MiB`입니다. 4-2의 KV 예산 계산이 이 12,282 MiB를 분모로 씁니다.
### 부하가 GPU까지 닿았다
![Prometheus DCGM_FI_DEV_GPU_UTIL 그래프 — 15분 구간에서 부하 시각에만 0%에서 약 83%로 사각 펄스가 올라갔다 내려온다. 시계열 라벨의 exported_pod가 vllm-service의 gpu-group-worker 파드](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/33165347-6518-4492-bc31-78962017b9c7/proof-w3-03-dcgm-gpu-util.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=d74e81ceea6d67f699381de32498ae3bb171482b9e87ace4ea8fc166d30b5be1&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
시계열 라벨의 `exported_pod`가 **Ray 워커 파드**라, 이 GPU 일이 어디서 나왔는지가 메트릭 자체에 박혀 있습니다. 이 그래프를 만든 것은 동시성 64로 900요청을 건 **별도의 지속 부하**입니다(1,036.9 tok/s, goodput 2.1%). 본문 표는 각 지점 100요청이라 조건이 다릅니다.
### Grafana DCGM 대시보드
![Grafana NVIDIA DCGM Exporter Dashboard, 12시간 범위 — GPU Utilization 패널에 84%·91%까지 오르는 스파이크 두 개, Tensor Core Utilization 패널은 No data, GPU Framebuffer Mem Used는 최대 10.7 GB](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/36dbb322-6110-4a4c-903d-0fef78f27fa1/proof-w3-08-grafana-dcgm-util.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=8c0dceec8d5a457929e8fca3ac3bb8cfc5b3c6a859800a71ce5afb1079a8507b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
- **GPU Utilization** — 측정 구간에서 **84% / 91%** 까지 오릅니다.
- **GPU Framebuffer Mem Used** — 최대 **10.7 GB**. `nvidia-smi`의 10,628 MiB, Ray Dashboard의 10,962 MiB와 같은 값입니다.
- Tensor Core Utilization은 `No data`로 표시됩니다. WSL2에서는 `DCGM_FI_PROF_*` 계열이 노출되지 않아 패널을 채울 데이터가 없습니다.
![Grafana DCGM 대시보드 상단 — GPU Temperature가 유휴 46°C 대에서 측정 구간에만 60°C·69°C로 치솟는다. GPU Avg. Temp 게이지는 46.1°C](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/c8656156-29ae-461f-9ef4-fc393514b3e7/proof-w3-09-grafana-dcgm-temp.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=400c66bcbf5559d744ff12aa55536a817a143d71c3d610040a0dff61931d0e1e&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
> ⚠️ 같은 화면의 `GPU Power Usage`는 **최대 593 W**로 읽힙니다. 이 GPU는 70 W 제품이라 그대로 믿을 수 없는 값이고, 원인을 확인하지 않았으므로 **전력 수치는 쓰지 않았습니다.**
### 엔진 설정이 본문과 같다
![브라우저에서 연 /v1/models 응답 — qwen2.5-1.5b 모델 하나, rayllm_metadata의 max_request_context_length가 4096](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/ee7444e6-68bd-4f0e-8b25-b4ffdcfe0f4d/proof-w3-04-v1-models.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=1dfc447c0998e11900de384c0993e591e7f92cddbad5e9d412c8e133b3cc0a0b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 그런데 `/metrics`는 없다
![같은 호스트의 :8000/metrics 응답 — detail Not Found](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/700926c1-1c5a-4eef-b991-5e1959f3280e/proof-w3-05-metrics-404.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=be264e823569ba499cfad81c408d04ed8b7f158c7c19e1c215f1eb60cad748d0&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
바로 위에서 `/v1/models`가 정상 응답한 **같은 포트**입니다. 「복잡도와 관측성」에서 표로 적은 404가 이것입니다.
### 기동 로그가 replica에 없다
![Ray Dashboard Serve 탭의 Deployments 로그 뷰 — LLMDeployment replica의 STDOUT에 4줄만 있고 vLLM 엔진 기동 로그가 없다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/93dfdf91-9f5c-40ce-976a-a9d7648e43a9/proof-w3-06-replica-stdout-empty.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=f28a2a84440eda0a19a164a92cbc3e337144211037f4de01ff66983835bd5b6d&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
![Ray Dashboard Actors 탭 — 액터 9개 ALIVE. _EngineBackgroundProcess(PID 377)와 ServeReplica의 LLMDeployment(PID 187)가 서로 다른 액터로 잡혀 있다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/529fc86f-a0d5-4475-aa2a-89e3af2bab70/proof-w3-07-ray-actors.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466VE4XQOI2%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T135440Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCeYF2Rwzt0kIcDqFws0EvdbW%2BaurDlbLfcWWER6BBhnQIgfmla%2FQq9zPELzf8C40VHUD2DMMEmJV6j92wYlkMZXCQqiAQIvv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDPM%2FZ0%2Bq45YDPP7SVircA22MSohQOf9SjQzCYBNLoFzP90IkoQ%2BMOvx7sYV36PBmma4T9c%2Bp6Ef5MCazIkpag3j%2F6s4ivisdVqld7bZvxtRwHEBYhsUFIPM2RaB365krF8Hm2vm3JOUOwJeShjbjJE4kx213jQ%2BoPuMeGCuU2PZ8BgXz95GgBRd9O3PdH%2FgtgGP17aoDWDBc10K9mD3mXEnKxvl60hdYR6syqSz50f8jYa17H9pfpjIkICn6gHItjxBuW35GS%2BaYJHgHp9pHZGrRdh8TnKoprXKCQk7E0%2BPQpMNiHcs93i0ro1NeUMy6JzYMHGJep2K5ISf4%2BCr9vcLNRkrpxgH4AGVTpd7UtN%2BtMw3Wd3h%2FfEyyP%2BF5wbFargBwppX%2FOnyrRYzY0MwgQQ9J5rJv%2BJRgeegktSMc8io6nLIhv6miujP992ukRUpzWRU0ixihM4hNqhNDDSDc69SRtRTGYqe3Bz%2Bbj3XCWZfyhKODC0oh9cR%2BNU5Ae8m2LOFTPD04lBaCQHQZ7wUdpf94cMELtSeby5WBrQwVrhhILS0%2FEuOwDY%2B58PCIAP3SQAbEl0Dq1OJKyMDIfnGla7eOUz0SLa3tJtm5zUbO8ZKgCCJFN7wecbHsKwrWLRsx%2BjJdfer4jk9MVGR5MLPGptQGOqUBkPMdx01MDWyqXvXsyly3%2Bc6OzHLwOoU3mL2bdUFnRtojlLBlHbppD%2BLuJaD%2FoOPQS5J0eSqs%2BSuhIkBDv7%2FdgkfdEk2IY69IQ%2FUE5%2Bxxl0qWOS2AiFBkJ2VOXktIMFBDX0cepcJ0JhRZPelv63PLS36wgk9IIIXR%2BVTkr486LGsg9G6iaB8p9E2dShCsmPyj4gx7YTjNjuUqQWG9tWFFTpyW2121&X-Amz-Signature=df8a08b1f47d3befe27e746101e14e3f007f187809172b04afd626d78723e293&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
`_EngineBackgroundProcess`가 `ServeReplica`와 **별개 액터**(PID 377 vs 187)입니다. vLLM 엔진은 replica가 아니라 이 액터 안에서 돌고 로그도 그쪽 파일로 갑니다. `Maximum concurrency` 한 줄을 찾으려면 파드에 들어가 `/tmp/ray/session_latest/logs/`를 뒤져야 하는 이유가 이 구조입니다.
> **Triton(5장) 화면은 없습니다.** GPU가 한 장이라 Ray Serve와 배타적이고, Triton은 대시보드 UI가 없어 캡처할 화면이 사실상 메트릭 텍스트뿐입니다. 증빙은 `labs/triton-dynamic-batching/results/`의 구간 차분 기록으로 남겼습니다.
---
## 이 결과를 그대로 일반화할 수 없는 이유
1. **부하가 짧은 프롬프트 한 종류입니다.** 4-3의 결론("상한을 낮춰도 처리량이 안 아프다")은 긴 프롬프트에서는 뒤집힐 수 있습니다. 오히려 그 조건이 KV 상한이 실제로 물리는 조건입니다.
2. **계층이 왜 막는지는 규명하지 못했습니다.** 프록시인지, 라우터 replica 수인지, 직렬화인지 — "얼마나 막는가"까지만 쟀습니다. `ray_serve_*` 지표로 구간을 나눠보는 것이 다음 편의 첫 과제입니다.
3. **각 지점 1회 측정입니다.** 5-3의 동시성 8 두 칸처럼 곡선과 어긋나는 값이 있어도 재측정하지 못했습니다.
4. **레플리카가 1개입니다.** Ray Serve의 오토스케일링·로드밸런싱·KV cache aware routing은 GPU 한 장에서는 볼 수 없습니다. 계층이 주는 값을 제대로 재려면 이게 필요합니다.
5. **Triton 실험은 LLM이 아닙니다.** mobilenet으로 "요청 시간이 같을 때"를 보인 것이고, LLM에서 깨진다는 것은 지난 편 결과와의 대비로 논증했지 같은 실험으로 재지 못했습니다.
6. `Maximum concurrency`가 59.50에서 28.77로 달라진 원인은 아직 확인하지 못했습니다.
7. WSL2에서는 `pin_memory=False`로 동작합니다. 세 구성 모두 같은 조건이라 비교에는 중립이지만 절대값은 낮게 나옵니다.
8. **chunked prefill(도전과제 3)은 하지 못했습니다.** 다만 ray-llm 2.44.1의 vLLM 0.7.2는 V0 엔진이고 `chunked_prefill_enabled=False`가 기본이라 ON/OFF 비교가 **가능한** 환경임은 확인했습니다.
9. **KServe는 다루지 않았습니다.** 교재의 권장 스택이 vLLM/Triton 중심이라 이번 범위에서 뺐습니다. 대안 스택 비교는 다음 편으로 넘깁니다.
10. **배칭 4종 중 "없음"·"static"은 빈칸**입니다. 교재 자작 서버 실습을 하지 않아서입니다.
---
## 결론
이번 실험의 출발점은 단순했습니다. Ray Serve 위에서 `max_num_seqs`를 16에서 64로 늘렸지만 처리량은 822 → 852 tok/s로 거의 변하지 않았습니다. 같은 `ray-llm` 이미지에서 Ray Serve를 제외하자 처리량은 2,837 tok/s까지 증가했습니다. 이번 단일 레플리카 구성에서는 vLLM 엔진보다 Ray Serve가 포함된 서빙 계층 구간에서 먼저 병목이 나타났습니다.
이 결론을 얻으려면 비교 조건을 두 번 바로잡아야 했습니다. 먼저 vLLM 0.23.0과 0.7.2의 차이를 분리하지 않았다면 계층 비용을 39.3%로 잘못 계산할 수 있었습니다. slots=16 결과만 봤다면 비용을 32.6%로 판단했을 것입니다. 같은 엔진을 slots=64로 다시 측정한 뒤에야 이번 조건의 처리량 차이가 **70.0%**까지 커진다는 것을 확인했습니다.
KV Cache 결과도 숫자의 정의를 구분해야 한다는 점을 보여줍니다. `Maximum concurrency`는 실제 동시 사용자 수가 아니라 모든 요청이 최대 컨텍스트를 사용한다고 가정한 추정치입니다. 교재의 KV Cache 공식도 MHA 전제이므로 GQA 모델에는 KV 헤드 수를 반영해야 했고, 그렇지 않으면 계산이 **6배** 어긋났습니다.
Triton 실험은 Ray Serve 병목을 판정하는 근거에서 제외했습니다. vLLM과 같은 시스템에서 측정하지 않았기 때문입니다. 대신 Dynamic Batching의 이득이 설정값만으로 정해지지 않고 요청 도착률에 따라 달라진다는 점을 확인했습니다. 비교할 수 없는 결과를 억지로 한 표에 넣지 않는 것까지가 이번 실험에서 확인한 측정 원칙입니다.
---
## 부록. 재현 절차
<details>
<summary>펼치기</summary>
	### 0. 준비
	```bash
# WSL 세션 붙잡기 (유휴 poweroff로 k3s가 내려가는 것을 막는다) — 별도 창에서
wsl -d Ubuntu -u root -- sleep infinity

# 이미지 (실측: ray-llm 11.9 GiB 다운로드 / Triton 디스크 27.4GB)
k3s ctr images pull docker.io/rayproject/ray-llm:2.44.1-py311-cu124
docker pull nvcr.io/nvidia/tritonserver:24.12-py3

helm repo add kuberay https://ray-project.github.io/kuberay-helm/ && helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.4.2 -n kuberay --create-namespace
	```
	### 1. 구성 C — Ray Serve
	```bash
kubectl -n llm-serving-lab scale deploy/vllm-baseline --replicas=0
nvidia-smi                                   # ★ VRAM 반환 확인
kubectl apply -f labs/rayserve-on-k8s/rayservice-qwen.yaml
kubectl -n llm-serving-lab get rayservice vllm-service -w
	```
	> ⚠️ `accelerator_type: null`을 쓰지 마세요. Ray 2.44.1의 `LLMConfig` 검증이 `Unsupported accelerator type: None`으로 거부해 **Serve 앱 배포가 통째로 실패**합니다. 그런데 파드는 둘 다 정상으로 보이고 `NUM SERVE ENDPOINTS`만 비어 있어 증상이 조용합니다. **필드를 통째로 생략**해야 합니다.
	기동 로그는 `kubectl logs`에 **안 나옵니다.** Ray가 액터별 파일로 따로 씁니다.
	```bash
W=$(kubectl -n llm-serving-lab get pod -l ray.io/node-type=worker -o jsonpath={.items[0].metadata.name})
kubectl -n llm-serving-lab exec "$W" -- bash -lc \
  'grep -rhE "Maximum concurrency|reserved for KV Cache" /tmp/ray/session_latest/logs/ | sort -k2,2 -k3,3 | tail -2'
	```
	> ⚠️ `grep -r ... | tail -1`은 시간순이 아닙니다. 엔진이 재기동하면 새 액터 = 새 파일이라, 파일 이름 순으로 잘못 집습니다. 줄에 박힌 타임스탬프로 정렬해야 합니다.
	### 2. 구성 B — 같은 이미지, Ray 없음 (통제 변수 분리)
	```bash
kubectl delete -f labs/rayserve-on-k8s/rayservice-qwen.yaml
nvidia-smi                                   # ★ 0 MiB 확인
kubectl apply -f labs/rayserve-on-k8s/vllm-v072-direct.yaml
	```
	> ⚠️ 2주차의 `huggingface-cache` PVC를 붙이면 죽습니다. `vllm/vllm-openai`는 root로, `rayproject/ray-llm`은 uid 1000(`ray`)으로 돌아 `/root/.cache`를 못 읽습니다(`PermissionError`).
	### 3. ★ 구성 B를 슬롯 64로 — 계층이 천장임을 확인하는 단계
	```bash
sed 's/value: "16"/value: "64"/' labs/rayserve-on-k8s/vllm-v072-direct.yaml > /tmp/vllm-v072-seqs64.yaml
kubectl apply -f /tmp/vllm-v072-seqs64.yaml
# 같은 벤치마크를 돌려 results/b-direct-v072-seqs64.json 생성
	```
	이 단계를 빼면 "슬롯이 안 듣는다"까지만 알고 **왜 안 듣는지는 모른 채** 끝납니다.
	### 4. KV cache 스윕
	원본 매니페스트는 테스트가 지키고 있으므로 **복사본으로만** 바꿉니다.
	```bash
sed -e 's/max_model_len: .*/max_model_len: 16384/' \
    -e 's/max_num_seqs: .*/max_num_seqs: 64/' \
    labs/rayserve-on-k8s/rayservice-qwen.yaml > /tmp/rayservice-sweep.yaml
kubectl apply -f /tmp/rayservice-sweep.yaml

# 반영 확인 — 상태가 RUNNING이어도 반드시 두 곳을 본다
curl -s localhost:8000/v1/models
	```
	### 5. Triton
	WSL의 `python3`(3.14)에는 pip이 없어 `numpy`·`tritonclient`를 넣을 수 없습니다. **컨테이너 안에서 돌립니다.**
	```bash
LAB=$(pwd)/labs/triton-dynamic-batching
docker run -d --name triton --gpus all -p8009:8000 -p8010:8001 -p8011:8002 \
  -v "$LAB":/lab nvcr.io/nvidia/tritonserver:24.12-py3 \
  tritonserver --model-repository=/lab/model_dir --model-control-mode=explicit

docker exec triton pip install --quiet 'tritonclient[http]'
docker exec -e HTTP=localhost:8000 -e METRICS=http://localhost:8002/metrics \
  -e CONFIG=/lab/model_dir/mobilenet_v2/config.pbtxt -e OUT=/lab/results \
  triton bash /lab/sweep.sh
	```
	> ⚠️ 클라이언트가 보내는 텐서에는 **배치 차원이 있어야 합니다** — `(1, 3, 224, 224)`. `config.pbtxt`의 `dims: [3, 224, 224]`는 샘플 하나의 모양이고 Triton이 `max_batch_size`를 보고 배치 축을 앞에 붙입니다. `(3, 224, 224)`로 보내면 **config는 멀쩡한데 요청만 전량 실패**합니다.
	### 6. 표와 그래프
	```bash
python3 summarize_results.py \
  results/b-direct-v072-seqs64.json results/b3-seqs64.json \
  --label-regex '(b-direct-v072-seqs64|b3-seqs64)' --delta --metric output_tok_per_s

python3 tools/make_figures.py        # → articles/figures/*.svg
	```
</details>
---
## 참고 자료
- 지난 편 — [Continuous Batching이 처리량을 높이는 방식](https://app.notion.com/p/3bd4c2420ac4801899f7c33bb57f64ee)
- 환경 구축 편 — [WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기](https://app.notion.com/p/3ac4c2420ac480329705ec710b5f95ea)
- 측정 원본 — `labs/wsl2-vllm-baseline/results/` · `labs/triton-dynamic-batching/results/`
- 계층 비용 비교 — `results/c3-layer-cost.md`(슬롯 16) · `results/c3-layer-cost-seqs64.md`(슬롯 64)
- KV 손계산 검증 — `results/b3-kv-handcalc.md`

<!-- HUMANIZE-SUMMARY
원본 글자수: 47,744자
윤문본 글자수: 47,756자
변경률: 약 12% (Notion API가 이전 리비전 전문을 제공하지 않아 수정 구간 기준으로 산정)

카테고리별 탐지 건수(before → after, 핵심 서사 구간):
- C-10 번호·콜론형 제목의 기계적 반복: 18 → 2
- D-3 열거형 도입: 4 → 0
- D-5 추상 대상 의인화·범인 비유: 12 → 2
- H-3 메타 진입 표현: 6 → 1
- J-1 본문 볼드 강조 과다: 34 → 12
- E-2 동일한 종결 리듬: 10 → 3

자체검증:
1. 고유명사·수치·날짜·인용 보존: 통과
2. 변경률 30% 이하: 통과
3. 기술 실험 보고서 장르 유지: 통과
4. 격식체 유지: 통과
5. 핵심 서사 구간 S1 패턴 제거: 통과
6. 새로운 비유·과장 표현 미추가: 통과

등급: B
사유: 핵심 서사는 S1 패턴 없이 정리했으나, 전체 47,000자 문서가 Fast Path 5,000자 한도를 크게 넘어 절별로 처리했으며 증빙·부록은 보수적으로 유지함.

주요 변경 하이라이트:
- “요청이 지나는 세 층” → “Ray Serve·vLLM 두 가설과 Triton 보조 실험”
- “범인/무혐의” → 관측 결과와 적용 범위를 직접 서술
- “노브가 듣지 않았다” → 슬롯 변경 전후 처리량을 수치로 설명
- “계층이 70%를 먹었다” → 이번 구성에서 직접 vLLM보다 70.0% 낮았다고 한정
- 측정 증거 → 본문 흐름과 분리한 선택 확인 절로 표시
-->
