"""Environment-backed API configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    repo_root: Path = REPO_ROOT
    models_config: Path = REPO_ROOT / "configs" / "models.yaml"
    output_dir: Path = REPO_ROOT / "outputs"
    upload_dir: Path = REPO_ROOT / "uploads"
    gpu_index: int = 0
    gpu_task_timeout_seconds: int = 180
    max_queue_size: int = 100
    sequential_gpu_queue: bool = True
    service_token: str = ""
    max_upload_mb: int = 300

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "Settings":
        root = (repo_root or REPO_ROOT).resolve()
        gpu_value = os.getenv("GPU_INDEX", "").strip()
        return cls(
            repo_root=root,
            models_config=root / "configs" / "models.yaml",
            output_dir=(root / os.getenv("GPU_OUTPUT_DIR", os.getenv("OUTPUT_DIR", "outputs"))).resolve(),
            upload_dir=(root / os.getenv("GPU_UPLOAD_DIR", os.getenv("UPLOAD_DIR", "uploads"))).resolve(),
            gpu_index=int(gpu_value or "0"),
            gpu_task_timeout_seconds=int(os.getenv("GPU_TASK_TIMEOUT_SECONDS", "180")),
            max_queue_size=int(os.getenv("GPU_QUEUE_MAX_SIZE", "100")),
            sequential_gpu_queue=_bool("SEQUENTIAL_GPU_QUEUE", True),
            service_token=os.getenv("GPU_API_SERVICE_TOKEN", "").strip(),
            max_upload_mb=int(os.getenv("GPU_MAX_UPLOAD_MB", "300")),
        )

