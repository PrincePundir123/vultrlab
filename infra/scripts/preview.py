"""Local UI/API preview. Does not replace or simulate the Docker worker."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
os.chdir(root)
sys.path.insert(0, str(root))
os.environ.update({"DATABASE_URL": "sqlite:///./preview.db", "PORTAL_DATABASE_URL": "sqlite:///./preview-portal.db",
    "APP_BASE_URL": "http://localhost:5173", "PORTAL_INTERNAL_URL": "http://127.0.0.1:8091",
    "WORKER_INTERNAL_URL": "http://127.0.0.1:8092", "ARTIFACT_DIR": "./artifacts", "COOKIE_SECURE": "false"})
from guard.db import Base, engine
Base.metadata.create_all(engine())
children = []
flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
try:
    for target, port in [("guard.api:app", 8000), ("portal.app:admin", 8091), ("portal.app:app", 8090)]:
        children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", target, "--host", "127.0.0.1", "--port", str(port)], creationflags=flags))
    print("API/portal preview running. Start frontend separately. Docker execution remains required.", flush=True)
    children[0].wait()
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait(timeout=10)
