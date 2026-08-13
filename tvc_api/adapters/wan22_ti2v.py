"""Dedicated Wan 2.2 text/image-to-video validation adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .external import UnconfiguredExternalAdapter
from ..errors import APIError


class Wan22TI2VAdapter(UnconfiguredExternalAdapter):
    adapter_name = "wan22_ti2v"

    def validate(self, inputs: dict[str, Any], parameters: dict[str, Any]) -> None:
        task_type = parameters.get("task_type")
        if task_type not in {"text_to_video", "image_to_video"}:
            raise APIError("validation_error", "Wan2.2 TI2V task_type must be text_to_video or image_to_video", 422)
        prompt = inputs.get("prompt")
        if task_type == "text_to_video" and (not isinstance(prompt, str) or not prompt.strip()):
            raise APIError("validation_error", "text_to_video requires a non-empty prompt", 422)
        if task_type == "image_to_video":
            image = inputs.get("image")
            if not isinstance(image, str) or not image.strip():
                raise APIError("validation_error", "image_to_video requires an image file", 422)
            if not Path(image).expanduser().is_file():
                raise APIError("input_file_not_found", "Input file does not exist: image", 422)
