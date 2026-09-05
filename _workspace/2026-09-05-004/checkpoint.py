# -*- coding: utf-8 -*-
from pathlib import Path
R=Path('docs');planlink='[`추가 검증 계획`](./plans/2026-09-05-week5-followup-validation.md)'
p=R/'AGENT_BRIEF.md';s=p.read_text()
s=s.replace('**② 5주차 원고·노션은 09-05 윤문 동기화 완료.**','**② 5주차 원고·노션은 09-05 구조·출처·수치 해석 개정 완료.**')
s=s.replace('**첫 작업은 측정 원본 `results/f*` 확보·대조**','**첫 작업은 측정 원본 `results/f*`·F2 집계 코드 확보·대조**')
s=s.replace('현재 `make check`는 pytest 미설치로 labs 단계 중단.','현재 `make check PY=/tmp/w5-review-venv/bin/python`은 문서·labs 106건 통과(09-05, 별도 검증 venv). 기본 Python에는 pytest가 없습니다.')
s=s.replace('**5주차(CH9·CH10)는 원고·노션 윤문 완료, 측정 원본 대조·제출표 공유 미확인(마감 09-06)**','**5주차(CH9·CH10)는 원고·노션 재구성 완료, 원본 대조·제출표 공유 미확인(마감 09-06)**')
lines=s.splitlines()
for i,l in enumerate(lines):
 if l.startswith('> ★ **09-02 개정'):
  lines[i]='> **09-05 해석 교정**: KV 예산 증가의 필요성을 시험한 실험이며 교재 반박이나 기여율 0% 증명이 아닙니다. F2는 28배 정규화 차이가 있어 역할별 집계는 잠정 근거입니다. '+planlink+'에 원본 집계 복구·KV 여유 2×2 비교·품질 평가 우선순위를 정리했습니다.'
p.write_text('\n'.join(lines)+'\n')
p=R/'STATUS.md';s=p.read_text();start=s.index('**현재 검증(');end=s.index('\n\n',start)
s=s[:start]+'**현재 검증(2026-09-05): 문서 검사와 labs 106건 통과.** `make check PY=/tmp/w5-review-venv/bin/python`으로 별도 venv에서 검증했습니다. 기본 Python에는 pytest가 없습니다. GPU 측정은 수행하지 않았습니다.'+s[end:]
start=s.index('> ⚠️ **게이트 실행 가능 여부');end=s.index('\n\n',start)
s=s[:start]+'> **검증 환경을 구분합니다.** 이번 macOS 검증은 `/tmp/w5-review-venv`의 Python 3.13·pytest 8.3.4·PyYAML 6.0.2를 사용했습니다. 임시 venv가 없으면 재생성해야 합니다. 이 통과는 실제 GPU 측정 검증을 의미하지 않습니다.'+s[end:]
s=s.replace('2026-09-05 제목·윤문 동기화 완료','2026-09-05 구조·출처·수치 해석 개정 및 노션 동기화 완료')
s=s.replace('5주차(CH9·CH10) 원고·발행본 윤문 완료','5주차(CH9·CH10) 원고·발행본 재구성 완료')
s=s.replace('아래 실험 설계는 09-02 기록입니다.','새 본문은 5개 절·표 3개·설명 그림 2개, 상세는 접기 7개입니다. 아래 실험 설계는 09-02 기록이며, 현재 해석과 후속 우선순위는 '+planlink+'를 따릅니다.')
for old,new in [('**인과**(왜 이득)를 귀속시킵니다.','**원인 후보**(왜 이득)를 대조합니다.'),('**09-02 개정 — 확인에서 반증으로.**','**09-02 당시 설계(현재는 교재 반박으로 해석하지 않음).**')]:s=s.replace(old,new)
p.write_text(s)
p=R/'NEXT_PLAN.md';s=p.read_text();start=s.index('## Priority 0');end=s.index('## Priority 5',start)
new='''## Priority 0 — 5주차 (CH9·CH10) · 마감 2026-09-06 (일) 09:00

원고·노션의 구조, 출처 구분, 수치 해석, 한국어 윤문은 09-05 개정했습니다. 추가 검증은 [2026-09-05 계획](./plans/2026-09-05-week5-followup-validation.md)을 따릅니다. 09-02 실행 체크리스트는 [당시 실험 설계](./plans/2026-08-30-week5-attribution.md)에 보존하며, 원본을 확인하기 전에 미실행으로 단정하거나 측정을 다시 시작하지 않습니다.

- [ ] [manual] **원본 확보** — `results/f*`, `f-analysis.md`, F2 트레이스·집계 코드, `run_f*.sh`의 위치 확인. 현재 체크아웃에 없음.
- [ ] [manual] **집계 대조** — F1b 3회 평균·σ, F1c 처리량 필드, F2 58·98스텝과 28배 정규화 차이 확인. 본문 역할별 커널 수치는 잠정 근거로 분리해 둠.
- [ ] [manual] **추가 실험 선택** — 새 실험 하나라면 BF16·FP8 × KV 여유·부족의 2×2 비교. 측정 조건·반복·지표·예상 그림은 추가 검증 계획에 정리. 아직 실행하지 않음.
- [ ] [manual] **원인·운영 주장의 확장** — 대역폭 원인 규명에는 같은 작업량의 프로파일링, 운영 도입 판단에는 품질 비교 필요. 현재 글은 그 주장을 확정하지 않음.
- [ ] [manual] **⑦ 링크 공유** — 사용자가 직접 제출표에 공유. 발행본 <https://app.notion.com/p/3d04c2420ac481c89ce1de666fbf9fbe>. 공유 여부 미확인.

현재 범위는 RTX 4080 Laptop 12GB·Qwen2.5-1.5B·vLLM v0.23.0입니다. 단일 GPU 밖의 MoE·TP·PP·라우터·Multi-LoRA를 현재 글에 추가할 필요는 없습니다. 실제 GPU 실험은 이 문서 개정 과정에서 실행하지 않았습니다.

'''
s=s[:start]+new+s[end:]
s=s.replace('**5주차 (CH9·CH10) — 09-05 원고·노션 윤문 완료.**','**5주차 (CH9·CH10) — 09-05 원고·노션 구조·근거 개정 완료.**')
s=s.replace('아래 실험 체크박스는 09-02 기준으로, 원본 대조 없이 완료 처리하지 않습니다.','기존 실험의 완료 여부는 원본 대조 없이 확정하지 않습니다.')
p.write_text(s)
