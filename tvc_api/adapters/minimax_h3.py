"""MiniMax H3 validation adapter; inference remains explicitly unconfigured."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .external import UnconfiguredExternalAdapter
from ..errors import APIError


SUPPORTED_TASKS = {
    "text_to_video", "image_to_video",
    "first_last_frame_to_video", "reference_to_video",
}
SUPPORTED_ASPECT_RATIOS = {"9:16", "16:9"}


def _existing_file(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise APIError("validation_error", f"{field} must be a file path", 422)
    path = Path(value).expanduser()
    if not path.is_file():
        raise APIError("input_file_not_found", f"Input file does not exist: {field}", 422)
    return path


def _reference_files(value: object, field: str) -> list[Path]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    if not values:
        raise APIError("validation_error", f"{field} must not be empty", 422)
    return [_existing_file(item, field) for item in values]


class MiniMaxH3Adapter(UnconfiguredExternalAdapter):
    adapter_name = "minimax_h3"

    def validate(self, inputs: dict[str, Any], parameters: dict[str, Any]) -> None:
        variant = parameters.get("variant")
        task_type = parameters.get("task_type")
        if variant not in {"fl2va", "ref2va"}:
            raise APIError("validation_error", "variant must be fl2va or ref2va", 422)
        if task_type not in SUPPORTED_TASKS:
            raise APIError("validation_error", "Unsupported MiniMax H3 task_type", 422)
        duration = parameters.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 4 <= duration <= 15:
            raise APIError("validation_error", "duration_seconds must be between 4 and 15", 422)
        if parameters.get("aspect_ratio") not in SUPPORTED_ASPECT_RATIOS:
            raise APIError("validation_error", "aspect_ratio must be 9:16 or 16:9", 422)
        if variant == "fl2va":
            self._validate_fl2va(task_type, inputs)
        else:
            self._validate_ref2va(task_type, inputs)

    def _validate_fl2va(self, task_type: str, inputs: dict[str, Any]) -> None:
        if task_type == "reference_to_video":
            raise APIError("validation_error", "reference_to_video requires ref2va", 422)
        prompt = inputs.get("prompt")
        if prompt is not None and (not isinstance(prompt, str) or not prompt.strip()):
            raise APIError("validation_error", "prompt must be a non-empty string", 422)
        first = inputs.get("first_frame")
        last = inputs.get("last_frame")
        if first is not None:
            _existing_file(first, "first_frame")
        if last is not None:
            _existing_file(last, "last_frame")
        if not any((isinstance(prompt, str) and prompt.strip(), first, last)):
            raise APIError("validation_error", "FL2VA requires prompt, first_frame, last_frame, or both frames", 422)
        if task_type == "text_to_video" and not (isinstance(prompt, str) and prompt.strip()):
            raise APIError("validation_error", "text_to_video requires prompt", 422)
        if task_type == "image_to_video" and first is None and last is None:
            raise APIError("validation_error", "image_to_video requires first_frame or last_frame", 422)

    def _validate_ref2va(self, task_type: str, inputs: dict[str, Any]) -> None:
        if task_type != "reference_to_video":
            raise APIError("validation_error", "ref2va requires reference_to_video", 422)
        references = []
        references.extend(_reference_files(inputs.get("reference_images"), "reference_images"))
        references.extend(_reference_files(inputs.get("reference_videos"), "reference_videos"))
        references.extend(_reference_files(inputs.get("reference_audio"), "reference_audio"))
        if not references:
            raise APIError("validation_error", "Ref2VA requires image, video, audio, or mixed references", 422)

