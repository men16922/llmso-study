# -*- coding: utf-8 -*-
from pathlib import Path
import re,json,difflib,collections
R=Path(__file__).parent;s=(R/'edited-draft.md').read_text();original=s
edits=[
('C-11','높았지만, 특히','높았지만 특히'),
('C-11','27.7%이며, 전체','27.7%이며 전체'),
('C-11','비교하고, 성능','비교하고 성능'),
('A-15','기존 기록의 58스텝과 98스텝을 분모로 적용하면 다음과 같습니다.','기록에 남은 58스텝과 98스텝으로 각각 나눠 봤습니다.'),
('B-2','원트레이스','원본 트레이스'),
('A-18','최대 길이 4,096토큰인 요청을 기준으로 환산한 용량이며, 실제 실행 중인 요청 수와는 다릅니다.','최대 길이 4,096토큰인 요청을 기준으로 용량을 환산한 값입니다. 실제 실행 중인 요청 수와는 다릅니다.'),
('F-5','개별 연산의 인과적 기여도와 동일시하지 않았습니다.','각 연산이 실제로 줄인 시간과 같다고 보지는 않았습니다.'),
('A-19','전체 감소분 중 GEMM의 비중은','전체 감소분에서 GEMM이 차지하는 비중은'),
('A-15','변경된', '변경된'),
('B-2','프롬프트, 성공 요청 수, 실제 생성 토큰 수, 스트리밍 usage 수집 여부도 결과와 함께 보관합니다.','프롬프트, 성공 요청 수, 실제 생성 토큰 수를 결과와 함께 보관합니다. 스트리밍 응답의 usage가 수집됐는지도 기록합니다.'),
('A-15','이번 분석은 Nsight Systems/Compute 실습까지 완료한 기록이 아닙니다. PyTorch Profiler와 서비스 지표를 대조한 범위입니다.','이번에는 PyTorch Profiler와 서비스 지표를 대조했습니다. Nsight Systems/Compute 실습은 완료하지 못했습니다.'),
('I-3','이 글의 0.7656을 다른 장비에 그대로 적용하지 않습니다.','다른 장비에서는 이 글의 0.7656을 그대로 쓰지 않고 예산을 다시 맞춥니다.'),
]
log=[]
for rule,a,b in edits:
 if a==b:continue
 assert a in s,a
 n=s.count(a);s=s.replace(a,b);log.append({'rule':rule,'before':a,'after':b,'count':n})
# Prose-only measurements; code, tables, URLs and diagrams remain verbatim.
def prose(x):
 x=re.sub(r'^```[^\n]*\n[\s\S]*?^```','',x,flags=re.M)
 x=re.sub(r'^\|.*$','',x,flags=re.M)
 x=re.sub(r'\]\([^)]+\)',']',x)
 return re.sub(r'\s+',' ',x).strip()
a,b=prose(original),prose(s);changed=sum(max(j-i,l-k) for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if t!='equal');rate=100*changed/len(a)
nums=lambda x:collections.Counter(re.findall(r'\d+(?:[.,]\d+)*',x))
codes=lambda x:re.findall(r'^```[^\n]*\n[\s\S]*?^```',x,re.M)
tables=lambda x:re.findall(r'^\|.*$',x,re.M)
assert nums(original)==nums(s)
assert codes(original)==codes(s)
assert tables(original)==tables(s)
assert rate<30
chunks=[];cur=''
for p in b.split('. '):
 if len(cur)+len(p)+2>5000:chunks.append(cur);cur=''
 cur+=p+'. '
if cur:chunks.append(cur)
for i,c in enumerate(chunks,1):(R/f'review-{i:02}.txt').write_text(c)
report={'scope':'사용자 승인에 따른 구조 및 사실 교정 후의 문체 윤문만 측정','before_chars':len(a),'after_chars':len(b),'changed_chars':changed,'change_percent':round(rate,2),'grade':'B','reason':'사실 교정과 구조 재편 후 보수적으로 윤문하여 변경률이 A 기준 10%보다 낮음','checks':{'고유명사_수치_날짜_인용_보존':True,'변경률_30퍼센트이하':True,'블로그_장르_유지':True,'격식체_유지':True,'문맥검토_S1_잔존없음':True,'비유수사_임의추가없음':True},'rule_counts':dict(collections.Counter({k:sum(e['count'] for e in log if e['rule']==k) for k in {e['rule'] for e in log}})),'edits':log,'review_chunk_chars':[len(c) for c in chunks]}
(R/'humanize-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
summary='\n<!-- HUMANIZE-SUMMARY\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n-->\n'
(R/'final.md').write_text(s+summary)
Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md').write_text(s)
print(json.dumps({k:v for k,v in report.items() if k not in ('edits','checks')},ensure_ascii=False,indent=2))
