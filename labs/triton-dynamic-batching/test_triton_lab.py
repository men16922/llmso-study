#!/usr/bin/env python3
"""C2 랩의 순수 로직 테스트 — 네트워크·GPU·Triton 없이 돈다.

tritonclient·torch가 없어도 통과해야 한다 (게이트가 오프라인이므로).
"""

import unittest

import make_config
import triton_load
import triton_metrics


class MakeConfigTest(unittest.TestCase):
    def test_off_omits_dynamic_batching_block(self):
        """대조군은 dynamic_batching 블록만 빠지고 모델 시그니처는 그대로여야 한다."""
        config = make_config.render_config("off")
        self.assertNotIn("dynamic_batching", config)
        self.assertIn("max_batch_size: 8", config)
        self.assertIn('name: "mobilenet_v2"', config)

    def test_control_group_keeps_the_same_model_signature(self):
        off = make_config.render_config("off")
        on = make_config.render_config(5000)
        # dynamic_batching 블록을 뺀 나머지가 완전히 같아야 공정한 대조군이다.
        self.assertTrue(on.startswith(off))

    def test_delay_is_rendered(self):
        config = make_config.render_config(5000)
        self.assertIn("dynamic_batching {", config)
        self.assertIn("max_queue_delay_microseconds: 5000", config)

    def test_zero_delay_still_enables_dynamic_batching(self):
        """delay=0도 '기다리지 않는 dynamic'이지 배칭 끔이 아니다."""
        config = make_config.render_config(0)
        self.assertIn("dynamic_batching {", config)
        self.assertIn("max_queue_delay_microseconds: 0", config)

    def test_batch_dimension_is_absent_from_dims(self):
        """max_batch_size > 0이면 dims에서 배치 차원을 빼야 한다 (Triton이 붙인다)."""
        config = make_config.render_config(1000)
        self.assertIn("dims: [ 3, 224, 224 ]", config)
        self.assertNotIn("dims: [ 1, 3, 224, 224 ]", config)
        self.assertNotIn("reshape", config)

    def test_negative_delay_is_rejected(self):
        with self.assertRaises(ValueError):
            make_config.render_config(-1)

    def test_cli_writes_config(self):
        self.assertEqual(make_config.main(["off"]), 0)
        self.assertEqual(make_config.main(["5000"]), 0)
        self.assertEqual(make_config.main(["-5"]), 2)


SNAPSHOT_BEFORE = """
# HELP nv_inference_request_success Number of successful inferences
# TYPE nv_inference_request_success counter
nv_inference_request_success{model="mobilenet_v2",version="1"} 100
nv_inference_exec_count{model="mobilenet_v2",version="1"} 100
nv_inference_queue_duration_us{model="mobilenet_v2",version="1"} 1000
nv_inference_compute_infer_duration_us{model="mobilenet_v2",version="1"} 50000
nv_inference_request_success{model="other_model",version="1"} 7
nv_inference_exec_count{model="other_model",version="1"} 7
"""

# 이 구간에서 요청 600개가 실행 100회로 처리됐다 → 평균 배치 크기 6.00
SNAPSHOT_AFTER = """
nv_inference_request_success{model="mobilenet_v2",version="1"} 700
nv_inference_exec_count{model="mobilenet_v2",version="1"} 200
nv_inference_queue_duration_us{model="mobilenet_v2",version="1"} 3001000
nv_inference_compute_infer_duration_us{model="mobilenet_v2",version="1"} 1250000
nv_inference_request_success{model="other_model",version="1"} 999
nv_inference_exec_count{model="other_model",version="1"} 999
"""


class TritonMetricsTest(unittest.TestCase):
    def _stats(self, model="mobilenet_v2"):
        before = triton_metrics.parse_metrics(SNAPSHOT_BEFORE, model)
        after = triton_metrics.parse_metrics(SNAPSHOT_AFTER, model)
        return triton_metrics.batch_stats(triton_metrics.delta(before, after))

    def test_parses_only_the_requested_model(self):
        parsed = triton_metrics.parse_metrics(SNAPSHOT_BEFORE, "mobilenet_v2")
        self.assertEqual(parsed["nv_inference_request_success"], 100)
        self.assertEqual(parsed["nv_inference_exec_count"], 100)

    def test_average_batch_size_from_interval(self):
        stats = self._stats()
        self.assertEqual(stats["requests"], 600)
        self.assertEqual(stats["executions"], 100)
        self.assertAlmostEqual(stats["avg_batch_size"], 6.0)

    def test_other_models_do_not_leak_in(self):
        """다른 모델의 카운터가 섞이면 평균 배치 크기가 통째로 틀어진다."""
        stats = self._stats()
        self.assertEqual(stats["requests"], 600, "other_model이 섞이면 안 된다")

    def test_queue_and_compute_per_request(self):
        stats = self._stats()
        # 큐 3,000,000us ÷ 600요청 = 5000us = 5ms — 설정한 max_queue_delay와 일치
        self.assertAlmostEqual(stats["queue_ms_per_request"], 5.0)
        self.assertAlmostEqual(stats["compute_ms_per_request"], 2.0)

    def test_no_executions_gives_none_not_crash(self):
        stats = triton_metrics.batch_stats(
            {name: 0.0 for name in triton_metrics.COUNTERS}
        )
        self.assertIsNone(stats["avg_batch_size"])
        self.assertIsNone(stats["queue_ms_per_request"])

    def test_counter_reset_is_clamped(self):
        """서버를 재시작하면 카운터가 줄어든다 — 음수 차분을 내면 안 된다."""
        interval = triton_metrics.delta(
            {"nv_inference_request_success": 500.0},
            {"nv_inference_request_success": 10.0},
        )
        self.assertEqual(interval["nv_inference_request_success"], 0.0)

    def test_render_is_readable_without_data(self):
        text = triton_metrics.render(
            triton_metrics.batch_stats({name: 0.0 for name in triton_metrics.COUNTERS})
        )
        self.assertIn("평균 배치 크기 -", text)


class TritonLoadTest(unittest.TestCase):
    def test_percentile_matches_benchmark_convention(self):
        # benchmark.py와 같은 선형보간이어야 두 랩의 숫자를 같은 기준으로 읽는다.
        self.assertEqual(triton_load.percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertIsNone(triton_load.percentile([], 0.95))

    def test_summarize_computes_throughput(self):
        summary = triton_load.summarize([0.01] * 100, wall_s=2.0, concurrency=8)
        self.assertEqual(summary["requests"], 100)
        self.assertEqual(summary["inf_per_s"], 50.0)
        self.assertAlmostEqual(summary["p50_ms"], 10.0)

    def test_summarize_handles_empty(self):
        summary = triton_load.summarize([], wall_s=1.0, concurrency=1, failures=3)
        self.assertIsNone(summary["p50_ms"])
        self.assertEqual(summary["failures"], 3)
        self.assertEqual(summary["requests"], 3)

    def test_run_level_counts_failures_without_dying(self):
        calls = {"n": 0}

        def flaky() -> float:
            calls["n"] += 1
            if calls["n"] % 3 == 0:
                raise RuntimeError("boom")
            return 0.005

        summary = triton_load.run_level(flaky, concurrency=2, requests=9, warmup=0)
        self.assertEqual(summary["requests"], 9)
        self.assertEqual(summary["failures"], 3)

    def test_parse_concurrency_rejects_bad_input(self):
        self.assertEqual(triton_load.parse_concurrency("1,8,32"), [1, 8, 32])
        with self.assertRaises(Exception):
            triton_load.parse_concurrency("0,8")


if __name__ == "__main__":
    unittest.main()
