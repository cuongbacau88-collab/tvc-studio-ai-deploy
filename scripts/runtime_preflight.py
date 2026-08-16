#!/usr/bin/env python3
"""Validate a live ComfyUI GPU runtime against checked-in workflows/manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_object_info(url: str) -> tuple[dict, str | None]:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/object_info", timeout=15) as response:
            data = json.load(response)
        return data if isinstance(data, dict) else {}, None
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return {}, str(exc)


def gpu_status(comfyui_dir: Path) -> dict:
    result = {"nvidia_smi": False, "torch_cuda": False, "errors": []}
    try:
        check = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=15)
        result["nvidia_smi"] = check.returncode == 0
        if check.returncode:
            result["errors"].append(check.stderr.strip() or "nvidia-smi failed")
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["errors"].append(str(exc))
    runtime_python = comfyui_dir / ".venv" / "bin" / "python"
    if runtime_python.is_file():
        check = subprocess.run(
            [str(runtime_python), "-c", "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)"],
            capture_output=True, text=True, timeout=30,
        )
        result["torch_cuda"] = check.returncode == 0
        if check.returncode:
            result["errors"].append(check.stderr.strip() or "torch.cuda.is_available() is false")
    else:
        result["errors"].append(f"runtime Python missing: {runtime_python}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfyui-dir", default=os.getenv("COMFYUI_DIR", str(ROOT / "runtime" / "ComfyUI")))
    parser.add_argument("--comfyui-url", default=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--skip-checksums", action="store_true", help="Development-only; presence is still checked")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    comfyui_dir = Path(args.comfyui_dir).resolve()
    workflow_registry = json.loads((ROOT / "workflows" / "manifest.json").read_text(encoding="utf-8"))["workflows"]
    node_manifest = json.loads((ROOT / "configs" / "custom_nodes_manifest.json").read_text(encoding="utf-8"))
    model_manifest = json.loads((ROOT / "configs" / "model_manifest.json").read_text(encoding="utf-8"))
    node_meta = {item["class_type"]: item for item in node_manifest["nodes"]}

    runtime_exists = (comfyui_dir / "main.py").is_file()
    expected_commit = node_manifest["comfyui"]["commit"]
    actual_commit = None
    if (comfyui_dir / ".git").is_dir():
        check = subprocess.run(
            ["git", "-C", str(comfyui_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        if check.returncode == 0:
            actual_commit = check.stdout.strip()
    commit_ok = actual_commit == expected_commit
    gpu = gpu_status(comfyui_dir)
    object_info, api_error = fetch_object_info(args.comfyui_url)
    runtime_nodes = set(object_info)

    models = {}
    for item in model_manifest["models"]:
        path = comfyui_dir / item["comfyui_subdir"] / item["filename"]
        present = path.is_file()
        checksum_ok = None
        if present and item.get("sha256") and not args.skip_checksums:
            checksum_ok = sha256(path).lower() == item["sha256"].lower()
        models[item["filename"]] = {
            "path": str(path), "present": present, "checksum_ok": checksum_ok,
            "required": bool(item.get("required")),
        }

    services = {}
    for workflow_name, entry in workflow_registry.items():
        graph = json.loads((ROOT / entry["file"]).read_text(encoding="utf-8"))
        class_types = sorted({node["class_type"] for node in graph.values()})
        missing_nodes = sorted(set(class_types) - runtime_nodes)
        missing_models = []
        invalid_models = []
        for filename in entry.get("models", []):
            status = models.get(filename)
            if not status or not status["present"]:
                missing_models.append(filename)
            elif status["checksum_ok"] is False:
                invalid_models.append(filename)
        output_nodes = entry.get("outputs", [])
        invalid_outputs = [
            output for output in output_nodes
            if str(output["node_id"]) not in graph
            or graph[str(output["node_id"])]["class_type"] not in {"SaveImage", "SaveVideo"}
        ]
        partner_nodes = [node for node in class_types if node_meta.get(node, {}).get("classification") == "partner_api"]
        missing_credentials = sorted({
            env for node in partner_nodes for env in node_meta[node].get("credential_env", []) if not os.getenv(env)
        })
        local_gpu_ready = not partner_nodes
        ready = all((
            runtime_exists, commit_ok, gpu["nvidia_smi"], gpu["torch_cuda"], not api_error,
            not missing_nodes, not missing_models, not invalid_models, not invalid_outputs,
            not missing_credentials,
        ))
        services[workflow_name] = {
            "service": entry["service"], "mode": entry.get("mode"), "required": bool(entry.get("default")),
            "ready": ready, "local_gpu_ready": local_gpu_ready and ready,
            "missing_nodes": missing_nodes, "missing_models": missing_models,
            "invalid_model_checksums": invalid_models, "invalid_outputs": invalid_outputs,
            "partner_api_nodes": partner_nodes, "missing_credentials": missing_credentials,
        }

    report = {
        "ready": all(item["ready"] for item in services.values() if item["required"]),
        "comfyui": {
            "path": str(comfyui_dir), "exists": runtime_exists, "url": args.comfyui_url,
            "api_error": api_error, "expected_commit": expected_commit,
            "actual_commit": actual_commit, "commit_ok": commit_ok,
        },
        "gpu": gpu,
        "capabilities": {
            "load_video": "LoadVideo" in runtime_nodes,
            "save_image": "SaveImage" in runtime_nodes,
            "save_video": "SaveVideo" in runtime_nodes,
        },
        "services": services,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"RUNTIME READY: {'YES' if report['ready'] else 'NO'}")
        for name, status in services.items():
            reasons = status["missing_nodes"] + status["missing_models"] + status["invalid_model_checksums"] + status["missing_credentials"]
            print(f"- {name}: {'READY' if status['ready'] else 'NOT READY'}" + (f" ({', '.join(reasons)})" if reasons else ""))
        if api_error:
            print(f"- ComfyUI /object_info: {api_error}")
        for error in gpu["errors"]:
            print(f"- GPU: {error}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
