# Cloud Run Gemma 4 vLLM A1~A4 벤치마크

[`Run inference of Gemma 4 model on Cloud Run`](../../articles/Run%20inference%20of%20Gemma%204%20model%20on%20Cloud%20Run.md)의 후속 성능 측정 자산입니다.

## 무엇을 측정하나

| 실험 | 측정 목적 |
|---|---|
| A1 | warm 상태의 동시성별 배칭 처리량과 TTFT |
| A2 | Prefix Caching hit와 길이를 맞춘 miss 대조군 |
| A3 | 짧은 요청·긴 입력(prefill)·긴 출력(decode) 비교 |
| A4 | TTFT·E2E SLO를 만족하는 goodput과 최대 동시성 |

측정기는 루트 `.env`의 `PROJECT_ID`를 자동으로 읽습니다. 인증 토큰은 `gcloud auth print-identity-token`으로 실행할 때만 가져오며 결과에 저장하지 않습니다.

## 비용 없는 로컬 검증

다음 명령은 mock 스트리밍 서버만 사용하며 Cloud Run을 호출하지 않습니다.

```bash
python3 -m unittest discover \
  -s labs/cloudrun-gemma4-vllm \
  -p 'test_*.py'
```

## GPU 실행

Cloud Run 서비스가 scale-to-zero 상태라면 아래 첫 요청이 GPU를 기동합니다. 비용이 발생할 수 있습니다.

```bash
python3 labs/cloudrun-gemma4-vllm/benchmark_a1_a4.py \
  --exp smoke \
  --output labs/cloudrun-gemma4-vllm/results/smoke.json
```

```bash
python3 labs/cloudrun-gemma4-vllm/benchmark_a1_a4.py \
  --exp all \
  --output labs/cloudrun-gemma4-vllm/results/a1-a4-rerun.json
```

기본 SLO는 TTFT 2초, E2E 30초입니다. `--ttft-slo`, `--e2e-slo`로 바꿀 수 있습니다. 콜드 스타트는 첫 warmup 결과에 별도로 저장되며 A1·A4의 warm 곡선에는 포함되지 않습니다.

기본값은 reasoning 길이에 따른 변동을 줄이기 위해 thinking을 끕니다. reasoning 성능을 따로 측정하려면 `--enable-thinking`을 추가하고 기존 결과와 다른 파일에 저장합니다.

## 결과 해석

- `tokens_exact=true`: vLLM의 스트리밍 usage에서 받은 실제 출력 토큰 수
- `tokens_exact=false`: usage가 없어 문자 길이로 추정한 값
- `goodput_pct`: TTFT와 E2E SLO를 모두 만족한 요청 비율
- `requests[]`: 실패 원인을 포함한 요청별 원시 측정값
- `summaries[]`: 실험·시나리오·동시성별 p50/p95와 처리량

실제 기준선으로 쓸 결과는 모든 성공 요청에서 `tokens_exact=true`인지 먼저 확인합니다.
