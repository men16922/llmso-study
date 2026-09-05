from pathlib import Path
import re,json,collections
R=Path(__file__).parent;P=Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md')
s=P.read_text();(R/'before.md').write_text(s)
folds=dict(re.findall(r'<details>\n<summary>(.*?)</summary>\n([\s\S]*?)</details>',s))
assert len(folds)==12
def fold(title,body):return '<details>\n<summary>'+title+'</summary>\n\n'+body.strip()+'\n\n</details>\n\n'
def take(title):return folds.pop(title)
out='''# FP8 양자화로 처리량이 늘어난 이유

**FP8 양자화로 처리량이 늘었습니다. 늘어난 KV Cache 덕분일까요?**

양자화로 모델이 차지하는 메모리를 줄이면 KV Cache에 쓸 공간이 늘어납니다. 동시에 가중치를 읽고 계산하는 경로도 달라집니다. 이번에는 FP8을 유지한 채 캐시 공간만 줄여, 어느 변화가 처리량 이득에 영향을 줬는지 확인했습니다.

> **핵심 결론: 이번 환경에서 FP8의 처리량 향상은 KV Cache 용량 증가만으로 설명되지 않았습니다.**

## 결과 한눈에 보기

| 구성 | BF16 대비 생성 처리량 | ITL p50 | 결과의 의미 |
| --- | --- | --- | --- |
| BF16 기준 | 기준값 | 9.7ms | 비교 기준 |
| FP8 기본 | **+33.7%** | 7.3ms | 양자화 후 처리량 증가 |
| FP8 · KV 예산 축소 | **+33.8%** | 7.3ms | **늘어난 캐시 공간을 줄여도 이득 유지** |

*RTX 4080 Laptop 12GB·Qwen2.5-1.5B·vLLM v0.23.0. 같은 decode 부하, 동시성 16, 구성별 3회 측정입니다. 예산 축소 구성의 KV 수용량은 BF16 기준보다 2.4% 컸습니다.*

'''
out+=fold('용어 정리 — 처리량·ITL·TTFT와 KV 예산','''이 글에서는 **얼마나 많이 생성했는지**, **얼마나 빨리 토큰이 이어지는지**, **첫 토큰까지 얼마나 기다렸는지**를 구분합니다.

| 용어 | 이 글에서의 의미 |
| --- | --- |
| **BF16 / FP8** | 각각 16비트·8비트 부동소수점 형식. 이번에는 같은 모델에 FP8 양자화를 적용했습니다. |
| **KV Cache / KV 예산** | 이전 토큰의 Attention Key·Value를 저장하는 캐시 / 그 캐시에 할당한 용량. 캐시의 정밀도를 바꾸는 실험은 아닙니다. |
| **생성 처리량 (tok/s, TPS)** | 모든 요청에서 생성한 출력 토큰을 합산한 초당 토큰 수. 요청 하나의 생성 속도와 구분합니다. |
| **ITL** | Inter-Token Latency. 응답이 시작된 뒤 토큰이 이어지는 시간 간격. 짧을수록 토큰이 빠르게 이어집니다. |
| **TTFT** | Time To First Token. 요청을 보낸 뒤 첫 토큰을 받을 때까지의 시간. ITL과 별도로 봅니다. |
| **Prefill / Decode** | 입력 프롬프트를 처리하는 단계 / 이후 출력 토큰을 순차적으로 생성하는 단계. |
| **GEMM** | 모델의 선형 계층에서 수행하는 행렬 곱셈. 프로파일링에서 살핀 연산입니다. |

표의 p50은 중앙값입니다. 처리량이 높아졌다는 사실만으로 TTFT가 짧아졌다고 판단하지 않습니다. 이 글의 핵심 비교에서는 생성 처리량과 ITL을 보고, KV 예산이 부족한 별도 prefill 실험에서는 TTFT도 확인합니다.''')
out+='''## 1. KV Cache를 줄여도 처리량 이득은 남았다

**FP8은 유지하고 KV 예산만 줄였습니다. 그래도 처리량은 BF16보다 높았습니다.**

'''
reason=take('무엇을 원인으로 의심했나')
reason=reason.replace('양자화를 켜면 모델이 차지하는 메모리가 줄어듭니다. 남는 공간에 더 많은 요청을 담을 수 있고 가중치를 읽고 계산하는 경로도 바뀔 수 있습니다.\n\n','')
reason=re.sub(r'\*\*KV 예산\*\*은[^\n]+\n\n','',reason)
out+=fold('가설 — 왜 KV Cache 용량을 줄였나',reason)
out+=fold('대조 실험 — 세 구성의 조건과 반복 측정 결과',take('세 구성의 대조 실험과 결과'))
out+=fold('실험 환경·전체 결과·기동 로그',take('실험 환경과 세 구성의 전체 결과'))
out+='''## 2. 동시 요청 수는 같고, 토큰 간격은 짧아졌다

**실행 요청 수가 같아도 처리량은 늘었습니다. ITL도 짧아져, 토큰을 처리하는 시간이 줄었다는 해석을 뒷받침했습니다.**

'''
measurement=take('처리량·요청 수 실측 화면과 커널 시간')
service,profiler=measurement.split('커널 시간은 PyTorch Profiler로 살펴봤습니다.',1)
service='ITL p50은 **9.7ms→7.3ms(−24.7%)**였습니다.\n\n'+service.strip()
out+=fold('실측 근거 — Prometheus 처리량·동시 요청 수와 ITL',service)
out+=fold('Prometheus 측정 조건과 A·B·C 구간 구분',take('Prometheus의 A·B·C 구간과 원본 화면'))
out+='''## 3. 커널 시간은 줄었지만, 세부 원인은 더 확인해야 한다

**기록된 스텝 수로 환산한 GPU 커널 시간 합계도 약 26.7% 줄었습니다. 다만 이 값을 실제 스텝 지연시간으로 읽거나, 이득 전부를 GEMM에 돌릴 수는 없습니다.**

'''
out+=fold('프로파일링 결과 — 스텝 수를 맞춰 비교한 커널 시간','커널 시간은 PyTorch Profiler로 살펴봤습니다.'+profiler)
out+=fold('집계 검증 — 단위 차이와 역할별 커널 분석',take('프로파일러 집계의 단위와 확인 범위'))
out+='''## 4. KV Cache가 부족해지면 처리량과 TTFT가 나빠졌다

**캐시 용량이 중요하지 않다는 뜻은 아닙니다. 긴 입력을 처리하는 prefill에서는 KV 예산을 더 낮추자 선점이 발생하고 TTFT가 늘었습니다.**

'''
low=take('KV 사용률·선점 실측 화면과 성능 변화').replace('KV 캐시 용량이 중요하지 않은 것은 아닙니다.\n\n','')
out+=fold('실측 근거 — KV 사용률·선점·TTFT의 변화',low)
out+=fold('KV 예산별 전체 결과와 부족 구간',take('KV 예산 스윕과 부족 구간'))
out+=fold('다른 워크로드·동시성에서는 얼마나 달라졌나',take('워크로드와 동시성에 따른 차이'))
out+='''## 5. 이번 실험에서 확인한 것

**FP8의 처리량 이득은 KV Cache 용량을 BF16 수준에 가깝게 줄여도 남았습니다. 같은 동시 요청 수에서 처리량이 늘고 ITL이 줄어, 캐시 용량 증가만으로는 설명되지 않는 처리시간 단축이 있었습니다.**

가중치를 읽는 비용과 FP8 계산 경로 중 어느 쪽이 얼마나 기여했는지는 아직 분리하지 못했습니다. 운영에 적용하려면 응답 품질도 함께 확인해야 합니다.

'''
out+=fold('운영에 적용할 때 확인할 조건',take('운영에 적용할 때 확인할 조건'))
out+=fold('재현 조건과 후속 검증 절차',take('재현에 필요한 자료와 실행 순서'))
out+='''## 측정 근거와 한계

이 글의 근거는 결과표와 Prometheus 원본 화면입니다. 원시 결과와 프로파일러 트레이스는 공개 자료에 포함하지 않았으며, 커널별 집계는 단위를 확정하지 못해 잠정 근거로 남겼습니다.

'''
out+=fold('참고 자료',take('참고 자료'))
assert not folds,folds.keys()
out=re.sub(r'\n{3,}','\n\n',out)
for pat in [r'^\|.*$',r'^```[^\n]*\n[\s\S]*?^```',r'!\[[^\n]*\]\([^\n]*\)']:
 missing=collections.Counter(re.findall(pat,s,re.M))-collections.Counter(re.findall(pat,out,re.M));assert not missing,missing
P.write_text(out);(R/'final.md').write_text(out)
visible=lambda x:re.sub(r'<details>[\s\S]*?</details>','',x)
v={'before_visible_chars':len(visible(s)),'after_visible_chars':len(visible(out)),'tables':len(re.findall(r'^\|[^\n]*\n\| ---',out,re.M)),'images':out.count('!['),'toggles':out.count('<details>'),'original_tables_code_images_preserved':True}
(R/'verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2));print(json.dumps(v,ensure_ascii=False))
