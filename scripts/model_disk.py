#!/usr/bin/env python3
"""Physical model-file classification shared by preflight and downloader."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
MISSING = "MISSING"
CHECKSUM_FAILED = "CHECKSUM_FAILED"


def default_comfyui_root(repo_root: Path) -> Path:
    configured = os.getenv("COMFYUI_ROOT", "").strip() or os.getenv("COMFYUI_DIR", "").strip()
    return Path(configured) if configured else repo_root / "runtime" / "ComfyUI"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_path(model: dict[str, Any], comfyui_root: Path) -> Path:
    return comfyui_root / model["comfyui_subdir"] / model["filename"]


def classify(model: dict[str, Any], comfyui_root: Path) -> dict[str, Any]:
    path = model_path(model, comfyui_root)
    partial = path.with_name(path.name + ".part")
    expected = model.get("sha256")
    if path.is_file():
        actual = sha256(path)
        state = COMPLETE if path.stat().st_size > 0 and actual == expected else CHECKSUM_FAILED
    elif partial.is_file():
        actual = None
        state = PARTIAL
    else:
        actual = None
        state = MISSING
    return {
        "filename": model.get("filename"),
        "required": bool(model.get("required")),
        "optional": bool(model.get("optional")),
        "path": str(path),
        "part_path": str(partial),
        "status": state,
        "size": path.stat().st_size if path.is_file() else 0,
        "partial_bytes": partial.stat().st_size if partial.is_file() else 0,
        "expected_sha256": expected,
        "actual_sha256": actual,
    }


def disk_summary(models: list[dict[str, Any]], comfyui_root: Path,
                 manifest_errors: list[str] | None = None) -> dict[str, Any]:
    records = [classify(model, comfyui_root) for model in models]
    required = [record for record in records if record["required"]]
    optional = [record for record in records if record["optional"]]
    counts = lambda items, state: sum(record["status"] == state for record in items)
    errors = list(manifest_errors or [])
    unresolved = [
        model.get("filename") for model in models
        if model.get("required") and (
            model.get("source_status") != "resolved" or not model.get("source_url")
        )
    ]
    return {
        "comfyui_root": str(comfyui_root),
        "manifest_valid": not errors,
        "source_ready": not errors and not unresolved,
        "required_total": len(required),
        "required_complete": counts(required, COMPLETE),
        "partial": counts(required, PARTIAL),
        "missing": counts(required, MISSING),
        "checksum_failed": counts(required, CHECKSUM_FAILED),
        "optional_total": len(optional),
        "optional_complete": counts(optional, COMPLETE),
        "unresolved_required": unresolved,
        "errors": errors,
        "ready": (
            not errors
            and not unresolved
            and len(required) > 0
            and all(record["status"] == COMPLETE for record in required)
        ),
        "models": records,
    }
