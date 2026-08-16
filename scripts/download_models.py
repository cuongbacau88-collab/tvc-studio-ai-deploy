#!/usr/bin/env python3
"""Manifest-driven, resumable model downloader for ComfyUI."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_manifest import validate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_existing(path: Path, expected: str | None) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    return expected is None or sha256(path) == expected


def download_once(model: dict[str, Any], destination: Path) -> None:
    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "tvc-studio-ai-model-downloader/1"}
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = Request(model["source_url"], headers=headers)
    try:
        response = urlopen(request, timeout=60)
    except HTTPError as exc:
        if exc.code == 416 and valid_existing(partial, model.get("sha256")):
            os.replace(partial, destination)
            return
        raise
    with response:
        append = offset > 0 and getattr(response, "status", None) == 206
        if offset and not append:
            offset = 0
        mode = "ab" if append else "wb"
        with partial.open(mode) as output:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    expected = model.get("sha256")
    if not valid_existing(partial, expected):
        actual = sha256(partial) if partial.exists() else "missing"
        raise RuntimeError(
            f"checksum/size validation failed for {model['filename']}: {actual}"
        )
    os.replace(partial, destination)


def download(model: dict[str, Any], root: Path, retries: int) -> None:
    destination = root / model["comfyui_subdir"] / model["filename"]
    if valid_existing(destination, model.get("sha256")):
        print(f"SKIP valid: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            print(f"DOWNLOAD {attempt}/{retries}: {model['filename']}")
            download_once(model, destination)
            print(f"OK: {destination}")
            return
        except Exception:
            if attempt == retries:
                raise
            time.sleep(min(2 ** (attempt - 1), 30))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comfyui-root",
        type=Path,
        default=Path(os.getenv("COMFYUI_ROOT", "ComfyUI")),
        help="ComfyUI installation root; models/ subdirectories are created below it",
    )
    parser.add_argument("--include-optional", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retries", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest, errors = validate(ROOT)
    selected = [
        item for item in manifest.get("models", [])
        if item.get("required") or args.include_optional
    ]
    unresolved = [
        item.get("filename") for item in selected
        if item.get("source_status") != "resolved" or not item.get("source_url")
    ]
    if errors or unresolved:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for filename in unresolved:
            print(f"ERROR: unresolved source: {filename}", file=sys.stderr)
        return 2
    if args.retries < 1:
        print("ERROR: --retries must be at least 1", file=sys.stderr)
        return 2
    if args.dry_run:
        for item in selected:
            print(args.comfyui_root / item["comfyui_subdir"] / item["filename"])
        print(f"READY: {len(selected)} model files; no files downloaded")
        return 0
    for item in selected:
        download(item, args.comfyui_root.resolve(), args.retries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
