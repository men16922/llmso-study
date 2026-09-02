# Status

Last Updated: 2026-09-03

## Current Baseline

**게이트 green.** `make check` = 문서 검사 3종(`links` / `index` / `tools`) + `labs/` 단위 테스트 **120건**, 전부 오프라인·결정론적, 약 2초. ★ **2026-09-02에 `test_summarize_trace.py` 14건을 추가하면서 `Makefile:25`에 파일명도 같이 넣었습니다** — 09-01에 `test_manifest.py`가 그 자리에서 빠져 91건만 돌던 사고를 되풀이하지 않으려고 추가와 배선을 한 커밋에 묶었습니다(아래 Open Risks).

> ⚠️ **게이트 실행 가능 여부는 머신마다 다릅니다.** **macOS 세션에서는 `make check`가 그대로 통과합니다**(2026-08-30 확인). **Windows/WSL 랩톱**(측정 머신)에서는 안 됩니다 — WSL의 `python3`(3.14)에 **pip 자체가 없고** pytest도 없으며, Windows 셸에는 GNU make가 없습니다. 그쪽에서는 `PYTHONIOENCODING=utf-8 py -3 scripts/check_docs.py` + pytest를 분리 실행하세요(2026-08-15에 Windows Python 3.12에 `pytest`·`pyyaml`을 설치해 확인).

- `knowledge/` — 번호 문서 `00`~`06` + `subpages/` 11종 + `references/` 6종. 상대 링크·앵커 전부 유효.
- `index/` — PDF 3종 + 마크다운 묶음(66개 문서) 인덱스. 스키마 검증 통과. 현재 Inference Engineering만 `llm-claude-code-korean`으로 보강됨, 나머지는 `extractive-*`.
- `labs/` — 6개. `wsl2-vllm-baseline`(85 = 벤치 56 + `test_manifest.py` 15 + **`test_summarize_trace.py` 14**) · `cloudrun-gemma4-vllm`(6) · `triton-dynamic-batching`(19) · `rayserve-on-k8s`(10) + **`triton-vllm-backend`·`kserve-on-k8s`**(매니페스트만, 테스트 없음). 테스트는 전부 mock·순수 로직이라 GPU·네트워크 불필요. **게이트 120건.**
- `k8s/vllm-baseline.yaml`에 **`EXTRA_ARGS` env 신설**(2026-08-27). 실험별 플래그가 들어가는 유일한 자리. args에서 **따옴표 없이** 전개돼야 하고(셸 단어 분리), `test_manifest.py`가 그것을 감시합니다.
- `articles/` — Cloud Run Gemma 4(1주차), CH3·CH4 시나리오 4편, `두 글을 잇는 선`, **2주차 과제 2편(발행 완료)**, 3주차 실습 시나리오 5편 + **3주차 과제 글 `서빙 최적화, 설정부터 만지면 안 되는 이유`(발행 완료)**, 4주차 실습 시나리오 6편(`4주차-00`~`-04`, **런북의 docker 명령을 kubectl로 정정 완료**) + **4주차 과제 글 `워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식`(429줄) — humanize A·노션 갱신 완료.** 3주차 발행본처럼 질문→측정→해석→운영 판단 흐름으로 정리하고 중립형 제목까지 적용.
- `articles/figures/` · `articles/screenshots/` — 그래프 **8종**(SVG, `fig-e1-spec-decode` 추가 — 추측 디코딩이 0% 선을 두 번 가로지르는 그림) + 실습 인증 캡처 **13장**(Ray Dashboard·Prometheus·Grafana DCGM + **4주차 `proof-w4-01~04`**: Prometheus target UP · spec_decode 위치별 수용 · prefix cache 적중 · GPU 메모리에 찍힌 두 번의 기동).
- `tools/` — 인덱싱 3종 + **`make_figures.py`**(결과 JSON → SVG) + **`md_to_notion.py`**(마크다운 → 노션 변환). 둘 다 외부 의존성 없음.
- **4주차 측정 원본** (2026-08-27) — `labs/wsl2-vllm-baseline/results/`에 `e-vllm-help.txt`(플래그 확정 근거) · `e0-smoke.json` · `e1-{vanilla,ngram}.json` + 기동로그·메트릭 · `e1-accept-*`(워크로드별 수용률) · `e2-mnbt{512,8192}-*` · `e3-cache{on,off}-{shared,unique}.json` + 적중률 · `e4-scheduler.py`. **분석 2종: [`e-analysis.md`](../labs/wsl2-vllm-baseline/results/e-analysis.md) · [`e4-scheduler-notes.md`](../labs/wsl2-vllm-baseline/results/e4-scheduler-notes.md).**
- **측정 원본** — `labs/wsl2-vllm-baseline/results/`에 2주차 B1·B2 8종 + **3주차 계층 3종과 각각의 짝**: `c3-rayserve-*`·`b3-*`·`b-direct-v072-*`(Ray Serve 짝) / `c3-triton-vllm-seqs64`·`b-direct-v055-*`(Triton 짝) / `c3-kserve-vllm-seqs64`·`b-direct-v0200-*`(KServe 짝) + `metrics-*.txt` 6종, 분석 3종. C2는 `labs/triton-dynamic-batching/results/` 16종.
- `study/` — 노션 원문 로컬 사본. **gitignore + 인덱스 제외** (멤버 전용 자료). `Ch1~Ch10.md` + `LLM기초.md`. `Ch10.md`는 라이브 노션 페이지와 **전량 일치**함을 대조로 확인했습니다(라이브-only 라인 0건).
  - ✅ **2026-09-02에 `.gitignore`의 `study/` 줄을 복구하고, 그 사이 커밋돼 있던 9개(`Ch1~Ch8` + `LLM기초`)를 `git rm --cached`로 해제했습니다.** 이제 가드레일이 실제로 섭니다. ⚠️ 다만 **`Ch9.md`·`Ch10.md`는 이 Windows 머신에 없습니다** — 맥 세션에서만 받았고 gitignore 대상이라 동기화되지 않습니다. 원문 인용이 필요하면 맥 세션이나 노션에서 확인하세요.

스터디 진행: **1·2·3주차 완료·제출 완료** (3주차 마감 08-23 통과). **4주차(CH7·CH8) — 측정·글·노션 발행 완료, ⚠️ 링크 공유 여부 미확인(마감 08-30 09:00 경과).** **5주차(CH9·CH10) 착수 — 마감 09-06 09:00, ⚠️ ⓪ 선행 미착수로 이틀 지연.**

## Active Focus

Authority: `docs/NEXT_PLAN.md`.

0. ⚠️ **4주차 ⑦ 링크 공유 — 마감(08-30 09:00) 경과, 공유 여부 여전히 미확인.** 사용자만 확인할 수 있습니다. 미공유 1회 = 제명.
1. **5주차 (CH9·CH10) — 측정 전량 완료, 글 완성. 남은 것은 ⑥ 노션 발행 + ⑦ 링크 공유.** 마감 **2026-09-06 09:00**.
   - 글 **[`articles/처리량이 올랐다면 무엇이 빨라진 것인가.md`](../articles/처리량이 올랐다면 무엇이 빨라진 것인가.md)** (589줄) — 그림 `fig-f1-kv-budget-curve.svg` + 인증샷 **`proof-w5-01~09`**(터미널 로그 카드 6장 + **Prometheus 대시보드 3장**).
   - ★ **대시보드 증거는 되짚어 못 찍습니다.** 스크랩 주기 15초 vs 측정 버스트 10~20초라 F1d의 KV 사용률 피크 0.998이 기록에는 0.078로만 남습니다. 같은 대비를 구간당 3분씩 다시 걸어 캡처했습니다(`run_f5.sh`). 대시보드가 본 FP8 이득 **+33.2%**가 클라이언트의 +33.7%와 맞고, **실행 요청 수가 양쪽 16으로 같아** "배칭 덕"이라는 해석이 화면에서 닫힙니다.
   - **결론**: 양자화가 만든 +33.7% 중 **KV 예산 기여분은 0%**. 예산을 BF16과 같은 자리로 되돌려도(60.95x vs 59.50x) 이득이 **+33.8%로 그대로** 남았습니다. 줄어든 시간은 프로파일러에서도 전부 **선형 계층**(GEMM −27.7%)이고 **어텐션·KV 경로는 −0.1%**입니다.
   - **교재와 다른 결과 1건**: CH9은 양자화 전후 GEMM 커널 시간이 거의 같았다고 적었지만, 여기서는 27.7% 빨라졌습니다. 커널이 바뀌었기 때문입니다(Ada FP8 텐서코어 `enable_sm89_to_sm90`). 저장만 줄이는 W4A16 계열과 계산까지 낮추는 W8A8을 "양자화"로 묶으면 원인을 잘못 짚습니다.
   - **4주차 판단 1건 정정**: draft-0.5B를 "KV 예산 −42.2%라 원인 분리 불가"로 뺐던 것은 근거가 없었습니다. 그 34.38x는 이번 스윕 구간 안이고 그 구간의 처리량 변동은 0.5%입니다.
   - F3(복제 2개)는 **미착수** — GPU 1장에 파드 둘을 올리려면 device plugin 우회가 필요해 우선순위를 낮췄습니다. 도전과제 954·955 미커버.
2. **AWS GPU 쿼터 신청** — 사용자가 콘솔에서 직접. **6주차(09-06) EKS가 걸려 있어 이번 주가 사실상 마감.**
3. **통합 메모리 vs VRAM 비교(G 시리즈) — 설계만 완료, 착수 보류.** [`docs/plans/2026-09-01-unified-memory-vs-vram.md`](./plans/2026-09-01-unified-memory-vs-vram.md)

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
- ★ **"게이트가 X를 감시한다"는 문서의 주장을 그대로 믿지 마세요.** 2026-09-01에 `test_manifest.py` 15건이 `Makefile:25`에서 누락돼 **한 번도 실행되지 않고 있었음**을 발견했습니다(이 문서가 106건이라 적는 동안 실제로는 91건). `meta.summary_method` 회귀 검사 부재에 이어 **두 번째 사례**입니다. 게이트 주장을 인용하기 전에 `make check` 출력의 실제 건수를 확인하세요. **2026-09-02에 `test_summarize_trace.py`를 넣을 때는 추가와 `Makefile` 배선을 한 커밋에 묶어 세 번째 사례를 막았습니다.**
- ★ **`vllm:iteration_tokens_total`을 "스텝당 스케줄된 토큰"으로 읽으면 안 됩니다.** 프리필이 **끝난 시점에 그 요청의 `computed` 토큰을 통째로** 기록합니다(`v1/metrics/loggers.py:1163` + `stats.py:270`). 그래서 `--max-num-batched-tokens 512`인데도 2,405토큰 프리필이 `le=4096` 버킷에 한 건으로 잡혀 **청킹이 안 된 것처럼 보입니다.** 실제 클램프는 `scheduler.py:410`의 `min(num_new_tokens, token_budget)`에 있습니다. token_budget 증거로 이 지표를 쓰지 마세요 (2026-08-29 오독 후 소스로 규명).
- **Prometheus 되짚어 찍기는 짧은 버스트 측정에 잘 안 맞습니다.** retention 1주라 데이터는 남지만, 08-27 측정이 70초짜리 버스트 6개 + 그 사이 파드 6회 롤아웃이라 ① DCGM 게이지가 스크랩 사이 0으로 끊기고 ② 적중률 같은 **비율 쿼리는 `pod` 라벨이 구성마다 달라 매칭이 안 됩니다.** 화면 증거가 필요하면 되짚기보다 **서버를 다시 띄우는 편**이 빠릅니다(기동 70~90초).
- **GPU·8000 포트가 하나씩뿐.** B1·B2 / C1 / C2 / C3는 서로 배타적입니다. 세션 전환 시 앞의 것을 안 내리면 다음 실험이 OOM으로 안 뜹니다.
- **KV cache 크기가 롤아웃마다 흔들립니다.** 같은 `slots=64`인데 `Maximum concurrency`가 59.50x / 28.77x로 갈렸습니다. 직전 파드의 VRAM 반환 지연이 유력하나 **미확인**. 롤아웃 직후 이 로그 줄을 반드시 확인하세요 — 조용히 절반이 되면 처리량 천장도 절반입니다.
- ★ **대시보드를 Windows 브라우저로 여는 경로는 세 군데서 막힙니다** (2026-09-03 규명, `_workspace/2026-09-02-001/prom_shot.py`·`labs/wsl2-vllm-baseline/_pf_dashboards.sh` 주석). ① **NodePort 30001/30002는 안 잡힙니다** — kube-proxy가 iptables 규칙만 두고 listening 소켓을 안 만들어 WSL2 localhost 포워딩이 중계할 대상을 못 찾습니다. `kubectl port-forward`(127.0.0.1 바인딩)로 대체하세요. ② **9090은 Windows 예약 포트 범위(9021~9120)** 라 막힙니다 — 9009 사용. ③ **Prometheus 3.x는 `/query?g0.tab=graph&g0.res_type=auto`** 라야 쿼리가 실행됩니다(`/graph?g0.tab=0`은 빈 패널). **Grafana는 로그인이 필요해 에이전트가 캡처할 수 없습니다**(익명 접근 꺼짐).
- ⚠️ **디스크가 꽉 차면 WSL이 통째로 멈춥니다.** Triton vLLM 이미지(36.3GB)를 받다가 C: 잔여 공간이 0.1GB가 됐고, ext4.vhdx가 더 못 늘어나 `libacl.so.1: Input/output error`와 함께 k3s까지 죽었습니다. **큰 이미지를 받기 전에 `df -h`와 Windows 드라이브 여유를 먼저 확인하세요.** 복구는 WSL 안에서 `docker rmi` → `wsl --shutdown` 순입니다.
- **GPU 1장에서 롤링 업데이트는 교착합니다.** 새 파드가 GPU를 기다리는데 옛 파드가 쥐고 있어 양쪽이 멈춥니다. 옛 ReplicaSet을 `scale --replicas=0`으로 내려야 진행됩니다. KServe처럼 컨트롤러가 Deployment를 되돌리는 경우 전략 패치는 소용없습니다.
- **c=64 재현 측정은 10%까지 흔들립니다.** 같은 서버를 같은 설정으로 두 번 재서 확인했습니다(c≤32는 1.3% 안). **c=64에서 10%대 차이를 결론의 근거로 쓰지 마세요.**
- **계층마다 품은 vLLM 버전이 다릅니다** — Ray Serve 0.7.2 / Triton 0.5.5 / KServe 0.20.0. 계층 비용을 재려면 **같은 이미지에서 계층만 뺀 짝**이 반드시 필요합니다. 짝이 맞았는지는 기동 로그의 KV 예산으로 확인합니다.
- **교재 CH5의 KV 공식은 MHA 전제입니다** (`2 × 층수 × 어텐션 헤드 수 × head_dim × 정밀도`). Qwen2.5-1.5B는 **GQA**라 그대로 쓰면 안 맞습니다 — 손계산 시 `num_key_value_heads`를 쓸 것. 교재가 *"이후 장에서 MQA·GQA·MLA 소개"* 라 예고한 장이 곧 **이번 주 CH6**이라, 이 어긋남을 3주차 글의 핵심 절로 배치했습니다.
- **C1이 노션 CH3 원문 대조로 재설계됐습니다.** 교재 서버는 `main.py:63/69/74`가 `async def` 안에서 동기 호출을 해 이벤트 루프가 막히고 동시 요청이 순차 처리됩니다. 배칭 축을 `--prompts-per-request`로 바꿨고, 동시성은 `async def`→`def` 수정 전후 비교로 씁니다. **이 발견 자체가 02편의 핵심**입니다.
- **PDF 인덱스 재생성 사고** — `build_pageindex.py`를 `--only md` 없이 돌리면 LLM 한국어 요약이 날아갑니다. 게이트는 스키마만 보므로 이 회귀를 **잡지 못합니다**(`meta.summary_method` 회귀 검사는 미도입). 복구는 `enrich_summaries.py` 재실행(해시 캐시 있어 거의 공짜).
- ⚠️ **AWS GPU 쿼터가 `0`으로 확인됐습니다** (2026-08-23 CLI 조회, us-east-1·ap-northeast-2 둘 다. 신청 이력 없음). **지금 상태로는 GPU 인스턴스를 아예 못 띄웁니다.** 6주차(09-06) EKS 실습이 여기 걸려 있습니다. 신청은 사용자가 콘솔에서 직접(us-east-1 / `L-DB2E81BA` / 값 32).
- **4주차는 GPU 1장 범위로 확정** (2026-08-23). 멀티GPU 도전과제(TP/PP·2노드·MoE EP·실제 PD 분리)와 SGLang·TensorRT-LLM은 이번 주 제외 — 글의 한계 절에 "왜 못 재는지"로 명시.
