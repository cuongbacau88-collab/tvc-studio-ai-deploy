from pathlib import Path
import tempfile
import unittest

from tvc_api.adapters.minimax_h3 import MiniMaxH3Adapter
from tvc_api.adapters.wan22_ti2v import Wan22TI2VAdapter
from tvc_api.config import Settings
from tvc_api.errors import APIError
from tvc_api.gpu import GPUStatus
from tvc_api.jobs import Job, JobStore
from tvc_api.main import create_app
from tvc_api.queue import SequentialGPUQueue
from tvc_api.registry import ModelSpec
from tvc_api.schemas import JobRequest
from tests.helpers import request


class VideoIntegrationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h3 = MiniMaxH3Adapter(ModelSpec("minimax_h3", {}), Path("."))
        self.wan = Wan22TI2VAdapter(ModelSpec("wan22_ti2v", {}), Path("."))

    def test_fl2va_supports_prompt_only_and_frame_combinations(self) -> None:
        base = {"variant": "fl2va", "aspect_ratio": "9:16", "duration_seconds": 4}
        self.h3.validate({"prompt": "video"}, {**base, "task_type": "text_to_video"})
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            last = Path(directory) / "last.png"
            first.touch()
            last.touch()
            for inputs in ({"first_frame": str(first)}, {"last_frame": str(last)},
                           {"first_frame": str(first), "last_frame": str(last)}):
                self.h3.validate(inputs, {**base, "task_type": "first_last_frame_to_video"})

    def test_ref2va_accepts_mixed_multimodal_references(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("image.png", "video.mp4", "audio.wav")]
            for path in paths:
                path.touch()
            self.h3.validate(
                {"reference_images": [str(paths[0])], "reference_videos": str(paths[1]),
                 "reference_audio": [str(paths[2])]},
                {"variant": "ref2va", "task_type": "reference_to_video",
                 "aspect_ratio": "16:9", "duration_seconds": 15},
            )

    def test_h3_rejects_duration_ratio_missing_files_and_empty_references(self) -> None:
        valid = {"variant": "fl2va", "task_type": "text_to_video", "aspect_ratio": "9:16"}
        with self.assertRaises(APIError):
            self.h3.validate({"prompt": "x"}, {**valid, "duration_seconds": 3})
        with self.assertRaises(APIError):
            self.h3.validate({"prompt": "x"}, {**valid, "duration_seconds": 4, "aspect_ratio": "1:1"})
        with self.assertRaises(APIError) as missing:
            self.h3.validate({"first_frame": "/missing/input.png"},
                             {**valid, "task_type": "image_to_video", "duration_seconds": 4})
        self.assertEqual("input_file_not_found", missing.exception.code)
        with self.assertRaises(APIError):
            self.h3.validate({}, {"variant": "ref2va", "task_type": "reference_to_video",
                                  "aspect_ratio": "9:16", "duration_seconds": 4})

    def test_wan_ti2v_validates_prompt_and_image(self) -> None:
        self.wan.validate({"prompt": "video"}, {"task_type": "text_to_video"})
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "input.png"
            image.touch()
            self.wan.validate({"image": str(image)}, {"task_type": "image_to_video"})
        with self.assertRaises(APIError) as missing:
            self.wan.validate({"image": "/missing/input.png"}, {"task_type": "image_to_video"})
        self.assertEqual("input_file_not_found", missing.exception.code)


class VideoQueueRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_h3_and_wan_use_shared_priority_queue(self) -> None:
        queue = SequentialGPUQueue(JobStore())
        wan = Job(JobRequest("owner", "wan", "text_to_video", "wan22_ti2v", {"prompt": "x"}, {"task_type": "text_to_video"}))
        h3 = Job(JobRequest("owner", "h3", "reference_to_video", "minimax_h3", {"reference_images": ["x"]}, {"task_type": "reference_to_video"}))
        await queue.submit(wan)
        await queue.submit(h3)
        self.assertIs(await queue.next(), h3)
        queue.done()
        self.assertIs(await queue.next(), wan)
        queue.done()


class MiniMaxHealthTests(unittest.TestCase):
    def test_installed_not_ready_on_sufficient_gpu_without_verified_entrypoint(self) -> None:
        app = create_app(Settings.from_env(), lambda index: GPUStatus(True, index, 24.0, 24.0))
        status, body = request(app, "GET", "/health/models/minimax_h3")
        self.assertEqual(200, status)
        self.assertEqual("installed_not_ready", body["status"])
        self.assertFalse(body["ready"])


if __name__ == "__main__":
    unittest.main()
