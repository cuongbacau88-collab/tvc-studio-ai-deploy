"""Build one adapter for each Phase 2 registry model."""

from pathlib import Path

from ..registry import ModelRegistry
from .base import ModelAdapter
from .birefnet import BiRefNetAdapter
from .codeformer import CodeFormerAdapter
from .fashn_vton import FashnVtonAdapter
from .ic_light import ICLightAdapter
from .minimax_h3 import MiniMaxH3Adapter
from .qwen_image_edit import QwenImageEditAdapter
from .realesrgan import RealESRGANAdapter
from .scail2 import Scail2Adapter
from .seedvr2 import SeedVR2Adapter
from .wan22_animate import Wan22AnimateAdapter
from .wan22_ti2v import Wan22TI2VAdapter


ADAPTER_TYPES = {
    "scail2": Scail2Adapter,
    "wan22-animate": Wan22AnimateAdapter,
    "wan22_ti2v": Wan22TI2VAdapter,
    "minimax_h3": MiniMaxH3Adapter,
    "fashn-vton": FashnVtonAdapter,
    "qwen-image-edit": QwenImageEditAdapter,
    "birefnet": BiRefNetAdapter,
    "ic-light": ICLightAdapter,
    "seedvr2": SeedVR2Adapter,
    "realesrgan": RealESRGANAdapter,
    "codeformer": CodeFormerAdapter,
}


def build_adapters(registry: ModelRegistry, repo_root: Path) -> dict[str, ModelAdapter]:
    return {
        model_id: ADAPTER_TYPES[model_id](spec, repo_root)
        for model_id, spec in registry.models.items()
        if model_id in ADAPTER_TYPES
    }

