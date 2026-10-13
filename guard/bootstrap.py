from argon2 import PasswordHasher
from sqlalchemy import select

from guard.config import settings
from guard.contracts import READ, PREPARE, WRITE, canonical_hash, contract
from guard.db import Operation, Regression, User, Version, db


def bootstrap():
    cfg = settings()
    if len(cfg.operator_password) < 12:
        raise RuntimeError("Set OPERATOR_PASSWORD to at least 12 characters")
    if len(cfg.session_secret) < 32:
        raise RuntimeError("Set SESSION_SECRET to at least 32 characters")
    with db() as s:
        if not s.scalar(select(User).where(User.username == cfg.operator_username)):
            s.add(User(username=cfg.operator_username, password_hash=PasswordHasher().hash(cfg.operator_password),
                       role="admin"))
        for name in (READ, PREPARE, WRITE):
            if not s.get(Operation, name):
                s.add(Operation(name=name, state="ACTIVE" if name == PREPARE else "DRAFT",
                                active_version=1 if name == PREPARE else None))
                s.flush()
                if name == PREPARE:
                    definition = {"implementation": "trusted_local_preparation_v1"}
                    s.add(Version(operation=name, number=1, definition=definition, contract=contract(name),
                                  digest=canonical_hash(definition)))
        if not s.scalar(select(Regression).limit(1)):
            for order_id, held, text in [("ORD-101", False, "On-time"), ("ORD-102", False, "Delayed"),
                                         ("ORD-103", False, "Missing arrival"), ("ORD-999", False, "Unknown"),
                                         ("ORD-104", True, "Held-out delayed"), ("ORD-107", True, "Canceled")]:
                s.add(Regression(operation=READ, inputs={"order_id": order_id}, held_out=held, description=text))
        s.commit()


if __name__ == "__main__":
    bootstrap()
