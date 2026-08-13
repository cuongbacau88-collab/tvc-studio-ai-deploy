"""In-memory job records for the single-process Phase 3 API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .schemas import JobRequest


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    request: JobRequest
    id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "queued"
    created_at: str = field(default_factory=now)
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def public(self, include_result: bool = False) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id, "owner_id": self.request.owner_id,
            "client_job_id": self.request.client_job_id, "operation": self.request.operation,
            "model_id": self.request.model_id, "priority": self.request.priority,
            "status": self.status, "created_at": self.created_at,
            "started_at": self.started_at, "finished_at": self.finished_at,
            "error": self.error,
        }
        if include_result:
            value["result"] = self.result
        return value


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._client_jobs: dict[tuple[str, str], str] = {}

    def add(self, job: Job) -> tuple[Job, bool]:
        key = (job.request.owner_id, job.request.client_job_id)
        existing_id = self._client_jobs.get(key)
        if existing_id is not None:
            return self._jobs[existing_id], False
        self._jobs[job.id] = job
        self._client_jobs[key] = job.id
        return job, True

    def remove(self, job: Job) -> None:
        self._jobs.pop(job.id, None)
        self._client_jobs.pop((job.request.owner_id, job.request.client_job_id), None)

    def get_client_job(self, owner_id: str, client_job_id: str) -> Job | None:
        job_id = self._client_jobs.get((owner_id, client_job_id))
        return self._jobs.get(job_id) if job_id else None

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at)

