# 2주차 과제 LinkedIn 포스트

## 게시 전략

- 첫 게시물에서는 Continuous Batching 실험의 **23배 처리량 차이**를 전면에 내세운다.
- WSL2 환경 구축은 실험을 가능하게 한 기반으로 짧게 소개하고, 자세한 내용은 후속 게시물로 분리한다.
- 단순한 성능 자랑보다 처리량·TTFT·goodput을 함께 측정한 이유와 실험의 한계를 밝힌다.
- 첫 게시물 게시 후 3~5일 뒤에 WSL2 환경 구축기를 후속으로 올린다.
- 대표 그래프를 PDF 문서 포스트로 만들 경우 첫 장에는 `GPU 추가 없이 LLM 처리량 23배`를 넣는다.

---

## 1편. Continuous Batching 실험

GPU를 추가하지 않았는데 LLM 처리량이 113 tok/s에서 2,627 tok/s로 늘었습니다.

바꾼 것은 vLLM의 `max-num-seqs` 값 하나였습니다.

2주차 과제로 Windows 노트북의 RTX 4080 Laptop GPU에 로컬 Kubernetes 환경을 구성하고, 그 위에서 Continuous Batching이 LLM 서빙 성능에 미치는 영향을 측정했습니다.

배치 슬롯을 1, 16, 64로 바꾸며 동시 요청을 보낸 결과는 다음과 같았습니다.

- `slots=1`: 동시 요청을 늘려도 처리량은 약 113 tok/s
- `slots=16`: 동시성 16까지 처리량 증가
- `slots=64`: 동시성 64에서 약 2,627 tok/s

하지만 처리량만 보면 중요한 문제를 놓치게 됩니다.

`max-num-seqs=16`에서 동시성을 16에서 64로 높였을 때 처리량은 0.3% 증가하는 데 그쳤지만, TTFT는 139배 증가하고 goodput은 100%에서 8%로 감소했습니다.

같은 시점의 Prometheus 지표는 다음과 같았습니다.

```text
running = 16
waiting = 48
```

처리 한도를 넘은 요청은 실패하지 않고 큐에서 기다렸습니다. 성공률만 확인하면 정상으로 보이지만, 사용자는 첫 토큰을 오래 기다리게 됩니다.

이번 실험에서 확인한 핵심은 두 가지입니다.

1. GPU 사용률 100%가 처리량의 한도를 의미하지는 않는다.
2. `max-num-seqs`는 무조건 높이는 성능 옵션이 아니라 GPU 메모리와 SLO를 함께 고려해 정해야 하는 동시 처리 용량이다.

각 조건을 한 번씩 측정했기 때문에 작은 차이는 노이즈일 수 있습니다. 그래서 이번 글에서는 배 단위로 차이가 나타난 결과만 해석에 사용했습니다.

실험 환경, 원본 데이터, Prometheus 캡처와 재현 절차를 문서에 정리했습니다.

- [Continuous Batching이 처리량을 높이는 방식](https://github.com/men16922/llmso-study/blob/main/articles/Continuous%20Batching이%20처리량을%20높이는%20방식.md)
- [WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기](https://github.com/men16922/llmso-study/blob/main/articles/WSL2를%20로컬%20GPU%20Kubernetes%20개발%20환경으로%20사용하기.md)

#LLM #vLLM #LLMServing #MLOps #Kubernetes

---

## 2편. WSL2 로컬 GPU Kubernetes 환경 구축

앞선 vLLM Continuous Batching 실험은 클라우드가 아니라 Windows 노트북 한 대에서 진행했습니다.

Windows의 NVIDIA GPU를 다음 경로로 연결했습니다.

```text
Windows GPU
  → WSL2
  → Docker
  → K3s 파드
  → Prometheus / Grafana
```

설치 여부만 확인하지 않고 다음 항목까지 직접 검증했습니다.

- WSL2에서 CUDA가 GPU를 인식하는지
- Docker 컨테이너에서 GPU 연산이 가능한지
- K3s가 `nvidia.com/gpu`를 자원으로 등록하는지
- 파드에 실제 GPU UUID가 전달되는지
- 부하 전후 GPU 사용률·전력·온도가 어떻게 달라지는지
- DCGM Exporter의 메트릭이 Prometheus와 Grafana에 표시되는지

이 과정에서 WSL2에서는 `DCGM_FI_PROF_*` 계열 프로파일링 메트릭이 노출되지 않는다는 제약도 확인했습니다. GPU Utilization은 정상적으로 수집됐지만 Tensor Core Utilization 패널에는 데이터가 없었습니다.

이 제약 때문에 다음 Continuous Batching 실험에서는 GPU 사용률만 보지 않고 vLLM의 `num_requests_running`, `num_requests_waiting`과 클라이언트 측 TTFT·ITL·goodput을 함께 측정했습니다.

환경 구축 자체보다 더 중요했던 점은 어디까지 측정할 수 있고, 어떤 지표는 사용할 수 없는지를 확인한 것입니다.

설치 명령, 실행 결과, 트러블슈팅과 측정값을 문서에 정리했습니다.

- [WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기](https://github.com/men16922/llmso-study/blob/main/articles/WSL2를%20로컬%20GPU%20Kubernetes%20개발%20환경으로%20사용하기.md)
- [Continuous Batching이 처리량을 높이는 방식](https://github.com/men16922/llmso-study/blob/main/articles/Continuous%20Batching이%20처리량을%20높이는%20방식.md)

#WSL2 #Kubernetes #GPU #MLOps #Observability

---

## PDF 문서 포스트 구성안

1. GPU 추가 없이 LLM 처리량 23배
2. 실험 환경과 변경 변수
3. `max-num-seqs`별 처리량 그래프
4. 처리 한도 이후 TTFT와 goodput 변화
5. Prometheus의 `running=16`, `waiting=48`
6. 운영에서 함께 확인할 지표
7. 실험의 한계와 전체 문서 링크

PDF는 세로형 단일 열로 만들고, 각 페이지에는 그래프 하나와 핵심 문장 하나만 배치한다.
