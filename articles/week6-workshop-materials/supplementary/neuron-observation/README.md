# Neuron 가속기 동시 관측 보존본

2026-09-12 22:01~22:08 KST에 동시 요청 4·8개를 각각 320건 실행하면서 NeuronCore·메모리·CPU·요청 대기·HPA를 함께 관측했습니다. 기존 ZIP의 81개 파일은 그대로 두고 후속 자료를 이 폴더에 추가했습니다.

- [집계 결과](results/2026-09-12-neuron/summary.json): 조건별 1회 측정. 출력 상한 256토큰, warmup 2건.
- [실제 Grafana 화면](week6-neuron-c4-c8.png): 왼쪽 부하가 C4, 오른쪽 부하가 C8입니다.
- `raw.jsonl`은 수신 시각과 원본 Neuron 보고서, `prometheus-history.json`은 같은 시간대의 서비스 지표입니다. 모두 위 결과 폴더에 있습니다.
- `observe_neuron.py`는 실행 중인 vLLM 컨테이너의 설치된 Neuron monitor·exporter를 제한 시간 동안 실행합니다. `run_neuron_load.py`는 별도 테스트 Pod의 `/tmp/run_sustained.py`를 호출하며, 같은 경로에 `benchmark.py`가 필요합니다.
- `collect_neuron_history.py`는 클러스터 내부에서 Prometheus를 조회합니다. 수집 대상과 임시 scrape job은 [현재 실습 안내](../../../../labs/eks-trainium-workshop/README.md)를 확인합니다. IP·실행 이미지·기존 설정을 재확인한 뒤 사용해야 합니다.
- `python3 summarize_neuron.py`로 보존된 원본의 집계를 다시 생성할 수 있습니다. 새 AWS 요청은 보내지 않습니다.

NeuronCore 약 79%를 완전 포화로 해석하지 않습니다. 디바이스 메모리 수치는 런타임 할당량이며 HBM 대역폭 사용률이 아닙니다. 임시 수집기·scrape job·테스트 Pod는 정리했고, 정리 후 API 및 기존 Prometheus 11개 대상 정상 상태를 결과에 보존했습니다.
