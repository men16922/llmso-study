#!/usr/bin/env python3
"""마크다운 문서를 Notion-flavored Markdown으로 변환한다.

    python3 tools/md_to_notion.py <입력.md> [--image-map map.json] [-o 출력.md]

노션에 붙일 때 손으로 고쳐야 했던 것들을 자동화한다.

- **파이프 표 → `<table>` XML** — 노션은 파이프 표를 그대로 받지 않는다. 표가 열 개를
  넘어가면 손으로 옮기다 반드시 어딘가 틀린다.
- **`<details>` 자식 들여쓰기** — 노션은 토글 자식이 탭으로 들여써져 있어야 접힌다.
  들여쓰기가 없으면 토글 밖으로 튀어나온다.
- **이미지 경로 치환** — 로컬 상대 경로를 업로드된 URL로 바꾼다(`--image-map`).
- **`<aside>` → `<callout>`**, 수동 목차 → `<table_of_contents/>`.

코드 펜스 안은 건드리지 않는다. 노션 규격상 코드 블록 내용은 문자 그대로다.
"""

import argparse
import json
import os
import re
import sys

FENCE = re.compile(r"^\s*```")
PIPE_ROW = re.compile(r"^\s*\|.*\|\s*$")
SEP_ROW = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


def split_cells(line):
    """파이프 표의 한 행을 셀 목록으로 나눈다. 인라인 코드 안의 `|`는 보호한다."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]

    cells, buf, in_code = [], [], False
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            buf.append("|")          # 이스케이프된 파이프는 리터럴
            i += 1
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def table_to_xml(rows, indent=""):
    """[[셀,...], ...] → 노션 <table> XML. 첫 행을 헤더로 본다."""
    out = [f'{indent}<table fit-page-width="true" header-row="true">']
    for row in rows:
        out.append(f"{indent}<tr>")
        for cell in row:
            out.append(f"{indent}<td>{cell}</td>")
        out.append(f"{indent}</tr>")
    out.append(f"{indent}</table>")
    return out


def convert(lines, image_map):
    out = []
    i = 0
    in_fence = False
    # <details> 안에서는 자식을 탭으로 들여쓴다 (노션 토글 요구사항)
    depth = 0

    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        if FENCE.match(line):
            in_fence = not in_fence
            out.append(("\t" * depth) + stripped)
            i += 1
            continue

        if in_fence:
            # 코드 블록 내용은 문자 그대로. 들여쓰기만 맞춘다.
            out.append(("\t" * depth) + line if depth else line)
            i += 1
            continue

        # --- 토글 ---
        if stripped.startswith("<details"):
            out.append(("\t" * depth) + stripped)
            depth += 1
            i += 1
            continue
        if stripped.startswith("</details>"):
            depth = max(0, depth - 1)
            out.append(("\t" * depth) + stripped)
            i += 1
            continue
        if stripped.startswith("<summary"):
            # summary는 details와 같은 레벨 (자식이 아니다)
            out.append(("\t" * (depth - 1) if depth else "") + stripped)
            i += 1
            continue

        # --- aside → callout ---
        if stripped == "<aside>":
            out.append(("\t" * depth) + '<callout icon="🎯" color="blue_bg">')
            depth += 1
            i += 1
            # 바로 뒤의 단독 이모지 줄은 icon으로 흡수했으므로 버린다
            while i < len(lines) and lines[i].strip() in ("", "🎯"):
                i += 1
            continue
        if stripped == "</aside>":
            depth = max(0, depth - 1)
            out.append(("\t" * depth) + "</callout>")
            i += 1
            continue

        # --- 여러 줄 인용 ---
        # 노션은 줄바꿈을 인용 블록의 끝으로 본다. 연속된 `>` 줄은 <br>로 이어야
        # 하나의 인용으로 렌더된다.
        if stripped.startswith(">"):
            parts = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                parts.append(lines[i].strip().lstrip(">").strip())
                i += 1
            joined = "<br>".join(p for p in parts if p)
            out.append(("\t" * depth) + "> " + joined)
            continue

        # --- 파이프 표 ---
        if PIPE_ROW.match(line):
            block = []
            while i < len(lines) and PIPE_ROW.match(lines[i].rstrip("\n")):
                block.append(lines[i].rstrip("\n"))
                i += 1
            rows = [split_cells(r) for r in block if not SEP_ROW.match(r)]
            if rows:
                out.extend(table_to_xml(rows, "\t" * depth))
            continue

        # --- 이미지·링크 경로 치환 ---
        # 저장소 상대 경로는 노션에서 죽는다. 매핑에 있으면 업로드 URL·노션 페이지로 바꾼다.
        line = IMAGE.sub(
            lambda m: f"![{m.group(1)}]({image_map.get(m.group(2), m.group(2))})", line
        )
        line = LINK.sub(
            lambda m: f"[{m.group(1)}]({image_map.get(m.group(2), m.group(2))})", line
        )

        if not line.strip():
            out.append("")            # 공백 줄에 들여쓰기를 넣으면 빈 블록이 생긴다
        else:
            out.append(("\t" * depth) + line.strip() if depth else line)
        i += 1

    return out


def strip_manual_toc(lines):
    """수동으로 쓴 '## 목차' 불릿 목록을 <table_of_contents/>로 바꾼다."""
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip() in ("## 목차", "## Table of Contents"):
            out.append("<table_of_contents color=\"gray\"/>")
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s == "" or s.startswith("-") or s.startswith("  -"):
                    i += 1
                    continue
                break
            continue
        out.append(lines[i].rstrip("\n"))
        i += 1
    return out


def apply_toggle_headings(lines, toggle_h3, h2_pattern):
    """지정한 헤딩을 노션 토글 헤딩으로 만들고 본문을 한 단 들여쓴다.

    노션은 `### 제목 {toggle="true"}` + 자식 들여쓰기로 접히는 헤딩을 만든다.
    헤딩 텍스트 자체는 건드리지 않으므로 목차(`<table_of_contents/>`)와 앵커가 살아 있다.
    """
    h2_re = re.compile(h2_pattern) if h2_pattern else None
    out = []
    i = 0
    in_fence = False

    def heading_level(s):
        m = re.match(r"^(#{1,4}) ", s)
        return len(m.group(1)) if m else 0

    while i < len(lines):
        line = lines[i]
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue

        lvl = heading_level(line)
        text = line[lvl + 1:] if lvl else ""
        want = (lvl == 3 and toggle_h3) or (lvl == 2 and h2_re and h2_re.search(text))

        if want:
            out.append(f"{line} {{toggle=\"true\"}}")
            i += 1
            # 다음 같은 레벨 이하 헤딩 전까지를 자식으로 들여쓴다
            fence = False
            while i < len(lines):
                nxt = lines[i]
                if FENCE.match(nxt):
                    fence = not fence
                elif not fence:
                    nl = heading_level(nxt)
                    if nl and nl <= lvl:
                        break
                    if nxt.strip() == "---":
                        break          # 구분선은 토글 밖에 둔다
                out.append(("\t" + nxt) if nxt.strip() else "")
                i += 1
            continue

        out.append(line)
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--image-map", help="{로컬경로: 업로드URL} JSON")
    ap.add_argument("--toggle-h3", action="store_true", help="모든 H3를 토글 헤딩으로")
    ap.add_argument("--toggle-h2", help="이 정규식에 맞는 H2를 토글 헤딩으로")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        lines = f.read().splitlines()

    image_map = {}
    if args.image_map:
        with open(args.image_map, encoding="utf-8") as f:
            image_map = json.load(f)

    lines = strip_manual_toc(lines)
    out = convert(lines, image_map)
    if args.toggle_h3 or args.toggle_h2:
        out = apply_toggle_headings(out, args.toggle_h3, args.toggle_h2)
    text = "\n".join(out) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        n_tab = sum(1 for line in out if line.lstrip().startswith("<table"))
        print(f"✓ {args.output}  (표 {n_tab}개 변환, 이미지 매핑 {len(image_map)}건)")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
