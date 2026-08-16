"""Load, validate, and bind the checked-in ComfyUI API workflows.

The manifest is explicit: runtime code never guesses a ComfyUI node identifier.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .errors import APIError


MODEL_INPUTS = {
    "ckpt_name": "checkpoints",
    "unet_name": "diffusion_models",
    "vae_name": "vae",
    "clip_name": "text_encoders",
    "lora_name": "loras",
    "model_name": "upscale_models",
}
OUTPUT_CLASSES = {"SaveImage": "image", "SaveVideo": "video"}
UPLOAD_CLASSES = {"LoadImage", "LoadVideo"}


class WorkflowRegistry:
    def __init__(self, root: Path, manifest_path: Path | None = None,
                 model_manifest_path: Path | None = None) -> None:
        self.root = root.resolve()
        self.manifest_path = manifest_path or self.root / "workflows" / "manifest.json"
        self.model_manifest_path = model_manifest_path or self.root / "configs" / "model_manifest.json"
        self.manifest = self._read_json(self.manifest_path, "workflow manifest")
        self.model_manifest = self._read_json(self.model_manifest_path, "model manifest")

    @staticmethod
    def _read_json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise APIError("workflow_preflight_failed", f"Invalid {label}: {exc}", 503) from exc
        if not isinstance(value, dict):
            raise APIError("workflow_preflight_failed", f"{label} must be a JSON object", 503)
        return value

    def spec_for(self, operation: str, model_id: str,
                 parameters: dict[str, Any]) -> dict[str, Any]:
        key = self._workflow_key(operation, model_id, parameters)
        try:
            return self.manifest["workflows"][key]
        except (KeyError, TypeError) as exc:
            raise APIError("workflow_not_mapped", f"No workflow mapped for {operation}/{model_id}", 422) from exc

    @staticmethod
    def _workflow_key(operation: str, model_id: str, parameters: dict[str, Any]) -> str:
        if model_id == "minimax_h3":
            if operation == "first_last_frame_to_video":
                return "video_h3_first_last"
            if operation in {"image_to_video", "reference_to_video"}:
                return "video_h3_i2v"
        return {
            ("motion-transfer-video", "scail2"): "motion_scail2",
            ("clothes-replacement", "fashn-vton"): "outfit_flux2_klein",
            ("scene-replacement", "qwen-image-edit"): "background_flux2_klein",
            ("image-upscale-restoration", "realesrgan"): "upscale_realesrgan",
        }.get((operation, model_id), "")

    def load_workflow(self, spec: dict[str, Any]) -> dict[str, Any]:
        relative = spec.get("file")
        if not isinstance(relative, str) or not relative:
            raise APIError("workflow_preflight_failed", "Workflow file mapping is missing", 503)
        path = (self.root / relative).resolve()
        if self.root not in path.parents or not path.is_file():
            raise APIError("workflow_preflight_failed", f"Workflow file does not exist: {relative}", 503)
        return self._read_json(path, f"workflow {relative}")

    def bind(self, operation: str, model_id: str, inputs: dict[str, Any],
             parameters: dict[str, Any], uploaded_names: dict[str, Any] | None = None
             ) -> tuple[dict[str, Any], dict[str, Any]]:
        spec = self.spec_for(operation, model_id, parameters)
        workflow = deepcopy(self.load_workflow(spec))
        values = dict(inputs)
        if uploaded_names:
            values.update(uploaded_names)
        for external, target in spec.get("inputs", {}).items():
            value = values.get(external)
            if value is None and "default" in target:
                value = target["default"]
            if value is None:
                if target.get("required", False):
                    raise APIError("validation_error", f"Missing workflow input: {external}", 422)
                continue
            self._set(workflow, target, value, external)
        for external, target in spec.get("parameters", {}).items():
            value = parameters.get(external, target.get("default"))
            if value is not None:
                self._set(workflow, target, value, external)
        all_values = {**values, **parameters}
        for target in spec.get("mirrors", []):
            source = target.get("source")
            if source in all_values and all_values[source] is not None:
                self._set(workflow, target, all_values[source], str(source))
        return workflow, spec

    @staticmethod
    def _set(workflow: dict[str, Any], target: dict[str, Any], value: Any, label: str) -> None:
        node_id, field = str(target.get("node_id", "")), target.get("field")
        if node_id not in workflow or not isinstance(field, str) or field not in workflow[node_id].get("inputs", {}):
            raise APIError("workflow_preflight_failed", f"Invalid mapping for {label}: {node_id}.{field}", 503)
        workflow[node_id]["inputs"][field] = value

    def validate_all(self) -> dict[str, Any]:
        errors: list[str] = []
        checked: list[str] = []
        declared_models = {
            item.get("filename")
            for item in self.model_manifest.get("models", [])
            if isinstance(item, dict)
        }
        for key, spec in self.manifest.get("workflows", {}).items():
            try:
                workflow = self.load_workflow(spec)
                self._validate_spec(spec, workflow, declared_models)
                checked.append(key)
            except APIError as exc:
                errors.append(f"{key}: {exc.message}")
        return {"ready": not errors, "checked": checked, "errors": errors}

    def _validate_spec(self, spec: dict[str, Any], workflow: dict[str, Any],
                       declared_models: set[Any]) -> None:
        for group in ("inputs", "parameters"):
            for label, target in spec.get(group, {}).items():
                node_id, field = str(target.get("node_id", "")), target.get("field")
                node = workflow.get(node_id)
                if not isinstance(node, dict) or field not in node.get("inputs", {}):
                    raise APIError("workflow_preflight_failed",
                                   f"{group}.{label} points to missing {node_id}.{field}", 503)
                if group == "inputs" and target.get("kind") == "upload":
                    if node.get("class_type") not in UPLOAD_CLASSES:
                        raise APIError("workflow_preflight_failed",
                                       f"{node_id} is not a LoadImage/LoadVideo node", 503)
        for target in spec.get("mirrors", []):
            node_id, field = str(target.get("node_id", "")), target.get("field")
            if node_id not in workflow or field not in workflow[node_id].get("inputs", {}):
                raise APIError("workflow_preflight_failed", "Mirror mapping is invalid", 503)
        outputs = spec.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            raise APIError("workflow_preflight_failed", "No output mapping declared", 503)
        for output in outputs:
            node = workflow.get(str(output.get("node_id", "")))
            expected = output.get("type")
            if not isinstance(node, dict) or OUTPUT_CLASSES.get(node.get("class_type")) != expected:
                raise APIError("workflow_preflight_failed", "Output mapping is invalid", 503)
        found_models: set[str] = set()
        for node in workflow.values():
            for field in MODEL_INPUTS:
                value = node.get("inputs", {}).get(field) if isinstance(node, dict) else None
                if isinstance(value, str):
                    found_models.add(value)
        missing = found_models - declared_models
        if missing:
            raise APIError("workflow_preflight_failed",
                           f"Undeclared model filenames: {', '.join(sorted(missing))}", 503)
        if found_models != set(spec.get("models", [])):
            raise APIError("workflow_preflight_failed", "Workflow model list does not match JSON", 503)
