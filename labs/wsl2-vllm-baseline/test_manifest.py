#!/usr/bin/env python3
"""`k8s/vllm-baseline.yaml`이 실험 조건을 유지하는지 — 오프라인 검증.

이 매니페스트는 2주차 B1 기준선을 만든 바로 그 배포이고, 3·4주차의 모든
비교가 "같은 이미지·같은 모델·같은 실행 경로"라는 전제 위에 서 있다.
전제가 조용히 깨지면 숫자는 나오는데 비교가 성립하지 않는다 — 3주차에
계층마다 vLLM 버전이 달라 겪은 것이 정확히 그것이다.

4주차에 추가된 `EXTRA_ARGS`는 특히 조심스럽다. args 안에서 **따옴표 없이**
전개돼야 셸 단어 분리로 여러 플래그가 된다. 누가 좋은 뜻으로 `"$EXTRA_ARGS"`
처럼 따옴표를 씌우면 통째로 인자 하나가 되어 vLLM이 죽는다.
"""

import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # 게이트는 pymupdf 외의 외부 의존성을 전제하지 않는다
    yaml = None

MANIFEST = Path(__file__).with_name("k8s") / "vllm-baseline.yaml"


@unittest.skipIf(yaml is None, "pyyaml 없음 — pip install pyyaml 후 검증됩니다")
class BaselineManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert yaml is not None
        docs = [d for d in yaml.safe_load_all(MANIFEST.read_text(encoding="utf-8")) if d]
        cls.deployment = next(d for d in docs if d["kind"] == "Deployment")
        cls.container = cls.deployment["spec"]["template"]["spec"]["containers"][0]
        cls.args = " ".join(cls.container["args"])
        cls.env = {e["name"]: e.get("value") for e in cls.container["env"]}

    # ── 통제 변수 ────────────────────────────────────────────────

    def test_image_is_pinned_to_v0_23_0(self):
        """B1·E1·E2·E3가 같은 엔진 위에서 나와야 같은 표에 들어간다."""
        self.assertEqual(self.container["image"], "vllm/vllm-openai:v0.23.0")

    def test_image_pull_policy_never_refetches(self):
        """이 이미지는 k3s containerd에만 있다. Always면 ~10GB를 새로 받는다."""
        self.assertEqual(self.container["imagePullPolicy"], "IfNotPresent")

    def test_model_is_pinned(self):
        self.assertEqual(self.env["MODEL_ID"], "Qwen/Qwen2.5-1.5B-Instruct")
        self.assertEqual(self.env["SERVED_MODEL_NAME"], "qwen2.5-1.5b")

    def test_single_gpu_request_and_limit(self):
        """물리 GPU가 1장뿐이다."""
        resources = self.container["resources"]
        self.assertEqual(resources["requests"]["nvidia.com/gpu"], "1")
        self.assertEqual(resources["limits"]["nvidia.com/gpu"], "1")

    def test_nvidia_runtime_class(self):
        """WSL2 K3s에서 GPU 파드는 runtimeClassName: nvidia가 필요하다."""
        self.assertEqual(
            self.deployment["spec"]["template"]["spec"]["runtimeClassName"], "nvidia"
        )

    def test_recreate_strategy(self):
        """GPU 1장에서 RollingUpdate는 교착한다 — 새 파드가 GPU를 못 받는다."""
        self.assertEqual(self.deployment["spec"]["strategy"]["type"], "Recreate")

    # ── 4주차: EXTRA_ARGS ────────────────────────────────────────

    def test_extra_args_env_exists_and_defaults_empty(self):
        """기본값이 비어 있어야 2주차 B1과 동일한 명령줄이 재현된다."""
        self.assertIn("EXTRA_ARGS", self.env)
        self.assertEqual(self.env["EXTRA_ARGS"], "")

    def test_extra_args_is_expanded_in_args(self):
        self.assertIn("$EXTRA_ARGS", self.args)

    def test_extra_args_is_unquoted(self):
        """★ 따옴표를 씌우면 여러 플래그가 인자 하나로 뭉쳐 vLLM이 죽는다.

        `--max-num-batched-tokens 512`가 단어 둘로 쪼개져야 하므로
        `"$EXTRA_ARGS"`도 `'$EXTRA_ARGS'`도 안 된다.
        """
        self.assertNotIn('"$EXTRA_ARGS"', self.args)
        self.assertNotIn("'$EXTRA_ARGS'", self.args)
        # 그 외 다른 env는 반대로 반드시 따옴표가 있어야 한다 (빈 값 방어).
        for name in ("MAX_NUM_SEQS", "MAX_MODEL_LEN", "GPU_MEMORY_UTILIZATION"):
            with self.subTest(env=name):
                self.assertIn(f'"${name}"', self.args)

    def test_extra_args_comes_last(self):
        """뒤에 와야 앞의 기본 플래그를 덮어쓸 수 있다."""
        tail = self.args[self.args.index("$EXTRA_ARGS") :]
        self.assertNotIn("--", tail.replace("$EXTRA_ARGS", "", 1))

    def test_baseline_flags_still_present(self):
        """EXTRA_ARGS를 넣다가 기본 플래그를 흘리면 B1 재현이 깨진다."""
        for flag in (
            "--served-model-name",
            "--max-model-len",
            "--gpu-memory-utilization",
            "--max-num-seqs",
            "--port",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.args)

    def test_no_leftover_experiment_flag_hardcoded(self):
        """실험 플래그가 매니페스트에 박히면 다음 실험이 조용히 오염된다.

        전부 EXTRA_ARGS로만 들어가야 하고, 기본 상태는 vanilla여야 한다.
        """
        for flag in (
            "--speculative-config",
            "--max-num-batched-tokens",
            "--no-enable-prefix-caching",
            "--enable-prefix-caching",
        ):
            with self.subTest(flag=flag):
                self.assertNotIn(flag, self.args)


@unittest.skipIf(yaml is None, "pyyaml 없음")
class RedeployHelperTest(unittest.TestCase):
    """`redeploy.sh`가 EXTRA_ARGS를 받을 수 있는 형태인지."""

    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).with_name("redeploy.sh")).read_text(encoding="utf-8")

    def test_redeploy_forwards_arbitrary_key_values(self):
        """`kubectl set env`에 인자를 그대로 넘겨야 EXTRA_ARGS도 통과한다."""
        self.assertRegex(self.source, r'set env "deploy/\$DEPLOY" "\$@"')

    def test_rollout_failure_is_detected(self):
        """롤아웃 실패를 안 잡으면 죽은 엔드포인트에 벤치마크를 돌린다."""
        self.assertIn("rollout status", self.source)
        self.assertRegex(self.source, r"롤아웃 실패")

    def test_waits_for_actual_response(self):
        self.assertIn("/v1/models", self.source)


if __name__ == "__main__":
    unittest.main()
