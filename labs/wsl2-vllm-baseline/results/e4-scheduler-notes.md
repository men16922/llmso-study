# E4 — vLLM 스케줄러 해부: 세 실험이 건드리는 한 곳

원본 `e4-scheduler.py` — `vllm/v1/core/sched/scheduler.py` (v0.23.0, 2,422줄).
컨테이너 안 경로는 `/usr/local/lib/python3.12/dist-packages/vllm/v1/core/sched/scheduler.py`.
추출은 2026-08-27, 이미지 `vllm/vllm-openai:v0.23.0`. **줄 번호는 이 파일 기준입니다.**

---

## 0. 결론부터 — 소스 주석이 이 글의 주장을 그대로 말한다

`schedule()` 맨 앞에 vLLM 개발자가 남긴 NOTE입니다 (`e4-scheduler.py:341-351`):

> *"There's no "decoding phase" nor "prefill phase" in the scheduler. Each request just has the `num_computed_tokens` and `num_tokens_with_spec`. (…) At each step, the scheduler tries to assign tokens to the requests so that each request's `num_computed_tokens` can catch up its `num_tokens_with_spec`. **This is general enough to cover chunked prefills, prefix caching, speculative decoding**, and the "jump decoding" optimization in the future."*

**세 기법을 한 글에 넣을 근거를 내가 만든 게 아니라, 스케줄러가 그렇게 짜여 있습니다.** 프리필과 디코드는 스케줄러에게 다른 종류의 일이 아닙니다. 요청마다 숫자 두 개 — **어디까지 계산했나(`num_computed_tokens`)** 와 **어디까지 계산해야 하나(`num_tokens_with_spec`)** — 가 있고, 스케줄러가 하는 일은 매 스텝 **그 간격을 좁히는 것**뿐입니다.

세 실험은 그 간격을 각자 다른 쪽에서 건드립니다.

| 실험 | 무엇을 건드리나 | 위치 |
|---|---|---|
| **E2** chunked prefill | 한 스텝에 좁힐 수 있는 **총량의 상한** | `:105-108`, `:360`, `:410`, `:699` |
| **E3** prefix caching | 간격의 **시작점**을 미리 밀어올린다 | `:609-641`, `:684` |
| **E1** 추측 디코딩 | 간격의 **끝점**을 늘려 그만큼 예산을 먹는다 | `:404-406` |

---

## 1. E2 — 예산의 상한 (`--max-num-batched-tokens`)

플래그가 곧 예산입니다. 중간에 이름만 한 번 갈아탑니다:

```python
# :105-108
self.max_num_scheduled_tokens = (
    self.scheduler_config.max_num_scheduled_tokens
    if self.scheduler_config.max_num_scheduled_tokens is not None
    else self.scheduler_config.max_num_batched_tokens      # ← 우리가 넣는 값
)
```

```python
# :360  — 매 스텝 이 값으로 초기화된다
token_budget = self.max_num_scheduled_tokens
```

그리고 **running 루프와 waiting 루프 양쪽에서 똑같이 잘립니다**:

```python
# :410  (RUNNING — 이미 디코드 중인 요청)
num_new_tokens = min(num_new_tokens, token_budget)
# :699  (WAITING — 새로 들어온 프리필)
num_new_tokens = min(num_new_tokens, token_budget)
```

```python
# :516  — 쓴 만큼 깎는다. 0이 되면 그 스텝은 끝
token_budget -= num_new_tokens
```

★ **여기가 "프리필이 디코드를 민다"의 물리적 위치입니다.** running 루프가 waiting 루프보다 **먼저** 돌지만(`:378` vs `:566`), 예산은 하나뿐이라 긴 프리필 하나가 `token_budget`을 쓸어 가면 그 스텝의 디코드 몫이 사라집니다. 청크를 작게 잡는다는 건 **프리필 하나가 한 번에 가져갈 수 있는 양을 제한**하는 것이고, 그래서 디코드의 ITL이 안정되는 대신 프리필의 TTFT가 늘어납니다. E2가 재려는 교환비가 이 두 줄 사이에 있습니다.

**chunked prefill이 꺼져 있을 때의 분기도 여기 있습니다** (`:690-697`):

```python
if (not self.scheduler_config.enable_chunked_prefill
        and num_new_tokens > token_budget):
    break          # ← 자르지 않고 "이번 스텝엔 안 넣는다"
```

켜져 있으면 `min(...)`으로 **잘라서 넣고**, 꺼져 있으면 `break`로 **통째로 미룹니다.** V1에서 청크 크기를 `max_model_len` 이상으로 키우는 것이 "사실상 OFF"와 같아지는 이유가 이것입니다 — 자를 일이 없어지니까.

---

## 2. E3 — 시작점 (`--no-enable-prefix-caching`)

캐시 조회는 **요청이 처음 스케줄될 때 딱 한 번** 일어납니다 (`:609`):

```python
if request.num_computed_tokens == 0:
    new_computed_blocks, num_new_local_computed_tokens = (
        self.kv_cache_manager.get_computed_blocks(request)   # :611-613
    )
    ...
    num_computed_tokens = (                                   # :639-641
        num_new_local_computed_tokens + num_external_computed_tokens
    )
```

그리고 그 값이 곧바로 **할 일의 크기**를 줄입니다 (`:684`):

```python
num_new_tokens = request.num_tokens - num_computed_tokens
```

★ **캐시 적중은 연산을 빠르게 하지 않습니다 — 아예 없앱니다.** 적중한 만큼 `num_computed_tokens`가 0이 아니라 이미 올라간 채로 출발하고, 스케줄러 입장에서 그 토큰들은 **이미 끝난 일**입니다. compute-bound 구간(프리필)이 통째로 사라지는 것이고, 그래서 이득이 TTFT에 나타납니다.

역으로, 공유 프리픽스가 없으면 `get_computed_blocks()`가 0을 돌려주므로 **조회 비용만 내고 얻는 게 없습니다.** E3의 2×2에서 「캐시 ON × 공유 OFF」 칸이 필요한 이유가 이것입니다.

---

## 3. E1 — 끝점 (`--spec-method ngram` / `--spec-model`)

running 루프에서 이번 스텝에 할 일을 계산하는 한 줄 (`:404-406`):

```python
num_new_tokens = (
    request.num_tokens_with_spec        # ← 여기에 draft 토큰이 들어 있다
    + request.num_output_placeholders
    - request.num_computed_tokens
)
```

`num_tokens_with_spec`의 정의는 위 NOTE에 있습니다:

```
num_tokens_with_spec = len(prompt_token_ids) + len(output_token_ids) + len(spec_token_ids)
```

★ **추측 디코딩은 별도의 예산을 쓰지 않습니다. 같은 `token_budget`에서 먹습니다.** draft 토큰 `k`개를 붙이면 그 요청의 `num_new_tokens`가 `k`만큼 커지고, `:410`의 `min(num_new_tokens, token_budget)`과 `:516`의 `token_budget -= num_new_tokens`를 그대로 통과합니다.

**이득과 손해가 갈리는 자리가 정확히 여기입니다.**

- 배치가 비어 있으면(memory-bound) `token_budget`이 남아돕니다. 남는 예산으로 `k`개를 미리 검증하니 **맞으면 그만큼 스텝을 건너뛴 것**이고, 틀려도 잃은 건 놀던 연산입니다.
- 배치가 꽉 차 있으면(compute-bound) `token_budget`이 이미 경쟁 상태입니다. 내가 먹은 `k`개는 **다른 요청이 못 쓴 `k`개**이고, 수용률이 낮으면 그건 그냥 버려집니다. 처리량이 **떨어집니다**.

교재 `Ch7.md:949`의 *"동시성 1에서 이미 GPU 98% → 추측 디코딩 시 오히려 역효과"* 가 이 산술입니다. E1이 재려는 건 그 뒤집히는 지점이고, **수용률**이 그 산술의 계수입니다.

`:415`에 붙은 방어선도 추측 디코딩 때문에 존재합니다:

```python
# Make sure the input position does not exceed the max model len.
# This is necessary when using spec decoding.
num_new_tokens = min(num_new_tokens, self.max_model_len - 1 - request.num_computed_tokens)
```

---

## 4. 한 문장으로

**세 기법은 서로 다른 최적화가 아니라, 같은 한 줄(`num_computed_tokens`가 `num_tokens_with_spec`을 따라잡는 속도)을 세 방향에서 건드리는 것입니다.** E2는 한 걸음의 보폭 상한을, E3는 출발선을, E1은 결승선을 옮깁니다. 그래서 셋 다 "켜면 이득"이 아니라 **"예산이 남는가"라는 같은 조건**에 걸립니다.

그리고 그 조건을 부르는 이름이 CH7의 첫 질문 — **compute-bound인가 memory-bound인가** — 입니다.
