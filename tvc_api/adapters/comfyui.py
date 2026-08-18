"""ComfyUI API adapter backed by checked-in workflow contracts."""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from .base import ModelAdapter, Readiness
from ..errors import APIError
from ..workflows import WorkflowRegistry

DEFAULT_COMFY_TIMEOUT_SECONDS = 180.0


class ComfyWorkflowAdapter(ModelAdapter):
    def __init__(self, spec, repo_root: Path, operation: str | None = None) -> None:
        super().__init__(spec, repo_root)
        self.operation = operation
        self.workflows = WorkflowRegistry(repo_root)
        self.base_url = os.getenv("COMFYUI_URL", "").strip().rstrip("/")

    def _operation(self, parameters: dict[str, Any]) -> str:
        operation = self.operation or parameters.get("task_type")
        if not isinstance(operation, str) or not operation:
            raise APIError("workflow_not_mapped", "Workflow operation is missing", 422)
        return operation

    def entrypoint_ready(self) -> bool:
        return bool(self.base_url) and self.workflows.validate_all()["ready"]

    def readiness(self) -> Readiness:
        validation = self.workflows.validate_all()
        checks = {
            "enabled": bool(self.spec.data["enabled"]),
            "comfyui_url": bool(self.base_url),
            "workflow_contracts": validation["ready"],
        }
        ready = all(checks.values())
        return Readiness(ready, checks, None if ready else "ComfyUI or workflow preflight is not ready")

    def validate(self, inputs: dict[str, Any], parameters: dict[str, Any]) -> None:
        operation = self._operation(parameters)
        self.workflows.bind(
            operation, self.spec.id, self._normalize_inputs(operation, inputs), parameters
        )

    async def run(self, inputs: dict[str, Any], parameters: dict[str, Any],
                  output_dir: Path) -> dict[str, Any]:
        if not self.base_url:
            raise APIError("comfyui_unavailable", "COMFYUI_URL is not configured", 503)
        return await asyncio.to_thread(self._run_sync, inputs, parameters, output_dir)

    def _interrupt_comfyui(self) -> None:
        try:
            req = Request(f"{self.base_url}/interrupt", data=b"{}", headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass

    def _run_sync(self, inputs: dict[str, Any], parameters: dict[str, Any],
                  output_dir: Path) -> dict[str, Any]:
        operation = self._operation(parameters)
        normalized = self._normalize_inputs(operation, inputs)
        spec = self.workflows.spec_for(operation, self.spec.id, parameters)
        partner_key = ""
        if spec.get("mode") == "first_last":
            partner_key = os.getenv("API_KEY_COMFY_ORG", "").strip()
            if not partner_key:
                raise APIError(
                    "partner_api_key_missing",
                    "API_KEY_COMFY_ORG is required for H3 First/Last Frame",
                    503,
                )
            try:
                object_info = json.loads(self._request("/object_info/MinimaxHailuo03FirstLastFrameNode"))
            except Exception as exc:
                raise APIError("comfyui_unavailable", f"Cannot query ComfyUI object info: {exc}", 503) from exc
            if "MinimaxHailuo03FirstLastFrameNode" not in object_info:
                raise APIError(
                    "partner_node_unavailable",
                    "ComfyUI runtime does not provide MinimaxHailuo03FirstLastFrameNode",
                    503,
                )

        uploaded: dict[str, str] = {}
        for external, target in spec.get("inputs", {}).items():
            if target.get("kind") == "upload" and external in normalized:
                uploaded[external] = self._upload(Path(str(normalized[external])))

        workflow, spec = self.workflows.bind(
            operation, self.spec.id, normalized, parameters, uploaded
        )

        prompt_id = self._submit_prompt(workflow, partner_key)

        try:
            result = self._wait_for_output(prompt_id, spec)
        except Exception:
            self._interrupt_comfyui()
            raise

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / Path(result["filename"]).name
        try:
            output_path.write_bytes(self._view(result))
        except Exception as exc:
            self._interrupt_comfyui()
            raise APIError("comfyui_output_fetch_failed", f"Failed to retrieve output media: {exc}", 502) from exc

        if output_path.stat().st_size == 0:
            self._interrupt_comfyui()
            raise APIError("invalid_output", "ComfyUI returned an empty output", 502)

        return {
            "output_path": str(output_path),
            "output_type": spec["outputs"][0]["type"],
            "workflow": spec["file"],
            "prompt_id": prompt_id,
        }

    @staticmethod
    def _normalize_inputs(operation: str, inputs: dict[str, Any]) -> dict[str, Any]:
        values = dict(inputs)
        aliases = {
            "image": ("character_image", "person_image", "source_image", "first_frame"),
            "video": ("motion_video", "reference_video"),
            "garment_image": ("outfit_image", "clothing_image", "reference_image"),
        }
        for target, candidates in aliases.items():
            if target not in values:
                for candidate in candidates:
                    if values.get(candidate) is not None:
                        values[target] = values[candidate]
                        break
        if operation in {"image_to_video", "reference_to_video"} and "image" not in values:
            references = values.get("reference_images")
            if isinstance(references, list) and references:
                values["image"] = references[0]
            elif isinstance(references, str):
                values["image"] = references
        return values

    def _request(self, path: str, data: bytes | None = None,
                 headers: dict[str, str] | None = None, timeout: float = 30.0) -> bytes:
        request = Request(f"{self.base_url}{path}", data=data, headers=headers or {})
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            raise APIError("comfyui_unavailable", f"ComfyUI request failed on {path}: {exc}", 503) from exc

    def _upload(self, path: Path) -> str:
        if not path.is_file():
            raise APIError("input_file_not_found", f"Input file does not exist: {path}", 422)
        boundary = f"----tvc-{uuid4().hex}"
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        try:
            payload = json.loads(self._request(
                "/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}
            ))
        except APIError:
            raise
        except Exception as exc:
            raise APIError("comfyui_upload_failed", f"Failed to upload asset to ComfyUI: {exc}", 502) from exc

        name = payload.get("name")
        if not isinstance(name, str) or not name:
            raise APIError("comfyui_upload_failed", "ComfyUI did not return an upload name", 502)
        subfolder = payload.get("subfolder")
        return f"{subfolder}/{name}" if isinstance(subfolder, str) and subfolder else name

    def _submit_prompt(self, workflow: dict[str, Any], partner_key: str = "") -> str:
        payload: dict[str, Any] = {"prompt": workflow, "client_id": uuid4().hex}
        if partner_key:
            payload["extra_data"] = {"api_key_comfy_org": partner_key}
        body = json.dumps(payload).encode()
        try:
            response_data = self._request("/prompt", body, {"Content-Type": "application/json"})
            payload = json.loads(response_data)
        except APIError:
            raise
        except Exception as exc:
            raise APIError("comfyui_prompt_failed", f"Failed to submit prompt to ComfyUI (port 8188): {exc}", 502) from exc

        prompt_id = payload.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            detail = payload.get("error") or payload.get("node_errors") or "missing prompt_id"
            raise APIError("comfyui_prompt_rejected", f"ComfyUI rejected workflow: {detail}", 502)
        return prompt_id

    def _wait_for_output(self, prompt_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        timeout_seconds = float(os.getenv("GPU_TASK_TIMEOUT_SECONDS", str(DEFAULT_COMFY_TIMEOUT_SECONDS)))
        start_time = time.time()
        poll_interval = 1.0
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                self._interrupt_comfyui()
                raise APIError(
                    "comfyui_timeout",
                    f"ComfyUI job execution exceeded maximum allowed timeout of {int(timeout_seconds)}s (3 minutes). GPU has been freed.",
                    504,
                )
            try:
                history_bytes = self._request(f"/history/{prompt_id}", timeout=10.0)
                history = json.loads(history_bytes)
            except APIError:
                if time.time() - start_time > timeout_seconds:
                    raise
                time.sleep(poll_interval)
                continue
            except Exception as exc:
                if time.time() - start_time > timeout_seconds:
                    self._interrupt_comfyui()
                    raise APIError("comfyui_timeout", f"ComfyUI polling timed out: {exc}", 504) from exc
                time.sleep(poll_interval)
                continue

            record = history.get(prompt_id)
            if isinstance(record, dict):
                status = record.get("status", {})
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    self._interrupt_comfyui()
                    raise APIError("comfyui_execution_failed", f"ComfyUI workflow execution failed: {messages}", 502)
                outputs = record.get("outputs", {})
                for mapping in spec["outputs"]:
                    node_output = outputs.get(str(mapping["node_id"]), {})
                    for key in ("images", "videos", "gifs"):
                        values = node_output.get(key)
                        if isinstance(values, list) and values and isinstance(values[0], dict):
                            return values[0]
                if status.get("completed"):
                    self._interrupt_comfyui()
                    raise APIError("invalid_output", "Mapped ComfyUI output node returned no file", 502)
            time.sleep(poll_interval)

    def _view(self, output: dict[str, Any]) -> bytes:
        filename = output.get("filename")
        if not isinstance(filename, str) or not filename:
            raise APIError("invalid_output", "ComfyUI output filename is missing", 502)
        query = urlencode({
            "filename": filename,
            "subfolder": output.get("subfolder", ""),
            "type": output.get("type", "output"),
        })
        return self._request(f"/view?{query}")
