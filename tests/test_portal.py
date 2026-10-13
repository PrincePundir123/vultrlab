from fastapi.testclient import TestClient
from portal.app import app, admin
from guard.config import settings


def test_real_persistence_and_duplicate_prevention():
    with TestClient(app) as browser, TestClient(admin) as truth:
        assert 'ORD-102' in browser.get('/?q=ORD-102').text
        assert 'not_found' in browser.get('/?q=ORD-999').text
        data = {"order_id": "ORD-102", "message": "Test delivery request", "idempotency_key": "c" * 32}
        assert browser.post('/requests', data=data).status_code == 200
        assert browser.post('/requests', data=data).status_code == 200
        result = truth.get('/requests/' + 'c' * 32, headers={"X-Internal-Secret": settings().portal_admin_secret}).json()
        assert result["request"]["message"] == data["message"]
        assert browser.post('/requests', data={**data, "message": "different"}).status_code == 409
        assert truth.post('/scenario', json={"version": 2}).status_code == 401
