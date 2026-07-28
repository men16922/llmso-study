#!/usr/bin/env python3
"""
pageindex_claude.py — 진짜 PageIndex를 'Claude Code'를 LLM 백엔드로 삼아 실행한다.

PageIndex는 LiteLLM을 통해 LLM을 부른다(requirements: litellm==1.84.0).
보통은 OPENAI_API_KEY나 ANTHROPIC_API_KEY가 필요하지만, 여기서는
litellm.completion / acompletion 을 가로채 `claude -p`(헤드리스 모드)로 돌린다.
→ 별도 API 키 없이 이미 로그인된 Claude Code 인증을 그대로 쓴다.

전제
    - `claude` CLI가 PATH에 있고 로그인되어 있을 것
    - PageIndex 저장소를 clone 해 두고 --pageindex 로 경로를 줄 것
      git clone https://github.com/VectifyAI/PageIndex.git
      pip install litellm pymupdf PyPDF2 python-dotenv pyyaml

사용법
    python3 tools/pageindex_claude.py \
        --pageindex /path/to/PageIndex \
        --pdf knowledge/references/pdf/nhn-cloud-factoryx-gpu-whitepaper-2026.pdf \
        --out index/

    # 비용/시간 먼저 재보고 싶을 때 (LLM 호출 안 함)
    python3 tools/pageindex_claude.py --pageindex ... --pdf ... --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time

# ---------------------------------------------------------------- Claude 호출

_LOCK = threading.Semaphore(3)  # claude -p 는 프로세스 스폰이라 동시 실행을 제한
_STATS = {"calls": 0, "in_chars": 0, "out_chars": 0, "seconds": 0.0, "errors": 0}
_STATS_LOCK = threading.Lock()
DRY_RUN = False


def call_claude(prompt, timeout=600):
    """`claude -p` 로 프롬프트를 실행하고 텍스트 응답을 돌려준다."""
    if DRY_RUN:
        with _STATS_LOCK:
            _STATS["calls"] += 1
            _STATS["in_chars"] += len(prompt)
        return '{"dry_run": true}'

    with _LOCK:
        t0 = time.time()  # 세마포어 대기 시간은 빼고 순수 호출 시간만 잰다
        try:
            proc = subprocess.run(
                ["claude", "-p", "--output-format", "text"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = proc.stdout.strip()
            if proc.returncode != 0 and not out:
                raise RuntimeError(proc.stderr.strip()[:400] or f"exit {proc.returncode}")
        except Exception as e:
            with _STATS_LOCK:
                _STATS["errors"] += 1
            raise RuntimeError(f"claude -p 실패: {e}") from e

    dt = time.time() - t0
    with _STATS_LOCK:
        _STATS["calls"] += 1
        _STATS["in_chars"] += len(prompt)
        _STATS["out_chars"] += len(out)
        _STATS["seconds"] += dt
        n = _STATS["calls"]
    if n % 5 == 0:
        print(f"    … LLM 호출 {n}회 / 누적 {_STATS['seconds']:.0f}s", flush=True)
    return out


# ------------------------------------------------- litellm 응답 객체 흉내내기

class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)
        self.finish_reason = "stop"


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


def install_shim():
    """litellm 을 Claude Code 백엔드로 바꿔치기한다.

    PageIndex 는 `from .utils import *` 로 함수를 당겨쓰므로 상위 함수를 패치해도
    이미 바인딩된 이름에는 반영되지 않는다. 반면 utils 내부는 매 호출마다
    litellm.completion 을 '속성으로' 조회하므로 litellm 모듈 쪽을 갈아끼우면 확실히 걸린다.

    또한 litellm 의 기능을 전부 대체하므로 실제 litellm(무거운 의존성)을 설치할 필요가
    없다. sys.modules 에 스텁 모듈을 미리 꽂아 import 를 만족시킨다.
    """
    import types

    def completion(model=None, messages=None, **kwargs):
        prompt = "\n\n".join(m["content"] for m in (messages or []) if m.get("content"))
        return _Response(call_claude(prompt))

    async def acompletion(model=None, messages=None, **kwargs):
        import asyncio
        prompt = "\n\n".join(m["content"] for m in (messages or []) if m.get("content"))
        content = await asyncio.to_thread(call_claude, prompt)
        return _Response(content)

    def token_counter(model=None, text=None, **kwargs):
        # 실제 토크나이저 대신 근사치. 노드 분할 임계값 판단용이라 이 정도면 충분하다.
        # (영문 ~4자/토큰, 한글은 더 촘촘해 보수적으로 3으로 잡음)
        return max(1, len(text or "") // 3)

    stub = sys.modules.get("litellm")
    if stub is None:
        stub = types.ModuleType("litellm")
        sys.modules["litellm"] = stub
        print("  ✓ litellm 스텁 주입 (실제 패키지 설치 불필요)")
    stub.completion = completion
    stub.acompletion = acompletion
    stub.token_counter = token_counter
    stub.drop_params = True
    print("  ✓ LLM 백엔드 → claude -p")


# ---------------------------------------------------------------------- main

def main():
    global DRY_RUN
    ap = argparse.ArgumentParser()
    ap.add_argument("--pageindex", required=True, help="clone 한 PageIndex 저장소 경로")
    ap.add_argument("--pdf", help="처리할 PDF 경로")
    ap.add_argument("--md", help="처리할 마크다운 경로")
    ap.add_argument("--out", default="index", help="결과 JSON 저장 폴더 (기본 index/)")
    ap.add_argument("--model", default="anthropic/claude-sonnet-4-6",
                    help="config 상 모델명. 실제 호출은 claude -p 가 하므로 라벨 용도")
    ap.add_argument("--no-summary", action="store_true", help="노드 요약 생략 (호출 수 크게 감소)")
    ap.add_argument("--dry-run", action="store_true", help="LLM 호출 없이 호출 횟수만 계측")
    args = ap.parse_args()

    if not args.pdf and not args.md:
        ap.error("--pdf 또는 --md 중 하나는 필요합니다")

    DRY_RUN = args.dry_run
    if not DRY_RUN and not subprocess.run(["which", "claude"], capture_output=True).stdout:
        print("claude CLI를 찾을 수 없습니다.", file=sys.stderr)
        return 1

    sys.path.insert(0, os.path.abspath(args.pageindex))
    install_shim()

    import pageindex as pi

    src = args.pdf or args.md
    name = os.path.splitext(os.path.basename(src))[0]
    print(f"  ▶ {os.path.basename(src)} 처리 시작"
          f"{' (dry-run)' if DRY_RUN else ''}", flush=True)

    t0 = time.time()
    if args.pdf:
        result = pi.page_index(
            os.path.abspath(args.pdf),
            model=args.model,
            if_add_node_id="yes",
            if_add_node_summary="no" if args.no_summary else "yes",
            if_add_doc_description="no",
        )
    else:
        result = pi.md_to_tree(os.path.abspath(args.md))
    elapsed = time.time() - t0

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}_structure.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ 저장: {out_path}")
    print(f"    소요 {elapsed:.0f}s · LLM 호출 {_STATS['calls']}회 "
          f"· 입력 {_STATS['in_chars']:,}자 · 출력 {_STATS['out_chars']:,}자 "
          f"· 실패 {_STATS['errors']}회")
    return 0


if __name__ == "__main__":
    sys.exit(main())
