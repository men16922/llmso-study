# 6주차 AWS 워크샵 원본 자료 복구본

2026-09-12에 Notion에 첨부했던 `week6-workshop-article-evidence.zip`의 81개 파일을 원래 상대 경로 그대로 복구했습니다. ZIP 원본도 이 폴더에 함께 보존합니다. 추출 파일을 ZIP 항목과 바이트 단위로 대조했습니다.

현재 독자용 원고는 [6주차 과제](../6주차%20과제.md)입니다. 이 복구본 안의 `articles/6주차 과제.md`는 **ZIP을 만들던 당시의 원고 스냅샷**입니다. 현재 원고를 덮어쓰는 용도로 사용하지 않습니다.

## 보존한 내용과 현재 글에서의 활용

| 자료 | 파일 수 | 본문·접기에서의 활용 |
| --- | ---: | --- |
| Python 코드 | 11 | API 검증 조건, 부하 생성·집계 방식, 지표 조회 쿼리, CPU 부하의 시간·작업 수 제한 |
| YAML 설정 | 8 | Ingress 규칙, Prometheus 수집 대상, Grafana 데이터 소스, HPA 정책, CloudWatch 수집 설정 |
| JSON | 37 | 기본·추가 부하 수치, HTTP 응답, 클러스터·HPA 상태, 대시보드·IAM 정책 |
| JSONL·로그·텍스트 | 12 | Neuron 모델 로딩, Pending 이벤트, CloudWatch 전송 오류, HPA 시계열, llmperf 집계 조건 |
| PNG·SVG | 10 | 실제 AWS·Grafana 화면, JSON으로 생성한 비교 그림. 중복 화면과 과거 미수집 화면도 원본 보존 |
| Markdown | 3 | 당시 아티클, 단계별 README, 실행 기록 |

기본 성능 비교는 `benchmark-final.json`을 사용합니다. 설치와 겹친 `benchmark-during-setup.json`은 예비 측정입니다. Neuron 상태 수집은 추론 부하와 동기화한 포화도 측정이 아닙니다. 이 구분은 원본을 재활용할 때도 유지합니다.

## 폴더 구성

- [실습 구성·명령](labs/eks-trainium-workshop/README.md)
- [실행 기록](labs/eks-trainium-workshop/execution-record.md)
- [당시 원고](articles/6주차%20과제.md)
- `labs/eks-trainium-workshop/results/`: 측정·상태·로그 원본
- `labs/eks-trainium-workshop/cloudwatch/`: Agent와 IAM 설정
- `labs/wsl2-vllm-baseline/benchmark.py`: 재사용한 벤치마크 코드
- `articles/screenshots/`, `articles/figures/`: 원본 화면과 비교 그림

ZIP SHA-256: `de25aa693ec0fb824e0f32faffc838015fca268b991d0d21a7b1cc8f91848066`

## 후속 관측 자료

[Neuron 가속기 동시 관측](supplementary/neuron-observation/README.md)에 추가 640건 요청의 코드·원본 결과·실제 Grafana 화면을 보존했습니다. 이 자료는 ZIP 생성 이후의 관측이며 원래 81개 파일과 구분합니다.
