#!/usr/bin/env python3
"""C3 랩의 순수 로직 테스트 — ray·torch 없이 돈다.

`mobilenet_serve.py`는 import 시점에 ray를 요구하지 않도록 만들어져 있다
(`build_app()` 안에서만 import). 여기서는 설정 해석만 검증한다.
"""

import importlib
import os
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # 게이트는 pymupdf 외의 외부 의존성을 전제하지 않는다
    yaml = None

MANIFEST = Path(__file__).with_name("rayservice-qwen.yaml")


def load_module_with_env(**env):
    """환경변수를 바꿔 mobilenet_serve를 다시 읽는다 (모듈 수준 상수라서)."""
    saved = {key: os.environ.get(key) for key in env}
    os.environ.update({k: v for k, v in env.items() if v is not None})
    for key, value in env.items():
        if value is None:
            os.environ.pop(key, None)
    try:
        import mobilenet_serve

        return importlib.reload(mobilenet_serve)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class BatchSettingsTest(unittest.TestCase):
    """Ray Serve의 두 노브가 Triton의 두 노브에 대응하는지."""

    def test_default_matches_c2_middle_point(self):
        module = load_module_with_env(MAX_BATCH_SIZE="8", BATCH_WAIT_S="0.005")
        settings = module.batch_settings()
        self.assertTrue(settings["batching"])
        self.assertEqual(settings["max_batch_size"], 8)
        self.assertAlmostEqual(settings["batch_wait_timeout_s"], 0.005)
        # C2(Triton)의 max_queue_delay_microseconds와 같은 단위로 읽을 수 있어야 한다
        self.assertEqual(settings["batch_wait_us"], 5000)

    def test_off_disables_batching_not_batch_size(self):
        """대조군은 배칭을 끄는 것이지 배치 크기를 0으로 만드는 게 아니다."""
        module = load_module_with_env(MAX_BATCH_SIZE="8", BATCH_WAIT_S="off")
        settings = module.batch_settings()
        self.assertFalse(settings["batching"])
        self.assertEqual(settings["max_batch_size"], 1)
        self.assertIsNone(settings["batch_wait_timeout_s"])

    def test_zero_wait_still_batches(self):
        """delay=0도 '기다리지 않는 dynamic'이지 배칭 끔이 아니다 (C2와 동일한 구분)."""
        module = load_module_with_env(MAX_BATCH_SIZE="8", BATCH_WAIT_S="0")
        settings = module.batch_settings()
        self.assertTrue(settings["batching"])
        self.assertEqual(settings["batch_wait_us"], 0)

    def test_c2_sweep_points_all_parse(self):
        """C2와 같은 스윕 지점(off/0/1ms/5ms/20ms)이 그대로 통해야 한다."""
        expected = {"off": None, "0": 0, "0.001": 1000, "0.005": 5000, "0.02": 20000}
        for raw, micros in expected.items():
            with self.subTest(wait=raw):
                module = load_module_with_env(BATCH_WAIT_S=raw)
                self.assertEqual(module.batch_settings()["batch_wait_us"], micros)


@unittest.skipIf(yaml is None, "pyyaml 없음 — pip install pyyaml 후 검증됩니다")
class ManifestTest(unittest.TestCase):
    """RayService 매니페스트가 B1과 같은 조건인지 — 아니면 비교가 성립하지 않는다."""

    @classmethod
    def setUpClass(cls):
        assert yaml is not None
        docs = list(yaml.safe_load_all(MANIFEST.read_text(encoding="utf-8")))
        cls.rayservice = next(d for d in docs if d and d["kind"] == "RayService")
        cls.serve_config = yaml.safe_load(
            cls.rayservice["spec"]["serveConfigV2"]
        )["applications"][0]["args"]["llm_configs"][0]

    def test_model_matches_b1(self):
        """B1과 다른 모델을 쓰면 오케스트레이션 오버헤드를 분리할 수 없다."""
        loading = self.serve_config["model_loading_config"]
        self.assertEqual(loading["model_source"], "Qwen/Qwen2.5-1.5B-Instruct")
        self.assertEqual(loading["model_id"], "qwen2.5-1.5b")

    def test_engine_kwargs_match_b1_baseline(self):
        engine = self.serve_config["engine_kwargs"]
        self.assertEqual(engine["max_model_len"], 4096)
        self.assertEqual(engine["gpu_memory_utilization"], 0.85)
        self.assertEqual(engine["max_num_seqs"], 16)

    def test_single_gpu_only(self):
        """물리 GPU가 1장뿐이다 — 공식 예제의 4장 설정을 그대로 쓰면 스케줄이 안 된다."""
        workers = self.rayservice["spec"]["rayClusterConfig"]["workerGroupSpecs"]
        self.assertEqual(len(workers), 1)
        worker = workers[0]
        self.assertEqual(worker["replicas"], 1)
        self.assertEqual(worker["maxReplicas"], 1)
        self.assertEqual(worker["rayStartParams"]["num-gpus"], "1")
        limits = worker["template"]["spec"]["containers"][0]["resources"]["limits"]
        self.assertEqual(limits["nvidia.com/gpu"], 1)

    def test_head_does_not_claim_a_gpu(self):
        """헤드가 GPU를 잡으면 워커가 못 뜬다 (GPU 1장)."""
        head = self.rayservice["spec"]["rayClusterConfig"]["headGroupSpec"]
        self.assertEqual(head["rayStartParams"]["num-gpus"], "0")

    def test_worker_uses_nvidia_runtime_class(self):
        """WSL2 K3s에서 GPU 파드는 runtimeClassName: nvidia가 필요하다."""
        worker = self.rayservice["spec"]["rayClusterConfig"]["workerGroupSpecs"][0]
        self.assertEqual(worker["template"]["spec"]["runtimeClassName"], "nvidia")

    def test_worker_memory_fits_wsl2_allocation(self):
        """WSL2에 23Gi만 할당돼 있다 — head+worker 합이 그걸 넘으면 안 뜬다."""
        cluster = self.rayservice["spec"]["rayClusterConfig"]
        head_mem = cluster["headGroupSpec"]["template"]["spec"]["containers"][0][
            "resources"]["requests"]["memory"]
        worker_mem = cluster["workerGroupSpecs"][0]["template"]["spec"][
            "containers"][0]["resources"]["requests"]["memory"]
        total = int(head_mem.rstrip("Gi")) + int(worker_mem.rstrip("Gi"))
        self.assertLessEqual(total, 20, f"requests 합이 {total}Gi — WSL2 23Gi에 빠듯하다")


if __name__ == "__main__":
    unittest.main()
