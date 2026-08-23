# Next Plan

Last Updated: 2026-08-23

> ✅ **3주차 마감 통과** (2026-08-23 09:00). `서빙 최적화, 설정부터 만지면 안 되는 이유` 노션 발행 + 링크 공유 완료.
>
> ▶ **4주차 (CH7·CH8) 진행 중.** 마감 **2026-08-30(일) 09:00**.
> 축은 **조건부 최적화와 그 조건** — 설계는 [`docs/plans/2026-08-23-week4-conditional-optimization.md`](./plans/2026-08-23-week4-conditional-optimization.md).

열린 작업만 담는 롤링 플랜입니다. 완료 이력은 `docs/COMPLETED_SUMMARY.md`.

> **이 저장소에서 `[auto]`가 드문 이유**: 게이트는 링크·스키마·문법만 증명합니다. 스터디 문서의 **내용이 맞는가**(교재 챕터 대응, PDF 쪽수 인용)는 원문 대조가 필요해 오프라인으로 검증할 수 없습니다. 그래서 문서 집필은 원칙적으로 `[manual]`이고, `[auto]`는 게이트 자체를 두껍게 만드는 작업에 집중됩니다.

## Priority 0 — 4주차 (CH7·CH8) · 마감 2026-08-30 (일) 09:00

스터디일 2026-08-23(모임 20:30). 범위는 **CH7 Advanced LLM Optimization Techniques** + **CH8 LLM Serving Frameworks**.

설계·근거·함정·잘라내기 순서는 **[`docs/plans/2026-08-23-week4-conditional-optimization.md`](./plans/2026-08-23-week4-conditional-optimization.md)**,
실행 런북은 **[`articles/조건부 최적화 실습 시나리오 (CH7·CH8)`](../articles/%EC%A1%B0%EA%B1%B4%EB%B6%80%20%EC%B5%9C%EC%A0%81%ED%99%94%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH7%C2%B7CH8%29.md)** 시리즈(00~04)에 있습니다. 여기에는 체크리스트만 둡니다.

**글의 축**: CH7이 스스로 밝힌 단일 기준 — **compute-bound vs memory-bound**. 네 기법이 전부 "조건부로만 이득"이고 조건이 하나의 축이다. 그 조건이 코드 어디에 있는지는 CH8(vLLM 스케줄러)이 답한다. 3주차 결론(*구조가 설정의 상한을 정한다*)의 다음 칸.

**범위 확정 (2026-08-23)**: 랩톱 GPU 1장만. 외부 GPU 없음. SGLang·TensorRT-LLM·멀티GPU 도전과제는 한계 절에 "왜 못 재는지"로 명시.

- [ ] [auto] **⓪ 선행 — 플래그·메트릭 이름 확인.** `docker run --rm vllm/vllm-openai:v0.23.0 --help`로 `--speculative-config` 스키마 · prefix caching OFF 플래그 · `--max-num-batched-tokens` 하한 · `vllm:spec_decode_*` / `vllm:prefix_cache_*` 메트릭 이름을 **추측하지 말고 확인**. 3주차 `accelerator_type: null` 같은 조용한 실패를 막는 자리. ⚠️ **`df -h` 먼저.**
- [ ] [auto] *(선택)* **`benchmark.py`에 `quote` 시나리오 추가** — 긴 문서 + "그대로 인용하며 요약". ngram 수용률의 최선값을 보려면 이게 가장 확실합니다. 순수 데이터라 오프라인 테스트 가능. **필수는 아닙니다** — 기존 `prefill`/`decode` 두 시나리오만으로도 워크로드 축은 섭니다.
- [ ] [manual] **① E1 — 추측 디코딩** ★ 주인공. vanilla / ngram / draft-0.5B × 동시성 1·4·16·64. ITL·TPOT·처리량·**수용률**. 가설은 "저동시성 이득, 고동시성 역효과". 출발점은 `Ch7.md:949`의 교재 관측. ⚠️ draft 팔은 KV 예산이 vanilla와 달라지므로 기동 로그를 세 팔 전부 기록해 비교 가능 여부부터 판정.
- [ ] [manual] **② E2 — chunked prefill.** `--max-num-batched-tokens` 512/2048/8192. **프리필 지배 요청과 디코드 지배 요청을 섞어서** 넣어야 간섭이 보인다. 3주차 이월분 ③-b 해소. PD 분리의 동기를 GPU 1장에서 설명하는 대역.
- [ ] [manual] **③ E3 — prefix caching.** 서버 캐시 ON/OFF × 클라이언트 `--unique-prefix` ON/OFF = **2×2**. TTFT와 `prefix_cache_hits/queries`. **도구 수정 불필요** — `prefill` 시나리오와 `--unique-prefix`가 이미 있습니다.
- [ ] [manual] **④ E4 — vLLM 스케줄러 해부.** `vllm/v1/core/sched/scheduler.py`를 읽고 A·B·C가 같은 토큰 예산 계산의 어느 항을 건드리는지 코드로 짚기. GPU 불필요 — 측정 대기 중 진행. **3주차 글과의 차별점.**
- [ ] [manual] **⑤ 글 작성** — 이전 글의 8단계 구조(목적→문제 인식→원인→해결→가격표→순서→한계→결론) 유지.
- [ ] [manual] **⑥ 노션 발행 + ⑦ 링크 공유** ★ 마감 **08-30 09:00**. 사용자가 직접 공유.

**⚠️ 통제 변수**: A·B·C를 **전부 `vllm/vllm-openai:v0.23.0` 하나 위에서** 돈다. 이미 로컬에 있어 추가 다운로드 0. A를 ray-llm(0.7.2, V0)에서 돌리면 그것만 다른 엔진 숫자가 되어 같은 표에 못 넣는다 — 3주차에 데인 자리.

**일정**: 08-24 선행 / 08-25 **B** / 08-26 A / 08-27 C+예비 / 08-28 분석·D / 08-29 초고 / 08-30 발행. B를 앞에 두는 이유는 유일하게 다운로드가 있고 실패 가능성이 가장 높아서.

## Priority 4 — 3주차 (CH5·CH6) · 완료 (마감 2026-08-23 통과)

스터디일 2026-08-16(모임 20:30). 범위는 **CH5 Challenges When Serving LLMs** + **CH6 Essential LLM Optimization Techniques**.

상세 설계·근거·표·함정은 **[`docs/plans/2026-08-16-week3-triton-rayserve.md`](./plans/2026-08-16-week3-triton-rayserve.md)** 에 있습니다. 여기에는 체크리스트만 둡니다.

한 줄 근거: **Ray Serve는 CH4 공식 도전과제**(`study/Ch4.md:1381`), **Triton dynamic batching은 CH6 본문**(`study/Ch6.md:140` — vLLM엔 dynamic batching 모드가 없어 이 절은 vLLM으로 실측 불가), 과제 규칙도 *"혹은 LLM 관련 내용(혹은 도전과제)"*로 열려 있음(`study/Ch6.md:1039`).

- [x] [manual] **① 준비** — 실측: ray-llm **11.9 GiB 다운로드**(280초) / Triton **디스크 27.4GB**(9.63GB는 다운로드 크기 — 계획서의 `~17GB`가 틀렸음). KubeRay operator 1.4.2.
- [x] [manual] **② C3 — Ray Serve 배포 + 접점 ① 계층 오버헤드** (2026-08-21). ★ **통제 변수가 깨져 있어 설계를 바꿨음** — ray-llm의 vLLM은 0.7.2, B1은 0.23.0. 같은 이미지로 Ray 없이 띄운 **구성 B**를 추가해 3자 비교. **계층의 순수 가격 −32.6%**(순진한 비교 −39.3%는 7%p 과대계상). 고정 오버헤드가 아니라 포화 전 11% / 후 31%.
- [x] [manual] **③ CH5 + 도전과제 2** — 스윕 4행 완료. `Maximum concurrency` 14.28x~64.02x로 4.5배 흔들리는데 **처리량은 ±17%**. 기동 로그 4종 전부 파일로 저장(`c3-startup-*.txt`). GQA 손계산이 네 설정 전부에서 로그와 소수점 둘째 자리까지 일치.
- [ ] [manual] **③-b 도전과제 3 (chunked prefill)** — **다음 편 이월.** 다만 확인해둔 것: ray-llm 2.44.1의 vLLM 0.7.2는 **V0 엔진**이고 `chunked_prefill_enabled=False`가 기본이라 **ON/OFF 비교가 가능한 환경**이다(V1에서 기본 ON일 것을 걱정했으나 해당 없음).
- [x] [manual] **④ C2 — Triton dynamic batching** (2026-08-22). `--verify`로 배치 축 열림 확인(✅). 대조군 평균 배치 **정확히 1.00**. 같은 20ms가 동시성 1에서 1/9, 32에서 2.3배.
- [x] [manual] **④-b Triton + vLLM 백엔드** (2026-08-23). `nvcr.io/nvidia/tritonserver:24.12-vllm-python-py3`의 OpenAI 호환 프론트엔드로 같은 벤치마크. 짝(같은 이미지, Triton 없음)과 `GPU blocks 15,326` 일치. **계층 비용 −12.6%, goodput 100%.**
- [x] [manual] **④-c KServe + vLLM** (2026-08-23). KServe 0.20.0 RawDeployment. 짝과 `247,024 tokens / 60.31x` 일치. **계층 비용 −2.2%, goodput 100%, `vllm:*` 66개 보존.** 막힌 다섯 곳은 `labs/kserve-on-k8s/README.md`에.
- [x] [manual] **⑤ 글 작성 → 전면 재구성** (2026-08-23). 이전 원고는 실험 나열로 읽혀 목적이 서지 않았다. **`articles/서빙 최적화, 설정부터 만지면 안 되는 이유.md`** 로 재작성 — 설정 축 vs 구조 축, 목적→문제 인식→원인→해결법. Triton dynamic batching과 KV 공식은 부록으로.
- [x] [manual] **⑥ 노션 재발행** (2026-08-23). 기존 페이지를 새 원고로 갱신 + 2차 윤문 반영.
- [x] [manual] **⑦ 과제 링크 공유 — 완료** (2026-08-23). **3주차 마감 통과.**

**실제 경과**: 08-16 이후 닷새 공백 뒤 08-21~22 한 세션에 측정 3종 + 글까지. 측정이 계획 추정보다 훨씬 빨랐다(벤치마크 1회 약 4분, `serveConfigV2` 롤아웃 20~60초 — 파드를 갈지 않으므로). **2주차와 달리 범위를 줄이지 않았다.**

## Priority 3 — 2주차 (CH3·CH4) · 완료

- [x] [manual] `knowledge/06-week2-prep.md` 작성 — 완료 (2026-08-09). PDF 해당 구간을 직접 추출해 읽고 작성했고, 인용 쪽수는 물리 페이지 기준으로 `search_index.py` 출력과 일치. 교재의 Triton·RAG·에이전틱은 이 PDF가 다루지 않아 "어긋날 수 있는 지점" 표로 명시.
- [ ] [manual] 모임(오늘 20:30) 후 — 노트의 "스터디 중 확인할 질문" 5개가 강의에서 채워졌는지 확인하고, 안 채워진 것은 과제 소재로 이월.
- [x] [manual] **2주차 과제 — 완료.** 2편 시리즈로 노션 발행 + 링크 공유 (마감 2026-08-16 09:00 통과).
  - [x] B1·B2 전 구간 실측 (2026-08-15). `short`·`decode` × slots 1/16/64 + B2 큐 부하. 결과 8종 + 타임라인 + 환경 기록 + 메트릭 목록이 `labs/wsl2-vllm-baseline/results/`에.
  - [x] 표 4개 + 파레토 + 지연 공식 검증 + 서버 측 큐 궤적까지 채우고 해석 작성 → `articles/Continuous Batching이 처리량을 높이는 방식.md` (8단계 템플릿 전부 + 한계 6개 + 재현 부록)
  - [x] **증빙 보강** (2026-08-15). 계획의 산출물 중 빠져 있던 *"concurrency 대비 latency·throughput 그래프"*를 채움 — `tools/make_figures.py`(표준 라이브러리만)가 결과 JSON에서 SVG 3종 생성. 서버 측 원본은 `results/b2-prometheus.{json,txt}`. 글에 5-9 「측정 증거」 절 추가.
  - [x] **증빙 캡처 3장 확보** (2026-08-15). Prometheus 콘솔 실제 캡처. `b1-timeline.txt`의 구간 시각으로 부하 종료 6시간 뒤에 되짚어 촬영.
  - [x] **윤문 + 어조 통일 + 본문 전면 재작성** (2026-08-15). 개념·용어는 사용자 개정판 기준, 근거(그래프·캡처·전체 표·부록)는 복원.
  - [x] **노션 발행** (2026-08-15). 2편 모두. 1편↔2편 양방향 연결.
  - [x] **과제 링크 2개 공유 완료** (2026-08-16)
  - ⚠️ **분량이 큼.** 잘라내는 순서를 시나리오 머리말에 명시해 뒀음: C3-4 → C1의 `bs` 축 → C2의 20ms 지점 (각각의 핵심 결론은 남음)
  - **C3 = CH4 도전과제(RayService)**. 따라하기가 되지 않게 두 접점으로 붙임 — ① B1(직접 vLLM) ↔ C3(Ray Serve로 감싼 vLLM) 계층 오버헤드 ② C2(Triton `dynamic_batching`) ↔ C3(`@serve.batch`) 같은 두 노브
  - **GPU·8000 포트가 하나뿐**이라 B1·B2 / C1 / C2 / C3는 서로 배타적. 세션 전환 시 앞의 것을 반드시 내릴 것
  - ★ **C1이 재설계됐습니다.** 노션 CH3 원문에서 확인 — 교재 서버는 `main.py:63/69/74`가 `async def` 안에서 동기 호출을 해 uvicorn 이벤트 루프가 막히고 **동시 요청이 순차 처리**됩니다(강의 `[실습4]`도 같은 관측). 따라서 배칭 축은 **요청당 프롬프트 수**(`--prompts-per-request`)이고, 동시성 축은 `async def`→`def` 수정 전후 비교로 씁니다
  - 글의 축: **배칭 4종(없음/static/dynamic/continuous)을 전부 실측해 예습 노트 §1 표를 숫자로 채운다.** dynamic이 전제하는 "요청들이 같은 시간 걸린다"가 LLM에서 깨지는 것이 결론
  - 7주 실행 계획(노션)의 이번 주 산출물은 공개 글 **`Continuous Batching이 처리량을 높이는 방식`** + concurrency 대비 latency·throughput 그래프. 글은 계획의 **8단계 템플릿**을 따를 것 — 특히 `7. 운영 관점`(비용·안정성·확장성·복잡도)을 빼먹지 말 것
  - 계획의 공통 규칙 반영 완료: ITL/TPOT 지표, 환경 기록 목록(`0-6`), 반복 3회 타협안(`0-7`)
  - **세션 순서 고정**: ① B1·B2(안전판) → ② C1 → ③ C2 → ④ C3. 세션 ① 시작 시 Triton(~17GB)·ray-llm(~10GB) 이미지 풀과 C1 venv 설치를 백그라운드로 걸어둘 것
  - B3~B5는 다음 편으로 이월 (시나리오 문서 뒤쪽에 설계 보존). B1의 `results/b1-timeline.txt`가 B4의 입력이므로 **반드시 남길 것**
- [x] [auto] **실습 도구 일체 완성** (2026-08-09). 노트북에서는 **실행과 기록만** 하면 됨. 게이트 91건 green.
  - `benchmark.py --api book` — 교재 서버 어댑터. 프롬프트 에코 보정 · TTFT 없는 엔드포인트의 goodput 판정 · 네 엔드포인트 동일 계수법을 `BookApiTest`가 검증
  - `benchmark.py` ITL/TPOT 추가 — `itl_p50_s` · `perceived_tps`. 스터디 공통 지표 요구사항
  - `redeploy.sh` — 롤아웃 실패 감지 · `/v1/models` 폴링 · `mark`로 타임라인 기록
  - `summarize_results.py` — 결과 JSON → 마크다운 표 + 파레토(SLO 충족·최적 경계 표시)
  - `summarize_results.py --formula` — 교재 CH4의 `E2E = TTFT + ITL×(N-1)` 검증. **잔차 = 큐 대기 + 네트워크**라 Prometheus 없이 B4의 질문에 답함
  - `summarize_results.py --delta` — 두 구성의 차이·차이% 열 (C3 계층 오버헤드용)
  - `labs/triton-dynamic-batching/` — `export_mobilenet_onnx.py` · `make_config.py` · `triton_load.py` · `triton_metrics.py` · `sweep.sh` + 테스트 19건
  - `labs/rayserve-on-k8s/` — `rayservice-qwen.yaml`(B1과 동일 조건, `ManifestTest`가 통제 변수 감시) · `mobilenet_serve.py`(`@serve.batch`) + 테스트 10건
- [ ] [auto] **`Makefile`의 `PY`를 이 머신에서 쓸 수 있게 만들기.** WSL의 `python3`(3.14)에 **pip 자체가 없어** `make check-labs`가 그대로 실패합니다. 2026-08-15에는 Windows Python 3.12에 `pytest`·`pyyaml`을 설치해 91건을 확인했습니다. Done: 이 머신에서 `make check`가 문서+labs 91건까지 한 번에 통과.
- [ ] [manual] **C1 선행 — WSL2에서 환경 준비.** ① 교재 저장소 `orca3/llm-model-inference` 클론 + `ch03/single_model_llm_serving` venv 설치(`vllm==0.9.0.1`, 8~10GB·30~40분) ② `model_worker.py:48`의 `max_new_tokens=50`을 20으로 맞춰 엔드포인트 간 출력 토큰 수 정렬. 이 정렬을 빠뜨리면 처리량 비교가 2.5배 왜곡됨.
- [ ] [manual] **C2 선행 — Triton 이미지 풀 + ONNX export.** 저장소의 `densenet_onnx`는 `max_batch_size: 0` + `reshape`로 배치 축이 1에 고정돼 **dynamic batching을 켤 수 없음**. `export_mobilenet_onnx.py --verify`로 배치 축 열린 mobilenet_v2를 뽑아야 함. 이미지 풀(~17GB)은 세션 1에서 백그라운드로.

## Priority 1 — 게이트 두껍게 만들기

- [ ] [auto] `meta.summary_method` 회귀 검사를 `scripts/check_docs.py`의 `index` 검사에 추가. LLM 보강이 끝난 문서가 `extractive-*`로 되돌아가면 실패해야 함 — 기대값을 저장소에 기록해두고 대조하는 방식. 이게 현재 게이트의 가장 큰 구멍(`docs/STATUS.md` Open Risks 참조). Done: 되돌린 상태를 만들면 `make check-index`가 exit 1.
- [ ] [auto] `scripts/check_docs.py` 자체 테스트 `scripts/test_check_docs.py` 작성 — 깨진 링크/앵커/펜스 안 예시/`%20` 인코딩/`<a id>` 명시 앵커 각각에 대한 케이스. 지금은 손으로만 역방향 확인했음. Done: `python3 -m pytest -q scripts/test_check_docs.py` 통과하고 `make check`에 편입.
- [ ] [auto] 마크다운 표의 열 개수 불일치 검사 추가 — 이 저장소는 표가 많아 실수가 잦음. Done: 고의로 깨진 표에 대해 exit 1.

## Priority 2 — 남은 준비물

- [ ] [manual] **AWS GPU 쿼터 증설 신청 — 사용자가 콘솔에서 직접.** 2026-08-23 CLI 조회로 **현재 값이 us-east-1·ap-northeast-2 둘 다 `0`이고 신청 이력도 없음**을 확인했습니다. 즉 **지금은 GPU 인스턴스를 아예 못 띄웁니다.**
  - 리전 **us-east-1** / 쿼터 `L-DB2E81BA` (`Running On-Demand G and VT instances`) / 신청 값 **32** (단위는 vCPU. `g6e.2xlarge`=8, `g6.12xlarge`=48)
  - 콘솔: `https://us-east-1.console.aws.amazon.com/servicequotas/home/services/ec2/quotas/L-DB2E81BA` → Request increase at account level
  - **CLI 말고 콘솔로 할 것** — `request-service-quota-increase`에는 사유 필드가 없는데 GPU 쿼터는 사유 유무가 승인 속도를 가릅니다.
  - 상세 절차·비용·정리 목록: **[`knowledge/07-aws-gpu-quota.md`](../knowledge/07-aws-gpu-quota.md)**. 6주차(09-06) EKS 실습용. 승인 여부는 CLI로 조회 가능.

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
