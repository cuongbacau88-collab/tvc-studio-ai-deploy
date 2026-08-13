import unittest

from tvc_api.config import Settings
from tvc_api.gpu import GPUStatus
from tvc_api.main import create_app
from tests.helpers import request


def no_gpu(index: int) -> GPUStatus:
    return GPUStatus(False, index, 0.0, 0.0, "test: no GPU")


class HealthEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(Settings.from_env(), no_gpu)

    def test_liveness(self) -> None:
        status, body = request(self.app, "GET", "/health/live")
        self.assertEqual(200, status)
        self.assertEqual("live", body["status"])

    def test_readiness_is_truthful_about_gpu_and_queue(self) -> None:
        status, body = request(self.app, "GET", "/health/ready")
        self.assertEqual(200, status)
        self.assertFalse(body["gpu"]["available"])
        self.assertEqual(1, body["queue"]["max_concurrent_gpu_tasks"])

    def test_models_are_not_ready_without_verification(self) -> None:
        status, body = request(self.app, "GET", "/v1/models")
        self.assertEqual(200, status)
        self.assertTrue(body["models"])
        self.assertTrue(all(not model["ready"] for model in body["models"]))

    def test_api_models_uses_canonical_wan_ti2v_id(self) -> None:
        status, body = request(self.app, "GET", "/api/models")
        self.assertEqual(200, status)
        ids = [model["id"] for model in body["models"]]
        self.assertEqual(1, ids.count("wan22_ti2v"))
        self.assertNotIn("wan22-ti2v", ids)

    def test_insufficient_gpu_is_stable_api_error(self) -> None:
        status, body = request(self.app, "POST", "/v1/jobs", {
            "operation": "prompt-video", "model_id": "wan22-animate",
            "inputs": {"prompt": "unit test"}, "parameters": {},
        })
        self.assertEqual(503, status)
        self.assertEqual("unavailable_insufficient_gpu", body["error"]["code"])

    def test_minimax_health_reports_insufficient_gpu(self) -> None:
        status, body = request(self.app, "GET", "/health/models/minimax_h3")
        self.assertEqual(200, status)
        self.assertEqual("minimax_h3", body["id"])
        self.assertEqual("unavailable_insufficient_gpu", body["status"])
        self.assertFalse(body["ready"])


if __name__ == "__main__":
    unittest.main()
