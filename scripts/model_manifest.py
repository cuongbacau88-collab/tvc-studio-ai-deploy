"""Validation shared by model preflight and downloader."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
from urllib.parse import urlparse


VALID_LOCATIONS = {
    "upscale_model": "models/upscale_models",
    "diffusion_model": "models/diffusion_models",
    "text_encoder": "models/text_encoders",
    "vae": "models/vae",
    "lora": "models/loras",
    "vision_encoder": "models/clip_vision",
    "checkpoint": "models/checkpoints",
}
MODEL_FIELDS = {
    "ckpt_name", "unet_name", "vae_name", "clip_name", "lora_name", "model_name"
}
PLACEHOLDERS = ("example.com", "placeholder", "todo", "replace-me", "<", ">", "...")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def workflow_model_filenames(root: Path) -> set[str]:
    filenames: set[str] = set()
    for path in sorted((root / "workflows").glob("*_api.json")):
        workflow = load_json(path)
        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs", {})
            for field in MODEL_FIELDS:
                value = inputs.get(field)
                if isinstance(value, str) and value:
                    filenames.add(value)
    return filenames


def validate(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = root / "configs" / "model_manifest.json"
    try:
        manifest = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"invalid manifest: {exc}"]
    errors: list[str] = []
    models = manifest.get("models")
    if not isinstance(models, list):
        return manifest, ["models must be a list"]
    seen: dict[str, tuple[Any, Any]] = {}
    for index, item in enumerate(models):
        label = f"models[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        filename = item.get("filename")
        model_type = item.get("model_type")
        subdir = item.get("comfyui_subdir")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename:
            errors.append(f"{label}.filename is invalid")
        if model_type not in VALID_LOCATIONS:
            errors.append(f"{label}.model_type is invalid: {model_type}")
        if subdir != VALID_LOCATIONS.get(model_type):
            errors.append(f"{label}.comfyui_subdir does not match {model_type}")
        if not isinstance(subdir, str) or PurePosixPath(subdir).is_absolute() or ".." in PurePosixPath(subdir).parts:
            errors.append(f"{label}.comfyui_subdir is unsafe")
        required, optional = item.get("required"), item.get("optional")
        if not isinstance(required, bool) or not isinstance(optional, bool) or required == optional:
            errors.append(f"{label} must set exactly one of required/optional")
        required_by = item.get("required_by")
        if not isinstance(required_by, dict) or not all(
            isinstance(required_by.get(key), list) and required_by[key]
            for key in ("workflows", "services")
        ):
            errors.append(f"{label}.required_by must contain non-empty workflow/service lists")
        source_url = item.get("source_url")
        source_repo = item.get("source_repo")
        resolved = item.get("source_status") == "resolved"
        if required and (not resolved or not source_url):
            errors.append(f"{filename}: required source is unresolved")
        if resolved:
            if not isinstance(source_url, str) or any(token in source_url.lower() for token in PLACEHOLDERS):
                errors.append(f"{filename}: source_url is missing or contains a placeholder")
            else:
                parsed = urlparse(source_url)
                if parsed.scheme != "https" or parsed.netloc != "huggingface.co" or "/resolve/" not in parsed.path:
                    errors.append(f"{filename}: source_url is not a Hugging Face resolve URL")
            if not isinstance(source_repo, str) or not re.fullmatch(r"[^/\s]+/[^/\s]+", source_repo):
                errors.append(f"{filename}: source_repo is invalid")
        checksum = item.get("sha256")
        if checksum is not None and (
            not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum)
        ):
            errors.append(f"{filename}: sha256 is invalid")
        if isinstance(filename, str):
            signature = (model_type, subdir)
            if filename in seen and seen[filename] != signature:
                errors.append(f"{filename}: duplicate filename has conflicting type/subdir")
            elif filename in seen:
                errors.append(f"{filename}: duplicate filename")
            seen[filename] = signature
    try:
        workflow_files = workflow_model_filenames(root)
        manifest_files = {item.get("filename") for item in models if isinstance(item, dict)}
        for filename in sorted(workflow_files - manifest_files):
            errors.append(f"{filename}: used by workflow but absent from manifest")
        for filename in sorted(manifest_files - workflow_files):
            errors.append(f"{filename}: declared but not used by any workflow")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot audit workflow models: {exc}")
    return manifest, errors
