"""Import must not invent or continue without required plan artifacts."""

import pytest

from containers.implementation.import_agent.activities import (
    ImportPlanContractError,
    _require_import_artifact,
)


def test_missing_import_artifact_is_a_hard_failure():
    with pytest.raises(
        ImportPlanContractError,
        match="no finalized plan",
    ):
        _require_import_artifact(None, "no finalized plan")


def test_present_import_artifact_is_returned():
    plan = {"status": "ready"}
    assert _require_import_artifact(plan, "missing") is plan
