import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tvc_api.adapters.comfyui import ComfyWorkflowAdapter
from tvc_api.registry import ModelRegistry
from tvc_api.workflows import MODEL_INPUTS, WorkflowRegistry


ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.registry = WorkflowRegistry(ROOT)

    def test_all_seven_workflows_pass_static_preflight(self):
        result = self.registry.validate_all()
        self.assertTrue(result["ready"], result["errors"])
        self.assertEqual(7, len(result["checked"]))

    def test_exact_upload_and_output_nodes(self):
        cases = [
            ("image-upscale-restoration", "realesrgan", {}, {"image": "up.png"}, "6", "10", "image"),
            ("clothes-replacement", "fashn-vton", {}, {"image": "person.png", "garment_image": "dress.png"}, "132", "133", "image"),
            ("scene-replacement", "qwen-image-edit", {}, {"image": "person.png", "prompt": "beach"}, "76", "9", "image"),
            ("motion-transfer-video", "scail2", {}, {"image": "person.png", "video": "motion.mp4"}, "30", "271", "video"),
            ("image_to_video", "minimax_h3", {"task_type": "image_to_video"}, {"image": "ref.png"}, "114", "92", "video"),
            ("first_last_frame_to_video", "minimax_h3", {"task_type": "first_last_frame_to_video"}, {"first_frame": "first.png", "last_frame": "last.png"}, "15", "26", "video"),
        ]
        for operation, model, parameters, inputs, upload_node, output_node, output_type in cases:
            with self.subTest(operation=operation):
                workflow, spec = self.registry.bind(operation, model, inputs, parameters)
                self.assertEqual(output_node, spec["outputs"][0]["node_id"])
                self.assertEqual(output_type, spec["outputs"][0]["type"])
                self.assertIn(upload_node, workflow)

    def test_h3_duration_defaults_to_fifteen_seconds(self):
        i2v, _ = self.registry.bind(
            "image_to_video", "minimax_h3", {"image": "ref.png"},
            {"task_type": "image_to_video"},
        )
        first_last, _ = self.registry.bind(
            "first_last_frame_to_video", "minimax_h3",
            {"first_frame": "first.png", "last_frame": "last.png"},
            {"task_type": "first_last_frame_to_video"},
        )
        self.assertEqual(15, i2v["105:111"]["inputs"]["value"])
        self.assertEqual(15, first_last["28"]["inputs"]["model.duration"])

    def test_motion_maps_both_segments_and_final_output(self):
        workflow, spec = self.registry.bind(
            "motion-transfer-video", "scail2",
            {"image": "person.png", "video": "motion.mp4", "prompt": "dance"},
            {"seed": 99, "width": 512, "height": 896},
        )
        self.assertEqual("dance", workflow["213:3"]["inputs"]["text"])
        self.assertEqual("dance", workflow["262:258"]["inputs"]["text"])
        self.assertEqual(99, workflow["213:19"]["inputs"]["noise_seed"])
        self.assertEqual(99, workflow["262:227"]["inputs"]["noise_seed"])
        self.assertEqual("271", spec["outputs"][0]["node_id"])

    def test_backup_is_never_default(self):
        manifest = self.registry.manifest["workflows"]
        defaults = [key for key, value in manifest.items() if value.get("default")]
        self.assertNotIn("backup_wan22_fun_inpaint", defaults)
        self.assertEqual("backup_test", manifest["backup_wan22_fun_inpaint"]["service"])

    def test_model_manifest_exactly_declares_all_json_model_filenames(self):
        found = set()
        for spec in self.registry.manifest["workflows"].values():
            workflow = self.registry.load_workflow(spec)
            for node in workflow.values():
                for field in MODEL_INPUTS:
                    value = node.get("inputs", {}).get(field)
                    if isinstance(value, str):
                        found.add(value)
        declared = {item["filename"] for item in self.registry.model_manifest["models"]}
        self.assertEqual(found, declared)


class FakeComfyAdapter(ComfyWorkflowAdapter):
    uploaded = {}

    def _upload(self, path):
        self.uploaded[path.name] = f"remote/{path.name}"
        return self.uploaded[path.name]

    def _submit_prompt(self, workflow, partner_key=""):
        self.submitted = workflow
        self.partner_key = partner_key
        return "prompt-1"

    def _request(self, path, data=None, headers=None):
        if path == "/object_info/MinimaxHailuo03FirstLastFrameNode":
            return json.dumps({"MinimaxHailuo03FirstLastFrameNode": {}}).encode()
        return super()._request(path, data, headers)

    def _wait_for_output(self, prompt_id, spec):
        self.asserted_output = spec["outputs"][0]
        return {"filename": "result.mp4", "subfolder": "", "type": "output"}

    def _view(self, output):
        return b"rendered-video"


class ComfyAdapterTests(unittest.TestCase):
    def test_worker_adapter_uploads_and_binds_first_last_files(self):
        model = ModelRegistry(ROOT / "configs" / "models.yaml").get("minimax_h3")
        with patch.dict(os.environ, {
            "COMFYUI_URL": "http://comfy.invalid",
            "API_KEY_COMFY_ORG": "test-placeholder",
        }):
            adapter = FakeComfyAdapter(model, ROOT)
            with tempfile.TemporaryDirectory() as directory:
                directory = Path(directory)
                first, last = directory / "first.png", directory / "last.png"
                first.write_bytes(b"first")
                last.write_bytes(b"last")
                output = asyncio.run(adapter.run(
                    {"first_frame": str(first), "last_frame": str(last), "prompt": "transition"},
                    {"task_type": "first_last_frame_to_video"},
                    directory / "out",
                ))
        self.assertEqual("remote/first.png", adapter.submitted["15"]["inputs"]["image"])
        self.assertEqual("remote/last.png", adapter.submitted["16"]["inputs"]["image"])
        self.assertEqual("transition", adapter.submitted["28"]["inputs"]["model.prompt"])
        self.assertEqual(15, adapter.submitted["28"]["inputs"]["model.duration"])
        self.assertEqual("test-placeholder", adapter.partner_key)
        self.assertEqual("26", adapter.asserted_output["node_id"])
        self.assertEqual("video", output["output_type"])

    def test_reference_image_alias_maps_to_h3_loadimage(self):
        model = ModelRegistry(ROOT / "configs" / "models.yaml").get("minimax_h3")
        with patch.dict(os.environ, {"COMFYUI_URL": "http://comfy.invalid"}):
            adapter = FakeComfyAdapter(model, ROOT)
        normalized = adapter._normalize_inputs(
            "reference_to_video", {"reference_images": ["/tmp/reference.png"]}
        )
        workflow, _ = adapter.workflows.bind(
            "reference_to_video", "minimax_h3", normalized,
            {"task_type": "reference_to_video"},
        )
        self.assertEqual("/tmp/reference.png", workflow["114"]["inputs"]["image"])


if __name__ == "__main__":
    unittest.main()
