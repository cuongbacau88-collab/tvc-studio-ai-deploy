"""Validated access to the existing Phase 2 model registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import APIError


REQUIRED_MODEL_FIELDS = {
    "enabled", "name", "repo_url", "install_dir", "venv_dir", "weights_dir",
    "task_type", "min_vram_gb",
}


@dataclass(frozen=True)
class ModelSpec:
    id: str
    data: dict[str, Any]

    def path(self, root: Path, field: str) -> Path:
        return (root / str(self.data[field])).resolve()

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.data["name"],
            "enabled": bool(self.data["enabled"]),
            "task_type": self.data["task_type"],
            "min_vram_gb": self.data["min_vram_gb"],
        }


class ModelRegistry:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.models: dict[str, ModelSpec] = {}
        self.error_codes: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        try:
            raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise APIError("registry_invalid", f"Cannot load model registry: {exc}", 503) from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("models"), dict):
            raise APIError("registry_invalid", "Registry must contain a models mapping", 503)
        parsed: dict[str, ModelSpec] = {}
        for model_id, data in raw["models"].items():
            if not isinstance(data, dict):
                raise APIError("registry_invalid", f"Model {model_id} must be a mapping", 503)
            missing = REQUIRED_MODEL_FIELDS - data.keys()
            if missing:
                raise APIError("registry_invalid", f"Model {model_id} missing: {', '.join(sorted(missing))}", 503)
            parsed[model_id] = ModelSpec(model_id, data)
        self.models = parsed
        self.error_codes = dict(raw.get("error_codes") or {})

    def get(self, model_id: str) -> ModelSpec:
        try:
            return self.models[model_id]
        except KeyError as exc:
            raise APIError("model_not_found", f"Unknown model: {model_id}", 404) from exc

    def list(self) -> list[ModelSpec]:
        return list(self.models.values())

