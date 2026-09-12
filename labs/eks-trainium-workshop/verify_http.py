"""Lab 3 HTTP 기능 확인. 성능 벤치마크가 아니며 실행 위치를 함께 기록한다."""
import argparse
import datetime
import json
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args()
    base = args.endpoint.rstrip("/")
    result = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "origin": args.origin,
        "endpoint": base,
        "purpose": "functional verification, not a performance benchmark",
        "checks": {},
    }

    def request(path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            base + path, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "week6-lab3-verification"},
        )
        return urllib.request.urlopen(req, timeout=30)

    for path in ("/health", "/v1/models", "/openapi.json"):
        with request(path) as response:
            raw = response.read()
            entry = {"status": response.status}
            if path == "/v1/models":
                models = json.loads(raw)["data"]
                entry["model_ids"] = [model["id"] for model in models]
            elif path == "/openapi.json":
                entry["has_chat_completions"] = "/v1/chat/completions" in json.loads(raw)["paths"]
                assert entry["has_chat_completions"]
            result["checks"][path] = entry

    model_id = result["checks"]["/v1/models"]["model_ids"][0]
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Say hello in one short sentence."}],
        "max_tokens": 32,
        "temperature": 0,
    }
    with request("/v1/chat/completions", payload) as response:
        body = json.load(response)
        assert body["choices"][0]["message"]["content"]
        result["checks"]["chat"] = {"status": response.status, "request": payload, "response": body}

    payload = dict(payload, stream=True)
    with request("/v1/chat/completions", payload) as response:
        chunks = []
        done = False
        for line in response:
            line = line.decode().strip()
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                done = True
                break
            chunks.append(json.loads(data))
        text = "".join(
            choice.get("delta", {}).get("content") or ""
            for chunk in chunks for choice in chunk.get("choices", [])
        )
        assert done and text
        result["checks"]["stream"] = {
            "status": response.status, "done": done, "chunk_count": len(chunks), "text": text,
        }
    result["passed"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
