# 3주차 (CH5·CH6) 설계 스냅샷 — Triton + Ray Serve

작성 2026-08-16 · 마감 **2026-08-23(일) 09:00** · 롤링 체크리스트는 [`docs/NEXT_PLAN.md`](../NEXT_PLAN.md)

스터디일 2026-08-16(모임 20:30). 범위는 **CH5 Challenges When Serving LLMs** + **CH6 Essential LLM Optimization Techniques**.
이월해둔 **C3(Ray Serve) + C2(Triton)** 를 3주차 과제로 수행한다.

## 왜 이게 3주차 과제인가 (근거)

과제 규칙이 "해당 주차 챕터"로 묶여 있지 않다 — `study/Ch6.md:1039`: *"3주차 스터디에서 학습한 내용 **혹은 LLM 관련 내용(혹은 도전과제)**"*. 그리고 셋 다 맞는다.

| 축 | 근거 |
|---|---|
| **Ray Serve = 공식 도전과제** | `study/Ch4.md:1381` — *"로컬 PC에 kind(k8s)로 RayService 배포 테스트 해보기"*. 사전 준비가 K3s + GPU Operator + kube-prometheus-stack + DCGM(12239)로 **1주차에 구축한 환경 그대로** |
| **Triton dynamic batching = CH6 본문** | `study/Ch6.md:140` 「Dynamic Batching in Online Inference」 절. max batch size + **max delay time** 두 파라미터, 그리고 결론 *"하지만 LLM에서는 이것만으로도 부족합니다"*(`Ch6.md:137`). **vLLM에는 dynamic batching 모드가 없어 이 절을 vLLM으로는 실측할 수 없다** — Triton이 그 두 노브를 실제로 가진 도구 |
| **권장 스택과 일치** | `study/Ch4.md:1373` — *"K8s + Ray Serve 또는 Triton + vLLM"* |

⚠️ 교재에서 Triton이 나오는 **CH3의 자리는 배칭이 아니라 "멀티모델 서빙 백엔드 위임"** 이다 (`study/Ch3.md:1543`, `TritonWorker`가 HTTP로 load/infer/unload 위임). 배칭 축은 이 저장소가 CH6에 붙여 확장한 것 — 글에 이 구분을 명시해야 "교재 요약"이 아니라 "교재 위에 얹은 실험"이 된다.

## 실습 문서 (실행 런북)

| # | 문서 | 내용 |
|---|---|---|
| 허브 | [`KV cache와 서빙 계층 실습 시나리오 (CH5·CH6)`](../../articles/KV%20cache%EC%99%80%20%EC%84%9C%EB%B9%99%20%EA%B3%84%EC%B8%B5%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH5%C2%B7CH6%29.md) | 목차·근거·선행 관측·글 뼈대 |
| 00 | [`3주차-00 실습 준비와 측정 규칙`](../../articles/3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) | GPU 배타성 · 이미지 풀 · **기동 로그 캡처 규칙** · 트러블슈팅 |
| 01 | [`3주차-01 Ray Serve라는 계층의 가격`](../../articles/3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) | C3 = 위 ② |
| 02 | [`3주차-02 KV cache가 정하는 동시성 상한`](../../articles/3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) | B3 = 위 ③·③-b |
| 03 | [`3주차-03 Triton dynamic batching`](../../articles/3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md) | C2 = 위 ④ |

원설계(가설·판단 기준의 배경)는 [`articles/2주차-03 dynamic batching과 그 위의 계층.md`](../../articles/2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md)에 그대로 둔다.
도구: `labs/triton-dynamic-batching/`(테스트 19건) · `labs/rayserve-on-k8s/`(10건). 전부 green.

## 실행 순서 — C3 먼저 (안전판)

### ① 준비 — 이미지 풀

⚠️ **백그라운드 태스크가 이 머신에서 반복 강제 종료된다.** 별도 PowerShell/터미널 창에서 사람이 직접 띄울 것.

- Triton `nvcr.io/nvidia/tritonserver:24.12-py3` — ⚠️ **크기 확인 필요**: `study/Ch3.md:2380` 실측 기록은 **9.63GB**(디스크 27.4GB)인데 기존 계획엔 `~17GB`로 적혀 있었다. 실제 값으로 정정할 것
- KubeRay operator(helm 1.4.2) + ray-llm 이미지 ~10GB

### ② C3 — Ray Serve on K8s ★ 여기까지만 해도 글 한 편이 선다

**왜 안전판인가**: `rayservice-qwen.yaml`이 B1과 동일 조건(`Qwen2.5-1.5B-Instruct` / `max_model_len=4096` / `gpu_memory_utilization=0.85` / `max_num_seqs=16`)으로 고정돼 있고 `ManifestTest`가 지킨다. 즉 **띄우기만 하면 기존 `results/b1-slots-16-short.json`과 바로 diff**가 난다.

- C3-1 KubeRay operator → C3-2 `vllm-baseline` 내리고 `rayservice-qwen.yaml` apply (READY까지 5~15분)
- C3-3 **접점 ① 계층 오버헤드** — B1과 똑같은 `benchmark.py` 명령 → `summarize_results.py --delta`로 `output_tok_per_s`·`ttft_p95_s` 차이·차이%
- C3-5 배포 계층 관찰 — Ray Dashboard(8265) replica·큐 길이, `serveConfigV2` 변경으로 **zero-downtime 롤아웃**을 B1의 `kubectl set env` 재배포와 대비 ★ 도전과제 본래 목적
- ⚠️ **오버헤드가 음수면 통제 변수를 의심**할 것 (이미지에 따른 vLLM 버전 차이 — 버전을 반드시 기록)

### ③ CH5 + 도전과제 2를 C3 위에서 수행 ★ 이 조합의 최대 이점

**왜 Ray Serve 환경이 더 유리한가**: `rayservice-qwen.yaml`의 `serveConfigV2 → engine_kwargs`에 `max_model_len`·`gpu_memory_utilization`·`max_num_seqs`가 그대로 노출돼 있다 — **도전과제 2가 요구하는 세 노브가 바로 그것**이다. 게다가 RayService는 `serveConfigV2` 변경을 **zero-downtime으로 갈아끼우므로**, B1에서 `kubectl set env`로 재배포하며 겪은 사고(13일 전 구버전이 떠 있어 무시됨)가 구조적으로 없다. **스윕이 훨씬 깨끗하다.**

- ⚠️ **순서 고정**: C3-3(접점 ①)을 **B1 동일 조건으로 먼저 끝낸 뒤에** `engine_kwargs`를 건드릴 것. 먼저 바꾸면 통제 변수가 깨져 ①이 무의미해진다
- ⚠️ **`rayservice-qwen.yaml`을 직접 고쳐 커밋하지 말 것.** `ManifestTest`가 네 값을 지키고 있어 `make check`가 깨진다. 스윕은 **별도 파일**(`rayservice-sweep.yaml`, gitignore 또는 테스트 예외)로 뜨거나 apply만 하고 원본은 둘 것

**채울 표**

| `max_model_len` | `max_num_seqs` | `util` | 손계산 예측 | 로그의 `Maximum concurrency` | 처리량 |
|---|---|---|---|---|---|
| 4096 | 16 | 0.85 | | | (= C3-3 결과 재사용) |
| 4096 | 64 | 0.85 | | | |
| 16384 | 64 | 0.85 | | | |
| 4096 | 64 | 0.60 | | | |

- **기동 로그의 `Maximum concurrency for N tokens per request: X.XXx` 줄을 매 롤아웃마다 파일로 저장**할 것 — 2주차에는 메모로만 남아 증빙이 없었다(`docs/STATUS.md` Open Risks). 이 로그가 손계산의 정답지다
- ★ **교재 CH5 공식은 MHA 전제**다: `2 × 층수 × 어텐션 헤드 수 × head_dim × 정밀도` (`study/Ch5.md`, Llama-2-7b → 0.5MB/token). **Qwen2.5-1.5B는 GQA**라 그대로 넣으면 안 맞는다. `config.json`에서 **어텐션 헤드 수와 KV 헤드 수를 각각** 뽑아 두 공식으로 계산해 로그값과 대조할 것. 원문도 *"이후 장에서 MQA·GQA·MLA를 소개한다"* 고 예고하며, **그 "이후 장"이 이번 주 CH6**(`Ch6.md:304` Scaling Attention)다 → **CH5의 공식이 CH6에서 깨지는 지점**이 글의 핵심 절
- 💡 **미해결 관측 규명 기회**: 같은 `slots=64`인데 `Maximum concurrency`가 59.50x / 28.77x로 갈린 건이 미확인으로 남아 있다. 손계산 기준선이 생기면 "직전 파드의 VRAM 미반환"인지 판정할 수 있다

### ③-b 도전과제 3 (chunked prefill) — 여유가 있으면

- 같은 `engine_kwargs`에 `max_num_batched_tokens`(+ 필요 시 `enable_chunked_prefill`) 추가. `study/Ch6.md:281` — *"별도의 청크 크기 전용 파라미터는 없고 `--max-num-batched-tokens` 값 자체가 청크 크기를 결정"*
- ⚠️ **먼저 확인할 것**: vLLM v0.23.0의 V1 엔진은 chunked prefill이 **기본 ON**일 가능성이 크다. OFF로 내리는 방법이 없으면 "ON/OFF 비교"는 성립하지 않으므로 **`max_num_batched_tokens` 튜닝 축만** 남기고 그 사실을 글에 적을 것
- 긴 프롬프트 시나리오라야 효과가 보인다 (TTFT vs ITL 트레이드오프)

### ④ C2 — Triton dynamic batching

- C2-1 **`export_mobilenet_onnx.py --verify`** ★ 진짜 장벽. 교재 실습의 `densenet_onnx`는 `max_batch_size: 0` + `reshape`로 **배치 축이 1에 고정**돼 dynamic batching을 켤 수 없다 (`study/Ch3.md:2352`의 `config.pbtxt`에 그대로 있음). `dynamic_axes={"input": {0: "batch"}, ...}` 한 줄이 실험 전체를 가능하게 한다 — 글에 남길 것
- C2-2 `make_config.py` — **대조군은 `0`이 아니라 `off`** (`0`은 모델 시그니처까지 바꿔 비교가 깨짐)
- C2-3 `--model-control-mode=explicit`이라 컨테이너 재시작 없이 unload/load로 config 재적용
- C2-4 **평균 배치 크기 = `nv_inference_request_success / nv_inference_exec_count`** — 반드시 `triton_metrics.py delta`로 차분(카운터가 기동 이후 누적)
- C2-5 `sweep.sh` — off / 0 / 1ms / 5ms / 20ms, 그리고 **같은 5ms에서 동시성 1/8/32** ★ 가설 2의 답이 여기

### ⑤ 글 작성

8단계 템플릿. `7. 운영 관점`(비용·안정성·확장성·복잡도)을 빼먹지 말 것.

- 결론 축: **dynamic batching은 "요청들이 같은 시간 걸린다"를 전제**로 배치를 통째로 묶었다 통째로 내보낸다. mobilenet에서는 성립(C2), LLM에서는 배치가 가장 긴 요청에 인질로 잡힌다. **continuous batching은 그 전제를 버려서 문제를 푼 것** — 2주차 글의 23배가 그 증거
- 배칭 4종 표에서 이번에 채우는 칸: **dynamic**(C2). 없음/static은 C1(미수행)이라 **빈칸으로 두고 범위를 명시**할 것

## 잘라내기 순서 (분량·시간 초과 시)

시나리오 머리말의 순서에 이번 주 추가분을 얹었다. **위에서부터 자른다.**

1. **③-b 도전과제 3 (chunked prefill)** — 애초에 "여유가 있으면"
2. **C3-4 (`@serve.batch` 스윕)** — 접점 ②. 자르면 "Triton과 Ray Serve가 같은 노브를 가진다"는 대응표만 남기고 측정은 생략
3. **③의 4행 표에서 `util=0.60` 행** — 나머지 3행으로도 "컨텍스트 길이가 동시성을 깎는다"는 결론은 선다
4. **C2의 20ms 지점** — 곡선 모양은 5ms까지로도 나온다
5. C2 보너스(모델 스와핑)는 애초에 여유가 있을 때만

**절대 자르지 말 것**: ②(C3-3 계층 오버헤드)와 ③의 로그 캡처. 앞의 것은 안전판이고, 뒤의 것은 재현 비용이 크다(롤아웃마다 5~15분).

## 일정 (마감까지 7일)

| 날짜 | 할 일 |
|---|---|
| 08-16(일) | 모임 20:30. ① 이미지 풀 걸어두기(별도 창) |
| 08-17(월) | ② **C3 완료** — 배포 + 접점 ① 계층 오버헤드. ★ 여기서 안전판 확보 |
| 08-18(화) | ③ `engine_kwargs` 스윕 4행 + 로그 캡처 + 손계산. **롤아웃마다 5~15분**이라 반나절 잡을 것 |
| 08-19~20 | ④ C2 (export → config → 스윕). 20일 저녁까지 측정 종료 |
| 08-21~22 | ⑤ 글 작성·윤문·노션 발행 |
| 08-23(일) 09:00 | **마감 — 링크 공유** |

⚠️ **08-09→08-15 6일 공백이 지난주 축소의 원인**이었다. 측정을 주중 앞쪽에서 끝내는 것이 이번 주의 핵심.

**GPU·8000 포트가 하나뿐**이라 C3(②③)와 C2(④)는 배타적이다. ④로 넘어가기 전 `kubectl delete -f rayservice-qwen.yaml`로 반드시 내릴 것.

## 공식 도전과제 대응표 (`study/Ch6.md:1047`)

| # | 도전과제 | 이번 주 |
|---|---|---|
| 1 | 배칭 ON vs `max_num_seqs=1` 처리량·지연 | ✅ 2주차 완료 (113→2,627 tok/s). 글 도입부로 재사용 |
| 2 | `max batch size`·`max model length`·`max number of tokens` 변경 비교 | ✅ **③에서 수행** — RayService `engine_kwargs` 스윕 (= 이월된 B3) |
| 3 | Chunked Prefill ON/OFF + `--max-num-batched-tokens` | ⚠️ **③-b, 여유 시** (잘라내기 1순위) |
| 4 | MHA vs GQA vs MQA vs MLA 속도·품질 | ◐ ③의 **GQA 공식 대조로 측정 없이 일부만**. 모델 4종 실측은 다음 편 |

여기에 **CH6 본문의 dynamic batching**(`Ch6.md:140`)을 C2가, **CH4 도전과제 RayService**(`Ch4.md:1381`)를 C3가 덮는다. 즉 이번 주 한 편으로 **공식 도전과제 4개 중 2.5개 + CH6 본문 + CH4 도전과제**가 커버된다.
