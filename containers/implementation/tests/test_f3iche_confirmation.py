"""Unit tests for F3iche confirmation synthesis helpers (Step 3.5)."""
from __future__ import annotations

import pytest

from containers.implementation.signals_agent.discovery_context import _transcript_from_chat_history
from containers.implementation.signals_agent.f3iche_confirmation_models import (
    F3icheConfirmationSynthesis,
    F3icheCorrectionResolution,
)


class TestDiscoveryTranscript:
    def test_list_format(self):
        history = [
            {"role": "user", "content": "We manufacture coatings"},
            {"role": "assistant", "content": "Got it — project installs too?"},
            {"role": "user", "content": "Yes, installation projects"},
        ]
        out = _transcript_from_chat_history(history)
        assert "user: We manufacture coatings" in out
        assert "assistant: Got it" in out

    def test_dict_messages_format(self):
        history = {"messages": [{"role": "user", "content": "Trading FMCG"}]}
        assert "user: Trading FMCG" in _transcript_from_chat_history(history)

    def test_empty_returns_blank(self):
        assert _transcript_from_chat_history([]) == ""
        assert _transcript_from_chat_history(None) == ""


class TestF3icheConfirmationModels:
    def test_synthesis_schema_validates(self):
        model = F3icheConfirmationSynthesis(
            confirmation_message="We think you are a coatings manufacturer. Is that right?",
            proposed_f3iche="manufacturing_project_chemical",
            proposed_industry="manufacturing",
            display_name="Chemical Coatings Manufacturer",
            confidence=0.85,
            evidence_from_files=["client_orders.csv has project columns"],
            evidence_from_discovery=["user said coatings + installs"],
            alignment="agree",
        )
        dumped = model.model_dump()
        assert dumped["proposed_f3iche"] == "manufacturing_project_chemical"
        assert dumped["alignment"] == "agree"

    def test_correction_schema_validates(self):
        model = F3icheCorrectionResolution(
            f3iche="manufacturing_food_batch",
            industry="manufacturing",
            display_name="Food / Batch Manufacturing",
            reasoning="User described batch food production",
        )
        assert model.f3iche == "manufacturing_food_batch"
