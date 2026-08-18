"""The sole consumer of the shared GPU queue."""

from __future__ import annotations

import asyncio
from pathlib import Path

from .adapters.base import ModelAdapter
from .errors import APIError
from .jobs import now
from .queue import SequentialGPUQueue


class GPUWorker:
    def __init__(self, queue: SequentialGPUQueue, adapters: dict[str, ModelAdapter], output_root: Path, timeout_seconds: int = 180) -> None:
        self.queue = queue
        self.adapters = adapters
        self.output_root = output_root
        self.timeout_seconds = timeout_seconds or 180
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run_forever(), name="single-gpu-worker")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def run_forever(self) -> None:
        while True:
            job = await self.queue.next()
            job.status = "running"
            job.started_at = now()
            adapter = self.adapters.get(job.request.model_id)
            if adapter is None:
                job.status = "failed"
                job.error = {"code": "model_not_found", "message": f"Model adapter {job.request.model_id} is not configured"}
                job.finished_at = now()
                self.queue.done()
                continue
            try:
                output_dir = self.output_root / job.id
                job.result = await asyncio.wait_for(
                    adapter.run(job.request.inputs, job.request.parameters, output_dir),
                    timeout=self.timeout_seconds,
                )
                job.status = "succeeded"
            except asyncio.TimeoutError:
                job.status = "failed"
                job.error = {
                    "code": "inference_timeout",
                    "message": f"GPU task exceeded maximum timeout of {self.timeout_seconds}s (3 minutes). GPU queue has been freed.",
                }
            except APIError as exc:
                job.status = "failed"
                job.error = exc.as_dict()["error"]
            except Exception as exc:
                job.status = "failed"
                job.error = {"code": "inference_crash", "message": f"Model task execution failed: {exc}"}
            finally:
                job.finished_at = now()
                self.queue.done()
