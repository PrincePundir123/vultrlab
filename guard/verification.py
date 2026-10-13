"""Independent checks use protected persisted portal state as their answer key."""
import httpx
from guard.config import settings


async def portal_truth(path: str, body: dict | None = None) -> dict:
    cfg = settings()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.request("POST" if body is not None else "GET", cfg.portal_internal_url + path,
            headers={"X-Internal-Secret": cfg.portal_admin_secret}, json=body)
        response.raise_for_status()
        return response.json()


def verify_read(order_id: str, observed: dict, truth: dict) -> dict:
    if observed.get("status") != "OBSERVED":
        return {"status": observed.get("status", "VALIDATION_FAILED"), "verified": False}
    evidence = bool(observed.get("screenshots") or observed.get("artifact_ids"))
    if not truth["found"]:
        ok = bool(observed.get("not_found")) and evidence
        return {"status": "NOT_FOUND" if ok else "VALIDATION_FAILED", "verified": ok, "order_id": order_id}
    fields = observed.get("fields", {})
    actual = truth["order"]
    checks = {"identity": fields.get("order_id") == order_id == actual["order_id"],
              "arrival": fields.get("arrival") == (actual["arrival"] or "Unknown"),
              "status": fields.get("status") == actual["status"], "evidence": evidence}
    ok = all(checks.values())
    return {"status": "VERIFIED" if ok else "VALIDATION_FAILED", "verified": ok, "checks": checks,
            "order_id": order_id, "order": actual if ok else None}


def verify_write(snapshot: dict, truth: dict, evidence: bool) -> dict:
    record = truth.get("request") or {}
    checks = {"persisted": truth.get("found", False), "order_id": record.get("order_id") == snapshot["order_id"],
              "message": record.get("message") == snapshot["message"],
              "idempotency_key": record.get("key") == snapshot["idempotency_key"],
              "reference": bool(record.get("reference")), "evidence": evidence}
    return {"status": "VERIFIED" if all(checks.values()) else "OUTCOME_UNCERTAIN",
            "verified": all(checks.values()), "checks": checks, "persisted_record": record,
            "vision": "NOT_RUN"}
