from pathlib import Path
import re,json,collections
R=Path(__file__).parent;P=Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md')
s=P.read_text();original=s;(R/'before.md').write_text(s);edits=[]
def change(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100])
 s=s.replace(a,b);edits.append({'before':a,'after':b})
change('양자화의 두 경로와 교재 사례','무엇을 원인으로 의심했나')
change('CH9의 Qwen3-14B AWQ 사례에서는 모델 메모리를 줄여 KV 캐시를 확보한 뒤 처리량이 2.7배 늘었습니다. 같은 스터디 자료의 RTX 4070 계열·Qwen3-4B 참고 실습에는 별도의 Nsight 분석이 있습니다. 모델과 측정 조건이 다른 두 사례를 하나의 결과로 합치지는 않았습니다.\n\n','')
change('제 GPU·모델·양자화 방식은 교재와 모두 다릅니다. **내 환경에서도 KV 예산이 늘어서 빨라졌는지**를 확인하려고 했습니다. 교재 사례의 재현이나 반박을 목적으로 삼지는 않았습니다.','먼저 **캐시 공간이 늘어서 처리량이 오른 것인지** 확인했습니다. FP8은 그대로 두고 KV 예산만 줄였을 때 이득이 사라지는지를 비교했습니다.')
change('**이 조건에서는 늘어난 KV 예산을 줄여도 처리량 이득이 사라지지 않았습니다.**','**이번 실험에서는 늘어난 KV 예산을 줄여도 처리량 이득이 남았습니다.**')
change('CH10에서는 서비스 지표와 실행 타임라인, 개별 커널을 대조하면서 병목을 좁힙니다. ','')
prior=re.search(r'<details>\n<summary>지난주 결과를 함께 보면 어디까지 해석할 수 있을까</summary>[\s\S]*?</details>\n\n',s)[0]
(R/'omitted-prior-experiment.md').write_text(prior)
change(prior,'')
for line in s.splitlines():
 if line.startswith(('- *LLM Optimization in Practice*','- *Advancements in LLM Serving*')):change(line+'\n','')
change('기존 원고에는 ‘재현 편차 0.38%’라고 적혀 있습니다. 계산식이 남아 있지 않아 판단 근거로 쓰지 않았습니다. ','')
change('최종 예산도 기준보다 2.4% 컸습니다. 정확히 같은 예산으로 오해하지 않도록 본문의 ‘동결’을 ‘KV 예산 축소’로 바꿨습니다.','최종 예산도 기준보다 2.4% 컸습니다. 따라서 완전히 같은 예산에서 비교한 결과는 아닙니다.')
change('현재 검토본에는 원본 트레이스와 집계 코드가 없습니다. 역할별 수치는 상세 표에 남겨 두되 잠정 근거로만 봤습니다.','원본 트레이스와 집계 코드는 이 글에 포함하지 않았습니다. 집계 단위를 확정할 근거가 부족해 역할별 수치는 잠정 근거로만 봤습니다.')
change('현재 저장소에는 기준선 배포 매니페스트, `redeploy.sh`, `benchmark.py`가 있습니다. 반면 원고가 참조하던 `results/f*`, `f-analysis.md`, `run_f1a2.sh`, `run_f1b.sh`, `run_f1c.sh`, `run_f1d.sh`, `run_f2.sh`, `run_f5.sh`는 현재 체크아웃에 없습니다. 아래 명령은 같은 대조 실험을 새로 구성하는 예시입니다. 기존 측정값을 그대로 재생하지는 못합니다. 수치를 직접 대조하려면 원래의 요청 수·입력·반복별 결과가 필요합니다.','아래 명령은 실험에 사용한 배포 매니페스트와 `redeploy.sh`, `benchmark.py`가 준비된 환경을 전제로 합니다. 같은 대조 실험을 새로 구성하는 예시이며, 이 글의 수치를 그대로 재생하는 명령은 아닙니다. 원시 결과·트레이스·전체 실행 스크립트는 이 페이지에 포함하지 않았습니다. 수치를 직접 대조하려면 원래의 요청 수·입력·반복별 결과가 필요합니다.')
change('추가 모델의 결과를 많이 나열하기보다 이 비교를 갖추면 실제 도입을 판단하는 데 도움이 됩니다.','성능 이득과 품질 변화를 함께 봐야 실제 도입을 판단할 수 있습니다.')
change('이 글에는 기존 측정 기록을 다시 정리했습니다. 표와 화면에서 그 근거를 확인할 수 있습니다. 현재 체크아웃에는 5주차 원시 결과·트레이스·자동 실행 스크립트가 없습니다. 이번 개정에서는 남은 기록끼리 계산과 출처를 대조했습니다. GPU 실험을 새로 실행하지는 않았습니다.','이 글의 근거는 결과표와 Prometheus 원본 화면입니다. 원시 결과와 프로파일러 트레이스는 공개 자료에 포함하지 않았으며, 커널별 집계는 단위를 확정하지 못해 잠정 근거로 남겼습니다.')
change('자체 실험 기록 — 본문과 상세 영역의 결과표, Prometheus 원본 화면. 5주차 원시 결과와 트레이스는 현재 검토본에 포함되지 않았습니다.','자체 실험 기록 — 본문과 상세 영역의 결과표, Prometheus 원본 화면.')
s=re.sub(r'\n{3,}','\n\n',s)
assert not re.search(r'교재|스터디|CH9|CH10|지난주|지난 글|RTX 4070|Qwen3-4B|Qwen3-14B|체크아웃|검토본',s)
# The removed prior-experiment table/figure are intentionally out of scope.
remaining=original.replace(prior,'')
for pat in [r'^\|.*$',r'^```[^\n]*\n[\s\S]*?^```',r'!\[[^\n]*\]\([^\n]*\)']:
 assert collections.Counter(re.findall(pat,remaining,re.M))==collections.Counter(re.findall(pat,s,re.M)),pat
P.write_text(s);(R/'final.md').write_text(s);(R/'edits.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2))
print(json.dumps({'edits':len(edits),'toggles':s.count('<details>'),'tables':len(re.findall(r'^\|[^\n]*\n\| ---',s,re.M)),'images':s.count('!['),'remaining_experiment_assets_preserved':True},ensure_ascii=False))
