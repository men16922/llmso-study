"""summarize_trace.py 단위 테스트 — 네트워크·GPU 없이 순수 로직만 검증한다.

분류가 틀리면 글의 숫자가 조용히 틀린다. 커널 이름은 정밀도가 바뀌면 통째로
달라지므로(BF16의 cutlass 계열이 FP8에서는 scaled_mm으로 교체된다) 역할 분류가
이 도구의 유일한 판단 지점이고, 그래서 여기만 테스트한다.
"""

import gzip
import json

import pytest

import summarize_trace as st


@pytest.mark.parametrize(
    "name, expected",
    [
        # BF16 쪽에서 실제로 나오는 이름들
        ("void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm...>", "GEMM (선형 계층)"),
        ("nvjet_tst_128x64_64x5_1x3_h_bz_coopA_NTn", "GEMM (선형 계층)"),
        # FP8로 바뀌면 이름이 통째로 달라진다 — 그래도 같은 역할로 묶여야 한다
        ("void vllm::scaled_mm_c3x<...>", "GEMM (선형 계층)"),
        ("flash_fwd_splitkv_kernel", "어텐션"),
        ("void vllm::rms_norm_kernel<...>", "정규화·활성화"),
        ("void vllm::act_and_mul_kernel<...>", "정규화·활성화"),
        ("void vllm::dynamic_scaled_int8_quant_kernel", "양자화·스케일"),
        ("Memcpy DtoH", "복사·형변환"),
        ("완전히 처음 보는 커널", "분류 안 됨"),
    ],
)
def test_bucket_of(name, expected):
    assert st.bucket_of(name) == expected


def test_kernel_time_ignores_cpu_side_events():
    """cuda_runtime은 CPU 쪽 launch라 같이 세면 GPU 시간이 두 배로 부푼다."""
    events = [
        {"cat": "kernel", "name": "k1", "dur": 100},
        {"cat": "kernel", "name": "k1", "dur": 50},
        {"cat": "cuda_runtime", "name": "cudaLaunchKernel", "dur": 999},
        {"cat": "gpu_memcpy", "name": "Memcpy DtoH", "dur": 7},
        {"cat": "kernel", "name": "no_dur"},  # dur 없는 이벤트는 건너뛴다
    ]
    got = st.kernel_time(events)
    assert got["k1"] == [150.0, 2]
    assert got["Memcpy DtoH"] == [7.0, 1]
    assert "cudaLaunchKernel" not in got
    assert "no_dur" not in got


def test_load_events_reads_gzipped_directory(tmp_path):
    """vLLM은 .pt.trace.json.gz로 떨어뜨린다. 디렉터리를 주면 다 읽어야 한다."""
    d = tmp_path / "traces"
    d.mkdir()
    with gzip.open(d / "a.pt.trace.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"traceEvents": [{"cat": "kernel", "name": "k", "dur": 1}]}, f)
    with open(d / "b.pt.trace.json", "w", encoding="utf-8") as f:
        json.dump({"traceEvents": [{"cat": "kernel", "name": "k", "dur": 2}]}, f)

    files, events = st.load_events(str(d))
    assert len(files) == 2
    assert st.kernel_time(events)["k"] == [3.0, 2]


def test_load_events_raises_when_nothing_found(tmp_path):
    with pytest.raises(SystemExit):
        st.load_events(str(tmp_path))
