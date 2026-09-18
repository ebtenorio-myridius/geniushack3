from src.app.models.schemas import ChangeType, ExtractedChangeRequest, RiskLevel
from src.app.services.risk_scoring import score_change_request


def _base_request(**overrides) -> ExtractedChangeRequest:
    defaults = dict(
        change_title="Minor UI update to online banking",
        change_type=ChangeType.feature_change,
        business_unit="Consumer Banking",
        description="Cosmetic update to the account dashboard.",
        geographies_involved=[],
        customer_segments_involved=[],
        vendor_involved=False,
        vendor_name=None,
        products_involved=["Online Banking"],
        stated_risk_factors=[],
        extraction_confidence=0.95,
    )
    defaults.update(overrides)
    return ExtractedChangeRequest(**defaults)


def test_low_complexity_change_scores_low_risk():
    req = _base_request()
    assessment = score_change_request(req)
    assert assessment.risk_level == RiskLevel.low
    assert assessment.requires_committee_review is False


def test_new_product_with_vendor_and_flagged_geography_scores_high():
    req = _base_request(
        change_title="New remittance product with third-party processor",
        change_type=ChangeType.new_product,
        geographies_involved=["Iran", "Germany", "Poland"],
        customer_segments_involved=["Non-resident customers"],
        vendor_involved=True,
        vendor_name="Acme Payments Processing",
        products_involved=["Remittances", "FX"],
        stated_risk_factors=["Cross-border payments", "New customer type", "Sanctions exposure"],
        extraction_confidence=0.8,
    )
    assessment = score_change_request(req)
    assert assessment.risk_level in (RiskLevel.high, RiskLevel.critical)
    assert assessment.requires_committee_review is True


def test_low_extraction_confidence_increases_complexity_score():
    confident = _base_request(extraction_confidence=0.9)
    unsure = _base_request(extraction_confidence=0.3)

    confident_complexity = next(
        cs.score for cs in score_change_request(confident).category_scores if cs.category == "Change Complexity"
    )
    unsure_complexity = next(
        cs.score for cs in score_change_request(unsure).category_scores if cs.category == "Change Complexity"
    )
    assert unsure_complexity > confident_complexity
