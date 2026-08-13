from ..context import AppContext


def get_queue(context: AppContext, owner_id: str) -> tuple[int, dict[str, object]]:
    snapshot = context.queue.snapshot()
    snapshot["queued"] = [job for job in snapshot["queued"] if job["owner_id"] == owner_id]
    if snapshot["active_job_id"]:
        active = context.store.get(str(snapshot["active_job_id"]))
        if active is None or active.request.owner_id != owner_id:
            snapshot["active_job_id"] = None
    return 200, snapshot
