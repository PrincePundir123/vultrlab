import pytest
from runner.main import classify_failure
from guard.contracts import READ, WRITE, contract, canonical_hash
from guard.db import db, Operation, Version, Job
from guard.orchestration import Runtime

@pytest.mark.parametrize("status,trace,message,missing,timeout,expected", [
    (403, [], "", True, True, "ACCESS_DENIED"),
    (503, [], "", True, True, "TRANSIENT_ERROR"),
    (200, [], "net::ERR_CONNECTION_RESET", False, False, "TRANSIENT_ERROR"),
    (200, [], "", True, True, "PORTAL_CHANGED"),
    (200, [], "", False, True, "TRANSIENT_ERROR"),
    (200, [{"kind":"POLICY_BLOCK"}], "", True, True, "REJECTED_BY_POLICY"),
    (200, [], "internal exception", False, False, "EXECUTION_FAILED"),
])
def test_failure_categories(status,trace,message,missing,timeout,expected):
    assert classify_failure(status,trace,message,missing,timeout) == expected

@pytest.mark.parametrize("status,calls,state", [("TRANSIENT_ERROR",2,"ACTIVE"),
    ("ACCESS_DENIED",1,"ACTIVE"), ("PORTAL_CHANGED",1,"QUARANTINED"),
    ("REJECTED_BY_POLICY",1,"ACTIVE")])
async def test_read_retry_and_quarantine(client, monkeypatch, status, calls, state):
    definition={"steps":[{"action":"navigate"}]}
    with db() as s:
        s.add(Version(operation=READ,number=1,definition=definition,contract=contract(READ),digest=canonical_hash(definition)))
        for name in (READ,WRITE):
            op=s.get(Operation,name);op.state="ACTIVE";op.active_version=1
        s.commit()
    runtime=Runtime(Job(id="test",owner_id="test",kind="read",payload={"orders":[{"order_id":"ORD-101"}]}))
    seen=[]
    async def run(*args,**kwargs):
        seen.append(1)
        return {"status":status}
    monkeypatch.setattr(runtime,"run",run)
    monkeypatch.setattr(runtime,"record",lambda *args:None)
    monkeypatch.setattr(runtime,"checkpoint",lambda:None)
    result=await runtime.read_orders()
    assert result["status"] == status
    assert len(seen)==calls
    with db() as s:
        assert s.get(Operation,READ).state==state
        assert s.get(Operation,WRITE).state==state
