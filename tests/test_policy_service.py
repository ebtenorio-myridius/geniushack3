from src.app.models.schemas import ExtractedChangeRequest
from src.app.services.policy_service import find_policy_evidence


def _request(**overrides):
    values = dict(
        change_title="Synthetic change",
        change_type="feature_change",
        business_unit="Consumer Banking",
        description="Synthetic change.",
        extraction_confidence=0.9,
    )
    values.update(overrides)
    return ExtractedChangeRequest(**values)


def test_policy_evidence_is_targeted_and_cited():
    evidence = find_policy_evidence(
        _request(
            change_type="vendor_onboarding",
            geographies_involved=["United States"],
            vendor_involved=True,
        )
    )
    policy_ids = {item.policy_id for item in evidence}
    assert policy_ids == {"customer-risk-v1", "third-party-risk-v1"}
    assert all(item.source_path.startswith("docs/policies/") for item in evidence)
    assert all(item.section and item.excerpt and item.relevance for item in evidence)


def test_policy_evidence_is_empty_for_unclassified_change():
    evidence = find_policy_evidence(_request(change_type="other"))
    assert evidence == []