#!/usr/bin/env python3
"""글을 장 순서대로 조립한다.

측정이 순서대로 끝나지 않아서 장을 쓴 순서와 실을 순서가 다르다.
`## ` 헤딩에서 쪼갠 뒤 번호순으로 다시 붙이고, 부록과 참고 자료는 맨 뒤에 둔다.
sections/의 장이 글에 이미 있으면 sections/ 쪽으로 덮어쓴다 — 몇 번 돌려도 결과가 같다.
"""
import io
import os
import re

ART = 'articles/처리량이 올랐다면 무엇이 빨라진 것인가.md'
SEC = '_workspace/2026-09-02-001/sections'


def heading(chunk):
    return chunk.split(chr(10), 1)[0]


def key(chunk):
    m = re.match(r'## (\d+)\.', chunk)
    if m:
        return (0, int(m.group(1)))
    if chunk.startswith('## 부록'):
        return (1, 0)
    return (2, 0)


def main():
    text = io.open(ART, encoding='utf-8').read()
    extra = ''.join(io.open(os.path.join(SEC, f), encoding='utf-8').read()
                    for f in sorted(os.listdir(SEC)) if f.endswith('.md'))

    parts = re.split(r'(?m)^(?=## )', text + chr(10) + extra)
    head, chapters = parts[0], parts[1:]

    # "결과 한눈에 보기"와 "목차"는 머리말의 일부라 항상 맨 앞에 남는다.
    lead = [c for c in chapters
            if c.startswith('## 결과 한눈에 보기') or c.startswith('## 목차')]
    body = [c for c in chapters if c not in lead]

    seen = {}
    for c in body:
        seen[heading(c)] = c
    body = sorted(seen.values(), key=key)

    out = head + ''.join(lead) + ''.join(body)
    out = re.sub(chr(10) + '{3,}', chr(10) * 2, out).rstrip() + chr(10)
    io.open(ART, 'w', encoding='utf-8', newline=chr(10)).write(out)

    for c in lead + body:
        print(heading(c))


if __name__ == '__main__':
    main()
