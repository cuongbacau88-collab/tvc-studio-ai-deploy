"""Conservative external-repository adapter.

Phase 3 does not guess upstream CLI contracts. An adapter remains unavailable until
an operator configures and verifies an entrypoint in a later model-integration step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import ModelAdapter
from ..errors import APIError


class UnconfiguredExternalAdapter(ModelAdapter):
    adapter_name = "external"

    def entrypoint_ready(self) -> bool:
        return False

    async def run(self, inputs: dict[str, Any], parameters: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        raise APIError("model_not_configured", f"{self.spec.id} inference entrypoint is not configured", 503)

