"""Request validation and public job operation definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import APIError


OPERATION_PRIORITIES = {
    "motion-transfer-video": 100,
    "prompt-video": 90,
    "clothes-replacement": 30,
    "scene-replacement": 20,
    "image-upscale-restoration": 10,
    "text_to_video": 90,
    "image_to_video": 90,
    "first_last_frame_to_video": 100,
    "reference_to_video": 100,
}

OPERATION_MODELS = {
    "motion-transfer-video": {"wan22-animate", "scail2"},
    "prompt-video": {"wan22-animate", "scail2"},
    "clothes-replacement": {"fashn-vton"},
    "scene-replacement": {"qwen-image-edit"},
    "image-upscale-restoration": {"seedvr2", "realesrgan", "codeformer"},
    "text_to_video": {"minimax_h3", "wan22_ti2v"},
    "image_to_video": {"minimax_h3", "wan22_ti2v"},
    "first_last_frame_to_video": {"minimax_h3"},
    "reference_to_video": {"minimax_h3"},
}


@dataclass(frozen=True)
class JobRequest:
    owner_id: str
    client_job_id: str
    operation: str
    model_id: str
    inputs: dict[str, Any]
    parameters: dict[str, Any]

    @property
    def priority(self) -> int:
        return OPERATION_PRIORITIES[self.operation]

    @classmethod
    def parse(cls, value: object) -> "JobRequest":
        if not isinstance(value, dict):
            raise APIError("validation_error", "Request body must be a JSON object", 422)
        owner_id = value.get("owner_id")
        client_job_id = value.get("client_job_id")
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise APIError("validation_error", "owner_id must be a non-empty string", 422)
        if not isinstance(client_job_id, str) or not client_job_id.strip():
            raise APIError("validation_error", "client_job_id must be a non-empty string", 422)
        operation = value.get("operation")
        model_id = value.get("model_id")
        if operation not in OPERATION_PRIORITIES:
            raise APIError("validation_error", "Unsupported operation", 422)
        if not isinstance(model_id, str) or model_id not in OPERATION_MODELS[operation]:
            raise APIError("validation_error", "Model is not valid for the requested operation", 422)
        inputs = value.get("inputs", {})
        parameters = value.get("parameters", {})
        if not isinstance(inputs, dict) or not inputs:
            raise APIError("validation_error", "inputs must be a non-empty object", 422)
        if not isinstance(parameters, dict):
            raise APIError("validation_error", "parameters must be an object", 422)
        typed_operations = {"text_to_video", "image_to_video", "first_last_frame_to_video", "reference_to_video"}
        if operation in typed_operations and parameters.get("task_type") != operation:
            raise APIError("validation_error", "parameters.task_type must match operation", 422)
        return cls(owner_id.strip(), client_job_id.strip(), operation, model_id, inputs, parameters)

