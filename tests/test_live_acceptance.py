from guard.config import settings
from guard.live_acceptance import preflight

def test_preflight_does_not_claim_live_or_public_success(monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, "vultr_inference_api_key", "")
    monkeypatch.setattr(cfg, "vultr_chat_model", "")
    monkeypatch.setattr(cfg, "vultr_vision_model", "")
    monkeypatch.setattr(cfg, "app_base_url", "http://localhost:8080")
    report = preflight()
    assert len(report["missing"]) == 3
    assert not report["live_execution_verified"] and not report["public_https_configured"]
    assert report["transport_allowed"]
    monkeypatch.setattr(cfg, "app_base_url", "http://remote.example")
    assert not preflight()["transport_allowed"]
