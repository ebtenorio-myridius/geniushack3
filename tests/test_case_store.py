import pytest

from src.app.models.governance import GovernanceRules, load_governance_rules
from src.app.models.schemas import AnalystReview, CaseStatus, CommitteeReview, ExtractedChangeRequest
from src.app.services.case_store import CaseStore
from src.app.services.risk_scoring import score_change_request


def _request(**overrides):
    values = dict(
        change_title="Synthetic dashboard change",
        change_type="feature_change",
        business_unit="Consumer Banking",
        description="A synthetic accessibility update.",
        products_involved=["Online Banking"],
        extraction_confidence=0.95,
    )
    values.update(overrides)
    return ExtractedChangeRequest(**values)


def test_case_store_persists_and_audits_analyst_review(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))

    assert store.get_case(case.case_id).status == CaseStatus.draft

    reviewed = store.review_case(
        case.case_id,
        AnalystReview(
            decision=CaseStatus.analyst_accepted,
            actor="synthetic-analyst",
            rationale="The extracted fields match the submitted synthetic document.",
        ),
    )

    assert reviewed.status == CaseStatus.analyst_finalized
    reopened = CaseStore(str(tmp_path / "cases.db")).get_case(case.case_id)
    assert reopened.status == CaseStatus.analyst_finalized


def test_case_store_records_manual_seed_provenance(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case(
        "synthetic-manual-seed",
        _request(),
        score_change_request(_request()),
        initial_actor="sample-seed",
        initial_rationale="Manually seeded synthetic sample; no PDF or model extraction used.",
        event_actor="sample-seed",
        event_rationale="Created manual synthetic case for analyst review.",
    )

    event = store.list_events(case.case_id)[0]
    assert event["actor"] == "sample-seed"
    assert event["rationale"] == "Created manual synthetic case for analyst review."


def test_case_store_rejects_second_review(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))
    review = AnalystReview(
        decision=CaseStatus.analyst_rejected,
        actor="synthetic-analyst",
        rationale="The request needs clarification.",
    )
    store.review_case(case.case_id, review)

    try:
        store.review_case(case.case_id, review)
    except ValueError as exc:
        assert "draft or analyst-review" in str(exc)
    else:
        raise AssertionError("A finalized case must not be reviewed twice")


def test_case_store_versions_edits_and_supports_committee_decision(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))
    store.submit_case(case.case_id, "product-owner-1")
    edited = _request(change_title="Edited synthetic change")
    updated = store.update_extraction(
        case.case_id,
        edited,
        score_change_request(edited),
        "synthetic-analyst",
        "Corrected the title from source evidence.",
    )
    assert updated.extraction_version == 2
    assert updated.status == CaseStatus.analyst_review

    finalized = store.review_case(
        case.case_id,
        AnalystReview(
            decision=CaseStatus.analyst_accepted,
            actor="synthetic-analyst",
            rationale="Reviewed the corrected extraction.",
        ),
    )
    assert finalized.status == CaseStatus.analyst_finalized
    submitted = store.submit_committee(case.case_id, "synthetic-analyst", "Escalated for committee review.")
    assert submitted.status == CaseStatus.committee_review
    with pytest.raises(ValueError, match="Direct committee decisions are disabled"):
        store.decide_committee(
            case.case_id,
            CommitteeReview(decision="approve", actor="synthetic-committee", rationale="Approved synthetic case."),
        )
    for actor, decision in (
        ("committee-1", "approve"),
        ("committee-2", "approve"),
        ("committee-3", "defer"),
    ):
        decided = store.cast_committee_vote(
            case.case_id,
            CommitteeReview(decision=decision, actor=actor, rationale="Reviewed synthetic case."),
        )
    assert decided.status == CaseStatus.decisioned


def test_product_owner_draft_correction_keeps_submission_gate_closed(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    incomplete = _request(business_unit="")
    case = store.create_case("synthetic.pdf", incomplete, score_change_request(incomplete))
    corrected = _request(business_unit="Payments")

    updated = store.update_draft(
        case.case_id,
        corrected,
        score_change_request(corrected),
        "product-owner-1",
        "Completed missing business unit from the source request.",
    )
    assert updated.status == CaseStatus.draft
    assert updated.extraction_version == 2
    assert store.list_events(case.case_id)[-1]["actor"] == "product-owner-1"
    assert store.submit_case(case.case_id, "product-owner-1").status == CaseStatus.analyst_review


def test_case_store_requires_three_committee_votes_for_final_decision(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))
    store.review_case(
        case.case_id,
        AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst", rationale="Ready."),
    )
    store.submit_committee(case.case_id, "analyst", "Escalated.")

    first = store.cast_committee_vote(
        case.case_id,
        CommitteeReview(decision="approve", actor="committee-1", rationale="Approve."),
    )
    second = store.cast_committee_vote(
        case.case_id,
        CommitteeReview(decision="approve", actor="committee-2", rationale="Approve."),
    )

    assert first.status == CaseStatus.committee_review
    assert second.status == CaseStatus.committee_review
    assert store.committee_vote_summary(case.case_id)["result"] == "Pending"

    decided = store.cast_committee_vote(
        case.case_id,
        CommitteeReview(decision="reject", actor="committee-3", rationale="Reject."),
    )

    assert decided.status == CaseStatus.decisioned
    summary = store.committee_vote_summary(case.case_id)
    assert summary["approvals"] == 2
    assert summary["rejections"] == 1
    assert summary["result"] == "Approved"


def test_case_uses_its_recorded_rules_snapshot_for_committee_quorum(tmp_path):
    rules_data = load_governance_rules().model_dump(mode="json")
    rules_data["version"] = "test-quorum-2"
    rules_data["workflow"]["committee_votes_required"] = 2
    rules_data["workflow"]["committee_majority_required"] = 2
    rules = GovernanceRules.model_validate(rules_data)
    store = CaseStore(str(tmp_path / "cases.db"))
    request = _request()
    case = store.create_case("synthetic.pdf", request, score_change_request(request, rules))

    assert case.ruleset_version == "test-quorum-2"
    store.review_case(
        case.case_id,
        AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst", rationale="Ready."),
    )
    store.submit_committee(case.case_id, "analyst", "Sent for committee vote.")
    store.cast_committee_vote(
        case.case_id,
        CommitteeReview(decision="approve", actor="committee-1", rationale="Approve."),
    )
    decided = store.cast_committee_vote(
        case.case_id,
        CommitteeReview(decision="approve", actor="committee-2", rationale="Approve."),
    )

    assert decided.status == CaseStatus.decisioned
    assert store.committee_vote_summary(case.case_id)["votes_needed"] == 2


def test_case_store_rejects_duplicate_committee_vote(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))
    store.review_case(case.case_id, AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst", rationale="Ready."))
    store.submit_committee(case.case_id, "analyst", "Escalated.")
    vote = CommitteeReview(decision="approve", actor="committee-1", rationale="Approve.")
    store.cast_committee_vote(case.case_id, vote)

    try:
        store.cast_committee_vote(case.case_id, vote)
    except ValueError as exc:
        assert "already voted" in str(exc)
    else:
        raise AssertionError("A committee member must not vote twice on the same case")


def test_case_store_defers_when_three_votes_have_no_approval_or_rejection_majority(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))
    store.review_case(case.case_id, AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst", rationale="Ready."))
    store.submit_committee(case.case_id, "analyst", "Escalated.")

    for actor, decision in [
        ("committee-1", "approve"),
        ("committee-2", "reject"),
        ("committee-3", "defer"),
    ]:
        case = store.cast_committee_vote(
            case.case_id,
            CommitteeReview(decision=decision, actor=actor, rationale="Synthetic committee vote."),
        )

    summary = store.committee_vote_summary(case.case_id)
    decision_event = store.list_events(case.case_id)[-1]
    assert case.status == CaseStatus.decisioned
    assert summary["deferred"] == 1
    assert summary["votes_cast"] == 3
    assert summary["result"] == "Deferred"
    assert "defer: Vote result" in decision_event["rationale"]


def test_case_store_rejects_when_two_committee_members_vote_to_reject(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    case = store.create_case("synthetic.pdf", _request(), score_change_request(_request()))
    store.review_case(case.case_id, AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst", rationale="Ready."))
    store.submit_committee(case.case_id, "analyst", "Escalated.")

    for actor, decision in [
        ("committee-1", "reject"),
        ("committee-2", "reject"),
        ("committee-3", "approve"),
    ]:
        case = store.cast_committee_vote(
            case.case_id,
            CommitteeReview(decision=decision, actor=actor, rationale="Synthetic committee vote."),
        )

    summary = store.committee_vote_summary(case.case_id)
    assert case.status == CaseStatus.decisioned
    assert summary["result"] == "Rejected"


def test_case_store_lists_cases_by_workflow_status(tmp_path):
    store = CaseStore(str(tmp_path / "cases.db"))
    draft = store.create_case("draft.pdf", _request(), score_change_request(_request()))
    finalized_request = _request(change_title="Finalized case")
    finalized = store.create_case("finalized.pdf", finalized_request, score_change_request(finalized_request))
    store.review_case(
        finalized.case_id,
        AnalystReview(decision=CaseStatus.analyst_accepted, actor="analyst", rationale="Reviewed."),
    )

    all_cases = store.list_cases()
    finalized_cases = store.list_cases((CaseStatus.analyst_finalized,))

    assert {case.case_id for case in all_cases} == {draft.case_id, finalized.case_id}
    assert [case.case_id for case in finalized_cases] == [finalized.case_id]
