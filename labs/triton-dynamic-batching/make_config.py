#!/usr/bin/env python3
"""Triton `config.pbtxt`를 생성한다 — dynamic batching 스윕용.

C2는 `max_queue_delay_microseconds`만 바꿔가며 재는 실험이라 config를 계속 다시
써야 한다. sed로 한 줄만 고치면 대조군(dynamic_batching 블록 자체가 없는 상태)을
만들 수 없어서 파일 전체를 생성한다.

    python3 make_config.py off   > model_dir/mobilenet_v2/config.pbtxt   # 대조군
    python3 make_config.py 5000  > model_dir/mobilenet_v2/config.pbtxt   # 5ms 대기

⚠️ 대조군을 `max_batch_size: 0`으로 만들면 안 된다. 그러면 Triton이 입력 텐서
   모양을 다르게 해석해(배치 차원을 클라이언트가 직접 넣어야 함) **모델
   시그니처까지 달라진다.** `dynamic_batching` 블록만 빼야 모델은 그대로 두고
   배칭만 끈 올바른 대조군이 된다.
"""

from __future__ import annotations

import argparse
import sys

DEFAULT_MODEL = "mobilenet_v2"
DEFAULT_MAX_BATCH = 8

# max_batch_size > 0이면 dims에서 **배치 차원을 뺀다** (Triton이 앞에 붙인다).
# 저장소의 densenet_onnx가 max_batch_size: 0 + reshape를 쓰는 이유가 이것으로,
# 그 ONNX는 배치 축이 1로 고정이라 애초에 배칭을 켤 수 없다.
TEMPLATE = """name: "{model}"
platform: "onnxruntime_onnx"
max_batch_size: {max_batch}
input [
  {{
    name: "input"
    data_type: TYPE_FP32
    dims: [ 3, 224, 224 ]
  }}
]
output [
  {{
    name: "output"
    data_type: TYPE_FP32
    dims: [ 1000 ]
  }}
]
"""

DYNAMIC_BLOCK = """dynamic_batching {{
  max_queue_delay_microseconds: {delay}
}}
"""


def render_config(
    delay: str | int,
    model: str = DEFAULT_MODEL,
    max_batch: int = DEFAULT_MAX_BATCH,
) -> str:
    """delay="off"면 dynamic_batching 블록을 빼고, 아니면 마이크로초 값으로 넣는다."""
    config = TEMPLATE.format(model=model, max_batch=max_batch)
    if isinstance(delay, str) and delay.lower() == "off":
        return config
    delay_us = int(delay)
    if delay_us < 0:
        raise ValueError("max_queue_delay_microseconds는 0 이상이어야 합니다.")
    return config + DYNAMIC_BLOCK.format(delay=delay_us)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "delay",
        help="'off'(대조군) 또는 max_queue_delay_microseconds 값 (예: 0, 1000, 5000)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-batch", type=int, default=DEFAULT_MAX_BATCH)
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(render_config(args.delay, args.model, args.max_batch))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
