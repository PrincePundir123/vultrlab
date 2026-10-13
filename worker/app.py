"""Trusted Docker supervisor. Not exposed on the public listener."""
import asyncio
import hmac
import json
import threading
import time
from pathlib import Path
from contextlib import asynccontextmanager, closing

import docker
from fastapi import FastAPI, Header, HTTPException

from guard.config import settings
from guard.contracts import SandboxSpec, check_workflow, validate_inputs

LIMIT = 4 * 1024 * 1024
slots = threading.BoundedSemaphore(2)


def client():
    return closing(docker.from_env(timeout=10))


def authenticate(secret):
    expected = settings().worker_shared_auth_secret
    if len(expected) < 32 or not hmac.compare_digest(expected, secret):
        raise HTTPException(401, "Worker authentication required")


def reap():
    with client() as c:
        for box in c.containers.list(all=True, filters={"label": "skg.sandbox=true"}):
            deadline = float(box.labels.get("skg.deadline", "0"))
            if deadline < time.time():
                box.remove(force=True)


@asynccontextmanager
async def lifespan(app):
    async def cleanup_loop():
        while True:
            try:
                await asyncio.to_thread(reap)
            except Exception:
                pass  # Readiness exposes daemon failures; no fabricated availability.
            await asyncio.sleep(15)
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="Guard trusted worker", lifespan=lifespan)


def run_sandbox(spec: SandboxSpec) -> dict:
    cfg = settings()
    check_workflow(spec.workflow, spec.operation, spec.approved)
    validate_inputs(spec.inputs, spec.operation)
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "Worker capacity reached")
    box = None
    started = time.monotonic()
    result = {"status": "SANDBOX_FAILED", "screenshots": [], "trace": []}
    deadline = min(cfg.sandbox_deadline, 8) if spec.mode == "containment" else cfg.sandbox_deadline
    try:
        with client() as c:
            network = c.networks.get(cfg.sandbox_network)
            if not network.attrs.get("Internal"):
                raise RuntimeError("Execution network must be internal")
            if network.attrs.get("Labels", {}).get("skg.egress") != "portal-only":
                raise RuntimeError("Execution network must have installed portal-only firewall policy")
            profile = json.loads(Path("/app/infra/security/seccomp_profile.json").read_text())
            command = ["python", "-c", "import time\nwhile True: time.sleep(1)"] if spec.mode == "containment" else ["python", "-m", "runner.main"]
            box = c.containers.create(cfg.sandbox_image, command,
                name="skg-run-" + spec.execution_id, user="10001:10001", init=True,
                read_only=True, cap_drop=["ALL"], security_opt=["no-new-privileges:true", "seccomp=" + json.dumps(profile)],
                mem_limit="1536m", memswap_limit="1536m", nano_cpus=1_000_000_000, pids_limit=256,
                shm_size="256m", tmpfs={"/tmp": "rw,noexec,nosuid,size=256m,mode=1777"},
                network=cfg.sandbox_network, environment={"PORTAL_BASE_URL": cfg.portal_base_url,
                    "HOME": "/tmp", "PYTHONDONTWRITEBYTECODE": "1", "SKG_JOB_JSON": spec.model_dump_json()},
                detach=True,
                labels={"skg.sandbox": "true", "skg.deadline": str(time.time() + deadline + 15)},
                log_config=docker.types.LogConfig(type="json-file", config={"max-size": "5m", "max-file": "1"}))
            box.start()
            startup_ms = round((time.monotonic() - started) * 1000)
            end = time.monotonic() + deadline
            while True:
                box.reload()
                if box.status not in ("created", "running"):
                    break
                if time.monotonic() >= end:
                    box.kill()
                    result = {"status": "SANDBOX_TERMINATED", "reason": "DEADLINE", "screenshots": [], "trace": []}
                    break
                time.sleep(0.2)
            else:
                pass
            if result["status"] != "SANDBOX_TERMINATED":
                data = box.logs(stdout=True, stderr=False)
                box.reload()
                if len(data) > LIMIT:
                    result["reason"] = "OUTPUT_LIMIT"
                elif box.attrs["State"].get("OOMKilled"):
                    result["status"] = "SANDBOX_TERMINATED"
                    result["reason"] = "MEMORY_LIMIT"
                elif box.attrs["State"]["ExitCode"] != 0:
                    result["error"] = box.logs(stdout=False, stderr=True)[-3000:].decode(errors="replace")
                else:
                    result = json.loads(data)
            result["sandbox"] = {"id": box.id, "startup_ms": startup_ms, "deadline_seconds": deadline,
                                 "memory_mb": 1536, "cpus": 1}
    finally:
        if box:
            try:
                box.remove(force=True)
                result["cleanup"] = True
            except Exception:
                result["cleanup"] = False
        slots.release()
    result["total_ms"] = round((time.monotonic() - started) * 1000)
    return result


@app.post("/execute")
def execute(spec: SandboxSpec, x_worker_secret: str = Header(default="")):
    authenticate(x_worker_secret)
    return run_sandbox(spec)


@app.get("/health/ready")
def ready(x_worker_secret: str = Header(default="")):
    authenticate(x_worker_secret)
    try:
        with client() as c:
            c.ping()
            c.images.get(settings().sandbox_image)
            network = c.networks.get(settings().sandbox_network)
            if not network.attrs.get("Internal"):
                raise ValueError("Network is not internal")
        return {"ready": True}
    except Exception as exc:
        raise HTTPException(503, str(exc)[:200])
