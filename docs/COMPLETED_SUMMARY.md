# Completed Summary

완료된 마일스톤의 목적·산출물·검증만 압축해 둡니다. 상세 이력은 `docs/PROGRESS_LOG.md`와 `docs/archive/`에.

| ID | 마일스톤 | 결과 |
| --- | --- | --- |
| M0 | **환경 구축** (~2026-08-09) | WSL2 + k3s + GPU Operator + kube-prometheus-stack/DCGM. 산출물 `articles/WSL2를 로컬 GPU Kubernetes 개발 환경으로 사용하기`. 검증: 파드 기동 + DCGM 메트릭 노출 확인 |
| M1 | **1주차 과제 제출** (마감 08-09 통과) | Cloud Run에서 Gemma 4 서빙. 산출물 `articles/Run inference of Gemma 4 model on Cloud Run.md`. 노션 발행 + 링크 공유 완료 |
| M2 | **2주차 과제 제출** (마감 08-16 통과) | **Continuous batching 실측** — `max_num_seqs` 1→64로 처리량 23배. 산출물 글 2편(환경 구축 + 측정) 시리즈, 그림 3종, Prometheus 캡처 3장. 검증: B1·B2 결과 8종 + 지연 공식 `E2E = TTFT + ITL×(N-1)` 잔차 대조 |
| M3 | **3주차 과제 제출** (마감 08-23 통과) | **서빙 계층 3종 가격표** — KServe −2.2% / Triton −12.6% / Ray Serve −70.0%, goodput 100·100·19%, `vllm:*` 66·0·0개. 결론: 계층 가격을 가르는 건 구현 품질이 아니라 **요청 경로에 서 있는가**. 산출물 `articles/서빙 최적화, 설정부터 만지면 안 되는 이유.md`(612줄) + 그림 7종 + 캡처 9장. 검증: **계층마다 같은 이미지에서 계층만 뺀 짝**을 만들어 엔진 버전 혼입 제거(짝 확인은 기동 로그의 KV 예산) |
| M4 | **실습 도구 일체** (2026-08-09~) | `benchmark.py`(ITL/TPOT·goodput·교재 서버 어댑터) · `summarize_results.py`(표·파레토·`--delta`·`--formula`) · `make_figures.py` · `md_to_notion.py` · `search_index.py` 외 인덱싱 3종. 검증: 오프라인 단위 테스트 **91건** green, 외부 의존성 0 |
