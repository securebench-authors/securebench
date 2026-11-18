"""A stub Anthropic Messages API that plays a model solving F1 with one tool call.

It runs inside a test container, never on the host. The first request gets a
`Bash` tool call that writes the answer; a request that carries a tool result
gets a short final text. Every request is printed, so tests can see what the
harness sent through the relay.
"""

import http.server
import json
import sys
from typing import Any, cast

COMMAND = "printf '{\"sum\": 1294}' > /srv/answer.json"


def events(blocks: list[dict[str, object]], stop: str) -> bytes:
    out: list[tuple[str, Any]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_stub",
                    "type": "message",
                    "role": "assistant",
                    "model": "stub",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            },
        )
    ]
    for index, block in enumerate(blocks):
        start: dict[str, Any]
        delta: dict[str, Any]
        if block["type"] == "tool_use":
            start = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
            delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
        else:
            start = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": block["text"]}
        out.append(
            (
                "content_block_start",
                {"type": "content_block_start", "index": index, "content_block": start},
            )
        )
        out.append(
            ("content_block_delta", {"type": "content_block_delta", "index": index, "delta": delta})
        )
        out.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
    out.append(
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop, "stop_sequence": None},
                "usage": {"output_tokens": 5},
            },
        )
    )
    out.append(("message_stop", {"type": "message_stop"}))
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in out).encode()


def _is_tool_result(part: Any) -> bool:
    return isinstance(part, dict) and cast(dict[str, Any], part).get("type") == "tool_result"


class Provider(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body: Any = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        key_ok = "stub-secret" in (
            self.headers.get("x-api-key"),
            self.headers.get("authorization", "").removeprefix("Bearer "),
        )
        messages: list[Any] = body.get("messages", [])
        parts: list[Any] = [
            part
            for message in messages
            if isinstance(message.get("content"), list)
            for part in message["content"]
        ]
        answered = any(_is_tool_result(part) for part in parts)
        tools = [tool.get("name") for tool in body.get("tools", [])]
        print(
            json.dumps(
                {
                    "path": self.path,
                    "key_ok": key_ok,
                    "stream": body.get("stream"),
                    "answered": answered,
                    "tools": tools,
                }
            ),
            flush=True,
        )
        if not key_ok:
            self.send_response(401)
            self.end_headers()
            return
        if answered or "Bash" not in tools:
            blocks: list[dict[str, object]] = [{"type": "text", "text": "Done."}]
            stop = "end_turn"
        else:
            blocks = [
                {
                    "type": "tool_use",
                    "id": "toolu_stub",
                    "name": "Bash",
                    "input": {"command": COMMAND, "description": "Write the answer"},
                }
            ]
            stop = "tool_use"
        if body.get("stream"):
            payload = events(blocks, stop)
            content_type = "text/event-stream"
        else:
            payload = json.dumps(
                {
                    "id": "msg_stub",
                    "type": "message",
                    "role": "assistant",
                    "model": "stub",
                    "content": blocks,
                    "stop_reason": stop,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 5},
                }
            ).encode()
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


server = http.server.ThreadingHTTPServer(("", 8000), Provider)
print("serving", flush=True)
sys.stdout.flush()
server.serve_forever()
