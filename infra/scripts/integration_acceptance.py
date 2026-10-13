"""Run inside a configured control service. Real worker/portal; explicitly test-only AI.

Stop the normal orchestrator before this script. Uses its own operator's records.
Never run on a real business portal. Outputs measurements, not projected results.
"""
import asyncio
import json
import time
from pathlib import Path

import httpx
from sqlalchemy import select

from guard.config import settings
from guard.db import Job, User, db
from guard.orchestration import Runtime, claim_job
from guard.verification import portal_truth
from tests.fixture_provider import FixtureProvider


async def main():
    cfg = settings()
    async with httpx.AsyncClient(base_url="http://api:8000", timeout=30) as api:
        login = await api.post("/api/v1/auth/login", json={"username": cfg.operator_username, "password": cfg.operator_password})
        login.raise_for_status()
        api.headers["X-CSRF-Token"] = login.json()["csrf"]
        async def call(path, body=None):
            response = await api.post("/api/v1" + path, json=body)
            response.raise_for_status()
            return response.json()
        measurements = []
        async def execute(record, fixture=False):
            job = claim_job()
            assert job and job.id == record["id"], "Stop normal orchestrator and clear queued jobs first"
            # Extend lease for synchronous acceptance driver; production uses heartbeats.
            with db() as s:
                s.get(Job, job.id).lease_until = time.time() + 900
                s.commit()
            begin = time.monotonic()
            try:
                result = await Runtime(job, FixtureProvider() if fixture else None).process()
            except Exception as exc:
                with db() as s:
                    saved = s.get(Job, job.id)
                    saved.state, saved.result, saved.finished = "FAILED", {"error": str(exc)}, time.time()
                    s.commit()
                raise
            with db() as s:
                saved = s.get(Job, job.id)
                saved.state, saved.result, saved.finished = result["status"], result, time.time()
                s.commit()
            measurements.append({"kind": job.kind, "duration_ms": round((time.monotonic() - begin)*1000),
                                 "status": result["status"], "inference": "TEST_FIXTURE_NOT_AI" if fixture else "none"})
            return result
        await call("/scenario", {"version": 1})
        learned = await execute(await call("/operations/learn"), True)
        assert learned["status"] == "VERIFIED"
        operations = (await api.get("/api/v1/operations")).json()
        write = next(o for o in operations if o["name"] == "submit_delivery_request")["versions"][0]
        await call("/operations/submit_delivery_request/review", {"version": write["number"], "digest": write["digest"]})
        csv = b"order_id,expected_delivery\nORD-101,2026-11-10\nORD-102,2026-11-10\nORD-103,2026-11-11\n"
        uploaded = await api.post("/api/v1/orders/upload", files={"file": ("sample.csv", csv)})
        uploaded.raise_for_status()
        result = await execute(await call("/tasks", {"orders": uploaded.json()["orders"]}))
        assert [r["classification"] for r in result["rows"]] == ["ON_TRACK", "DELAYED", "UNKNOWN"]
        draft = await call("/requests/prepare", {"order_id": "ORD-102", "message": "Acceptance test: please update delivery."})
        await call("/requests/"+draft["id"]+"/approve", {"digest": draft["digest"]})
        verified = await execute(await call("/requests/"+draft["id"]+"/submit", {"digest": draft["digest"]}))
        assert verified["status"] == "VERIFIED"
        retry = await api.post("/api/v1/requests/"+draft["id"]+"/submit", json={"digest": draft["digest"]})
        assert retry.status_code == 409
        await call("/scenario", {"version": 2})
        failed = await execute(await call("/tasks", {"orders": uploaded.json()["orders"]}))
        assert failed["status"] == "PORTAL_CHANGED"
        repaired = await execute(await call("/operations/get_order_status/repair"), True)
        assert repaired["version"] > learned["version"]
        assert (await execute(await call("/tasks", {"orders": uploaded.json()["orders"]})))["status"] == "VERIFIED"
        contained = await execute(await call("/containment"))
        assert contained["status"] == "SANDBOX_TERMINATED" and contained["cleanup"]
        assert (await api.get("/health/live")).status_code == 200
        path = Path("/data/artifacts/acceptance-measurements.json")
        path.write_text(json.dumps({"inference": "DETERMINISTIC_TEST_FIXTURE; NOT VULTR", "measurements": measurements}, indent=2))
        print(json.dumps({"checks": "passed", "measurements": measurements}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
