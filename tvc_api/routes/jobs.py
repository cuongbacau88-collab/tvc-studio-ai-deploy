from dataclasses import replace
from pathlib import Path
from typing import Any

from ..context import AppContext
from ..errors import APIError, UNAVAILABLE_GPU
from ..jobs import Job
from ..schemas import JobRequest


def _owned(context: AppContext, job_id: str, owner_id: str) -> Job:
    job = context.store.get(job_id)
    if job is None or job.request.owner_id != owner_id:
        raise APIError("job_not_found", "Job not found", 404)
    return job


def _resolve_uploads(context: AppContext, owner_id: str, value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"upload_id"}:
        upload_id = value["upload_id"]
        if not isinstance(upload_id, str) or not upload_id:
            raise APIError("validation_error", "upload_id must be a non-empty string", 422)
        return str(context.uploads.get_owned(upload_id, owner_id).path)
    if isinstance(value, dict):
        return {key: _resolve_uploads(context, owner_id, item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_uploads(context, owner_id, item) for item in value]
    return value


async def submit(context: AppContext, body: object, owner_id: str) -> tuple[int, dict[str, object]]:
    request = JobRequest.parse(body)
    if request.owner_id != owner_id:
        raise APIError("owner_mismatch", "Job owner does not match authenticated owner", 403)
    existing = context.store.get_client_job(owner_id, request.client_job_id)
    if existing is not None:
        payload = existing.public()
        payload["duplicate"] = True
        return 200, payload
    request = replace(request, inputs=_resolve_uploads(context, owner_id, request.inputs))
    spec = context.registry.get(request.model_id)
    adapter = context.adapters.get(request.model_id)
    if adapter is None:
        raise APIError("installed_not_ready", "Model adapter is not configured", 503)
    validator = getattr(adapter, "validate", None)
    if validator is not None:
        validator(request.inputs, request.parameters)
    gpu = context.gpu_probe(context.settings.gpu_index)
    if not gpu.sufficient(float(spec.data["min_vram_gb"])):
        raise APIError(UNAVAILABLE_GPU, "GPU unavailable or below model minimum VRAM", 503)
    if not adapter.readiness().ready:
        raise APIError("installed_not_ready", "Model has not passed all readiness checks", 503)
    job, created = await context.queue.submit(Job(request))
    payload = job.public()
    payload["duplicate"] = not created
    return (202 if created else 200), payload


def list_jobs(context: AppContext, owner_id: str) -> tuple[int, dict[str, object]]:
    return 200, {"jobs": [job.public() for job in context.store.list()
                          if job.request.owner_id == owner_id]}


def get_job(context: AppContext, job_id: str, owner_id: str, result: bool = False) -> tuple[int, dict[str, object]]:
    job = _owned(context, job_id, owner_id)
    payload = job.public()
    if result:
        metadata: dict[str, object] = {"available": False}
        try:
            path, filename = output_file(context, job_id, owner_id)
            metadata = {"available": True, "filename": filename, "size": path.stat().st_size}
        except APIError:
            pass
        payload["result"] = metadata
    return 200, payload


def cancel_job(context: AppContext, job_id: str, owner_id: str) -> tuple[int, dict[str, object]]:
    job = _owned(context, job_id, owner_id)
    if job.status == "cancelled":
        return 200, job.public()
    if not context.queue.cancel(job_id):
        raise APIError("job_not_cancellable", "Only queued jobs can be cancelled", 409)
    return 200, job.public()


def output_file(context: AppContext, job_id: str, owner_id: str) -> tuple[Path, str]:
    job = _owned(context, job_id, owner_id)
    if job.status != "succeeded" or not isinstance(job.result, dict):
        raise APIError("not_ready", "Job output is not ready", 404)
    raw_path = next((job.result.get(key) for key in ("output_path", "path", "file")
                     if isinstance(job.result.get(key), str)), None)
    if raw_path is None:
        raise APIError("not_ready", "Job output is not ready", 404)
    root = context.settings.output_dir.resolve()
    candidate = Path(raw_path)
    path = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if root not in path.parents or not path.is_file():
        raise APIError("output_not_found", "Job output is unavailable", 404)
    return path, path.name
