import pytest
from pydantic import ValidationError
from guard.contracts import READ, WRITE, PolicyError, Step, Workflow, check_step, canonical_hash, classify, same_origin


@pytest.mark.parametrize("step", [
    Step(action="navigate", path="http://169.254.169.254"),
    Step(action="navigate", path="//evil.test"),
    Step(action="click", target="submit_request"),
    Step(action="click", target="cancel_order"),
    Step(action="fill", target="message", value_from="message"),
    Step(action="fill", target="order_search", value_from="message"),
])
def test_read_denies_forbidden_actions(step):
    with pytest.raises(PolicyError):
        check_step(step, READ)


def test_write_requires_approval():
    step = Step(action="click", target="submit_request")
    with pytest.raises(PolicyError):
        check_step(step, WRITE, False)
    check_step(step, WRITE, True)


def test_strict_language_rejects_code_and_selector_injection():
    for value in ({"action": "eval", "code": "alert(1)"}, {"action": "click", "target": 'x"] button'}):
        with pytest.raises(ValidationError):
            Step.model_validate(value)


def test_hash_binds_exact_input():
    a = {"order": "ORD-101", "message": "Please update"}
    assert canonical_hash(a) == canonical_hash(dict(reversed(list(a.items()))))
    assert canonical_hash(a) != canonical_hash({**a, "order": "ORD-102"})
    assert canonical_hash(a) != canonical_hash({**a, "message": "Please update!"})


def test_origin_does_not_accept_prefix_spoofing():
    assert not same_origin("http://portal.evil:8090/", "http://portal:8090")
    assert not same_origin("http://portal@evil:8090/", "http://portal:8090")
    assert same_origin("http://portal:8090/?q=ORD-101", "http://portal:8090")


def test_business_rules():
    assert classify("2026-11-10", "2026-11-13", "In transit") == "DELAYED"
    assert classify("2026-11-10", None, "In transit") == "UNKNOWN"
    assert classify("2026-11-10", "2026-11-09", "In transit") == "ON_TRACK"
    assert classify("2026-11-10", "2026-11-13", "Canceled") == "CANCELED"
