from src.app.models.schemas import ExtractedChangeRequest, PolicyEvidence


_POLICIES = {
    "customer-risk": PolicyEvidence(
        policy_id="customer-risk-v1",
        title="Synthetic customer and geography risk guidance",
        section="Customer and geography exposure",
        excerpt="Assess customer segments, geography footprint, and cross-border exposure before launch.",
        relevance="Supports customer and geography risk review.",
    ),
    "third-party-risk": PolicyEvidence(
        policy_id="third-party-risk-v1",
        title="Synthetic third-party risk guidance",
        section="Vendor oversight",
        excerpt="Vendor involvement requires due diligence, monitoring, and documented accountability.",
        relevance="Supports third-party risk review.",
    ),
    "product-risk": PolicyEvidence(
        policy_id="product-risk-v1",
        title="Synthetic product change risk guidance",
        section="New products and channels",
        excerpt="New products and channels require documented risk analysis before approval.",
        relevance="Supports product and channel risk review.",
    ),
}


def find_policy_evidence(request: ExtractedChangeRequest) -> list[PolicyEvidence]:
    evidence = [_POLICIES["product-risk"]]
    if request.geographies_involved or request.customer_segments_involved:
        evidence.append(_POLICIES["customer-risk"])
    if request.vendor_involved:
        evidence.append(_POLICIES["third-party-risk"])
    return evidence