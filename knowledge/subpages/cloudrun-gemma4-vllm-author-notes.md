# Cloud Run Gemma 4 실습 운영·증빙 메모

> 공개용 글에서 제외한 작성자용 기록이다. 공유 문서는 [`Run inference of Gemma 4 model on Cloud Run`](../../articles/Run%20inference%20of%20Gemma%204%20model%20on%20Cloud%20Run.md)을 사용한다.

## 1. 실행 환경 메모

| 항목 | 값 |
| --- | --- |
| 프로젝트 | 루트 `.env`의 `PROJECT_ID` |
| 리전 | `europe-west4` |
| 실행 위치 | 로컬 macOS + Google Cloud SDK 571.0.0 |
| 서비스 | `gemma-rtx-vllm-codelab` |
| 리비전 | `gemma-rtx-vllm-codelab-00001-7pm` |
| GPU | NVIDIA RTX PRO 6000 1개 |
| vLLM | `0.17.2rc1.dev133+g9279c59a0` |
| 모델 | 10개 객체, 62,578,670,545B(58.28GiB) |

## 2. 첫 측정을 최종 결과에서 제외한 이유

초기 A1·A2 결과는 병목 가설을 세우는 데만 사용한다.

- TTFT를 첫 내용 토큰이 아니라 첫 SSE 이벤트로 측정했다.
- 출력 토큰 수를 API `usage` 대신 `문자 수 ÷ 4`로 추정했다.
- 동시성 1에만 콜드 스타트가 섞였고 요청별 원시 JSON이 없었다.
- Prefix Caching은 길이를 맞춘 miss 대조군 없이 첫 요청과 후속 요청을 비교했다.

공유용 수치는 `a1-a4-20260801-211752.json`과 같은 시각의 터미널 로그만 사용한다.

## 3. 인증 파일 현황

실행 구간은 `2026-08-01T21:17:52Z~21:22:03Z`, 한국시간으로 `2026-08-02 06:17:52~06:22:03`이다. Metrics 캡처 범위는 앞뒤 여유를 둔 `06:15~06:25`로 맞췄다.

| 파일 | 상태 | 메모 |
| --- | --- | --- |
| `proof-01-terminal-a1-a4.png` | 재촬영 필요 | 기존 잘못된 파일은 휴지통으로 이동. 실행 완료 명령과 A1~A4 요약을 한 화면에 담아야 함 |
| `proof-02-request-load.png` | 통과 | 요청 수와 지연 시간 확인 가능 |
| `proof-03-gpu-utilization.png` | 통과 | GPU 사용률 최대 100%, 메모리 사용률 약 95~98% |
| `proof-04-gpu-memory-instance.png` | 부분 통과 | 추천 인스턴스와 GPU 메모리는 보이나 실제 Container instance count 차트가 아님 |
| `proof-05-request-logs.png` | 통과 | POST 144건, HTTP 200, 요청별 latency 확인 가능 |

## 4. 재측정과 시각 기록

```bash
set -o pipefail
RUN_STAMP=$(date -u +%Y%m%d-%H%M%S)
START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 labs/cloudrun-gemma4-vllm/benchmark_a1_a4.py \
  --exp all \
  --ttft-slo 2 \
  --e2e-slo 30 \
  --output "labs/cloudrun-gemma4-vllm/results/a1-a4-${RUN_STAMP}.json" \
  2>&1 | tee "labs/cloudrun-gemma4-vllm/results/a1-a4-${RUN_STAMP}.log"

END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf 'START_UTC=%s\nEND_UTC=%s\n' "$START_UTC" "$END_UTC"
```

warmup 1건과 A1~A4 143건을 합쳐 Cloud Logging의 예상 POST 요청은 144건이다. Monitoring 반영에는 3~5분이 걸릴 수 있다. 인스턴스가 다시 0으로 내려가는 장면까지 필요하면 `OBS_END_UTC`도 따로 기록한다.

## 5. Cloud Console 캡처 경로

### 요청과 GPU 지표

Cloud Run → `gemma-rtx-vllm-codelab` → 관측 가능성 → 측정항목에서 실제 실행 시각을 맞춤 범위로 지정한다. 기본 차트에 원하는 지표가 없으면 Metrics Explorer에서 다음 메트릭을 선택한다.

```text
run.googleapis.com/request_count
run.googleapis.com/request_latencies
run.googleapis.com/container/max_request_concurrencies
run.googleapis.com/container/gpu/utilizations
run.googleapis.com/container/gpu/memory_utilizations
run.googleapis.com/container/instance_count
```

리소스 유형은 `Cloud Run Revision`, 필터는 `service_name = gemma-rtx-vllm-codelab`로 고정한다.

### 요청 로그

```text
resource.type="cloud_run_revision"
resource.labels.service_name="gemma-rtx-vllm-codelab"
logName:"run.googleapis.com%2Frequests"
httpRequest.requestUrl:"/v1/chat/completions"
timestamp>="START_UTC_VALUE"
timestamp<="END_UTC_VALUE"
```

같은 결과는 `.env` 전체를 로드하지 않고 `PROJECT_ID`만 읽어 확인한다.

```bash
PROJECT_ID=$(grep '^PROJECT_ID=' .env | cut -d= -f2-)

gcloud logging read "
resource.type=\"cloud_run_revision\"
resource.labels.service_name=\"gemma-rtx-vllm-codelab\"
logName:\"run.googleapis.com%2Frequests\"
httpRequest.requestUrl:\"/v1/chat/completions\"
timestamp>=\"${START_UTC}\"
timestamp<=\"${END_UTC}\"
" \
  --project "$PROJECT_ID" \
  --limit 300 \
  --order asc \
  --format='table(timestamp,httpRequest.status,httpRequest.latency)'
```

## 6. 문서에 넣기 전 확인

- [ ] 실행 완료 후 터미널을 촬영했는가?
- [ ] 모든 Metrics 차트가 같은 관측 범위인가?
- [ ] Logs가 실제 요청 구간만 조회하는가?
- [ ] 서비스 필터, 차트 제목, 축과 범례가 보이는가?
- [ ] JSON 요청 수와 Logs 요청 수의 차이를 설명할 수 있는가?
- [ ] 액세스 토큰, 이메일, 결제 정보가 노출되지 않았는가?

Cloud Run Metrics와 Logs만으로 TTFT를 복원할 수는 없다. TTFT·tok/s·goodput은 벤치마크 JSON과 터미널 출력으로 증명한다.

## 7. 운영 상태와 정리

- [x] `europe-west4` RTX PRO 6000 할당량 1 확인
- [x] GCS 버킷과 Cloud Run 서비스를 같은 리전에 배치
- [x] `--no-allow-unauthenticated`와 ID 토큰 호출 확인
- [x] 콜드 스타트, TTFT, 처리량과 GPU 메모리 측정
- [ ] 서비스 계정 권한 축소: 현재 실습 절차대로 `roles/storage.admin`
- [ ] 예산 알림 설정
- [ ] GPU 서비스와 모델 캐시 삭제

서비스는 `min-instances=0`이라 유휴 GPU는 과금되지 않지만, GCS에는 58.28GiB 모델이 남아 있다. 실습을 끝내면 공유 문서의 Clean up 명령으로 서비스, 버킷, 서비스 계정과 VPC를 정리한다.
