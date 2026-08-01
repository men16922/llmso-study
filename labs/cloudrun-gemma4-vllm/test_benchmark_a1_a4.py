#!/usr/bin/env python3

import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("benchmark_a1_a4.py")
SPEC = importlib.util.spec_from_file_location("cloudrun_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        if payload.get("stream_options") != {"include_usage": True}:
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        events = [
            {"choices": [{"delta": {"role": "assistant", "content": ""}}]},
            {"choices": [{"delta": {"reasoning_content": "생각"}}]},
            {"choices": [{"delta": {"content": "답변"}}]},
            {"choices": [], "usage": {"completion_tokens": 5}},
        ]
        for event in events:
            time.sleep(0.003)
            self.wfile.write(
                f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
            )
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class CloudRunBenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_ttft_starts_at_first_generated_fragment_and_usage_is_exact(self):
        result = benchmark.make_streaming_request(
            url=self.url,
            token="test-token",
            model="mock-model",
            messages=[{"role": "user", "content": "테스트"}],
            max_tokens=8,
            experiment="test",
            scenario="stream",
            concurrency=1,
            request_id=0,
            timeout_s=2,
            enable_thinking=True,
        )
        self.assertTrue(result.ok)
        self.assertGreater(result.ttft_s, 0.004)
        self.assertEqual(result.output_tokens, 5)
        self.assertTrue(result.tokens_exact)

    def test_concurrency_limit_and_summary(self):
        async def run():
            return await benchmark.run_requests(
                url=self.url,
                token="test-token",
                model="mock-model",
                messages_factory=lambda _i: [{"role": "user", "content": "테스트"}],
                max_tokens=8,
                experiment="a4",
                scenario="goodput-capacity",
                concurrency=2,
                request_count=4,
                timeout_s=2,
                enable_thinking=False,
            )

        import asyncio

        results, wall_s = asyncio.run(run())
        summary = benchmark.summarize(results, wall_s, 1, 1)
        self.assertEqual(summary["successes"], 4)
        self.assertEqual(summary["output_tokens"], 20)
        self.assertEqual(summary["goodput_pct"], 100)
        self.assertEqual(summary["exact_usage_requests"], 4)

    def test_parser_covers_all_experiments_and_environment_project(self):
        with mock.patch.dict(os.environ, {"PROJECT_ID": "test-project"}):
            args = benchmark.build_parser().parse_args(["--exp", "a4"])
        self.assertEqual(args.exp, "a4")
        self.assertEqual(args.project, "test-project")

    def test_percentile_and_concurrency_parser(self):
        self.assertEqual(benchmark.percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(benchmark.parse_positive_ints("1,4,8"), [1, 4, 8])

    def test_smoke_cli_persists_raw_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "smoke.json"
            with mock.patch.object(benchmark, "identity_token", return_value="token"):
                exit_code = benchmark.main(
                    [
                        "--url",
                        self.url,
                        "--project",
                        "test-project",
                        "--exp",
                        "smoke",
                        "--skip-warmup",
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["requests"]), 1)
            self.assertEqual(len(payload["summaries"]), 1)
            self.assertEqual(payload["requests"][0]["output_tokens"], 5)

    def test_a2_and_a4_write_derived_decisions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(benchmark, "identity_token", return_value="token"):
                for experiment in ("a2", "a4"):
                    output = Path(temp_dir) / f"{experiment}.json"
                    exit_code = benchmark.main(
                        [
                            "--url",
                            self.url,
                            "--project",
                            "test-project",
                            "--exp",
                            experiment,
                            "--skip-warmup",
                            "--prefix-repeats",
                            "2",
                            "--concurrency",
                            "1,2",
                            "--requests-per-level",
                            "1",
                            "--output",
                            str(output),
                        ]
                    )
                    self.assertEqual(exit_code, 0)
                    payload = json.loads(output.read_text(encoding="utf-8"))
                    self.assertTrue(payload["derived"])
            a4 = json.loads((Path(temp_dir) / "a4.json").read_text(encoding="utf-8"))
            self.assertEqual(
                a4["derived"]["a4_capacity"]["max_concurrency_meeting_target"], 2
            )


if __name__ == "__main__":
    unittest.main()
