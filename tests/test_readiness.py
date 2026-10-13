import httpx
import pytest
from sqlalchemy import select
from guard.config import settings
from guard.db import User, db
from guard.inference import InferenceUnavailable
from guard.readiness import configuration_status, model_catalog, probe_inference

def test_missing_configuration_never_exposes_key(monkeypatch):
    monkeypatch.setattr(settings(), "vultr_inference_api_key", "private-secret-value")
    monkeypatch.setattr(settings(), "vultr_chat_model", "")
    result = configuration_status()
    assert result["missing"] == ["VULTR_CHAT_MODEL"]
    assert "private-secret-value" not in str(result)
    assert not result["live_inference_verified"]

async def test_missing_key_never_contacts_provider(monkeypatch):
    monkeypatch.setattr(settings(), "vultr_inference_api_key", "")
    async def forbidden():
        raise AssertionError("No network calls allowed")
    monkeypatch.setattr("guard.readiness.model_catalog", forbidden)
    assert (await probe_inference())["status"] == "NOT_CONFIGURED"

@pytest.mark.parametrize("valid", [True, False])
async def test_public_catalog_does_not_claim_authentication(monkeypatch, valid):
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            assert "headers" not in kwargs
            return httpx.Response(200, request=httpx.Request("GET", url),
                                  json={"data": [{"id": "test-model"}]} if valid else {"data": []})
    monkeypatch.setattr("guard.readiness.httpx.AsyncClient", Client)
    if valid:
        result = await model_catalog()
        assert result["models"] == ["test-model"] and result["authenticated"] is False
    else:
        with pytest.raises(InferenceUnavailable): await model_catalog()

@pytest.mark.parametrize("present", [True, False])
async def test_probe_requires_catalog_match_and_real_adapter(monkeypatch, present):
    monkeypatch.setattr(settings(), "vultr_inference_api_key", "test-key")
    monkeypatch.setattr(settings(), "vultr_chat_model", "test-model")
    async def catalog(): return {"models": ["test-model"] if present else ["other-model"]}
    calls = []
    async def request(self, messages, schema):
        calls.append(messages)
        return schema(ready=True)
    monkeypatch.setattr("guard.readiness.model_catalog", catalog)
    monkeypatch.setattr("guard.readiness.VultrInference.request", request)
    if present:
        assert (await probe_inference())["live_inference_verified"]
        assert len(calls) == 1
    else:
        with pytest.raises(InferenceUnavailable): await probe_inference()
        assert not calls

def test_provider_routes_require_admin_and_csrf(client):
    assert client.get("/api/v1/system/provider").status_code == 200
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/system/inference-check").status_code == 403
    with db() as s:
        s.scalar(select(User).where(User.username == "operator")).role = "operator"
        s.commit()
    assert client.get("/api/v1/system/provider").status_code == 403
    assert client.get("/api/v1/system/models").status_code == 403
