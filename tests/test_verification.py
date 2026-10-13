from guard.verification import verify_read, verify_write


def test_wrong_order_and_false_success_do_not_verify():
    truth = {"found": True, "order": {"order_id": "ORD-102", "arrival": "2026-11-13", "status": "In transit"}}
    observed = {"status": "OBSERVED", "success": True, "fields": {"order_id": "ORD-101", "arrival": "2026-11-13", "status": "In transit"}, "artifact_ids": ["real-id"]}
    assert not verify_read("ORD-102", observed, truth)["verified"]
    observed["fields"]["order_id"] = "ORD-102"
    assert verify_read("ORD-102", observed, truth)["verified"]
    observed["artifact_ids"] = []
    assert not verify_read("ORD-102", observed, truth)["verified"]


def test_write_requires_persistence_exact_values_and_evidence():
    snapshot = {"order_id": "ORD-102", "message": "Please update", "idempotency_key": "a" * 32}
    truth = {"found": True, "request": {"order_id": "ORD-102", "message": "Please update", "key": "a" * 32, "reference": "REQ-1"}}
    assert verify_write(snapshot, truth, True)["status"] == "VERIFIED"
    assert verify_write(snapshot, truth, False)["status"] == "OUTCOME_UNCERTAIN"
    truth["request"]["message"] = "Different text"
    assert not verify_write(snapshot, truth, True)["verified"]
