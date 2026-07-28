#!/usr/bin/env python3
"""
search_index.py — index/*.json 트리를 키워드로 탐색한다.

PageIndex의 "reasoning-based retrieval"은 LLM이 트리를 훑어 내려가며 답이 있을
노드를 고르는 방식이다. 이 스크립트는 그 앞단인 '후보 노드 추리기'를 LLM 없이
키워드 매칭으로 수행한다. 결과의 (문서, 페이지/줄 범위)를 그대로 원문에서 펼쳐
읽으면 된다.

사용법:
    python3 tools/search_index.py "KV cache"
    python3 tools/search_index.py "prefill decode" --top 15
    python3 tools/search_index.py "MIG" --doc gpu-enabled       # 문서 필터
    python3 tools/search_index.py --outline inference-engineering --depth 2
"""

import argparse
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
INDEX_DIR = os.path.join(REPO, "index")

TITLE_W, SUMMARY_W = 10, 3


def load_docs(doc_filter=None):
    """index/*.json을 (doc_meta, structure) 목록으로 평탄화."""
    docs = []
    for path in sorted(glob.glob(os.path.join(INDEX_DIR, "*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        if "documents" in data:
            for d in data["documents"]:
                docs.append((d["doc_name"], d["meta"]["index_unit"], d["structure"]))
        else:
            docs.append((data["doc_name"], data["meta"]["index_unit"], data["structure"]))
    if doc_filter:
        f = doc_filter.lower()
        docs = [d for d in docs if f in d[0].lower()]
    return docs


def walk(nodes, trail=()):
    for n in nodes:
        path = trail + (n["title"],)
        yield n, path
        yield from walk(n.get("nodes", []), path)


def score(node, terms):
    title = node["title"].lower()
    summary = node.get("summary", "").lower()
    total, hit = 0, 0
    for t in terms:
        c_t, c_s = title.count(t), summary.count(t)
        if c_t or c_s:
            hit += 1
        total += c_t * TITLE_W + min(c_s, 4) * SUMMARY_W
    if hit == 0:
        return 0
    # 모든 검색어가 걸린 노드를 크게 우대
    return total * (1 + hit / len(terms)) * (2 if hit == len(terms) else 1)


def highlight(text, terms, width=150):
    low = text.lower()
    pos = min((low.find(t) for t in terms if low.find(t) >= 0), default=-1)
    if pos < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, pos - 40)
    snippet = text[start:start + width]
    return ("…" if start else "") + snippet + ("…" if start + width < len(text) else "")


def cmd_search(args):
    terms = [t.lower() for t in re.split(r"\s+", args.query.strip()) if t]
    if not terms:
        print("검색어가 없습니다.", file=sys.stderr)
        return 1

    results = []
    for doc_name, unit, structure in load_docs(args.doc):
        for node, path in walk(structure):
            s = score(node, terms)
            if s > 0:
                results.append((s, doc_name, unit, node, path))

    if not results:
        print(f"'{args.query}' 결과 없음.")
        return 0

    results.sort(key=lambda r: -r[0])
    print(f"'{args.query}' → {len(results)}개 노드 매칭 (상위 {min(args.top, len(results))}개)\n")

    for rank, (s, doc_name, unit, node, path) in enumerate(results[:args.top], 1):
        loc = "p." if unit == "page" else "L"
        span = f"{loc}{node['start_index']}-{node['end_index']}"
        print(f"{rank:2}. [{s:6.1f}] {doc_name}  {span}")
        if len(path) > 1:
            print(f"      {' › '.join(path[:-1])[:100]}")
        print(f"      ▸ {node['title']}")
        if node.get("summary"):
            print(f"        {highlight(node['summary'], terms)}")
        print()
    return 0


def cmd_outline(args):
    docs = load_docs(args.outline)
    if not docs:
        print(f"'{args.outline}'에 해당하는 문서가 없습니다.", file=sys.stderr)
        return 1
    for doc_name, unit, structure in docs:
        print(f"\n=== {doc_name} ===")
        loc = "p." if unit == "page" else "L"
        for node, path in walk(structure):
            depth = len(path) - 1
            if depth < args.depth:
                print(f"{'  ' * depth}- {node['title']}  ({loc}{node['start_index']}-{node['end_index']})")
    return 0


def main():
    ap = argparse.ArgumentParser(description="PageIndex 트리 키워드 탐색")
    ap.add_argument("query", nargs="?", help="검색어 (공백으로 구분)")
    ap.add_argument("--top", type=int, default=10, help="출력 개수 (기본 10)")
    ap.add_argument("--doc", help="문서 이름 부분 일치 필터")
    ap.add_argument("--outline", help="해당 문서의 목차 출력")
    ap.add_argument("--depth", type=int, default=2, help="--outline 깊이 (기본 2)")
    args = ap.parse_args()

    if not os.path.isdir(INDEX_DIR):
        print("index/ 가 없습니다. 먼저 python3 tools/build_pageindex.py 를 실행하세요.", file=sys.stderr)
        return 1
    if args.outline:
        return cmd_outline(args)
    if not args.query:
        ap.print_help()
        return 1
    return cmd_search(args)


if __name__ == "__main__":
    sys.exit(main())
