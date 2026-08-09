#!/usr/bin/env python3
"""benchmark.py 결과 JSON들을 시나리오 문서에 붙일 마크다운 표로 바꾼다.

실습에서 채워야 할 표가 8개다. 손으로 옮기면 반드시 어딘가 틀리므로 결과 파일에서
직접 뽑는다. 네트워크·GPU를 쓰지 않고 JSON만 읽는다.

    # B1 — 슬롯별 처리량 (행=동시성, 열=슬롯)
    python3 summarize_results.py results/b1-slots-*-short.json \\
        --label-regex 'slots-(\\d+)' --label-format 'slots={}' --metric output_tok_per_s

    # B1 — 세 표를 한 번에
    python3 summarize_results.py results/b1-slots-*-short.json \\
        --label-regex 'slots-(\\d+)' --label-format 'slots={}' --all

    # B1 — 파레토 곡선용 점 목록 (처리량 vs TTFT p95)
    python3 summarize_results.py results/b1-slots-*-short.json \\
        --label-regex 'slots-(\\d+)' --label-format 'slots={}' --pareto --ttft-slo 0.5

    # C1 — 엔드포인트별 (라벨은 meta.endpoint에서 자동)
    python3 summarize_results.py results/c1-bs4-*.json --metric output_tok_per_s
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

METRICS = {
    "output_tok_per_s": ("처리량 (tok/s)", 1),
    "ttft_p50_s": ("TTFT p50 (s)", 3),
    "ttft_p95_s": ("TTFT p95 (s)", 3),
    "itl_p50_s": ("ITL p50 (s) — 토큰 간 간격", 4),
    "itl_p95_s": ("ITL p95 (s)", 4),
    "perceived_tps": ("perceived TPS (사용자별)", 1),
    "e2e_p50_s": ("E2E p50 (s)", 3),
    "e2e_p95_s": ("E2E p95 (s)", 3),
    "goodput_pct": ("goodput (%)", 1),
}

# --all이 찍는 표 묶음. 시나리오 문서 B1/C1의 "관측 — 채울 표"와 같은 순서다.
ALL_METRICS = ("output_tok_per_s", "ttft_p95_s", "goodput_pct")


def derive_label(path: Path, meta: dict[str, Any],
                 label_regex: str | None, label_format: str) -> str:
    """결과 파일 하나의 열 이름을 정한다.

    우선순위: --label-regex(파일명에서 추출) → meta.endpoint(교재 API) → 파일 stem.
    """
    if label_regex:
        match = re.search(label_regex, path.name)
        if match:
            captured = match.group(1) if match.groups() else match.group(0)
            return label_format.format(captured)
    endpoint = meta.get("endpoint")
    if endpoint:
        return str(endpoint).lstrip("/")
    return path.stem


def load_summaries(paths: list[Path], label_regex: str | None = None,
                   label_format: str = "{}") -> list[dict[str, Any]]:
    """결과 JSON들을 읽어 summary 레코드에 label을 붙여 펼친다."""
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload.get("meta", {})
        label = derive_label(path, meta, label_regex, label_format)
        for summary in payload.get("summaries", []):
            record = dict(summary)
            record["label"] = label
            record["source"] = path.name
            records.append(record)
    return records


def pivot(records: list[dict[str, Any]], metric: str,
          scenario: str | None = None) -> tuple[list[str], list[int], dict]:
    """행=동시성, 열=label 로 접는다. 열 순서는 처음 등장한 순서를 지킨다."""
    if metric not in METRICS:
        raise ValueError(f"알 수 없는 지표: {metric} (가능: {', '.join(METRICS)})")
    rows = [r for r in records if scenario is None or r.get("scenario") == scenario]
    labels: list[str] = []
    for record in rows:
        if record["label"] not in labels:
            labels.append(record["label"])
    concurrencies = sorted({int(r["concurrency"]) for r in rows})
    cells = {(r["label"], int(r["concurrency"])): r.get(metric) for r in rows}
    return labels, concurrencies, cells


def fmt_cell(value: Any, digits: int) -> str:
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def render_markdown(records: list[dict[str, Any]], metric: str,
                    scenario: str | None = None, delta: bool = False) -> str:
    """행=동시성, 열=label 표를 만든다.

    delta=True이고 열이 정확히 2개면 `차이`·`차이 %` 열을 붙인다. 계층 오버헤드
    (직접 vLLM vs Ray Serve로 감싼 vLLM)처럼 두 구성을 나란히 볼 때 쓴다.
    """
    labels, concurrencies, cells = pivot(records, metric, scenario)
    if not labels:
        return "(해당하는 결과가 없습니다)"
    title, digits = METRICS[metric]
    scenario_note = f", `{scenario}` 시나리오" if scenario else ""
    show_delta = delta and len(labels) == 2
    header = list(labels) + (["차이", "차이 %"] if show_delta else [])
    lines = [
        f"**{title}{scenario_note}**",
        "",
        "| 동시성 | " + " | ".join(header) + " |",
        "|---|" + "---|" * len(header),
    ]
    for concurrency in concurrencies:
        raw = [cells.get((label, concurrency)) for label in labels]
        cell_values = [fmt_cell(value, digits) for value in raw]
        if show_delta:
            base, other = raw[0], raw[1]
            if base is None or other is None:
                cell_values += ["-", "-"]
            else:
                diff = other - base
                cell_values += [
                    f"{diff:+.{digits}f}",
                    f"{diff / base * 100:+.1f}%" if base else "-",
                ]
        lines.append(f"| {concurrency} | " + " | ".join(cell_values) + " |")
    if delta and len(labels) != 2:
        lines += ["", f"> ⚠️ `--delta`는 열이 정확히 2개일 때만 차이를 냅니다 (현재 {len(labels)}개)."]
    return "\n".join(lines)


def pareto_rows(records: list[dict[str, Any]], ttft_slo_s: float,
                scenario: str | None = None) -> list[dict[str, Any]]:
    """처리량 vs TTFT p95 산점도용 점 목록. SLO 충족 여부와 파레토 최적을 표시한다.

    파레토 최적 = 자기보다 처리량이 높으면서 TTFT도 낮은 점이 하나도 없는 점.
    """
    rows = [r for r in records if scenario is None or r.get("scenario") == scenario]
    points = [
        {
            "label": r["label"],
            "concurrency": int(r["concurrency"]),
            "throughput": r.get("output_tok_per_s"),
            "ttft_p95": r.get("ttft_p95_s"),
            "goodput_pct": r.get("goodput_pct"),
        }
        for r in rows
        if r.get("output_tok_per_s") is not None and r.get("ttft_p95_s") is not None
    ]
    for point in points:
        point["meets_slo"] = point["ttft_p95"] <= ttft_slo_s
        point["pareto"] = not any(
            other["throughput"] > point["throughput"]
            and other["ttft_p95"] < point["ttft_p95"]
            for other in points
        )
    points.sort(key=lambda p: (-p["throughput"], p["ttft_p95"]))
    return points


def render_pareto(points: list[dict[str, Any]], ttft_slo_s: float) -> str:
    if not points:
        return "(처리량·TTFT가 모두 있는 결과가 없습니다)"
    lines = [
        f"**파레토 — 처리량 vs TTFT p95** (TTFT SLO {ttft_slo_s}s)",
        "",
        "| 구성 | 동시성 | 처리량 (tok/s) | TTFT p95 (s) | goodput (%) | SLO | 파레토 |",
        "|---|---|---|---|---|---|---|",
    ]
    for point in points:
        lines.append(
            f"| {point['label']} | {point['concurrency']} | "
            f"{point['throughput']:.1f} | {point['ttft_p95']:.3f} | "
            f"{fmt_cell(point['goodput_pct'], 1)} | "
            f"{'✅' if point['meets_slo'] else '❌'} | "
            f"{'★' if point['pareto'] else ''} |"
        )
    feasible = [p for p in points if p["meets_slo"]]
    if feasible:
        best = max(feasible, key=lambda p: p["throughput"])
        lines += [
            "",
            f"> SLO를 지키면서 낼 수 있는 최대 처리량: **{best['throughput']:.1f} tok/s** "
            f"({best['label']}, 동시성 {best['concurrency']}, "
            f"TTFT p95 {best['ttft_p95']:.3f}s)",
        ]
    else:
        lines += ["", "> ⚠️ TTFT SLO를 만족하는 구성이 하나도 없습니다."]
    return "\n".join(lines)


def formula_rows(records: list[dict[str, Any]],
                 scenario: str | None = None) -> list[dict[str, Any]]:
    """교재 CH4의 지연 공식이 실제로 성립하는지 검증한다.

        E2E latency = TTFT + ITL × (N - 1)

    이 식은 **모델 실행 시간만** 설명한다. 교재는 실제 E2E에 "요청 대기(대량 요청
    처리 시), 네트워크 지연, 라우팅 시간, 확장 오버헤드"가 더해진다고 말한다.
    따라서 남는 차이(residual)가 곧 **모델 밖에서 쓰인 시간**이다.

        residual = 측정된 E2E − (TTFT + ITL × (N-1))

    동시성을 올릴수록 residual이 커지면 그게 큐 대기의 증거다. Prometheus 없이
    클라이언트 측정만으로 확인할 수 있다.
    """
    rows = [r for r in records if scenario is None or r.get("scenario") == scenario]
    out: list[dict[str, Any]] = []
    for record in rows:
        ttft = record.get("ttft_p50_s")
        itl = record.get("itl_p50_s")
        e2e = record.get("e2e_p50_s")
        successes = record.get("successes") or 0
        tokens = record.get("output_tokens") or 0
        if ttft is None or itl is None or e2e is None or not successes:
            continue
        tokens_per_request = tokens / successes
        if tokens_per_request < 2:
            continue
        predicted = ttft + itl * (tokens_per_request - 1)
        out.append({
            "label": record["label"],
            "concurrency": int(record["concurrency"]),
            "tokens_per_request": tokens_per_request,
            "ttft_s": ttft,
            "itl_s": itl,
            "predicted_e2e_s": predicted,
            "measured_e2e_s": e2e,
            "residual_s": e2e - predicted,
            "residual_pct": (e2e - predicted) / e2e * 100 if e2e else None,
        })
    out.sort(key=lambda r: (r["label"], r["concurrency"]))
    return out


def render_formula(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(TTFT·ITL·E2E가 모두 있는 결과가 없습니다 — 스트리밍 측정이어야 합니다)"
    lines = [
        "**지연 공식 검증** — 교재 CH4: `E2E = TTFT + ITL × (N-1)`",
        "",
        "| 구성 | 동시성 | N(토큰/요청) | TTFT (s) | ITL (s) | 공식 예측 E2E | 실측 E2E | 차이 | 차이 비율 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['concurrency']} | {row['tokens_per_request']:.1f} | "
            f"{row['ttft_s']:.3f} | {row['itl_s']:.4f} | "
            f"{row['predicted_e2e_s']:.3f} | {row['measured_e2e_s']:.3f} | "
            f"{row['residual_s']:+.3f} | {fmt_cell(row['residual_pct'], 1)}% |"
        )
    lines += [
        "",
        "> 공식은 **모델 실행 시간만** 설명합니다. 남는 차이는 교재가 말한 "
        "`요청 대기 + 네트워크 지연 + 라우팅 시간 + 확장 오버헤드`입니다. "
        "**동시성이 오를수록 차이가 커지면 그게 큐 대기의 증거**입니다.",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("results", nargs="+", type=Path, help="benchmark.py 결과 JSON")
    # default=None으로 두고 main()에서 해석한다 — --pareto만 줬을 때 기본 표가
    # 딸려 나오지 않게 하려면 "명시했는지"를 알아야 한다.
    parser.add_argument("--metric", choices=tuple(METRICS), default=None)
    parser.add_argument("--all", action="store_true",
                        help=f"표 3종을 한 번에 ({', '.join(ALL_METRICS)})")
    parser.add_argument("--pareto", action="store_true",
                        help="처리량 vs TTFT p95 점 목록")
    parser.add_argument("--formula", action="store_true",
                        help="교재 CH4의 E2E = TTFT + ITL×(N-1) 검증 (잔차 = 큐+네트워크)")
    parser.add_argument("--delta", action="store_true",
                        help="열이 2개일 때 차이·차이%% 열 추가 (계층 오버헤드 비교용)")
    parser.add_argument("--ttft-slo", type=float, default=0.5)
    parser.add_argument("--scenario", help="short/prefill/decode 중 하나만 추림")
    parser.add_argument("--label-regex",
                        help=r"파일명에서 열 이름을 뽑는 정규식 (예: 'slots-(\d+)')")
    parser.add_argument("--label-format", default="{}",
                        help="추출한 값을 감쌀 형식 (예: 'slots={}')")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    missing = [str(path) for path in args.results if not path.exists()]
    if missing:
        print(f"파일을 찾을 수 없습니다: {', '.join(missing)}", file=sys.stderr)
        return 1

    records = load_summaries(args.results, args.label_regex, args.label_format)
    if not records:
        print("결과 JSON에 summaries가 없습니다.", file=sys.stderr)
        return 1

    blocks: list[str] = []
    if args.all:
        metrics: tuple[str, ...] = ALL_METRICS
    elif args.metric:
        metrics = (args.metric,)
    elif args.pareto or args.formula:
        metrics = ()          # 전용 표만 요청했으면 기본 표는 내지 않는다
    else:
        metrics = ("output_tok_per_s",)
    for metric in metrics:
        blocks.append(render_markdown(records, metric, args.scenario, args.delta))
    if args.pareto:
        blocks.append(
            render_pareto(pareto_rows(records, args.ttft_slo, args.scenario),
                          args.ttft_slo)
        )
    if args.formula:
        blocks.append(render_formula(formula_rows(records, args.scenario)))
    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
