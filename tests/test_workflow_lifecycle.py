from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.models.schemas import (
    AnalystReview,
    CaseStatus,
    CommitteeReview,
    ExtractedChangeRequest,
)
from src.app.services.case_store import CaseStore
from src.app.services.risk_scoring import score_change_request
from src.app.routers import intake


def _request(**overrides):
    values = {
        "change_title": "Synthetic cross-border payment change",
        "change_type": "new_product",
        "business_unit": "Payments",
        "description": "Synthetic launch with updated payment flows.",
        "geographies_involved": ["United States", "Philippines"],
        "products_involved": ["Remittance"],
        "extraction_confidence": 0.9,
    }
    values.update(overrides)
    return ExtractedChangeRequest(**values)


def _case(store: CaseStore, **overrides):
    request = _request(**overrides)
    return store.create_case("synthetic.pdf", request, score_change_request(request))


def _committee_ready(store: CaseStore):
    case = _case(store)
    store.submit_case(case.case_id, "product-owner-1")
    store.review_case(
        case.case_id,
        AnalystReview(
            decision=CaseStatus.analyst_accepted,
            actor="analyst-1",
            rationale="Evidence and scores checked.",
        ),
    )
    store.submit_committee(case.case_id, "analyst-1", "Escalated for committee decision.")
    return store.get_case(case.case_id)


def test_submission_gate_requires_complete_request_and_records_owner(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    incomplete = _case(store, business_unit=" ")

    with pytest.raises(ValueError, match="business unit"):
        store.submit_case(incomplete.case_id, "product-owner-1")
    assert store.get_case(incomplete.case_id).status == CaseStatus.draft

    case = _case(store)
    submitted = store.submit_case(case.case_id, "product-owner-1")
    assert submitted.status == CaseStatus.analyst_review
    assert submitted.submitted_by == "product-owner-1"
    assert submitted.assigned_to == "analyst-1"

    with pytest.raises(ValueError, match="submitting product owner"):
        store.submit_case(case.case_id, "another-owner")


def test_information_request_pauses_and_resumes_original_review_stage(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    store.submit_case(case.case_id, "product-owner-1")

    paused = store.request_information(case.case_id, "analyst-1", "Confirm the launch geography.")
    assert paused.status == CaseStatus.needs_information
    assert paused.awaiting_from == "product_owner"
    assert paused.information_request == "Confirm the launch geography."
    with pytest.raises(ValueError, match="submitting product owner"):
        store.respond_to_information(case.case_id, "not-the-owner", "Confirmed.")

    resumed = store.respond_to_information(case.case_id, "product-owner-1", "Confirmed from the source request.")
    assert resumed.status == CaseStatus.analyst_review
    assert resumed.information_request is None
    events = store.list_events(case.case_id)
    assert events[-1]["event_type"] == "information_received"
    assert events[-1]["rationale"] == "Confirmed from the source request."


def test_committee_information_request_returns_to_committee_without_votes(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _committee_ready(store)

    store.request_information(case.case_id, "committee-1", "Clarify the control owner.")
    resumed = store.respond_to_information(case.case_id, "product-owner-1", "Control owner is Payments Compliance.")
    assert resumed.status == CaseStatus.committee_review
    assert store.committee_vote_summary(case.case_id)["votes_cast"] == 0

    store.cast_committee_vote(
        case.case_id,
        CommitteeReview(decision="approve", actor="committee-1", rationale="Reviewed response."),
    )
    with pytest.raises(ValueError, match="before committee voting starts"):
        store.request_information(case.case_id, "committee-2", "Need another detail.")


def test_conditional_approval_tracks_conditions_until_completion_then_closes(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _committee_ready(store)
    due_date = date(2026, 12, 31)
    votes = [
        CommitteeReview(
            decision="approve_with_conditions",
            actor="committee-1",
            rationale="Approve after mitigation.",
            conditions="Complete sanctions screening test\nDocument escalation procedure",
            conditions_owner="product-owner-1",
            conditions_due_date=due_date,
        ),
        CommitteeReview(decision="approve", actor="committee-2", rationale="Approve."),
        CommitteeReview(decision="defer", actor="committee-3", rationale="No objection."),
    ]
    for vote in votes:
        decided = store.cast_committee_vote(case.case_id, vote)

    assert decided.status == CaseStatus.conditions_pending
    assert decided.decision.value == "approve_with_conditions"
    conditions = store.list_conditions(case.case_id)
    assert len(conditions) == 2
    assert all(item["owner"] == "product-owner-1" for item in conditions)
    assert all(item["due_date"] == due_date.isoformat() for item in conditions)
    with pytest.raises(ValueError, match="Complete all decision conditions"):
        store.close_case(case.case_id, "analyst-1", "Close.")

    for condition in conditions:
        store.complete_condition(
            case.case_id,
            condition["condition_id"],
            "product-owner-1",
            "Synthetic evidence attached.",
        )
    closed = store.close_case(case.case_id, "analyst-1", "All conditions have evidence.")
    assert closed.status == CaseStatus.closed


def test_reassessment_creates_linked_case_without_changing_prior_decision(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    original = _committee_ready(store)
    store.cast_committee_vote(
        original.case_id,
        CommitteeReview(decision="approve", actor="committee-1", rationale="Approve."),
    )
    store.cast_committee_vote(
        original.case_id,
        CommitteeReview(decision="approve", actor="committee-2", rationale="Approve."),
    )
    decided = store.cast_committee_vote(
        original.case_id,
        CommitteeReview(decision="reject", actor="committee-3", rationale="One dissent."),
    )

    reassessment = store.create_reassessment(decided.case_id, "analyst-1")
    assert reassessment.status == CaseStatus.analyst_review
    assert reassessment.parent_case_id == decided.case_id
    assert reassessment.extracted == decided.extracted
    assert store.get_case(decided.case_id).status == CaseStatus.decisioned

    with pytest.raises(ValueError, match="Only decisioned or closed cases"):
        store.create_reassessment(reassessment.case_id, "analyst-1")


def test_case_closure_and_reassessment_require_terminal_workflow_state(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    with pytest.raises(ValueError, match="Only decisioned or closed"):
        store.create_reassessment(case.case_id, "analyst-1")
    with pytest.raises(ValueError, match="Only decided cases"):
        store.close_case(case.case_id, "analyst-1", "Premature close.")

    high_risk = _case(
        store,
        geographies_involved=["United States", "Iran"],
        customer_segments_involved=["New customers"],
        vendor_involved=True,
        vendor_name="Synthetic vendor",
        products_involved=["Remittance", "Wallet"],
        stated_risk_factors=["rapid funds movement"],
    )
    store.submit_case(high_risk.case_id, "product-owner-1")
    store.review_case(
        high_risk.case_id,
        AnalystReview(
            decision=CaseStatus.analyst_accepted,
            actor="analyst-1",
            rationale="High risk; must proceed to committee.",
        ),
    )
    with pytest.raises(ValueError, match="must complete committee review"):
        store.close_case(high_risk.case_id, "analyst-1", "Premature closure.")


def test_analyst_cannot_finalize_draft_before_product_owner_submission(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    monkeypatch.setattr(intake, "case_store", store)
    analyst = TestClient(app)
    analyst.cookies.set("demo_user", "analyst-1")
    analyst.cookies.set("demo_role", "analyst")

    response = analyst.post(
        f"/intake/{case.case_id}/review",
        data={"decision": "analyst_accepted", "rationale": "Attempt before submission."},
    )
    assert response.status_code == 409
    assert store.get_case(case.case_id).status == CaseStatus.draft


def test_role_headers_do_not_substitute_for_signed_in_demo_cookie(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    monkeypatch.setattr(intake, "case_store", store)

    response = TestClient(app).post(
        f"/intake/{case.case_id}/review",
        data={"decision": "analyst_accepted", "rationale": "Forged header attempt."},
        headers={"X-Demo-User": "analyst-1", "X-Demo-Role": "analyst"},
    )
    assert response.status_code == 403
    assert store.get_case(case.case_id).status == CaseStatus.draft


def test_product_owner_can_correct_incomplete_draft_before_submission(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store, business_unit=" ")
    monkeypatch.setattr(intake, "case_store", store)
    owner = TestClient(app)
    owner.cookies.set("demo_user", "product-owner-1")
    owner.cookies.set("demo_role", "product_owner")

    incomplete = owner.post(f"/intake/{case.case_id}/submit")
    assert incomplete.status_code == 409
    assert "business unit" in incomplete.text

    corrected = owner.post(
        f"/intake/{case.case_id}/draft/edit",
        data={
            "change_title": case.extracted.change_title,
            "business_unit": "Payments",
            "description": case.extracted.description,
            "rationale": "Filled the missing value from the source request.",
        },
    )
    assert corrected.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.draft

    submitted = owner.post(f"/intake/{case.case_id}/submit")
    assert submitted.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.analyst_review

def test_route_workflow_uses_verified_actors_and_returns_case_to_review(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    monkeypatch.setattr(intake, "case_store", store)
    owner = TestClient(app)
    owner.cookies.set("demo_user", "product-owner-1")
    owner.cookies.set("demo_role", "product_owner")
    analyst = TestClient(app)
    analyst.cookies.set("demo_user", "analyst-1")
    analyst.cookies.set("demo_role", "analyst")

    submitted = owner.post(f"/intake/{case.case_id}/submit")
    assert submitted.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.analyst_review

    requested = analyst.post(
        f"/intake/{case.case_id}/request-information",
        data={"rationale": "Confirm the customer segment."},
    )
    assert requested.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.needs_information

    detail = owner.get(f"/intake/product-owner/cases/{case.case_id}")
    assert detail.status_code == 200
    assert "Confirm the customer segment." in detail.text

    response = owner.post(
        f"/intake/{case.case_id}/information-response",
        data={"response": "The request is limited to existing retail customers."},
    )
    assert response.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.analyst_review
    assert store.list_events(case.case_id)[-1]["actor"] == "product-owner-1"


def test_committee_decision_packet_renders_review_trace_and_reassessment_links(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    store.submit_case(case.case_id, "product-owner-1")
    edited = _request(change_title="Corrected synthetic change")
    store.update_extraction(
        case.case_id,
        edited,
        score_change_request(edited),
        "analyst-1",
        "Corrected title from source.",
    )
    finalized = store.review_case(
        case.case_id,
        AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst-1", rationale="Reviewed corrected details."),
    )
    store.submit_committee(finalized.case_id, "analyst-1", "Escalated after revision.")
    monkeypatch.setattr(intake, "case_store", store)
    committee = TestClient(app)
    committee.cookies.set("demo_user", "committee-1")
    committee.cookies.set("demo_role", "committee")

    response = committee.get(f"/intake/committee/cases/{case.case_id}")
    assert response.status_code == 200
    assert "Assessment version 2" in response.text
    assert "Corrected title from source." in response.text
    assert "Quorum: three distinct committee members" in response.text


def test_committee_route_persists_owner_due_date_and_condition_completion(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _committee_ready(store)
    monkeypatch.setattr(intake, "case_store", store)
    committee1 = TestClient(app)
    committee1.cookies.set("demo_user", "committee-1")
    committee1.cookies.set("demo_role", "committee")

    missing_fields = committee1.post(
        f"/intake/{case.case_id}/committee/decision",
        data={
            "decision": "approve_with_conditions",
            "rationale": "Approve with follow-up.",
            "conditions": "Complete screening test",
        },
    )
    assert missing_fields.status_code == 409

    invalid_date = committee1.post(
        f"/intake/{case.case_id}/committee/decision",
        data={
            "decision": "approve_with_conditions",
            "rationale": "Approve with follow-up.",
            "conditions": "Complete screening test",
            "conditions_owner": "product-owner-1",
            "conditions_due_date": "not-a-date",
        },
    )
    assert invalid_date.status_code == 422
    assert "Condition due date must be a valid date." in invalid_date.text

    conditional_vote = committee1.post(
        f"/intake/{case.case_id}/committee/decision",
        data={
            "decision": "approve_with_conditions",
            "rationale": "Approve with follow-up.",
            "conditions": "Complete screening test",
            "conditions_owner": "product-owner-1",
            "conditions_due_date": "2026-12-31",
        },
    )
    assert conditional_vote.status_code == 200
    assert store.list_committee_votes(case.case_id)[0]["conditions_due_date"] == "2026-12-31"
    conditions = store.list_conditions(case.case_id)
    assert conditions == []

    for user, decision in (("committee-2", "approve"), ("committee-3", "defer")):
        member = TestClient(app)
        member.cookies.set("demo_user", user)
        member.cookies.set("demo_role", "committee")
        response = member.post(
            f"/intake/{case.case_id}/committee/decision",
            data={"decision": decision, "rationale": "Reviewed.", "conditions_due_date": ""},
        )
        assert response.status_code == 200

    assert store.get_case(case.case_id).status == CaseStatus.conditions_pending
    owner = TestClient(app)
    owner.cookies.set("demo_user", "product-owner-1")
    owner.cookies.set("demo_role", "product_owner")
    detail = owner.get(f"/intake/product-owner/cases/{case.case_id}")
    assert detail.status_code == 200
    assert "Complete screening test" in detail.text
    assert "2026-12-31" in detail.text
