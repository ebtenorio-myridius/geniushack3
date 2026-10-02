from fastapi.testclient import TestClient

from src.app.models.schemas import CaseStatus, ExtractedChangeRequest, RiskLevel
from src.app.routers import intake
from src.app.services.case_store import CaseStore
from src.app.services.risk_scoring import score_change_request
from src.app.main import app


def test_analyst_can_finalize_low_risk_case_from_case_detail(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    extracted = ExtractedChangeRequest(
        change_title="Existing dashboard accessibility update",
        change_type="feature_change",
        business_unit="Consumer Banking",
        description="Improve keyboard navigation on an existing dashboard.",
        geographies_involved=["United States"],
        products_involved=["Existing dashboard"],
        extraction_confidence=0.95,
    )
    assessment = score_change_request(extracted)
    assert assessment.risk_level == RiskLevel.low
    case = store.create_case("manual synthetic sample", extracted, assessment)
    monkeypatch.setattr(intake, "case_store", store)

    client = TestClient(app)
    client.cookies.set("demo_user", "analyst-1")
    client.cookies.set("demo_role", "analyst")
    detail = client.get(f"/intake/analyst/cases/{case.case_id}")

    assert detail.status_code == 200
    assert "Analyst review" in detail.text
    assert "Finalize assessment" in detail.text
    assert "Read-only analyst view" not in detail.text

    response = client.post(
        f"/intake/{case.case_id}/review",
        data={
            "decision": "analyst_accepted",
            "rationale": "The low-risk change is limited to accessibility improvements on an existing product.",
        },
    )

    assert response.status_code == 200
    finalized = store.get_case(case.case_id)
    assert finalized.status == CaseStatus.analyst_finalized
    assert store.list_events(case.case_id)[-1]["actor"] == "analyst-1"