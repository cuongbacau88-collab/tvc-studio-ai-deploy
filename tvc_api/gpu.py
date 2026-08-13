"""Non-throwing NVIDIA GPU availability probes."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class GPUStatus:
    available: bool
    index: int
    total_vram_gb: float
    free_vram_gb: float
    reason: str | None = None

    def sufficient(self, minimum_gb: float) -> bool:
        return self.available and self.total_vram_gb >= minimum_gb


def probe_gpu(index: int = 0) -> GPUStatus:
    command = ["nvidia-smi", f"--id={index}", "--query-gpu=memory.total,memory.free", "--format=csv,noheader,nounits"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        if result.returncode != 0:
            return GPUStatus(False, index, 0.0, 0.0, result.stderr.strip() or "nvidia-smi failed")
        total_mb, free_mb = (float(part.strip()) for part in result.stdout.strip().split(",")[:2])
        return GPUStatus(True, index, total_mb / 1024, free_mb / 1024)
    except (FileNotFoundError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return GPUStatus(False, index, 0.0, 0.0, str(exc))
