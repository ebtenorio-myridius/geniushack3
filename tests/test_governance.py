import pytest

from src.app.models.governance import GovernanceRules, load_governance_rules


def test_active_governance_rules_are_prototype_and_have_stable_digest():
    rules = load_governance_rules()

    assert rules.approval_state == "prototype"
    assert rules.sha256 == load_governance_rules().sha256


def test_governance_rules_reject_unreachable_quorum():
    rules_data = load_governance_rules().model_dump(mode="json")
    rules_data["workflow"]["committee_votes_required"] = 4

    with pytest.raises(ValueError, match="less than or equal to 3"):
        GovernanceRules.model_validate(rules_data)


def test_governance_rules_reject_unmeasured_stage_sla():
    rules_data = load_governance_rules().model_dump(mode="json")
    rules_data["workflow"]["stage_sla_hours"]["unknown_stage"] = 24

    with pytest.raises(ValueError, match="Unsupported stage SLA keys"):
        GovernanceRules.model_validate(rules_data)
