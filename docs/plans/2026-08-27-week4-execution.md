# 4주차 실행 계획 — 남은 61시간

작성 **2026-08-27(목) 19:31** · 마감 **2026-08-30(일) 09:00** · 남은 시간 **약 61시간**(실작업 가용 ~14시간)

설계·근거·축은 [`2026-08-23-week4-conditional-optimization.md`](./2026-08-23-week4-conditional-optimization.md)에 있습니다. **이 문서는 그 설계를 지금 상태에서 어떻게 끝낼 것인가**만 다룹니다. 롤링 체크리스트는 [`docs/NEXT_PLAN.md`](../NEXT_PLAN.md) Priority 0.

---

## 0. 상황 — 3일 밀렸다

원래 일정은 08-24 선행 / 08-25 E1 / 08-26 E2 / 08-27 E3였습니다. **오늘(08-27) 시점에 ⓪ 선행조차 시작되지 않았습니다.** `labs/wsl2-vllm-baseline/results/`에 `e1-*`·`e2-*`·`e3-*` 파일이 하나도 없는 것으로 확인했습니다(50개 전부 2·3주차 산출물).

3주차도 닷새 공백 뒤 한 세션에 측정 3종 + 글을 넣어 마감을 통과했습니다. **이번에도 물리적으로 가능하지만, 그때는 운이 좋았습니다**(`docs/STATUS.md`). 이번에는 운에 기대지 않도록 **선제적으로 범위를 자르고**(§4) **중단 기준을 미리 정합니다**(§7).

---

## 1. 착수 전 확인한 환경 실태 (2026-08-27 19:30, 실측)

| 항목 | 실측값 | 계획 대비 |
|---|---|---|
| WSL 루트 여유 | `/dev/sdd 1007G, 780G avail (19%)` | ✅ 문제 없음 |
| Windows C: 여유 | **198.4 GB** | ✅ 문제 없음 |
| GPU | RTX 4080 Laptop, 12282 MiB **중 0 MiB 사용** | ✅ 비어 있음 |
| k3s 노드 | `Ready`, v1.36.2+k3s1 | ✅ |
| k3s 파드 | 거의 전부 `Completed`/`Error`, **53초 전 재시작** | ⚠️ WSL 유휴 poweroff 흔적 |
| `deployment/vllm-baseline` | 존재, **replicas=0** (Service·PVC 살아 있음) | ✅ 되살리면 됨 |
| HF 캐시(PVC) | `Qwen2.5-1.5B-Instruct` · `Qwen2.5-7B-Instruct-AWQ` | ✅ 타깃 모델 재다운로드 0 |
| `Qwen2.5-0.5B-Instruct`(draft) | **없음** | ⚠️ E1 팔 C는 ~1GB 다운로드 |
| docker 이미지 | ubuntu · hello-world · pytorch 12.7GB · **tritonserver 36.3GB + 27.4GB** | 3주차 잔해 48.5GB |
| **`vllm/vllm-openai:v0.23.0`** | **docker에 없음. k3s containerd에만 있음** | ❌ **계획의 전제가 틀렸다** |

---

## 2. ★ 계획을 바꾸는 발견 3가지

### 2-1. v0.23.0은 docker가 아니라 containerd에 있다 — 런북 명령이 그대로는 안 돈다

런북 [`4주차-00`](../../articles/4%EC%A3%BC%EC%B0%A8-00%20%EC%8B%A4%EC%8A%B5%20%EC%A4%80%EB%B9%84%EC%99%80%20%EC%B8%A1%EC%A0%95%20%EA%B7%9C%EC%B9%99.md)·[`-01`](../../articles/4%EC%A3%BC%EC%B0%A8-01%20%EC%B6%94%EC%B8%A1%20%EB%94%94%EC%BD%94%EB%94%A9%EC%9D%80%20%EC%96%B8%EC%A0%9C%20%EC%86%90%ED%95%B4%EA%B0%80%20%EB%90%98%EB%8A%94%EA%B0%80.md)은 `docker run --rm vllm/vllm-openai:v0.23.0 --help` · `docker rm -f vllm` · `docker logs vllm`으로 쓰여 있습니다. 그런데 `docker images`에 이 이미지가 **없습니다**. 있는 곳은 k3s의 containerd입니다:

```
$ k3s ctr images ls -q | grep -i vllm
docker.io/vllm/vllm-openai:v0.20.0
docker.io/vllm/vllm-openai:v0.23.0
```

**런북대로 하면 `docker run`이 ~10GB를 새로 받습니다.** 설계의 *"추가 다운로드 0"* 전제가 여기서 깨집니다. 그리고 3주차에 디스크로 하루를 날린 바로 그 실수의 재발입니다.

### 2-2. 매니페스트에 임의 플래그를 넣을 자리가 없다 — 이번 주 유일한 도구 작업

`labs/wsl2-vllm-baseline/k8s/vllm-baseline.yaml`의 `args`는 고정 문자열이고, env로 뺀 것은 `MAX_NUM_SEQS` · `MAX_MODEL_LEN` · `GPU_MEMORY_UTILIZATION` **셋뿐**입니다. `redeploy.sh`의 `redeploy KEY=VALUE`도 `kubectl set env`만 합니다.

**이번 주에 흔들어야 하는 것은 전부 새 플래그입니다** — `--speculative-config`(E1) · `--max-num-batched-tokens`(E2) · `--no-enable-prefix-caching`(E3). **지금 도구로는 E1·E2·E3가 전부 막혀 있습니다.** 계획서에 없던 항목이고, 이게 이번 주의 첫 번째 블로커입니다.

### 2-3. 디스크는 이번 주 리스크가 아니다 — ⓪에서 내려도 된다

브리프·런북이 *"이번 주 첫 번째 명령은 `df -h`"* 라고 못박아 뒀지만, 실측 여유는 WSL 780G · C: 198GB입니다. 3주차 잔해 48.5GB를 지워도 지금은 얻는 게 없습니다. **필수에서 선택으로 내립니다.** 다만 §2-1의 `docker run`을 실수로 돌리면 그때 디스크가 다시 문제가 되므로, **경계는 "docker에 새 이미지를 받지 않는다"로 옮깁니다.**

---

## 3. 실행 경로 결정 — k3s를 유지한다

| | 경로 A: k3s Deployment 유지 | 경로 B: containerd→docker 이관 |
|---|---|---|
| 준비 | 매니페스트에 `EXTRA_ARGS` 추가 (~15분) | `k3s ctr images export` ~10GB tar → `docker load` (~15분 + 디스크 20GB) |
| 팔 전환 | 롤아웃 1~3분(파드 재기동, 모델은 PVC 캐시) | `docker rm -f` → `docker run` 1~2분 |
| 기존 도구 | `redeploy.sh`(롤아웃 실패 감지·`/v1/models` 폴링·`mark`) **그대로** | 전부 못 씀 |
| 메트릭 | ServiceMonitor로 Prometheus에 그대로 적재 | `curl :8000/metrics` 수동 |
| 2주차 B1 기준선과의 비교 | **같은 실행 경로** | 다른 경로 — 통제 변수가 샌다 |

**경로 A를 택합니다.** 결정적인 이유는 마지막 줄입니다. 설계의 「재사용하는 것」 표가 `results/b1-*.json`을 2주차 기준선으로 쓰겠다고 적어 뒀는데, 그건 k3s에서 잰 숫자입니다. 여기서 docker로 갈아타면 **3주차에 데인 자리(같은 저울에 안 올라간 숫자)를 스스로 다시 만드는 것**입니다.

**대가**: 런북 4편의 `docker` 명령을 `kubectl`로 정정해야 합니다(⓪-4).

---

## 4. 선제 범위 축소 — 지금 자른다

설계서의 잘라내기 순서를 **마감 직전이 아니라 지금** 적용합니다. 시간이 남으면 되살리는 방향이지, 모자라서 잘라내는 방향이 아닙니다.

| 실험 | 이번 주 확정 범위 | 잘라낸 것 | 되살리는 조건 |
|---|---|---|---|
| **E1 추측 디코딩** ★ | **vanilla / ngram** × `decode`·`prefill` × 동시성 **1·4·16·64** | — (draft 0.5B 팔은 **선택**, §4-1) | — |
| **E2 chunked prefill** | `--max-num-batched-tokens` **512 / 8192** (양 끝) | 중간값 2048 | 토요일 오후 여유 시 |
| **E3 prefix caching** | **2×2 전체 유지** | — | (가장 싸다 — 도구 수정 0) |
| **E4 스케줄러 해부** | 유지, **본문** | — | 시간 부족 시 부록으로 |

**E1의 동시성 축(1·4·16·64)은 자르지 않습니다.** 이득이 뒤집히는 걸 보이는 게 글의 핵심이라 양 끝이 반드시 필요합니다.

### 4-1. draft 0.5B 팔 — 디스크 제약이 풀려 되살립니다 (2026-08-27 갱신)

사용자 확인으로 **다운로드 제약이 없어졌습니다**(WSL 780G · C: 198GB). 다만 draft 팔의 진짜 비용은 다운로드가 아니라 **비교 가능성**입니다.

- 12GB에 target 1.5B + draft 0.5B가 같이 올라가면 `gpu_memory_utilization`이 그대로여도 **KV 예산이 vanilla 팔과 달라집니다.**
- 그러면 *"추측 디코딩이 느려서"* 와 *"KV가 좁아져서"* 를 구별할 수 없습니다 — 3주차에 계층마다 vLLM 버전이 달라 겪은 것과 **같은 종류의 오염**입니다.

**따라서 순서를 이렇게 둡니다**: vanilla·ngram **2팔을 먼저 완주**해 글이 설 재료를 확보하고, 그다음 draft 팔을 붙입니다. draft 팔은 기동 로그의 KV 예산이 vanilla와 **비교 가능한 범위인지 먼저 판정**하고, 어긋나면 같은 표에 넣지 않고 **"왜 같은 저울에 못 올렸는가"를 글에 적습니다.** 그것 자체가 3주차 교훈의 연장이라 버리는 재료가 아닙니다.

- 다운로드: `Qwen/Qwen2.5-0.5B-Instruct` ~1GB (PVC 캐시에 없음 — 확인함)
- 슬롯: 금요일 E1·E2 완주 후, 또는 토요일 오전 예비

---

## 5. 시간표

| 슬롯 | 할 일 | 산출물 |
|---|---|---|
| **목 8/27 21:00–23:00** | ⓪ 선행 전부 (§6) | `e-vllm-help.txt` · `EXTRA_ARGS` 패치 + 테스트 · 런북 정정 · 스모크 1회 |
| **금 8/28 19:00–23:00** | **E1**(2팔 × 2워크로드) → **E2**(2값) | `e1-*.json` 4종 + 기동로그·메트릭 / `e2-*.json` |
| **토 8/29 10:00–14:00** | **E3**(2×2) + 예비(실패 복구·draft 팔 되살리기) | `e3-*.json` 4종 |
| **토 8/29 14:00–18:00** | **E4** 소스 해부 + 분석·그림 | `e4-scheduler-notes.md` · `fig-e1-*.svg` |
| **토 8/29 19:00–24:00** | 글 초고 | `articles/<제목>.md` |
| **일 8/30 06:00–09:00** | 윤문 → 노션 발행 → **링크 공유** ★ | 마감 |

**E4는 GPU가 필요 없습니다.** 금요일 롤아웃 대기 시간(회당 1~3분, 총 8~10회)에 끼워 넣으면 토요일 오후가 통째로 예비일이 됩니다.

---

## 6. 단계별 상세

### ⓪ 선행 (목 21:00–23:00) — 전부 `[auto]`, GPU 측정 없음

#### ⓪-1. ✅ keeper — **해결 (2026-08-27 19:48). 다만 처음 시도한 방법은 틀렸습니다**

**먼저 시도했다가 실패한 것 — `.wslconfig`의 `vmIdleTimeout=-1`.** `[wsl2]`에도 `[experimental]`에도 넣어 보고 BOM까지 제거해 `wsl --shutdown`으로 재적용했지만, **100초 무활동 후 VM이 그대로 내려갔습니다**(WSL 2.7.8.0). `.wslconfig`는 원복했습니다.

**원인은 유휴 타이머가 아니었습니다.** WSL은 **distro 안에 살아 있는 세션이 없으면** VM을 내립니다. systemd가 켜져 있어 k3s가 `active`여도 마찬가지입니다. 그래서 **여전히 keeper가 필요합니다** — 다만 *"사람이 창을 열어 두는"* 방식일 필요는 없습니다.

**작동하는 방법 — 분리된 Windows 프로세스로 띄웁니다:**

```powershell
Start-Process -FilePath "wsl.exe" `
  -ArgumentList '-d','Ubuntu','-u','root','--','sleep','infinity' `
  -WindowStyle Hidden -PassThru
```

**검증 결과 PASS** — 100초 무활동 뒤에도 keeper 생존(PID 13748), WSL `Running`. 이건 에이전트의 백그라운드 태스크가 아니라 **독립된 Windows 프로세스**라서 세션이 끝나도 살아남습니다. 창을 띄워 둘 필요도, 사람이 지킬 필요도 없습니다. **재부팅하면 사라지므로 그때 다시 띄우세요.**

**현재 상태 (검증 완료)**: keeper 생존 · k3s `active` · 파드 전부 `Running` · GPU `0 MiB / 12282 MiB`.

세션 시작 시 확인:

```powershell
Get-Process wsl -ErrorAction SilentlyContinue   # keeper가 살아 있나
```
```bash
kubectl get pods -A | grep -v Running   # (Completed 2개는 helm-install 잔여, 정상)
nvidia-smi                              # 0 MiB인지
```

> ⚠️ **남아 있는 무해한 잡음**: 모든 `wsl` 호출에 `wsl: Failed to translate 'D:\VulkanSDK\1.4.321.1\Bin'`가 붙습니다. **없는 드라이브(D:) 경로가 시스템 PATH에 박혀 있어서**이고 동작에는 영향이 없습니다. 지우려면 **관리자** PowerShell이 필요합니다(사용자 PATH가 아니라 시스템 PATH).

#### ⓪-2. 플래그·메트릭 이름 확인 — **`docker run` 금지**

```bash
# X  docker run --rm vllm/vllm-openai:v0.23.0 --help   <- ~10GB 새로 받는다
kubectl run vllm-help -n llm-serving-lab --rm -i --restart=Never \
  --image=vllm/vllm-openai:v0.23.0 \
  --overrides='{"spec":{"containers":[{"name":"vllm-help","image":"vllm/vllm-openai:v0.23.0","imagePullPolicy":"IfNotPresent","args":["--help"]}]}}' \
  | tee labs/wsl2-vllm-baseline/results/e-vllm-help.txt
```

⚠️ **`imagePullPolicy: IfNotPresent`가 핵심입니다.** 빠뜨리면 `Always`로 돌아 결국 받습니다.

**✅ 완료 (2026-08-27 20:10).** 원본 `results/e-vllm-help.txt`(1,714줄). 첫 시도는 `vllm serve --help`가 *"Failed to infer device type"* 로 죽었습니다 — **help를 뽑는 데도 GPU가 필요합니다.** GPU를 붙이고 `--help=all`(그냥 `--help`는 **그룹 이름만** 보여줌)로 다시 받았습니다.

**확인 결과 — 런북의 1순위 후보보다 나은 게 있었습니다:**

| 쓰는 곳 | 계획했던 것 | **실제로 쓸 것** | 근거 |
|---|---|---|---|
| E1 ngram | `--speculative-config '{"method":"ngram",...}'` | **`--spec-method ngram --spec-tokens 5`** | `e-vllm-help.txt:1667,1679` |
| E1 draft | `--speculative-config '{"model":"...",...}'` | **`--spec-model Qwen/Qwen2.5-0.5B-Instruct --spec-tokens 5`** | `:1676` — *"model을 주면 method는 자동 감지"* |
| E2 | `--max-num-batched-tokens N` | 그대로 ✅ | `:1351` |
| E3 | `--no-enable-prefix-caching` | 그대로 ✅ | `:860` — `--enable-prefix-caching, --no-enable-prefix-caching` 쌍, 기본 `None` |

★ **v0.23.0은 `--speculative-config` JSON 말고 평탄화된 `--spec-*` 플래그를 제공합니다.** JSON을 쓰면 `EXTRA_ARGS`의 단어 분리 때문에 **공백 하나로 조용히 깨지는데**, 평탄화 플래그는 그 위험이 아예 없습니다. 이쪽을 씁니다.

**덤으로 풀린 것들:**
- ✅ **draft 모델 방식은 V1에서 지원됩니다** — `--spec-method` 선택지에 `draft_model`이 있습니다(`ngram`·`ngram_gpu`·`eagle`·`eagle3`·`medusa`·`suffix` 등과 함께). 계획서의 ⬜ 미확인 항목이 해소됐습니다.
- ⚠️ **`prompt_lookup_min`/`_max`에는 평탄화 플래그가 없습니다.** 굳이 조이려면 `--speculative-config` JSON을 써야 하고, 그러면 공백 함정으로 돌아갑니다. **이번 주는 기본값으로 두고, 값을 글의 재현 부록에 기동 로그로 남깁니다.**
- ⚠️ **`--max-num-batched-tokens`의 하한은 문서화돼 있지 않습니다.** 대신 `'1k'`·`'2M'` 같은 표기를 받습니다. 512가 거부되면 그때 올립니다.
- ℹ️ WSL 경고가 매 기동에 뜹니다 — `Using 'pin_memory=False' as WSL is detected. This may slow down the performance.` **모든 팔에 똑같이 적용되므로 팔 사이 비교는 성립합니다.** 절대 성능을 인용할 때만 각주로 달 것.
- ℹ️ vLLM 설치 경로 확인 — `/usr/local/lib/python3.12/dist-packages/vllm`. **E4용 `scheduler.py`(2,422줄)를 같은 파드에서 이미 뽑아 `results/e4-scheduler.py`에 저장했습니다.**

> `vllm:spec_decode_*` 메트릭 이름은 **켠 뒤에야 나타나므로** E1 팔 기동 후에 확인합니다.

#### ⓪-3. ✅ `EXTRA_ARGS` 패치 — **완료 (2026-08-27)** ★ 이번 주 유일한 도구 작업 (§2-2)

**결과**: `k8s/vllm-baseline.yaml` args 끝에 따옴표 없는 `$EXTRA_ARGS` + 빈 문자열 env 추가. `labs/wsl2-vllm-baseline/test_manifest.py` 신규(15 tests + 12 subtests). **게이트 91건 → 106건 green.**
가장 중요한 가드 `test_extra_args_is_unquoted`는 **역방향으로 검증했습니다** — 일부러 `"$EXTRA_ARGS"`로 바꿔 돌리니 그 테스트만 정확히 실패했고, 되돌린 뒤 다시 통과했습니다.
그 외 감시 항목: 이미지 `v0.23.0` 고정 · `imagePullPolicy: IfNotPresent`(§2-1 재발 방지) · 모델 고정 · GPU 1장 · `runtimeClassName: nvidia` · `strategy: Recreate` · **실험 플래그가 매니페스트에 박히지 않았는가**(다음 실험 오염 방지) · `redeploy.sh`가 임의 KEY=VALUE를 넘기는가.

<details><summary>적용한 내용</summary>

`k8s/vllm-baseline.yaml`의 args 끝에 `$EXTRA_ARGS`를 붙이고 빈 문자열 env를 추가합니다.

```yaml
              --max-num-seqs "$MAX_NUM_SEQS"
              $EXTRA_ARGS          # <- 따옴표 없이. 셸 단어 분리로 여러 플래그가 된다
...
            - name: EXTRA_ARGS
              value: ""
```

그러면 기존 헬퍼가 그대로 먹습니다:

```bash
source labs/wsl2-vllm-baseline/redeploy.sh
redeploy EXTRA_ARGS='--speculative-config {"method":"ngram","num_speculative_tokens":5}'
redeploy EXTRA_ARGS=''            # 원복
```

</details>

#### ⓪-4. 런북 정정 (§2-1)

`4주차-00`·`-01`·`-02`·`-03`의 `docker run` / `docker rm -f vllm` / `docker logs vllm`을 kubectl 계열로 바꿉니다.

| 런북의 명령 | 바꿀 것 |
|---|---|
| `docker rm -f vllm && nvidia-smi` | `redeploy EXTRA_ARGS='...'` (Recreate 전략이라 옛 파드가 먼저 죽습니다) + `nvidia-smi` |
| `docker logs vllm 2>&1 \| grep -iE "kv cache\|maximum concurrency"` | `kubectl -n llm-serving-lab logs deploy/vllm-baseline \| grep -iE ...` |
| `curl -s localhost:8000/metrics` | 그대로 (`redeploy`가 포트포워딩을 다시 걸어 줍니다) |
| `df -h` 절 | 필수 → **선택**으로 강등, 대신 *"docker에 이미지를 받지 말 것"* 경고로 교체 |

#### ⓪-5. 스모크 1회 (10분)

```bash
redeploy MAX_NUM_SEQS=64 MAX_MODEL_LEN=4096 GPU_MEMORY_UTILIZATION=0.85 EXTRA_ARGS=''
confirm_slots                                    # 반영 확인
python3 benchmark.py --scenarios short --concurrency 1 --requests-per-level 2 \
  --output results/e0-smoke.json
```

**Done 기준**: 2주차 `b1-slots-64-short.json`과 같은 자릿수. 다르면 여기서 멈추고 원인부터 — 이 상태로 E1을 재면 전부 버립니다.

---

### E1 — 추측 디코딩 (금 19:00–21:30, 2팔)

**팔마다 3단계를 반드시 밟습니다.** ③을 빠뜨리면 *"이득이 없다"* 가 사실은 *"안 켜졌다"* 가 됩니다(3주차 `accelerator_type: null`).

```bash
ARM=e1-vanilla                    # 또는 e1-ngram

# 1) 띄우기
redeploy EXTRA_ARGS=''            # vanilla
# redeploy EXTRA_ARGS='--speculative-config {"method":"ngram","num_speculative_tokens":5,"prompt_lookup_min":2,"prompt_lookup_max":5}'

# 2) 기동 로그 — KV 예산이 팔 사이에 같은지 (별표)
kubectl -n llm-serving-lab logs deploy/vllm-baseline \
  | grep -iE "kv cache|maximum concurrency|speculat|ngram|draft" \
  | tee "results/${ARM}-startup.txt"

# 3) 메트릭 존재 확인 — ngram 팔에 spec_decode가 없으면 측정 금지 (별표)
curl -s localhost:8000/metrics | grep -oE '^vllm:[a-z0-9_]+' | sort -u \
  > "results/metrics-${ARM}.txt"
grep -c spec_decode "results/metrics-${ARM}.txt"
```

측정 — **팔당 1회 실행**으로 워크로드 2종 × 동시성 4레벨이 한 번에 나옵니다:

```bash
mark "E1 ${ARM} start"
python3 benchmark.py --scenarios decode,prefill --concurrency 1,4,16,64 \
  --requests-per-level 8 --output "results/${ARM}.json"
mark "E1 ${ARM} end"
curl -s localhost:8000/metrics | grep -E 'spec_decode|num_requests' \
  > "results/${ARM}-metrics-after.txt"        # 수용률의 원본
```

**보는 것**: ITL·TPOT(이득) / 처리량(손해) / **수용률**(`num_accepted / num_draft`). 가설은 저동시성 이득·고동시성 역효과(`Ch7.md:949`).
⚠️ **`decode`만 보고 "ngram은 효과 없다"고 쓰지 말 것** — ngram은 출력이 입력을 되풀이할 때만 맞으므로 `prefill`(긴 문맥)이 실험군입니다.
**소요**: 팔당 롤아웃 3분 + 벤치 8~16분 → 2팔 **40분~1시간**.

---

### E2 — chunked prefill (금 21:30–23:00)

⚠️ **`benchmark.py`는 시나리오를 순차로 돕니다**(`run_scenario`가 시나리오마다 별도 executor). `--scenarios prefill,decode`로는 **안 섞입니다** — 간섭을 재려는 실험인데 간섭이 안 생깁니다. **두 프로세스 동시 실행이 코드 수정 없는 유일한 방법입니다.**

```bash
for MNBT in 512 8192; do
  redeploy EXTRA_ARGS="--max-num-batched-tokens ${MNBT}"
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -iE "kv cache|maximum concurrency|batched" > "results/e2-mnbt${MNBT}-startup.txt"
  mark "E2 mnbt=${MNBT} start"
  python3 benchmark.py --scenarios prefill --concurrency 8 --requests-per-level 8 \
    --output "results/e2-mnbt${MNBT}-prefill.json" &
  python3 benchmark.py --scenarios decode  --concurrency 8 --requests-per-level 8 \
    --output "results/e2-mnbt${MNBT}-decode.json" &
  wait
  mark "E2 mnbt=${MNBT} end"
done
```

**보는 것**: 디코드 쪽 **ITL 지터**가 프리필 때문에 얼마나 튀는가 ↔ 프리필 쪽 **TTFT**가 얼마나 늘어나는가. 그 교환비가 결과입니다.
**글에서의 자리**: 같은 GPU에 둘이 있으면 반드시 서로를 민다 → 청크는 완화일 뿐 제거가 아니다 → 제거하려면 물리적 분리 = **PD 분리**. GPU 1장에서 PD 분리의 동기를 설명하는 대역입니다.
**소요**: 롤아웃 2회 + 동시 벤치 2회 ≈ **30~40분**. 3주차 이월분 ③-b 해소.

---

### E3 — prefix caching (토 10:00–11:30)

**도구 수정 0.** `prefill` 시나리오 프롬프트가 같은 문단을 24회 반복한 긴 문맥이고(`benchmark.py:30`), `--unique-prefix`(`:160`)가 UUID를 붙여 일부러 적중을 막습니다. 서버 ON/OFF와 곱하면 2×2가 그대로 나옵니다.

```bash
for CACHE in on off; do
  if [ "$CACHE" = off ]; then redeploy EXTRA_ARGS='--no-enable-prefix-caching'
  else                        redeploy EXTRA_ARGS=''
  fi
  for SHARE in shared unique; do
    UNIQ=""; [ "$SHARE" = unique ] && UNIQ="--unique-prefix"
    curl -s localhost:8000/metrics | grep -E 'prefix_cache' > "results/e3-${CACHE}-${SHARE}-before.txt"
    mark "E3 cache=${CACHE} share=${SHARE}"
    python3 benchmark.py --scenarios prefill --concurrency 4 --requests-per-level 8 \
      $UNIQ --output "results/e3-${CACHE}-${SHARE}.json"
    curl -s localhost:8000/metrics | grep -E 'prefix_cache' > "results/e3-${CACHE}-${SHARE}-after.txt"
  done
done
```

**보는 것**: TTFT + `vllm:prefix_cache_hits_total / queries_total`의 **증분**(before/after 차). 3주차에 v0.23.0에서 이 두 메트릭의 존재는 실측 확인됐습니다(`gpu_` 접두 버전은 없음).
**축과의 연결**: 캐시 적중은 프리필 연산을 통째로 건너뜁니다 = compute-bound 구간을 지웁니다. 공유가 없으면 순수 오버헤드 — 그래서 2×2가 필요합니다.
**소요**: 롤아웃 2회 + 짧은 벤치 4회 ≈ **30분**.

---

### E4 — 스케줄러 해부 (금 대기시간 + 토 오후) — GPU 불필요

`vllm/v1/core/sched/scheduler.py`를 읽고 **E1·E2·E3가 같은 토큰 예산 계산의 어느 항을 건드리는지** 코드로 짚습니다. 출발점은 `Ch8.md:9`의 `num_computed_tokens` ↔ `num_tokens_with_spec`.

```bash
# 경로는 exec로 먼저 확인 (파이썬 버전에 따라 dist-packages 경로가 다름)
kubectl -n llm-serving-lab exec deploy/vllm-baseline -- \
  python -c "import vllm,os;print(os.path.dirname(vllm.__file__))"
kubectl -n llm-serving-lab exec deploy/vllm-baseline -- \
  cat <위경로>/v1/core/sched/scheduler.py \
  > labs/wsl2-vllm-baseline/results/e4-scheduler.py
```

짚을 세 자리:
1. **E2** — 한 스텝의 토큰 예산 상한(`--max-num-batched-tokens`)이 프리필 요청을 어디서 자르는가
2. **E3** — `num_computed_tokens`가 캐시 적중분만큼 **미리 올라간 채로** 시작하는 자리
3. **E1** — 검증할 draft 토큰이 같은 예산에서 **어느 항으로 빠져나가는가**(`num_tokens_with_spec`)

**이게 없으면 글이 "재 봤더니 이렇더라"에서 멈춥니다.** 3주차 글과의 차별점이 여기입니다.

---

## 7. 중단 기준 (kill switch) — 미리 정한다

| 시점 | 조건 | 행동 |
|---|---|---|
| 목 23:00 | ⓪-3 `EXTRA_ARGS` 패치가 `make check` green이 아님 | **경로 B(docker 이관)로 전환.** 통제 변수는 포기하고 글에 한계로 명시 |
| 금 21:30 | E1이 아직 안 끝남 | E1 `prefill` 워크로드만 남기고 `decode` 포기, E2로 진행 |
| 금 23:00 | E2 미착수 | **E2를 버리고 E3로.** E3가 더 싸고(도구 수정 0) 축을 똑같이 증명함. E2는 "이월"로 글에 명시 |
| 토 14:00 | 측정이 둘 이하만 성공 | **더 재지 않고 글로 넘어간다.** 실험 하나 + E4 소스 해부로도 축은 선다 |
| 토 24:00 | 초고 미완 | 분량을 줄이지 말고 **실험 하나를 통째로 부록으로** 내린다 |

**절대 자르지 않는 것**: ⑥ 노션 발행 + ⑦ 링크 공유. **미공유 1회 = 제명**입니다.

---

## 8. 위험 등록부

| 위험 | 징후 | 대응 |
|---|---|---|
| **조용한 실패** — 플래그명이 틀려 엔진이 무시하고 뜸 | `metrics-e1-ngram.txt`에 `spec_decode` 0개 | 측정 중단, `--help` 재확인. **3주차 `accelerator_type: null`과 같은 종류** |
| **KV 예산이 팔마다 다름** | `${ARM}-startup.txt`의 `Maximum concurrency` 불일치 | 비교 가능 여부부터 판정. 어긋나면 그 팔은 표에서 빼고 이유를 글에 |
| **VRAM 미반환** | 롤아웃 직후 KV 예산이 절반 | `nvidia-smi`로 0 확인 후 재롤아웃. 3주차 미해결 관측(59.50x↔28.77x)이 이 가설과 맞음 |
| **GPU 1장 롤링 교착** | 새 파드 Pending, 옛 파드 Running | 매니페스트가 `strategy: Recreate`라 원칙적으로 없음. 생기면 옛 ReplicaSet을 `scale --replicas=0` |
| **c=64 잡음 10%** | E1 고동시성 차이가 10%대 | **결론의 근거로 쓰지 않는다.** c≤32는 1.3% 안 |
| **WSL 유휴 poweroff** | 파드가 `Completed`로 바뀜, keeper 프로세스 없음 | ✅ 분리 keeper로 해소(⓪-1). **`vmIdleTimeout=-1`은 안 먹습니다** — 유휴 타이머가 아니라 *"세션이 없으면 내린다"* 가 원인. 재부팅하면 다시 띄울 것 |
| **`docker run` 실수** | 10GB 다운로드 시작 | 즉시 중단. 이번 주 docker는 건드리지 않음 — 디스크가 아니라 **통제 변수** 문제 |
| **draft 팔의 KV 예산 오염** | `e1-draft-startup.txt`의 `Maximum concurrency`가 vanilla와 다름 | 다운로드는 이제 자유롭지만 **비교 가능성은 별개**(§4-1). 어긋나면 같은 표에 넣지 말고 이유를 글에 |

---

## 9. 산출물 목록 — 하나라도 비면 그 실험은 글에 못 쓴다

측정이 끝나면 `labs/wsl2-vllm-baseline/results/`에 아래가 있어야 합니다.

```
e-vllm-help.txt                          0  플래그 확인 원본
e0-smoke.json                            0  기준선 일치 확인
e1-{vanilla,ngram}.json                  E1 측정 (워크로드 2 x 동시성 4)
e1-{vanilla,ngram}-startup.txt           E1 KV 예산 — 팔 비교 가능 판정
metrics-e1-{vanilla,ngram}.txt           E1 spec_decode 존재 확인
e1-{vanilla,ngram}-metrics-after.txt     E1 수용률 원본
e2-mnbt{512,8192}-{prefill,decode}.json  E2 간섭 (동시 실행)
e2-mnbt{512,8192}-startup.txt            E2 기동 로그
e3-{on,off}-{shared,unique}.json         E3 2x2
e3-*-{before,after}.txt                  E3 prefix_cache 증분
e4-scheduler.py + e4-scheduler-notes.md  E4 소스 해부
```
