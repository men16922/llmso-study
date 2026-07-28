#!/usr/bin/env python3
"""
enrich_summaries.py — index/*.json 의 summary 만 LLM 요약으로 교체한다 (C안).

배경: PageIndex 통째로 돌려본 결과(index/_verify/) 요약 품질은 좋았지만
      ① 실행할 때마다 트리 제목이 달라지고 ② 한국어 문서인데 요약이 영어로 나왔다.
      그래서 트리는 build_pageindex.py 의 결정론적 결과를 그대로 두고,
      summary 필드만 LLM으로 채운다. 재현성 문제와 언어 문제를 동시에 피한다.

LLM 백엔드는 `claude -p` (별도 API 키 불필요).

특징
    - 캐시: 노드 원문 해시 기준. 중단 후 재실행하면 이미 만든 요약은 건너뛴다.
    - 부분 실행: --doc / --max-depth / --limit 으로 비용을 조절한다.
    - 원본 보존: summary 외 필드는 건드리지 않는다.

사용 예
    # 먼저 규모와 비용을 가늠 (LLM 호출 없음)
    python3 tools/enrich_summaries.py --dry-run

    # 상위 2단계만, 문서 하나에 대해 시험
    python3 tools/enrich_summaries.py --doc nhn --max-depth 2 --limit 5

    # 실제 적용
    python3 tools/enrich_summaries.py --doc nhn --max-depth 2
"""

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time

REPO = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
INDEX_DIR = os.path.join(REPO, "index")
PDF_DIR = os.path.join(REPO, "knowledge", "references", "pdf")
CACHE_PATH = os.path.join(INDEX_DIR, ".summary_cache.json")

MAX_SOURCE_CHARS = 6000   # 프롬프트에 넣을 원문 상한
MAX_PDF_PAGES = 6         # 한 노드에서 읽을 PDF 페이지 상한
CONCURRENCY = 3

PROMPT = """다음은 문서 "{doc}"의 "{title}" 섹션 원문이다.

이 섹션이 무엇을 다루는지 **한국어로 2~3문장** 요약하라.

규칙:
- 원문에 없는 내용을 지어내지 말 것
- "이 섹션은~", "본 문서는~" 같은 서두 없이 핵심부터 쓸 것
- 고유명사·수치·기술 용어는 원문 표기를 유지할 것
- 요약문만 출력하고 그 외 어떤 말도 덧붙이지 말 것

--- 원문 시작 ---
{text}
--- 원문 끝 ---"""

_sem = threading.Semaphore(CONCURRENCY)
_lock = threading.Lock()
_stats = {"llm": 0, "cached": 0, "skipped": 0, "errors": 0, "seconds": 0.0}


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            return json.load(open(CACHE_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_cache(cache):
    os.makedirs(INDEX_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)


def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def summarize(doc, title, text, timeout=180):
    prompt = PROMPT.format(doc=doc, title=title, text=text[:MAX_SOURCE_CHARS])
    with _sem:
        t0 = time.time()
        try:
            p = subprocess.run(
                ["claude", "-p", "--output-format", "text"],
                input=prompt, capture_output=True, text=True, timeout=timeout,
            )
            out = clean(p.stdout)
            if p.returncode != 0 and not out:
                raise RuntimeError(p.stderr.strip()[:200] or f"exit {p.returncode}")
        except Exception as e:
            with _lock:
                _stats["errors"] += 1
            print(f"    ! 실패 ({title[:30]}): {e}", file=sys.stderr)
            return None
        dt = time.time() - t0
    with _lock:
        _stats["llm"] += 1
        _stats["seconds"] += dt
        n = _stats["llm"]
    if n % 5 == 0:
        print(f"    … {n}건 완료 / 누적 {_stats['seconds']:.0f}s", flush=True)
    return out


# ------------------------------------------------------------ 원문 추출

def pdf_text_fn(pdf_name):
    import fitz
    path = os.path.join(PDF_DIR, pdf_name)
    if not os.path.exists(path):
        return None
    doc = fitz.open(path)

    def get(start, end):
        last = min(end, start + MAX_PDF_PAGES - 1, doc.page_count)
        buf = []
        for p in range(max(1, start), last + 1):
            try:
                buf.append(doc[p - 1].get_text())
            except Exception:
                continue
            if len(" ".join(buf)) > MAX_SOURCE_CHARS:
                break
        return " ".join(buf)

    return get


def md_text_fn(rel_path):
    path = os.path.join(REPO, rel_path)
    if not os.path.exists(path):
        return None
    lines = open(path, encoding="utf-8").read().splitlines()

    def get(start, end):
        return "\n".join(lines[max(0, start - 1): min(end, len(lines))])

    return get


# ------------------------------------------------------------ 순회

def collect(nodes, depth=0, out=None):
    out = out if out is not None else []
    for n in nodes:
        out.append((n, depth))
        collect(n.get("nodes", []), depth + 1, out)
    return out


def process_doc(doc_name, structure, text_fn, args, cache):
    targets = []
    for node, depth in collect(structure):
        if args.max_depth is not None and depth >= args.max_depth:
            _stats["skipped"] += 1
            continue
        src = clean(text_fn(node["start_index"], node["end_index"]))
        if len(src) < 80:                      # 원문이 거의 없으면 요약할 게 없다
            _stats["skipped"] += 1
            continue
        key = hashlib.sha1(
            f"{doc_name}|{node['title']}|{src[:2000]}".encode("utf-8")
        ).hexdigest()[:16]
        if key in cache:
            node["summary"] = cache[key]
            _stats["cached"] += 1
            continue
        targets.append((node, src, key))

    if args.limit:
        targets = targets[: args.limit]
    if args.dry_run or not targets:
        return len(targets)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {
            ex.submit(summarize, doc_name, n["title"], s): (n, k)
            for n, s, k in targets
        }
        for fut, (node, key) in futs.items():
            res = fut.result()
            if res:
                node["summary"] = res
                cache[key] = res
    return len(targets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="문서 이름 부분 일치 필터 (예: nhn, inference)")
    ap.add_argument("--max-depth", type=int, default=2,
                    help="이 깊이 미만 노드만 요약 (기본 2 = 상위 2단계). 0이면 전체")
    ap.add_argument("--limit", type=int, help="문서당 최대 요약 개수 (시험용)")
    ap.add_argument("--dry-run", action="store_true", help="대상 개수만 세고 종료")
    args = ap.parse_args()
    if args.max_depth == 0:
        args.max_depth = None

    files = sorted(f for f in glob.glob(os.path.join(INDEX_DIR, "*.json")))
    cache = load_cache()
    total_targets = 0

    for path in files:
        data = json.load(open(path, encoding="utf-8"))
        changed = 0

        if "documents" in data:                      # 마크다운 묶음
            for d in data["documents"]:
                if args.doc and args.doc.lower() not in d["doc_name"].lower():
                    continue
                fn = md_text_fn(d["doc_name"])
                if fn:
                    changed += process_doc(d["doc_name"], d["structure"], fn, args, cache)
        else:                                        # PDF
            if args.doc and args.doc.lower() not in data["doc_name"].lower():
                continue
            fn = pdf_text_fn(data["doc_name"])
            if fn:
                changed += process_doc(data["doc_name"], data["structure"], fn, args, cache)

        total_targets += changed
        if changed and not args.dry_run:
            data.setdefault("meta", {})["summary_method"] = "llm-claude-code-korean"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ {os.path.basename(path)} — {changed}개 요약 갱신")
        elif changed:
            print(f"  · {os.path.basename(path)} — 대상 {changed}개")

    if not args.dry_run:
        save_cache(cache)

    print(f"\n대상 {total_targets}개 · LLM {_stats['llm']}건 · 캐시적중 {_stats['cached']}건 "
          f"· 건너뜀 {_stats['skipped']}건 · 실패 {_stats['errors']}건")
    if args.dry_run:
        est = total_targets * 12
        print(f"예상: 호출 {total_targets}회, 동시 {CONCURRENCY} 기준 약 {est // CONCURRENCY // 60}분")
    return 0


if __name__ == "__main__":
    sys.exit(main())
