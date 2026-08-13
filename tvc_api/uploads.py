"""In-memory upload metadata with files stored under a configured safe root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .errors import APIError


ALLOWED_TYPES = {
    ".png": {"image/png"}, ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"}, ".mp4": {"video/mp4"}, ".mov": {"video/quicktime"},
    ".webm": {"video/webm"}, ".mp3": {"audio/mpeg"}, ".wav": {"audio/wav", "audio/x-wav"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
}


@dataclass(frozen=True)
class Upload:
    id: str
    owner_id: str
    path: Path
    original_name: str
    content_type: str
    size: int

    def public(self) -> dict[str, object]:
        return {"id": self.id, "owner_id": self.owner_id, "filename": self.original_name,
                "content_type": self.content_type, "size": self.size}


class UploadStore:
    def __init__(self, root: Path, max_upload_mb: int) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_upload_mb * 1024 * 1024
        self._uploads: dict[str, Upload] = {}

    def validate(self, filename: str, content_type: str) -> str:
        if (not filename or Path(filename).name != filename or chr(92) in filename
                or filename in {".", ".."} or any(ord(char) < 32 for char in filename)):
            raise APIError("invalid_filename", "Upload filename is invalid", 422)
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_TYPES or content_type.lower() not in ALLOWED_TYPES[extension]:
            raise APIError("unsupported_upload", "Upload type is not allowed", 415)
        return extension

    def target(self, extension: str) -> tuple[str, Path]:
        upload_id = uuid4().hex
        path = (self.root / f"{upload_id}{extension}").resolve()
        if self.root not in path.parents:
            raise APIError("invalid_upload_path", "Upload path is invalid", 422)
        return upload_id, path

    def add(self, upload_id: str, owner_id: str, path: Path, original_name: str,
            content_type: str, size: int) -> Upload:
        upload = Upload(upload_id, owner_id, path, original_name, content_type, size)
        self._uploads[upload_id] = upload
        return upload

    def get_owned(self, upload_id: str, owner_id: str) -> Upload:
        upload = self._uploads.get(upload_id)
        if upload is None or upload.owner_id != owner_id:
            raise APIError("upload_not_found", "Upload not found", 404)
        return upload
