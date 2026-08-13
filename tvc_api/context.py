"""Application-owned Phase 3 services.

Exactly one context, queue, and worker are created per API process. Deployment must
use one server worker so GPU work cannot split across process-local queues.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .adapters import build_adapters
from .config import Settings
from .gpu import GPUStatus, probe_gpu
from .jobs import JobStore
from .queue import SequentialGPUQueue
from .registry import ModelRegistry
from .worker import GPUWorker
from .uploads import UploadStore


@dataclass
class AppContext:
    settings: Settings
    registry: ModelRegistry
    store: JobStore
    queue: SequentialGPUQueue
    worker: GPUWorker
    gpu_probe: Callable[[int], GPUStatus]
    uploads: UploadStore

    @classmethod
    def build(cls, settings: Settings, gpu_probe_fn: Callable[[int], GPUStatus] = probe_gpu) -> "AppContext":
        if not settings.sequential_gpu_queue:
            raise ValueError("SEQUENTIAL_GPU_QUEUE must remain enabled")
        registry = ModelRegistry(settings.models_config)
        store = JobStore()
        queue = SequentialGPUQueue(store, settings.max_queue_size)
        adapters = build_adapters(registry, settings.repo_root)
        worker = GPUWorker(queue, adapters, settings.output_dir, settings.gpu_task_timeout_seconds)
        uploads = UploadStore(settings.upload_dir, settings.max_upload_mb)
        context = cls(settings, registry, store, queue, worker, gpu_probe_fn, uploads)
        context.adapters = adapters
        return context

