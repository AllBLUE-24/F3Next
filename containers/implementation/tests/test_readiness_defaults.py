"""Readiness contracts default to blocked when evidence is absent."""

from containers.implementation.data_readiness_agent.models import (
    DataReadinessAssessment,
)


def test_empty_readiness_assessment_is_fail_closed():
    assessment = DataReadinessAssessment()

    assert assessment.minimum_viable_import_possible is False
    assert assessment.user_action_required is True
    assert assessment.import_readiness_score == 0.0
