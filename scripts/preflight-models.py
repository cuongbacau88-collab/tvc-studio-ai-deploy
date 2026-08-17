#!/usr/bin/env python3
"""Validate manifest sources and physical model files without downloading."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_disk import default_comfyui_root, disk_summary
from model_manifest import validate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comfyui-root",
        type=Path,
        default=default_comfyui_root(ROOT),
        help="ComfyUI root containing the manifest model subdirectories",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest, errors = validate(ROOT)
    models = manifest.get("models", []) if manifest else []
    result = disk_summary(
        [item for item in models if isinstance(item, dict)],
        args.comfyui_root.expanduser().resolve(),
        errors,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
