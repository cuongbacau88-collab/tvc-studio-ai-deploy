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
            "id": self.id, "operation": self.request.operation,
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

    def add(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at)

