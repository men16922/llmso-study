#!/usr/bin/env python3
"""mobilenet_v2를 **배치 축이 열린** ONNX로 export한다 (C2의 전제 조건).

왜 필요한가 — 교재 저장소의 `densenet_onnx`로는 dynamic batching을 켤 수 없다.
그 모델의 config.pbtxt는 이렇게 되어 있다.

    max_batch_size : 0                       # 배칭 자체가 꺼짐
    dims: [ 3, 224, 224 ]
    reshape { shape: [ 1, 3, 224, 224 ] }    # 배치 차원 1을 억지로 끼워 넣는 중

즉 그 ONNX는 **배치 축이 1로 고정**이라 max_batch_size를 켜면 모델이 거부한다.
`reshape`가 그 우회 흔적이다. 그래서 배치 축을 dynamic으로 연 모델을 새로 만든다.

`dynamic_axes` 한 줄이 이 실험 전체를 가능하게 한다 — 서빙 계층만 봐서는 보이지
않는 제약이다. "배칭을 지원하려면 모델이 먼저 배치를 받아들여야 한다."

    python3 export_mobilenet_onnx.py --out model_dir/mobilenet_v2/1/model.onnx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

OPSET = 17


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=Path("model_dir/mobilenet_v2/1/model.onnx")
    )
    parser.add_argument("--opset", type=int, default=OPSET)
    parser.add_argument(
        "--verify", action="store_true",
        help="export 후 배치 축이 실제로 열렸는지 onnx로 확인 (onnx 패키지 필요)",
    )
    return parser


def verify_dynamic_batch(path: Path) -> bool:
    """입력 텐서의 첫 차원이 고정 숫자가 아니라 심볼(dim_param)인지 확인한다."""
    import onnx

    model = onnx.load(str(path))
    first_input = model.graph.input[0]
    first_dim = first_input.type.tensor_type.shape.dim[0]
    return first_dim.dim_param != ""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        import torch
        import torchvision
    except ImportError:
        print("torch·torchvision이 필요합니다: pip install torch torchvision onnx",
              file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model = torchvision.models.mobilenet_v2(weights="DEFAULT").eval()
    dummy = torch.randn(1, 3, 224, 224)

    torch.onnx.export(
        model,
        dummy,
        str(args.out),
        input_names=["input"],
        output_names=["output"],
        # ★ 이 한 줄이 배치 축을 연다. 없으면 Triton이 max_batch_size를 거부한다.
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=args.opset,
    )
    print(f"export 완료: {args.out}")

    if args.verify:
        try:
            ok = verify_dynamic_batch(args.out)
        except ImportError:
            print("확인하려면 onnx 패키지가 필요합니다: pip install onnx", file=sys.stderr)
            return 0
        print("배치 축 dynamic: " + ("✅" if ok else "❌ — 고정 배치로 나왔습니다"))
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
