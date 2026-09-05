from pathlib import Path
import re, json, collections
R=Path(__file__).parent
P=Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md')
s=P.read_text(); (R/'before.md').write_text(s)
parts=re.split(r'^## ',s,flags=re.M)
main=parts[1:6]
appendix=parts[6]
folds=re.findall(r'<details>\n<summary>(.*?)</summary>\n([\s\S]*?)</details>',appendix)
assert len(folds)==7
intro='''# FP8 양자화로 처리량이 늘어난 이유

**처리량이 늘었다면, 답변도 빨라진 걸까요?**

한꺼번에 더 많은 요청을 처리해도 초당 생성하는 토큰 수는 늘어납니다. 하지만 사용자가 자신의 답변을 더 빨리 받는지는 다른 문제입니다.

FP8 양자화를 적용했을 때도 처리량이 늘었습니다. 그런데 측정 화면에서 눈에 들어온 건 다른 숫자였습니다. **동시에 처리하는 요청은 여전히 16개였습니다.**

요청 수는 같은데, 초당 나오는 토큰은 더 많아졌습니다. 어디서 시간이 줄어든 걸까요?

'''
def fold(title,body):
 return '<details>\n<summary>'+title+'</summary>\n\n'+body.strip()+'\n\n</details>\n\n'
cores=[
'처리량이 올랐다는 사실만으로는 어느 변화가 효과를 냈는지 알기 어렵습니다.',
'이 조건에서는 늘어난 KV 예산을 줄여도 처리량 이득이 사라지지 않았습니다.',
'ITL p50은 9.7ms에서 7.3ms로 **24.7%** 줄었습니다. 처리량만 오른 것이 아니라 사용자에게 토큰이 도착하는 간격도 짧아졌습니다.',
'긴 입력을 처리하는 `prefill` 부하에서 예산을 더 낮추자 처리량이 떨어졌습니다.',
'**이번 환경에서는 KV 예산을 BF16 수준에 가깝게 줄여도 FP8의 처리량 이득이 남았고, 토큰 간격도 짧아졌습니다.**'
]
titles=['양자화의 두 경로와 교재 사례','세 구성의 대조 실험과 결과','처리량·요청 수 실측 화면과 커널 시간','KV 사용률·선점 실측 화면과 성능 변화','운영에 적용할 때 확인할 조건']
place={0:[],1:[0],2:[3,4],3:[1,2],4:[5,6]}
out=intro
for i,part in enumerate(main):
 heading,body=part.split('\n',1)
 body=body.strip().removesuffix('---').strip()
 assert cores[i] in body
 body=body.replace(cores[i],'',1).strip()
 if i==4:
  # The approved structure uses prose for these three related checks.
  body=body.replace('이번 실험에서 남긴 확인 순서는 세 가지입니다.','')
  body=re.sub(r'^\d\. ', '', body, flags=re.M)
  body=body.replace('\n2. ', '\n\n').replace('\n3. ', '\n\n')
  body=body.replace('기록합니다.\n**원인','기록합니다.\n\n**원인').replace('확인합니다.\n**지표','확인합니다.\n\n**지표')
 core=cores[i].replace('**','')
 out+='## '+heading+'\n\n**'+core+'**\n\n'+fold(titles[i],body)
 for j in place[i]:
  title,b=folds[j]
  out+=fold(title[3:],b)
note=appendix.split('<details>')[0].split('\n',1)[1].strip()
out+='## 기록의 범위와 출처\n\n'+note+'\n\n'+fold('참고 자료',parts[7].split('\n',1)[1])
# Repair references after moving supporting material beside each conclusion.
out=out.replace('부록에 보존하고','상세 표에 보존하고').replace('본문과 부록의 결과표','본문과 상세 영역의 결과표')
out=out.replace('뒤의 3분 대시보드 실험','앞의 3분 대시보드 실험')
out=re.sub(r'\n{3,}','\n\n',out)
(R/'structured.md').write_text(out)
# Tables, executable examples and evidence images must survive the layout change.
def blocks(x,pattern):return collections.Counter(re.findall(pattern,x,re.M))
for pattern in [r'^\|.*$',r'^```[^\n]*\n[\s\S]*?^```',r'!\[[^\n]*\]\([^\n]*\)']:
 assert blocks(s,pattern)==blocks(out,pattern),pattern
print(json.dumps({'chars':len(out),'toggles':out.count('<details>'),'tables_preserved':True,'code_preserved':True,'images_preserved':True},ensure_ascii=False))
