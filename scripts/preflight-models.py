#!/usr/bin/env python3
"""Validate model download readiness without downloading anything."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_manifest import validate


manifest, errors = validate(ROOT)
models = manifest.get("models", []) if manifest else []
unresolved = [
    item.get("filename")
    for item in models
    if isinstance(item, dict) and item.get("required") and item.get("source_status") != "resolved"
]
result = {
    "ready": not errors,
    "models": len(models),
    "required": sum(bool(item.get("required")) for item in models if isinstance(item, dict)),
    "optional": sum(bool(item.get("optional")) for item in models if isinstance(item, dict)),
    "unresolved_required": unresolved,
    "errors": errors,
}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["ready"] else 1)
