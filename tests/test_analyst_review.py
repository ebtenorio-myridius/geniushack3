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
    store.submit_case(case.case_id, "product-owner-1")
    monkeypatch.setattr(intake, "case_store", store)

    client = TestClient(app)
    client.cookies.set("demo_user", "analyst-1")
    client.cookies.set("demo_role", "analyst")
    detail = client.get(f"/intake/analyst/cases/{case.case_id}")

    assert detail.status_code == 200
    assert "Analyst review" in detail.text
    assert "Finalize assessment for committee" in detail.text
    assert "Reject draft" not in detail.text
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
    assert "not yet in the committee queue" in response.text
    assert "Submit to committee" in response.text
    assert store.list_events(case.case_id)[-1]["actor"] == "analyst-1"

    submitted = client.post(
        f"/intake/{case.case_id}/committee/submit",
        data={"rationale": "The finalized low-risk assessment is ready for committee decision."},
    )
    assert submitted.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.committee_review
    assert "committee decision queue" in submitted.text

    committee = TestClient(app)
    committee.cookies.set("demo_user", "committee-1")
    committee.cookies.set("demo_role", "committee")
    committee_dashboard = committee.get("/intake/committee/dashboard/demo")
    assert committee_dashboard.status_code == 200
    assert case.case_id in committee_dashboard.text