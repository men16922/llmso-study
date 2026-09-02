#!/usr/bin/env python3
"""글을 장 순서대로 조립한다.

측정이 순서대로 끝나지 않아서 장을 쓴 순서와 실을 순서가 다르다.
`## N.` 헤딩을 기준으로 쪼갠 뒤 번호순으로 다시 붙이고, 부록은 맨 뒤에 둔다.
"""
import io, os, re, sys

ART = 'articles/처리량이 올랐다면 무엇이 빨라진 것인가.md'
SEC = '_workspace/2026-09-02-001/sections'

text = io.open(ART, encoding='utf-8').read()
extra = ''.join(io.open(os.path.join(SEC, f), encoding='utf-8').read()
                for f in sorted(os.listdir(SEC)) if f.endswith('.md'))

# 헤딩 앞에서 쪼갠다. 첫 조각은 제목·요약·목차라 항상 맨 앞에 남는다.
parts = re.split(r'(?m)^(?=## )', text + '\n' + extra)
head, chapters = parts[0], parts[1:]

def key(chunk):
    m = re.match(r'## (\d+)\.', chunk)
    if m:
        return (0, int(m.group(1)))
    return (1, 0) if chunk.startswith('## 부록') else (2, 0)

# "결과 한눈에 보기"는 머리말의 일부라 head로 되돌린다.
lead = [c for c in chapters if c.startswith('## 결과 한눈에 보기') or c.startswith('## 목차')]
body = [c for c in chapters if c not in lead]

out = head + ''.join(lead) + ''.join(sorted(body, key=key))
out = re.sub(r'\n{3,}', '\n\n', out).rstrip() + '\n'
io.open(ART, 'w', encoding='utf-8', newline='\n').write(out)

order = [re.match(r'## [^\n]*', c).group(0) for c in lead + sorted(body, key=key)]
print('\n'.join(order))
