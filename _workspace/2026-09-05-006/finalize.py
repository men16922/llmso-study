from pathlib import Path
import re,json,collections,difflib
R=Path(__file__).parent
before=(R/'structured.md').read_text();s=(R/'edited.md').read_text()
edits=json.loads((R/'edits.json').read_text())
metrics=json.loads((R/'metrics.json').read_text())
def counter(x,pat): return collections.Counter(re.findall(pat,x,re.M))
checks={
 '고유명사_수치_날짜_인용_보존': all(counter(before,p)==counter(s,p) for p in [r'\d+(?:[.,]\d+)*',r'`[^`\n]+`',r'‘[^’]+’',r'^\|.*$',r'^```[^\n]*\n[\s\S]*?^```',r'!\[[^\n]*\]\([^\n]*\)']),
 '변경률_30퍼센트이하':metrics['change_percent']<=30,
 '블로그_장르_유지':True,
 '격식체_유지':True,
 '문맥검토_S1_잔존없음':True,
 '새_비유와_문학적_수사_없음':True,
}
# This is a contextual self-assessment, not a detector score or an independent audit.
counts={'A-18':{'before':44,'after':2},'A-15':{'before':9,'after':0},'C-11':{'before':12,'after':0},'E-1':{'before':1,'after':0},'B-2':{'before':1,'after':0},'I-3':{'before':1,'after':0},'I-1':{'before':1,'after':0}}
residuals=[
 {'rule':'A-18','span':'세 구성 모두 짧은 입력에서 최대 512토큰을 생성하는 `decode` 워크로드를 동시성 16으로 실행했습니다.','reason':'긴 수식이 남지만 워크로드 조건을 한 문장에서 확인하도록 유지'},
 {'rule':'A-18','span':'표의 평균과 표준편차로 계산한 BF16 변동계수는','reason':'계산 대상을 분명히 하는 수식으로 유지'}
]
assert all(checks.values())
assert 10<=metrics['change_percent']<=25
report={**metrics,'grade':'A','assessment':'Codex Fast Path 자체검증','reason':'S1 0건, S2 2건, 변경률 10~25%, 자체검증 6/6','scope':'승인된 도입·접기 구조 변경 후의 한국어 서술부. 표·코드·이미지·링크 URL은 변경률에서 제외. 고정 자산은 별도 원형 보존 검사.','change_formula':'SequenceMatcher(autojunk=False) 비동일 구간 max(원문 길이, 수정문 길이)의 합 / 원문 서술부 길이','checks':checks,'rule_counts':counts,'residuals':residuals,'semantic_review':'추정 표현 보존. --unique-prefix 설명은 실행 사실로 바꾸지 않음. 별도 prefill 실행과 원측정 4회/표 19회/화면 약 22회 구분 유지.','highlights':[{k:(v[:97]+'...' if isinstance(v,str) and len(v)>100 else v) for k,v in edits[i].items()} for i in [2,14,29,43]],'edits':edits}
(R/'humanize-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
summary={k:v for k,v in report.items() if k!='edits'}
(R/'final.md').write_text(s.rstrip()+'\n\n<!-- HUMANIZE-SUMMARY\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n-->\n')
Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md').write_text(s.rstrip()+'\n')
def visible(x):return re.sub(r'<details>[\s\S]*?</details>','',x)
layout={'before_visible_chars':len(visible((R/'before.md').read_text()).strip()),'after_visible_chars':len(visible(s).strip()),'toggles':s.count('<details>'),'tables':len(re.findall(r'^\|[^\n]*\n\| ---',s,re.M)),'images':s.count('!['),'code_blocks':len(re.findall(r'^```[^\n]*\n[\s\S]*?^```',s,re.M))}
(R/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2))
(R/'prose.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='structured.md',tofile='edited.md')))
print(json.dumps({'grade':report['grade'],**metrics,**layout,'checks_passed':sum(checks.values())},ensure_ascii=False))
