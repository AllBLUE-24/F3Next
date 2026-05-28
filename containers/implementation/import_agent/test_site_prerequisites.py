"""Tests for greenfield setup wizard arg builder."""
from containers.implementation.import_agent.site_prerequisites import (
    build_setup_wizard_args,
    _f3iche_to_domain,
)


def test_build_setup_wizard_args_india():
    args = build_setup_wizard_args(
        company_name="Regww",
        company_abbr="REG",
        country="India",
        default_currency="INR",
        fy_start_date="2026-04-01",
        fy_end_date="2027-03-31",
    )
    assert args["company_name"] == "Regww"
    assert args["company_abbr"] == "REG"
    assert args["country"] == "India"
    assert args["chart_of_accounts"] == "India - Chart of Accounts"
    assert args["setup_demo"] == 0
    assert args["currency"] == "INR"


def test_f3iche_manufacturing_domain():
    assert _f3iche_to_domain("manufacturing_sme") == "Manufacturing"
    assert _f3iche_to_domain("") is None
