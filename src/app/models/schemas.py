from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    new_product = "new_product"
    feature_change = "feature_change"
    process_change = "process_change"
    vendor_onboarding = "vendor_onboarding"
    new_geography = "new_geography"
    new_customer_segment = "new_customer_segment"
    other = "other"


class ExtractedChangeRequest(BaseModel):
    """What the LLM extracts from the submitted document.

    This is the contract between the LLM call and the rest of the app.
    Structured outputs (see services/llm_service.py) enforce this shape,
    so a malformed extraction fails the request instead of silently
    passing bad data downstream.
    """

    change_title: str = Field(description="Short name for the change being requested")
    change_type: ChangeType
    business_unit: str = Field(description="e.g. Consumer Banking, Payments, Wealth Management")
    description: str = Field(description="Plain-language summary of what is changing")
    geographies_involved: list[str] = Field(default_factory=list)
    customer_segments_involved: list[str] = Field(default_factory=list)
    vendor_involved: bool = False
    vendor_name: str | None = None
    products_involved: list[str] = Field(default_factory=list)
    stated_risk_factors: list[str] = Field(
        default_factory=list,
        description="Any risk-relevant factors explicitly mentioned in the source document",
    )
    extraction_confidence: float = Field(
        ge=0.0, le=1.0, description="Model's own confidence in this extraction, 0-1"
    )


class RiskCategoryScore(BaseModel):
    category: str
    score: int = Field(ge=1, le=5)
    rationale: str


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CaseStatus(str, Enum):
    draft = "draft"
    analyst_review = "analyst_review"
    analyst_finalized = "analyst_finalized"
    analyst_accepted = "analyst_accepted"
    analyst_rejected = "analyst_rejected"
    committee_review = "committee_review"
    decisioned = "decisioned"


class CommitteeDecision(str, Enum):
    approve = "approve"
    reject = "reject"
    defer = "defer"
    approve_with_conditions = "approve_with_conditions"


class UserRole(str, Enum):
    product_owner = "product_owner"
    analyst = "analyst"
    committee = "committee"
    administrator = "administrator"


class RiskAssessmentDraft(BaseModel):
    """Output of the deterministic scoring step — see services/risk_scoring.py.

    Deliberately NOT produced by the LLM. Scoring math is plain Python so
    it is traceable, reproducible and auditable — every score can be
    traced back to the category scores and the rule that combined them.
    """

    category_scores: list[RiskCategoryScore]
    overall_score: float
    risk_level: RiskLevel
    requires_committee_review: bool
    scoring_method: str = "deterministic_weighted_v1"


class PolicyEvidence(BaseModel):
    policy_id: str
    title: str
    section: str
    excerpt: str
    relevance: str
    source_path: str = "docs/policies/unknown.md"


class AnalystReview(BaseModel):
    decision: CaseStatus
    actor: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class CommitteeReview(BaseModel):
    decision: CommitteeDecision
    actor: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    conditions: str = ""


class TelemetryRecord(BaseModel):
    operation: str
    model: str
    prompt_version: str
    latency_ms: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    success: bool
    error_type: str | None = None


class CaseRecord(BaseModel):
    case_id: str
    filename: str
    extracted: ExtractedChangeRequest
    assessment: RiskAssessmentDraft
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)
    extraction_version: int = 1
    status: CaseStatus = CaseStatus.draft
    created_at: datetime
    updated_at: datetime


