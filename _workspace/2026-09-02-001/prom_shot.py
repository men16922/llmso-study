#!/usr/bin/env python3
"""Prometheus 표현식 브라우저를 여러 패널로 띄워 PNG로 굽는다.

    python3 prom_shot.py out.png --range 25m --end "2026-09-02 21:20:00" \
        "sum(vllm:kv_cache_usage_perc)" "sum(vllm:num_requests_waiting)"

왜 이렇게 하는가 — Grafana는 로그인이 필요하고(비밀번호를 대신 입력하지 않는다),
Prometheus 표현식 브라우저는 인증이 없으면서 같은 시계열을 같은 그래프로 보여준다.

★ 경로와 파라미터 이름이 3.x에서 바뀌었다. `/graph?g0.tab=0`은 페이지는 뜨지만
  쿼리가 실행되지 않아 빈 패널이 나온다. `/query?g0.tab=graph&g0.res_type=auto` 라야 한다.
"""
import argparse
import subprocess
import urllib.parse
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def build_url(exprs, range_input, end_input, base="http://localhost:9009"):
    params = []
    for i, e in enumerate(exprs):
        params += [
            (f"g{i}.expr", e),
            (f"g{i}.show_tree", "0"),
            (f"g{i}.tab", "graph"),
            (f"g{i}.range_input", range_input),
            (f"g{i}.res_type", "auto"),
            (f"g{i}.display_mode", "lines"),
            (f"g{i}.show_exemplars", "0"),
        ]
        if end_input:
            params.append((f"g{i}.end_input", end_input))
    return f"{base}/query?" + urllib.parse.urlencode(params)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("exprs", nargs="+")
    ap.add_argument("--range", dest="range_input", default="30m")
    ap.add_argument("--end", dest="end_input", default=None,
                    help='"YYYY-MM-DD HH:MM:SS" (Prometheus UI가 쓰는 로컬 표기)')
    ap.add_argument("--width", type=int, default=1500)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--budget", type=int, default=30000)
    args = ap.parse_args()

    url = build_url(args.exprs, args.range_input, args.end_input)
    out = Path(args.out).resolve()
    out.unlink(missing_ok=True)
    subprocess.run(
        [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={args.width},{args.height}", f"--screenshot={out}",
         f"--virtual-time-budget={args.budget}", url],
        capture_output=True, timeout=180,
    )
    print(f"{'OK ' if out.exists() else 'FAILED '}{out.name}"
          + (f"  {out.stat().st_size // 1024}KB" if out.exists() else ""))
    print(f"  panels={len(args.exprs)} range={args.range_input} end={args.end_input or 'now'}")


if __name__ == "__main__":
    main()
