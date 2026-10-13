"""Real Docker boundary probes using service image, not browser acceptance.

Run inside the trusted worker. No generated code or real business data involved.
"""
import json
import time
from guard.config import settings
from guard.contracts import SandboxSpec, Step, Workflow
from guard.db import uid
from worker.app import client, reap, run_sandbox


def main():
    cfg = settings()
    cfg.sandbox_image = "skg-service:local"
    result = run_sandbox(SandboxSpec(execution_id=uid(), operation="get_order_status",
        workflow=Workflow(steps=[Step(action="navigate")]), inputs={"order_id": "ORD-101"}, mode="containment"))
    assert result["status"] == "SANDBOX_TERMINATED" and result["cleanup"], result
    results = [{"test": "supervisor_deadline", **result}]
    with client() as c:
        code = "import socket,json\nr=[]\nfor host,port in [('172.30.90.2',8090),('172.30.90.1',22),('169.254.169.254',80),('1.1.1.1',443),('172.30.90.2',8091)]:\n try:\n  s=socket.create_connection((host,port),timeout=2);s.close();r.append(True)\n except OSError:r.append(False)\nprint(json.dumps(r))"
        raw = c.containers.run("skg-service:local", ["python", "-c", code], user="10001:10001",
            network=cfg.sandbox_network, cap_drop=["ALL"], read_only=True, mem_limit="128m", remove=True)
        access = json.loads(raw)
        assert access == [True, False, False, False, False], access
        results.append({"test": "network_boundary", "portal_host_metadata_public_admin": access})
        box = c.containers.create("skg-service:local", ["python", "-c", "x=bytearray(512*1024*1024)"],
            network="none", user="10001:10001", cap_drop=["ALL"], read_only=True, mem_limit="64m", memswap_limit="64m")
        try:
            box.start()
            box.wait(timeout=15)
            box.reload()
            assert box.attrs["State"]["OOMKilled"], box.attrs["State"]
            results.append({"test": "memory_limit", "oom_killed": True})
        finally:
            box.remove(force=True)
        box = c.containers.run("skg-service:local", ["python", "-c", "import time;time.sleep(120)"],
            detach=True, network="none", labels={"skg.sandbox": "true", "skg.deadline": str(time.time()-1)})
        ident = box.id
        reap()
        assert not c.containers.list(all=True, filters={"id": ident})
        results.append({"test": "orphan_cleanup", "removed": True})
    print(json.dumps({"scope": "Real Docker supervisor/resource/network probes; not browser workflow acceptance", "results": results}, indent=2))


if __name__ == "__main__":
    main()
