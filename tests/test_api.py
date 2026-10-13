import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select
from guard.api import app
from guard.contracts import WRITE, canonical_hash, contract
from guard.db import Artifact, Draft, Job, Operation, User, Version, db


def seed_draft(client, expires=None):
    with db() as s:
        user = s.scalar(select(User))
        definition = {"steps": [{"action": "navigate", "target": "", "path": "/", "value_from": None}]}
        op = s.get(Operation, WRITE)
        op.active_version, op.state = 1, "ACTIVE"
        if not s.scalar(select(Version).where(Version.operation == WRITE)):
            s.add(Version(operation=WRITE, number=1, definition=definition, contract=contract(WRITE), digest=canonical_hash(definition)))
        snapshot = {"order_id": "ORD-102", "message": "Update please", "version": 1,
                    "definition_hash": canonical_hash(definition), "idempotency_key": "a" * 32}
        draft = Draft(owner_id=user.id, snapshot=snapshot, digest=canonical_hash(snapshot), state="APPROVED",
                      approved_by=user.id, expires=expires or time.time() + 100)
        s.add(draft)
        s.commit()
        return draft.id, draft.digest


def test_csv_validation(client):
    good = b"order_id,expected_delivery\nORD-102,2026-11-10\n"
    assert client.post("/api/v1/orders/upload", files={"file": ("x.csv", good)}).status_code == 200
    for bad in (b"bad,columns\na,b", b"order_id,expected_delivery\nORD-102,xxx", good + b"ORD-102,2026-11-10\n"):
        assert client.post("/api/v1/orders/upload", files={"file": ("x.csv", bad)}).status_code == 422
    assert client.post("/api/v1/orders/upload", files={"file": ("x.csv", b"x" * 65537)}).status_code == 413


def test_csrf_and_authentication(client):
    response = client.post("/api/v1/tasks", headers={"X-CSRF-Token": "bad"}, json={"orders": []})
    assert response.status_code == 403
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/v1/tasks").status_code == 401


def test_exact_approval_and_single_use(client):
    draft_id, digest = seed_draft(client)
    assert client.post(f"/api/v1/requests/{draft_id}/submit", json={"digest": "b" * 64}).status_code == 409
    first = client.post(f"/api/v1/requests/{draft_id}/submit", json={"digest": digest})
    assert first.status_code == 200
    assert client.post(f"/api/v1/requests/{draft_id}/submit", json={"digest": digest}).status_code == 409
    with db() as s:
        assert len(list(s.scalars(select(Job).where(Job.kind == "submit")))) == 1


def test_expired_approval(client):
    draft_id, digest = seed_draft(client, time.time() - 1)
    assert client.post(f"/api/v1/requests/{draft_id}/submit", json={"digest": digest}).status_code == 409


def test_approval_race_has_one_winner(client):
    draft_id, digest = seed_draft(client)
    def submit(_):
        return client.post(f"/api/v1/requests/{draft_id}/submit", json={"digest": digest}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [200, 409]


def test_changed_snapshot_rejected(client):
    draft_id, digest = seed_draft(client)
    with db() as s:
        d = s.get(Draft, draft_id)
        d.snapshot = {**d.snapshot, "order_id": "ORD-101"}
        s.commit()
    assert client.post(f"/api/v1/requests/{draft_id}/submit", json={"digest": digest}).status_code == 409


def test_cross_owner_artifact_and_job_hidden(client):
    with db() as s:
        other = User(username="other", password_hash="not-used", role="operator")
        s.add(other)
        s.flush()
        job = Job(owner_id=other.id, kind="read", payload={})
        s.add(job)
        s.flush()
        artifact = Artifact(owner_id=other.id, job_id=job.id, filename="none.png", digest="0" * 64, size=0)
        s.add(artifact)
        s.commit()
    assert client.get("/api/v1/artifacts/" + artifact.id).status_code == 404
    assert client.get("/api/v1/tasks/" + job.id).status_code == 404


def test_cancel_queued_job_and_export(client):
    job = client.post("/api/v1/tasks", json={"orders": [{"order_id": "ORD-102", "expected_delivery": "2026-11-10"}]}).json()
    assert client.post(f'/api/v1/tasks/{job["id"]}/cancel').status_code == 200
    assert client.get(f'/api/v1/tasks/{job["id"]}').json()["state"] == "CANCELED"
    assert client.get(f'/api/v1/tasks/{job["id"]}/export/json').status_code == 200
