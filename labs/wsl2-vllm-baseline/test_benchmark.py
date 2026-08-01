#!/usr/bin/env python3

import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
