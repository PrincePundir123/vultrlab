"""Run from the control plane: python -m guard.live_acceptance [--run].

--run uses real Vultr tokens, changes the synthetic portal layout and creates one
explicitly approved synthetic request. Never injects fixture inference.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from guard.config import settings
from guard.readiness import configuration_status


def preflight():
    cfg = settings()
    url = urlsplit(cfg.app_base_url)
    local = url.hostname in {"localhost", "127.0.0.1", "::1"}
    missing = configuration_status()["missing"]
    if not cfg.vultr_vision_model: missing += ["VULTR_VISION_MODEL"]
    if not cfg.operator_password: missing += ["OPERATOR_PASSWORD"]
    return {"missing": missing, "public_https_configured": url.scheme == "https" and not local,
            "endpoint_allowed": configuration_status()["endpoint_allowed"],
            "transport_allowed": url.scheme == "https" or (local and url.scheme == "http"),
            "vultr_host_location": "Requires independent VM evidence",
            "demo_video": "Must be recorded separately", "live_execution_verified": False}


async def run(report):
    cfg = settings()
    report["steps"] = []
    async with httpx.AsyncClient(base_url=cfg.app_base_url, timeout=30, follow_redirects=False) as client:
        async def call(path, method="GET", body=None):
            response = await client.request(method, "/api/v1" + path, json=body)
            if not response.is_success:
                raise RuntimeError(f"{method} {path} returned HTTP {response.status_code}; inspect the application timeline")
            return response.json()
        user = await call("/auth/login", "POST", {"username": cfg.operator_username, "password": cfg.operator_password})
        client.headers["X-CSRF-Token"] = user["csrf"]
        client.headers["Origin"] = cfg.app_base_url.rstrip("/")
        if user["role"] != "admin": raise RuntimeError("Administrator account required")
        async def job(path, payload=None, expected="VERIFIED"):
            queued = await call(path, "POST", payload)
            deadline = time.monotonic() + cfg.max_job_seconds + 120
            while time.monotonic() < deadline:
                value = await call("/tasks/" + queued["id"])
                if value["state"] not in {"QUEUED", "RUNNING"}: break
                await asyncio.sleep(2)
            else: raise RuntimeError("Job polling deadline reached; inspect before retrying")
            report["steps"].append({"job_id": value["id"], "kind": value["kind"], "state": value["state"],
                "evidence": cfg.app_base_url + "/api/v1/tasks/" + value["id"] + "/export/json"})
            if value["state"] != expected: raise RuntimeError(f"Job {value['id']} ended as {value['state']}")
            return value
        probe = await call("/system/inference-check", "POST")
        if not probe.get("live_inference_verified"): raise RuntimeError("Real inference probe did not pass")
        base = {"version": 1, "hostile": False, "timeout_after_write": False, "wrong_order": False, "access_denied": False}
        await call("/scenario", "POST", base)
        learned = await job("/operations/learn")
        if learned["result"].get("provider") != "Vultr": raise RuntimeError("Non-Vultr learning rejected")
        orders = {"orders": [{"order_id": "ORD-102", "expected_delivery": "2026-11-10"}], "mode": "reusable"}
        await job("/tasks", orders)
        ops = await call("/operations")
        write = next(x for x in ops if x["name"] == "submit_delivery_request")["versions"][0]
        await call("/operations/submit_delivery_request/review", "POST", {"version": write["number"], "digest": write["digest"]})
        draft = await call("/requests/prepare", "POST", {"order_id": "ORD-102", "message": "Live acceptance: please confirm the delivery date."})
        await call("/requests/" + draft["id"] + "/approve", "POST", {"digest": draft["digest"]})
        submitted = await job("/requests/" + draft["id"] + "/submit", {"digest": draft["digest"]})
        if not isinstance(submitted["result"].get("vision"), dict) or not submitted["result"]["vision"].get("consistent"):
            raise RuntimeError("Actual vision verification did not pass")
        await call("/scenario", "POST", {**base, "version": 2})
        await job("/tasks", orders, expected="PORTAL_CHANGED")
        repaired = await job("/operations/get_order_status/repair")
        if repaired["result"].get("provider") != "Vultr": raise RuntimeError("Non-Vultr repair rejected")
        await job("/tasks", orders)
        contained = await job("/containment", expected="SANDBOX_TERMINATED")
        if not contained["result"].get("cleanup"): raise RuntimeError("Sandbox cleanup unconfirmed")
        health = await client.get("/health/ready")
        health.raise_for_status()
        report["live_execution_verified"] = True
        report["vision_verified"] = True
        report["portal_left_at"] = 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", default="artifacts/live-acceptance.json")
    args = parser.parse_args()
    report = preflight()
    if not args.run:
        print(json.dumps(report, indent=2)); return 0
    if report["missing"] or not report["endpoint_allowed"] or not report["transport_allowed"]:
        print(json.dumps(report, indent=2)); return 2
    try: asyncio.run(run(report))
    except Exception as exc: report["error"] = type(exc).__name__ + ": " + str(exc)[:400]
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["live_execution_verified"] else 1


if __name__ == "__main__": raise SystemExit(main())
