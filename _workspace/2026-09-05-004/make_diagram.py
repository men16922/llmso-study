# -*- coding: utf-8 -*-
from pathlib import Path
from html import escape
out=['''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="450" viewBox="0 0 820 450" role="img" aria-labelledby="title desc">
<title id="title">FP8 양자화가 처리량을 높일 수 있는 두 경로</title>
<desc id="desc">모델 메모리 감소로 KV 캐시 공간이 늘어 더 많은 요청을 수용하는 경로와, 가중치 및 활성화 정밀도와 커널이 바뀌어 토큰 처리시간이 줄어드는 경로. 두 경로는 함께 작동할 수 있다. FP8을 유지한 채 KV 예산을 줄여 첫 경로의 필요성을 확인한다.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#687789"/></marker></defs>
<rect width="820" height="450" rx="12" fill="#fafaf8"/>
<g font-family="-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif">
''']
def box(x,y,w,h,lines,color='#eef2f7',bold=False):
 out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{color}"/>')
 for i,t in enumerate(lines):out.append(f'<text x="{x+w/2}" y="{y+h/2+(i-(len(lines)-1)/2)*26+7}" text-anchor="middle" fill="#17202b" font-size="20" font-weight="{600 if bold else 400}">{escape(t)}</text>')
def arrow(path):out.append(f'<path d="{path}" fill="none" stroke="#687789" stroke-width="2" marker-end="url(#arrow)"/>')
box(290,20,240,48,['FP8 양자화'],'#dfeaf8',True)
arrow('M350 68 V86 H216 V103');arrow('M470 68 V86 H604 V103')
box(46,110,340,80,['모델 메모리 감소','→ KV 캐시 공간 증가'])
box(434,110,340,80,['가중치·활성화 정밀도','및 커널 변화'])
arrow('M216 190 V218');arrow('M604 190 V218')
box(46,225,340,55,['더 많은 요청 수용 가능'])
box(434,225,340,55,['토큰 처리시간 단축 가능'])
arrow('M216 280 V304 H350 V321');arrow('M604 280 V304 H470 V321')
box(290,328,240,48,['처리량 증가'],'#dfeaf8',True)
box(28,397,764,35,['검증 질문  ·  FP8은 유지하고 KV 예산만 줄이면 이득이 사라질까?'],'#e7f3ef')
out.append('</g></svg>')
Path('articles/figures/fig-w5-fp8-paths.svg').write_text('\n'.join(out))
