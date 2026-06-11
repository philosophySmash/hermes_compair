import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    body: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self):
        return json.loads(self.text)


def request(app, method: str, target: str, json_body=None) -> AsgiResponse:
    """Small stdlib-only ASGI request helper for local read-only API tests."""

    parsed = urlsplit(target)
    body = b"" if json_body is None else json.dumps(json_body).encode("utf-8")
    request_headers = []
    if json_body is not None:
        request_headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("ascii"),
        "query_string": parsed.query.encode("ascii"),
        "headers": request_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    messages = []
    sent_body = False

    async def receive():
        nonlocal sent_body
        if sent_body:
            return {"type": "http.disconnect"}
        sent_body = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    body_parts = [message.get("body", b"") for message in messages if message["type"] == "http.response.body"]
    headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in start["headers"]}
    return AsgiResponse(start["status"], b"".join(body_parts), headers)
