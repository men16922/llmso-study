#!/usr/bin/env python3

import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import benchmark


class MockOpenAIHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        body = json.dumps({"data": [{"id": "mock-model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        if not payload.get("stream"):
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for event in [
            {"choices": [{"delta": {"content": "안녕"}}]},
            {"choices": [{"delta": {"content": "하세요"}}]},
            {"choices": [], "usage": {"completion_tokens": 2}},
        ]:
            time.sleep(0.005)
            self.wfile.write(
                f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
            )
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class MockBookHandler(BaseHTTPRequestHandler):
    """교재 ch03 single_model_llm_serving 서버를 흉내낸다.

    핵심 재현 포인트 둘:
      - /generate·/basic_generate는 batch_decode 결과라 **프롬프트를 그대로 되돌려준다**
      - /generate_stream은 [DONE] 센티널 없이 연결을 그냥 닫는다
    """

    COMPLETION = " 하나 둘 셋"          # 생성분 = 3 단어
    STREAM_TOKENS = [" 하나", " 둘", " 셋"]

    def log_message(self, _format, *_args):
        return

    def _json(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))

        if self.path == "/generate_stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for token in self.STREAM_TOKENS:
                time.sleep(0.005)
                event = {"token": token, "sequence_id": "seq-1"}
                self.wfile.write(
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.flush()
            return  # [DONE] 없이 그냥 닫는다 — 교재 서버와 동일

        if self.path == "/basic_generate":
            prompt = payload["prompt"]
            self._json({"generated_text": prompt + self.COMPLETION})
            return

        if self.path in ("/generate", "/generate_vllm"):
            prompts = payload["prompts"]
            if self.path == "/generate":
                texts = [p + self.COMPLETION for p in prompts]   # 프롬프트 에코
            else:
                texts = [self.COMPLETION for _ in prompts]        # vLLM은 생성분만
            self._json({"generated_texts": texts})
            return

        self.send_error(404)


class BookApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockBookHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _one(self, endpoint):
        return benchmark.run_request(
            base_url=self.base_url,
            scenario_name="short",
            concurrency=1,
            request_id=0,
            timeout_s=5,
            api="book",
            endpoint=endpoint,
        )

    def test_streaming_endpoint_measures_ttft(self):
        result = self._one("/generate_stream")
        self.assertTrue(result.ok, result.error)
        ttft = result.ttft_s
        self.assertIsNotNone(ttft, "SSE 엔드포인트는 TTFT를 재야 한다")
        assert ttft is not None
        self.assertGreater(result.e2e_s, ttft)
        self.assertEqual(result.output_tokens, 3)

    def test_non_streaming_endpoints_have_no_ttft(self):
        for endpoint in ("/basic_generate", "/generate", "/generate_vllm"):
            with self.subTest(endpoint=endpoint):
                result = self._one(endpoint)
                self.assertTrue(result.ok, result.error)
                self.assertIsNone(
                    result.ttft_s, "비스트리밍 엔드포인트는 TTFT가 정의되지 않는다"
                )

    def test_prompt_echo_is_subtracted(self):
        """/generate는 프롬프트를 되돌려주므로 빼지 않으면 처리량이 부풀려진다."""
        echoed = self._one("/generate")
        clean = self._one("/generate_vllm")
        self.assertEqual(echoed.output_tokens, clean.output_tokens)
        self.assertEqual(clean.output_tokens, 3)

    def test_all_four_endpoints_count_the_same_way(self):
        counts = {ep: self._one(ep).output_tokens for ep in benchmark.BOOK_ENDPOINTS}
        self.assertEqual(
            set(counts.values()), {3}, f"엔드포인트 간 세는 방식이 어긋난다: {counts}"
        )

    def test_goodput_ignores_missing_ttft(self):
        results, wall_s = benchmark.run_group(
            base_url=self.base_url,
            scenario_name="short",
            concurrency=2,
            request_count=4,
            timeout_s=5,
            api="book",
            endpoint="/generate",
        )
        summary = benchmark.summarize_group(results, wall_s, ttft_slo_s=0.001, e2e_slo_s=30)
        self.assertEqual(summary["successes"], 4)
        self.assertFalse(summary["ttft_measured"])
        self.assertEqual(
            summary["goodput_pct"], 100,
            "TTFT가 없는 엔드포인트를 전부 SLO 위반으로 세면 안 된다",
        )

    def test_prompts_per_request_sends_a_list(self):
        """교재 서버의 배칭 축은 요청당 프롬프트 수다 (동시 요청 수가 아니라)."""
        result = benchmark.run_book_request(
            base_url=self.base_url,
            endpoint="/generate",
            scenario_name="short",
            concurrency=1,
            request_id=0,
            timeout_s=5,
            prompts_per_request=4,
        )
        self.assertTrue(result.ok, result.error)
        # 프롬프트 4개 → 생성분 4개(각 3단어). 에코된 프롬프트 4벌은 빠져야 한다.
        self.assertEqual(result.output_tokens, 12)

    def test_prompt_echo_subtracted_once_per_response(self):
        """에코 보정은 응답 개수만큼 빼야 한다 — 한 번만 빼면 과대계상된다."""
        one = benchmark.run_book_request(
            base_url=self.base_url, endpoint="/generate", scenario_name="short",
            concurrency=1, request_id=0, timeout_s=5, prompts_per_request=1,
        )
        four = benchmark.run_book_request(
            base_url=self.base_url, endpoint="/generate", scenario_name="short",
            concurrency=1, request_id=1, timeout_s=5, prompts_per_request=4,
        )
        self.assertEqual(four.output_tokens, one.output_tokens * 4)

    def test_single_prompt_endpoint_ignores_the_list(self):
        """/generate_stream은 프롬프트를 하나만 받는다 — 여러 개를 실을 수 없다."""
        result = benchmark.run_book_request(
            base_url=self.base_url,
            endpoint="/generate_stream",
            scenario_name="short",
            concurrency=1,
            request_id=0,
            timeout_s=5,
            prompts_per_request=4,
        )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output_tokens, 3)

    def test_zero_prompts_is_rejected(self):
        with self.assertRaises(ValueError):
            benchmark.run_book_request(
                base_url=self.base_url, endpoint="/generate", scenario_name="short",
                concurrency=1, request_id=0, timeout_s=5, prompts_per_request=0,
            )

    def test_prompts_per_request_recorded_in_meta(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = f"{temp_dir}/result.json"
            exit_code = benchmark.main([
                "--api", "book", "--endpoint", "/generate",
                "--base-url", self.base_url, "--scenarios", "short",
                "--concurrency", "1", "--requests-per-level", "2",
                "--warmup", "0", "--prompts-per-request", "4",
                "--output", output,
            ])
            self.assertEqual(exit_code, 0)
            payload = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["prompts_per_request"], 4)

    def test_unknown_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            benchmark.run_book_request(
                base_url=self.base_url,
                endpoint="/nope",
                scenario_name="short",
                concurrency=1,
                request_id=0,
                timeout_s=2,
            )

    def test_cli_records_api_and_batching_label(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = f"{temp_dir}/result.json"
            exit_code = benchmark.main(
                [
                    "--api", "book",
                    "--endpoint", "/generate_stream",
                    "--base-url", self.base_url,
                    "--scenarios", "short",
                    "--concurrency", "1,2",
                    "--requests-per-level", "2",
                    "--warmup", "1",
                    "--output", output,
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["api"], "book")
            self.assertEqual(payload["meta"]["endpoint"], "/generate_stream")
            self.assertEqual(payload["meta"]["batching"], "continuous-naive")
            self.assertEqual(len(payload["summaries"]), 2)

    def test_endpoint_without_book_api_is_rejected(self):
        exit_code = benchmark.main(
            [
                "--endpoint", "/generate",
                "--base-url", self.base_url,
                "--scenarios", "short",
                "--concurrency", "1",
                "--requests-per-level", "1",
                "--warmup", "0",
            ]
        )
        self.assertEqual(exit_code, 2)


class BenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockOpenAIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_discovers_model(self):
        self.assertEqual(
            benchmark.discover_model(self.base_url, None, 2), "mock-model"
        )

    def test_streaming_request_and_summary(self):
        results, wall_s = benchmark.run_group(
            base_url=self.base_url,
            api_key=None,
            model="mock-model",
            scenario_name="short",
            concurrency=2,
            request_count=4,
            timeout_s=2,
        )
        self.assertTrue(all(result.ok for result in results))
        self.assertTrue(all(result.output_tokens == 2 for result in results))
        self.assertTrue(all(result.tokens_exact for result in results))
        summary = benchmark.summarize_group(results, wall_s, 1, 1)
        self.assertEqual(summary["successes"], 4)
        self.assertEqual(summary["output_tokens"], 8)
        self.assertEqual(summary["goodput_pct"], 100)

    def test_unique_prefix_makes_each_prompt_distinct(self):
        base = benchmark.SCENARIOS["short"]["prompt"]

        # 기본값은 프롬프트를 그대로 쓴다 (기존 측정과의 호환).
        self.assertEqual(benchmark.build_prompt("short", False), base)

        prompts = {benchmark.build_prompt("short", True) for _ in range(20)}
        self.assertEqual(len(prompts), 20, "요청마다 프롬프트가 달라야 한다")
        for prompt in prompts:
            self.assertTrue(prompt.startswith("request-id="))
            self.assertTrue(prompt.endswith(base), "본문은 유지되어야 한다")

    def test_unique_prefix_flows_through_cli(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = f"{temp_dir}/result.json"
            exit_code = benchmark.main(
                [
                    "--base-url", self.base_url,
                    "--scenarios", "short",
                    "--concurrency", "1",
                    "--requests-per-level", "2",
                    "--warmup", "0",
                    "--unique-prefix",
                    "--output", output,
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertTrue(payload["meta"]["unique_prefix"])

    def test_itl_is_measured_on_streaming(self):
        result = benchmark.run_request(
            base_url=self.base_url,
            model="mock-model",
            scenario_name="short",
            concurrency=1,
            request_id=0,
            timeout_s=5,
        )
        self.assertTrue(result.ok, result.error)
        # mock은 토큰 2개를 5ms 간격으로 보낸다 → 간격은 1개.
        self.assertIsNotNone(result.itl_s)
        assert result.itl_s is not None
        self.assertGreater(result.itl_s, 0)

    def test_compute_itl_edge_cases(self):
        # 토큰 이벤트가 1개면 간격 자체가 없다.
        self.assertIsNone(benchmark.compute_itl(1.0, 1.0, 1))
        self.assertIsNone(benchmark.compute_itl(None, 2.0, 5))
        self.assertIsNone(benchmark.compute_itl(1.0, None, 5))
        # 1.0 → 2.0 사이에 이벤트 5개 = 간격 4개 = 0.25초
        self.assertAlmostEqual(benchmark.compute_itl(1.0, 2.0, 5), 0.25)

    def test_summary_reports_itl_and_perceived_tps(self):
        results, wall_s = benchmark.run_group(
            base_url=self.base_url,
            model="mock-model",
            scenario_name="short",
            concurrency=2,
            request_count=4,
            timeout_s=5,
        )
        summary = benchmark.summarize_group(results, wall_s, 5, 30)
        itl_p50 = summary["itl_p50_s"]
        perceived = summary["perceived_tps"]
        self.assertIsNotNone(itl_p50)
        self.assertIsNotNone(perceived)
        assert itl_p50 is not None and perceived is not None
        self.assertAlmostEqual(float(perceived), 1 / float(itl_p50), places=6)

    def test_percentile_interpolates(self):
        self.assertEqual(benchmark.percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertIsNone(benchmark.percentile([], 0.95))

    def test_cli_writes_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = f"{temp_dir}/result.json"
            exit_code = benchmark.main(
                [
                    "--base-url",
                    self.base_url,
                    "--scenarios",
                    "short",
                    "--concurrency",
                    "1,2",
                    "--requests-per-level",
                    "2",
                    "--warmup",
                    "0",
                    "--output",
                    output,
                ]
            )
            self.assertEqual(exit_code, 0)
            with open(output, encoding="utf-8") as result_file:
                payload = json.load(result_file)
            self.assertEqual(payload["meta"]["model"], "mock-model")
            self.assertEqual(len(payload["summaries"]), 2)


if __name__ == "__main__":
    unittest.main()
