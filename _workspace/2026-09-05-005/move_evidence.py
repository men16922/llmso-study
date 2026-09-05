# -*- coding: utf-8 -*-
from pathlib import Path
import re,json
P=Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md');s=P.read_text();edits=[]
def replace(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b);edits.append({'old':a,'new':b})
through=re.search(r'!\[[^\n]*\]\(\./screenshots/proof-w5-08-dash-throughput.png\)\n\n\*[^\n]+\*',s)[0]
preempt=re.search(r'!\[[^\n]*\]\(\./screenshots/proof-w5-07-dash-kv-preempt.png\)\n\n\*[^\n]+\*',s)[0]
replace(through,'')
replace(preempt,'')
anchor='그다음 PyTorch Profiler로 커널 시간을 살펴봤습니다.'
proof='''아래는 그때의 Prometheus 원본 화면입니다. 위 그래프는 생성 처리량, 아래 그래프는 실행 중인 요청 수입니다. 아래쪽 높이는 같은데 위쪽 높이만 달라진 두 구간을 비교하면 차이가 드러납니다.

![같은 decode 부하에서 BF16과 FP8의 생성 처리량 및 동시 실행 요청 수를 비교한 Prometheus 원본 화면](./screenshots/proof-w5-08-dash-throughput.png)

*9월 2일 UTC 기준, 21:01에 시작한 A는 BF16이고 21:05의 B는 FP8입니다. 실행 요청 수는 둘 다 16개지만 생성 처리량은 약 1,700→2,270 tok/s로 올라갑니다. 오른쪽 21:09의 C는 다른 prefill 부하라 이 처리량 비교에서 제외합니다.*

'''
replace(anchor,proof+anchor)
anchor='KV 사용률만으로는 이런 상태를 구분하기 어려웠습니다.'
proof='''같은 저예산 BF16 구성에 prefill 부하를 3분간 가한 별도 실행에서도 선점이 발생했습니다. 아래 원본 화면에서는 21:09에 시작한 C 구간의 KV 사용률이 높아지고, 누적 선점 곡선도 계단 모양으로 올라갑니다.

![KV 예산을 줄인 C 구간에서 KV 사용률과 누적 선점이 증가한 Prometheus 원본 화면](./screenshots/proof-w5-07-dash-kv-preempt.png)

*위는 KV 사용률, 아래는 누적 선점입니다. C는 BF16·util 0.33·prefill 동시성 64입니다. 앞 표의 선점 4회와는 다른 실행이며, 이 화면은 낮은 예산에서 선점이 발생한 현상을 뒷받침합니다.*

'''
replace(anchor,proof+anchor)
replace('세 화면은 모두 9월 2일 20:48~21:13 UTC를 표시합니다. 시작 시각 **21:01은 A**, **21:05는 B**, **21:09는 C**입니다. 사이의 공백은 서버를 재배포한 구간입니다.','본문의 처리량·선점 화면과 아래 보충 화면은 모두 9월 2일 20:48~21:13 UTC를 표시합니다. 시작 시각 **21:01은 A**, **21:05는 B**, **21:09는 C**입니다. 사이의 공백은 서버를 재배포한 구간입니다.\n\n**선점 횟수의 기록 차이:** 위 요약표의 C 구간에는 19회가 남아 있지만, 원본 화면의 마지막 누적값은 약 22회로 읽힙니다. 집계 시점 차이인지 원시 데이터로 확인하지 못했으므로 19회를 화면의 최종값으로 제시하지 않습니다. 본문에서는 선점이 발생한 구간을 확인하는 근거로 사용합니다.')
s=re.sub(r'\n{3,}','\n\n',s)
P.write_text(s)
Path('_workspace/2026-09-05-005/edits.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2))
print('moved two screenshots, corrected preemption caption, total images',s.count('!['))
