# 기동 로그에서 Maximum concurrency 숫자만 꺼낸다
read_conc() {
  kubectl -n llm-serving-lab logs deploy/vllm-baseline \
    | grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' \
    | tail -1 | grep -oE '[0-9.]+x$' | tr -d 'x'
}
