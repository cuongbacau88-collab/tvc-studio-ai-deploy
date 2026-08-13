from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from tvc_api.adapters.base import Readiness
from tvc_api.config import Settings
from tvc_api.gpu import GPUStatus
from tvc_api.main import create_app
from tests.helpers import request


class ReadyAdapter:
    def readiness(self):
        return Readiness(True, {"test": True})

    def validate(self, inputs, parameters):
        return None

    async def run(self, inputs, parameters, output_dir):
        return {}


def settings(root: Path) -> Settings:
    return replace(Settings.from_env(root), service_token="test-token",
                   upload_dir=root / "uploads", output_dir=root / "outputs",
                   max_upload_mb=1)


def auth(owner="owner-1", token="test-token", **extra):
    values = {"authorization": f"Bearer {token}", "x-owner-id": owner}
    values.update(extra)
    return values


def payload(owner="owner-1", client="client-1"):
    return {"owner_id": owner, "client_job_id": client, "operation": "prompt-video",
            "model_id": "wan22-animate", "inputs": {"prompt": "test"}, "parameters": {}}


class Phase4ATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        source_config = Path(__file__).parents[1] / "configs" / "models.yaml"
        (root / "configs").mkdir()
        (root / "configs" / "models.yaml").write_bytes(source_config.read_bytes())
        self.app = create_app(settings(root), lambda index: GPUStatus(True, index, 24.0, 24.0))
        self.app.context.adapters["wan22-animate"] = ReadyAdapter()

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_and_invalid_authentication(self):
        status, body = request(self.app, "GET", "/v1/jobs", headers={})
        self.assertEqual(401, status)
        self.assertEqual("unauthorized", body["error"]["code"])
        status, _ = request(self.app, "GET", "/v1/jobs", headers=auth(token="wrong"))
        self.assertEqual(401, status)

    def test_idempotency_and_duplicate_queue_prevention(self):
        first_status, first = request(self.app, "POST", "/v1/jobs", payload())
        second_status, second = request(self.app, "POST", "/v1/jobs", payload())
        self.assertEqual(202, first_status)
        self.assertEqual(200, second_status)
        self.assertEqual(first["id"], second["id"])
        self.assertTrue(second["duplicate"])
        snapshot = self.app.context.queue.snapshot()
        self.assertEqual(1, len(snapshot["queued"]))

    def test_ownership_isolation(self):
        _, job = request(self.app, "POST", "/v1/jobs", payload())
        status, _ = request(self.app, "GET", f"/v1/jobs/{job['id']}", headers=auth("owner-2"))
        self.assertEqual(404, status)
        status, _ = request(self.app, "DELETE", f"/v1/jobs/{job['id']}", headers=auth("owner-2"))
        self.assertEqual(404, status)
        status, body = request(self.app, "POST", "/v1/jobs", payload("owner-2"), headers=auth("owner-1"))
        self.assertEqual(403, status)
        self.assertEqual("owner_mismatch", body["error"]["code"])

    def test_safe_upload_and_traversal_rejection(self):
        headers = auth(**{"x-filename": "photo.png", "content-type": "image/png"})
        status, body = request(self.app, "POST", "/v1/uploads", b"png-data", headers)
        self.assertEqual(201, status)
        upload = self.app.context.uploads.get_owned(body["upload"]["id"], "owner-1")
        self.assertEqual(".png", upload.path.suffix)
        self.assertNotEqual("photo.png", upload.path.name)
        self.assertEqual(self.app.context.settings.upload_dir.resolve(), upload.path.parent)
        audio_headers = auth(**{"x-filename": "voice.wav", "content-type": "audio/wav"})
        status, audio = request(self.app, "POST", "/v1/uploads", b"audio", audio_headers)
        self.assertEqual(201, status)
        self.assertEqual("audio/wav", audio["upload"]["content_type"])
        bad = auth(**{"x-filename": "../escape.png", "content-type": "image/png"})
        status, body = request(self.app, "POST", "/v1/uploads", b"x", bad)
        self.assertEqual(422, status)
        self.assertEqual("invalid_filename", body["error"]["code"])
        windows_bad = auth(**{"x-filename": "..\\escape.png", "content-type": "image/png"})
        status, _ = request(self.app, "POST", "/v1/uploads", b"x", windows_bad)
        self.assertEqual(422, status)

    def test_upload_type_size_and_owner(self):
        bad_type = auth(**{"x-filename": "payload.exe", "content-type": "application/octet-stream"})
        status, _ = request(self.app, "POST", "/v1/uploads", b"x", bad_type)
        self.assertEqual(415, status)
        headers = auth(**{"x-filename": "clip.mp4", "content-type": "video/mp4"})
        status, body = request(self.app, "POST", "/v1/uploads", b"x" * (1024 * 1024 + 1), headers)
        self.assertEqual(413, status)
        status, uploaded = request(self.app, "POST", "/v1/uploads", b"video", headers)
        self.assertEqual(201, status)
        with self.assertRaises(Exception):
            self.app.context.uploads.get_owned(uploaded["upload"]["id"], "owner-2")

    def test_output_authorization_and_traversal(self):
        _, job = request(self.app, "POST", "/v1/jobs", payload())
        stored = self.app.context.store.get(job["id"])
        stored.status = "succeeded"
        output_dir = self.app.context.settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        result = output_dir / "result.mp4"
        result.write_bytes(b"video")
        stored.result = {"output_path": str(result)}
        status, body = request(self.app, "GET", f"/v1/jobs/{job['id']}/output")
        self.assertEqual(200, status)
        self.assertEqual(b"video", body)
        status, _ = request(self.app, "GET", f"/v1/jobs/{job['id']}/output", headers=auth("owner-2"))
        self.assertEqual(404, status)
        outside = Path(self.temp.name) / "outside.mp4"
        outside.write_bytes(b"secret")
        stored.result = {"output_path": str(outside)}
        status, body = request(self.app, "GET", f"/v1/jobs/{job['id']}/output")
        self.assertEqual(404, status)
        self.assertEqual("output_not_found", body["error"]["code"])


if __name__ == "__main__":
    unittest.main()
