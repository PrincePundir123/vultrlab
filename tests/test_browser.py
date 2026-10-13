"""Actual browser tests on a controlled local portal. NOT Docker containment tests."""
import asyncio
import os
import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import select

from guard.config import settings
from guard.contracts import READ, WRITE, SandboxSpec, Step, Workflow
from guard.db import Job, User, db, uid
from guard.orchestration import Runtime
from guard.verification import verify_read, verify_write
from portal.app import app, admin
from runner.main import execute
from tests.fixture_provider import FixtureProvider

pytestmark = [pytest.mark.browser, pytest.mark.skipif(os.environ.get("SKG_BROWSER_TEST") != "1",
              reason="Set SKG_BROWSER_TEST=1 for actual local browser tests; this does not test Docker")]


@pytest.fixture
def site():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", timeout_graceful_shutdown=1))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.05)
    assert server.started
    with TestClient(admin) as truth:
        truth.headers["X-Internal-Secret"] = settings().portal_admin_secret
        truth.post("/scenario", json={"version": 1}).raise_for_status()
        yield f"http://127.0.0.1:{port}", truth
    server.should_exit = True
    thread.join(5)


def read_workflow():
    return Workflow(steps=[Step(action="fill", target="order_search", value_from="order_id"),
                           Step(action="click", target="search_button"), Step(action="read", target="order_details")])


async def browser_run(origin, workflow, inputs, operation=READ, approved=False):
    return await execute(SandboxSpec(execution_id=uid(), operation=operation, workflow=workflow,
                         inputs=inputs, approved=approved), origin, os.environ.get("SKG_CHROME_PATH"))


async def test_actual_browser_reads_writes_and_layout_detection(site):
    origin, truth = site
    observed = await browser_run(origin, read_workflow(), {"order_id": "ORD-102"})
    assert verify_read("ORD-102", observed, truth.get("/orders/ORD-102").json())["verified"], observed
    assert observed["screenshots"][0].startswith("iVBOR")
    unknown = await browser_run(origin, read_workflow(), {"order_id": "ORD-999"})
    assert verify_read("ORD-999", unknown, truth.get("/orders/ORD-999").json())["status"] == "NOT_FOUND"
    inputs = {"order_id": "ORD-102", "message": "Actual browser test request", "idempotency_key": uid()}
    write = Workflow(steps=read_workflow().steps + [Step(action="fill", target="message", value_from="message"),
        Step(action="fill", target="idempotency_key", value_from="idempotency_key"),
        Step(action="click", target="submit_request"), Step(action="read", target="receipt")])
    observation = await browser_run(origin, write, inputs, WRITE, True)
    assert verify_write(inputs, truth.get("/requests/" + inputs["idempotency_key"]).json(),
                        bool(observation["screenshots"]))["verified"], observation
    truth.post("/scenario", json={"version": 2}).raise_for_status()
    failed = await browser_run(origin, read_workflow(), {"order_id": "ORD-102"})
    assert failed["status"] == "PORTAL_CHANGED"


async def test_fixture_learning_and_repair_use_actual_observations(site, client, monkeypatch):
    origin, truth = site
    async def trusted(path, body=None):
        r = truth.post(path, json=body) if body is not None else truth.get(path)
        r.raise_for_status()
        return r.json()
    monkeypatch.setattr("guard.orchestration.portal_truth", trusted)
    class LocalBrowserTestRuntime(Runtime):
        async def run(self, workflow, inputs, operation=READ, approved=False, mode="execute"):
            return await browser_run(origin, workflow, inputs, operation, approved)
    with db() as s:
        user = s.scalar(select(User))
        job = Job(owner_id=user.id, kind="learn", payload={}, state="RUNNING", lease_token=uid(), lease_until=time.time()+900)
        s.add(job)
        s.commit()
    runtime = LocalBrowserTestRuntime(job, FixtureProvider())
    first = await runtime.learn()
    assert first["provider"] == "TEST_FIXTURE_NOT_AI"
    assert first["status"] == "VERIFIED"
    truth.post("/scenario", json={"version": 2}).raise_for_status()
    second = await runtime.learn(repair=True)
    assert second["status"] == "VERIFIED" and second["version"] > first["version"]


async def test_timed_out_browser_write_is_found_without_resubmission(site):
    origin, truth = site
    truth.post("/scenario", json={"version": 1, "timeout_after_write": True}).raise_for_status()
    inputs = {"order_id": "ORD-104", "message": "Timeout reconciliation test", "idempotency_key": uid()}
    workflow = Workflow(steps=read_workflow().steps + [
        Step(action="fill", target="message", value_from="message"),
        Step(action="fill", target="idempotency_key", value_from="idempotency_key"),
        Step(action="click", target="submit_request"), Step(action="read", target="receipt")])
    observed = await browser_run(origin, workflow, inputs, WRITE, True)
    assert observed["status"] == "TRANSIENT_ERROR"  # Timeout is not evidence of a layout change.
    persisted = truth.get("/requests/" + inputs["idempotency_key"]).json()
    assert persisted["found"]
    fresh = await browser_run(origin, read_workflow(), {"order_id": "ORD-104"})
    assert verify_write(inputs, persisted, bool(fresh["screenshots"]))["verified"]


async def test_access_denial_is_not_layout_change(site):
    origin, truth = site
    truth.post("/scenario", json={"version":1,"access_denied":True}).raise_for_status()
    observed = await browser_run(origin, read_workflow(), {"order_id":"ORD-102"})
    assert observed["status"] == "ACCESS_DENIED"
    minimal = await browser_run(origin, Workflow(steps=[Step(action="navigate")]), {"order_id":"ORD-102"})
    assert minimal["status"] == "ACCESS_DENIED"
