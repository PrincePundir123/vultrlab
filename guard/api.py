import asyncio
import csv
import io
import json
import time
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import Field
from sqlalchemy import select, update, func

from guard import auth
from guard.readiness import configuration_status, model_catalog, probe_inference
from guard.inference import InferenceUnavailable
from guard.bootstrap import bootstrap
from guard.config import settings
from guard.contracts import READ, WRITE, OrderInput, Strict, Workflow, PolicyError, canonical_hash, check_workflow
from guard.db import (Artifact, Audit, Draft, Job, JobEvent, Operation, Receipt, Session,
                      User, Validation, Version, db, uid)
from guard.orchestration import active_version
from guard.verification import portal_truth
from portal.app import ScenarioInput


@asynccontextmanager
async def lifespan(app):
    bootstrap()
    yield


app = FastAPI(title="Skeleton Key Guard", version="0.1.0", lifespan=lifespan)
prefix = "/api/v1"


@app.middleware("http")
async def headers(request: Request, call_next):
    request_id = uid()
    response = await call_next(request)
    response.headers.update({"X-Request-ID": request_id, "X-Content-Type-Options": "nosniff",
                            "Referrer-Policy": "same-origin", "Cache-Control": "no-store"})
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse({"error": {"code": exc.status_code, "message": exc.detail}}, status_code=exc.status_code)


@app.exception_handler(PolicyError)
async def policy_error(request, exc):
    return JSONResponse({"error": {"code": exc.code, "message": str(exc)}}, status_code=409)


def audit(user: User, kind: str, detail: dict):
    with db() as s:
        s.add(Audit(owner_id=user.id, kind=kind, detail=detail))
        s.commit()


def owned(s, cls, item_id, user):
    item = s.get(cls, item_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(404, "Record not found")
    return item


def serialize_job(job):
    return {"id": job.id, "kind": job.kind, "state": job.state, "payload": job.payload,
            "result": job.result, "created": job.created, "finished": job.finished}


def enqueue(user: User, kind: str, payload: dict):
    with db() as s:
        if s.scalar(select(func.count()).select_from(Job).where(Job.owner_id == user.id,
            Job.state.in_(["QUEUED", "RUNNING"]))) >= 5:
            raise HTTPException(429, "At most five outstanding jobs per operator")
        job = Job(owner_id=user.id, kind=kind, payload=payload)
        s.add(job)
        s.commit()
        return serialize_job(job)


class Login(Strict):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


@app.post(prefix + "/auth/login")
def login(body: Login, request: Request, response: Response):
    if request.headers.get("origin") not in (None, settings().app_base_url.rstrip("/")):
        raise HTTPException(403, "Origin not allowed")
    return auth.login(body.username, body.password, request, response)


class Signup(Strict):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-z][a-z0-9_-]{2,39}$")
    password: str = Field(min_length=12, max_length=200)


@app.post(prefix + "/auth/register", status_code=201)
def register(body: Signup, request: Request, response: Response):
    if request.headers.get("origin") not in (None, settings().app_base_url.rstrip("/")):
        raise HTTPException(403, "Origin not allowed")
    return auth.register(body.username, body.password, request, response)


@app.get(prefix + "/auth/me")
def me(request: Request, user: User = Depends(auth.current_user)):
    with db() as s:
        session = s.get(Session, auth.digest(request.cookies["skg_session"]))
        return {"id": user.id, "username": user.username, "role": user.role, "csrf": session.csrf}


@app.post(prefix + "/auth/logout")
def logout(request: Request, response: Response, user: User = Depends(auth.current_user)):
    with db() as s:
        session = s.get(Session, auth.digest(request.cookies["skg_session"]))
        s.delete(session)
        s.commit()
    response.delete_cookie("skg_session")
    return {"ok": True}


@app.post(prefix + "/orders/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(auth.current_user)):
    content = await file.read(65537)
    if len(content) > 65536:
        raise HTTPException(413, "CSV must be smaller than 64 KiB")
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        if reader.fieldnames != ["order_id", "expected_delivery"]:
            raise ValueError("CSV headers must be order_id,expected_delivery")
        rows = [OrderInput.model_validate(row).model_dump() for row in reader]
        if not 1 <= len(rows) <= 20:
            raise ValueError("Upload between 1 and 20 orders")
        if len({x["order_id"] for x in rows}) != len(rows):
            raise ValueError("Duplicate order IDs are not allowed")
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)[:500])
    return {"orders": rows, "synthetic": True}


class TaskInput(Strict):
    orders: list[OrderInput] = Field(min_length=1, max_length=20)
    goal: str = Field(default="Check delivery delays", max_length=500)
    mode: str = Field(default="reusable", pattern="^(reusable|baseline)$")


@app.post(prefix + "/tasks")
def create_task(body: TaskInput, user: User = Depends(auth.current_user)):
    if body.mode == "baseline":
        auth.require_admin(user)
    return enqueue(user, "read", body.model_dump())


@app.get(prefix + "/tasks")
def tasks(offset: int = 0, user: User = Depends(auth.current_user)):
    with db() as s:
        return [serialize_job(x) for x in s.scalars(select(Job).where(Job.owner_id == user.id)
            .order_by(Job.created.desc()).offset(max(offset, 0)).limit(50))]


@app.get(prefix + "/tasks/{job_id}")
def task(job_id: str, user: User = Depends(auth.current_user)):
    with db() as s:
        return serialize_job(owned(s, Job, job_id, user))


@app.post(prefix + "/tasks/{job_id}/cancel")
def cancel(job_id: str, user: User = Depends(auth.current_user)):
    with db() as s:
        job = owned(s, Job, job_id, user)
        if job.kind == "submit" and job.state != "QUEUED":
            raise HTTPException(409, "A dispatched write must finish reconciliation")
        job.cancel_requested = True
        if job.state == "QUEUED":
            job.state = "CANCELED"
            job.finished = time.time()
            if job.kind == "submit":
                s.get(Draft, job.payload["draft_id"]).state = "CANCELED"
        s.commit()
    return {"status": "Cancellation requested"}


@app.get(prefix + "/tasks/{job_id}/events")
async def events(job_id: str, request: Request, after: int = 0, user: User = Depends(auth.current_user)):
    with db() as s:
        owned(s, Job, job_id, user)
    async def stream():
        cursor = max(after, int(request.headers.get("last-event-id", "0")))
        for _ in range(300):
            if await request.is_disconnected():
                return
            with db() as s:
                rows = list(s.scalars(select(JobEvent).where(JobEvent.job_id == job_id, JobEvent.id > cursor)
                                     .order_by(JobEvent.id).limit(100)))
                job = s.get(Job, job_id)
            for row in rows:
                cursor = row.id
                yield f'id: {row.id}\ndata: {json.dumps({"id": row.id, "kind": row.kind, "data": row.data, "created": row.created})}\n\n'
            if job.state not in ("QUEUED", "RUNNING") and not rows:
                yield 'event: complete\ndata: {}\n\n'
                return
            yield ': heartbeat\n\n'
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.get(prefix + "/operations")
def operations(user: User = Depends(auth.current_user)):
    with db() as s:
        output = []
        for op in s.scalars(select(Operation)):
            versions = list(s.scalars(select(Version).where(Version.operation == op.name).order_by(Version.number.desc())))
            output.append({"name": op.name, "state": op.state, "active_version": op.active_version,
                "history": op.history, "versions": [{"id": v.id, "number": v.number, "definition": v.definition,
                    "contract": v.contract, "digest": v.digest, "created": v.created,
                    "expires": v.created + v.contract.get("valid_for_seconds", 0),
                    "validations": [{"passed": t.passed, "details": t.details} for t in
                        s.scalars(select(Validation).where(Validation.version_id == v.id))]} for v in versions]})
        return output


@app.post(prefix + "/operations/learn")
def learn(user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    return enqueue(user, "learn", {})


@app.post(prefix + "/operations/{name}/repair")
def repair(name: str, user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    if name != READ:
        raise HTTPException(422, "Automatic repair is limited to the read operation")
    return enqueue(user, "repair", {})


@app.post(prefix + "/operations/{name}/validate")
def validate(name: str, user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    if name != READ:
        raise HTTPException(422, "Use explicit write-version review")
    return enqueue(user, "validate", {})


class VersionReview(Strict):
    version: int
    digest: str = Field(min_length=64, max_length=64)


@app.post(prefix + "/operations/submit_delivery_request/review")
def review_write(body: VersionReview, user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    active_version(READ)
    with db() as s:
        version = s.scalar(select(Version).where(Version.operation == WRITE, Version.number == body.version))
        latest = s.scalar(select(func.max(Version.number)).where(Version.operation == WRITE))
        if not version or body.version != latest or version.digest != body.digest:
            raise HTTPException(409, "Review must match the newest exact candidate")
        check_workflow(Workflow.model_validate(version.definition), WRITE, True)
        op = s.get(Operation, WRITE)
        op.active_version, op.state = version.number, "ACTIVE"
        op.history = op.history + [{"state": "ACTIVE", "reason": "Explicit operator review; each write still requires approval", "at": time.time()}]
        s.commit()
    audit(user, "WRITE_VERSION_REVIEWED", body.model_dump())
    return {"state": "ACTIVE"}


class PrepareInput(Strict):
    order_id: str = Field(pattern=r"^ORD-\d{3,8}$")
    message: str = Field(min_length=1, max_length=1000)


@app.post(prefix + "/requests/prepare")
async def prepare(body: PrepareInput, user: User = Depends(auth.current_user)):
    auth.require_operator(user)
    truth = await portal_truth("/orders/" + body.order_id)
    if not truth["found"]:
        raise HTTPException(404, "Order does not exist")
    try:
        version = active_version(WRITE)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    snapshot = {**body.model_dump(), "version": version.number, "definition_hash": version.digest,
                "contract_hash": canonical_hash(version.contract),
                "operation": WRITE, "idempotency_key": uid(), "owner_id": user.id,
                "portal_origin": settings().portal_base_url, "policy_revision": 1}
    with db() as s:
        draft = Draft(owner_id=user.id, snapshot=snapshot, digest=canonical_hash(snapshot))
        s.add(draft)
        s.commit()
        return {"id": draft.id, "snapshot": snapshot, "digest": draft.digest, "state": draft.state}


@app.get(prefix + "/requests")
def requests(user: User = Depends(auth.current_user)):
    with db() as s:
        return [{"id": d.id, "snapshot": d.snapshot, "digest": d.digest, "state": d.state,
                 "expires": d.expires, "approved_by": d.approved_by, "job_id": d.job_id} for d in
                s.scalars(select(Draft).where(Draft.owner_id == user.id).order_by(Draft.created.desc()).limit(100))]


class ApprovalInput(Strict):
    digest: str = Field(min_length=64, max_length=64)


@app.post(prefix + "/requests/{draft_id}/approve")
def approve(draft_id: str, body: ApprovalInput, user: User = Depends(auth.current_user)):
    auth.require_operator(user)
    with db() as s:
        draft = owned(s, Draft, draft_id, user)
        if body.digest != draft.digest or canonical_hash(draft.snapshot) != draft.digest:
            raise HTTPException(409, "Approval snapshot changed")
        changed = s.execute(update(Draft).where(Draft.id == draft_id, Draft.state == "AWAITING_APPROVAL")
                            .values(state="APPROVED", approved_by=user.id, expires=time.time() + 600))
        s.commit()
        if changed.rowcount != 1:
            raise HTTPException(409, "Request cannot be approved in its current state")
    audit(user, "APPROVED", {"draft_id": draft_id, "digest": body.digest})
    return {"state": "APPROVED", "valid_seconds": 600}


@app.post(prefix + "/requests/{draft_id}/reject")
def reject(draft_id: str, user: User = Depends(auth.current_user)):
    auth.require_operator(user)
    with db() as s:
        owned(s, Draft, draft_id, user)
        changed = s.execute(update(Draft).where(Draft.id == draft_id, Draft.state.in_(["AWAITING_APPROVAL", "APPROVED"]),
                            Draft.consumed.is_(False)).values(state="REJECTED"))
        s.commit()
        if changed.rowcount != 1:
            raise HTTPException(409, "A dispatched request cannot be rejected")
    return {"state": "REJECTED"}


@app.post(prefix + "/requests/{draft_id}/submit")
def submit(draft_id: str, body: ApprovalInput, user: User = Depends(auth.current_user)):
    auth.require_operator(user)
    try:
        version = active_version(WRITE)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    with db() as s:
        draft = owned(s, Draft, draft_id, user)
        if draft.digest != body.digest or draft.digest != canonical_hash(draft.snapshot):
            raise HTTPException(409, "Approval snapshot mismatch")
        if draft.snapshot["version"] != version.number or draft.snapshot["definition_hash"] != version.digest:
            raise HTTPException(409, "Operation changed; prepare and approve a new request")
        job = Job(owner_id=user.id, kind="submit", payload={"draft_id": draft_id})
        s.add(job)
        s.flush()
        changed = s.execute(update(Draft).where(Draft.id == draft_id, Draft.state == "APPROVED",
            Draft.consumed.is_(False), Draft.expires > time.time(), Draft.approved_by == user.id)
            .values(consumed=True, state="EXECUTING", job_id=job.id))
        if changed.rowcount != 1:
            s.rollback()
            raise HTTPException(409, "Approval expired, consumed, or absent")
        s.commit()
        return serialize_job(job)


@app.get(prefix + "/artifacts/{artifact_id}")
def artifact(artifact_id: str, user: User = Depends(auth.current_user)):
    with db() as s:
        item = owned(s, Artifact, artifact_id, user)
        path = Path(settings().artifact_dir) / item.filename
        if not path.is_file():
            raise HTTPException(410, "Evidence file is no longer available")
        content = path.read_bytes()
        if len(content) != item.size or hashlib.sha256(content).hexdigest() != item.digest:
            raise HTTPException(409, "Evidence integrity check failed")
        return Response(content, media_type="image/png")


@app.post(prefix + "/requests/{draft_id}/reconcile")
def reconcile(draft_id: str, user: User = Depends(auth.current_user)):
    auth.require_operator(user)
    with db() as s:
        draft = owned(s, Draft, draft_id, user)
        if draft.state != "OUTCOME_UNCERTAIN":
            raise HTTPException(409, "Only uncertain submissions can be reconciled")
        job = Job(owner_id=user.id, kind="reconcile", payload={"draft_id": draft_id})
        s.add(job)
        s.flush()
        changed = s.execute(update(Draft).where(Draft.id == draft_id, Draft.state == "OUTCOME_UNCERTAIN")
                            .values(state="VERIFYING", job_id=job.id))
        if changed.rowcount != 1:
            s.rollback()
            raise HTTPException(409, "Reconciliation already started")
        s.commit()
        return serialize_job(job)


@app.get(prefix + "/receipts")
def receipts(user: User = Depends(auth.current_user)):
    with db() as s:
        return [{"id": x.id, "job_id": x.job_id, "result": x.result, "digest": x.digest} for x in
                s.scalars(select(Receipt).where(Receipt.owner_id == user.id).order_by(Receipt.created.desc()).limit(100))]


@app.get(prefix + "/tasks/{job_id}/export/{format}")
def export(job_id: str, format: str, user: User = Depends(auth.current_user)):
    with db() as s:
        job = owned(s, Job, job_id, user)
        if format == "json":
            return Response(json.dumps(serialize_job(job), indent=2), media_type="application/json",
                            headers={"Content-Disposition": f'attachment; filename="{job_id}.json"'})
        if format != "csv":
            raise HTTPException(404, "Unknown format")
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(["order_id", "classification", "verification", "request_reference", "message"])
        for row in job.result.get("rows", []):
            writer.writerow([row.get("order_id"), row.get("classification"), row.get("status"), "", ""])
        record = job.result.get("persisted_record")
        if record:
            message = record.get("message", "")
            if message.lstrip().startswith(("=", "+", "-", "@")):
                message = "'" + message
            writer.writerow([record.get("order_id"), "DELIVERY_REQUEST", job.result.get("status"), record.get("reference"), message])
        return Response(text.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'})


@app.get(prefix + "/scenario")
async def scenario(user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    return await portal_truth("/scenario")


@app.post(prefix + "/scenario")
async def change_scenario(body: ScenarioInput, user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    with db() as s:
        if s.scalar(select(Job.id).where(Job.state.in_(["RUNNING", "QUEUED"])).limit(1)):
            raise HTTPException(409, "Wait until jobs finish before changing the portal scenario")
    result = await portal_truth("/scenario", body.model_dump())
    audit(user, "SCENARIO_CHANGED", result)
    return result


@app.post(prefix + "/containment")
def containment(user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    return enqueue(user, "containment", {})


@app.get(prefix + "/audit-events")
def audit_events(user: User = Depends(auth.current_user)):
    with db() as s:
        return [{"id": x.id, "kind": x.kind, "detail": x.detail, "created": x.created} for x in
                s.scalars(select(Audit).where(Audit.owner_id == user.id).order_by(Audit.created.desc()).limit(100))]


@app.get(prefix + "/metrics")
@app.get(prefix + "/benchmarks")
def metrics(user: User = Depends(auth.current_user)):
    with db() as s:
        jobs = list(s.scalars(select(Job).where(Job.owner_id == user.id).order_by(Job.created.desc()).limit(1000)))
        events = list(s.scalars(select(JobEvent).join(Job).where(Job.owner_id == user.id, JobEvent.kind == "INFERENCE")))
        measurements = [{"job_id": j.id, "mode": j.payload.get("mode", j.kind), "state": j.state,
                         "duration_ms": round((j.finished - j.created) * 1000), "orders": len(j.payload.get("orders", []))}
                        for j in jobs if j.finished]
        return {"measurements": measurements, "total_jobs": len(jobs),
                "verified_jobs": sum(j.state == "VERIFIED" for j in jobs),
                "inference_calls": len(events), "inference_usage": [e.data for e in events],
                "pricing": "Not configured; no cost estimate", "benchmark_note": "Observed runs, including queue time. Not a controlled performance claim."}


@app.get(prefix + "/system")
async def system(user: User = Depends(auth.current_user)):
    cfg = settings()
    worker = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(cfg.worker_internal_url + "/health/ready",
                headers={"X-Worker-Secret": cfg.worker_shared_auth_secret})
            worker = response.is_success
    except httpx.HTTPError:
        pass
    return {"worker_ready": worker, "inference_configured": bool(cfg.vultr_inference_api_key and cfg.vultr_chat_model),
            "vision_configured": bool(cfg.vultr_inference_api_key and cfg.vultr_vision_model), "synthetic": True,
            "deployment": "Configured runtime; cloud location not independently attested"}


@app.get(prefix + "/system/provider")
def provider_configuration(user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    return configuration_status()


@app.get(prefix + "/system/models")
async def provider_models(user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    try:
        return await model_catalog()
    except InferenceUnavailable as exc:
        raise HTTPException(503, str(exc))


@app.post(prefix + "/system/inference-check")
async def provider_check(user: User = Depends(auth.current_user)):
    auth.require_admin(user)
    try:
        result = await probe_inference()
    except InferenceUnavailable as exc:
        audit(user, "INFERENCE_PREFLIGHT_FAILED", {"reason": str(exc)})
        raise HTTPException(503, str(exc))
    audit(user, "INFERENCE_PREFLIGHT", result)
    return result


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    with db() as s:
        s.scalar(select(func.count()).select_from(User))
    return {"status": "ok"}
