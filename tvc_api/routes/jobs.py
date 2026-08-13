from ..context import AppContext
from ..errors import APIError, UNAVAILABLE_GPU
from ..jobs import Job
from ..schemas import JobRequest


async def submit(context: AppContext, body: object) -> tuple[int, dict[str, object]]:
    request = JobRequest.parse(body)
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
    job = Job(request)
    await context.queue.submit(job)
    return 202, job.public()


def list_jobs(context: AppContext) -> tuple[int, dict[str, object]]:
    return 200, {"jobs": [job.public() for job in context.store.list()]}


def get_job(context: AppContext, job_id: str, result: bool = False) -> tuple[int, dict[str, object]]:
    job = context.store.get(job_id)
    if job is None:
        raise APIError("job_not_found", "Job not found", 404)
    return 200, job.public(include_result=result)


def cancel_job(context: AppContext, job_id: str) -> tuple[int, dict[str, object]]:
    job = context.store.get(job_id)
    if job is None:
        raise APIError("job_not_found", "Job not found", 404)
    if not context.queue.cancel(job_id):
        raise APIError("job_not_cancellable", "Only queued jobs can be cancelled", 409)
    return 200, job.public()

