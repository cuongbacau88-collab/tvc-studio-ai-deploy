import json

import pytest

from tvc_api.adapters.comfyui import ComfyWorkflowAdapter
from tvc_api.errors import APIError


class FirstLastRegistry:
    def spec_for(self, operation, model_id, parameters):
        return {"mode": "first_last", "inputs": {}}


def adapter_for_first_last():
    adapter = object.__new__(ComfyWorkflowAdapter)
    adapter.operation = "first_last_frame_to_video"
    adapter.workflows = FirstLastRegistry()
    adapter.spec = type("Spec", (), {"id": "minimax_h3"})()
    return adapter


def test_first_last_fails_clearly_without_partner_key(monkeypatch, tmp_path):
    monkeypatch.delenv("API_KEY_COMFY_ORG", raising=False)
    adapter = adapter_for_first_last()
    with pytest.raises(APIError) as caught:
        adapter._run_sync({}, {}, tmp_path)
    assert caught.value.code == "partner_api_key_missing"
    assert caught.value.status == 503


def test_first_last_fails_clearly_when_partner_node_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_COMFY_ORG", "test-placeholder")
    adapter = adapter_for_first_last()
    adapter._request = lambda path, *args, **kwargs: json.dumps({}).encode()
    with pytest.raises(APIError) as caught:
        adapter._run_sync({}, {}, tmp_path)
    assert caught.value.code == "partner_node_unavailable"
    assert caught.value.status == 503


def test_partner_key_is_sent_only_as_comfy_extra_data():
    adapter = object.__new__(ComfyWorkflowAdapter)
    captured = {}

    def request(path, data=None, headers=None):
        captured.update(json.loads(data))
        return json.dumps({"prompt_id": "prompt-1"}).encode()

    adapter._request = request
    assert adapter._submit_prompt({"1": {"class_type": "SaveVideo"}}, "secret") == "prompt-1"
    assert captured["extra_data"] == {"api_key_comfy_org": "secret"}
    assert "secret" not in json.dumps(captured["prompt"])
