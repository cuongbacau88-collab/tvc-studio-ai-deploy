#!/usr/bin/env python3
"""Build the runtime node manifest from the checked-in API workflows."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MANIFEST = ROOT / "workflows" / "manifest.json"
OUTPUT = ROOT / "configs" / "custom_nodes_manifest.json"

COMFY_REPOSITORY = "https://github.com/Comfy-Org/ComfyUI.git"
COMFY_COMMIT = "b963f4ad210a42841ab23dfc28a84143a0cce227"
PARTNER_NODE = "MinimaxHailuo03FirstLastFrameNode"
FRONTEND_ONLY_UNRESOLVED: set[str] = set()


def main() -> int:
    registry = json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))["workflows"]
    used_by: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"workflows": set(), "services": set()}
    )
    optional_only: dict[str, bool] = {}

    for workflow_name, entry in registry.items():
        graph = json.loads((ROOT / entry["file"]).read_text(encoding="utf-8"))
        workflow_optional = not bool(entry.get("default", False))
        for node in graph.values():
            class_type = node.get("class_type")
            if not isinstance(class_type, str) or not class_type:
                continue
            used_by[class_type]["workflows"].add(workflow_name)
            used_by[class_type]["services"].add(entry["service"])
            optional_only[class_type] = optional_only.get(class_type, True) and workflow_optional

    nodes = []
    for class_type in sorted(used_by):
        if class_type == PARTNER_NODE:
            classification = "partner_api"
            package = "ComfyUI comfy_api_nodes"
            repository = COMFY_REPOSITORY
            source_status = "resolved"
            credential_env = ["API_KEY_COMFY_ORG"]
            local_gpu_ready = False
            note = "Official Comfy Partner/API node; execution is billed remote API, not local GPU inference."
        elif class_type in FRONTEND_ONLY_UNRESOLVED:
            classification = "unresolved"
            package = None
            repository = None
            source_status = "unresolved"
            credential_env = []
            local_gpu_ready = False
            note = "Present in official blueprint JSON but absent from the pinned server's Python node registry; runtime /object_info must prove availability."
        else:
            classification = "core"
            package = "ComfyUI"
            repository = COMFY_REPOSITORY
            source_status = "resolved"
            credential_env = []
            local_gpu_ready = True
            note = None

        optional = optional_only[class_type]
        item = {
            "class_type": class_type,
            "classification": classification,
            "package": package,
            "repository": repository,
            "commit": COMFY_COMMIT if repository else None,
            "source_status": source_status,
            "required_by": {
                "workflows": sorted(used_by[class_type]["workflows"]),
                "services": sorted(used_by[class_type]["services"]),
            },
            "required": not optional,
            "optional": optional,
            "credential_env": credential_env,
            "local_gpu_ready": local_gpu_ready,
        }
        if note:
            item["note"] = note
        nodes.append(item)

    document = {
        "version": 1,
        "generated_from": "All class_type values in the seven workflows registered by workflows/manifest.json.",
        "comfyui": {
            "repository": COMFY_REPOSITORY,
            "commit": COMFY_COMMIT,
        },
        "nodes": nodes,
    }
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(nodes)} class types)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
