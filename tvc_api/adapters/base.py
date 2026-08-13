"""Safe adapter contract for isolated upstream model environments."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..registry import ModelSpec


@dataclass(frozen=True)
class Readiness:
    ready: bool
    checks: dict[str, bool]
    reason: str | None = None


class ModelAdapter(ABC):
    def __init__(self, spec: ModelSpec, repo_root: Path) -> None:
        self.spec = spec
        self.repo_root = repo_root

    def readiness(self) -> Readiness:
        repo = self.spec.path(self.repo_root, "install_dir")
        venv_python = self.spec.path(self.repo_root, "venv_dir") / "bin" / "python"
        weights = self.spec.path(self.repo_root, "weights_dir")
        checks = {
            "enabled": bool(self.spec.data["enabled"]),
            "repository": repo.is_dir(),
            "venv_python": venv_python.is_file(),
            "weights": weights.is_dir() and any(item.is_file() for item in weights.rglob("*")),
            "entrypoint": self.entrypoint_ready(),
        }
        ready = all(checks.values())
        return Readiness(ready, checks, None if ready else "One or more readiness checks failed")

    @abstractmethod
    def entrypoint_ready(self) -> bool:
        """Return true only when the upstream invocation entrypoint is verified."""

    @abstractmethod
    async def run(self, inputs: dict[str, Any], parameters: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        """Execute one inference job. Called only by the shared GPU worker."""

