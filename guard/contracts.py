"""Restricted workflow language and trusted policy. No executable model code."""
import hashlib
import json
import re
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

READ = "get_order_status"
PREPARE = "prepare_delivery_request"
WRITE = "submit_delivery_request"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Step(Strict):
    action: Literal["navigate", "fill", "click", "read", "wait_for", "screenshot"]
    target: str = Field(default="", max_length=80, pattern=r"^[a-zA-Z0-9_-]*$")
    path: str = Field(default="/", max_length=120)
    value_from: Literal["order_id", "message", "idempotency_key"] | None = None


class Workflow(Strict):
    steps: list[Step] = Field(min_length=1, max_length=12)


class Proposal(Strict):
    explanation: str = Field(max_length=800)
    done: bool
    step: Step | None = None


class OrderInput(Strict):
    order_id: str = Field(pattern=r"^ORD-[0-9]{3,8}$")
    expected_delivery: str

    @field_validator("expected_delivery")
    @classmethod
    def date_valid(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class SandboxSpec(Strict):
    execution_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    operation: Literal["get_order_status", "submit_delivery_request"]
    workflow: Workflow
    inputs: dict[str, str]
    approved: bool = False
    mode: Literal["execute", "observe", "containment"] = "execute"


class PolicyError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def canonical_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def contract(name: str) -> dict:
    from guard.config import settings
    return {
        "operation": name,
        "purpose": {READ: "Retrieve and independently verify supplier order status",
                    PREPARE: "Prepare an immutable local request preview",
                    WRITE: "Submit the exact approved delivery-update request"}[name],
        "allowed_origin": settings().portal_base_url,
        "permission": {READ: "READ", PREPARE: "LOCAL_PREPARATION", WRITE: "WRITE_WITH_APPROVAL"}[name],
        "approval_required": name == WRITE,
        "allowed_fields": ["order_id"] if name == READ else ["order_id", "message", "idempotency_key"],
        "allowed_actions": ["navigate", "fill", "click", "read", "wait_for", "screenshot"],
        "verification": ["identity", "persisted_state", "screenshot"],
        "max_steps": 12,
        "valid_for_seconds": 7 * 24 * 60 * 60,
        "input_schema": {"type": "object", "additionalProperties": False,
            "properties": {"order_id": {"type": "string", "pattern": "^ORD-[0-9]{3,8}$"},
                **({"message": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "idempotency_key": {"type": "string", "pattern": "^[a-f0-9]{32}$"}} if name != READ else {})},
            "required": ["order_id"] if name == READ else ["order_id", "message", "idempotency_key"]},
        "output_schema": {"type": "object", "required": ["status"],
            "properties": {"status": {"type": "string"}, "verified": {"type": "boolean"}}},
        "policy_revision": 1,
    }


def check_step(step: Step, operation: str, approved: bool = False) -> None:
    if operation not in (READ, WRITE):
        raise PolicyError("OPERATION_NOT_ALLOWED")
    if step.action == "navigate":
        # No model-controlled origin, redirects, query strings or request paths.
        if step.path != "/":
            raise PolicyError("NAVIGATION_NOT_ALLOWED")
    elif step.action == "fill":
        allowed = {"order_search": "order_id", "order_lookup": "order_id"}
        if operation == WRITE and approved:
            allowed.update({"message": "message", "idempotency_key": "idempotency_key"})
        if step.target not in allowed or step.value_from != allowed[step.target]:
            raise PolicyError("FIELD_NOT_ALLOWED")
    elif step.action == "click":
        allowed = {"search_button", "lookup_button"}
        if operation == WRITE and approved:
            allowed.add("submit_request")
        if step.target not in allowed:
            raise PolicyError("ACTION_NOT_ALLOWED")
    elif step.action in ("read", "wait_for"):
        if step.target not in {"order_details", "shipment_details", "not_found", "receipt", "request_history"}:
            raise PolicyError("READ_TARGET_NOT_ALLOWED")


def check_workflow(workflow: Workflow, operation: str, approved: bool = False) -> None:
    for step in workflow.steps:
        check_step(step, operation, approved)


def validate_inputs(inputs: dict, operation: str) -> None:
    if not re.fullmatch(r"ORD-\d{3,8}", inputs.get("order_id", "")):
        raise PolicyError("INVALID_ORDER_ID")
    allowed = {"order_id"}
    if operation == WRITE:
        allowed |= {"message", "idempotency_key"}
        if not 1 <= len(inputs.get("message", "")) <= 1000:
            raise PolicyError("INVALID_MESSAGE")
        if not re.fullmatch(r"[a-f0-9]{32}", inputs.get("idempotency_key", "")):
            raise PolicyError("INVALID_IDEMPOTENCY_KEY")
    if set(inputs) - allowed:
        raise PolicyError("UNAUTHORIZED_INPUT_FIELD")


def same_origin(url: str, origin: str) -> bool:
    a, b = urlsplit(url), urlsplit(origin)
    return (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port) and not a.username


def classify(expected: str, arrival: str | None, status: str) -> str:
    if status == "Canceled":
        return "CANCELED"
    if status not in {"In transit", "Processing", "Delivered"} or not arrival:
        return "UNKNOWN"
    return "DELAYED" if date.fromisoformat(arrival) > date.fromisoformat(expected) else "ON_TRACK"
