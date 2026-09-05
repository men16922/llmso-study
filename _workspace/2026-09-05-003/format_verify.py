from pathlib import Path
import re, json, collections, difflib
R=Path(__file__).parent
original=(R/'02_corrected_input.md').read_text()
edited=(R/'edited-unformatted.md').read_text()
title=edited.splitlines()[0][2:]

# 기존 탭은 노션의 블록 계층 들여쓰기다. 먼저 풀고 토글 범위에 맞게 다시 넣는다.
lines=[l.lstrip('\t') for l in edited.splitlines()]
canonical=[]; stack=[]; in_code=False; callout=False
for line in lines:
    heading=re.match(r'^(#{1,3}) (.*)',line) if not in_code else None
    if heading:
        level=len(heading[1])
        while stack and level <= stack[-1]: stack.pop()
        is_toggle='{toggle="true"}' in line
        canonical.append('\t'*len(stack)+line)
        if is_toggle: stack.append(level)
        continue
    # 가로줄은 절 구분자이며 앞선 토글의 바깥에 둔다.
    if not in_code and line=='---': stack=[]
    depth=len(stack)+(1 if callout and not line.startswith('</callout>') else 0)
    canonical.append('\t'*depth+line if line else '')
    if line.startswith('<callout'):callout=True
    if line.startswith('</callout>'):callout=False
    if line.startswith('```'):in_code=not in_code
canonical='\n'.join(canonical).strip()+'\n'
assert not in_code
(R/'notion-ready.md').write_text(canonical.split('\n',1)[1].lstrip())

# 로컬 문서는 일반 Markdown 표와 details를 사용한다.
local=[];stack=[];in_code=False;callout=False
for line in lines:
    heading=re.match(r'^(#{1,3}) (.*)',line) if not in_code else None
    if heading:
        level=len(heading[1])
        while stack and level<=stack[-1]:local.extend(['','</details>','']);stack.pop()
        if '{toggle="true"}' in line:
            label=heading[2].replace(' {toggle="true"}','')
            # summary에서는 Markdown 대신 평문을 쓴다.
            local.extend(['<details>', '<summary>'+label.replace('`','')+'</summary>', ''])
            stack.append(level)
        else:local.extend(['',line,''])
        continue
    if not in_code and line=='---':
        while stack:local.extend(['','</details>','']);stack.pop()
    if line.startswith('<callout'):
        callout=True;continue
    if line.startswith('</callout>'):
        callout=False;local.append('');continue
    if '<table_of_contents' in line:
        local.append('<!-- TOC -->');continue
    local.append(('> '+line) if callout else line)
    if line.startswith('```'):in_code=not in_code
while stack:local.extend(['','</details>','']);stack.pop()
local='\n'.join(local)
def table(m):
    rows=[]
    for row in re.findall(r'<tr[^>]*>([\s\S]*?)</tr>',m[0]):
        cells=re.findall(r'<td[^>]*>([\s\S]*?)</td>',row)
        rows.append([c.strip().replace('|',r'\|') for c in cells])
    assert rows and len({len(r) for r in rows})==1
    result=['| '+' | '.join(rows[0])+' |', '| '+' | '.join(['---']*len(rows[0]))+' |']
    result+=['| '+' | '.join(row)+' |' for row in rows[1:]]
    return '\n\n'+'\n'.join(result)+'\n\n'
local=re.sub(r'<table\b[\s\S]*?</table>',table,local)
def image(m):
    name=Path(m[2].split('?')[0]).name
    folder='figures' if name.endswith('.svg') else 'screenshots'
    path=Path('articles')/folder/name
    assert path.is_file(),path
    return '!['+m[1]+'](./'+folder+'/'+name+')'
local=re.sub(r'!\[([^\]]*)\]\(([^\n]+)\)',image,local)
old_link='https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234'
previous=Path('articles/켜면 이득인 최적화는 없다.md')
assert previous.exists()
from urllib.parse import quote
local=local.replace(old_link,'./'+quote(previous.name))
local=local.replace('<!-- TOC -->','')
# 코드·표 안을 제외하고 블록 경계에 빈 줄을 둔다. 원문의 한 줄은 한 문단이다.
spaced=[]; in_code=False
for line in local.splitlines():
    if not in_code and line and spaced and spaced[-1]:
        prev=spaced[-1]
        same_table=line.startswith('|') and prev.startswith('|')
        same_quote=line.startswith('>') and prev.startswith('>')
        same_list=bool(re.match(r'^- ',line) and re.match(r'^- ',prev))
        same_html=line.startswith('<summary>') and prev=='<details>'
        if not (same_table or same_quote or same_list or same_html):spaced.append('')
    spaced.append(line)
    if line.startswith('```'):in_code=not in_code
local='\n'.join(spaced)
local=local.replace('> **실험에서 확인한 세 가지**\n> -', '> **실험에서 확인한 세 가지**\n>\n> -')
local=re.sub(r'\n{3,}','\n\n',local).strip()+'\n'
(R/'local-ready.md').write_text(local)

def norm_body(x):
    x=re.sub(r'!\[([^\]]*)\]\([^\n]*\)',r'\1',x)
    x=re.sub(r'\[([^\]]*)\]\([^\n]*?\)',r'\1',x)
    x=re.sub(r'<[^>]+>|\{toggle="true"\}',' ',x)
    x=re.sub(r'^[\t ]*[#]+ .*$', '',x,flags=re.M)
    x=re.sub(r'[`*|>#]','',x)
    return re.sub(r'\s+',' ',x).strip()
def num(x):return collections.Counter(re.findall(r'(?<![A-Za-z])[-+−±]?\d[\d,.]*(?:%|x|배)?',norm_body(x)))
def codes(x):
    out=[];chunk=None
    for line in x.splitlines():
        line=line.lstrip('\t')
        if line.startswith('```'):
            if chunk is None:chunk=[]
            else:out.append('\n'.join(chunk));chunk=None
        elif chunk is not None:chunk.append(line)
    assert chunk is None
    return out
assert codes(original)==codes(canonical)==codes(local),'code changed'
# 수치 표 15개는 셀 값 순서를 모두 대조한다.
cells=lambda x:[v.strip() for v in re.findall(r'<td[^>]*>([\s\S]*?)</td>',x)]
assert [v.replace('팔','구성').replace('커널·대역폭 쪽에서 벌었음','커널 실행·가중치 읽기 시간이 줄었음') for v in cells(original)]==cells(canonical)
assert num(original)==num(canonical), {'removed':num(original)-num(canonical),'added':num(canonical)-num(original)}
quotes=lambda x:re.findall(r'"([^"\n]+)"',re.sub(r'<[^>]+>|!\[[^\]]*\]\([^\n]+\)','',x))
assert quotes(original)==quotes(canonical),'quoted words changed'
assert re.findall(r'`([^`\n]+)`',original)==re.findall(r'`([^`\n]+)`',canonical),'inline code changed'
plain_before=norm_body(original);plain_after=norm_body(canonical)
matcher=difflib.SequenceMatcher(None,plain_before,plain_after,autojunk=False)
changed=sum(max(j-i,l-k) for op,i,j,k,l in matcher.get_opcodes() if op!='equal')
rate=100*changed/max(len(plain_before),len(plain_after))
assert rate<=30
print(json.dumps({'title':title,'body_chars_before':len(plain_before),'body_chars_after':len(plain_after),'changed_chars':changed,'change_percent':round(rate,2),'numeric_tokens':sum(num(original).values()),'tables':len(re.findall('<table ',original)),'table_cells':len(cells(original)),'code_blocks':len(codes(original)),'images':local.count('!['),'toggles':local.count('<details>'),'all_protected_checks_passed':True},ensure_ascii=False,indent=2))
(R/'verification.json').write_text(json.dumps({'title':title,'body_chars_before':len(plain_before),'body_chars_after':len(plain_after),'changed_chars':changed,'change_percent':round(rate,2),'numeric_tokens':sum(num(original).values()),'table_cells':len(cells(original)),'code_blocks':len(codes(original)),'images':local.count('!['),'toggles':local.count('<details>'),'all_protected_checks_passed':True},ensure_ascii=False,indent=2))

# 문단 경계로 5,000자 이하 검토 단위를 남긴다(기술 블록은 별도 보존 검사).
prose=re.sub(r'<table\b[\s\S]*?</table>|^[\t ]*```[^\n]*\n[\s\S]*?^[\t ]*```[^\n]*$', '', canonical, flags=re.M)
prose=re.sub(r'!\[([^\]]*)\]\([^\n]+\)',r'[그림: \1]',prose)
chunks=[];chunk=''
for p in prose.split('\n\n'):
    if len(chunk)+len(p)+2>5000:chunks.append(chunk);chunk=''
    chunk+=p+'\n\n'
if chunk:chunks.append(chunk)
assert all(len(c)<=5000 for c in chunks)
for i,c in enumerate(chunks,1):(R/f'review-section-{i:02}.txt').write_text(c)
print('review_chunks',len(chunks),[len(c) for c in chunks])
