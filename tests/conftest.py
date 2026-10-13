import os
import tempfile
from pathlib import Path

_temp = tempfile.TemporaryDirectory(prefix="skg-tests-")
os.environ.update({"DATABASE_URL": "sqlite:///" + str(Path(_temp.name) / "guard.db"),
    "PORTAL_DATABASE_URL": "sqlite:///" + str(Path(_temp.name) / "portal.db"),
    "SESSION_SECRET": "test-session-secret-" * 3, "OPERATOR_PASSWORD": "test-password-for-unit-tests",
    "PORTAL_ADMIN_SECRET": "test-portal-secret-" * 3,
    "WORKER_SHARED_AUTH_SECRET": "test-worker-secret-" * 3,
    "ARTIFACT_DIR": str(Path(_temp.name) / "artifacts")})

import pytest
from fastapi.testclient import TestClient
from guard.db import Base, engine
from guard.api import app
from portal.app import initialize, portal_engine, PortalBase


@pytest.fixture(scope="session", autouse=True)
def dispose_databases():
    yield
    engine().dispose()
    portal_engine.dispose()
    _temp.cleanup()


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())
    PortalBase.metadata.drop_all(portal_engine)
    initialize()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        response = c.post("/api/v1/auth/login", json={"username": "operator", "password": "test-password-for-unit-tests"})
        assert response.status_code == 200
        c.headers["X-CSRF-Token"] = response.json()["csrf"]
        yield c
