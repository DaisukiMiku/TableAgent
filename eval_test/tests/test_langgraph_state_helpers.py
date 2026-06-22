from __future__ import annotations

from frameworks.langgraph_runner import route_after_verify


def test_route_after_verify_final_when_passed() -> None:
    state = {"verification": {"passed": True}, "repair_count": 0, "max_repairs": 1}
    assert route_after_verify(state) == "final"


def test_route_after_verify_repairs_once() -> None:
    state = {"verification": {"passed": False}, "repair_count": 0, "max_repairs": 1}
    assert route_after_verify(state) == "solve"


def test_route_after_verify_stops_at_cap() -> None:
    state = {"verification": {"passed": False}, "repair_count": 1, "max_repairs": 1}
    assert route_after_verify(state) == "final"
