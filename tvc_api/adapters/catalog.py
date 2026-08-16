"""Build one adapter for each registry model."""

from pathlib import Path

from ..registry import ModelRegistry
from .base import ModelAdapter
from .birefnet import BiRefNetAdapter
from .codeformer import CodeFormerAdapter
from .comfyui import ComfyWorkflowAdapter
from .ic_light import ICLightAdapter
from .seedvr2 import SeedVR2Adapter
from .wan22_animate import Wan22AnimateAdapter
from .wan22_ti2v import Wan22TI2VAdapter


ADAPTER_TYPES = {
    "wan22-animate": Wan22AnimateAdapter,
    "wan22_ti2v": Wan22TI2VAdapter,
    "birefnet": BiRefNetAdapter,
    "ic-light": ICLightAdapter,
    "seedvr2": SeedVR2Adapter,
    "codeformer": CodeFormerAdapter,
}

COMFY_OPERATIONS = {
    "scail2": "motion-transfer-video",
    "fashn-vton": "clothes-replacement",
    "qwen-image-edit": "scene-replacement",
    "realesrgan": "image-upscale-restoration",
    "minimax_h3": None,
}


def build_adapters(registry: ModelRegistry, repo_root: Path) -> dict[str, ModelAdapter]:
    adapters: dict[str, ModelAdapter] = {}
    for model_id, spec in registry.models.items():
        if model_id in COMFY_OPERATIONS:
            adapters[model_id] = ComfyWorkflowAdapter(
                spec, repo_root, COMFY_OPERATIONS[model_id]
            )
        elif model_id in ADAPTER_TYPES:
            adapters[model_id] = ADAPTER_TYPES[model_id](spec, repo_root)
    return adapters
