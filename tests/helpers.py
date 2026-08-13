from __future__ import annotations

import asyncio
import json


def request(app, method: str, path: str, body: object | None = None) -> tuple[int, dict]:
    async def call() -> tuple[int, dict]:
        sent: list[dict] = []
        raw = b"" if body is None else json.dumps(body).encode()
        received = False

        async def receive() -> dict:
            nonlocal received
            if received:
                await asyncio.sleep(0)
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": raw, "more_body": False}

        async def send(message: dict) -> None:
            sent.append(message)

        await app({"type": "http", "method": method, "path": path, "headers": []}, receive, send)
        status = next(message["status"] for message in sent if message["type"] == "http.response.start")
        response_body = next(message["body"] for message in sent if message["type"] == "http.response.body")
        return status, json.loads(response_body)

    return asyncio.run(call())

