import asyncio
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import download_models
from model_manifest import validate, workflow_model_filenames


ROOT = Path(__file__).resolve().parents[1]


class Response(io.BytesIO):
    status = 206

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ModelManifestTests(unittest.TestCase):
    def test_required_models_have_verified_sources_and_exact_workflow_names(self):
        manifest, errors = validate(ROOT)
        self.assertEqual([], errors)
        models = manifest["models"]
        self.assertEqual(workflow_model_filenames(ROOT), {item["filename"] for item in models})
        self.assertTrue(all(item["source_url"] and item["source_repo"] for item in models if item["required"]))
        self.assertTrue(all(len(item["sha256"]) == 64 for item in models))

    def test_preflight_cli_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "preflight-models.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn('"ready": true', result.stdout)

    def test_dry_run_does_not_create_or_download(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ComfyUI"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "download_models.py"),
                 "--comfyui-root", str(target), "--dry-run"],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(target.exists())
            self.assertIn("no files downloaded", result.stdout)

    def test_unresolved_source_fails_before_creating_target(self):
        manifest = {
            "models": [{
                "filename": "missing.safetensors", "required": True,
                "source_status": "unresolved", "source_url": None,
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ComfyUI"
            argv = ["download_models.py", "--comfyui-root", str(target)]
            with (
                patch.object(download_models, "validate", return_value=(manifest, [])),
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(2, download_models.main())
            self.assertFalse(target.exists())


class DownloaderTests(unittest.TestCase):
    def test_resume_uses_part_file_then_atomic_rename_and_checksum(self):
        content = b"complete-model"
        checksum = hashlib.sha256(content).hexdigest()
        model = {
            "filename": "model.bin",
            "source_url": "https://huggingface.co/org/repo/resolve/main/model.bin",
            "sha256": checksum,
        }
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "model.bin"
            partial = Path(str(destination) + ".part")
            partial.write_bytes(content[:8])
            with patch.object(download_models, "urlopen",
                              return_value=Response(content[8:])) as mocked:
                download_models.download_once(model, destination)
            self.assertEqual(content, destination.read_bytes())
            self.assertFalse(partial.exists())
            self.assertEqual("bytes=8-", mocked.call_args.args[0].headers["Range"])

    def test_valid_existing_file_is_skipped_without_network(self):
        content = b"valid"
        model = {
            "filename": "model.bin", "comfyui_subdir": "models/vae",
            "source_url": "https://huggingface.co/org/repo/resolve/main/model.bin",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "models" / "vae" / "model.bin"
            destination.parent.mkdir(parents=True)
            destination.write_bytes(content)
            with patch.object(download_models, "urlopen") as mocked:
                download_models.download(model, root, 2)
            mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
