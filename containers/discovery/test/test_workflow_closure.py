"""Tests for workflow closure signal detection and promotion."""

from __future__ import annotations

from containers.discovery.workflow_closure import detect_workflow_signals


def test_detects_yield_routing_and_wip_signals():
    text = (
        "Our factory floor is a black box because of yield variance. "
        "We need machine time at each step of the routing process."
    )
    signals = detect_workflow_signals(text)
    assert "yield_routing" in signals
    assert "wip_visibility" in signals


def test_detects_manufacturing_execution():
    text = "We manufacture industrial adhesives and make to stock."
    signals = detect_workflow_signals(text)
    assert "manufacturing_execution" in signals
