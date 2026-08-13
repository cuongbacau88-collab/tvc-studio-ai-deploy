from pathlib import Path
import tempfile
import unittest

from tvc_api.errors import APIError
from tvc_api.registry import ModelRegistry


class RegistryTests(unittest.TestCase):
    def test_loads_all_existing_models(self) -> None:
        registry = ModelRegistry(Path("configs/models.yaml"))
        self.assertEqual(11, len(registry.models))
        self.assertIn("scail2", registry.models)
        self.assertIn("wan22-animate", registry.models)
        self.assertIn("wan22_ti2v", registry.models)
        self.assertNotIn("wan22-ti2v", registry.models)
        h3 = registry.get("minimax_h3").data
        self.assertEqual(["text_to_video", "image_to_video", "first_last_frame_to_video", "reference_to_video"], h3["task_types"])
        self.assertEqual("hosted_api_optional", h3["capabilities"]["h3_context_ir"]["mode"])
        self.assertEqual("hosted_api_optional", h3["capabilities"]["h3_regenerate_2k"]["mode"])

    def test_rejects_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "models.yaml"
            config.write_text("models:\n  broken:\n    enabled: true\n", encoding="utf-8")
            with self.assertRaises(APIError) as raised:
                ModelRegistry(config)
            self.assertEqual("registry_invalid", raised.exception.code)


if __name__ == "__main__":
    unittest.main()

