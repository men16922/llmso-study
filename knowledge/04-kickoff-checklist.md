# 04. 시작 전 체크리스트

**스터디 시작: 2026-08-02 (일) 20:30**

> 이 문서는 "읽는 문서"가 아니라 **체크하며 실행하는 문서**입니다. 위에서부터 순서대로 하세요.

## ① 계정 준비 — 8/2 전까지

- [x] 슬랙 초대 메일 확인 → `CloudNetaStudy` 워크스페이스 `llmso` 채널 입장
- [x] 슬랙 프로필을 **`이름-닉네임`** 형식으로 변경 (예: `홍길동-gasida`)
- [x] 노션 초대 메일 확인 → 임시암호키로 로그인 (Guest 권한, 유료 가입 불필요)
- [x] ZOOM 무료 가입 + 프로필에 **본명·사진** 설정

> AWS GPU 쿼터는 여기 있었지만 **6주차(9/6)용이라 8월 하순으로 미뤘습니다.** → [아래 ⑥](#-aws-gpu-쿼터--8월-하순까지)

---

## ② 필수 영상 (총 55분) — 8/1까지

[priority-guide.md](./references/priority-guide.md)의 🔴필수 5편입니다. **시간이 없으면 1~3번 20분만이라도.**

- [x] ① [LLM prefill 설명](https://youtu.be/Vuu27UTFUZ8) — 5분
- [x] ② [KV cache](https://youtu.be/sq3XGM1qdQY) — 8분
- [x] ③ [Flash attention의 원리](https://youtu.be/4Tw_ytMYHLI) — 7분
- [x] ④ [왜 컴퓨터는 한 가지 메모리만 쓰지 않을까](https://youtu.be/TfhL5kBiQVI) — 27분
- [x] ⑤ [LLM 설명 (요약버전)](https://youtu.be/HnvitMTkXro) — 8분 *(트랜스포머를 이미 안다면 생략 가능)*

**왜 이 3편이 먼저인가**: 1주차 CH2가 트랜스포머 → 자기회귀 생성 → **KV cache → prefill/decode** → vLLM 순으로 나갑니다. ①②③을 보고 가면 강의 중 개념 설명을 따라가는 게 아니라 **적용을 보는** 상태가 됩니다.

- [ ] (선택) [Transformer Explainer](https://poloclub.github.io/transformer-explainer/) 5분간 직접 조작해보기

---

## ③ 1주차 예습 — 8/1 (토) 권장

1주차 범위: **CH1 (Introduction to Model Serving) + CH2 (Large Language Model Serving)**

- [ ] **[05-week1-prep.md](./05-week1-prep.md) 읽기** — CH1~2 핵심을 미리 정리해둔 노트
- [ ] [00-study-overview.md](./00-study-overview.md) 주차별 커리큘럼 표 훑기
- [ ] 교재가 있다면 CH1~2, 없다면 아래 대체 자료
  - [ ] [Inference Engineering PDF](./references/pdf/inference-engineering-2026.pdf) **CH0 Inference (p.17)** + **CH2 Models (p.41)**
  - 찾기: `python3 tools/search_index.py --outline inference-engineering --depth 2`
- [ ] CH2 핵심어를 미리 인덱스에서 위치 확인해두기

```bash
python3 tools/search_index.py "KV cache"
python3 tools/search_index.py "prefill decode"
python3 tools/search_index.py "attention"
```

---

## ④ 8/2 (일) 스터디 당일

- [ ] 20:20까지 ZOOM 입장 (영상·음성 OFF 기본)
- [ ] 질문은 슬랙/줌 채팅 모두 사용 가능
- [ ] 녹화본이 제공되므로 놓친 부분은 다시 볼 수 있음

### 끝나고 바로

- [ ] **과제 시작** — 마감은 **8/9 (일) 09:00**
  - 정리 글을 올릴 곳 정하기 (블로그 / GitHub / 링크드인 공개 글 등)
  - 과제 유형 4가지 중 선택 → [02-assignments.md](./02-assignments.md)
  - ⚠️ **특별한 이유 없이 1회 미공유 시 제명**

---

## ⑤ (옵션) 로컬 GPU가 있다면

없어도 스터디 참여에 지장은 없습니다. 있다면 미리 해두면 실습이 수월합니다.

- [ ] Ubuntu **24.04 Server** (26.04 아님 — K8s 생태계 툴이 24.04까지 지원)
- [ ] **Secure Boot 끄기** (안 끄면 NVIDIA 커널 모듈 로드 실패)
- [ ] NVIDIA Driver → Docker → NVIDIA Container Toolkit
- [ ] 확인: `docker run --gpus all ubuntu nvidia-smi`

상세 절차 → [subpages/gpu-setup-docker-k8s.md](./subpages/gpu-setup-docker-k8s.md)

> WSL은 비권장입니다. GPU-PV 구조라 PCIe 패스스루가 아니고 기능 제한이 있습니다.

---

## ⑥ AWS GPU 쿼터 — 8월 하순까지

**6주차(9/6) EKS 실습용**입니다. 표준 증설은 보통 몇 시간~며칠이면 승인되므로 지금 급하게 할 필요는 없습니다. **8월 셋째 주쯤(~8/23)** 신청해두면 거절 후 재신청할 여유까지 확보됩니다.

- [ ] AWS 계정 준비 (없다면)
- [ ] 쿼터 증설 신청 (아래 표)
- [ ] 승인 확인

| 항목 | 값 |
|---|---|
| 서비스 | **Amazon EC2** |
| 쿼터 이름 | **Running On-Demand G and VT instances** |
| 단위 | **vCPU 수** (인스턴스 대수가 아님) |
| 목표 인스턴스 | `g6e.2xlarge` = **8 vCPU** |
| 신청 값 | 최소 **8**, 여유 있게 **16~32** 권장 |

```
AWS Console → Service Quotas → AWS services → Amazon Elastic Compute Cloud (Amazon EC2)
→ "Running On-Demand G and VT instances" 검색 → Request increase at account level
```

- **리전을 확인하세요.** 쿼터는 리전별입니다. 워크숍을 돌릴 리전에 신청해야 합니다.
- 신청 사유에는 "머신러닝 추론 워크숍 실습" 정도로 구체적으로 적으면 승인이 빠릅니다.
- 거절되면 사유를 보고 재신청하거나 리전을 바꿔보세요.

> GCP/Azure를 쓸 계획이면 각각 `GPUs (all regions)` 할당량, `Standard NCASv3_T4 Family vCPUs` 등에 해당하는 증설을 신청하세요. 다만 **6주차는 AWS EKS 환경**이라 AWS 계정은 별도로 필요합니다.

---

## 미리 알아둘 함정

| 함정 | 대응 |
|---|---|
| **GPU 쿼터 승인 지연** | 8월 하순까지는 신청. **리전별로 따로** 신청해야 함 |
| **GPU 인스턴스 요금 누적** | 실습 후 `terraform destroy` / 인스턴스 종료 필수. NAT Gateway·LoadBalancer·EBS도 과금 |
| **6주차 ODCR** | 용량 예약은 **예약 시점부터 과금**. 실습 직전에 만들고 끝나면 해제 |
| **과제 제출표 이름 혼동** | 모든 멤버가 편집 권한 보유. 본인 이름 확인 후 업로드 |
| **자료 외부 유출** | 노션 내용은 외부 공개 금지. 가공한 글은 권장 → [03-study-rules.md](./03-study-rules.md) |

---

## 진행 상황 한눈에

| 날짜 | 할 일 | 비고 |
|---|---|---|
| ~8/1 | 슬랙·노션·ZOOM 가입 | ✅ 완료 |
| ~8/1 | 필수 영상 20분 (prefill → KV cache → Flash) | ✅ 완료 |
| 8/1 (토) | 1주차 CH1~2 예습 | → [1주차 예습 노트](./05-week1-prep.md) |
| **8/2 (일) 20:30** | **스터디 1주차** | ZOOM |
| 8/9 (일) 09:00 | 1주차 과제 마감 | 미공유 1회 = 제명 |
| **~8/23** | **AWS GPU 쿼터 신청** | 남은 준비물은 이것뿐 |
| 9/6 (일) | 6주차 EKS 실습 | 쿼터가 여기서 필요 |
