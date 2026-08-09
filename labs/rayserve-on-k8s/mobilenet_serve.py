#!/usr/bin/env python3
"""Ray Serve의 `@serve.batch`로 mobilenet을 서빙한다 — C2(Triton)와 같은 실험.

**왜 이 파일이 있는가.** Ray Serve의 dynamic batching 노브는 Triton과 정확히 대응한다.

    Triton                                  Ray Serve
    ------------------------------------    ----------------------------------
    max_batch_size: 8                       @serve.batch(max_batch_size=8)
    max_queue_delay_microseconds: 5000      @serve.batch(batch_wait_timeout_s=0.005)
    (dynamic_batching 블록 없음)              @serve.batch 데코레이터 없음

같은 모델(mobilenet_v2)·같은 개념·다른 프레임워크다. C2에서 잰 곡선을 여기서 다시 그리면
**"dynamic batching은 프레임워크가 아니라 워크로드의 성질이 정한다"**가 증명된다.

    MAX_BATCH_SIZE=8 BATCH_WAIT_S=0.005 serve run mobilenet_serve:app

BATCH_WAIT_S=off면 @serve.batch를 아예 걸지 않는다 — C2의 대조군과 같은 방식이다
(배칭을 끄는 것이지 배치 크기를 0으로 만드는 것이 아니다).
"""

from __future__ import annotations

import os

# --- 설정 (환경변수로 스윕한다 — 코드를 고치지 않기 위해) -----------------------
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "8"))
BATCH_WAIT_RAW = os.getenv("BATCH_WAIT_S", "0.005")
BATCHING_ENABLED = BATCH_WAIT_RAW.lower() != "off"
BATCH_WAIT_S = float(BATCH_WAIT_RAW) if BATCHING_ENABLED else 0.0


def batch_settings() -> dict[str, object]:
    """현재 설정을 되돌려준다 (테스트와 /config 엔드포인트가 쓴다).

    Triton의 config.pbtxt에 해당하는 것이 이 dict다. C2와 같은 축으로 스윕하려면
    max_batch_size는 고정하고 batch_wait_timeout_s만 바꾼다.
    """
    return {
        "batching": BATCHING_ENABLED,
        "max_batch_size": MAX_BATCH_SIZE if BATCHING_ENABLED else 1,
        "batch_wait_timeout_s": BATCH_WAIT_S if BATCHING_ENABLED else None,
        # C2와 같은 단위로 읽기 위해 마이크로초도 같이 준다
        "batch_wait_us": int(BATCH_WAIT_S * 1_000_000) if BATCHING_ENABLED else None,
    }


def build_app():
    """Ray Serve 앱을 만든다. import 시점에 ray를 요구하지 않도록 함수 안에 둔다."""
    import numpy as np
    import torch
    import torchvision
    from ray import serve
    from starlette.requests import Request

    @serve.deployment(
        ray_actor_options={"num_gpus": 1 if torch.cuda.is_available() else 0},
        autoscaling_config={"min_replicas": 1, "max_replicas": 1},
    )
    class MobileNet:
        def __init__(self) -> None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = (
                torchvision.models.mobilenet_v2(weights="DEFAULT")
                .eval()
                .to(self.device)
            )
            # 배치 실행 횟수를 세어 평균 배치 크기를 직접 계산한다.
            # Triton은 nv_inference_exec_count가 해 주는 일을 여기서는 우리가 센다.
            self.requests_seen = 0
            self.batches_run = 0

        def _run(self, images: list) -> list:
            self.requests_seen += len(images)
            self.batches_run += 1
            batch = torch.from_numpy(np.stack(images)).to(self.device)
            with torch.no_grad():
                logits = self.model(batch)
            return logits.argmax(dim=1).cpu().tolist()

        if BATCHING_ENABLED:
            # ★ 이 데코레이터가 Triton의 dynamic_batching 블록에 해당한다
            @serve.batch(
                max_batch_size=MAX_BATCH_SIZE,
                batch_wait_timeout_s=BATCH_WAIT_S,
            )
            async def infer(self, images: list) -> list:
                return self._run(images)
        else:
            # 대조군 — 데코레이터를 아예 걸지 않는다. 요청 하나당 실행 하나.
            async def infer(self, images: list) -> list:  # type: ignore[misc]
                return self._run([images])[0]

        async def __call__(self, request: Request):
            if request.url.path.endswith("/stats"):
                return {
                    **batch_settings(),
                    "requests_seen": self.requests_seen,
                    "batches_run": self.batches_run,
                    # C2와 같은 정의: 요청 수 ÷ 실행 횟수
                    "avg_batch_size": (
                        self.requests_seen / self.batches_run
                        if self.batches_run else None
                    ),
                }
            payload = await request.json()
            image = np.asarray(payload["image"], dtype=np.float32)
            result = await self.infer(image)
            return {"class_id": result}

    return MobileNet.bind()


# `serve run mobilenet_serve:app`이 찾는 이름
try:  # ray가 없는 환경(게이트)에서는 import 자체가 실패하므로 감싼다
    app = build_app()
except Exception:  # pragma: no cover - 로컬 게이트에서만 도달
    app = None
