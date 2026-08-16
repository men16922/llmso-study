# KV cache와 서빙 계층 실습 시나리오 (CH5·CH6) — 허브

> **이 문서는 3주차 시리즈의 목차이자 종합입니다.** 실험 절차는 아래 네 문서에 나뉘어 있습니다.
> 2주차 시리즈([허브](./vLLM%20%EB%B0%B0%EC%B9%AD%C2%B7%ED%81%90%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH3%C2%B7CH4%29.md))에서 **이월한 C2·C3에 B3를 더한** 구성입니다.

| # | 문서 | 내용 | 소요 |
|---|---|---|---|
| 00 | [실습 준비와 측정 규칙](./3%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md) | 사전 조건 · GPU 배타성 · 이미지 풀 · **기동 로그 캡처 규칙** · 트러블슈팅 | 30분 |
| 01 | [Ray Serve라는 계층의 가격](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) | **C3** RayService 배포 · 계층 오버헤드 · zero-downtime 롤아웃 | 90~120분 |
| 02 | [KV cache가 정하는 동시성 상한](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) | **B3** 손계산 vs 로그 · `engine_kwargs` 스윕 · chunked prefill | 120~150분 |
| 03 | [Triton dynamic batching](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md) | **C2** 배치 축 열기 · delay 스윕 · 도착률 의존성 | 120~150분 |

**총 6~8시간·세 세션.** [01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md)만으로도 글 한 편이 서므로 **반드시 먼저 끝내세요.**

시간이 부족해지면 잘라내는 순서: **02의 chunked prefill → 01의 `@serve.batch` 스윕 → 02의 `util=0.60` 행 → 03의 20ms 지점.**
**절대 자르지 말 것**은 01의 계층 오버헤드(안전판)와 02의 기동 로그 캡처(재현 비용이 큼 — 롤아웃당 5~15분)입니다.

---

## 실행 순서가 문서 번호와 같습니다

2주차의 실패(네 세션 계획 → 한 세션 수행 → 마감 전날 축소)를 반복하지 않기 위해 **안전판을 먼저 만드는 순서**로 배치했습니다.

```
01 C3 배포  →  02 B3 (그 위에서 스윕)  →  03 C2 (GPU 반납 후)
   ↑ 안전판       ↑ 01의 환경을 그대로 재사용      ↑ 배타적, 반드시 01·02 종료 후
```

**02가 01 위에서 돌아가는 것이 이번 시리즈의 핵심 이점입니다.** RayService는 `serveConfigV2`를 바꾸면 zero-downtime으로 갈아끼우므로, 2주차에 `kubectl set env`로 재배포하며 겪은 사고(13일 전 구버전이 떠 있어 무시됨)가 구조적으로 없습니다.

---

## 이 시리즈가 답하려는 질문

| # | 질문 | 교재 대응 | 어디에 |
|---|---|---|---|
| **C3** | 오케스트레이션 **계층을 얹으면 얼마를 내야 하나** | CH4 오픈소스 스택 · **공식 도전과제** | [01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md) |
| **B3** | 슬롯을 계속 키우면 되나? **동시 요청 수의 상한은 무엇이 정하나** | **CH5** KV cache 사이징 · **도전과제 2** | [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) |
| **C2** | **dynamic batching은 언제 쓰나?** 그리고 왜 LLM에는 안 맞나 | **CH6** 배칭 전략 | [03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md) |

### 왜 이 셋이 3주차인가 (근거)

과제 규칙이 "해당 주차 챕터"로 묶여 있지 않습니다 — *"3주차 스터디에서 학습한 내용 **혹은 LLM 관련 내용(혹은 도전과제)**"*.

| 축 | 근거 |
|---|---|
| **B3 = CH5 본문 + 도전과제 2** | CH5의 「Estimating KV Cache Size」 절. 도전과제 2는 *"`max batch size`·`max model length`·`max number of tokens` 기본값 확인 및 변경 후 성능 비교"* |
| **C2 = CH6 본문** | CH6의 「Dynamic Batching in Online Inference」 절 — max batch size + **max delay time** 두 파라미터. **vLLM에는 dynamic batching 모드가 없어 이 절을 vLLM으로는 실측할 수 없습니다.** Triton이 그 두 노브를 실제로 가진 도구 |
| **C3 = CH4 공식 도전과제** | *"로컬 PC에 kind(k8s)로 RayService 배포 테스트 해보기"*. 사전 준비가 1주차에 구축한 환경 그대로 |

> ⚠️ **챕터 대응 주의.** 교재에서 Triton이 나오는 **CH3의 자리는 배칭이 아니라 "멀티모델 서빙 백엔드 위임"** 입니다(`TritonWorker`가 HTTP로 load/infer/unload 위임). 배칭 축은 이 시리즈가 CH6에 붙여 확장한 것입니다. **글에 이 구분을 명시해야** "교재 요약"이 아니라 "교재 위에 얹은 실험"이 됩니다.

---

## 선행 관측 — 2주차가 남긴 것 셋

**① 슬롯을 키우면 처리량이 오른다 (그런데 어디까지?)**

| 슬롯 | `short` 처리량 | `decode` 처리량 |
|---|---|---|
| 1 | 113 tok/s | 115 tok/s |
| 64 | **2,627 tok/s (23배)** | **2,852 tok/s (24.8배)** |

→ [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)가 그 천장을 손계산으로 예측하고 로그와 대조합니다.

**② `Maximum concurrency`가 롤아웃마다 흔들렸습니다 ★ 미해결**

같은 `slots=64` 설정인데 어떤 롤아웃은 **59.50x**, 어떤 롤아웃은 **28.77x**였습니다. 28.77은 59.50의 거의 정확히 절반입니다. 원인 미확인으로 남아 있습니다.

→ [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)에서 손계산 기준선이 생기면 "직전 파드의 VRAM 미반환"인지 판정할 수 있습니다. **아무 에러 없이 실질 수용량만 절반이 되는** 종류의 함정이라 글감으로 좋습니다.

**③ goodput은 조용히 무너집니다**

B2 c=64에서 200/200 요청이 전부 성공했는데 goodput은 8%였습니다. 부하를 4배 올려 처리량은 +0.3%, TTFT는 139배.

→ [01](./3%EC%A3%BC%EC%B0%A8-01%20Ray%20Serve%EB%9D%BC%EB%8A%94%20%EA%B3%84%EC%B8%B5%EC%9D%98%20%EA%B0%80%EA%B2%A9.md)의 계층 오버헤드를 볼 때 같은 함정에 빠지지 않도록, **처리량만이 아니라 TTFT p95를 나란히** 봅니다.

---

## 종합 — 이번 시리즈가 채우는 칸

### 배칭 4종 (2주차에서 이어짐)

| 방식 | 어디서 쟀나 | 대기 전략 | 상태 |
|---|---|---|---|
| 배칭 없음 | C1 `/basic_generate` | — | ⏸ 미수행 (C1 이월) |
| static | C1 `/generate` | 배치가 **찰 때까지** | ⏸ 미수행 (C1 이월) |
| **dynamic** | **C2 Triton** · C3 `@serve.batch` | **시간 상한까지** | ✅ **이번 시리즈 [03](./3%EC%A3%BC%EC%B0%A8-03%20Triton%20dynamic%20batching.md)** |
| **continuous** | B1·B2 vLLM | 기다리지 않음, **슬롯 단위로 교체** | ✅ 2주차 완료 |

> 없음·static 칸은 **빈칸으로 두고 글에 범위를 명시**하세요. 채운 척하지 않는 것이 중요합니다.

### 공식 도전과제 대응

| # | 도전과제 | 이번 시리즈 |
|---|---|---|
| 1 | 배칭 ON vs `max_num_seqs=1` | ✅ 2주차 완료 (113→2,627 tok/s). 글 도입부로 재사용 |
| 2 | `max batch size`·`max model length`·`max number of tokens` 변경 비교 | ✅ **[02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)** |
| 3 | Chunked Prefill ON/OFF + `--max-num-batched-tokens` | ⚠️ [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md) 후반, **여유 시** |
| 4 | MHA vs GQA vs MQA vs MLA | ◐ [02](./3%EC%A3%BC%EC%B0%A8-02%20KV%20cache%EA%B0%80%20%EC%A0%95%ED%95%98%EB%8A%94%20%EB%8F%99%EC%8B%9C%EC%84%B1%20%EC%83%81%ED%95%9C.md)의 GQA 공식 대조로 **측정 없이 일부만** |

---

## 글로 옮길 때의 뼈대

7주 실행 계획의 **8단계 템플릿**을 따릅니다. 특히 `7. 운영 관점`(비용·안정성·확장성·복잡도)을 빼먹지 마세요.

**결론 축 후보 두 개** — 측정 결과를 보고 하나를 고르거나 둘을 잇습니다.

1. **교재 공식이 내 모델에서 깨진다** — CH5의 KV 공식은 MHA 전제(`2 × 층수 × **어텐션 헤드 수** × head_dim × 정밀도`)인데 Qwen2.5-1.5B는 **GQA**라 맞지 않습니다. 교재도 *"이후 장에서 MQA·GQA·MLA를 소개한다"* 고 예고하고, **그 "이후 장"이 이번 주 CH6**입니다. → **CH5의 공식이 CH6에서 보정되는 지점**
2. **dynamic batching은 프레임워크의 기능이 아니라 워크로드의 성질** — dynamic은 *"요청들이 같은 시간 걸린다"* 를 전제로 배치를 통째로 묶었다 통째로 내보냅니다. mobilenet에서는 성립하고(03) LLM에서는 배치가 가장 긴 요청에 인질로 잡힙니다. **continuous batching은 그 전제를 버려서 문제를 푼 것** — 2주차의 23배가 그 증거

### 운영 관점에 넣을 것

| 축 | 소재 |
|---|---|
| **비용** | 파레토 곡선 + "동시 사용자 N명당 GPU 몇 장" 환산. KV 예산이 정하는 실질 수용량 |
| **안정성** | ★ **`Maximum concurrency`가 롤아웃마다 흔들리는데 에러가 없다** — 조용히 절반이 되는 함정 |
| **확장성** | 컨텍스트 길이와 동시성이 같은 KV 예산을 두고 경쟁한다. 레플리카 없이 GPU 1장에서 할 수 있는 것의 끝 |
| **복잡도** | Ray Serve가 얹는 계층의 가격 vs 그 대가로 얻는 zero-downtime 롤아웃·오토스케일링. Triton은 모델을 다시 export해야 했다는 진입 비용 |

---

## 이 환경에서 못 하는 것 (글의 "한계" 절)

| 못 하는 것 | 이유 | 어디서 다루나 |
|---|---|---|
| 오토스케일링, 멀티 레플리카, concurrency target | GPU 1장 | 6주차 EKS |
| 라우팅·로드밸런싱, KV cache-aware routing | 레플리카가 없음 | 7주차 llm-d |
| Prefill/Decode disaggregation | 노드·GPU 부족 | 7주차 llm-d |
| Tensor Core 활용률 | WSL2에 `DCGM_FI_PROF_*` 미노출 | (이 환경의 구조적 한계) |
| MHA·MQA·MLA 실측 비교 (도전과제 4) | 모델 4종 다운로드 + 12GB VRAM | 다음 편 |
| 배칭 4종 중 없음·static | C1(교재 서버) 미수행 | 다음 편 |

---

## 참고

- 2주차 시리즈: [허브](./vLLM%20%EB%B0%B0%EC%B9%AD%C2%B7%ED%81%90%20%EC%8B%A4%EC%8A%B5%20%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4%20%28CH3%C2%B7CH4%29.md) · [01 배치 슬롯과 큐](./2%EC%A3%BC%EC%B0%A8-01%20%EB%B0%B0%EC%B9%98%20%EC%8A%AC%EB%A1%AF%EA%B3%BC%20%ED%81%90.md) · [03 dynamic batching과 계층](./2%EC%A3%BC%EC%B0%A8-03%20dynamic%20batching%EA%B3%BC%20%EA%B7%B8%20%EC%9C%84%EC%9D%98%20%EA%B3%84%EC%B8%B5.md) ← **C2·C3의 원설계(가설·판단 기준)가 여기 있습니다**
- 2주차 발행글: [Continuous Batching이 처리량을 높이는 방식](./Continuous%20Batching%EC%9D%B4%20%EC%B2%98%EB%A6%AC%EB%9F%89%EC%9D%84%20%EB%86%92%EC%9D%B4%EB%8A%94%20%EB%B0%A9%EC%8B%9D.md)
- 도구: [`labs/wsl2-vllm-baseline/`](../labs/wsl2-vllm-baseline/README.md) · [`labs/triton-dynamic-batching/`](../labs/triton-dynamic-batching/README.md) · [`labs/rayserve-on-k8s/`](../labs/rayserve-on-k8s/README.md)
- 실행 계획: [`docs/plans/2026-08-16-week3-triton-rayserve.md`](../docs/plans/2026-08-16-week3-triton-rayserve.md)
