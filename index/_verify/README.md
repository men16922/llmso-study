# PageIndex 실측 산출물

[`../README.md` §2](../README.md)의 검증 근거 자료입니다. 대상은 **NHN 백서 66p** 하나이며, LLM 백엔드는 [`tools/pageindex_claude.py`](../../tools/pageindex_claude.py)를 통한 **Claude Code(`claude -p`)** 입니다.

| 파일 | 내용 |
|---|---|
| `nhn_pageindex-claude_verify.json` | 1차 실행 (`--no-summary`) — 121회 호출 / 278초 |
| `run.log` | 1차 실행 로그 |
| `nhn_pageindex-claude_with-summary.json` | 2차 실행 (요약 O) — 176회 호출 / 508초 |
| `run_with-summary.log` | 2차 실행 로그 |

## 이 파일들로 확인할 수 있는 것

- **요약 품질**: 2차 파일의 `summary` 필드는 평균 1,934자로 증상·원인·진단까지 서술 (로컬 발췌본은 265자)
- **재현성 문제**: 1차와 2차의 `title`을 비교하면 98개 중 12개만 일치. 같은 PDF인데 절 번호 유지 여부가 갈림
- **언어 문제**: 2차 요약 55개 중 54개가 영어 (원문은 한국어)

```bash
# 두 실행의 제목 차이 재확인
python3 - <<'PY'
import json
def t(p):
    out=[]
    def w(ns):
        for n in ns: out.append(n["title"].strip()); w(n.get("nodes",[]))
    w(json.load(open(p,encoding="utf-8"))["structure"]); return set(out)
a=t("index/_verify/nhn_pageindex-claude_verify.json")
b=t("index/_verify/nhn_pageindex-claude_with-summary.json")
print(f"일치 {len(a&b)} / 합집합 {len(a|b)}")
PY
```

> 이 폴더는 **재현 근거 보관용**이며 `tools/search_index.py`의 탐색 대상이 아닙니다.
