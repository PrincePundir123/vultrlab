"""Run inside a disposable probe container on skg-execution; no credentials needed."""
import socket


def reachable(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


assert reachable("172.30.90.2", 8090), "Portal must be reachable"
for host, port in [("172.30.90.1", 22), ("169.254.169.254", 80), ("1.1.1.1", 443), ("172.30.90.2", 8091)]:
    assert not reachable(host, port), f"Unauthorized network access: {host}:{port}"
print("Portal reachable; host, metadata, public egress and admin port probes blocked.")
