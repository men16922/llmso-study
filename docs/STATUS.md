# Status

Last Updated: 2026-08-23

## Current Baseline

**게이트 green.** `make check` = 문서 검사 3종(`links` / `index` / `tools`) + `labs/` 단위 테스트 **91건**, 전부 오프라인·결정론적, 약 2초.

> ⚠️ **이 머신에서는 `make check-labs`가 그대로 안 돕니다.** WSL의 `python3`(3.14)에 **pip 자체가 없고** pytest도 없습니다. 2026-08-15에는 Windows Python 3.12에 `pytest`·`pyyaml`을 설치해 91건을 확인했습니다. `Makefile`의 `PY ?= python3`를 Windows 파이썬으로 덮어쓰거나 WSL에 pip를 넣어야 합니다.

- `knowledge/` — 번호 문서 `00`~`06` + `subpages/` 11종 + `references/` 6종. 상대 링크·앵커 전부 유효.
- `index/` — PDF 3종 + 마크다운 묶음(66개 문서) 인덱스. 스키마 검증 통과. 현재 Inference Engineering만 `llm-claude-code-korean`으로 보강됨, 나머지는 `extractive-*`.
- `labs/` — 6개. `wsl2-vllm-baseline`(56) · `cloudrun-gemma4-vllm`(6) · `triton-dynamic-batching`(19) · `rayserve-on-k8s`(10) + **`triton-vllm-backend`·`kserve-on-k8s`**(매니페스트만, 테스트 없음). 테스트는 전부 mock·순수 로직이라 GPU·네트워크 불필요.
- `articles/` — Cloud Run Gemma 4(1주차), CH3·CH4 시나리오 4편, `두 글을 잇는 선`, **2주차 과제 2편(노션 발행·링크 공유 완료)**, 3주차 실습 시나리오 5편(허브 + `3주차-00`~`-03`), **3주차 과제 글 `서빙 최적화, 설정부터 만지면 안 되는 이유`(571줄) — 이전 원고 `슬롯을 4배로...`를 대체. 윤문·노션 재발행 진행 중**.
- `articles/figures/` · `articles/screenshots/` — 그래프 **7종**(SVG, `fig-c3-layer-cost` 추가 — 세 계층의 가격 곡선) + 실습 인증 캡처 9장(Ray Dashboard·Prometheus·Grafana DCGM).
- `tools/` — 인덱싱 3종 + **`make_figures.py`**(결과 JSON → SVG) + **`md_to_notion.py`**(마크다운 → 노션 변환). 둘 다 외부 의존성 없음.
- **측정 원본** — `labs/wsl2-vllm-baseline/results/`에 2주차 B1·B2 8종 + **3주차 계층 3종과 각각의 짝**: `c3-rayserve-*`·`b3-*`·`b-direct-v072-*`(Ray Serve 짝) / `c3-triton-vllm-seqs64`·`b-direct-v055-*`(Triton 짝) / `c3-kserve-vllm-seqs64`·`b-direct-v0200-*`(KServe 짝) + `metrics-*.txt` 6종, 분석 3종. C2는 `labs/triton-dynamic-batching/results/` 16종.
- `study/` — 노션 원문 로컬 사본. **gitignore + 인덱스 제외** (멤버 전용 자료). `Ch1~Ch6.md` + `LLM기초.md`.

스터디 진행: **1·2주차 완료·제출 완료. 3주차(CH5·CH6) 계층 3종 측정 + 글 재작성 완료 — 노션 재발행·링크 공유 남음.**

## Active Focus

Authority: `docs/NEXT_PLAN.md`.

0. **3주차 과제 제출** — 원고 재작성 완료. **남은 것은 노션 재발행(https://app.notion.com/p/3c44c2420ac48157aaebe78f971e05c9 갱신) + 링크 공유.** 마감 **2026-08-23 09:00**.
1. 그다음: 4주차 예습 노트.

## Open Risks

- **과제 미공유 1회 = 제명.** 다음 마감 **2026-08-23(일) 09:00**. 원고는 끝났고 **재발행 + 공유가 남았습니다.**
- ⚠️ **공백이 또 반복됐습니다** — 08-16 → 08-21 닷새. 이번에는 측정이 계획 추정보다 훨씬 빨라(벤치마크 1회 약 4분, `serveConfigV2` 롤아웃 20~60초) 한 세션에 셋을 다 넣었지만, 운이 좋았던 것에 가깝습니다. 4주차는 측정을 주중 앞쪽으로.
- ~~`Maximum concurrency` 변동 원인 미확인~~ → **부분 규명.** `max_num_seqs`를 키우면 활성화 피크가 커져 KV 예산을 갉아먹습니다(0.26→0.48 GiB ⇒ KV 7.00→6.79 GiB). KV 예산은 정적 공식이 아니라 **기동 시 프로파일링 결과**입니다. 다만 이번 변동은 3%라 **2주차의 2배(59.50↔28.77)는 여전히 미확인**입니다.
- **`vllm:*` 메트릭은 데이터 플레인 계층에서만 사라집니다.** Ray Serve(`:8000/metrics` 404)·Triton 둘 다 0개인데, KServe(RawDeployment)는 66개가 그대로 남습니다 — KServe는 요청 경로에 없기 때문입니다. 서버 측 교차검증이 필요한 실험은 KServe나 계층 없는 구성 위에서 설계하세요.
- ~~Grafana 스크린샷 미확보~~ → **해소.** Prometheus 콘솔 캡처 3장을 `articles/screenshots/proof-0{1,2,3}-*.jpg`로 확보했습니다. `b1-timeline.txt`의 구간 시각 덕분에 부하가 끝난 **여섯 시간 뒤에** 되짚어 찍을 수 있었습니다.
- **백그라운드 태스크가 이 환경에서 반복 강제 종료됩니다.** 0-1 keeper가 죽으면 WSL 유휴 poweroff로 k3s 파드가 `Completed`/`Unknown`이 되어 측정이 끊깁니다. **긴 측정은 포그라운드로 돌리거나, keeper를 별도 PowerShell 창에서 사람이 직접 띄우세요.**
- **`make check-labs`가 이 머신에서 그대로 안 됩니다** (위 Baseline 참조).
- **GPU·8000 포트가 하나씩뿐.** B1·B2 / C1 / C2 / C3는 서로 배타적입니다. 세션 전환 시 앞의 것을 안 내리면 다음 실험이 OOM으로 안 뜹니다.
- **KV cache 크기가 롤아웃마다 흔들립니다.** 같은 `slots=64`인데 `Maximum concurrency`가 59.50x / 28.77x로 갈렸습니다. 직전 파드의 VRAM 반환 지연이 유력하나 **미확인**. 롤아웃 직후 이 로그 줄을 반드시 확인하세요 — 조용히 절반이 되면 처리량 천장도 절반입니다.
- ⚠️ **디스크가 꽉 차면 WSL이 통째로 멈춥니다.** Triton vLLM 이미지(36.3GB)를 받다가 C: 잔여 공간이 0.1GB가 됐고, ext4.vhdx가 더 못 늘어나 `libacl.so.1: Input/output error`와 함께 k3s까지 죽었습니다. **큰 이미지를 받기 전에 `df -h`와 Windows 드라이브 여유를 먼저 확인하세요.** 복구는 WSL 안에서 `docker rmi` → `wsl --shutdown` 순입니다.
- **GPU 1장에서 롤링 업데이트는 교착합니다.** 새 파드가 GPU를 기다리는데 옛 파드가 쥐고 있어 양쪽이 멈춥니다. 옛 ReplicaSet을 `scale --replicas=0`으로 내려야 진행됩니다. KServe처럼 컨트롤러가 Deployment를 되돌리는 경우 전략 패치는 소용없습니다.
- **c=64 재현 측정은 10%까지 흔들립니다.** 같은 서버를 같은 설정으로 두 번 재서 확인했습니다(c≤32는 1.3% 안). **c=64에서 10%대 차이를 결론의 근거로 쓰지 마세요.**
- **계층마다 품은 vLLM 버전이 다릅니다** — Ray Serve 0.7.2 / Triton 0.5.5 / KServe 0.20.0. 계층 비용을 재려면 **같은 이미지에서 계층만 뺀 짝**이 반드시 필요합니다. 짝이 맞았는지는 기동 로그의 KV 예산으로 확인합니다.
- **교재 CH5의 KV 공식은 MHA 전제입니다** (`2 × 층수 × 어텐션 헤드 수 × head_dim × 정밀도`). Qwen2.5-1.5B는 **GQA**라 그대로 쓰면 안 맞습니다 — 손계산 시 `num_key_value_heads`를 쓸 것. 교재가 *"이후 장에서 MQA·GQA·MLA 소개"* 라 예고한 장이 곧 **이번 주 CH6**이라, 이 어긋남을 3주차 글의 핵심 절로 배치했습니다.
- **C1이 노션 CH3 원문 대조로 재설계됐습니다.** 교재 서버는 `main.py:63/69/74`가 `async def` 안에서 동기 호출을 해 이벤트 루프가 막히고 동시 요청이 순차 처리됩니다. 배칭 축을 `--prompts-per-request`로 바꿨고, 동시성은 `async def`→`def` 수정 전후 비교로 씁니다. **이 발견 자체가 02편의 핵심**입니다.
- **PDF 인덱스 재생성 사고** — `build_pageindex.py`를 `--only md` 없이 돌리면 LLM 한국어 요약이 날아갑니다. 게이트는 스키마만 보므로 이 회귀를 **잡지 못합니다**(`meta.summary_method` 회귀 검사는 미도입). 복구는 `enrich_summaries.py` 재실행(해시 캐시 있어 거의 공짜).
- **AWS GPU 쿼터 미신청** — 6주차(09-06) EKS 실습용. 목표 시한 2026-08-23.
