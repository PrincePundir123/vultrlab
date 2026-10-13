import pytest
from sqlalchemy import select
from guard.contracts import READ, Workflow, Step, canonical_hash, contract
from guard.db import Job, Operation, User, Version, db, uid
from guard.orchestration import Runtime


async def test_failed_candidate_never_promoted(client):
    with db() as s:
        user = s.scalar(select(User))
        definition = Workflow(steps=[Step(action="navigate")]).model_dump()
        s.add(Version(operation=READ, number=1, definition=definition, contract=contract(READ), digest=canonical_hash(definition)))
        op = s.get(Operation, READ)
        op.state, op.active_version = "QUARANTINED", 1
        job = Job(owner_id=user.id, kind="repair", state="RUNNING", lease_token=uid(), payload={})
        s.add(job)
        s.commit()
    class FailingRuntime(Runtime):
        async def discover(self, repair=None):
            return Workflow(steps=[Step(action="navigate")])
        async def validate_candidate(self, definition, version):
            return False
    with pytest.raises(RuntimeError, match="CANDIDATE_FAILED_REGRESSION"):
        await FailingRuntime(job).learn(repair=True)
    with db() as s:
        op = s.get(Operation, READ)
        assert op.state == "QUARANTINED"
        assert op.active_version == 1
        assert len(list(s.scalars(select(Version).where(Version.operation == READ)))) == 3
