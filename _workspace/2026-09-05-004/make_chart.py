# -*- coding: utf-8 -*-
from pathlib import Path
from html import escape
rows=[('BF16 기본',1689.3,3.3,'59.50x','#6b7280'),('FP8 기본',2258.8,6.5,'70.20x','#2a78d6'),('FP8 · KV 예산 축소',2261.0,12.5,'60.95x','#168466')]
out=['''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="450" viewBox="0 0 820 450" role="img" aria-labelledby="title desc">
<title id="title">KV 예산을 줄여도 FP8의 처리량 이득은 남았다</title>
<desc id="desc">decode 동시성 16, 각 구성 3회 평균과 표준편차. BF16 1689.3 ±3.3, FP8 2258.8 ±6.5, FP8 KV 예산 축소 2261.0 ±12.5 tok/s. 예산 축소 구성은 기준보다 KV 수용량 지표가 2.4퍼센트 크다. 기존 원고의 집계 수치를 시각화했으며 원시 결과를 재집계한 것은 아니다.</desc>
<rect width="820" height="450" rx="12" fill="#fafaf8"/>
<g font-family="-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif">
<text x="28" y="42" font-size="25" font-weight="700" fill="#17202b">KV 예산을 줄여도 FP8의 이득은 남았다</text>
<text x="28" y="73" font-size="17" fill="#56616f">decode · 동시성 16 · 각 구성 3회 평균 · 오차 막대 ±1σ</text>''']
x0=240; width=450; scale=width/2500
for t in [0,500,1000,1500,2000,2500]:
 x=x0+t*scale
 out.append(f'<line x1="{x}" y1="100" x2="{x}" y2="319" stroke="#e0e4e8"/><text x="{x}" y="345" text-anchor="middle" font-size="15" fill="#56616f">{t:,}</text>')
for i,(label,mean,sd,kv,color) in enumerate(rows):
 y=114+i*74
 out.append(f'<text x="28" y="{y+20}" font-size="20" font-weight="600" fill="#17202b">{escape(label)}</text>')
 out.append(f'<text x="28" y="{y+43}" font-size="15" fill="#56616f">KV 수용량 {kv}</text>')
 end=x0+mean*scale;lo=x0+(mean-sd)*scale;hi=x0+(mean+sd)*scale
 out.append(f'<rect x="{x0}" y="{y}" width="{mean*scale:.3f}" height="45" rx="4" fill="{color}"/>')
 out.append(f'<path d="M{lo},{y+13} V{y+32} M{hi},{y+13} V{y+32} M{lo},{y+22.5} H{hi}" stroke="#17202b" stroke-width="2" fill="none"/>')
 out.append(f'<text x="{end+15}" y="{y+29}" font-size="21" font-weight="700" fill="#17202b">{mean:,.1f}</text>')
out+=['''<text x="690" y="374" text-anchor="end" font-size="16" fill="#56616f">생성 처리량 (tok/s)</text>
<rect x="28" y="392" width="764" height="38" rx="6" fill="#e7f3ef"/>
<text x="44" y="417" font-size="17" fill="#12614c">BF16 대비 +33.7% → 예산 축소 뒤에도 +33.8% · 예산 오차 +2.4%</text>
</g></svg>''']
p=Path('articles/figures/fig-w5-fp8-ablation.svg');p.write_text('\n'.join(out));print(p)
