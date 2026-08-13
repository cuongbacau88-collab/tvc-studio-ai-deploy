"""Authenticated raw-body uploads for image, video, and audio inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from ..auth import headers
from ..context import AppContext
from ..errors import APIError


async def create(context: AppContext, owner_id: str, scope: dict[str, Any],
                 receive: Callable[..., Awaitable[dict[str, Any]]]) -> tuple[int, dict[str, object]]:
    values = headers(scope)
    filename = values.get("x-filename", "").strip()
    content_type = values.get("content-type", "").split(";", 1)[0].strip().lower()
    extension = context.uploads.validate(filename, content_type)
    upload_id, target = context.uploads.target(extension)
    temporary = Path(str(target) + ".part")
    size = 0
    try:
        with temporary.open("xb") as output:
            while True:
                message = await receive()
                if message.get("type") == "http.disconnect":
                    raise APIError("upload_interrupted", "Upload was interrupted", 400)
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > context.uploads.max_bytes:
                    raise APIError("upload_too_large", "Upload exceeds configured size limit", 413)
                output.write(chunk)
                if not message.get("more_body", False):
                    break
        if size == 0:
            raise APIError("empty_upload", "Upload is empty", 422)
        temporary.replace(target)
        upload = context.uploads.add(upload_id, owner_id, target, filename, content_type, size)
        return 201, {"upload": upload.public()}
    except APIError:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    except OSError:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise APIError("upload_failed", "Upload could not be stored", 500)
