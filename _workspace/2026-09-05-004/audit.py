# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import unquote
import re,json,difflib,collections,xml.etree.ElementTree as ET,hashlib
R=Path(__file__).parent;P=Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md');s=P.read_text();old=(R/'before.md').read_text()
def visible(x):return re.sub(r'<details>[\s\S]*?</details>','',x)
def ntables(x):return len(re.findall(r'^\|[^\n]+\n\|[\s:|\-]+\n',x,re.M))
def normal(x):
 x=re.sub(r'!\[[^\]]*\]\([^\n]+\)','IMAGE',x)
 x=re.sub(r'\\([~_*\[\]{}|^])',r'\1',x)
 return re.sub(r'\s+','',x)
checks={}
checks['five_main_sections']=len(re.findall(r'^## [1-5]\. ',s,re.M))==5
checks['three_visible_tables']=ntables(visible(s))==3
checks['seven_independent_toggles']=s.count('<details>')==s.count('</details>')==7 and not re.search(r'<details>(?:(?!</details>)[\s\S])*<details>',s)
checks['six_images']=len(re.findall(r'!\[',s))==6
checks['image_files_exist']=all((P.parent/unquote(u)).exists() for u in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',s))
checks['no_signed_urls_in_local']='X-Amz-' not in s
checks['no_member_source_links_in_public']=all(t not in (R/'notion-ready.md').read_text() for t in ['study/Ch9.md','study/Ch10.md','gasidaseo','](./','](../'])
# Arithmetic and transformed units independently recomputed from preserved source values.
calc={'fp8_gain_pct':(2258.8/1689.3-1)*100,'reduced_budget_gain_pct':(2261/1689.3-1)*100,'budget_residual_pct':(60.95/59.5-1)*100,'itl_reduction_pct':(1-.0073/.0097)*100,'bf16_kernel_ms_per_step':503.1/58,'fp8_kernel_ms_per_step':622.8/98,'kernel_reduction_pct':(1-(622.8/98)/(503.1/58))*100,'prefill_reduction_pct':(1-8306/12686)*100,'ttft_ratio':7.679/4.448,'gemm_share_pct':(279.54-202.21)/(309.77-226.96)*100,'bf16_cv_pct':3.3/1689.3*100,'prometheus_gain_pct':(2269.3/1703.6-1)*100}
expected={'fp8_gain_pct':33.7,'reduced_budget_gain_pct':33.8,'budget_residual_pct':2.4,'itl_reduction_pct':24.7,'kernel_reduction_pct':26.7,'prefill_reduction_pct':34.5,'gemm_share_pct':93.4,'prometheus_gain_pct':33.2}
checks['rounded_percentages']=all(round(calc[k],1)==v for k,v in expected.items())
checks['kernel_units']=round(calc['bf16_kernel_ms_per_step'],2)==8.67 and round(calc['fp8_kernel_ms_per_step'],2)==6.36
for file in ['fig-w5-fp8-ablation.svg','fig-w5-fp8-paths.svg']:
 root=ET.parse(P.parent/'figures'/file).getroot();checks[file+'_valid_svg']=root.tag.endswith('svg') and root.find('{http://www.w3.org/2000/svg}title') is not None
checks['explicit_raw_data_limit']='5주차 원시 결과·트레이스·자동 실행 스크립트가 없어' in s
checks['explicit_quality_limit']='응답 품질은 평가하지 않았고' in s
checks['explicit_profiling_limit']='집계 코드가 현재 검토본에 없어' in s
checks['no_full_step_label_for_309us']='BF16 (스텝당)' not in s
checks['no_exact_zero_attribution']='기여한 몫은 0%' not in s and '예산의 기여분은 0%' not in s
checks['no_single_book_experiment_conflation']='양자화 뒤 처리량은 2.7배가 됐지만 Nsight' not in s
checks['followup_experiments_documented']=Path('docs/plans/2026-09-05-week5-followup-validation.md').exists()
if (R/'notion-after.md').exists():
 a=(R/'notion-ready.md').read_text();b=(R/'notion-after.md').read_text();checks['notion_body_matches']=normal(a)==normal(b)
 # Every table cell and code block compares independently of narrative normalization.
 cells=lambda x:re.findall(r'<td>(.*?)</td>',x,re.S)
 code=lambda x:[re.sub(r'^\t','',v,flags=re.M) for v in re.findall(r'```[^\n]*\n(.*?)```',x,re.S)]
 checks['notion_table_cells_match']=cells(a)==cells(b)
 checks['notion_code_blocks_match']=code(a)==code(b)
checks['humanize_protected_content']=all(json.loads((R/'humanize-report.json').read_text())['checks'].values())
report={'checks':checks,'calculations':calc,'structure':{'before_visible_tables':ntables(visible(old)),'after_visible_tables':ntables(visible(s)),'after_total_tables':ntables(s),'before_visible_chars':len(visible(old)),'after_visible_chars':len(visible(s))},'article_sha256':hashlib.sha256(s.encode()).hexdigest()}
report['verification_scope']='GPU 실험 재실행을 제외한 기존 기록의 산술·출처·문서 구조·발행 본문 일치 검증'
(R/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2));assert all(checks.values()),[k for k,v in checks.items() if not v]
