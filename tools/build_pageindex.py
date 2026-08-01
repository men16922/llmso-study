#!/usr/bin/env python3
"""
build_pageindex.py — PageIndex 호환 트리 인덱스 생성기 (로컬/무API 버전)

PageIndex(https://github.com/VectifyAI/PageIndex)와 동일한 JSON 트리 스키마
  { title, node_id, start_index, end_index, summary, nodes[] }
를 생성하되, LLM 호출 없이 결정론적으로 만든다.

  - PDF  : PyMuPDF가 읽은 내장 목차(TOC)를 트리로 사용. 없으면 사이드카 TOC 파일 사용.
  - MD   : 마크다운 헤딩(#, ##, ###)을 트리로 사용. 인덱스는 '줄 번호'.

summary는 LLM 요약이 아니라 해당 구간 첫 문단을 잘라낸 '발췌(extractive)'다.
문서 루트의 meta.summary_method 로 이를 명시한다.

사용법:
    python3 tools/build_pageindex.py                 # 전체 재생성
    python3 tools/build_pageindex.py --only pdf      # PDF만
    python3 tools/build_pageindex.py --only md       # 마크다운만
"""

import argparse
import importlib.util
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
PDF_DIR = os.path.join(REPO, "knowledge", "references", "pdf")
KNOWLEDGE_DIR = os.path.join(REPO, "knowledge")  # (하위 호환용, 현재는 REPO 전체를 순회)
TOC_DIR = os.path.join(REPO, "tools", "toc")
OUT_DIR = os.path.join(REPO, "index")

# 마크다운 인덱싱에서 제외할 디렉터리
MD_SKIP_DIRS = {
    ".git",
    ".claude",
    "_workspace",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
}

SUMMARY_CHARS = 300


class NodeIdGen:
    """PageIndex 형식의 4자리 zero-padded 노드 ID를 순서대로 발급."""

    def __init__(self):
        self.n = -1

    def next(self):
        self.n += 1
        return f"{self.n:04d}"


def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def make_summary(text):
    t = clean(text)
    if len(t) <= SUMMARY_CHARS:
        return t
    cut = t[:SUMMARY_CHARS]
    last = max(cut.rfind(". "), cut.rfind("다. "), cut.rfind("! "), cut.rfind("? "))
    if last > SUMMARY_CHARS * 0.5:
        cut = cut[: last + 1]
    return cut.rstrip() + " …"


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def toc_to_tree(toc, last_page, page_text, idgen):
    """PyMuPDF get_toc() 결과([[level, title, page], ...])를 중첩 트리로 변환."""
    root = {"level": 0, "children": []}
    stack = [root]

    for level, title, page in toc:
        while len(stack) > level:
            stack.pop()
        while len(stack) < level:
            # 레벨이 건너뛴 경우(예: 1 → 3) 더미로 채워 트리를 안정시킨다
            filler = stack[-1]["children"][-1] if stack[-1]["children"] else None
            if filler is None:
                break
            stack.append(filler)

        node = {"level": level, "title": clean(title), "page": max(1, page), "children": []}
        stack[-1]["children"].append(node)
        stack.append(node)

    def flatten_starts(node, acc):
        for c in node["children"]:
            acc.append(c)
            flatten_starts(c, acc)

    ordered = []
    flatten_starts(root, ordered)

    # end_index = 다음 노드 시작 - 1 (문서 순서 기준), 마지막은 문서 끝
    for i, node in enumerate(ordered):
        nxt = ordered[i + 1]["page"] if i + 1 < len(ordered) else last_page + 1
        node["end"] = max(node["page"], nxt - 1)

    def subtree_last(node):
        return subtree_last(node["children"][-1]) if node["children"] else node

    def build(node):
        # 자기 구간이 표지/장 제목뿐이라 요약이 빈약하면, 하위 트리 끝까지 넓혀 다시 뽑는다
        text = page_text(node["page"], node["end"])
        if len(clean(text)) < 150 and node["children"]:
            text = page_text(node["page"], subtree_last(node)["end"])
        out = {
            "title": node["title"],
            "node_id": idgen.next(),
            "start_index": node["page"],
            "end_index": node["end"],
            "summary": make_summary(text),
        }
        kids = [build(c) for c in node["children"]]
        if kids:
            out["nodes"] = kids
        return out

    return [build(c) for c in root["children"]]


def build_pdf(path, idgen):
    import fitz

    doc = fitz.open(path)
    name = os.path.splitext(os.path.basename(path))[0]
    meta = doc.metadata or {}

    def page_text(start, end, max_pages=4):
        """구간 앞부분에서 요약 분량이 찰 때까지만 읽는다 (전체를 읽으면 느림)."""
        buf = []
        last = min(end, start + max_pages - 1, doc.page_count)
        for p in range(max(1, start), last + 1):
            try:
                buf.append(doc[p - 1].get_text())
            except Exception:
                continue
            if len(clean(" ".join(buf))) > SUMMARY_CHARS * 2:
                break
        return " ".join(buf)

    toc = doc.get_toc()
    source = "embedded_toc"

    if not toc:
        sidecar = os.path.join(TOC_DIR, name + ".json")
        if os.path.exists(sidecar):
            with open(sidecar, encoding="utf-8") as f:
                toc = json.load(f)
            source = "sidecar_toc"
        else:
            print(f"  ! {name}: 내장 TOC 없음, 사이드카({sidecar})도 없음 → 루트 노드만 생성")
            toc = []
            source = "none"

    structure = toc_to_tree(toc, doc.page_count, page_text, idgen) if toc else []

    result = {
        "doc_name": os.path.basename(path),
        "doc_description": clean(meta.get("title") or name),
        "meta": {
            "type": "pdf",
            "pages": doc.page_count,
            "author": clean(meta.get("author")) or None,
            "index_unit": "page",
            "toc_source": source,
            "summary_method": "extractive-first-page",
            "generator": "tools/build_pageindex.py",
        },
        "structure": structure,
    }
    doc.close()
    return name, result


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

# Notion 토글(<details>)의 자식 블록은 탭으로 들여쓴다. 공백 네 칸은
# 코드 블록일 수 있으므로 허용하지 않고, 선행 탭만 제거해 헤딩을 찾는다.
HEADING = re.compile(r"^\t*(#{1,4})\s+(.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")


def parse_md_headings(lines):
    """코드펜스 안의 '#'는 헤딩으로 세지 않는다."""
    out, in_fence = [], False
    for i, line in enumerate(lines, start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            out.append((len(m.group(1)), clean(m.group(2)), i))
    return out


def build_md(path, idgen, rel_root):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    heads = parse_md_headings(lines)
    rel = os.path.relpath(path, rel_root)

    def strip_md(s):
        s = re.sub(r"^[-*+]\s+|^\d+\.\s+", "", s)  # 목록 마커 제거
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # 링크는 텍스트만
        return s.replace("**", "").replace("`", "").strip()

    def body_after(start_line, end_line, allow_tables=False):
        """구간의 산문·목록을 발췌. 표/코드/헤딩은 기본적으로 건너뛴다.

        allow_tables=True 면 표 셀도 긁는다. 내용이 표뿐인 섹션(이 저장소에 많다)에서
        요약이 통째로 비는 걸 막기 위한 2차 시도.
        """
        chunk, in_fence = [], False
        for line in lines[start_line: min(end_line, len(lines))]:
            s = line.strip()
            if FENCE.match(s):
                in_fence = not in_fence
                continue
            if in_fence or not s:
                continue
            if s.startswith("|"):
                if not allow_tables:
                    continue
                cells = [c.strip() for c in s.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):  # 구분선 행
                    continue
                s = " · ".join(strip_md(c) for c in cells if c.strip())
            elif s.startswith(("#", ">", "!", "---", ":--")):
                continue
            else:
                s = strip_md(s)
            if not s:
                continue
            chunk.append(s)
            if len(" ".join(chunk)) > SUMMARY_CHARS:
                break
        return " ".join(chunk)

    root = {"level": 0, "children": []}
    stack = [root]
    for level, title, line_no in heads:
        while len(stack) > 1 and stack[-1]["level"] >= level:
            stack.pop()
        node = {"level": level, "title": title, "line": line_no, "children": []}
        stack[-1]["children"].append(node)
        stack.append(node)

    ordered = []

    def flatten(n):
        for c in n["children"]:
            ordered.append(c)
            flatten(c)

    flatten(root)
    for i, node in enumerate(ordered):
        nxt = ordered[i + 1]["line"] if i + 1 < len(ordered) else len(lines) + 1
        node["end"] = max(node["line"], nxt - 1)

    def subtree_last(node):
        return subtree_last(node["children"][-1]) if node["children"] else node

    def build(node):
        # ① 자기 구간의 산문
        text = body_after(node["line"], node["end"])
        # ② 제목 아래 하위 제목만 있으면 하위 트리까지 넓힘
        if len(clean(text)) < 40 and node["children"]:
            text = body_after(node["line"], subtree_last(node)["end"])
        # ③ 그래도 비면 표 내용까지 긁는다 (표만 있는 섹션 대응)
        if len(clean(text)) < 40:
            end = subtree_last(node)["end"] if node["children"] else node["end"]
            text = body_after(node["line"], end, allow_tables=True)
        out = {
            "title": node["title"],
            "node_id": idgen.next(),
            "start_index": node["line"],
            "end_index": node["end"],
            "summary": make_summary(text),
        }
        kids = [build(c) for c in node["children"]]
        if kids:
            out["nodes"] = kids
        return out

    return {
        "doc_name": rel,
        "doc_description": heads[0][1] if heads else rel,
        "meta": {
            "type": "markdown",
            "lines": len(lines),
            "index_unit": "line",
            "summary_method": "extractive-first-paragraph",
            "generator": "tools/build_pageindex.py",
        },
        "structure": [build(c) for c in root["children"]],
    }


# --------------------------------------------------------------------------

def count_nodes(nodes):
    return sum(1 + count_nodes(n.get("nodes", [])) for n in nodes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["pdf", "md"], help="한 종류만 생성")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    written = []

    if args.only != "md":
        if importlib.util.find_spec("fitz") is None:
            print("PyMuPDF(fitz)가 필요합니다: pip install pymupdf", file=sys.stderr)
            return 1

        for pdf in sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")):
            idgen = NodeIdGen()
            name, result = build_pdf(os.path.join(PDF_DIR, pdf), idgen)
            out = os.path.join(OUT_DIR, f"{name}_structure.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            n = count_nodes(result["structure"])
            written.append((os.path.relpath(out, REPO), n, result["meta"]["toc_source"]))
            print(f"  ✓ {pdf} → {n} nodes ({result['meta']['toc_source']})")

    if args.only != "pdf":
        idgen = NodeIdGen()
        docs = []
        for dirpath, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs if d not in MD_SKIP_DIRS]
            for fn in sorted(files):
                if fn.endswith(".md"):
                    docs.append(build_md(os.path.join(dirpath, fn), idgen, REPO))
        docs.sort(key=lambda d: d["doc_name"])
        bundle = {
            "doc_name": "(repo markdown)",
            "doc_description": "LLMSO 스터디 정리 문서 모음",
            "meta": {
                "type": "markdown-collection",
                "documents": len(docs),
                "index_unit": "line",
                "summary_method": "extractive-first-paragraph",
                "generator": "tools/build_pageindex.py",
            },
            "documents": docs,
        }
        out = os.path.join(OUT_DIR, "knowledge_structure.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        n = sum(count_nodes(d["structure"]) for d in docs)
        written.append((os.path.relpath(out, REPO), n, f"{len(docs)} docs"))
        print(f"  ✓ repo *.md → {n} nodes ({len(docs)} docs)")

    print("\n생성 완료:")
    for path, n, src in written:
        print(f"  {path}  ({n} nodes, {src})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
