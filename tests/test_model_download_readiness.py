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
from model_disk import CHECKSUM_FAILED, COMPLETE, MISSING, PARTIAL, disk_summary
from model_manifest import validate, workflow_model_filenames


ROOT = Path(__file__).resolve().parents[1]


class Response(io.BytesIO):
    status = 206
    headers = {}

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

    def test_empty_model_directory_is_not_ready_and_has_zero_of_fifteen(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "preflight-models.py"),
                 "--comfyui-root", directory],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
        self.assertEqual(1, result.returncode, result.stderr + result.stdout)
        payload = __import__("json").loads(result.stdout)
        self.assertFalse(payload["ready"])
        self.assertEqual(15, payload["required_total"])
        self.assertEqual(0, payload["required_complete"])
        self.assertEqual(15, payload["missing"])

    def test_dry_run_does_not_create_or_download(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ComfyUI"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "download_models.py"),
                 "--comfyui-root", str(target), "--dry-run"],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertFalse(target.exists())
            self.assertIn("DRY RUN: no files downloaded", result.stdout)
            self.assertIn("READY: false", result.stdout)

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


class DiskPreflightTests(unittest.TestCase):
    @staticmethod
    def model(filename, content, required=True):
        return {
            "filename": filename,
            "comfyui_subdir": "models/test",
            "sha256": hashlib.sha256(content).hexdigest(),
            "required": required,
            "optional": not required,
            "source_status": "resolved",
            "source_url": "https://huggingface.co/org/repo/resolve/main/" + filename,
        }

    def test_valid_required_files_are_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            models = [self.model("a.bin", b"a"), self.model("b.bin", b"b")]
            for model, content in zip(models, (b"a", b"b")):
                path = root / model["comfyui_subdir"] / model["filename"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            result = disk_summary(models, root)
        self.assertTrue(result["ready"])
        self.assertEqual(2, result["required_complete"])

    def test_part_file_is_partial_and_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = self.model("a.bin", b"complete")
            part = root / model["comfyui_subdir"] / "a.bin.part"
            part.parent.mkdir(parents=True)
            part.write_bytes(b"partial")
            result = disk_summary([model], root)
        self.assertFalse(result["ready"])
        self.assertEqual(1, result["partial"])
        self.assertEqual(PARTIAL, result["models"][0]["status"])

    def test_corrupt_final_is_checksum_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = self.model("a.bin", b"expected")
            final = root / model["comfyui_subdir"] / "a.bin"
            final.parent.mkdir(parents=True)
            final.write_bytes(b"corrupt")
            result = disk_summary([model], root)
        self.assertFalse(result["ready"])
        self.assertEqual(1, result["checksum_failed"])
        self.assertEqual(CHECKSUM_FAILED, result["models"][0]["status"])


class DownloaderTests(unittest.TestCase):
    def test_huggingface_url_is_parsed(self):
        self.assertEqual(
            ("org/repo", "folder/model.bin", "main"),
            download_models.huggingface_source(
                "https://huggingface.co/org/repo/resolve/main/folder/model.bin"
            ),
        )

    def test_truncated_hf_download_cannot_be_promoted_to_final(self):
        content = b"complete-model"
        model = {
            "filename": "model.bin",
            "source_url": "https://huggingface.co/org/repo/resolve/main/model.bin",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "model.bin"
            cached = Path(directory) / "cache" / "truncated.bin"
            cached.parent.mkdir()
            cached.write_bytes(content[:8])
            hub_download = unittest.mock.Mock(return_value=str(cached))
            with patch.dict(sys.modules, {"huggingface_hub": unittest.mock.Mock(
                hf_hub_download=hub_download
            )}):
                with self.assertRaises(RuntimeError):
                    download_models.download_huggingface(
                        model, destination, Path(directory) / "cache"
                    )
            self.assertFalse(destination.exists())

    def test_valid_cached_hf_download_is_reused_and_promoted(self):
        content = b"complete-model"
        model = {
            "filename": "model.bin",
            "source_url": "https://huggingface.co/org/repo/resolve/main/model.bin",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            cached = Path(directory) / "cache" / "model.bin"
            cached.parent.mkdir()
            cached.write_bytes(content)
            destination = Path(directory) / "final" / "model.bin"
            destination.parent.mkdir()
            hub_download = unittest.mock.Mock(return_value=str(cached))
            with patch.dict(sys.modules, {"huggingface_hub": unittest.mock.Mock(
                hf_hub_download=hub_download
            )}):
                download_models.download_huggingface(
                    model, destination, Path(directory) / "cache"
                )
            self.assertEqual(content, destination.read_bytes())
            hub_download.assert_called_once()

    def test_final_sha256_must_match_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cached.bin"
            destination = Path(directory) / "final.bin"
            source.write_bytes(b"wrong")
            with self.assertRaises(RuntimeError):
                download_models.promote_verified(
                    source, destination, hashlib.sha256(b"expected").hexdigest()
                )
            self.assertFalse(destination.exists())

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


    def test_transient_failure_preserves_partial_file(self):
        content = b"partial-data"
        model = {
            "filename": "model.bin",
            "source_url": "https://huggingface.co/org/repo/resolve/main/model.bin",
            "sha256": hashlib.sha256(content + b"rest").hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "model.bin"
            partial = Path(str(destination) + ".part")
            partial.write_bytes(content)
            with patch.object(download_models, "urlopen", side_effect=TimeoutError("network timeout")):
                with self.assertRaises(TimeoutError):
                    download_models.download_once(model, destination, timeout=1)
            self.assertEqual(content, partial.read_bytes())

    def test_preflight_stays_false_until_physical_final_is_valid(self):
        content = b"valid-model"
        model = DiskPreflightTests.model("model.bin", content)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / ".cache" / "model.bin"
            cache.parent.mkdir()
            cache.write_bytes(content)
            self.assertFalse(disk_summary([model], root)["ready"])
            destination = root / model["comfyui_subdir"] / model["filename"]
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"truncated")
            self.assertFalse(disk_summary([model], root)["ready"])
            destination.write_bytes(content)
            self.assertTrue(disk_summary([model], root)["ready"])

    def test_failed_model_does_not_prevent_later_model_attempt_and_exit_is_nonzero(self):
        first_content, second_content = b"first", b"second"
        models = [
            {
                "filename": "first.bin", "comfyui_subdir": "models/test",
                "source_url": "https://huggingface.co/org/repo/resolve/main/first.bin",
                "source_status": "resolved", "sha256": hashlib.sha256(first_content).hexdigest(),
                "required": True, "optional": False,
            },
            {
                "filename": "second.bin", "comfyui_subdir": "models/test",
                "source_url": "https://huggingface.co/org/repo/resolve/main/second.bin",
                "source_status": "resolved", "sha256": hashlib.sha256(second_content).hexdigest(),
                "required": True, "optional": False,
            },
        ]
        attempted = []

        def fake_download(model, root, retries, timeout):
            attempted.append(model["filename"])
            if model["filename"] == "first.bin":
                return "FAILED"
            destination = root / model["comfyui_subdir"] / model["filename"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(second_content)
            return COMPLETE

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(download_models, "validate", return_value=({"models": models}, [])),
            patch.object(download_models, "download", side_effect=fake_download),
            patch.object(sys, "argv", [
                "download_models.py", "--comfyui-root", directory, "--retries", "1"
            ]),
            redirect_stdout(io.StringIO()) as stdout,
            redirect_stderr(io.StringIO()),
        ):
            result = download_models.main()
        self.assertEqual(1, result)
        self.assertEqual(["first.bin", "second.bin"], attempted)
        self.assertIn("FAILED: 1", stdout.getvalue())
        self.assertIn("REQUIRED COMPLETE: 1/2", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
