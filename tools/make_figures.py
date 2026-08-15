#!/usr/bin/env python3
"""B1·B2 결과 JSON에서 글에 넣을 SVG 그래프를 만든다.

외부 의존성 없음 (표준 라이브러리만). 저장소의 다른 도구와 같은 원칙이다 —
matplotlib을 넣으면 이 저장소에서 유일하게 무거운 의존성이 되고,
필요한 것은 선 3개짜리 그래프뿐이다.

    python3 tools/make_figures.py

출력: articles/figures/*.svg

색은 눈으로 고르지 않았다. 3계열이라 카테고리 슬롯 1~3(blue/orange/aqua)을
쓰고, light/dark 양쪽 모드에서 색각 분리도 검증을 통과한 조합이다.
light 모드의 aqua는 표면 대비가 3:1 미만이라 **직접 라벨**을 반드시 함께 둔다.
"""

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "labs", "wsl2-vllm-baseline", "results")
OUTDIR = os.path.join(REPO, "articles", "figures")

# 검증된 카테고리 슬롯 1~3 (light / dark)
SERIES = [
    ("slots=1", "#2a78d6", "#3987e5"),
    ("slots=16", "#eb6834", "#d95926"),
    ("slots=64", "#1baf7a", "#199e70"),
]
SLOTS = [1, 16, 64]

INK = ("#0b0b0b", "#ffffff")        # primary
INK2 = ("#52514e", "#c3c2b7")       # secondary
MUTED = ("#898781", "#898781")      # axis/labels
GRID = ("#e1e0d9", "#2c2c2a")
AXIS = ("#c3c2b7", "#383835")
SURFACE = ("#fcfcfb", "#1a1a19")

FONT = 'system-ui,-apple-system,"Segoe UI",sans-serif'

W, H = 780, 470
# MT는 플롯 상단. 제목(26) · 부제(46) · 범례(70) · y축 단위(92)가 그 위에 쌓인다.
ML, MR, MT, MB = 66, 118, 104, 58    # 오른쪽 여백은 직접 라벨 자리
Y_TITLE, Y_SUB, Y_LEGEND, Y_UNIT = 26, 46, 70, 92


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def head(title, subtitle, legend, unit):
    """SVG 머리말 — 표면을 명시적으로 칠하고 두 모드를 모두 정의한다.

    <img>로 삽입해도 SVG는 자체 렌더링 컨텍스트를 가지므로 내부 미디어 쿼리가 적용된다.

    legend: [(슬롯 인덱스, 이름), ...] — 계열이 2개 이상이면 범례는 항상 둔다.
    unit:   y축 단위. 플롯 왼쪽 위에 눕혀 둔다(세로 회전 텍스트는 읽기 나쁘다).
    """
    css = f"""
  .surface {{ fill: {SURFACE[0]}; }}
  .ink     {{ fill: {INK[0]}; }}
  .ink2    {{ fill: {INK2[0]}; }}
  .muted   {{ fill: {MUTED[0]}; }}
  .grid    {{ stroke: {GRID[0]}; }}
  .axis    {{ stroke: {AXIS[0]}; }}
  .s0 {{ stroke: {SERIES[0][1]}; }} .f0 {{ fill: {SERIES[0][1]}; }}
  .s1 {{ stroke: {SERIES[1][1]}; }} .f1 {{ fill: {SERIES[1][1]}; }}
  .s2 {{ stroke: {SERIES[2][1]}; }} .f2 {{ fill: {SERIES[2][1]}; }}
  @media (prefers-color-scheme: dark) {{
    .surface {{ fill: {SURFACE[1]}; }}
    .ink     {{ fill: {INK[1]}; }}
    .ink2    {{ fill: {INK2[1]}; }}
    .muted   {{ fill: {MUTED[1]}; }}
    .grid    {{ stroke: {GRID[1]}; }}
    .axis    {{ stroke: {AXIS[1]}; }}
    .s0 {{ stroke: {SERIES[0][2]}; }} .f0 {{ fill: {SERIES[0][2]}; }}
    .s1 {{ stroke: {SERIES[1][2]}; }} .f1 {{ fill: {SERIES[1][2]}; }}
    .s2 {{ stroke: {SERIES[2][2]}; }} .f2 {{ fill: {SERIES[2][2]}; }}
  }}
  text {{ font-family: {FONT}; }}
  .tick {{ font-size: 12px; font-variant-numeric: tabular-nums; }}
  .lbl  {{ font-size: 13px; }}
  .ttl  {{ font-size: 17px; font-weight: 600; }}
  .sub  {{ font-size: 13px; }}
  .line {{ fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
"""
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">',
        f"<style>{css}</style>",
        f'<rect class="surface" width="{W}" height="{H}"/>',
        f'<text class="ttl ink" x="{ML}" y="{Y_TITLE}">{esc(title)}</text>',
        f'<text class="sub ink2" x="{ML}" y="{Y_SUB}">{esc(subtitle)}</text>',
    ]
    x = ML
    for slot, name in legend:
        out.append(f'<circle class="f{slot}" cx="{x + 5}" cy="{Y_LEGEND - 4}" r="5"/>')
        out.append(f'<text class="lbl ink" x="{x + 16}" y="{Y_LEGEND}">{esc(name)}</text>')
        x += 26 + int(len(name) * 8.2)
    out.append(f'<text class="lbl muted" x="{ML}" y="{Y_UNIT}">{esc(unit)}</text>')
    return out


def xpos(i, n):
    return ML + (W - ML - MR) * (i / (n - 1))


def load_summaries(fname, scenario):
    with open(os.path.join(RESULTS, fname), encoding="utf-8") as f:
        d = json.load(f)
    return [s for s in d["summaries"] if s["scenario"] == scenario]


def draw_series_label(out, x, y, cls_fill, text, dy=0):
    """직접 라벨 — 텍스트는 잉크 색, 정체성은 옆의 색 점이 나른다."""
    out.append(f'<circle class="{cls_fill}" cx="{x + 12:.1f}" cy="{y + dy:.1f}" r="4.5"/>')
    out.append(
        f'<text class="lbl ink" x="{x + 22:.1f}" y="{y + dy + 4.5:.1f}">{esc(text)}</text>'
    )


def fig_linear(fname, title, subtitle, key, ylab, yticks, files, scenario):
    n_series = len(files)
    data = [load_summaries(f, scenario) for f in files]
    xs = [s["concurrency"] for s in data[0]]
    n = len(xs)
    ymax = yticks[-1]
    y0, y1 = H - MB, MT

    def ypos(v):
        return y1 + (y0 - y1) * (1 - v / ymax)

    out = head(title, subtitle, [(i, SERIES[i][0]) for i in range(n_series)], ylab)
    for t in yticks:
        y = ypos(t)
        out.append(f'<line class="grid" x1="{ML}" y1="{y:.1f}" x2="{W - MR}" y2="{y:.1f}" stroke-width="1"/>')
        out.append(f'<text class="tick muted" x="{ML - 10}" y="{y + 4:.1f}" text-anchor="end">{t:,}</text>')
    out.append(f'<line class="axis" x1="{ML}" y1="{y0}" x2="{W - MR}" y2="{y0}" stroke-width="1"/>')
    for i, c in enumerate(xs):
        x = xpos(i, n)
        out.append(f'<text class="tick muted" x="{x:.1f}" y="{y0 + 20}" text-anchor="middle">{c}</text>')
    out.append(f'<text class="lbl muted" x="{(ML + W - MR) / 2:.0f}" y="{H - 14}" text-anchor="middle">동시 요청 수</text>')

    for si in range(n_series):
        pts = [(xpos(i, n), ypos(min(data[si][i][key], ymax))) for i in range(n)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path class="line s{si}" d="{d}"/>')
        for x, y in pts:
            out.append(f'<circle class="f{si}" cx="{x:.1f}" cy="{y:.1f}" r="4"/>')
        draw_series_label(out, pts[-1][0], pts[-1][1], f"f{si}", SERIES[si][0])

    out.append("</svg>")
    write(fname, out)


def fig_log(fname, title, subtitle, key, ylab, files, scenario, slo=None):
    import math

    n_series = len(files)
    data = [load_summaries(f, scenario) for f in files]
    xs = [s["concurrency"] for s in data[0]]
    n = len(xs)
    decades = [0.01, 0.1, 1, 10, 100]
    lo, hi = math.log10(decades[0]), math.log10(decades[-1])
    y0, y1 = H - MB, MT

    def ypos(v):
        v = max(v, decades[0])
        return y1 + (y0 - y1) * (1 - (math.log10(v) - lo) / (hi - lo))

    out = head(title, subtitle, [(i, SERIES[i][0]) for i in range(n_series)], ylab)
    for t in decades:
        y = ypos(t)
        out.append(f'<line class="grid" x1="{ML}" y1="{y:.1f}" x2="{W - MR}" y2="{y:.1f}" stroke-width="1"/>')
        lab = f"{t:g}"
        out.append(f'<text class="tick muted" x="{ML - 10}" y="{y + 4:.1f}" text-anchor="end">{lab}</text>')
    out.append(f'<line class="axis" x1="{ML}" y1="{y0}" x2="{W - MR}" y2="{y0}" stroke-width="1"/>')
    for i, c in enumerate(xs):
        x = xpos(i, n)
        out.append(f'<text class="tick muted" x="{x:.1f}" y="{y0 + 20}" text-anchor="middle">{c}</text>')
    out.append(f'<text class="lbl muted" x="{(ML + W - MR) / 2:.0f}" y="{H - 14}" text-anchor="middle">동시 요청 수</text>')

    if slo:
        y = ypos(slo)
        out.append(f'<line class="axis" x1="{ML}" y1="{y:.1f}" x2="{W - MR}" y2="{y:.1f}" stroke-width="1.5" stroke-dasharray="5 4"/>')
        # 오른쪽 끝은 계열 선들이 지나가므로 라벨은 왼쪽에 둔다
        out.append(f'<text class="lbl ink2" x="{ML + 6}" y="{y - 7:.1f}">TTFT SLO {slo}s</text>')

    for si in range(n_series):
        pts = [(xpos(i, n), ypos(data[si][i][key])) for i in range(n)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path class="line s{si}" d="{d}"/>')
        for x, y in pts:
            out.append(f'<circle class="f{si}" cx="{x:.1f}" cy="{y:.1f}" r="4"/>')

    # 끝점이 겹치지 않도록 라벨을 세로로 분리한다
    ends = sorted(
        ((data[si][-1][key], si) for si in range(n_series)), key=lambda t: -t[0]
    )
    for rank, (val, si) in enumerate(ends):
        y = ypos(val)
        draw_series_label(out, xpos(n - 1, n), y, f"f{si}", SERIES[si][0])

    out.append("</svg>")
    write(fname, out)


def fig_queue(fname):
    with open(os.path.join(RESULTS, "b2-prometheus.json"), encoding="utf-8") as f:
        d = json.load(f)
    run = d["series"]["vllm:num_requests_running"]
    wait = d["series"]["vllm:num_requests_waiting"]
    ts = run["t_offset_s"]
    n = len(ts)
    ymax = 60
    y0, y1 = H - MB, MT

    def ypos(v):
        return y1 + (y0 - y1) * (1 - v / ymax)

    def xp(i):
        return ML + (W - ML - MR) * (i / (n - 1))

    out = head(
        "서버 측 큐 관측 — 처리 중인 요청과 대기 중인 요청",
        "vLLM 내부 지표 · slots=16 고정 · 동시성 4 → 16 → 64 · 10초 간격",
        [(0, "처리 중 (running)"), (1, "대기 중 (waiting)")],
        "요청 수",
    )
    for t in range(0, ymax + 1, 10):
        y = ypos(t)
        out.append(f'<line class="grid" x1="{ML}" y1="{y:.1f}" x2="{W - MR}" y2="{y:.1f}" stroke-width="1"/>')
        out.append(f'<text class="tick muted" x="{ML - 10}" y="{y + 4:.1f}" text-anchor="end">{t}</text>')
    out.append(f'<line class="axis" x1="{ML}" y1="{y0}" x2="{W - MR}" y2="{y0}" stroke-width="1"/>')
    for i in range(0, n, 6):
        out.append(f'<text class="tick muted" x="{xp(i):.1f}" y="{y0 + 20}" text-anchor="middle">{ts[i]}</text>')
    out.append(f'<text class="lbl muted" x="{(ML + W - MR) / 2:.0f}" y="{H - 14}" text-anchor="middle">B2 시작 이후 경과 (초)</text>')

    # 슬롯 천장
    y16 = ypos(16)
    out.append(f'<line class="axis" x1="{ML}" y1="{y16:.1f}" x2="{W - MR}" y2="{y16:.1f}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<text class="lbl ink2" x="{ML + 6}" y="{y16 - 7:.1f}">max-num-seqs = 16</text>')

    # 직접 라벨은 짧게 — 전체 이름은 위 범례가 나른다
    for si, (series, name) in enumerate(((run, "running"), (wait, "waiting"))):
        cls = 0 if si == 0 else 1
        pts = [(xp(i), ypos(min(series["values"][i], ymax))) for i in range(n)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path class="line s{cls}" d="{d}"/>')
        draw_series_label(out, pts[-1][0], pts[-1][1], f"f{cls}", name, dy=(-10 if si else 10))

    out.append("</svg>")
    write(fname, out)


def write(fname, lines):
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  ✓ articles/figures/{fname}")


def main():
    short = [f"b1-slots-{s}-short.json" for s in SLOTS]
    print("생성:")
    fig_linear(
        "fig-b1-throughput.svg",
        "슬롯 수에 따른 처리량 변화",
        "Qwen2.5-1.5B-Instruct · vLLM v0.23.0 · RTX 4080 Laptop · short 시나리오 · 각 지점 100요청 1회",
        "output_tok_per_s", "처리량 (tok/s)", [0, 500, 1000, 1500, 2000, 2500, 3000],
        short, "short",
    )
    fig_log(
        "fig-b1-ttft.svg",
        "처리 한도를 넘었을 때의 TTFT",
        "같은 측정의 TTFT p95 (로그 눈금) · 처리량 증가가 멈추는 지점에서 급증한다",
        "ttft_p95_s", "TTFT p95 (초, 로그)",
        short, "short", slo=0.5,
    )
    fig_queue("fig-b2-queue.svg")


if __name__ == "__main__":
    main()
