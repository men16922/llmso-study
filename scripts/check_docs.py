#!/usr/bin/env python3
"""저장소 게이트 — 문서·인덱스 무결성을 오프라인·결정론적으로 검증합니다.

이 저장소는 애플리케이션이 아니라 문서 모음 + 인덱싱 도구라서, "빌드가 되는가"가
아니라 **문서가 서로 가리키는 곳이 실제로 존재하는가**가 유일하게 의미 있는 검증입니다.

검사 항목:
  1. links  — 마크다운의 상대 경로 링크가 실제 파일/앵커를 가리키는가
  2. index  — index/*.json이 PageIndex 스키마를 지키는가, 구간이 뒤집히지 않았는가
  3. tools  — tools/·scripts/의 파이썬이 문법적으로 성립하는가

네트워크·LLM·GPU를 쓰지 않으며, 같은 트리에 대해 항상 같은 결과를 냅니다.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent

# 순회 제외 — build_pageindex.py --only md 의 제외 목록과 맞춥니다.
SKIP_DIRS = {
    ".git", ".claude", ".codex", ".kiro", "node_modules", "__pycache__",
    ".venv", "logs", "_workspace",
}

# 링크 검사에서 통째로 제외할 경로 (플러그인이 스캐폴딩한 참조 문서 — 이 저장소 소유가 아님)
LINK_SKIP_PREFIXES = ("docs/engineering/", "scripts/overnight/")

INLINE_LINK = re.compile(r"(?<!!)\[(?:[^\]\[]|\[[^\]]*\])*\]\(\s*<?([^)<>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s*(```|~~~)")
ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# 이 저장소는 <a id="..."></a> 로 명시 앵커를 다는 관례를 씁니다 (deep-dives.md, index/README.md).
EXPLICIT_ANCHOR = re.compile(r"<a\s+(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)


def iter_markdown() -> list[Path]:
    out = []
    for p in sorted(REPO.rglob("*.md")):
        rel = p.relative_to(REPO)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        out.append(p)
    return out


def strip_code_fences(text: str) -> list[tuple[int, str]]:
    """(줄번호, 본문) 목록. 코드 펜스 내부는 제외 — 예시 링크를 검사하지 않기 위함."""
    lines = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append((i, line))
    return lines


def _anchor_char_ok(ch: str) -> bool:
    """GitHub 슬러그가 보존하는 문자 — ASCII 영숫자, 하이픈/밑줄/공백, 유니코드 글자·결합기호.

    ⑥ 같은 기호 숫자(category No)나 em dash는 제거됩니다. 한글은 유지됩니다.
    """
    if ch in {" ", "-", "_"}:
        return True
    if ch.isascii():
        return ch.isalnum()
    return unicodedata.category(ch)[0] in {"L", "M", "N"} and not unicodedata.category(ch) == "No"


def slugify(heading: str) -> str:
    """GitHub 앵커 규칙: 마크다운 서식 제거 → 소문자화 → 허용 문자만 남김 → 공백을 하이픈으로."""
    s = re.sub(r"`([^`]*)`", r"\1", heading)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[*_~]", "", s)
    s = s.strip().lower()
    return "".join(ch for ch in s if _anchor_char_ok(ch)).replace(" ", "-")


def anchors_of(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    seen: dict[str, int] = {}
    out = set()
    for _, line in strip_code_fences(text):
        out.update(EXPLICIT_ANCHOR.findall(line))
        m = ATX_HEADING.match(line)
        if not m:
            continue
        base = slugify(m.group(2))
        if not base:
            continue
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.add(base if n == 0 else f"{base}-{n}")
    return out


def check_links() -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}

    for md in iter_markdown():
        rel = md.relative_to(REPO).as_posix()
        if rel.startswith(LINK_SKIP_PREFIXES):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: 읽기 실패 — {exc}")
            continue

        for lineno, line in strip_code_fences(text):
            for target in INLINE_LINK.findall(line):
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
                    continue  # http:, mailto:, 프로토콜 상대 등 외부 링크는 검사하지 않음

                path_part, _, anchor = target.partition("#")
                path_part = unquote(path_part)  # 공백이 %20으로 인코딩된 링크

                if not path_part:  # 같은 문서 내 앵커
                    dest = md
                else:
                    dest = (md.parent / path_part).resolve()
                    if not dest.exists():
                        errors.append(f"{rel}:{lineno}: 링크 대상 없음 → {target}")
                        continue
                    if dest.is_dir():
                        continue  # 디렉터리 링크는 앵커 검사 대상이 아님

                if anchor and dest.suffix == ".md":
                    if dest not in anchor_cache:
                        anchor_cache[dest] = anchors_of(dest)
                    anchor = unquote(anchor)
                    if anchor not in anchor_cache[dest] and slugify(anchor) not in anchor_cache[dest]:
                        errors.append(f"{rel}:{lineno}: 앵커 없음 → {target}")
    return errors


def check_index() -> list[str]:
    errors: list[str] = []
    index_dir = REPO / "index"
    if not index_dir.is_dir():
        return ["index/ 디렉터리가 없습니다"]

    # .summary_cache.json은 인덱스가 아니라 LLM 요약 캐시(커밋 제외)이므로 제외합니다.
    jsons = [p for p in sorted(index_dir.glob("*.json")) if not p.name.startswith(".")]
    if not jsons:
        return ["index/*.json이 하나도 없습니다 — build_pageindex.py를 실행하세요"]

    def walk(node: object, path: str, doc: str) -> None:
        if not isinstance(node, dict):
            errors.append(f"{doc}: {path} 노드가 객체가 아닙니다")
            return
        for key in ("title", "node_id"):
            if key not in node:
                errors.append(f"{doc}: {path} 에 '{key}' 필드가 없습니다")
        start, end = node.get("start_index"), node.get("end_index")
        if isinstance(start, int) and isinstance(end, int) and end < start:
            errors.append(f"{doc}: {path} 구간이 뒤집혔습니다 (start={start} > end={end})")
        for i, child in enumerate(node.get("nodes") or []):
            walk(child, f"{path}.nodes[{i}]", doc)

    for jf in jsons:
        doc = jf.relative_to(REPO).as_posix()
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{doc}: JSON 파싱 실패 — {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{doc}: 최상위가 객체가 아닙니다")
            continue
        meta = data.get("meta")
        if not isinstance(meta, dict) or "summary_method" not in meta:
            errors.append(f"{doc}: meta.summary_method 가 없습니다")

        # 단일 문서(PDF)는 최상위에 structure, 마크다운 묶음은 documents[] 안에 문서별 structure를 둡니다.
        if isinstance(data.get("documents"), list):
            entries = [
                (f"{doc}#{e.get('doc_name', i)}", e)
                for i, e in enumerate(data["documents"])
                if isinstance(e, dict)
            ]
            if not entries:
                errors.append(f"{doc}: documents[] 가 비어 있습니다")
        else:
            entries = [(doc, data)]

        for label, entry in entries:
            roots = entry.get("structure") or entry.get("nodes") or []
            if not roots:
                errors.append(f"{label}: 노드가 비어 있습니다")
            for i, root in enumerate(roots):
                walk(root, f"structure[{i}]", label)
    return errors


def check_tools() -> list[str]:
    errors: list[str] = []
    targets = sorted((REPO / "tools").glob("*.py")) + sorted((REPO / "scripts").glob("*.py"))
    for py in targets:
        rel = py.relative_to(REPO).as_posix()
        try:
            py_compile.compile(str(py), doraise=True, cfile=str(py) + "c")
        except py_compile.PyCompileError as exc:
            errors.append(f"{rel}: 컴파일 실패 — {exc.msg.strip()}")
        finally:
            Path(str(py) + "c").unlink(missing_ok=True)
    return errors


CHECKS = {"links": check_links, "index": check_index, "tools": check_tools}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=sorted(CHECKS), help="한 가지 검사만 실행")
    args = ap.parse_args()

    names = [args.only] if args.only else list(CHECKS)
    total = 0
    for name in names:
        errors = CHECKS[name]()
        total += len(errors)
        if errors:
            print(f"✗ {name}: {len(errors)}건")
            for e in errors:
                print(f"    {e}")
        else:
            print(f"✓ {name}")

    if total:
        print(f"\n게이트 실패 — 총 {total}건", file=sys.stderr)
        return 1
    print("\n게이트 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
