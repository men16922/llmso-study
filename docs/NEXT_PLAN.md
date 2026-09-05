# Next Plan

Last Updated: 2026-09-03

> ⚠️ **4주차 마감(2026-08-30 09:00)이 지났습니다.** 글·노션 발행은 끝났고 **⑦ 링크 공유만 사용자 몫**이었습니다 — **공유했는지 먼저 확인하세요.** 미공유 1회 = 제명. 아래 Priority 5.
>
> ▶ **5주차 (CH9·CH10) — 측정 전량 완료 · 글 완성 (2026-09-02).** 남은 것은 **⑥ 노션 발행 + ⑦ 링크 공유**. 마감 **2026-09-06(일) 09:00**.
> 축은 **"빨라졌다"의 원인 귀속** — 설계·시간표·중단 기준은 [`docs/plans/2026-08-30-week5-attribution.md`](./plans/2026-08-30-week5-attribution.md)(**2026-09-02 §5~§9 개정**).
> ★ **결과**: 양자화가 만든 **+33.7%** 중 **KV 예산 기여분은 0%**였습니다(예산을 되돌려도 +33.8% 유지). 프로파일러·Prometheus 대시보드가 같은 말을 합니다. **F3는 미착수**(근거는 `docs/DECISIONS.md` 2026-09-02 (2)), **F4는 잘라냈습니다**.

열린 작업만 담는 롤링 플랜입니다. 완료 이력은 `docs/COMPLETED_SUMMARY.md`.

> **이 저장소에서 `[auto]`가 드문 이유**: 게이트는 링크·스키마·문법만 증명합니다. 스터디 문서의 **내용이 맞는가**(교재 챕터 대응, PDF 쪽수 인용)는 원문 대조가 필요해 오프라인으로 검증할 수 없습니다. 그래서 문서 집필은 원칙적으로 `[manual]`이고, `[auto]`는 게이트 자체를 두껍게 만드는 작업에 집중됩니다.

## Priority 0 — 5주차 (CH9·CH10) · 마감 2026-09-06 (일) 09:00

스터디일 2026-08-30(모임 20:30, 종료). 범위는 **CH9 LLM Optimization in Practice** + **CH10 Advancements in LLM Serving**.

설계·근거·한계·실험 설계·시간표·중단 기준은 **[`docs/plans/2026-08-30-week5-attribution.md`](./plans/2026-08-30-week5-attribution.md)**. 여기에는 체크리스트만 둡니다.

**글의 축**: `study/Ch9.md:9`의 첫 질문 — *"처리량이 올랐다는 건 GPU가 더 빨리 계산해서인가, 아니면 그냥 덜 다시 계산해서인가?"* 4주차가 **조건**(언제 이득인가)을 쟀다면 5주차는 **인과**(왜 이득인가)를 귀속시킨다.

★ **확인이 아니라 반증으로 물었고, 답이 나왔습니다** (2026-09-02 개정 → 09-02~03 측정). 교재 주장이 맞다면 예산을 도로 깎을 때 이득이 사라져야 하는데, **깎아도 +33.8%가 그대로 남았습니다.** 예산 기여분 0%.

**범위 확정**: 랩톱 GPU 1장(RTX 4080 Laptop 12GB)만. CH9 본편(Qwen3-14B · L40S · A100 x8)은 **AWS 쿼터 `0`이라 재현 불가** — 한계 절에 "왜 못 재는지"로 명시. TP=2·PP=2·MoE EP·NVLink 비교도 제외.

**완료분(2026-09-02~03)은 여기서 뺐습니다** — ⓪ 선행 4건 · F1a·F1b·F1c·F1d·F2·F5 · 그림 · 글까지 끝났습니다. 결과와 수치는 [`docs/PROGRESS_LOG.md`](./PROGRESS_LOG.md) 2026-09-02 (2)·2026-09-03 항목과 [`labs/wsl2-vllm-baseline/results/f-analysis.md`](../labs/wsl2-vllm-baseline/results/f-analysis.md)에 있습니다. 여기에는 **열린 것만** 둡니다.

- [x] [manual] **⑥ 노션 발행 — 완료** (2026-09-03, 사용자 요청). <https://app.notion.com/p/3d04c2420ac481c89ce1de666fbf9fbe> · `CloudNetaStudy` 아래, 4주차 페이지와 형제. 이미지 4장(SVG 그림 1 + Prometheus 캡처 3)을 `create-file-upload`로 올리고 `file-upload://` 참조로 삽입. 콜아웃 1·토글 3·표 17. 발행용 변환본은 `_workspace/2026-09-02-001/notion/publish.md`. **2026-09-04 humanize(heavy·리포트·적극, 등급 A) 반영본으로 같은 페이지를 교체.**
- [ ] [manual] **⑦ 링크 공유** ★ **사용자가 직접 — 에이전트 권한 밖**(제출표가 스터디 멤버 전용 워크스페이스라 이 노션 연결로 안 잡힙니다). 마감 **09-06(일) 09:00**.
- [ ] [manual] **(선택) Grafana 패널 캡처** — 로그인이 필요해 에이전트가 못 합니다. 사용자가 로그인하면 DCGM 대시보드를 캡처해 글 5-B장에 붙일 수 있습니다. 포트포워딩은 `labs/wsl2-vllm-baseline/_pf_dashboards.sh`.
- [ ] [manual] **(이월) F3 — 복제 2개.** GPU 1장에 파드 둘을 올리려면 device plugin이 광고하는 `nvidia.com/gpu: 1`을 우회해야 해 **매니페스트를 고쳐야** 하는데, 이번 주 통제 변수가 *"매니페스트 수정 0"* 이었습니다. 근거는 [`docs/DECISIONS.md`](./DECISIONS.md) 2026-09-02 (2). **CH10 도전과제 954·955 미커버** — 되살릴 때는 별도 매니페스트(`k8s/vllm-replica2.yaml`)로.

**⚠️ 통제 변수**: 4주차 저울을 그대로 씁니다 — `vllm/vllm-openai:v0.23.0` · k3s containerd 경로 · `EXTRA_ARGS` 한 곳 · 팔마다 KV 예산 기록 후 **비교 성립 판정 먼저**. `docker run` 금지.

**남은 일정**: 측정·글은 **2026-09-02~03에 전부 끝났습니다.** 남은 것은 ⑥ 발행 → ⑦ 공유뿐이고, 마감은 **09-06(일) 09:00**입니다. 발행은 외부 게시라 **사용자 확인 후에** 진행합니다.

## Priority 5 — 4주차 (CH7·CH8) · ⚠️ 마감 2026-08-30 09:00 **경과, 공유 확인 필요**

스터디일 2026-08-23(모임 20:30). 범위는 **CH7 Advanced LLM Optimization Techniques** + **CH8 LLM Serving Frameworks**.

설계·근거·함정·잘라내기 순서는 **[`docs/plans/2026-08-23-week4-conditional-optimization.md`](./plans/2026-08-23-week4-conditional-optimization.md)**,
**남은 시간에 이걸 어떻게 끝낼 것인가(시간표·명령·중단 기준)는 [`docs/plans/2026-08-27-week4-execution.md`](./plans/2026-08-27-week4-execution.md)**,
실행 런북은 **[`articles/조건부 최적화 실습 시나리오 (CH7·CH8)`](../articles/%EC%A1%B0%EA%B1%B4%EB%B6%80%20%EC%B5%9C%EC%A0%81%ED%99%94%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH7%C2%B7CH8%29.md)** 시리즈(00~04)에 있습니다. 여기에는 체크리스트만 둡니다.

> ✅ 측정·글·윤문·노션 발행은 완료했습니다. 아래 체크리스트에서 열린 작업은 **⑦ 링크 공유**뿐입니다.

**글의 축**: CH7이 스스로 밝힌 단일 기준 — **compute-bound vs memory-bound**. 네 기법이 전부 "조건부로만 이득"이고 조건이 하나의 축이다. 그 조건이 코드 어디에 있는지는 CH8(vLLM 스케줄러)이 답한다. 3주차 결론(*구조가 설정의 상한을 정한다*)의 다음 칸.

**범위 확정 (2026-08-23)**: 랩톱 GPU 1장만. 외부 GPU 없음. SGLang·TensorRT-LLM·멀티GPU 도전과제는 한계 절에 "왜 못 재는지"로 명시.

**⓪ 선행 (목 밤, 전부 `[auto]`)** — 상세는 실행 계획서 §6.

- [x] [auto] **⓪-1 keeper 띄우기 + 클러스터 복구** (2026-08-27, 검증 완료). `Start-Process wsl.exe ... 'sleep','infinity' -WindowStyle Hidden -PassThru` — **독립 Windows 프로세스**라 창을 지킬 필요가 없습니다(100초 유휴 후 생존 PASS). 파드 전부 `Running`, GPU `0 MiB`. ❌ `.wslconfig`의 `vmIdleTimeout=-1`은 WSL 2.7.8.0에서 **안 먹습니다**(원복함) — 원인이 유휴 타이머가 아니라 "세션이 없으면 내린다"라서. ⚠️ **재부팅하면 keeper를 다시 띄우세요.**
- [x] [auto] **⓪-2 플래그·메트릭 이름 확인** (2026-08-27). `results/e-vllm-help.txt`(1,714줄). ★ **v0.23.0은 JSON 대신 평탄화 플래그를 준다** — `--spec-method ngram` · `--spec-model` · `--spec-tokens`. `EXTRA_ARGS`의 단어 분리 함정을 통째로 피한다. `draft_model`이 `--spec-method` 선택지에 있어 **V1 지원 확인**. `--help`가 아니라 **`--help=all`**(그냥 `--help`는 그룹 이름만). help 뽑는 데도 GPU가 필요했다.
- [x] [auto] **⓪-3 `EXTRA_ARGS` 패치** (2026-08-27). args 끝에 따옴표 없는 `$EXTRA_ARGS` + 빈 문자열 env. `labs/wsl2-vllm-baseline/test_manifest.py` 신규 — **게이트 91건 → 106건 green.** 핵심 가드(`test_extra_args_is_unquoted`)는 일부러 따옴표를 씌워 **역방향으로 검증**했다.
- [x] [auto] **⓪-4 런북 정정** (2026-08-27). `4주차-00`~`-03`의 `docker` 계열 명령을 `redeploy`/`kubectl logs`로 전부 교체. `df -h` 절은 선택으로 강등하고 경계를 *"docker에 이미지를 받지 말 것"* 으로 이동.
- [x] [auto] **⓪-5 스모크** (2026-08-27). 처리량 −4.4%/+0.4%, ITL +4.3%/+0.1%로 2주차 B1과 일치. `Maximum concurrency 59.50x` 동일. ⚠️ **`e2e`만 −39%인데 이건 출력 길이 차이**(2주차 51.1토큰 → 36.0토큰, `temperature=0`인데도). **`e2e`·wall time은 세션 간 비교 금지.**
- [x] [auto] *(잘라냄)* **`benchmark.py` `quote` 시나리오** — 안 했습니다. `prefill`/`decode`만으로 워크로드 축이 섰습니다.

**측정 — 전부 완료 (2026-08-27 한 세션)**

- [x] [manual] **① E1 — 추측 디코딩** ★ vanilla/ngram × `decode`·`prefill` × c=1·4·16·64. **결과: `prefill` +199.3%(c=1) → −53.7%(c=64), `decode` 전 구간 −12~−29%.** ★★ **워크로드별 수용률을 따로 재서 가설이 뒤집혔다** — `prefill` c=64는 **수용률 100.0%인데 −53.7%**. 손해의 원인이 "추측이 틀려서"가 아니라 **"맞아도 쓸 예산이 없어서"**. 합산 수용률 68.7%로는 아무것도 설명 못 했다. KV 예산 vanilla 59.50x vs ngram 57.48x(−3.4%)로 비교 성립 확인.
- [x] [manual] **② E2 — chunked prefill.** 512 / 8192. **ITL 간섭은 청크와 무관(+16.3% vs +16.6%)한데 디코드 TTFT만 18배 갈림(+10.5% vs +188.9%).** 계획의 예상과 반대 — 청크가 사는 건 ITL이 아니라 **진입 지연**. 청크 512에서도 ITL +16.3%가 남는 것이 **PD 분리의 동기**. ⚠️ 첫 시도는 간섭 0이 나왔는데 **부하가 안 겹친 설계 결함**이었다(프리필 1초 / 디코드 5초). 배경 부하로 바꾸고 겹친 초를 매 회 기록.
- [x] [manual] **③ E3 — prefix caching.** 2×2 · 64요청. **ON+공유만 다르다** — TTFT p50 8.0배·p95 11.3배·처리량 +71%, 적중률 97.9%. 나머지 세 칸은 구별 안 됨. **공유가 없으면 캐시는 이득도 손해도 아니다(1% 안).** 설명 못 한 관측 1건은 부록 B에(순서 효과 아님을 3회 반복으로 확인).
- [x] [manual] **④ E4 — vLLM 스케줄러 해부.** `results/e4-scheduler.py`(2,422줄) + `e4-scheduler-notes.md`. ★ **소스 주석이 글의 주장을 그대로 말한다** — *"general enough to cover chunked prefills, prefix caching, speculative decoding"*. 셋이 같은 `token_budget`을 각각 상한·시작점·끝점에서 건드린다.
- [x] [manual] **⑤ 글 작성** — `articles/켜면 이득인 최적화는 없다.md`. 8단계 구조 유지 + 부록 3종. 그림 `fig-e1-spec-decode.svg` 신규(`make_figures.py`의 `fig_cost`를 시나리오별 짝 비교로 확장).
- [x] [manual] **⑥ 노션 발행 — 완료** (2026-08-27). <https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234> · `CloudNetaStudy` 아래, 3주차 페이지와 형제. 표 8개·콜아웃 5개·목차·SVG 그림 정상. 1절의 "지난 글" 링크는 3주차 노션 페이지로 연결해 뒀습니다.
- [x] [manual] **⑥-b 발행본 형태로 전면 재구성 + 실습 인증샷** (2026-08-29). ★ **로컬 원고와 노션 발행본이 다른 문서였다는 것을 3주차 대조로 발견.** 발행 시 거치던 변환 5단계 중 ①요약→callout 3불릿 ②헤딩 평서 발견문화 ③환경·한계·부록 토글 ④`결론` 장을 §8에 흡수까지 적용(⑤제목 중립화는 미적용). 표현도 정리 — em-dash 40→24 · ★ 2→0 · 이탤릭 인용 7→0 · "팔"→"구성" 16곳. **인증샷 4장 신규**(`proof-w4-01~04`) — E1·E2 두 구성으로 서버를 다시 띄워 찍었고 **KV 예산이 08-27과 소수점까지 동일**(235,440/57.48x · 244,000/59.57x)해 부록 C에 재현 확인 절로 넣었습니다. 로컬·노션 양쪽 반영 후 되읽기로 손실 0 확인.
- [x] [manual] **⑥-c 구조·문체 명료화 + humanize A + 중립형 제목 반영** (2026-08-29). 제목을 `워크로드 조건이 vLLM 최적화 효과를 바꾸는 방식`으로 확정하고 질문→측정→해석→운영 판단 흐름을 강화했습니다. 변경률 24.14%·자체검증 6/6·등급 A. 노션 되읽기로 이미지 5·콜아웃 6·토글 3·표 12·코드 블록 7 유지, 수치 멀티셋 불일치 0.
- [ ] [manual] **⑦ 링크 공유** ★ **사용자가 직접 — 에이전트 권한 밖입니다.** 마감 **08-30(일) 09:00**. 미공유 1회 = 제명.
  - **왜 대신 못 하는가 (2026-08-27, 도구로 확인)**
    - ★ **제출표에 접근할 수 없습니다 — 이게 결정적입니다.** `notion-get-teams`에 팀스페이스가 **`최병민 HQ` 하나뿐**이고(사용자 소유), `notion-list-shared-pages`는 **비어 있습니다.** CloudNet@ 스터디의 멤버 전용 워크스페이스는 이 연결(개인 워크스페이스 `d3427551-…`)에 잡히지 않습니다. 슬랙 `llmso`도 동일.
    - 페이지의 **공개 여부는 판별하지 못했습니다.** 노션 자식 페이지는 부모 공유 설정을 상속하므로 3주차 페이지와 같은 부모 아래 있는 이 페이지도 이미 공개일 수 있으나, `WebFetch`가 SPA 셸만 돌려줘 확인 불가였습니다. **어느 쪽이든 공유 설정을 바꾸는 MCP 도구는 없습니다.**
  - **사용자가 할 일**: ㉠ 페이지가 공개인지 확인(아니면 **공유 → 웹에 게시**) ㉡ 스터디 노션의 **과제 제출표 → 본인 이름 → URL 추가** ㉢ 페이지 스크린샷 1장 업로드.
  - 발행된 페이지: <https://app.notion.com/p/3c94c2420ac48122a485ef00100c6234> (08-29 명료화·A등급 윤문본이 최신)
- [x] [manual] **E1 draft-0.5B 팔 — 측정 완료** (2026-08-28). ★ **비교 가능성 판정에서 탈락했고, 그 자체가 결과였습니다.** KV 예산 **140,832 tokens / 34.38x = vanilla 대비 −42.2%**(ngram은 −3.4%). 12GB에 1.5B+0.5B를 같이 올리면 예산의 42%가 사라집니다. 수용률 40.1%. `decode` c=64에서 **goodput 0.0%**(e2e p95 45.6초, SLO 30초 초과) — vanilla·ngram은 같은 지점에서 100%. **ngram이 3배를 내던 `prefill` c=1에서조차 −4.1%.** 글에 **부록 D**로 넣고 한계 #4를 교체했습니다.

**⚠️ 통제 변수**: E1·E2·E3를 **전부 `vllm/vllm-openai:v0.23.0` 하나 위에서, 2주차 B1과 같은 k3s 실행 경로로** 돈다. ray-llm(0.7.2, V0)로 새거나 docker로 갈아타면 그것만 다른 저울의 숫자가 된다 — 3주차에 데인 자리.

**일정 (재조정)**: 08-27(목) 밤 ⓪ / 08-28(금) 저녁 **E1→E2** / 08-29(토) 오전 E3+예비, 오후 E4·분석, 밤 초고 / 08-30(일) 06:00~09:00 윤문·발행·공유. **중단 기준은 실행 계획서 §7에 미리 정해 뒀습니다.**

## Priority 4 — 3주차 (CH5·CH6) · 완료 (마감 2026-08-23 통과)

결과 요약은 `docs/COMPLETED_SUMMARY.md`의 **M3**, 상세 이력은 [`docs/archive/progress-2026-08.md`](./archive/progress-2026-08.md)(08-22·08-23 항목), 설계·근거·함정은 [`docs/plans/2026-08-16-week3-triton-rayserve.md`](./plans/2026-08-16-week3-triton-rayserve.md)에 있습니다. 여기에는 **이월분만** 남깁니다.

- [ ] [manual] **③-b 도전과제 3 (chunked prefill)** — **다음 편 이월.** 다만 확인해둔 것: ray-llm 2.44.1의 vLLM 0.7.2는 **V0 엔진**이고 `chunked_prefill_enabled=False`가 기본이라 **ON/OFF 비교가 가능한 환경**이다(V1에서 기본 ON일 것을 걱정했으나 해당 없음).

## Priority 3 — 2주차 (CH3·CH4) · 완료

과제 제출은 `docs/COMPLETED_SUMMARY.md`의 **M2**, 실습 도구 일체는 **M4**, 상세 이력은 [`docs/archive/progress-2026-08.md`](./archive/progress-2026-08.md)(08-15·08-16 항목). 여기에는 **이월분만** 남깁니다.

- [ ] [auto] **`Makefile`의 `PY`를 이 머신에서 쓸 수 있게 만들기.** WSL의 `python3`(3.14)에 **pip 자체가 없어** `make check-labs`가 그대로 실패합니다. 2026-08-15에는 Windows Python 3.12에 `pytest`·`pyyaml`을 설치해 91건을 확인했습니다. Done: 이 머신에서 `make check`가 문서+labs 91건까지 한 번에 통과.
- [ ] [manual] **C1 선행 — WSL2에서 환경 준비.** ① 교재 저장소 `orca3/llm-model-inference` 클론 + `ch03/single_model_llm_serving` venv 설치(`vllm==0.9.0.1`, 8~10GB·30~40분) ② `model_worker.py:48`의 `max_new_tokens=50`을 20으로 맞춰 엔드포인트 간 출력 토큰 수 정렬. 이 정렬을 빠뜨리면 처리량 비교가 2.5배 왜곡됨.
- [ ] [manual] **C2 선행 — Triton 이미지 풀 + ONNX export.** 저장소의 `densenet_onnx`는 `max_batch_size: 0` + `reshape`로 배치 축이 1에 고정돼 **dynamic batching을 켤 수 없음**. `export_mobilenet_onnx.py --verify`로 배치 축 열린 mobilenet_v2를 뽑아야 함. 이미지 풀(~17GB)은 세션 1에서 백그라운드로.

## Priority 1 — 게이트 두껍게 만들기

- [ ] [auto] ★ **`study/Ch1~Ch8.md` + `LLM기초.md` 9개를 추적 해제** (`git rm --cached`). 2026-09-02에 `.gitignore`의 `study/` 줄은 복구했지만, 커밋 `ae10b8e "study"`에서 **이미 커밋된 9개는 계속 추적 중**이라 가드레일이 실제로는 서 있지 않습니다(멤버 전용 원문의 전재 — `knowledge/03-study-rules.md`). 디스크 파일은 그대로 두고 인덱스에서만 뺍니다. Done: `git ls-files study/`가 빈 출력.
- [ ] [auto] `meta.summary_method` 회귀 검사를 `scripts/check_docs.py`의 `index` 검사에 추가. LLM 보강이 끝난 문서가 `extractive-*`로 되돌아가면 실패해야 함 — 기대값을 저장소에 기록해두고 대조하는 방식. 이게 현재 게이트의 가장 큰 구멍(`docs/STATUS.md` Open Risks 참조). Done: 되돌린 상태를 만들면 `make check-index`가 exit 1.
- [ ] [auto] `scripts/check_docs.py` 자체 테스트 `scripts/test_check_docs.py` 작성 — 깨진 링크/앵커/펜스 안 예시/`%20` 인코딩/`<a id>` 명시 앵커 각각에 대한 케이스. 지금은 손으로만 역방향 확인했음. Done: `python3 -m pytest -q scripts/test_check_docs.py` 통과하고 `make check`에 편입.
- [ ] [auto] 마크다운 표의 열 개수 불일치 검사 추가 — 이 저장소는 표가 많아 실수가 잦음. Done: 고의로 깨진 표에 대해 exit 1.

## Priority 2 — 남은 준비물

- [ ] [manual] **AWS GPU 쿼터 증설 신청 — 사용자가 콘솔에서 직접.** 2026-08-23 CLI 조회로 **현재 값이 us-east-1·ap-northeast-2 둘 다 `0`이고 신청 이력도 없음**을 확인했습니다. 즉 **지금은 GPU 인스턴스를 아예 못 띄웁니다.**
  - 리전 **us-east-1** / 쿼터 `L-DB2E81BA` (`Running On-Demand G and VT instances`) / 신청 값 **32** (단위는 vCPU. `g6e.2xlarge`=8, `g6.12xlarge`=48)
  - 콘솔: `https://us-east-1.console.aws.amazon.com/servicequotas/home/services/ec2/quotas/L-DB2E81BA` → Request increase at account level
  - **CLI 말고 콘솔로 할 것** — `request-service-quota-increase`에는 사유 필드가 없는데 GPU 쿼터는 사유 유무가 승인 속도를 가릅니다.
  - 상세 절차·비용·정리 목록: **[`knowledge/07-aws-gpu-quota.md`](../knowledge/07-aws-gpu-quota.md)**. 6주차(09-06) EKS 실습용. 승인 여부는 CLI로 조회 가능.

- [ ] [manual] **통합 메모리 vs VRAM 비교 (G 시리즈) — 설계만 완료, 착수 보류.** 이 랩톱(M4 Max 48GB)과 WSL2 랩톱(RTX 4080 12GB)을 놓고 *"메모리도 3배 크고 대역폭도 높은데 왜 서빙에서는 지는가"* 를 묻습니다. 설계·교란 통제·중단 기준은 **[`docs/plans/2026-09-01-unified-memory-vs-vram.md`](./plans/2026-09-01-unified-memory-vs-vram.md)**.
  - ⛔ **5주차 마감(09-06 09:00) 전에는 착수 금지.** 과제가 우선입니다.
  - **5주차 과제로는 안 씁니다** — 통제 변수가 무너지고(5주차 축인 *원인 귀속*과 정반대), CH9·CH10 범위 밖이며, 남은 시간이 없습니다. 판단 근거는 계획서 §0.
  - 실행 트리거 둘 중 먼저 오는 것: **(A)** 5주차 ⑦ 종료 후 **별도 블로그 글** / **(B)** **AWS 쿼터가 `0`인 채 6주차 EKS가 막히면 비상 대안**(판단 시점 09-06 모임 직후, 위 쿼터 항목과 연동).
  - 비용 전제: `labs/wsl2-vllm-baseline/benchmark.py`가 **OpenAI 호환 + `--base-url`** 이라 맥 엔드포인트에 **코드 수정 0**으로 붙습니다. 이 전제가 깨지면(계획서 ⓪-2) 중단.

## Rules

- 작업 시작 전 `docs/AGENT_BRIEF.md` → `docs/STATUS.md` → 이 파일 순으로 읽으세요.
- 큰 작업의 설계 스냅샷은 `docs/plans/YYYY-MM-DD-<topic>.md`에 둡니다.
- **모든 문서는 한국어로.** `CLAUDE.md`의 깨지기 쉬운 지점·콘텐츠 정책을 먼저 확인하세요.

### Automation Tags (무인 루프용)

상태 박스(`[x]`/`[/]`/`[ ]`)와 별개 축으로, 무인 루프가 소비 가능한지를 나타냅니다.

- `[auto]` — 로컬·결정론적·오프라인 게이트(`make check`)로 검증 가능한 항목만.
- `[manual]` — 사람의 판단·감각·외부 서비스가 필요. 무인 루프는 건너뜁니다.
- `[blocked]` — 의존성 미충족 또는 Blocker 2회 누적(러너가 자동 표시). 사람이 검토 후 해제.
- **태그 없음 = 무인 실행 대상 아님** (보안 기본값). 러너는 `[auto]`만 소비합니다.
