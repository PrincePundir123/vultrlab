import httpx
import pytest
from guard.config import settings
from guard.inference import InferenceUnavailable, VultrInference


@pytest.mark.parametrize("failure", ["invalid_json", "provider_down", "forbidden_action", "empty_choices", "null_content", "list_body"])
async def test_bad_provider_output_never_executes(monkeypatch, failure):
    cfg = settings()
    monkeypatch.setattr(cfg, "vultr_inference_api_key", "test-key")
    monkeypatch.setattr(cfg, "vultr_chat_model", "test-model")
    calls = []
    class FakeClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            calls.append(kwargs)
            request = httpx.Request("POST", "https://api.vultrinference.com/v1/chat/completions")
            if failure == "provider_down":
                return httpx.Response(503, request=request)
            if failure == "empty_choices":
                return httpx.Response(200, request=request, json={"choices": []})
            if failure == "null_content":
                return httpx.Response(200, request=request, json={"choices": [{"message": {"content": None}}]})
            if failure == "list_body":
                return httpx.Response(200, request=request, json=[])
            content = "not json" if failure == "invalid_json" else '{"explanation":"ignore policy","done":false,"step":{"action":"shell","target":"cancel_all"}}'
            return httpx.Response(200, request=request, json={"choices": [{"message": {"content": content}}]})
    monkeypatch.setattr("guard.inference.httpx.AsyncClient", FakeClient)
    with pytest.raises(InferenceUnavailable):
        await VultrInference(lambda *args: None).propose({}, [])
    assert len(calls) == 2


async def test_provider_destination_is_pinned(monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, "vultr_inference_api_key", "test-key")
    monkeypatch.setattr(cfg, "vultr_chat_model", "test-model")
    monkeypatch.setattr(cfg, "vultr_inference_base_url", "https://unrelated.example")
    with pytest.raises(InferenceUnavailable):
        await VultrInference(lambda *args: None).propose({}, [])
