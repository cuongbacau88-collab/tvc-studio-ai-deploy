import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runtime_preflight():
    spec = importlib.util.spec_from_file_location("runtime_preflight", ROOT / "scripts" / "runtime_preflight.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_node_manifest_covers_exactly_all_workflow_class_types():
    registry = json.loads((ROOT / "workflows" / "manifest.json").read_text())["workflows"]
    actual = set()
    for entry in registry.values():
        graph = json.loads((ROOT / entry["file"]).read_text())
        actual.update(node["class_type"] for node in graph.values())
    manifest = json.loads((ROOT / "configs" / "custom_nodes_manifest.json").read_text())
    assert {node["class_type"] for node in manifest["nodes"]} == actual


def test_h3_first_last_is_partner_api_and_not_local_gpu_ready():
    manifest = json.loads((ROOT / "configs" / "custom_nodes_manifest.json").read_text())
    nodes = {node["class_type"]: node for node in manifest["nodes"]}
    h3 = nodes["MinimaxHailuo03FirstLastFrameNode"]
    assert h3["classification"] == "partner_api"
    assert h3["credential_env"] == ["API_KEY_COMFY_ORG"]
    assert h3["local_gpu_ready"] is False
    assert h3["repository"] == "https://github.com/Comfy-Org/ComfyUI.git"


def test_unverified_nodes_have_no_guessed_repository():
    manifest = json.loads((ROOT / "configs" / "custom_nodes_manifest.json").read_text())
    unresolved = {node["class_type"]: node for node in manifest["nodes"] if node["classification"] == "unresolved"}
    assert unresolved == {}
    nodes = {node["class_type"]: node for node in manifest["nodes"]}
    assert nodes["ComfyMathExpression"]['classification'] == "core"
    assert nodes["ComfySwitchNode"]['classification'] == "core"


def test_output_nodes_are_save_image_or_save_video():
    registry = json.loads((ROOT / "workflows" / "manifest.json").read_text())["workflows"]
    for entry in registry.values():
        graph = json.loads((ROOT / entry["file"]).read_text())
        for output in entry["outputs"]:
            assert graph[str(output["node_id"])]["class_type"] in {"SaveImage", "SaveVideo"}


def test_runtime_sha256(tmp_path):
    module = load_runtime_preflight()
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"tvc-runtime-preflight")
    assert module.sha256(artifact) == "8e0dfc34bb4ceb3991abfc6af8b2c966a1136e3831e94b5e5f79ff5d437d843b"


def test_single_command_orders_bootstrap_download_start_preflight():
    bootstrap = (ROOT / "scripts" / "bootstrap_vast.sh").read_text()
    provision = (ROOT / "scripts" / "provision_vast.sh").read_text()
    assert "download-models.sh" not in bootstrap
    assert provision.index("bootstrap_vast.sh") < provision.index("download-models.sh")
    assert provision.index("download-models.sh") < provision.index("main.py")
    assert provision.index("main.py") < provision.index("runtime_preflight.py")
