import asyncio
from pathlib import Path
import unittest

from tvc_api.adapters.base import ModelAdapter, Readiness
from tvc_api.jobs import Job, JobStore
from tvc_api.queue import SequentialGPUQueue
from tvc_api.registry import ModelSpec
from tvc_api.schemas import JobRequest
from tvc_api.worker import GPUWorker


class FakeAdapter(ModelAdapter):
    active = 0
    maximum_active = 0

    def entrypoint_ready(self) -> bool:
        return True

    def readiness(self) -> Readiness:
        return Readiness(True, {"fake": True})

    async def run(self, inputs, parameters, output_dir):
        type(self).active += 1
        type(self).maximum_active = max(type(self).maximum_active, type(self).active)
        await asyncio.sleep(0.01)
        type(self).active -= 1
        return {"ok": True}


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_never_runs_more_than_one_gpu_task(self) -> None:
        FakeAdapter.active = 0
        FakeAdapter.maximum_active = 0
        store = JobStore()
        queue = SequentialGPUQueue(store)
        adapter = FakeAdapter(ModelSpec("wan22-animate", {}), Path("."))
        worker = GPUWorker(queue, {"wan22-animate": adapter}, Path("outputs"), 1)
        jobs = [Job(JobRequest("prompt-video", "wan22-animate", {"prompt": str(i)}, {})) for i in range(3)]
        for job in jobs:
            await queue.submit(job)
        worker.start()
        for _ in range(100):
            if all(job.status == "succeeded" for job in jobs):
                break
            await asyncio.sleep(0.005)
        await worker.stop()
        self.assertTrue(all(job.status == "succeeded" for job in jobs))
        self.assertEqual(1, FakeAdapter.maximum_active)


if __name__ == "__main__":
    unittest.main()
