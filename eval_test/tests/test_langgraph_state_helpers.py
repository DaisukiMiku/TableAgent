from __future__ import annotations

from frameworks.langgraph_runner import route_after_verify


def test_route_after_verify_final_when_passed() -> None:
    state = {"verification": {"passed": True}, "repair_count": 0, "max_repairs": 1}
    assert route_after_verify(state) == "final"


def test_route_after_verify_repairs_when_requested() -> None:
    state = {
        "verification": {"passed": False, "repair_requested": True},
        "repair_count": 1,
        "max_repairs": 1,
    }
    assert route_after_verify(state) == "solve"


def test_route_after_verify_final_when_repair_not_requested() -> None:
    state = {
        "verification": {"passed": False, "repair_requested": False},
        "repair_count": 0,
        "max_repairs": 1,
    }
    assert route_after_verify(state) == "final"
