#!/usr/bin/env python3
"""summarize_results.py 테스트 — 결과 JSON만 읽으므로 완전 오프라인이다."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import summarize_results as sr


def make_result(path: Path, summaries: list[dict], meta: dict | None = None) -> Path:
    path.write_text(
        json.dumps({"meta": meta or {}, "summaries": summaries}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def row(concurrency: int, tput: float, ttft: float, **extra) -> dict:
    base = {
        "scenario": "short",
        "concurrency": concurrency,
        "output_tok_per_s": tput,
        "ttft_p95_s": ttft,
        "ttft_p50_s": ttft * 0.8,
        "itl_p50_s": 0.010,
        "goodput_pct": 100.0,
        "e2e_p50_s": 0.9,
        "e2e_p95_s": 1.0,
        "successes": 10,
        "output_tokens": 640,     # N = 64 토큰/요청
    }
    base.update(extra)
    return base


class LabelTest(unittest.TestCase):
    def test_regex_label_beats_everything(self):
        label = sr.derive_label(
            Path("b1-slots-16-short.json"), {"endpoint": "/generate"},
            r"slots-(\d+)", "slots={}",
        )
        self.assertEqual(label, "slots=16")

    def test_endpoint_label_for_book_api(self):
        label = sr.derive_label(
            Path("c1-bs4-generate_stream.json"), {"endpoint": "/generate_stream"},
            None, "{}",
        )
        self.assertEqual(label, "generate_stream")

    def test_falls_back_to_filename(self):
        label = sr.derive_label(Path("whatever.json"), {}, None, "{}")
        self.assertEqual(label, "whatever")

    def test_non_matching_regex_falls_through(self):
        label = sr.derive_label(
            Path("nomatch.json"), {"endpoint": "/generate"}, r"slots-(\d+)", "slots={}"
        )
        self.assertEqual(label, "generate")


class PivotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.paths = [
            make_result(root / "b1-slots-1-short.json",
                        [row(1, 40, 0.05), row(8, 40, 3.2)]),
            make_result(root / "b1-slots-16-short.json",
                        [row(1, 40, 0.05), row(8, 320, 0.05)]),
        ]

    def tearDown(self):
        self.temp.cleanup()

    def _records(self):
        return sr.load_summaries(self.paths, r"slots-(\d+)", "slots={}")

    def test_column_order_follows_first_appearance(self):
        labels, concurrencies, _ = sr.pivot(self._records(), "output_tok_per_s")
        self.assertEqual(labels, ["slots=1", "slots=16"])
        self.assertEqual(concurrencies, [1, 8])

    def test_markdown_has_one_column_per_file(self):
        table = sr.render_markdown(self._records(), "output_tok_per_s")
        self.assertIn("| 동시성 | slots=1 | slots=16 |", table)
        self.assertIn("| 8 | 40.0 | 320.0 |", table)

    def test_missing_cell_renders_as_dash(self):
        records = self._records()
        records = [r for r in records
                   if not (r["label"] == "slots=16" and r["concurrency"] == 8)]
        self.assertIn("| 8 | 40.0 | - |", sr.render_markdown(records, "output_tok_per_s"))

    def test_unknown_metric_is_rejected(self):
        with self.assertRaises(ValueError):
            sr.pivot(self._records(), "nope")

    def test_scenario_filter(self):
        records = self._records()
        table = sr.render_markdown(records, "output_tok_per_s", scenario="decode")
        self.assertIn("해당하는 결과가 없습니다", table)


class DeltaTest(unittest.TestCase):
    """계층 오버헤드 비교 — 직접 vLLM(B1) vs Ray Serve로 감싼 vLLM(C3)."""

    def _records(self, direct: float = 100.0, wrapped: float = 90.0):
        return [
            {"label": "직접 vLLM", "concurrency": 8, "scenario": "short",
             "output_tok_per_s": direct},
            {"label": "Ray Serve", "concurrency": 8, "scenario": "short",
             "output_tok_per_s": wrapped},
        ]

    def test_delta_columns_are_added_for_two_labels(self):
        table = sr.render_markdown(
            self._records(), "output_tok_per_s", delta=True
        )
        self.assertIn("| 동시성 | 직접 vLLM | Ray Serve | 차이 | 차이 % |", table)
        # 90 − 100 = −10 → −10.0%
        self.assertIn("| 8 | 100.0 | 90.0 | -10.0 | -10.0% |", table)

    def test_positive_delta_is_signed(self):
        table = sr.render_markdown(
            self._records(wrapped=110.0), "output_tok_per_s", delta=True
        )
        self.assertIn("+10.0", table)
        self.assertIn("+10.0%", table)

    def test_delta_warns_when_not_exactly_two_columns(self):
        records = self._records() + [
            {"label": "제3자", "concurrency": 8, "scenario": "short",
             "output_tok_per_s": 50.0}
        ]
        table = sr.render_markdown(records, "output_tok_per_s", delta=True)
        self.assertIn("정확히 2개일 때만", table)
        self.assertNotIn("| 차이 |", table)

    def test_missing_cell_does_not_crash(self):
        records = [
            {"label": "a", "concurrency": 8, "scenario": "short",
             "output_tok_per_s": 100.0},
            {"label": "b", "concurrency": 16, "scenario": "short",
             "output_tok_per_s": 90.0},
        ]
        table = sr.render_markdown(records, "output_tok_per_s", delta=True)
        self.assertIn("| 8 | 100.0 | - | - | - |", table)

    def test_delta_off_by_default(self):
        table = sr.render_markdown(self._records(), "output_tok_per_s")
        self.assertNotIn("차이", table)


class ParetoTest(unittest.TestCase):
    def _points(self, ttft_slo=0.5):
        records = [
            {"label": "a", "concurrency": 1, "scenario": "short",
             "output_tok_per_s": 100.0, "ttft_p95_s": 0.10, "goodput_pct": 100.0},
            # 지배당하는 점: 처리량은 낮고 TTFT는 높다
            {"label": "b", "concurrency": 2, "scenario": "short",
             "output_tok_per_s": 50.0, "ttft_p95_s": 0.20, "goodput_pct": 100.0},
            # SLO 위반이지만 처리량은 최고
            {"label": "c", "concurrency": 4, "scenario": "short",
             "output_tok_per_s": 400.0, "ttft_p95_s": 3.00, "goodput_pct": 20.0},
        ]
        return sr.pareto_rows(records, ttft_slo)

    def test_dominated_point_is_not_pareto(self):
        points = {p["label"]: p for p in self._points()}
        self.assertFalse(points["b"]["pareto"], "a에 완전히 지배당하는 점")
        self.assertTrue(points["a"]["pareto"])
        self.assertTrue(points["c"]["pareto"], "처리량 최고면 지배당하지 않는다")

    def test_slo_flag(self):
        points = {p["label"]: p for p in self._points()}
        self.assertTrue(points["a"]["meets_slo"])
        self.assertFalse(points["c"]["meets_slo"])

    def test_sorted_by_throughput_desc(self):
        self.assertEqual([p["label"] for p in self._points()], ["c", "a", "b"])

    def test_best_feasible_excludes_slo_violators(self):
        text = sr.render_pareto(self._points(), 0.5)
        # 400 tok/s는 SLO 위반이므로 "최대 처리량"이 될 수 없다
        self.assertIn("100.0 tok/s", text)
        self.assertNotIn("400.0 tok/s**", text)

    def test_warns_when_nothing_meets_slo(self):
        text = sr.render_pareto(self._points(ttft_slo=0.01), 0.01)
        self.assertIn("만족하는 구성이 하나도 없습니다", text)

    def test_points_without_ttft_are_dropped(self):
        """비스트리밍 엔드포인트(TTFT=None)는 파레토에 못 올린다."""
        points = sr.pareto_rows(
            [{"label": "x", "concurrency": 1, "output_tok_per_s": 10.0,
              "ttft_p95_s": None}], 0.5
        )
        self.assertEqual(points, [])


class FormulaTest(unittest.TestCase):
    """교재 CH4의 E2E = TTFT + ITL × (N-1) 검증 로직."""

    def _record(self, **overrides):
        base = {
            "label": "slots=16", "concurrency": 8, "scenario": "short",
            "ttft_p50_s": 0.100, "itl_p50_s": 0.010, "e2e_p50_s": 0.800,
            "successes": 10, "output_tokens": 500,   # N = 50
        }
        base.update(overrides)
        return base

    def test_predicted_matches_the_textbook_formula(self):
        rows = sr.formula_rows([self._record()])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertAlmostEqual(row["tokens_per_request"], 50.0)
        # 0.100 + 0.010 × 49 = 0.590
        self.assertAlmostEqual(row["predicted_e2e_s"], 0.590)

    def test_residual_is_time_outside_the_model(self):
        row = sr.formula_rows([self._record()])[0]
        # 0.800 − 0.590 = 0.210 → 큐 대기 + 네트워크
        self.assertAlmostEqual(row["residual_s"], 0.210)
        self.assertAlmostEqual(row["residual_pct"], 26.25)

    def test_residual_grows_with_concurrency(self):
        """동시성이 오를수록 잔차가 커지면 큐 대기의 증거다."""
        rows = sr.formula_rows([
            self._record(concurrency=1, e2e_p50_s=0.60),
            self._record(concurrency=32, e2e_p50_s=1.60),
        ])
        residuals = {r["concurrency"]: r["residual_s"] for r in rows}
        self.assertLess(residuals[1], residuals[32])
        self.assertAlmostEqual(residuals[1], 0.010, places=3)

    def test_non_streaming_records_are_skipped(self):
        """ITL이 없는(비스트리밍) 결과는 공식을 적용할 수 없다."""
        self.assertEqual(sr.formula_rows([self._record(itl_p50_s=None)]), [])
        self.assertEqual(sr.formula_rows([self._record(ttft_p50_s=None)]), [])

    def test_single_token_response_is_skipped(self):
        """토큰이 1개면 ITL 항이 성립하지 않는다."""
        self.assertEqual(
            sr.formula_rows([self._record(output_tokens=10, successes=10)]), []
        )

    def test_zero_successes_does_not_divide_by_zero(self):
        self.assertEqual(sr.formula_rows([self._record(successes=0)]), [])

    def test_render_mentions_the_formula(self):
        text = sr.render_formula(sr.formula_rows([self._record()]))
        self.assertIn("E2E = TTFT + ITL × (N-1)", text)
        self.assertIn("큐 대기의 증거", text)

    def test_render_handles_empty(self):
        self.assertIn("스트리밍 측정이어야", sr.render_formula([]))


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.path = make_result(root / "b1-slots-16-short.json",
                                [row(1, 40, 0.05), row(8, 320, 0.05)])

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, args) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = sr.main(args)
        return code, buffer.getvalue()

    def test_pareto_alone_prints_only_pareto(self):
        code, text = self._run([str(self.path), "--pareto"])
        self.assertEqual(code, 0)
        self.assertIn("파레토 —", text)
        self.assertNotIn("**처리량 (tok/s)**", text)

    def test_metric_with_pareto_prints_both(self):
        _, text = self._run(
            [str(self.path), "--pareto", "--metric", "output_tok_per_s"]
        )
        self.assertIn("파레토 —", text)
        self.assertIn("**처리량 (tok/s)**", text)

    def test_default_prints_throughput(self):
        _, text = self._run([str(self.path)])
        self.assertIn("**처리량 (tok/s)**", text)

    def test_all_prints_three_tables(self):
        _, text = self._run([str(self.path), "--all"])
        for metric in sr.ALL_METRICS:
            self.assertIn(sr.METRICS[metric][0], text)

    def test_missing_file_is_reported(self):
        code, _ = self._run(["/nonexistent/nope.json"])
        self.assertEqual(code, 1)

    def test_formula_alone_prints_only_formula(self):
        code, text = self._run([str(self.path), "--formula"])
        self.assertEqual(code, 0)
        self.assertNotIn("**처리량 (tok/s)**", text)
        self.assertIn("지연 공식 검증", text)


if __name__ == "__main__":
    unittest.main()
