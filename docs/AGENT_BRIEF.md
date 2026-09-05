# Agent Brief

Last Updated: 2026-09-05

> ▶ NEXT SESSION: [5주차 추가 검증 계획](./plans/2026-09-05-week5-followup-validation.md) §1에 따라 **확보된 F1b 반복 JSON·기동 로그와 F2 트레이스·집계 코드를 원고와 대조**합니다. 새 GPU 측정부터 시작하지 않습니다. 4·5주차 제출표 공유 여부는 사용자 확인이 필요합니다(5주차 마감 09-06 09:00).

## 현재 상태

- CloudNet@ LLMSO 한국어 학습 문서·WSL2 GPU 실습 저장소입니다. 1~3주차 제출 완료, 4·5주차 발행 완료·제출표 공유 미확인입니다.
- 5주차 최종 원고: `articles/처리량이 올랐다면 무엇이 빨라진 것인가.md`, 제목 「FP8 양자화로 처리량이 늘어난 이유」. [노션 발행본](https://app.notion.com/p/3d04c2420ac481c89ce1de666fbf9fbe).
- **요점:** FP8의 처리량 이득은 늘어난 KV Cache 공간을 줄여도 남았고, 같은 요청 수에서 ITL이 짧아졌습니다. 캐시 기여율 0%·전부 GEMM·메모리 대역폭 원인을 확정한 실험은 아닙니다.
- **최종 구성:** 질문·핵심 결론·세 구성 비교표 → 용어 접기 → 본문 6절. 표 15개·그림 5개·코드 11개·접기 14개. 6번은 「결론 — FP8의 효과는 메모리 절감에 그치지 않았다」입니다.
- 전문 용어는 짧게 설명하고, 소제목에는 요점을 담습니다. 핵심 비교표는 펼쳐 두고 실측 화면·세부 조건은 해당 결론 아래 접기에 둡니다. 교재·지난 글에 의존하지 않는 발행본으로 유지합니다.
- Humanize A(19.41%, Fast Path 자체검증 6/6)는 앞선 윤문 단계 결과입니다. 이후 구조·결론 편집본을 같은 등급으로 재채점한 것은 아닙니다.
- **09-05 원격 동기화:** `d37fbae`까지 18개 커밋을 반영해 `results/f*`·F2 트레이스 2개·`summarize_trace.py`를 확보했습니다. 이전의 원본 미확보 상태는 해소됐으며 산술·집계 대조는 남았습니다.
- `study/` 추적 해제는 원격 `cc9da27`에서 완료됐습니다. 이 macOS의 원문 11개는 로컬 보존했고 Git·인덱스에서 제외합니다.
- 원격의 오프라인 게이트는 labs 120건입니다. 현재 머신은 `/tmp/w5-review-venv/bin/python`을 사용하며, 실제 실행 결과는 [STATUS](./STATUS.md)에 기록합니다. GPU 실측과는 별개입니다.

## 다음 작업

Authority: [NEXT_PLAN](./NEXT_PLAN.md). 원본 집계 대조·제출 확인이 우선이며 추가 GPU 실험·품질 평가는 미실행입니다.
AWS GPU 쿼터는 08-23 조회 당시 0이었습니다. 현재 상태를 다시 확인해야 합니다. 통합 메모리 vs VRAM 비교는 [별도 계획](./plans/2026-09-01-unified-memory-vs-vram.md)의 트리거 충족 전까지 보류합니다.

## 읽는 순서와 명령

[STATUS](./STATUS.md) → [NEXT_PLAN](./NEXT_PLAN.md) → [최근 기록](./PROGRESS_LOG.md). 완료 결과는 [COMPLETED_SUMMARY](./COMPLETED_SUMMARY.md), 설계 이유는 [DECISIONS](./DECISIONS.md), 저장소 규칙은 `CLAUDE.md`를 봅니다.

- 게이트: `make check PY=/tmp/w5-review-venv/bin/python` (임시 venv가 없으면 재생성)
- 문서 수정 후: `python3 tools/build_pageindex.py --only md`
- 빠른 문서 검사: `python3 scripts/check_docs.py`
- 검색: `python3 tools/search_index.py "KV cache"`

## 실행 경계

- 비공개 저장소입니다. 사용자 승인 범위 밖의 외부 게시·푸시·유료 GPU 호출을 수행하지 않습니다. `study/` 원문은 커밋하지 않습니다.
- PDF 인덱스는 재생성하지 않습니다. `--only md`를 지키고 LLM 보강 요약을 보존합니다.
- 측정은 k3s containerd의 기존 이미지와 `EXTRA_ARGS` 경로를 유지합니다. `docker run vllm/...`은 별도 대용량 다운로드와 비교 조건 변경을 일으킵니다.
- 기동 로그의 KV 예산은 매번 확인합니다. `Maximum concurrency`는 실제 동시 실행 요청 수가 아닙니다.
- keeper·긴 측정은 독립 Windows 프로세스로 유지합니다. `.wslconfig`의 `vmIdleTimeout=-1`과 `nohup`으로 해결됐다고 가정하지 않습니다.
- 실증 이미지는 실제 대시보드 캡처입니다. 로그를 HTML로 꾸민 이미지를 관측 화면으로 쓰지 않습니다. 오래된 `assemble.py` 재실행은 원고 편집을 덮어씁니다.
- 상세 환경 함정과 이전 상태는 [원격 상태 보관본](./archive/context-2026-09-05-remote/STATUS.md)에 보존했습니다.
