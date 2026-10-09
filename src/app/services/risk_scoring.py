from src.app.models.governance import GovernanceRules
from src.app.models.schemas import (
    ChangeType,
    ExtractedChangeRequest,
    RiskAssessmentDraft,
    RiskCategoryScore,
    RiskLevel,
)
from src.app.services.governance_service import active_governance_rules


def _score_customer_and_geography(
    request: ExtractedChangeRequest,
    rules: GovernanceRules,
) -> RiskCategoryScore:
    params = rules.scoring.geography
    geographies = {place.lower() for place in request.geographies_involved}
    flagged = geographies & set(rules.scoring.high_risk_geographies)
    if flagged:
        score = params.high_risk_score
        rationale = f"Involves higher-risk geographies: {', '.join(sorted(flagged))}"
    elif len(geographies) >= params.many_geographies_count:
        score = params.many_geographies_score
        rationale = f"Spans {len(geographies)} geographies — broader exposure"
    elif geographies:
        score = params.known_geographies_score
        rationale = "Limited, known geography exposure"
    else:
        score = params.no_geographies_score
        rationale = "No new geography exposure identified"

    if request.customer_segments_involved:
        score = min(params.maximum_score, score + params.customer_segment_increment)
        rationale += f"; new/changed customer segment(s): {', '.join(request.customer_segments_involved)}"

    return RiskCategoryScore(
        category="Customer & Geography",
        score=min(score, params.maximum_score),
        rationale=rationale,
        input_fields=["geographies_involved", "customer_segments_involved"],
    )


def _score_product_and_channel(
    request: ExtractedChangeRequest,
    rules: GovernanceRules,
) -> RiskCategoryScore:
    params = rules.scoring.product_and_channel
    higher_risk_types = {ChangeType(value) for value in rules.scoring.higher_risk_change_types}
    if request.change_type in higher_risk_types:
        score = params.higher_risk_base_score
        rationale = f"Change type '{request.change_type.value}' is inherently higher risk"
    else:
        score = params.incremental_base_score
        rationale = f"Change type '{request.change_type.value}' is incremental"

    if len(request.products_involved) >= params.multiple_products_count:
        score += params.multiple_products_increment
        rationale += f"; touches {len(request.products_involved)} products"

    high_impact_terms = {
        term.lower() for term in request.stated_risk_factors
    } & set(rules.scoring.high_impact_risk_terms)
    if high_impact_terms:
        score += params.high_impact_increment
        rationale += f"; explicit high-impact factors: {', '.join(sorted(high_impact_terms))}"

    return RiskCategoryScore(
        category="Product & Channel",
        score=min(score, params.maximum_score),
        rationale=rationale,
        input_fields=["change_type", "products_involved", "stated_risk_factors"],
    )


def _score_third_party(
    request: ExtractedChangeRequest,
    rules: GovernanceRules,
) -> RiskCategoryScore:
    params = rules.scoring.third_party
    if request.vendor_involved:
        return RiskCategoryScore(
            category="Third-Party / Vendor",
            score=params.vendor_score,
            rationale=f"Vendor involved ({request.vendor_name or 'unnamed'}) — introduces third-party risk",
            input_fields=["vendor_involved", "vendor_name"],
        )
    return RiskCategoryScore(
        category="Third-Party / Vendor",
        score=params.no_vendor_score,
        rationale="No vendor involvement identified",
        input_fields=["vendor_involved"],
    )


def _score_change_complexity(
    request: ExtractedChangeRequest,
    rules: GovernanceRules,
) -> RiskCategoryScore:
    params = rules.scoring.change_complexity
    factor_count = len(request.stated_risk_factors)
    if factor_count >= params.many_factors_count:
        score = params.many_factors_score
        rationale = f"{factor_count} distinct risk factors stated in source document"
    elif factor_count:
        score = params.some_factors_score
        rationale = f"{factor_count} risk factor(s) stated in source document"
    else:
        score = params.no_factors_score
        rationale = "No explicit risk factors stated"

    if request.extraction_confidence < params.low_confidence_threshold:
        score = min(params.maximum_score, score + params.low_confidence_increment)
        rationale += "; low extraction confidence increases uncertainty — analyst should verify source"

    return RiskCategoryScore(
        category="Change Complexity",
        score=min(score, params.maximum_score),
        rationale=rationale,
        input_fields=["stated_risk_factors", "extraction_confidence"],
    )


def score_change_request(
    request: ExtractedChangeRequest,
    rules: GovernanceRules | None = None,
) -> RiskAssessmentDraft:
    """Apply the selected versioned scoring configuration without model decisions."""
    rules = rules or active_governance_rules
    category_scores = [
        _score_customer_and_geography(request, rules),
        _score_product_and_channel(request, rules),
        _score_third_party(request, rules),
        _score_change_complexity(request, rules),
    ]
    category_keys = {
        "Customer & Geography": "customer_and_geography",
        "Product & Channel": "product_and_channel",
        "Third-Party / Vendor": "third_party",
        "Change Complexity": "change_complexity",
    }
    overall = round(
        sum(
            item.score * rules.scoring.weights[category_keys[item.category]]
            for item in category_scores
        ),
        2,
    )

    thresholds = rules.scoring.risk_thresholds
    if overall >= thresholds["critical"]:
        level = RiskLevel.critical
    elif overall >= thresholds["high"]:
        level = RiskLevel.high
    elif overall >= thresholds["medium"]:
        level = RiskLevel.medium
    else:
        level = RiskLevel.low

    return RiskAssessmentDraft(
        category_scores=category_scores,
        overall_score=overall,
        risk_level=level,
        requires_committee_review=level in (RiskLevel.high, RiskLevel.critical),
        ruleset_version=rules.version,
        ruleset_sha256=rules.sha256,
        ruleset_snapshot=rules.model_dump(mode="json"),
    )
