"""One shared, stable, sequential priority queue for all GPU work."""

from __future__ import annotations

import asyncio
from itertools import count

from .errors import APIError
from .jobs import Job, JobStore, now


class SequentialGPUQueue:
    def __init__(self, store: JobStore, max_size: int = 100) -> None:
        self.store = store
        self._queue: asyncio.PriorityQueue[tuple[int, int, str]] = asyncio.PriorityQueue(max_size)
        self._sequence = count()
        self.active_job_id: str | None = None

    async def submit(self, job: Job) -> tuple[Job, bool]:
        stored, created = self.store.add(job)
        if not created:
            return stored, False
        if self._queue.full():
            self.store.remove(job)
            raise APIError("queue_full", "GPU task queue is full", 503)
        await self._queue.put((-job.request.priority, next(self._sequence), job.id))
        return job, True

    async def next(self) -> Job:
        while True:
            _, _, job_id = await self._queue.get()
            job = self.store.get(job_id)
            if job is not None and job.status == "queued":
                self.active_job_id = job.id
                return job
            self._queue.task_done()

    def done(self) -> None:
        self.active_job_id = None
        self._queue.task_done()

    def cancel(self, job_id: str) -> bool:
        job = self.store.get(job_id)
        if job is None or job.status != "queued":
            return False
        job.status = "cancelled"
        job.finished_at = now()
        return True

    def snapshot(self) -> dict[str, object]:
        queued = [job for job in self.store.list() if job.status == "queued"]
        queued.sort(key=lambda job: (-job.request.priority, job.created_at))
        return {"mode": "sequential", "max_concurrent_gpu_tasks": 1,
                "active_job_id": self.active_job_id,
                "queued": [job.public() for job in queued]}

