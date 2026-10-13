import time
import pytest
from sqlalchemy import select
from guard.contracts import READ, PolicyError, canonical_hash, contract
from guard.db import Job, Operation, User, Version, db
from guard.orchestration import active_version, claim_job
from guard.inference import InferenceUnavailable, VultrInference


def test_quarantined_operation_not_reused(client):
    with db() as s:
        s.get(Operation, READ).state = "QUARANTINED"
        s.commit()
    with pytest.raises(PolicyError):
        active_version(READ)


def test_versions_are_immutable(client):
    with db() as s:
        value = {"steps": []}
        version = Version(operation=READ, number=1, definition=value, contract=contract(READ), digest=canonical_hash(value))
        s.add(version)
        s.commit()
        version.definition = {"steps": ["changed"]}
        with pytest.raises(ValueError):
            s.commit()


def test_expired_operation_requires_new_validation(client):
    with db() as s:
        definition = {"steps": []}
        s.add(Version(operation=READ, number=1, definition=definition, contract=contract(READ),
                      digest=canonical_hash(definition), created=time.time() - 8 * 24 * 3600))
        op = s.get(Operation, READ)
        op.state, op.active_version = "ACTIVE", 1
        s.commit()
    with pytest.raises(PolicyError, match="OPERATION_VALIDITY_EXPIRED"):
        active_version(READ)


def test_claim_once_and_recover_expired_read_without_replay(client):
    with db() as s:
        user = s.scalar(select(User))
        job = Job(owner_id=user.id, kind="read", payload={})
        s.add(job)
        s.commit()
    first = claim_job()
    assert first and first.id == job.id
    assert claim_job() is None
    with db() as s:
        s.get(Job, job.id).lease_until = time.time() - 5
        s.commit()
    assert claim_job() is None
    with db() as s:
        assert s.get(Job, job.id).state == "INTERRUPTED"


async def test_no_mock_fallback_when_inference_missing(monkeypatch):
    from guard.config import settings
    monkeypatch.setattr(settings(), "vultr_inference_api_key", "")
    with pytest.raises(InferenceUnavailable):
        await VultrInference(lambda *args: None).propose({}, [])
