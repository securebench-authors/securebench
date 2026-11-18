"""A stub OpenAI Responses API that plays a model solving F1 with one tool call.

It runs inside a test container, never on the host. The first request gets an
`exec_command` call that writes the answer; a request that carries the call's
output gets a short final message. Every request is printed.
"""

import http.server
import json
from typing import Any, cast

COMMAND = "printf '{\"sum\": 1294}' > /srv/answer.json"
USAGE = {
    "input_tokens": 1,
    "input_tokens_details": {"cached_tokens": 0},
    "output_tokens": 1,
    "output_tokens_details": {"reasoning_tokens": 0},
    "total_tokens": 2,
}


def stream(item: dict[str, Any]) -> bytes:
    response: dict[str, Any] = {"id": "resp_stub", "object": "response", "status": "in_progress"}
    done = {**response, "status": "completed", "output": [item], "usage": USAGE}
    events = [
        ("response.created", {"type": "response.created", "response": response}),
        ("response.output_item.done",
         {"type": "response.output_item.done", "output_index": 0, "item": item}),
        ("response.completed", {"type": "response.completed", "response": done}),
    ]  # fmt: skip
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events).encode()


def _type(item: Any) -> object:
    return cast(dict[str, Any], item).get("type") if isinstance(item, dict) else None


class Provider(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body: Any = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        key_ok = self.headers.get("authorization") == "Bearer stub-secret"
        items: list[Any] = body.get("input", [])
        answered = any(_type(item) == "function_call_output" for item in items)
        print(json.dumps({"path": self.path, "key_ok": key_ok, "answered": answered}), flush=True)
        if not key_ok:
            self.send_response(401)
            self.end_headers()
            return
        if answered:
            item: dict[str, Any] = {
                "type": "message",
                "id": "msg_stub",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": "Done.", "annotations": []}],
            }
        else:
            item = {
                "type": "function_call",
                "id": "fc_stub",
                "call_id": "call_stub",
                "name": "exec_command",
                "arguments": json.dumps({"cmd": COMMAND, "login": False}),
                "status": "completed",
            }
        payload = stream(item)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


server = http.server.ThreadingHTTPServer(("", 8000), Provider)
print("serving", flush=True)
server.serve_forever()
