import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

_CHANGE_TYPES = {
    "new_product",
    "feature_change",
    "process_change",
    "vendor_onboarding",
    "new_geography",
    "new_customer_segment",
    "other",
}


class GeographyScoringRules(BaseModel):
    high_risk_score: int = Field(ge=1, le=5)
    many_geographies_count: int = Field(ge=1)
    many_geographies_score: int = Field(ge=1, le=5)
    known_geographies_score: int = Field(ge=1, le=5)
    no_geographies_score: int = Field(ge=1, le=5)
    customer_segment_increment: int = Field(ge=0, le=4)
    maximum_score: int = Field(ge=1, le=5)


class ProductScoringRules(BaseModel):
    higher_risk_base_score: int = Field(ge=1, le=5)
    incremental_base_score: int = Field(ge=1, le=5)
    multiple_products_count: int = Field(ge=1)
    multiple_products_increment: int = Field(ge=0, le=4)
    high_impact_increment: int = Field(ge=0, le=4)
    maximum_score: int = Field(ge=1, le=5)


class ThirdPartyScoringRules(BaseModel):
    vendor_score: int = Field(ge=1, le=5)
    no_vendor_score: int = Field(ge=1, le=5)


class ComplexityScoringRules(BaseModel):
    many_factors_count: int = Field(ge=1)
    many_factors_score: int = Field(ge=1, le=5)
    some_factors_score: int = Field(ge=1, le=5)
    no_factors_score: int = Field(ge=1, le=5)
    low_confidence_threshold: float = Field(ge=0, le=1)
    low_confidence_increment: int = Field(ge=0, le=4)
    maximum_score: int = Field(ge=1, le=5)


class ScoringRules(BaseModel):
    weights: dict[str, float]
    risk_thresholds: dict[str, float]
    high_risk_geographies: list[str]
    high_impact_risk_terms: list[str]
    higher_risk_change_types: list[str]
    geography: GeographyScoringRules
    product_and_channel: ProductScoringRules
    third_party: ThirdPartyScoringRules
    change_complexity: ComplexityScoringRules

    @model_validator(mode="after")
    def validate_scoring_parameters(self):
        expected = {"customer_and_geography", "product_and_channel", "third_party", "change_complexity"}
        if set(self.weights) != expected or any(weight < 0 for weight in self.weights.values()):
            raise ValueError("Scoring weights must define all four categories and be nonnegative")
        if abs(sum(self.weights.values()) - 1.0) > 0.000001:
            raise ValueError("Scoring weights must sum to 1")
        if set(self.risk_thresholds) != {"medium", "high", "critical"}:
            raise ValueError("Risk thresholds must define medium, high, and critical")
        if not set(self.higher_risk_change_types) <= _CHANGE_TYPES:
            raise ValueError("Higher-risk change types must use supported change-type values")
        if not (
            0 <= self.risk_thresholds["medium"]
            < self.risk_thresholds["high"]
            < self.risk_thresholds["critical"]
        ):
            raise ValueError("Risk thresholds must be ordered from medium through critical")
        return self


class WorkflowRules(BaseModel):
    committee_votes_required: int = Field(ge=1, le=3)
    committee_majority_required: int = Field(ge=1)
    end_to_end_sla_hours: int = Field(ge=1)
    stage_sla_hours: dict[str, int]

    @model_validator(mode="after")
    def validate_quorum(self):
        if self.committee_majority_required > self.committee_votes_required:
            raise ValueError("Committee majority cannot exceed the number of required votes")
        if any(hours < 1 for hours in self.stage_sla_hours.values()):
            raise ValueError("Stage SLA hours must be positive")
        supported_stages = {"analyst_review", "committee_review", "needs_information"}
        unknown_stages = set(self.stage_sla_hours) - supported_stages
        if unknown_stages:
            raise ValueError(f"Unsupported stage SLA keys: {', '.join(sorted(unknown_stages))}")
        return self


class GovernanceRules(BaseModel):
    version: str = Field(min_length=1)
    approval_state: Literal["prototype", "approved"]
    owner: str = Field(min_length=1)
    approved_by: str | None = None
    effective_at: date
    change_rationale: str = Field(min_length=1)
    scoring: ScoringRules
    workflow: WorkflowRules

    @model_validator(mode="after")
    def validate_approval(self):
        if self.approval_state == "approved" and not self.approved_by:
            raise ValueError("Approved governance rules must identify the approver")
        return self

    @property
    def sha256(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "governance_rules.json"


def load_governance_rules(path: str | Path | None = None) -> GovernanceRules:
    rules_path = Path(path) if path is not None else DEFAULT_RULES_PATH
    return GovernanceRules.model_validate_json(rules_path.read_text(encoding="utf-8"))
