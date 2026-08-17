#!/usr/bin/env python3
"""Manifest-driven, resumable model downloader for ComfyUI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_disk import (
    COMPLETE, MISSING, PARTIAL, default_comfyui_root, disk_summary, model_path, sha256,
)
from model_manifest import validate

DEFAULT_READ_TIMEOUT = int(os.getenv("GPU_MODEL_DOWNLOAD_TIMEOUT_SECONDS", "600"))


def valid_existing(path: Path, expected: str | None) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    return expected is None or sha256(path) == expected


def huggingface_source(source_url: str) -> tuple[str, str, str] | None:
    """Return repo_id, filename, and revision for a Hugging Face resolve URL."""
    parsed = urlparse(source_url)
    if parsed.hostname not in {"huggingface.co", "www.huggingface.co"}:
        return None
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 5 or parts[2] != "resolve":
        raise ValueError(f"unsupported Hugging Face model URL: {source_url}")
    return "/".join(parts[:2]), "/".join(parts[4:]), parts[3]


def huggingface_cache_dir(comfyui_root: Path) -> Path:
    """Locate the HF cache on the persistent volume unless explicitly configured."""
    hf_home = os.getenv("HF_HOME", "").strip()
    if hf_home:
        return Path(hf_home).expanduser() / "hub"
    xdg_cache = os.getenv("XDG_CACHE_HOME", "").strip()
    if xdg_cache:
        return Path(xdg_cache).expanduser() / "huggingface" / "hub"
    return comfyui_root.parent / ".cache" / "huggingface" / "hub"


def promote_verified(source: Path, destination: Path, expected: str | None) -> None:
    """Copy a verified cache file to a same-filesystem temporary, then rename it."""
    if not valid_existing(source, expected):
        actual = sha256(source) if source.is_file() else "missing"
        raise RuntimeError(
            f"checksum validation failed for cached {destination.name}: {actual}"
        )
    partial = destination.with_name(destination.name + ".part")
    with source.open("rb") as cached, partial.open("wb") as output:
        while chunk := cached.read(8 * 1024 * 1024):
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
    if not valid_existing(partial, expected):
        actual = sha256(partial) if partial.is_file() else "missing"
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"checksum validation failed before promotion of {destination.name}: {actual}"
        )
    os.replace(partial, destination)


def download_huggingface(model: dict[str, Any], destination: Path,
                         cache_dir: Path, force_download: bool = False) -> None:
    source = huggingface_source(model["source_url"])
    if source is None:
        raise ValueError("download_huggingface requires a huggingface.co URL")
    repo_id, filename, revision = source
    from huggingface_hub import hf_hub_download

    cached = Path(hf_hub_download(
        repo_id=repo_id, filename=filename, revision=revision,
        cache_dir=str(cache_dir), token=os.getenv("HF_TOKEN", "").strip() or None,
        force_download=force_download,
    ))
    promote_verified(cached, destination, model.get("sha256"))


def download_once(model: dict[str, Any], destination: Path,
                  timeout: int = DEFAULT_READ_TIMEOUT) -> None:
    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "tvc-studio-ai-model-downloader/2"}
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = Request(model["source_url"], headers=headers)
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        if exc.code == 416 and valid_existing(partial, model.get("sha256")):
            os.replace(partial, destination)
            return
        raise
    with response:
        append = offset > 0 and getattr(response, "status", None) == 206
        mode = "ab" if append else "wb"
        expected_bytes = response.headers.get("Content-Length")
        received = 0
        with partial.open(mode) as output:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                received += len(chunk)
            output.flush()
            os.fsync(output.fileno())
        if expected_bytes is not None and received != int(expected_bytes):
            raise RuntimeError(
                f"incomplete HTTP response for {model['filename']}: "
                f"received {received} of {expected_bytes} bytes"
            )
    expected = model.get("sha256")
    if not valid_existing(partial, expected):
        actual = sha256(partial) if partial.exists() else "missing"
        if partial.exists():
            partial.unlink()
        raise RuntimeError(
            f"checksum/size validation failed for {model['filename']}: {actual}"
        )
    os.replace(partial, destination)


def human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TiB"


def download(model: dict[str, Any], root: Path, retries: int,
             timeout: int = DEFAULT_READ_TIMEOUT) -> str:
    destination = model_path(model, root)
    if valid_existing(destination, model.get("sha256")):
        print(f"SKIP VALID: {destination}")
        return COMPLETE
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    hf_source = huggingface_source(model["source_url"])
    cache_dir = huggingface_cache_dir(root)
    if partial.is_file() and hf_source is None:
        print(f"RESUME: {human_bytes(partial.stat().st_size)}")
    force_hf_download = False
    for attempt in range(1, retries + 1):
        print(f"ATTEMPT {attempt}/{retries}")
        try:
            if hf_source is not None:
                cache_dir.mkdir(parents=True, exist_ok=True)
                download_huggingface(
                    model, destination, cache_dir, force_download=force_hf_download,
                )
            else:
                download_once(model, destination, timeout)
            print(f"COMPLETE: {destination}")
            return COMPLETE
        except Exception as exc:
            if (
                hf_source is not None
                and str(exc).startswith("checksum validation failed for cached ")
            ):
                force_hf_download = True
            print(
                f"ATTEMPT FAILED {attempt}/{retries}: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            if attempt < retries:
                delay = min(2 ** (attempt - 1), 30)
                print(f"RETRY IN: {delay}s")
                time.sleep(delay)
    print(f"FAILED: {model['filename']}", file=sys.stderr)
    return "FAILED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comfyui-root",
        type=Path,
        default=default_comfyui_root(ROOT),
        help="ComfyUI installation root; models/ subdirectories are created below it",
    )
    parser.add_argument("--include-optional", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument(
        "--read-timeout",
        type=int,
        default=DEFAULT_READ_TIMEOUT,
        help="Per-network-read timeout in seconds for large model files",
    )
    return parser.parse_args()


def print_summary(models: list[dict[str, Any]], root: Path,
                  failed: set[str]) -> dict[str, Any]:
    summary = disk_summary(models, root)
    buckets: dict[str, list[str]] = {
        COMPLETE: [], "FAILED": [], PARTIAL: [], MISSING: [],
    }
    for model, record in zip(models, summary["models"]):
        filename = str(model["filename"])
        if filename in failed:
            buckets["FAILED"].append(filename)
        elif record["status"] in buckets:
            buckets[record["status"]].append(filename)
        else:
            buckets["FAILED"].append(filename)
    print("\nDOWNLOAD SUMMARY")
    for label in (COMPLETE, "FAILED", PARTIAL, MISSING):
        print(f"{label}: {len(buckets[label])}")
        for filename in buckets[label]:
            print(f"  - {filename}")
    print(
        f"REQUIRED COMPLETE: {summary['required_complete']}/{summary['required_total']}"
    )
    print(f"READY: {str(summary['ready']).lower()}")
    return summary


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
    if args.retries < 1 or args.read_timeout < 1:
        print("ERROR: retries and read timeout must be at least 1", file=sys.stderr)
        return 2
    root = args.comfyui_root.expanduser().resolve()
    if args.dry_run:
        for index, item in enumerate(selected, 1):
            print(f"[{index}/{len(selected)}] {item['filename']}")
            print(model_path(item, root))
        summary = print_summary(selected, root, set())
        print("DRY RUN: no files downloaded")
        return 0 if summary["ready"] else 1

    failed: set[str] = set()
    for index, item in enumerate(selected, 1):
        print(f"\n[{index}/{len(selected)}] {item['filename']}")
        if download(item, root, args.retries, args.read_timeout) == "FAILED":
            failed.add(str(item["filename"]))
    summary = print_summary(selected, root, failed)
    required_failed = any(
        item.get("required")
        and summary["models"][index]["status"] != COMPLETE
        for index, item in enumerate(selected)
    )
    return 1 if required_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
