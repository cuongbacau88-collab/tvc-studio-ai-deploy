from __future__ import annotations

import asyncio
import json


def request(app, method: str, path: str, body: object | bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[int, object]:
    async def call() -> tuple[int, object]:
        sent: list[dict] = []
        raw = body if isinstance(body, bytes) else (b"" if body is None else json.dumps(body).encode())
        received = False
        values = {"authorization": "Bearer test-token", "x-owner-id": "owner-1"} if headers is None else headers
        asgi_headers = [(key.lower().encode(), value.encode()) for key, value in values.items()]

        async def receive() -> dict:
            nonlocal received
            if received:
                await asyncio.sleep(0)
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": raw, "more_body": False}

        async def send(message: dict) -> None:
            sent.append(message)

        await app({"type": "http", "method": method, "path": path, "headers": asgi_headers}, receive, send)
        status = next(message["status"] for message in sent if message["type"] == "http.response.start")
        response_body = b"".join(message.get("body", b"") for message in sent
                                 if message["type"] == "http.response.body")
        response_headers = dict(next(message["headers"] for message in sent
                                     if message["type"] == "http.response.start"))
        if response_headers.get(b"content-type") == b"application/json":
            return status, json.loads(response_body)
        return status, response_body

    return asyncio.run(call())
