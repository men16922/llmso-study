#!/usr/bin/env python3
"""3회 반복 실측 평균으로 아티클용 정적 비교 그림을 만든다."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

base = Path(__file__).resolve().parent
rows = json.loads((base / 'results/2026-09-12-extra/output-matrix-summary.json').read_text())['rows']
font = next((x for x in ['AppleGothic', 'NanumGothic', 'Noto Sans CJK KR'] if x in {f.name for f in font_manager.fontManager.ttflist}), None)
if not font:
    raise SystemExit('Korean font required: AppleGothic / NanumGothic / Noto Sans CJK KR')
plt.rcParams.update({'font.family': font, 'axes.unicode_minus': False, 'font.size': 12, 'svg.fonttype': 'path'})
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
fig.patch.set_facecolor('#ffffff')
for cap, color in [(64, '#66798c'), (256, '#1665c1')]:
    r = sorted((x for x in rows if x['max_tokens'] == cap), key=lambda x: x['concurrency'])
    for ax, key in zip(axes, ['tok_s_mean', 'ttft_p95_mean_s']):
        values = [x[key] for x in r]
        ax.plot([4,8], values, marker='o', lw=2.5, ms=7, color=color, label=f'출력 {cap}토큰')
        for c,v in zip([4,8],values):
            if key=='ttft_p95_mean_s' and c==4 and cap==64:
                continue  # 두 값 0.172/0.173이 겹치므로 아래에서 공통 근삿값 표기
            label = '≈ 0.17' if key=='ttft_p95_mean_s' and c==4 else (f'{v:.2f}' if key=='tok_s_mean' else f'{v:.3f}')
            ax.annotate(label, (c,v), xytext=(0,10), textcoords='offset points', ha='center', fontsize=11, color=color)
for ax in axes:
    ax.set_xticks([4,8],['4개','8개']); ax.set_xlim(3,9)
    ax.set_xlabel('클라이언트 동시 요청 수'); ax.grid(axis='y',alpha=.16)
    ax.spines[['top','right']].set_visible(False)
axes[0].set_title('처리량은 거의 늘지 않았습니다',loc='left',pad=18,fontweight='bold');axes[0].set_ylabel('생성 토큰/초'); axes[0].set_ylim(0,560)
axes[1].set_title('첫 응답 대기는 길어졌습니다',loc='left',pad=18,fontweight='bold');axes[1].set_ylabel('TTFT p95 (초)');axes[1].set_ylim(0,3)
axes[1].axhline(2,color='#b04738',ls='--',lw=1.2);axes[1].text(3.1,2.06,'실험의 TTFT 목표: 2초',fontsize=10,color='#b04738')
axes[0].legend(loc='lower left',frameon=False)
fig.text(.06,.025,'조건별 32건 × 3회 평균 · p95는 실행별 p95의 평균 · TinyLlama / Trainium 1대 / max_num_seqs=4',fontsize=10,color='#586575')
fig.subplots_adjust(left=.08,right=.97,bottom=.21,top=.88,wspace=.27)
out=base.parents[1] / 'articles/figures';out.mkdir(exist_ok=True)
for ext in ['png','svg']:fig.savefig(out/f'week6-throughput-ttft.{ext}',dpi=220,facecolor='white')
print('Created article figure from measured output-matrix-summary.json')
