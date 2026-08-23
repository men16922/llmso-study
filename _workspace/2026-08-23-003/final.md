**같은 GPU와 모델에서 엔진 설정과 서빙 구조를 나눠 비교한 기록**
<callout icon="🎯" color="blue_bg">
	**핵심 결과**
	- Ray Serve에서는 엔진 설정을 바꿔도 처리량이 **822\~964 tok/s** 범위에 머물렀습니다. 같은 슬롯 변경을 vLLM 단독 구성에 적용하자 처리량은 **1,186 → 2,837 tok/s(+139%)**로 증가했습니다.
	- 동시성 64에서 각 서빙 구조의 오버헤드는 KServe RawDeployment **−2.2%**, Triton **−12.6%**, Ray Serve **−70.0%**였습니다. 각 값은 동일한 엔진 버전의 단독 구성과 비교해 계산했습니다.
	- 이번 실험에서는 요청 경로에 직접 개입하는 구조일수록 처리량과 엔진 관측성에 미치는 영향이 컸습니다. 따라서 서빙 구조를 먼저 결정한 뒤 그 구조 안에서 엔진 설정을 조정해야 합니다.
</callout>
---
<table_of_contents color="gray"/>
## 1. 무엇을 비교했나
LLM 서빙의 처리량을 높일 때는 보통 엔진 설정부터 조정합니다. vLLM은 `max_num_seqs`, `max_model_len`, `gpu_memory_utilization` 같은 설정을 제공하며, 값을 바꿔가며 비교하기도 쉽습니다.
지난 실험에서는 `max_num_seqs`(동시에 처리할 요청 슬롯 수)를 1에서 64로 늘렸을 때 처리량이 23배 증가했습니다. 이 결과만 보면 다음 최적화도 엔진 설정에서 찾기 쉽습니다.
실제 쿠버네티스 환경에서는 vLLM 앞에 배포·헬스체크·라우팅·스케일링을 담당하는 서빙 구조가 추가됩니다. 이 글에서는 Ray Serve, Triton Inference Server, KServe를 비교했습니다.
비교 대상은 엔진 설정과 서빙 구조 두 가지입니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구분</td>
<td>비교 대상</td>
<td>설정·도구</td>
</tr>
<tr>
<td>**설정**</td>
<td>vLLM 엔진 설정</td>
<td>`max_num_seqs`, `max_model_len`, `gpu_memory_utilization`</td>
</tr>
<tr>
<td>**구조**</td>
<td>배포와 요청 처리를 담당하는 서빙 구조</td>
<td>계층 없음 / Ray Serve / Triton / KServe</td>
</tr>
</table>
두 요소가 처리량과 지연 시간에 미치는 영향을 각각 측정했습니다.
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
전 구성 공통 설정은 `max_model_len=4096`, `gpu_memory_utilization=0.85`, `max_num_seqs=64`입니다(2장의 설정 스윕 구간만 예외). 계층별로 쓴 것은 이렇습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>계층</td>
<td>버전</td>
<td>품고 있는 vLLM</td>
</tr>
<tr>
<td>Ray Serve</td>
<td>KubeRay 1.4.2 / ray-llm 2.44.1</td>
<td>0.7.2</td>
</tr>
<tr>
<td>Triton</td>
<td>24.12 (`vllm-python-py3`)</td>
<td>0.5.5</td>
</tr>
<tr>
<td>KServe</td>
<td>0.20.0 (RawDeployment)</td>
<td>0.20.0</td>
</tr>
</table>
엔진 버전이 계층마다 다릅니다. 그래서 계층 비용은 항상 같은 버전끼리 짝을 만들어 쟀습니다(3-1·4-2·4-4).
> 이 글의 화면 캡처는 전부 **측정을 마친 뒤 같은 매니페스트로 다시 띄워 찍은 것**입니다(Ray Serve는 2026-08-22, Triton·KServe는 08-23). 기동값이 본문과 같은지, 관측성 주장이 실제 화면에서 성립하는지를 보이려는 것이고, **부하 조건은 본문 표와 다릅니다.** 화면 속 숫자를 표와 섞어 읽지 마세요.
![Ray Dashboard Cluster 탭 — 노드 2개 ALIVE. head 노드는 GPU N/A, gpu-group-worker 노드만 GPU \[0\] 83.0% · GRAM 10962MiB/12282MiB](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/d3ed048b-07b6-4003-825b-eb71b5ffeca5/proof-w3-02-ray-cluster-gpu.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=531ae791339e4324b3c5979e08b9ec057a33e0cce2156cdd6fa2a6fa20a92376&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
워커에만 `[0] 83.0%` / `10962MiB/12282MiB`가 붙습니다. 헤드는 `GPU N/A`입니다. 여기 보이는 12,282 MiB를 2장에서 KV 예산의 분모로 씁니다.
![Grafana NVIDIA DCGM Exporter Dashboard, 12시간 범위 — GPU Utilization 패널에 84%·91%까지 오르는 스파이크 두 개, Tensor Core Utilization 패널은 No data, GPU Framebuffer Mem Used는 최대 10.7 GB](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/56d0611b-e995-46f6-8c6f-9a0b830e1bf7/proof-w3-08-grafana-dcgm-util.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=afe476390a64afedb104346725f5f19e9f9861bcb28f38a78f355fd91d5c79a8&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
측정 구간에서 GPU 사용률이 84%·91%까지 오릅니다. 뒤에 나오는 낮은 처리량은 GPU가 놀아서 생긴 게 아닙니다. `GPU Framebuffer Mem Used` 최대 10.7 GB도 `nvidia-smi`·Ray Dashboard 값과 맞습니다.
같은 화면의 `Tensor Core Utilization`은 `No data`입니다. WSL2에서는 `DCGM_FI_PROF_*` 계열이 노출되지 않아 패널만 있고 채울 데이터가 오지 않습니다.
GPU가 한 장이라 구성끼리 배타적입니다. 앞의 것을 완전히 내리고 `nvidia-smi`로 VRAM 반환을 확인한 뒤 다음을 띄웠습니다.
부하는 전 구성 같은 명령입니다. 짧은 프롬프트, 동시성 1·2·4·8·16·32·64, 각 100요청, 요청마다 프롬프트 앞에 고유 접두사를 붙여 캐시 효과를 배제했습니다.
```bash
python3 benchmark.py --scenarios short --concurrency 1,2,4,8,16,32,64 \
  --requests-per-level 100 --warmup 1 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 --output results/<구성>.json
```
`goodput`은 TTFT ≤ 0.5초이면서 E2E ≤ 10초를 함께 만족한 요청의 비율입니다. 처리량만 보면 토큰은 나오는데 사용자는 기다리다 지치는 상태를 놓칩니다. 그 상태를 잡기 위한 지표입니다.
---
## 2. Ray Serve에서는 설정 변경의 효과가 작았다
3주차에는 Ray Serve 위에서 vLLM을 실행했습니다. 이 구성에서 `max_num_seqs`를 16에서 64로 늘렸습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>c=64 처리량</td>
<td>TTFT p95</td>
<td>goodput</td>
</tr>
<tr>
<td>Ray Serve, 슬롯 16</td>
<td>821.6 tok/s</td>
<td>3.777s</td>
<td>16%</td>
</tr>
<tr>
<td>Ray Serve, 슬롯 64</td>
<td>852.3 tok/s</td>
<td>4.006s</td>
<td>19%</td>
</tr>
<tr>
<td>**차이**</td>
<td>**+3.7%**</td>
<td>—</td>
<td>—</td>
</tr>
</table>
지난 실험에서 큰 차이를 만들었던 설정이 이번에는 처리량을 3.7% 높이는 데 그쳤습니다.
다른 엔진 설정도 확인했습니다. `max_num_seqs=64`를 유지한 채 컨텍스트 길이와 GPU 메모리 사용 비율을 바꿨습니다. 두 값은 KV Cache 예산에 직접 영향을 주므로 추정 동시성도 크게 달라졌습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>설정 (전부 slots=64)</td>
<td>기동 로그의 `Maximum concurrency`</td>
<td>c=64 처리량</td>
</tr>
<tr>
<td>기준 (len 4096, util 0.85)</td>
<td>62.04x</td>
<td>852.3 tok/s</td>
</tr>
<tr>
<td>컨텍스트 4096 → **16384**</td>
<td>14.28x</td>
<td>964.0 tok/s</td>
</tr>
<tr>
<td>메모리 0.85 → **0.60**</td>
<td>34.62x</td>
<td>961.0 tok/s</td>
</tr>
<tr>
<td>슬롯 16 (참고)</td>
<td>64.02x</td>
<td>821.6 tok/s</td>
</tr>
</table>
추정 동시성은 14.28x에서 64.02x까지 4.5배 달라졌지만, 처리량은 822\~964 tok/s 범위에 머물렀습니다.
> `Maximum concurrency`는 실제 동시 사용자 수가 아닙니다. 모든 요청이 최대 컨텍스트를 사용한다고 가정한 추정치입니다. 이번 부하는 짧은 프롬프트를 사용했으므로 이 상한에 도달하지 않았습니다.
네 가지 설정에서 측정한 최고 처리량은 964 tok/s였습니다. Ray Serve 구성의 처리량은 모든 설정에서 1,000 tok/s 아래에 머물렀습니다.
![브라우저에서 연 /v1/models 응답 — qwen2.5-1.5b 모델 하나, rayllm_metadata의 max_request_context_length가 4096](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/579142df-04c5-4ff4-974c-c36a58fef4d4/proof-w3-04-v1-models.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=692dd1cc249d2a6ebc28283a262f500028d2bf87b801f39ac5d8dd1ab58de773&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
`max_request_context_length`가 4096입니다. 위 표의 기준 행과 같은 값이니 설정이 실제로 걸려 있었습니다.
---
## 3. 같은 엔진으로 서빙 계층의 영향을 분리했다
다음으로 Ray Serve 유무에 따른 차이를 측정했습니다. 이때 엔진 버전이 다르면 서빙 계층의 영향만 분리할 수 없습니다.
### 3-1. 엔진 버전 차이를 먼저 제거했다
기준선으로 쓰려던 2주차 구성은 vLLM 0.23.0이었고 Ray Serve가 쓰는 ray-llm 이미지 안의 vLLM은 0.7.2였습니다. 그대로 비교하면 계층 비용에 엔진 버전 차이가 섞입니다.
그래서 구성을 하나 더 만들었습니다. ray-llm과 똑같은 이미지에서 Ray만 빼고 vLLM을 직접 띄운 것입니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>엔진</td>
<td>계층</td>
</tr>
<tr>
<td>A</td>
<td>vLLM 0.23.0</td>
<td>없음 (2주차 기준선)</td>
</tr>
<tr>
<td>B</td>
<td>vLLM 0.7.2</td>
<td>없음 ← **새로 만듦**</td>
</tr>
<tr>
<td>C</td>
<td>vLLM 0.7.2</td>
<td>Ray Serve</td>
</tr>
</table>
A와 C를 그냥 비교하면 −39.3%가 나옵니다. 하지만 A→B(엔진 버전만)가 이미 −9.9%였으니 B와 C를 비교해야 계층만의 값이 나옵니다.
이 구성 하나를 더 만드는 데 15분이 들었고 그게 이 글에서 확신할 수 있는 숫자를 만들었습니다.
### 3-2. Ray Serve를 제외하자 슬롯 설정의 효과가 나타났다
Ray Serve를 제외한 구성 B에서도 같은 슬롯 변경을 적용했습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구조</td>
<td>슬롯 16 → 64, c=64 처리량</td>
<td>변화</td>
</tr>
<tr>
<td>Ray Serve</td>
<td>821.6 → 852.3</td>
<td>**+3.7%**</td>
</tr>
<tr>
<td>계층 없음</td>
<td>1,186.1 → 2,836.8</td>
<td>**+139.2%**</td>
</tr>
</table>
엔진, 설정, 부하는 같고 Ray Serve 유무만 다릅니다.
`max_num_seqs` 설정은 정상적으로 동작했습니다. 다만 Ray Serve 구성에서는 서빙 계층이 먼저 포화해 엔진의 추가 처리 능력을 활용하지 못했습니다.
여기서 계층이라고 부른 것의 실체는 이렇게 생겼습니다.
![Ray Dashboard Serve 탭 — Controller HEALTHY, Proxy HEALTHY ×2, Application RUNNING ×1. llm 애플리케이션 아래 LLMDeployment:qwen2_5-1_5b가 replica 1개, LLMRouter가 replica 2개로 HEALTHY 상태](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/f98a972d-0eb3-49c4-a652-33a7223b6600/proof-w3-01-ray-serve-tab.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=54038cf6df84bd22f59bb1c29a325cdaddf99d25d3d6b92d2e30c045d5e13b82&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
엔진을 감싼 `LLMDeployment` replica 1개 앞에 `LLMRouter` replica 2개와 프록시가 섭니다.
### 3-3. 부하가 클수록 차이가 커졌다
같은 엔진(0.7.2)·같은 설정(슬롯 64)에서 계층 하나만 놓고 동시성별로 비교하면 이렇게 나옵니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>계층 없음</td>
<td>Ray Serve</td>
<td>차이</td>
</tr>
<tr>
<td>1</td>
<td>104.6</td>
<td>97.6</td>
<td>−6.7%</td>
</tr>
<tr>
<td>2</td>
<td>201.1</td>
<td>182.4</td>
<td>−9.3%</td>
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
<td>**64**</td>
<td>**2,836.8**</td>
<td>**852.3**</td>
<td>**−70.0%**</td>
</tr>
</table>
![슬롯을 64로 열었을 때 계층 유무 비교 — 직접 vLLM은 동시성이 오를수록 처리량이 계속 올라 c=64에서 2,837 tok/s에 닿지만, Ray Serve는 c=16 부근부터 850 근처에서 평평해진다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/6ad9dcd8-1444-457c-8b9b-a6e33302b33a/fig-c3-seqs64-throughput.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=f359128c3dc5627b606ed1fefcb3a654406ffcf6b66f08804a76331f533b8f01&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
동시성이 1일 때 처리량 차이는 6.7%였지만, 동시성 64에서는 70.0%까지 커졌습니다. Ray Serve의 영향은 부하가 증가할수록 확대됐습니다.
slots=16에서만 측정하면 차이는 37.9%입니다. slots=64로 엔진의 처리 폭을 넓힌 뒤에는 차이가 70.0%로 늘었습니다.
![Prometheus DCGM_FI_DEV_GPU_UTIL 그래프 — 15분 구간에서 부하 시각에만 0%에서 약 83%로 사각 펄스가 올라갔다 내려온다. 시계열 라벨의 exported_pod가 vllm-service의 gpu-group-worker 파드](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/63011358-f730-4fcb-a3e9-94b5e11ad19c/proof-w3-03-dcgm-gpu-util.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=b3d05d4a19241c461c5cbee6ccf5bad39e7efa1458f1fb3f536c808ed8ce6559&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
부하 구간에서 사용률이 83%까지 올랐습니다. 시계열 라벨의 `exported_pod`가 Ray 워커 파드라 이 일이 어디서 나왔는지까지 메트릭이 남깁니다. 이 그래프를 만든 것은 동시성 64로 900요청을 건 별도의 지속 부하입니다(1,036.9 tok/s, goodput 2.1%).
지연과 goodput을 같이 보면 성격이 분명해집니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>계층 없음 TTFT p95 / goodput</td>
<td>Ray Serve TTFT p95 / goodput</td>
</tr>
<tr>
<td>16</td>
<td>0.112s / 100%</td>
<td>0.285s / 100%</td>
</tr>
<tr>
<td>32</td>
<td>0.190s / 100%</td>
<td>1.698s / 48%</td>
</tr>
<tr>
<td>64</td>
<td>0.330s / 100%</td>
<td>4.006s / **19%**</td>
</tr>
</table>
계층 없는 구성은 c=64에서도 TTFT p95가 0.33초로 SLO(0.5초) 안이고 goodput 100%입니다. Ray Serve는 c=32부터 무너져 c=64에서 10건 중 8건이 SLO를 못 지킵니다. 운영에서는 처리량 감소보다 SLO 미충족이 사용자 경험에 더 직접적인 영향을 줍니다.
---
## 4. Triton과 KServe도 같은 방식으로 비교했다
Ray Serve 결과만으로 서빙 계층 전체를 평가할 수는 없습니다. 같은 방법으로 Triton과 KServe의 오버헤드도 측정했습니다.
### 4-1. Triton을 비교 대상으로 선택한 이유
Triton Inference Server는 NVIDIA가 vLLM 백엔드를 공식 지원하며, Ray Serve와 마찬가지로 모델을 HTTP API로 제공할 수 있습니다. 역할이 비슷해 서빙 계층의 오버헤드를 비교하기에 적합했습니다. Triton의 Dynamic Batching 실험은 부록 A에 따로 정리했습니다.
### 4-2. Triton도 같은 엔진으로 기준선을 만들었다
Triton 24.12 컨테이너 안의 vLLM은 0.5.5로 Ray Serve의 0.7.2보다도 낮습니다. Ray Serve 때와 똑같은 함정입니다.
그래서 똑같이 처리했습니다. Triton 이미지에서 Triton만 빼고 vLLM 0.5.5를 직접 띄워 짝을 만들었습니다.
두 구성의 기동 로그에는 모두 `# GPU blocks: 15326`이 기록됐습니다. KV Cache 예산이 같으므로 비교 조건도 일치합니다.
### 4-3. Triton 적용 전후 차이
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>계층 없음 (0.5.5)</td>
<td>Triton + vLLM (0.5.5)</td>
<td>차이</td>
</tr>
<tr>
<td>1</td>
<td>98.0</td>
<td>91.5</td>
<td>−6.6%</td>
</tr>
<tr>
<td>2</td>
<td>186.7</td>
<td>173.1</td>
<td>−7.3%</td>
</tr>
<tr>
<td>4</td>
<td>348.6</td>
<td>330.0</td>
<td>−5.3%</td>
</tr>
<tr>
<td>8</td>
<td>633.4</td>
<td>603.4</td>
<td>−4.7%</td>
</tr>
<tr>
<td>16</td>
<td>1,065.3</td>
<td>1,021.3</td>
<td>−4.1%</td>
</tr>
<tr>
<td>32</td>
<td>1,593.4</td>
<td>1,537.1</td>
<td>−3.5%</td>
</tr>
<tr>
<td>64</td>
<td>2,310.1</td>
<td>2,018.9</td>
<td>−12.6%</td>
</tr>
</table>
곡선의 모양이 다릅니다. Ray Serve는 부하가 커질수록 비용이 커졌습니다(6.7% → 70%). Triton은 부하와 무관하게 평평하고(3.5\~12.6%) 부하가 커질 때 오히려 줄어드는 구간도 있습니다.
goodput은 c=64에서도 100%이고 TTFT p95는 0.384초로 SLO 안입니다.
![브라우저에서 연 :9000/v1/models 응답 — 모델 하나(id qwen), owned_by가 "Triton Inference Server"](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/dbc33614-a935-4674-9ef6-e8626a95c214/proof-w3-10-triton-v1-models.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=b92fbaf46e7e9c0fbf20d8db57aaa421c342829c643a5169ab28f6aaeaa7547b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
같은 OpenAI 규격이어도 응답을 만든 주체는 `owned_by`가 밝힙니다.
> c=64의 −12.6%는 조심해서 읽어야 합니다. 같은 서버를 두 번 잰 재현 측정에서 c=64만 10% 가까이 흔들렸습니다(c≤32는 1.3% 안). c=64에서 10%대 차이는 잡음과 구별되지 않습니다. **확실한 것은 "Triton의 계층 비용은 한 자릿수\~10%대이고, Ray Serve의 70%와는 자릿수가 다르다"까지입니다.**
### 4-4. KServe RawDeployment 적용 전후 차이
여기서 계층을 하나 더 올렸습니다. KServe는 쿠버네티스에서 모델 서빙을 CRD(`InferenceService`)로 선언하는 표준에 가장 가까운 프로젝트이고 앞의 둘과 성격이 다릅니다.
Istio·Knative가 없는 k3s라 RawDeployment 모드로 설치했습니다.
여기서도 짝을 만들었습니다. KServe가 쓰는 이미지는 `vllm/vllm-openai:v0.20.0`이라 또 다른 버전이어서 같은 이미지·같은 인자로 KServe 없이 Deployment 하나만 띄운 구성을 만들어 비교했습니다.
두 구성의 기동 로그가 `GPU KV cache size: 247,024 tokens` / `Maximum concurrency ... 60.31x`로 완전히 같습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>계층 없음 (0.20.0)</td>
<td>KServe + vLLM (0.20.0)</td>
<td>차이</td>
</tr>
<tr>
<td>1</td>
<td>113.5</td>
<td>113.7</td>
<td>+0.2%</td>
</tr>
<tr>
<td>2</td>
<td>217.4</td>
<td>217.8</td>
<td>+0.2%</td>
</tr>
<tr>
<td>4</td>
<td>422.7</td>
<td>426.6</td>
<td>+0.9%</td>
</tr>
<tr>
<td>8</td>
<td>791.3</td>
<td>781.8</td>
<td>−1.2%</td>
</tr>
<tr>
<td>16</td>
<td>1,400.5</td>
<td>1,384.9</td>
<td>−1.1%</td>
</tr>
<tr>
<td>32</td>
<td>2,032.5</td>
<td>2,166.5</td>
<td>+6.6%</td>
</tr>
<tr>
<td>64</td>
<td>2,714.2</td>
<td>2,654.0</td>
<td>−2.2%</td>
</tr>
</table>
계층 비용이 사실상 0입니다. 부호가 왔다 갔다 하는 걸 보면 잡음과 구별되지 않는 수준입니다. goodput은 양쪽 다 100%, TTFT p95는 0.296s 대 0.310s입니다.
![브라우저에서 연 KServe 예측기 :30080/v1/models 응답 — id qwen, owned_by가 "vllm", root가 /mnt/models/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306, max_model_len 4096](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/97b1de0e-4253-410f-b70d-f40911e8cb61/proof-w3-13-kserve-v1-models.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=dd39a35afd6a0bd7c13233b53f9d6f90c12796bea5367888c3325e4814a07d7a&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
같은 자리에서 `owned_by`가 `vllm`입니다. `root`의 `/mnt/models/hub/...`는 KServe가 `storageUri`로 붙여 준 HF 캐시 경로이고 `max_model_len` 4096은 본문 통제 변수와 같습니다.
### 4-5. 요청 경로 개입 여부
세 구조의 오버헤드가 −2.2%, −12.6%, −70.0%로 달랐습니다. 이번 구성에서는 요청 경로에 개입하는 방식이 차이를 설명했습니다.
- KServe(RawDeployment)는 컨트롤 플레인입니다. `InferenceService`를 받아 Deployment와 Service를 만들어 주고 그다음엔 요청 경로에서 빠집니다. 클라이언트 요청은 vLLM 자신의 HTTP 서버로 곧장 갑니다. 통과하는 게 없으니 낼 비용도 없습니다.
- Triton과 Ray Serve는 데이터 플레인입니다. 모든 요청이 그들의 서버를 거쳐 엔진으로 들어갑니다. 그래서 통과 비용이 생기고 그 비용이 동시성에 따라 어떻게 늘어나느냐가 둘을 갈랐습니다.
이 결과만으로 KServe가 더 우수하다고 결론 내릴 수는 없습니다. 세 도구의 역할이 다르기 때문입니다. KServe는 요청을 중계하지 않으므로 요청 단위로 뭔가를 할 수 없습니다. Ray Serve가 제공하는 요청 단위 라우팅, 모델 조합, 파이썬 파이프라인은 요청 경로에 직접 개입해야 구현할 수 있습니다.
---
## 5. 서빙 구조별 측정 결과
모든 구성은 같은 GPU·모델·부하 조건에서 측정했습니다. 오버헤드는 각 도구가 사용하는 엔진과 동일한 버전의 단독 구성에 대비해 계산했습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>계층</td>
<td>요청 경로에 서나</td>
<td>엔진</td>
<td>계층 비용 (c=64)</td>
<td>goodput (c=64)</td>
<td>TTFT p95 (c=64)</td>
<td>`vllm:*` 메트릭</td>
</tr>
<tr>
<td>**없음**</td>
<td>—</td>
<td>0.7.2 / 0.5.5 / 0.20.0</td>
<td>—</td>
<td>100%</td>
<td>0.30\~0.35s</td>
<td>15 / 21 / 66개</td>
</tr>
<tr>
<td>**KServe** (RawDeployment)</td>
<td>**아니오** (컨트롤 플레인)</td>
<td>0.20.0</td>
<td>**−2.2%**</td>
<td>**100%**</td>
<td>0.310s</td>
<td>**66개 (보존)**</td>
</tr>
<tr>
<td>**Triton**  • vLLM 백엔드</td>
<td>예</td>
<td>0.5.5</td>
<td>**−12.6%**</td>
<td>**100%**</td>
<td>0.384s</td>
<td>0개 (`nv_*` 22개)</td>
</tr>
<tr>
<td>**Ray Serve** (ray-llm)</td>
<td>예</td>
<td>0.7.2</td>
<td>**−70.0%**</td>
<td>**19%**</td>
<td>4.006s</td>
<td>0개 (`ray_*` 184개)</td>
</tr>
</table>
동시성이 증가할 때 오버헤드가 어떻게 변하는지도 함께 비교했습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>동시성</td>
<td>KServe</td>
<td>Triton</td>
<td>Ray Serve</td>
</tr>
<tr>
<td>1</td>
<td>+0.2%</td>
<td>−6.6%</td>
<td>−6.7%</td>
</tr>
<tr>
<td>8</td>
<td>−1.2%</td>
<td>−4.7%</td>
<td>−19.1%</td>
</tr>
<tr>
<td>16</td>
<td>−1.1%</td>
<td>−4.1%</td>
<td>−37.9%</td>
</tr>
<tr>
<td>32</td>
<td>+6.6%</td>
<td>−3.5%</td>
<td>−57.4%</td>
</tr>
<tr>
<td>64</td>
<td>−2.2%</td>
<td>−12.6%</td>
<td>**−70.0%**</td>
</tr>
</table>
![서빙 구조별 오버헤드 변화 — 가로축 동시 요청 수, 세로축 계층 비용 %. KServe는 0% 선 근처에 붙어 있고, Triton은 −3\~−13% 사이에서 평평하며, Ray Serve만 동시성이 오를수록 아래로 벌어져 −70%에 닿는다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/22397350-179f-4349-8504-c8a855ea5738/fig-c3-layer-cost.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=483726c98c111932cd04925ad58770e335492188d3e4d4074fb7673071534777&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
- **KServe**: 측정값이 0% 부근에서 오르내려 잡음과 구분하기 어렵습니다.
- **Triton**: 동시성이 증가해도 오버헤드는 대체로 한 자릿수에서 10%대였습니다.
- **Ray Serve**: 동시성이 높아질수록 차이가 커졌고, goodput은 c=32부터 감소했습니다.
동시성 64에서 Ray Serve의 goodput은 19%였습니다. 처리량 감소와 함께 SLO 충족률도 확인해야 하는 이유입니다.
---
## 6. 관측성 차이
서빙 구조는 엔진 지표를 확인하는 방법도 바꿉니다.
vLLM은 `/metrics`에 자기 상태를 내놓습니다. KV cache 사용률, 대기 중인 요청 수, 선점(preemption) 횟수, TTFT 히스토그램처럼 서빙을 진단할 때 실제로 보게 되는 값들입니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>구성</td>
<td>메트릭 엔드포인트</td>
<td>`vllm:*` 이름 수</td>
<td>대신 주는 것</td>
</tr>
<tr>
<td>계층 없음 (0.20.0)</td>
<td>`:8080/metrics` → 200</td>
<td>**66개**</td>
<td>—</td>
</tr>
<tr>
<td>계층 없음 (0.5.5)</td>
<td>`:8000/metrics` → 200</td>
<td>21개</td>
<td>—</td>
</tr>
<tr>
<td>계층 없음 (0.7.2)</td>
<td>200</td>
<td>15개</td>
<td>—</td>
</tr>
<tr>
<td>**KServe**  • vLLM</td>
<td>`:8080/metrics` → 200</td>
<td>**66개 (그대로)**</td>
<td>—</td>
</tr>
<tr>
<td>Triton + vLLM</td>
<td>`:9000/metrics` → 200</td>
<td>**0개**</td>
<td>`nv_*` 22개</td>
</tr>
<tr>
<td>Ray Serve + vLLM</td>
<td>`:8000/metrics` → **404**</td>
<td>**0개**</td>
<td>`ray_*` 184개 (`:8080`)</td>
</tr>
</table>
KServe RawDeployment에서는 vLLM의 `/metrics`와 66개 지표가 그대로 노출됐습니다. Triton과 Ray Serve에서는 vLLM 엔진이 내부 라이브러리로 실행되어 `vllm:*` 지표가 직접 노출되지 않았습니다.
같은 자리를 세 구성에서 열어 보면 이렇습니다.
**KServe** — 이름이 전부 `vllm:`으로 시작합니다.
![KServe 예측기 :30080/metrics 중간 부분 — vllm:num_requests_running, vllm:num_requests_waiting, vllm:num_requests_waiting_by_reason, vllm:kv_cache_usage_perc, vllm:prefix_cache_queries_total 209650, vllm:prefix_cache_hits_total 38452, vllm:num_preemptions_total 등 vllm: 으로 시작하는 이름이 이어진다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/1e1cc675-e272-4cb4-a026-1f52c9de9379/proof-w3-14-kserve-metrics.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=c92075827f9feda57459903432a9ab177e5e57ef467bc53ff05c773bcef775c2&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
`vllm:prefix_cache_queries_total 209650` / `vllm:prefix_cache_hits_total 38452`에 방금 건 부하가 그대로 들어왔습니다(2,400요청, 3,248.3 tok/s, goodput 100%).
**Triton** — 같은 자리에 `nv_`로 시작하는 이름만 있고 `vllm:`은 한 줄도 없습니다.
![Triton :9000/metrics 전문 — nv_inference_request_success 2401, nv_inference_queue_duration_us 1179290, nv_gpu_utilization·nv_gpu_memory_used_bytes 등 nv_로 시작하는 이름만 나열되고 vllm: 로 시작하는 이름은 하나도 없다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/0645a70b-85a0-4d9a-bc35-f872bdc511d2/proof-w3-11-triton-metrics.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=6f70a1539d20a724eae048ab293a5705289fed6093e3a33ab5cad0443e16ef61&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
메트릭은 정상적으로 기록됐습니다. 동시성 64로 2,400요청을 보낸 직후에 확인했습니다(2,243.6 tok/s, goodput 100%). 부하 전 0이던 카운터가 이렇게 올라갔습니다.
<table fit-page-width="true" header-row="true">
<tr>
<td>지표</td>
<td>부하 전</td>
<td>부하 후</td>
</tr>
<tr>
<td>`nv_inference_request_success`</td>
<td>0</td>
<td>2,401</td>
</tr>
<tr>
<td>`nv_inference_count`</td>
<td>0</td>
<td>2,401</td>
</tr>
<tr>
<td>`nv_inference_queue_duration_us`</td>
<td>0</td>
<td>1,179,290</td>
</tr>
</table>
누적 큐 대기 1,179,290µs를 2,401건으로 나누면 건당 약 491µs입니다.
**Ray Serve** — 엔드포인트 자체가 없습니다.
![같은 호스트의 :8000/metrics 응답 — detail Not Found](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/4c40c6be-ad33-4a44-bb82-d1b279180ec4/proof-w3-05-metrics-404.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174003Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=70fdb7fc50d755cf5b25c21c32c90410291e373a8bf8714f57613904cf2ac202&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
`/v1/models`가 정상 응답한 것과 **같은 포트**입니다.
대신 각 도구가 자체 지표를 제공합니다.
- **Triton**의 `nv_*` 22개에는 `nv_inference_queue_duration_us`(큐에서 기다린 시간)와 `nv_inference_pending_request_count`(대기 요청 수)가 있습니다. "큐에 밀렸나"를 계층 층위에서 볼 수 있습니다.
- **Ray Serve**의 `ray_*` 184개는 배포·액터·replica 단위 지표입니다. 다만 `:8000/metrics`가 404이고 `:8080`에 따로 있어 찾아가는 것부터 한 단계입니다.
Triton과 Ray Serve에서는 vLLM의 KV Cache 사용률과 선점 횟수를 직접 확인할 수 없었습니다. "메모리가 모자라 요청이 밀려났는가"를 엔진에게 직접 물을 수 없습니다.
위 KServe 화면에는 그 두 가지가 `vllm:kv_cache_usage_perc`와 `vllm:num_preemptions_total`로 그대로 있습니다. Triton 화면의 `nv_` 목록에는 대응하는 이름이 없습니다.
Ray Serve에서는 엔진 로그의 위치도 달라집니다. vLLM 엔진은 `ServeReplica`가 아니라 `_EngineBackgroundProcess`라는 별개 액터에서 돌고 기동 로그도 그쪽 파일로 갑니다. `Maximum concurrency` 한 줄을 보려고 파드에 들어가 `/tmp/ray/session_latest/logs/`를 뒤져야 했습니다.
![Ray Dashboard Serve 탭의 Deployments 로그 뷰 — LLMDeployment replica의 STDOUT에 4줄만 있고 vLLM 엔진 기동 로그가 없다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/329d403a-c6c3-4c70-80c1-22e02f1c6ca5/proof-w3-06-replica-stdout-empty.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174004Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=94120cf7a376650b8b952bb0e7cffc9caefce877ce2828a230caafb6a6a177e1&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
![Ray Dashboard Actors 탭 — 액터 9개 ALIVE. _EngineBackgroundProcess(PID 377)와 ServeReplica의 LLMDeployment(PID 187)가 서로 다른 액터로 잡혀 있다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/5ee6e94c-9967-47c1-97ad-658d61a3eba1/proof-w3-07-ray-actors.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174004Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=4044464d1726fd01bea80b6b2273e809fad70beb3d8c3d6395a7d7bd82bfe27f&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
replica의 STDOUT에는 네 줄뿐입니다. `_EngineBackgroundProcess`는 `ServeReplica`와 **별개 액터**(PID 377 vs 187)입니다. 그래서 기동 로그가 replica 쪽에 없습니다.
GPU 지표에 붙는 출처 라벨도 실행 방식에 따라 달랐습니다.
![Prometheus DCGM_FI_DEV_GPU_UTIL 그래프 15분 구간 — 왼쪽 청록 계열이 45%에서 65%로 올랐다 내려오고, 오른쪽 초록 계열이 35%에서 99%로 올랐다 내려온다. 초록 시계열의 라벨에 exported_container kserve-container, exported_namespace llm-serving-lab, exported_pod qwen-predictor가 붙어 있다](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/5e49d7c3-9df5-4026-ae4b-dd2d78c252fe/proof-w3-15-gpu-util-triton-kserve.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174004Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=ae9663751cb8bc67aba0d2a829371da220216050e9d194785f4da73db28e5363&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
한 그래프에 두 부하가 나란히 있습니다. 왼쪽 봉우리가 Triton, 오른쪽이 KServe입니다. 오른쪽 시계열에만 `exported_pod="qwen-predictor-..."`가 붙습니다. KServe 예측기는 쿠버네티스 파드라 DCGM 지표에 출처가 박히지만 도커로 띄운 Triton은 그 라벨이 없습니다.
---
## 7. 적용 순서
### 7-1. 서빙 구조를 먼저 결정한다
배포 방식, 요청 라우팅, 모델 조합, 오토스케일링, 필요한 메트릭을 기준으로 서빙 구조를 선택합니다. 이번 실험에서는 구조를 바꿨을 때의 처리량 차이가 Ray Serve 내부에서 엔진 설정을 바꿨을 때보다 컸습니다.
### 7-2. 선택한 구조에서 엔진을 조정한다
서빙 구조를 정한 뒤 `max_num_seqs`, `max_model_len`, `gpu_memory_utilization`을 조정합니다. vLLM 단독 구성에서는 slots=16 → 64 변경으로 처리량이 139% 증가했습니다. 설정 자체가 효과가 없는 것이 아니라, 앞단이 먼저 포화하면 효과가 드러나지 않습니다.
### 7-3. 설정 변경이 효과가 없으면 기준선을 비교한다
설정을 크게 바꿨는데 처리량과 지연 시간이 거의 달라지지 않는다면, 같은 엔진을 서빙 계층 없이 실행해 비교합니다. 단독 구성에서 차이가 나타나면 엔진 설정보다 서빙 구조를 먼저 점검할 수 있습니다.
### 7-4. 성능과 운영 기능을 함께 판단한다
이번 측정에서 Ray Serve, Triton, KServe RawDeployment의 오버헤드는 각각 달랐습니다. 그러나 이 수치만으로 도구의 우열을 정할 수는 없습니다. 요청 단위 라우팅과 모델 조합이 필요하면 데이터 플레인 계층이 필요하고, 선언형 배포가 목적이라면 요청 경로에 개입하지 않는 구조를 선택할 수 있습니다.
---
## 8. 실험의 한계
1. 짧은 프롬프트 한 종류만 사용했습니다. 긴 프롬프트에서는 KV Cache 상한이 처리량에 직접 영향을 줄 수 있습니다.
2. Ray Serve에서 병목이 발생한 정확한 원인은 규명하지 못했습니다. 프록시, 라우터 replica 수, 직렬화 비용 가운데 어느 요소가 영향을 줬는지 `ray_serve_*` 지표로 추가 측정해야 합니다.
3. 각 지점 1회 측정입니다. 같은 서버를 두 번 잰 재현 측정에서 c=64만 10% 가까이 흔들렸습니다(c≤32는 1.3% 안). c=64에서 10%대 차이는 잡음과 구별되지 않습니다.
4. 엔진 버전이 구성마다 다릅니다. Ray Serve는 0.7.2, Triton은 0.5.5, KServe는 0.20.0입니다. 그래서 계층 비용은 항상 같은 버전끼리 짝을 만들어 쟀습니다. 다만 구성끼리의 절대값 비교(2,837 vs 2,310)에는 버전 차이가 섞여 있습니다.
5. 레플리카가 1개라 Ray Serve의 오토스케일링·로드밸런싱·KV cache aware routing은 측정하지 못했습니다. 따라서 이 글은 성능 오버헤드만 비교하며 운영 기능의 효용은 평가하지 않습니다.
6. Triton 구성에서는 토큰을 스트림 이벤트 수로 셌습니다. Triton 24.12 프론트엔드가 `stream_options`를 거부해 `usage`를 못 받기 때문입니다. 같은 서버에서 두 방식을 비교해 확인한 결과 c≤32에서 차이는 1.3% 안이었고 실제 토크나이저 대조에서도 46 대 47토큰(오차 2%)이었습니다.
7. KV 예산은 정적 공식이 아니라 기동 시 프로파일링 결과입니다. 그래서 같은 설정으로 다시 띄워도 `Maximum concurrency`가 달라질 수 있고, 지난 편에서는 같은 구성이 두 배 차이로 갈린 적도 있습니다. 원인은 아직 못 밝혔습니다. 이번 측정에서는 짝마다 기동 로그의 KV 값이 일치하는 것을 확인하고 진행했습니다.
8. WSL2에서 `pin_memory=False`로 동작합니다. 전 구성 같은 조건이라 비교에는 중립이지만 절대값은 낮게 나옵니다.
9. chunked prefill은 하지 못했습니다. 다만 ray-llm 2.44.1의 vLLM 0.7.2는 V0 엔진이고 `chunked_prefill_enabled=False`가 기본이라 ON/OFF 비교가 가능한 환경임은 확인했습니다.
10. KServe는 RawDeployment 모드만 측정했습니다. Istio·Knative 기반 Serverless 모드의 scale-to-zero와 트래픽 분할은 범위에서 제외했습니다. −2.2%는 RawDeployment 구성의 결과입니다.
마지막으로 쓰지 않기로 한 지표가 하나 있습니다.
![Grafana DCGM 대시보드 상단 — GPU Temperature가 유휴 46도 대에서 측정 구간에만 60도·69도로 치솟는다. GPU Avg. Temp 게이지는 46.1도](https://prod-files-secure.s3.us-west-2.amazonaws.com/d3427551-025a-4992-86f8-60e800d6ced0/c4588a57-f1ad-4d71-aeec-03e0fd52766d/proof-w3-09-grafana-dcgm-temp.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TLMC3HK3%2F20260822%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260822T174004Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIFCFml1olhb3Sudli%2Fx5AjZdNFl%2BQex54WbkAp5TJZXtAiEAme5h7Q1Y%2B0sptK6SxxgJ5LxYqD7oUkGc0knrpoKux%2BgqiAQIwv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDL7wj7ibigCr%2FzFTTCrcAzuGEliDgdVrnm5tDC0kF5wmvHWxh287sLmVyPWRfYR3veV9pFCE0v4AvOWAcD0WNTxqxJBMgRcCUNWrGmA051HcXwWWum998XluyrWnQzj6jelQyEZAto4XeRzYs%2FKEwnmw%2BPcgnCnQxod5bOK1BkoRch1Y%2BKeyYukF%2BFiMExlcjfILDPyJuHIRDmJaBAysBVNuxESWp9s%2B8zXnrrxS9wayFwAzVU7rbm57ktKtvZDzbW3Kt%2BAKWY9CTsJsOYYM4L0eG8ibew2x%2BiI4XHG7FO7Mpwr7egqF4BWPgs7i0Uq6jdxM5hP%2B4gkuyz1gAVioTGdCAnXDhpMh56Tvzo6XAiPEErbUqRzCOVOGKZPK5%2Fu1Y1qafy9oNA%2FJeFhGi2cEfQpRIXMIKeEZZWGl0u976vkWdQE8Zpfg9tZgxd2gwfIbGhiUYUjMJzS5r78qF3bztcRxdcaA0xqtErSzDFOECtNQ%2F3BQRlY8qQbiosBFBqFdllbGa3cOMLtIHFXDzJZXquV18qGMjxuKw3vCaoNt25uhqoh1Cq%2F%2B9f1LGgFxDVoo2Zqa2dhPEYtomhYmW592Hswkw79921L5eKGvTJaxQXvoa4Z%2FKRbZucYAluArmFmA4EOTzJVIXyjysMDKMNuxp9QGOqUBRFP01yzWw1Go%2FC4TFtM5PAk9YOIY7NWGQyMe2B7uBILJKjTTdgkflpKMjY2ezlbpB2YNp7itkNhGclAbK7q1xajc9SZTVR%2BRP%2BXW%2F%2F52tOwUTtaVfIak8YJb1hNLHNR3e0QIPLsZpIY8GNbyXlWV%2B6mk7cSwlcc%2FkNuQYIVBQTm8VCFnkuxvkquL47J4WKn0ipAM5DzPBkkyxVOjqiGIYse4ZiMZ&X-Amz-Signature=596932a8588076f68f81ac3e5748f40b7fe765b8128203e969ced1f9bc6da8e3&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
> ⚠️ 온도는 유휴 46°C에서 측정 구간에만 60·69°C로 오릅니다. 다만 같은 화면의 `GPU Power Usage`가 **최대 593 W**로 읽힙니다. 이 GPU는 70 W 제품이라 그대로 믿을 수 없는 값이고, 원인을 확인하지 않았으므로 **이 글에서 전력 수치는 쓰지 않았습니다.**
---
## 결론
이번 실험에서는 엔진 설정과 서빙 구조가 처리량에 미치는 영향을 분리해 측정했습니다. Ray Serve에서 네 가지 엔진 설정을 비교했을 때 처리량은 822\~964 tok/s 범위였습니다. 같은 슬롯 변경을 vLLM 단독 구성에 적용하자 처리량은 1,186 → 2,837 tok/s로 증가했습니다.
서빙 구조별 오버헤드는 같은 엔진 버전의 단독 구성과 짝을 맞춰 계산했습니다. 동시성 64에서 KServe RawDeployment는 −2.2%, Triton은 −12.6%, Ray Serve는 −70.0%였습니다. Ray Serve의 차이는 부하가 증가할수록 커졌고 goodput도 19%까지 낮아졌습니다.
관측성도 구조에 따라 달랐습니다. KServe RawDeployment에서는 vLLM 지표 66개가 유지됐지만, Triton과 Ray Serve에서는 자체 메트릭을 사용해야 했습니다. 처리량뿐 아니라 필요한 엔진 지표를 계속 확인할 수 있는지도 구조 선택에 포함해야 합니다.
이 결과는 단일 GPU와 레플리카 1개에서 얻은 값입니다. 특정 도구의 우열을 뜻하지 않습니다. 운영 요구사항에 맞는 서빙 구조를 먼저 선택하고, 그 안에서 엔진 설정을 조정하는 것이 이번 실험의 결론입니다.
---
## 부록 {toggle="true"}
	### 부록 A. Triton의 dynamic batching은 왜 LLM에 안 맞나
	4장에서 Triton을 vLLM 백엔드로 썼습니다. 그런데 Triton에는 자체 배칭 기능인 dynamic batching이 따로 있습니다. 왜 그걸 쓰지 않았는지를 확인하려고 별도로 재 봤습니다.
	dynamic batching은 요청이 오면 바로 처리하지 않고 `max_queue_delay_microseconds` 동안 기다려 여러 개를 묶습니다. 모델은 `mobilenet_v2`(ONNX)를 썼습니다. LLM이 아닌 이유는 바로 아래에 나옵니다.
	<table fit-page-width="true" header-row="true">
<tr>
<td>지연 설정</td>
<td>c=1</td>
<td>c=8</td>
<td>c=32</td>
</tr>
<tr>
<td>없음 (대조군)</td>
<td>258.9 inf/s</td>
<td>1,290.6</td>
<td>1,368.9</td>
</tr>
<tr>
<td>1ms</td>
<td>246.9</td>
<td>1,281.1</td>
<td>1,371.4</td>
</tr>
<tr>
<td>20ms</td>
<td>**37.5**</td>
<td>396.1</td>
<td>**1,371.2**</td>
</tr>
	</table>
	대조군의 평균 배치 크기는 정확히 1.00이었습니다. 기능이 꺼져 있음을 확인한 값입니다.
	읽는 법은 이렇습니다. 동시성이 낮으면 기다린 시간이 그대로 손해입니다(20ms에서 37.5 inf/s, 대조군의 7분의 1). 도착률이 충분히 높으면 기다릴 필요가 없어 차이가 사라집니다(c=32에서 셋 다 1,370 근처). dynamic batching의 효과를 정하는 것은 설정값이 아니라 도착률입니다.
	LLM에서 이게 안 맞는 이유는 전제에 있습니다. dynamic batching은 "묶은 요청들이 같은 시간에 끝난다"를 전제로 합니다. mobilenet은 입력 크기가 같으면 처리 시간도 같으니 성립합니다. 그런데 LLM은 요청마다 출력 길이가 다릅니다. 10토큰짜리와 500토큰짜리를 한 배치로 묶으면 먼저 끝난 요청이 나머지를 기다립니다.
	그래서 vLLM은 이 방식 대신 continuous batching을 씁니다. 배치를 미리 묶지 않고 토큰 생성 단계마다 끝난 요청을 빼고 대기 중인 요청을 채웁니다. 4장에서 Triton의 dynamic batching을 끄고 배칭을 vLLM 백엔드에 맡긴 이유가 이것입니다.
	### 부록 B. KV cache 공식이 6배 어긋난 자리
	2장에서 KV cache 예산을 다뤘으니 손으로 검산해 봤습니다. 교재 공식은 이렇습니다.
	```javascript
토큰당 KV = 2(K와 V) × 레이어 수 × 헤드 수 × 헤드 차원 × 데이터 타입 바이트
	```
	Qwen2.5-1.5B에 넣으면 `2 × 28 × 12 × 128 × 2 = 172,032바이트 = 168.0 KiB/토큰`입니다. 그런데 기동 로그에서 역산한 값은 28.0 KiB/토큰으로 6배 차이입니다.
	원인은 GQA(Grouped Query Attention)입니다. 위 공식은 어텐션 헤드 수와 KV 헤드 수가 같은 MHA 전제입니다. Qwen2.5-1.5B는 어텐션 헤드가 12개지만 KV 헤드는 2개입니다. KV cache는 K와 V만 저장하므로 헤드 수 자리에 들어가야 할 것은 12가 아니라 2입니다.
	```javascript
2 × 28 × 2 × 128 × 2 = 28,672바이트 = 28.0 KiB/토큰
	```
	이 값으로 계산한 결과는 서로 다른 네 번의 기동 로그와 소수점 둘째 자리까지 일치했습니다.
	액면대로 썼다면 용량 산정을 6배 틀렸을 자리입니다. 요즘 모델은 대부분 GQA를 쓰므로 `config.json`의 `num_key_value_heads`를 확인하는 습관이 필요합니다.
	### 부록 C. KServe를 띄우기까지 막힌 다섯 곳
	KServe 0.20.0을 k3s에 배포해 첫 응답을 받기까지 해결한 문제를 정리했습니다. 모두 매니페스트 수정으로 해결했지만, 원인을 찾는 데 시간이 필요했습니다.
	1. `kserve.yaml`이 네임스페이스를 만들지 않습니다. `kubectl create namespace kserve`를 먼저 하지 않으면 전부 `NotFound`로 튕깁니다.
	2. 기본 모드가 Serverless입니다. Istio·Knative가 없으면 `InferenceService`가 계속 `Ready=False`입니다. `inferenceservice-config`의 `deploy`를 `RawDeployment`로 바꾸고 컨트롤러를 재시작해야 합니다.
	3. 번들 런타임과 이미지가 어긋나 있습니다. `kserve-vllmserver`는 `python`을 실행하는데 정작 그 런타임이 지정한 `vllm/vllm-openai:v0.20.0`에는 `python3`만 있습니다 → `exec: "python": executable file not found in $PATH`. `command`를 덮어써야 합니다. 같은 맥락으로 vLLM 0.20.0에는 `--disable-log-requests`가 없습니다(→ `--no-enable-log-requests`).
	4. HF 캐시를 `storageUri`로 바로 가리키면 안 됩니다. `snapshots/<hash>/` 안의 파일들은 `../../blobs/<sha>`를 가리키는 심볼릭 링크입니다. 그 폴더만 subPath로 잘라 마운트하면 링크가 끊겨 `Invalid repository ID or local directory specified: '/mnt/models'`가 납니다. 캐시 루트째 마운트하고 `--model`로 스냅샷 경로를 주면 됩니다.
	5. WSL2 k3s에서는 `runtimeClassName: nvidia`가 필수입니다. 빠지면 컨테이너에서 CUDA가 보이지 않아 `Failed to infer device type`으로 죽습니다.
	그리고 GPU가 한 장이면 롤링 업데이트가 스스로 풀리지 않습니다. 새 파드가 GPU를 기다리는데 그 GPU를 옛 파드가 쥐고 있어 교착합니다. 옛 ReplicaSet을 0으로 내려야 진행됩니다.
	### 부록 D. 재현 절차
	측정 순서는 GPU가 한 장이라 직렬입니다. 각 단계 사이에 앞 구성을 완전히 내리고 `nvidia-smi`로 VRAM 반환을 확인합니다.
	```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
	```
	**1. Ray Serve — 계층 비용 짝 ①**
	```bash
kubectl apply -f labs/rayserve-on-k8s/rayservice-qwen.yaml
# 짝: 같은 이미지에서 Ray만 뺀 구성
kubectl apply -f labs/rayserve-on-k8s/vllm-v072-direct.yaml
	```
	**2. Triton + vLLM 백엔드 — 계층 비용 짝 ②**
	```bash
docker run -d --name triton-vllm --gpus all --shm-size=8g -p 9000:9000 \
  -v /opt/llmso/triton-models:/models \
  -v "$HF_CACHE":/root/.cache/huggingface \
  nvcr.io/nvidia/tritonserver:24.12-vllm-python-py3 \
  python3 /opt/tritonserver/python/openai/openai_frontend/main.py \
    --model-repository /models --tokenizer Qwen/Qwen2.5-1.5B-Instruct \
    --openai-port 9000

# 짝: 같은 이미지에서 Triton만 뺀 구성
docker run -d --name direct-v055 --gpus all --shm-size=8g -p 9101:8000 \
  -v "$HF_CACHE":/root/.cache/huggingface \
  --entrypoint python3 nvcr.io/nvidia/tritonserver:24.12-vllm-python-py3 \
  -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-1.5B-Instruct --served-model-name qwen \
    --max-model-len 4096 --gpu-memory-utilization 0.85 --max-num-seqs 64
	```
	Triton 24.12 프론트엔드는 `stream_options`를 거부하므로 벤치마크에 `--no-stream-options`를 줍니다.
	**3. KServe — 계층 비용 짝 ③**
	```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml
kubectl -n cert-manager wait --for=condition=Available deployment --all --timeout=300s

kubectl create namespace kserve
kubectl apply --server-side -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve.yaml
kubectl -n kserve rollout restart deployment/kserve-controller-manager
kubectl apply --server-side -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve-cluster-resources.yaml

kubectl apply -f labs/kserve-on-k8s/isvc-qwen.yaml
# 짝: 같은 이미지에서 KServe만 뺀 구성
kubectl apply -f labs/kserve-on-k8s/vllm-v0200-direct.yaml
	```
	RawDeployment 전환은 `inferenceservice-config`의 `deploy` 키를 `{"defaultDeploymentMode":"RawDeployment"}`로 병합 패치합니다(→ 부록 C 2번).
	**4. 부하 — 전 구성 같은 명령**
	```bash
python3 labs/wsl2-vllm-baseline/benchmark.py \
  --base-url <각 구성의 주소> \
  --scenarios short --concurrency 1,2,4,8,16,32,64 \
  --requests-per-level 100 --warmup 1 --unique-prefix \
  --ttft-slo 0.5 --e2e-slo 10 \
  --output labs/wsl2-vllm-baseline/results/<구성>.json
	```
	**5. 표 만들기**
	```bash
python3 labs/wsl2-vllm-baseline/summarize_results.py \
  results/b-direct-v0200-seqs64.json results/c3-kserve-vllm-seqs64.json \
  --label-regex '(b-direct-v0200|c3-kserve)' --delta --metric output_tok_per_s
	```
---
## 참고 자료
- [vLLM — Optimization and Tuning](https://docs.vllm.ai/en/latest/configuration/optimization.html)
- [Ray Serve LLM](https://docs.ray.io/en/latest/serve/llm/serving-llms.html)
- [Triton Inference Server — vLLM Backend](https://github.com/triton-inference-server/vllm_backend)
- [Triton — OpenAI-Compatible Frontend](https://github.com/triton-inference-server/server/tree/main/python/openai)
- [KServe — Raw Kubernetes Deployment](https://kserve.github.io/website/latest/admin/kubernetes_deployment/)
- 실측 원본: `labs/wsl2-vllm-baseline/results/`, `labs/kserve-on-k8s/`, `labs/triton-vllm-backend/`, `labs/triton-dynamic-batching/results/`

<!-- HUMANIZE-SUMMARY
원본 글자수: 56,742자
윤문본 글자수: 54,314자
변경률: 약 8% (Notion API가 이전 리비전 전문을 제공하지 않아 수정 구간 기준으로 산정)
순감소: 2,428자

카테고리별 탐지 건수(before → after, 핵심 본문 기준):
- D-5 비유·의인화 표현(노브·가격·저울·사고판다): 18 → 0
- C-10 설명형 부제 제목 반복: 15 → 2
- H-3 메타 진입 표현: 7 → 1
- J-1 본문 굵은 강조 과다: 28 → 9
- F-4 추상 명사화·중복 표현: 11 → 4
- E-2 동일한 종결 리듬: 14 → 5

자체검증:
1. 고유명사·수치·날짜·인용 보존: 통과
2. 변경률 30% 이하: 통과
3. 기술 실험 보고서 장르 유지: 통과
4. 격식체 유지: 통과
5. 핵심 본문 S1 패턴 제거: 통과
6. 새로운 비유·과장 표현 미추가: 통과

등급: B
사유: 핵심 본문은 S1 패턴 없이 정리했으나 전체 문서가 Fast Path 5,000자 한도를 크게 넘어 절별로 처리했고, 변경률이 A 기준인 10%에 미치지 않음.

주요 변경 하이라이트:
- “엔진 노브” → “vLLM 엔진 설정”
- “계층 가격” → “서빙 구조의 오버헤드”
- “저울이 맞았다” → “비교 조건이 일치한다”
- “설정 축이 죽었다” → “설정 변경의 효과가 작았다”
- 반복된 7장·결론 → 적용 순서와 최종 측정 결과로 압축
-->
