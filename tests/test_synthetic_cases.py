import json
from pathlib import Path

import pytest

from src.app.models.schemas import ExtractedChangeRequest, RiskLevel
from src.app.services.risk_scoring import score_change_request


_CASES_PATH = Path(__file__).resolve().parents[1] / "evals" / "data" / "synthetic_cases.json"


with _CASES_PATH.open(encoding="utf-8") as cases_file:
    SYNTHETIC_CASES = json.load(cases_file)


@pytest.mark.parametrize("case", SYNTHETIC_CASES, ids=lambda case: case["case_id"])
def test_synthetic_case_matches_schema_and_expected_score(case):
    request = ExtractedChangeRequest.model_validate(case["expected_extraction"])
    assessment = score_change_request(request)

    assert assessment.risk_level == RiskLevel(case["expected_risk_level"])
    assert assessment.requires_committee_review is case["expected_committee_review"]



def test_synthetic_cases_are_non_production_and_unique():
    case_ids = [case["case_id"] for case in SYNTHETIC_CASES]
    source_texts = [case["source_text"] for case in SYNTHETIC_CASES]

    assert len(case_ids) == len(set(case_ids))
    assert len(source_texts) == len(set(source_texts))
    assert all(case_id.startswith("SYN-") for case_id in case_ids)
    assert all("@" not in source_text for source_text in source_texts)
    assert all("account number" not in source_text.lower() for source_text in source_texts)
