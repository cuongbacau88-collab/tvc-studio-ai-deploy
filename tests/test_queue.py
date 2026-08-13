import unittest

from tvc_api.jobs import Job, JobStore
from tvc_api.queue import SequentialGPUQueue
from tvc_api.schemas import JobRequest


def make_job(operation: str, model: str) -> Job:
    return Job(JobRequest(operation, model, {"input": "test"}, {}))


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_priority_order_and_single_active_slot(self) -> None:
        queue = SequentialGPUQueue(JobStore())
        low = make_job("image-upscale-restoration", "realesrgan")
        medium = make_job("scene-replacement", "qwen-image-edit")
        high = make_job("motion-transfer-video", "wan22-animate")
        await queue.submit(low)
        await queue.submit(medium)
        await queue.submit(high)
        self.assertIs(await queue.next(), high)
        self.assertEqual(high.id, queue.active_job_id)
        queue.done()
        self.assertIs(await queue.next(), medium)
        queue.done()
        self.assertIs(await queue.next(), low)
        queue.done()
        self.assertIsNone(queue.active_job_id)

    async def test_equal_priority_is_fifo(self) -> None:
        queue = SequentialGPUQueue(JobStore())
        first = make_job("prompt-video", "wan22-animate")
        second = make_job("prompt-video", "scail2")
        await queue.submit(first)
        await queue.submit(second)
        self.assertIs(await queue.next(), first)
        queue.done()
        self.assertIs(await queue.next(), second)
        queue.done()


if __name__ == "__main__":
    unittest.main()

