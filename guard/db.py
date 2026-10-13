import time
import uuid
from functools import lru_cache

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from guard.config import settings


def uid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="operator")


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[float] = mapped_column(Float)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    source: Mapped[str] = mapped_column(String(100), index=True)
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Operation(Base):
    __tablename__ = "operations"
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    state: Mapped[str] = mapped_column(String(30), default="DRAFT")
    active_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    history: Mapped[list] = mapped_column(JSON, default=list)


class Version(Base):
    __tablename__ = "operation_versions"
    __table_args__ = (UniqueConstraint("operation", "number"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    operation: Mapped[str] = mapped_column(ForeignKey("operations.name"))
    number: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)
    contract: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    created: Mapped[float] = mapped_column(Float, default=time.time)


@event.listens_for(Version, "before_update")
def immutable_version(mapper, connection, target):
    raise ValueError("Operation version definitions are immutable")


class Regression(Base):
    __tablename__ = "regressions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    operation: Mapped[str] = mapped_column(ForeignKey("operations.name"))
    inputs: Mapped[dict] = mapped_column(JSON)
    held_out: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text)


class Validation(Base):
    __tablename__ = "validations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("operation_versions.id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    details: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(40), default="QUEUED", index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    lease_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=time.time)
    finished: Mapped[float | None] = mapped_column(Float, nullable=True)


class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Draft(Base):
    __tablename__ = "delivery_requests"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(40), default="AWAITING_APPROVAL")
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires: Mapped[float] = mapped_column(Float, default=0)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, unique=True)
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Receipt(Base):
    __tablename__ = "receipts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    result: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    created: Mapped[float] = mapped_column(Float, default=time.time)


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(100))
    digest: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=time.time)


@lru_cache
def engine():
    url = settings().database_url
    result = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
                           pool_pre_ping=True)
    if url.startswith("sqlite"):
        @event.listens_for(result, "connect")
        def sqlite_config(conn, record):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    return result


def db():
    return sessionmaker(engine(), expire_on_commit=False)()
