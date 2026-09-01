# Status

Last Updated: 2026-09-01

## Current Baseline

**게이트 green.** `make check` = 문서 검사 3종(`links` / `index` / `tools`) + `labs/` 단위 테스트 **106건**, 전부 오프라인·결정론적, 약 2초. ★ **106건은 2026-09-01부터 실제 숫자입니다** — 그 전까지 `Makefile:25`에 `test_manifest.py`가 빠져 실제 실행은 91건이었습니다(아래 Open Risks).

> ⚠️ **게이트 실행 가능 여부는 머신마다 다릅니다.** **macOS 세션에서는 `make check`가 그대로 통과합니다**(2026-08-30 확인). **Windows/WSL 랩톱**(측정 머신)에서는 안 됩니다 — WSL의 `python3`(3.14)에 **pip 자체가 없고** pytest도 없으며, Windows 셸에는 GNU make가 없습니다. 그쪽에서는 `PYTHONIOENCODING=utf-8 py -3 scripts/check_docs.py` + pytest를 분리 실행하세요(2026-08-15에 Windows Python 3.12에 `pytest`·`pyyaml`을 설치해 확인).

- `knowledge/` — 번호 문서 `00`~`06` + `subpages/` 11종 + `references/` 6종. 상대 링크·앵커 전부 유효.
- `index/` — PDF 3종 + 마크다운 묶음(66개 문서) 인덱스. 스키마 검증 통과. 현재 Inference Engineering만 `llm-claude-code-korean`으로 보강됨, 나머지는 `extractive-*`.
- `labs/` — 6개. `wsl2-vllm-baseline`(56 + **`test_manifest.py` 15**) · `cloudrun-gemma4-vllm`(6) · `triton-dynamic-batching`(19) · `rayserve-on-k8s`(10) + **`triton-vllm-backend`·`kserve-on-k8s`**(매니페스트만, 테스트 없음). 테스트는 전부 mock·순수 로직이라 GPU·네트워크 불필요. **게이트 106건.**
- `k8s/vllm-baseline.yaml`에 **`EXTRA_ARGS` env 신설**(2026-08-27). 실험별 플래그가 들어가는 유일한 자리. args에서 **따옴표 없이** 전개돼야 하고(셸 단어 분리), `test_manifest.py`가 그것을 감시합니다.
- `articles/` — Cloud Run Gemma 4(1주차), CH3·CH4 시나리오 4편, `두 글을 잇는 선`, **2주차 과제 2편(발행 완료)**, 3주차 실습 시나리오 5편 + **3주차 과제 글 `서빙 최적화, 설정부터 만지면 안 되는 이유`(발행 완료)**, 4주차 실습 시나리오 6편(`4주차-00`~`-04`, **런북의 docker 명령을 kubectl로 정정 완료**) + **4주차 과제 글 `워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식`(429줄) — humanize A·노션 갱신 완료.** 3주차 발행본처럼 질문→측정→해석→운영 판단 흐름으로 정리하고 중립형 제목까지 적용.
- `articles/figures/` · `articles/screenshots/` — 그래프 **8종**(SVG, `fig-e1-spec-decode` 추가 — 추측 디코딩이 0% 선을 두 번 가로지르는 그림) + 실습 인증 캡처 **13장**(Ray Dashboard·Prometheus·Grafana DCGM + **4주차 `proof-w4-01~04`**: Prometheus target UP · spec_decode 위치별 수용 · prefix cache 적중 · GPU 메모리에 찍힌 두 번의 기동).
- `tools/` — 인덱싱 3종 + **`make_figures.py`**(결과 JSON → SVG) + **`md_to_notion.py`**(마크다운 → 노션 변환). 둘 다 외부 의존성 없음.
- **4주차 측정 원본** (2026-08-27) — `labs/wsl2-vllm-baseline/results/`에 `e-vllm-help.txt`(플래그 확정 근거) · `e0-smoke.json` · `e1-{vanilla,ngram}.json` + 기동로그·메트릭 · `e1-accept-*`(워크로드별 수용률) · `e2-mnbt{512,8192}-*` · `e3-cache{on,off}-{shared,unique}.json` + 적중률 · `e4-scheduler.py`. **분석 2종: [`e-analysis.md`](../labs/wsl2-vllm-baseline/results/e-analysis.md) · [`e4-scheduler-notes.md`](../labs/wsl2-vllm-baseline/results/e4-scheduler-notes.md).**
- **측정 원본** — `labs/wsl2-vllm-baseline/results/`에 2주차 B1·B2 8종 + **3주차 계층 3종과 각각의 짝**: `c3-rayserve-*`·`b3-*`·`b-direct-v072-*`(Ray Serve 짝) / `c3-triton-vllm-seqs64`·`b-direct-v055-*`(Triton 짝) / `c3-kserve-vllm-seqs64`·`b-direct-v0200-*`(KServe 짝) + `metrics-*.txt` 6종, 분석 3종. C2는 `labs/triton-dynamic-batching/results/` 16종.
- `study/` — 노션 원문 로컬 사본. **gitignore + 인덱스 제외** (멤버 전용 자료). `Ch1~Ch10.md` + `LLM기초.md`. **`Ch9`·`Ch10`은 2026-08-30 추가**했고, `Ch10.md`는 라이브 노션 페이지와 **전량 일치**함을 대조로 확인했습니다(라이브-only 라인 0건).

스터디 진행: **1·2·3주차 완료·제출 완료** (3주차 마감 08-23 통과). **4주차(CH7·CH8) — 측정·글·노션 발행 완료, ⚠️ 링크 공유 여부 미확인(마감 08-30 09:00 경과).** **5주차(CH9·CH10) 착수 — 마감 09-06 09:00.**

## Active Focus

Authority: `docs/NEXT_PLAN.md`.

0. ⚠️ **4주차 ⑦ 링크 공유 — 마감(08-30 09:00) 경과, 공유 여부 미확인.** 글·노션 발행은 08-29에 끝났습니다(`워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식`, humanize A). **이 확인이 5주차 착수보다 먼저입니다.** 미공유 1회 = 제명.
1. **5주차 (CH9·CH10) — 계획 수립 완료, 측정 미착수.** 마감 **2026-09-06 09:00**. 설계·시간표·중단 기준은 [`docs/plans/2026-08-30-week5-attribution.md`](./plans/2026-08-30-week5-attribution.md).
   - **축**: `study/Ch9.md:10`의 첫 질문 — *"처리량이 올랐다는 건 GPU가 더 빨리 계산해서인가, 덜 다시 계산해서인가"*. 4주차가 **조건**(언제 이득)을 쟀다면 5주차는 **인과**(왜 이득)를 커널 타임라인에서 귀속시킵니다. 교재 근거: AWQ 2.7배인데 **GEMM 커널 시간은 거의 동일**.
   - **실험**: F1 양자화(★ 주인공, 자르지 않음) · F2 3계층 프로파일링(Nsight Systems → PyTorch Profiler → Nsight Compute, **CH10 공식 도전과제**) · F3 복제2 + LiteLLM · F4 Multi-LoRA(선택).
   - **⓪에서 먼저 뚫을 것 2개**: 컨테이너 안 **Nsight 권한**(1시간 초과 시 PyTorch Profiler 단독으로 축소) · **v0.23.0의 양자화 커널 지원**(FP8 → GPTQ → AWQ 1회씩).
   - 4주차가 남긴 두 공백이 그대로 재료입니다 — `iteration_tokens_total` 오독, 청크 512에도 남던 **ITL +16.3%**.
2. **AWS GPU 쿼터 신청** — 사용자가 콘솔에서 직접. **6주차(09-06) EKS가 걸려 있어 이번 주가 사실상 마감.**
3. **통합 메모리 vs VRAM 비교(G 시리즈) — 설계만 완료, 착수 보류.** 5주차 과제로는 안 씁니다(통제 변수 붕괴 + 범위 밖 + 시간). 트리거는 5주차 종료 후 별도 글, 또는 **쿼터가 `0`인 채 6주차 EKS가 막히면 비상 대안**. [`docs/plans/2026-09-01-unified-memory-vs-vram.md`](./plans/2026-09-01-unified-memory-vs-vram.md)

## Open Risks

- ⚠️ **과제 미공유 1회 = 제명. 4주차 마감(2026-08-30 09:00)이 이미 지났고 공유 여부를 확인하지 못했습니다.** 3주차까지 3회는 전부 통과. 다음 마감은 5주차 **09-06(일) 09:00**.
- **스터디 노션 원문(`gasidaseo` 워크스페이스)은 MCP 커넥션으로 안 잡힙니다** (2026-08-30 확인). `notion-fetch`는 404, `get-teams`는 `최병민 HQ` 하나뿐. **브라우저(Claude in Chrome)로만 열립니다** — 그마저도 기존 탭이 다른 계정 컨텍스트를 잡으면 "사용 권한 없음"이 뜨므로 **새 탭에서 열 것.** 페이지가 크면 가상 스크롤 때문에 한 번에 다 안 읽히니 스크롤하며 모아야 합니다.
- ★ **`vllm/vllm-openai:v0.23.0`은 docker에 없고 k3s containerd에만 있습니다** (2026-08-27 확인). 런북의 `docker run --rm vllm/vllm-openai:v0.23.0 --help`를 그대로 돌리면 **~10GB를 새로 받습니다.** 설계의 "추가 다운로드 0" 전제가 여기서 깨집니다. `kubectl run` + `imagePullPolicy: IfNotPresent`로 대체하고, 실험은 2주차 B1과 같은 **k3s 실행 경로**를 유지합니다(docker로 갈아타면 B1 기준선과 다른 저울이 됩니다).
- ~~디스크 여유~~ → **이번 주 리스크 아님** (2026-08-27 실측: WSL `/` 780G avail, C: 198.4GB, GPU 0 MiB 사용). 3주차 잔해는 docker에 48.5GB 남아 있으나 실험은 containerd를 쓰므로 지울 이유가 없습니다. 경계는 *"docker에 새 이미지를 받지 않는다"* 로 이동.
- ⚠️ **공백이 또 반복됐습니다** — 08-16 → 08-21 닷새. 이번에는 측정이 계획 추정보다 훨씬 빨라(벤치마크 1회 약 4분, `serveConfigV2` 롤아웃 20~60초) 한 세션에 셋을 다 넣었지만, 운이 좋았던 것에 가깝습니다. 4주차는 측정을 주중 앞쪽으로.
- ~~`Maximum concurrency` 변동 원인 미확인~~ → **부분 규명.** `max_num_seqs`를 키우면 활성화 피크가 커져 KV 예산을 갉아먹습니다(0.26→0.48 GiB ⇒ KV 7.00→6.79 GiB). KV 예산은 정적 공식이 아니라 **기동 시 프로파일링 결과**입니다. 다만 이번 변동은 3%라 **2주차의 2배(59.50↔28.77)는 여전히 미확인**입니다.
- **`vllm:*` 메트릭은 데이터 플레인 계층에서만 사라집니다.** Ray Serve(`:8000/metrics` 404)·Triton 둘 다 0개인데, KServe(RawDeployment)는 66개가 그대로 남습니다 — KServe는 요청 경로에 없기 때문입니다. 서버 측 교차검증이 필요한 실험은 KServe나 계층 없는 구성 위에서 설계하세요.
- ~~Grafana 스크린샷 미확보~~ → **해소.** Prometheus 콘솔 캡처 3장을 `articles/screenshots/proof-0{1,2,3}-*.jpg`로 확보했습니다. `b1-timeline.txt`의 구간 시각 덕분에 부하가 끝난 **여섯 시간 뒤에** 되짚어 찍을 수 있었습니다.
- **백그라운드 태스크가 이 환경에서 반복 강제 종료됩니다.** keeper가 죽으면 WSL이 VM을 내려 k3s 파드가 `Completed`/`Unknown`이 되고 측정이 끊깁니다. **긴 측정은 여전히 포그라운드로.**
  - ✅ **keeper는 창을 지키지 않아도 됩니다** (2026-08-27 해결·검증). `Start-Process wsl.exe -ArgumentList '-d','Ubuntu','-u','root','--','sleep','infinity' -WindowStyle Hidden -PassThru` — **독립 Windows 프로세스**라 에이전트 세션이 끝나도 살아남습니다(100초 유휴 후 생존 확인). 재부팅하면 다시 띄우세요.
  - ❌ **`.wslconfig`의 `vmIdleTimeout=-1`은 이 버전(WSL 2.7.8.0)에서 안 먹습니다.** `[wsl2]`·`[experimental]` 양쪽, BOM 제거, `wsl --shutdown` 재적용까지 해봤지만 100초 뒤 그대로 내려갔습니다. **원인이 유휴 타이머가 아니라 "distro에 살아 있는 세션이 없으면 내린다"** 이기 때문이고, systemd로 k3s가 `active`여도 마찬가지입니다. `.wslconfig`는 원복했습니다.
- **`make check-labs`가 이 머신에서 그대로 안 됩니다** (위 Baseline 참조).
- ★ **"게이트가 X를 감시한다"는 문서의 주장을 그대로 믿지 마세요.** 2026-09-01에 `test_manifest.py` 15건이 `Makefile:25`에서 누락돼 **한 번도 실행되지 않고 있었음**을 발견했습니다(이 문서가 106건이라 적는 동안 실제로는 91건). `meta.summary_method` 회귀 검사 부재에 이어 **두 번째 사례**입니다. 게이트 주장을 인용하기 전에 `make check` 출력의 실제 건수를 확인하세요.
- ★ **`vllm:iteration_tokens_total`을 "스텝당 스케줄된 토큰"으로 읽으면 안 됩니다.** 프리필이 **끝난 시점에 그 요청의 `computed` 토큰을 통째로** 기록합니다(`v1/metrics/loggers.py:1163` + `stats.py:270`). 그래서 `--max-num-batched-tokens 512`인데도 2,405토큰 프리필이 `le=4096` 버킷에 한 건으로 잡혀 **청킹이 안 된 것처럼 보입니다.** 실제 클램프는 `scheduler.py:410`의 `min(num_new_tokens, token_budget)`에 있습니다. token_budget 증거로 이 지표를 쓰지 마세요 (2026-08-29 오독 후 소스로 규명).
- **Prometheus 되짚어 찍기는 짧은 버스트 측정에 잘 안 맞습니다.** retention 1주라 데이터는 남지만, 08-27 측정이 70초짜리 버스트 6개 + 그 사이 파드 6회 롤아웃이라 ① DCGM 게이지가 스크랩 사이 0으로 끊기고 ② 적중률 같은 **비율 쿼리는 `pod` 라벨이 구성마다 달라 매칭이 안 됩니다.** 화면 증거가 필요하면 되짚기보다 **서버를 다시 띄우는 편**이 빠릅니다(기동 70~90초).
- **GPU·8000 포트가 하나씩뿐.** B1·B2 / C1 / C2 / C3는 서로 배타적입니다. 세션 전환 시 앞의 것을 안 내리면 다음 실험이 OOM으로 안 뜹니다.
- **KV cache 크기가 롤아웃마다 흔들립니다.** 같은 `slots=64`인데 `Maximum concurrency`가 59.50x / 28.77x로 갈렸습니다. 직전 파드의 VRAM 반환 지연이 유력하나 **미확인**. 롤아웃 직후 이 로그 줄을 반드시 확인하세요 — 조용히 절반이 되면 처리량 천장도 절반입니다.
- ⚠️ **디스크가 꽉 차면 WSL이 통째로 멈춥니다.** Triton vLLM 이미지(36.3GB)를 받다가 C: 잔여 공간이 0.1GB가 됐고, ext4.vhdx가 더 못 늘어나 `libacl.so.1: Input/output error`와 함께 k3s까지 죽었습니다. **큰 이미지를 받기 전에 `df -h`와 Windows 드라이브 여유를 먼저 확인하세요.** 복구는 WSL 안에서 `docker rmi` → `wsl --shutdown` 순입니다.
- **GPU 1장에서 롤링 업데이트는 교착합니다.** 새 파드가 GPU를 기다리는데 옛 파드가 쥐고 있어 양쪽이 멈춥니다. 옛 ReplicaSet을 `scale --replicas=0`으로 내려야 진행됩니다. KServe처럼 컨트롤러가 Deployment를 되돌리는 경우 전략 패치는 소용없습니다.
- **c=64 재현 측정은 10%까지 흔들립니다.** 같은 서버를 같은 설정으로 두 번 재서 확인했습니다(c≤32는 1.3% 안). **c=64에서 10%대 차이를 결론의 근거로 쓰지 마세요.**
- **계층마다 품은 vLLM 버전이 다릅니다** — Ray Serve 0.7.2 / Triton 0.5.5 / KServe 0.20.0. 계층 비용을 재려면 **같은 이미지에서 계층만 뺀 짝**이 반드시 필요합니다. 짝이 맞았는지는 기동 로그의 KV 예산으로 확인합니다.
- **교재 CH5의 KV 공식은 MHA 전제입니다** (`2 × 층수 × 어텐션 헤드 수 × head_dim × 정밀도`). Qwen2.5-1.5B는 **GQA**라 그대로 쓰면 안 맞습니다 — 손계산 시 `num_key_value_heads`를 쓸 것. 교재가 *"이후 장에서 MQA·GQA·MLA 소개"* 라 예고한 장이 곧 **이번 주 CH6**이라, 이 어긋남을 3주차 글의 핵심 절로 배치했습니다.
- **C1이 노션 CH3 원문 대조로 재설계됐습니다.** 교재 서버는 `main.py:63/69/74`가 `async def` 안에서 동기 호출을 해 이벤트 루프가 막히고 동시 요청이 순차 처리됩니다. 배칭 축을 `--prompts-per-request`로 바꿨고, 동시성은 `async def`→`def` 수정 전후 비교로 씁니다. **이 발견 자체가 02편의 핵심**입니다.
- **PDF 인덱스 재생성 사고** — `build_pageindex.py`를 `--only md` 없이 돌리면 LLM 한국어 요약이 날아갑니다. 게이트는 스키마만 보므로 이 회귀를 **잡지 못합니다**(`meta.summary_method` 회귀 검사는 미도입). 복구는 `enrich_summaries.py` 재실행(해시 캐시 있어 거의 공짜).
- ⚠️ **AWS GPU 쿼터가 `0`으로 확인됐습니다** (2026-08-23 CLI 조회, us-east-1·ap-northeast-2 둘 다. 신청 이력 없음). **지금 상태로는 GPU 인스턴스를 아예 못 띄웁니다.** 6주차(09-06) EKS 실습이 여기 걸려 있습니다. 신청은 사용자가 콘솔에서 직접(us-east-1 / `L-DB2E81BA` / 값 32).
- **4주차는 GPU 1장 범위로 확정** (2026-08-23). 멀티GPU 도전과제(TP/PP·2노드·MoE EP·실제 PD 분리)와 SGLang·TensorRT-LLM은 이번 주 제외 — 글의 한계 절에 "왜 못 재는지"로 명시.
