"""Unit tests for F3iche confirmation synthesis helpers (Step 3.5)."""
from __future__ import annotations

import pytest

from containers.implementation.signals_agent.discovery_context import _transcript_from_chat_history
from containers.implementation.signals_agent.f3iche_confirmation_activities import (
    _reconcile_proposal_with_sources,
)
from containers.implementation.signals_agent.f3iche_confirmation_models import (
    F3icheConfirmationSynthesis,
    F3icheCorrectionResolution,
)

NICHE_IDS = [
    "trading_fmcg_distributor",
    "manufacturing_garment_variants",
    "manufacturing_project_chemical",
    "manufacturing_fabrication_jobshop",
    "service_professional",
]


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


class TestReconcileProposal:
    def test_message_describes_chemical_but_proposed_garment(self):
        synthesis = F3icheConfirmationSynthesis(
            confirmation_message=(
                "Based on discovery, you manufacture epoxy coatings and run installation projects. "
                "Is that correct?"
            ),
            proposed_f3iche="manufacturing_garment_variants",
            proposed_industry="Manufacturing",
            display_name="Garment Manufacturing",
            confidence=0.8,
            evidence_from_discovery=["user: epoxy coatings and site installs"],
            alignment="agree",
        )
        reconciled = _reconcile_proposal_with_sources(
            synthesis,
            discovery_ctx={
                "discovery_f3iche": "manufacturing",
                "discovery_industry": "Manufacturing",
                "chat_transcript": "user: We manufacture epoxy coatings",
            },
            infer_result={"f3iche": "manufacturing_garment_variants"},
            niche_ids=NICHE_IDS,
        )
        assert reconciled.proposed_f3iche == "manufacturing_project_chemical"
        assert reconciled.proposed_f3iche != "manufacturing_garment_variants"
