# 01. 실습 환경 준비

## 필수

- **클라우드 GPU 인스턴스 사용 준비** — AWS / GCP / Azure 중 택일
  - 계정, 결제 수단, GPU 인스턴스 쿼터(quota) 사전 신청 필요 (신규 계정은 GPU 쿼터 승인에 시간이 걸릴 수 있음)
- **6주차(09-06)는 AWS EKS 환경**에서 진행
  - 워크숍 권장 인스턴스: [`g6e.2xlarge`](https://instances.vantage.sh/aws/ec2/g6e.2xlarge) (NVIDIA L40S 48GB, 8 vCPU, 64GB RAM)

## 옵션

- GPU 카드가 **최소 1장** 장착된 로컬 PC
- 또는 [Google Colab](https://developers.google.com/colab) (무료 티어 가능)

## 체크리스트

- [ ] 클라우드 계정 생성 및 결제 수단 등록
- [ ] GPU 인스턴스 쿼터 신청 (예: AWS `G and VT instances` vCPU 한도 상향)
- [ ] AWS CLI / `kubectl` / `eksctl` / `helm` 설치 (6주차 대비)
- [ ] 로컬 GPU 환경이라면 NVIDIA Driver + CUDA + Docker(nvidia-container-toolkit) 설치
- [ ] **비용 주의** — GPU 인스턴스는 시간당 과금. 실습 후 반드시 종료/삭제

## 비용 참고

`g6e.2xlarge` 기준 온디맨드 요금은 리전에 따라 시간당 약 $2 내외 수준입니다. 하루 실습(3~4시간) 후 인스턴스와 EKS 클러스터, EBS 볼륨, NAT Gateway, LoadBalancer까지 정리하지 않으면 비용이 누적되니 실습 종료 시 `eksctl delete cluster` 등으로 전체 정리 권장.

> 정확한 최신 단가는 리전·시점에 따라 달라지므로 [AWS 요금 페이지](https://instances.vantage.sh/aws/ec2/g6e.2xlarge)에서 확인하세요.
