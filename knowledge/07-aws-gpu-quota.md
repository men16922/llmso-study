# 07. AWS GPU 쿼터 신청 가이드

6주차(2026-09-06) **Generative AI on Amazon EKS** 워크숍용입니다. 킥오프 체크리스트 [⑥](./04-kickoff-checklist.md)의 상세판입니다.

> ⚠️ **2026-08-23 확인: 쿼터가 `0`이고 신청 이력이 없습니다.** `us-east-1`·`ap-northeast-2` 둘 다입니다. **이 상태로는 GPU 인스턴스를 아예 못 띄웁니다** — 시간당 1달러짜리 짧은 실습조차 시작이 안 됩니다.

---

## 1. 지금 상태 확인 (읽기 전용)

```bash
aws service-quotas get-service-quota \
  --service-code ec2 --quota-code L-DB2E81BA --region us-east-1 \
  --query '{Name:Quota.QuotaName,Value:Quota.Value,Adjustable:Quota.Adjustable}' --output table

aws service-quotas list-requested-service-quota-change-history-by-quota \
  --service-code ec2 --quota-code L-DB2E81BA --region us-east-1 \
  --query 'RequestedQuotas[].{Status:Status,Desired:DesiredValue,Created:Created}' --output table
```

두 번째 명령이 **비어 있으면 아직 신청한 적이 없다**는 뜻입니다.

---

## 2. 신청

```
https://us-east-1.console.aws.amazon.com/servicequotas/home/services/ec2/quotas/L-DB2E81BA
→ [Request increase at account level]
→ Increase quota value: 32
```

| 항목 | 값 |
|---|---|
| 서비스 | **Amazon EC2** |
| 쿼터 이름 | **Running On-Demand G and VT instances** |
| 쿼터 코드 | **`L-DB2E81BA`** |
| 리전 | **us-east-1** (아래 §3) |
| 단위 | **vCPU 수** — 인스턴스 대수가 아닙니다 |
| 현재 값 | **0** |
| 신청 값 | **32** |

사유란에 붙여넣을 문구:

> 머신러닝 추론 워크숍 실습용입니다. Generative AI on Amazon EKS 워크숍을 진행하며, g6e.2xlarge 1~2대에서 LLM 서빙 벤치마크(vLLM)를 수행할 예정입니다. 실습 종료 후 즉시 인스턴스를 종료합니다.

### ⚠️ CLI로 신청하지 마세요

`aws service-quotas request-service-quota-increase`는 동작하지만 **사유를 적는 필드가 없습니다.** GPU 쿼터는 사유 유무가 승인 속도를 크게 가르므로 **콘솔로** 신청하세요. 값만 던져지면 사람 검토로 넘어가 늦어질 수 있습니다.

### 왜 32인가

목표 인스턴스 `g6e.2xlarge`가 **8 vCPU**라 최소는 8입니다. 그런데 8만 받으면 인스턴스 한 대에 묶여 **실습 중 교체가 안 됩니다.**

| 인스턴스 | GPU | vCPU | 32로 되나 |
|---|---|---|---|
| `g5.xlarge` | A10G 24GB ×1 | 4 | ⭕ |
| `g6e.2xlarge` | L40S 48GB ×1 | 8 | ⭕ (목표) |
| `g6.12xlarge` | L4 24GB ×4 | **48** | ❌ |

`g6.12xlarge`(TP=4 도전과제용)는 48 vCPU라 32로도 부족합니다. **0에서 48을 한 번에 부르면 사람 검토로 넘어가므로**, 필요해지면 그때 증액 신청하는 쪽이 승인 확률이 높습니다.

---

## 3. 리전 선택

**쿼터는 리전별로 따로입니다.** 신청 자체는 무료라 여러 곳에 걸어도 손해는 없습니다.

목표 인스턴스는 세 리전 모두에 있습니다(2026-08-23 `describe-instance-type-offerings` 확인). 그래서 기준은 가용성이 아니라 **워크숍을 돌릴 곳**입니다.

| 리전 | 근거 |
|---|---|
| **us-east-1 (버지니아)** ★ 선택 | AWS 워크숍의 기본값. 스터디 자료의 실습 기록도 us-east-1(`study/Ch7.md:1412`). 단가가 가장 쌈 |
| us-west-2 (오레곤) | AWS 공식 워크숍이 두 번째로 많이 쓰는 리전. GPU 재고가 비교적 여유로움 |
| ap-northeast-2 (서울) | 네트워크 지연이 짧아 직접 벤치마크를 돌릴 때 유리(TTFT에 왕복이 섞임) |

거절되면 사유를 보고 재신청하거나 **리전을 바꿔** 보세요.

---

## 4. 비용 — 승인 후 실제로 얼마

단가는 `study/Ch7.md:1423`·`:1470`의 스터디 자료 기록 기준(us-east-1 온디맨드)입니다.

| 인스턴스 | 시간당 |
|---|---|
| `g5.xlarge` (A10G 24GB) | **$1.006** |
| `g6.12xlarge` (L4 24GB ×4) | **$4.60** |
| `g4dn.xlarge` (T4 16GB) | ~$0.53 — **bf16 미지원**이라 자료가 비권장 |

| 시나리오 | 시간 | 인스턴스 | EBS | 합계 |
|---|---|---|---|---|
| 단일 GPU 벤치마크 (설치 40분 + 모델 10분 + 측정 3종) | ~4–5h | ~$5 | ~$0.5 | **약 $6** |
| TP=4 도전과제 `g6.12xlarge` | ~4h | ~$18 | ~$0.5 | **약 $19** |

자료의 *"전 실습 2.5시간, $2~3"* 이 `g5.xlarge` 기준입니다.

### ⚠️ 자료에 안 적힌 비용 두 가지

- **EBS는 인스턴스를 꺼도 계속 나갑니다.** 200GB gp3 = 월 $16(하루 약 $0.53). 자료가 200GB를 권한 건 *"venv 하나가 8.0GB"* 여서인데, 도커 이미지까지 받으면 더 큽니다. **실습이 끝나면 볼륨을 지우세요.**
- **끄는 걸 잊는 게 제일 비쌉니다.** `g6.12xlarge`를 하루 방치하면 **$110**입니다. 랩톱은 잊어도 0원이지만 EC2는 아닙니다.

스팟은 60~70% 싸지만 **중단되면 측정이 끊깁니다.** 3주차에 백그라운드 프로세스 강제 종료로 측정이 끊긴 전력이 있어 벤치마크에는 권하지 않습니다.

### 정리할 것 목록 (실습 종료 시)

인스턴스만 끄면 안 됩니다 — [`04-kickoff-checklist.md`](./04-kickoff-checklist.md)의 "미리 알아둘 함정"에도 있는 항목입니다.

- [ ] EC2 인스턴스 종료 (stop이 아니라 **terminate**)
- [ ] EBS 볼륨 삭제 (`DeleteOnTermination=true`면 자동)
- [ ] EKS 클러스터 (`eksctl delete cluster` / `terraform destroy`)
- [ ] **NAT Gateway** · **LoadBalancer** — 클러스터를 지워도 남는 경우가 있음
- [ ] ODCR(용량 예약) — **예약 시점부터 과금**되므로 실습 직전에 만들고 끝나면 해제

---

## 5. 승인 확인

```bash
aws service-quotas list-requested-service-quota-change-history-by-quota \
  --service-code ec2 --quota-code L-DB2E81BA --region us-east-1 \
  --query 'RequestedQuotas[].{Status:Status,Desired:DesiredValue}' --output table
```

`Status`가 `CASE_CLOSED` + 값이 반영되면 완료입니다. `get-service-quota`의 `Value`가 실제로 32로 바뀌었는지도 확인하세요.

표준 증설은 보통 몇 시간~며칠입니다. **6주차(09-06) 전까지 여유가 있지만, 거절 후 재신청할 시간까지 감안해 지금 넣는 것이 안전합니다.**

---

## 참고

- 킥오프 체크리스트: [`04-kickoff-checklist.md`](./04-kickoff-checklist.md) ⑥
- 환경 준비: [`01-environment-setup.md`](./01-environment-setup.md)
- 6주차 커리큘럼: [`00-study-overview.md`](./00-study-overview.md)
