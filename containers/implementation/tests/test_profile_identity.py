"""Tests for profile identity resolution from discovery + synthesis."""
from __future__ import annotations

from containers.implementation.profile_agent.profile_identity import (
    resolve_profile_identity,
    slug_to_display_name,
)


def test_slug_to_display_name():
    assert slug_to_display_name("green-surface") == "Green Surface"
    assert slug_to_display_name("unknown") is None


def test_fills_company_name_from_slug():
    identity = resolve_profile_identity(
        company_slug="green-surface",
        industry="Manufacturing",
        discovery_ctx={},
    )
    assert identity["company_name"] == "Green Surface"


def test_broad_industry_gets_sub_from_discovery():
    identity = resolve_profile_identity(
        industry="manufacturing",
        discovery_ctx={
            "discovery_industry": "Epoxy floor coatings manufacturer",
            "discovery_metadata": {"industry": "Epoxy floor coatings manufacturer"},
        },
        synthesis={"proposed_industry": "Manufacturing"},
    )
    assert identity["industry_sub"] == "Epoxy floor coatings manufacturer"


def test_synthesis_industry_used_when_missing():
    identity = resolve_profile_identity(
        discovery_ctx={},
        synthesis={"proposed_industry": "Manufacturing"},
    )
    assert identity["industry"] == "Manufacturing"


def test_company_size_from_discovery_coverage():
    identity = resolve_profile_identity(
        company_name="Green Surface",
        discovery_ctx={
            "discovery_metadata": {
                "coverage": {"scale": {"value": "11-50"}},
            },
        },
    )
    assert identity["company_size"] == "11-50"
