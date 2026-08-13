"""Dependency-light authenticated ASGI API for the shared GPU queue."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any, Awaitable, Callable

from .auth import authenticate
from .config import Settings
from .context import AppContext
from .errors import APIError
from .gpu import GPUStatus, probe_gpu
from .routes import health, jobs, models, queue, uploads


class APIApplication:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[dict[str, Any]]],
                       send: Callable[..., Awaitable[None]]) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope["type"] != "http":
            return
        try:
            response = await self._dispatch(scope, receive)
            if len(response) == 3:
                status, path, filename = response
                await self._respond_file(send, status, path, filename)
                return
            status, payload = response
        except APIError as exc:
            status, payload = exc.status, exc.as_dict()
        except json.JSONDecodeError:
            status, payload = 400, APIError("invalid_json", "Request body is not valid JSON", 400).as_dict()
        except Exception:
            status, payload = 500, APIError("internal_error", "Request could not be completed", 500).as_dict()
        await self._respond_json(send, status, payload)

    async def _dispatch(self, scope: dict[str, Any],
                        receive: Callable[..., Awaitable[dict[str, Any]]]) -> tuple:
        method = scope["method"].upper()
        path = scope.get("path", "/").rstrip("/") or "/"
        if method == "GET" and path == "/health/live":
            return health.live(self.context)
        if method == "GET" and path == "/health/ready":
            return health.ready(self.context)
        if method == "GET" and path == "/health/models/minimax_h3":
            return models.health_model(self.context, "minimax_h3")
        owner_id = authenticate(scope, self.context.settings.service_token)
        if method == "GET" and path in {"/api/models", "/v1/models"}:
            return models.list_models(self.context)
        if method == "POST" and path == "/v1/uploads":
            return await uploads.create(self.context, owner_id, scope, receive)
        if method == "GET" and path == "/v1/queue":
            return queue.get_queue(self.context, owner_id)
        if method == "GET" and path == "/v1/jobs":
            return jobs.list_jobs(self.context, owner_id)
        if method == "POST" and path == "/v1/jobs":
            return await jobs.submit(self.context, await self._json_body(receive), owner_id)
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["v1", "models"] and method == "GET":
            return models.get_model(self.context, parts[2])
        if len(parts) == 3 and parts[:2] == ["v1", "jobs"]:
            if method == "GET":
                return jobs.get_job(self.context, parts[2], owner_id)
            if method == "DELETE":
                return jobs.cancel_job(self.context, parts[2], owner_id)
        if len(parts) == 4 and parts[:2] == ["v1", "jobs"] and method == "GET":
            if parts[3] == "result":
                return jobs.get_job(self.context, parts[2], owner_id, result=True)
            if parts[3] == "output":
                output, filename = jobs.output_file(self.context, parts[2], owner_id)
                return 200, output, filename
        raise APIError("not_found", "Endpoint not found", 404)

    async def _json_body(self, receive: Callable[..., Awaitable[dict[str, Any]]]) -> object:
        chunks = bytearray()
        while True:
            message = await receive()
            chunks.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return json.loads(bytes(chunks) or b"{}")

    async def _respond_json(self, send: Callable[..., Awaitable[None]], status: int,
                            payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})

    async def _respond_file(self, send: Callable[..., Awaitable[None]], status: int,
                            path: Path, filename: str) -> None:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        size = path.stat().st_size
        safe_name = filename.replace('"', "")
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", content_type.encode()),
                                (b"content-length", str(size).encode()),
                                (b"content-disposition", f'attachment; filename="{safe_name}"'.encode())]})
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _lifespan(self, receive: Callable[..., Awaitable[dict[str, Any]]],
                        send: Callable[..., Awaitable[None]]) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                self.context.worker.start()
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await self.context.worker.stop()
                await send({"type": "lifespan.shutdown.complete"})
                return


def create_app(settings: Settings | None = None,
               gpu_probe_fn: Callable[[int], GPUStatus] = probe_gpu) -> APIApplication:
    return APIApplication(AppContext.build(settings or Settings.from_env(), gpu_probe_fn))


app = create_app()
