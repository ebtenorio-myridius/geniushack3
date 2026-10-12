import hashlib
import io
import json
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.models.schemas import (
    AnalystReview,
    CaseStatus,
    CommitteeReview,
    EvidenceCitation,
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


def test_all_product_owner_submissions_enter_analyst_queue_before_committee(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    low_risk = _case(
        store,
        change_type="feature_change",
        geographies_involved=["United States"],
        products_involved=["Remittance"],
        stated_risk_factors=[],
    )
    high_risk = _case(
        store,
        geographies_involved=["United States", "Iran"],
        customer_segments_involved=["New customers"],
        vendor_involved=True,
        vendor_name="Synthetic vendor",
        products_involved=["Remittance", "Wallet"],
        stated_risk_factors=["rapid funds movement"],
    )

    assert low_risk.assessment.requires_committee_review is False
    assert high_risk.assessment.requires_committee_review is True
    monkeypatch.setattr(intake, "case_store", store)
    owner = TestClient(app)
    owner.cookies.set("demo_user", "product-owner-1")
    owner.cookies.set("demo_role", "product_owner")

    low_submission = owner.post(f"/intake/{low_risk.case_id}/submit")
    assert low_submission.status_code == 200
    assert store.get_case(low_risk.case_id).status == CaseStatus.analyst_review

    high_submission = owner.post(f"/intake/{high_risk.case_id}/submit")
    assert high_submission.status_code == 200
    assert store.get_case(high_risk.case_id).status == CaseStatus.analyst_review
    assert "analyst review queue" in high_submission.text

    analyst = TestClient(app)
    analyst.cookies.set("demo_user", "analyst-1")
    analyst.cookies.set("demo_role", "analyst")
    analyst_dashboard = analyst.get("/intake/analyst/dashboard/demo")
    assert analyst_dashboard.status_code == 200
    assert low_risk.case_id in analyst_dashboard.text
    assert high_risk.case_id in analyst_dashboard.text

    committee = TestClient(app)
    committee.cookies.set("demo_user", "committee-1")
    committee.cookies.set("demo_role", "committee")
    committee_dashboard = committee.get("/intake/committee/dashboard/demo")
    assert committee_dashboard.status_code == 200
    assert high_risk.case_id not in committee_dashboard.text
    assert low_risk.case_id not in committee_dashboard.text

    finalized = store.review_case(
        high_risk.case_id,
        AnalystReview(
            decision=CaseStatus.analyst_accepted,
            actor="analyst-1",
            rationale="Verified high-risk facts and finalized the assessment.",
        ),
    )
    assert finalized.status == CaseStatus.analyst_finalized
    with pytest.raises(ValueError, match="Only decided cases"):
        store.close_case(high_risk.case_id, "analyst-1", "Cannot close before committee decision.")
    submitted_to_committee = analyst.post(
        f"/intake/{high_risk.case_id}/committee/submit",
        data={"rationale": "Assessment is finalized; requesting committee decision."},
    )
    assert submitted_to_committee.status_code == 200
    assert store.get_case(high_risk.case_id).status == CaseStatus.committee_review
    assert "committee decision queue" in submitted_to_committee.text

    committee_dashboard = committee.get("/intake/committee/dashboard/demo")
    assert high_risk.case_id in committee_dashboard.text
    committee_detail = committee.get(f"/intake/committee/cases/{high_risk.case_id}")
    assert committee_detail.status_code == 200
    assert "Verify the extracted facts and risk score" not in committee_detail.text

    assert analyst.post(
        f"/intake/{low_risk.case_id}/review",
        data={
            "decision": "analyst_accepted",
            "rationale": "Verified low-risk facts and finalized the assessment.",
        },
    ).status_code == 200
    assert analyst.post(
        f"/intake/{low_risk.case_id}/committee/submit",
        data={"rationale": "Submitting the finalized low-risk assessment for the required committee decision."},
    ).status_code == 200
    committee_dashboard = committee.get("/intake/committee/dashboard/demo")
    assert low_risk.case_id in committee_dashboard.text


def test_product_owner_dashboard_shows_pending_and_committee_outcome(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _committee_ready(store)
    monkeypatch.setattr(intake, "case_store", store)

    owner = TestClient(app)
    owner.cookies.set("demo_user", "product-owner-1")
    owner.cookies.set("demo_role", "product_owner")

    pending_dashboard = owner.get("/intake/product-owner/dashboard/demo")
    assert pending_dashboard.status_code == 200
    assert "Pending committee decision" in pending_dashboard.text

    for actor, decision in (
        ("committee-1", "approve"),
        ("committee-2", "approve"),
        ("committee-3", "defer"),
    ):
        store.cast_committee_vote(
            case.case_id,
            CommitteeReview(
                decision=decision,
                actor=actor,
                rationale="Reviewed the finalized assessment.",
            ),
        )

    decided_dashboard = owner.get("/intake/product-owner/dashboard/demo")
    assert decided_dashboard.status_code == 200
    assert "Approved" in decided_dashboard.text
    assert "decisioned</span>" not in decided_dashboard.text


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
    submitted = store.submit_case(high_risk.case_id, "product-owner-1")
    assert submitted.status == CaseStatus.analyst_review
    with pytest.raises(ValueError, match="Only decided cases"):
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
    request = _request(
        business_unit=" ",
        evidence=[
            EvidenceCitation(field_name="change_title", page_number=1, quote="Synthetic cross-border payment change"),
            EvidenceCitation(field_name="change_type", page_number=1, quote="new product"),
            EvidenceCitation(field_name="description", page_number=1, quote="Synthetic launch with updated payment flows."),
            EvidenceCitation(field_name="geographies_involved", page_number=1, quote="United States; Philippines"),
            EvidenceCitation(field_name="products_involved", page_number=1, quote="Remittance"),
        ],
    )
    page_text = "Synthetic cross-border payment change; new product; Synthetic launch with updated payment flows.; United States; Philippines; Remittance; Payments"
    case = store.create_case(
        "synthetic.pdf",
        request,
        score_change_request(request),
        source_document_bytes=b"synthetic source bytes",
        source_pages=[page_text],
    )
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
            "source_citations": "business_unit | 1 | Payments",
            "rationale": "Filled the missing value from the source request.",
        },
    )
    assert corrected.status_code == 200
    assert store.get_case(case.case_id).status == CaseStatus.draft
    saved = store.get_case(case.case_id)
    assert any(
        item.field_name == "business_unit" and item.quote == "Payments"
        for item in saved.extracted.evidence
    )

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
    assert "Quorum: 3 distinct committee members" in response.text


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


def test_source_document_hash_and_audit_chain_verification(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = store.create_case(
        "source.pdf",
        _request(),
        score_change_request(_request()),
        source_document_bytes=b"retained synthetic document",
        source_pages=["page one"],
    )

    metadata, content = store.read_source_document(case.case_id)
    assert content == b"retained synthetic document"
    assert metadata["sha256"] == case.source_sha256
    assert store.list_source_pages(case.case_id) == [{"page_number": 1, "page_text": "page one"}]
    assert store.verify_audit_chain(case.case_id)["valid"]

    with store._connect() as connection:
        connection.execute(
            "UPDATE source_pages SET page_text = ? WHERE case_id = ?",
            ("tampered page", case.case_id),
        )
    assert store.verify_audit_chain(case.case_id)["valid"] is False

    with store._connect() as connection:
        connection.execute(
            "UPDATE source_pages SET page_text = ? WHERE case_id = ?",
            ("page one", case.case_id),
        )
        connection.execute(
            "UPDATE workflow_events SET rationale = ? WHERE case_id = ?",
            ("tampered rationale", case.case_id),
        )
    verification = store.verify_audit_chain(case.case_id)
    assert verification["valid"] is False
    assert verification["first_invalid_event_id"] is not None

    with store._connect() as connection:
        connection.execute("DELETE FROM workflow_events WHERE case_id = ?", (case.case_id,))
    verification = store.verify_audit_chain(case.case_id)
    assert verification["valid"] is False
    assert verification["error"] == "No workflow events are recorded for this case."


def test_examiner_style_export_contains_verification_manifest_and_source(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = store.create_case(
        "source.pdf",
        _request(),
        score_change_request(_request()),
        source_document_bytes=b"synthetic source",
        source_pages=["source page"],
    )
    monkeypatch.setattr(intake, "case_store", store)
    analyst = TestClient(app)
    analyst.cookies.set("demo_user", "analyst-1")
    analyst.cookies.set("demo_role", "analyst")

    response = analyst.get(f"/intake/{case.case_id}/examiner-export")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        record_bytes = bundle.read("case-record.json")
        record = json.loads(record_bytes)
        manifest = json.loads(bundle.read("manifest.json"))
        source = bundle.read("source-document.pdf")

    assert record["case"]["case_id"] == case.case_id
    assert record["audit_verification"]["valid"] is True
    assert record["source_pages"] == [{"page_number": 1, "page_text": "source page"}]
    assert source == b"synthetic source"
    assert manifest["files"]["source-document.pdf"]["sha256"] == case.source_sha256
    assert manifest["files"]["case-record.json"]["sha256"] == hashlib.sha256(record_bytes).hexdigest()
    assert manifest["files"]["case-record.json"]["byte_length"] == len(record_bytes)
    assert manifest["audit_chain_head"] == record["audit_verification"]["chain_head"]

    owner = TestClient(app)
    owner.cookies.set("demo_user", "product-owner-1")
    owner.cookies.set("demo_role", "product_owner")
    download = owner.get(f"/intake/{case.case_id}/source-document")
    assert download.status_code == 200
    assert download.content == b"synthetic source"

    assert TestClient(app).get(f"/intake/{case.case_id}/source-document").status_code == 403


def test_analyst_finalization_is_not_a_completed_case_until_committee_decision(tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    store.submit_case(case.case_id, "product-owner-1")
    store.review_case(
        case.case_id,
        AnalystReview(
            decision=CaseStatus.analyst_accepted,
            actor="analyst-1",
            rationale="Reviewed the low-risk case.",
        ),
    )

    metrics = store.cycle_time_metrics(case.case_id)
    assert metrics["status"] == "in_progress"
    assert metrics["decided_at"] is None
    assert metrics["decision_ready_hours"] is not None
    assert metrics["sla_met"] is None
    store.submit_committee(case.case_id, "analyst-1", "Finalized assessment submitted for committee decision.")
    for actor, decision in (
        ("committee-1", "approve"),
        ("committee-2", "approve"),
        ("committee-3", "defer"),
    ):
        store.cast_committee_vote(
            case.case_id,
            CommitteeReview(decision=decision, actor=actor, rationale="Committee decision."),
        )

    metrics = store.cycle_time_metrics(case.case_id)
    assert metrics["status"] == "complete"
    assert metrics["decided_at"] is not None
    assert metrics["sla_met"] is True
    report = store.cycle_time_report()
    assert report["completed_cases"] == 1
    assert report["median_decision_ready_hours"] is not None


def test_analyst_cycle_time_metrics_page_uses_recorded_report(monkeypatch, tmp_path):
    store = CaseStore(str(tmp_path / "workflow.db"))
    case = _case(store)
    store.submit_case(case.case_id, "product-owner-1")
    monkeypatch.setattr(intake, "case_store", store)
    analyst = TestClient(app)
    analyst.cookies.set("demo_user", "analyst-1")
    analyst.cookies.set("demo_role", "analyst")

    response = analyst.get("/intake/analyst/metrics")
    assert response.status_code == 200
    assert case.case_id in response.text
    assert "does not establish a two-day performance claim" in response.text
    assert "Decision-ready hours" in response.text
