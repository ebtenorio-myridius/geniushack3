from src.app.models.schemas import (
    ChangeType,
    ExtractedChangeRequest,
    RiskAssessmentDraft,
    RiskCategoryScore,
    RiskLevel,
)

# Placeholder starting weights. Swap for figures grounded in a real
# supervisory framework (BSA/AML, FFIEC, FATF risk categories, etc.) once
# the BA has done that research — see /docs/requirements. Keeping these
# named constants (not magic numbers inline) makes that swap a one-line
# change per category.
_CATEGORY_WEIGHTS = {
    "customer_and_geography": 0.35,
    "product_and_channel": 0.30,
    "third_party": 0.20,
    "change_complexity": 0.15,
}

_HIGH_RISK_GEOGRAPHY_KEYWORDS = {"russia", "iran", "north korea", "syria", "myanmar"}


def _score_customer_and_geography(req: ExtractedChangeRequest) -> RiskCategoryScore:
    geographies = {g.lower() for g in req.geographies_involved}
    flagged = geographies & _HIGH_RISK_GEOGRAPHY_KEYWORDS

    if flagged:
        score, rationale = 5, f"Involves higher-risk geographies: {', '.join(flagged)}"
    elif len(geographies) > 2:
        score, rationale = 3, f"Spans {len(geographies)} geographies — broader exposure"
    elif geographies:
        score, rationale = 2, "Limited, known geography exposure"
    else:
        score, rationale = 1, "No new geography exposure identified"

    if req.customer_segments_involved:
        score = min(5, score + 1)
        rationale += f"; new/changed customer segment(s): {', '.join(req.customer_segments_involved)}"

    return RiskCategoryScore(category="Customer & Geography", score=score, rationale=rationale)


def _score_product_and_channel(req: ExtractedChangeRequest) -> RiskCategoryScore:
    higher_risk_types = {ChangeType.new_product, ChangeType.new_geography, ChangeType.new_customer_segment}
    if req.change_type in higher_risk_types:
        score = 4
        rationale = f"Change type '{req.change_type.value}' is inherently higher risk"
    else:
        score = 2
        rationale = f"Change type '{req.change_type.value}' is incremental"

    if len(req.products_involved) > 1:
        score = min(5, score + 1)
        rationale += f"; touches {len(req.products_involved)} products"

    return RiskCategoryScore(category="Product & Channel", score=score, rationale=rationale)


def _score_third_party(req: ExtractedChangeRequest) -> RiskCategoryScore:
    if req.vendor_involved:
        return RiskCategoryScore(
            category="Third-Party / Vendor",
            score=4,
            rationale=f"Vendor involved ({req.vendor_name or 'unnamed'}) — introduces third-party risk",
        )
    return RiskCategoryScore(category="Third-Party / Vendor", score=1, rationale="No vendor involvement identified")


def _score_change_complexity(req: ExtractedChangeRequest) -> RiskCategoryScore:
    factor_count = len(req.stated_risk_factors)
    if factor_count >= 3:
        score, rationale = 4, f"{factor_count} distinct risk factors stated in source document"
    elif factor_count >= 1:
        score, rationale = 2, f"{factor_count} risk factor(s) stated in source document"
    else:
        score, rationale = 1, "No explicit risk factors stated"

    if req.extraction_confidence < 0.6:
        score = min(5, score + 1)
        rationale += "; low extraction confidence increases uncertainty — analyst should verify source"

    return RiskCategoryScore(category="Change Complexity", score=score, rationale=rationale)


def score_change_request(req: ExtractedChangeRequest) -> RiskAssessmentDraft:
    """Deterministic, rule-based scoring — no LLM in this path.

    Rationale for this being plain code rather than a model call: risk
    scoring here follows fixed, defensible rules a committee needs to be
    able to reproduce and challenge. That's a good fit for deterministic
    logic; an LLM's job upstream was structuring the unstructured input,
    not deciding the number. Document this trade-off in /docs/architecture.
    """
    category_scores = [
        _score_customer_and_geography(req),
        _score_product_and_channel(req),
        _score_third_party(req),
        _score_change_complexity(req),
    ]

    weight_by_category = dict(
        zip(
            ["Customer & Geography", "Product & Channel", "Third-Party / Vendor", "Change Complexity"],
            _CATEGORY_WEIGHTS.values(),
        )
    )
    overall = sum(cs.score * weight_by_category[cs.category] for cs in category_scores)
    overall = round(overall, 2)

    if overall >= 4.0:
        level = RiskLevel.critical
    elif overall >= 3.0:
        level = RiskLevel.high
    elif overall >= 2.0:
        level = RiskLevel.medium
    else:
        level = RiskLevel.low

    return RiskAssessmentDraft(
        category_scores=category_scores,
        overall_score=overall,
        risk_level=level,
        requires_committee_review=level in (RiskLevel.high, RiskLevel.critical),
    )
