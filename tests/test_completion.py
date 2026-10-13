import time
import pytest
from sqlalchemy import select
from guard.contracts import READ, WRITE, Workflow, Step, contract, canonical_hash
from guard.db import db, User, Job, Operation, Version, uid
from guard.orchestration import Runtime, active_version, process_claimed

@pytest.mark.parametrize("passes", [True, False])
async def test_expired_version_revalidates_without_mutating_history(client, passes):
    definition = Workflow(steps=[Step(action="navigate")]).model_dump()
    with db() as s:
        user = s.scalar(select(User))
        old = Version(operation=READ, number=1, definition=definition, contract=contract(READ),
                      digest=canonical_hash(definition), created=time.time()-8*86400)
        s.add(old)
        op = s.get(Operation, READ)
        op.state, op.active_version = "ACTIVE", 1
        job = Job(owner_id=user.id, kind="validate", state="RUNNING", lease_token=uid(), payload={})
        s.add(job)
        s.commit()
        original_created = old.created
    class ValidationRuntime(Runtime):
        async def validate_candidate(self, workflow, version):
            assert version.number == 2
            return passes
    result = await ValidationRuntime(job).process()
    assert result["status"] == ("VERIFIED" if passes else "VALIDATION_FAILED")
    with db() as s:
        assert s.get(Version, old.id).created == original_created
        op = s.get(Operation, READ)
        assert op.active_version == (2 if passes else 1)
        assert op.state == ("ACTIVE" if passes else "QUARANTINED")
        assert s.get(Operation, WRITE).state == ("TESTING" if passes else "QUARANTINED")
    if passes:
        assert active_version(READ).number == 2

async def test_running_read_cancellation_is_not_reported_as_failure(client, monkeypatch):
    with db() as s:
        user = s.scalar(select(User))
        job = Job(owner_id=user.id, kind="read", state="RUNNING", lease_token=uid(), payload={})
        s.add(job)
        s.commit()
    async def canceled(self):
        raise RuntimeError("CANCELED")
    monkeypatch.setattr(Runtime, "process", canceled)
    await process_claimed(job)
    with db() as s:
        assert s.get(Job, job.id).state == "CANCELED"
