import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.app.models.schemas import (
    AnalystReview,
    CaseRecord,
    CaseStatus,
    CommitteeDecision,
    CommitteeReview,
    ExtractedChangeRequest,
    PolicyEvidence,
    RiskAssessmentDraft,
    TelemetryRecord,
)


class CaseStore:
    """Small SQLite store for cases and append-only workflow events."""

    def __init__(self, database_path: str = "risk_workbench.db"):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS cases (
                        case_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        extracted_json TEXT NOT NULL,
                        assessment_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        submitted_by TEXT NOT NULL DEFAULT 'product-owner-1',
                        assigned_to TEXT,
                        parent_case_id TEXT,
                        resume_status TEXT,
                        information_request TEXT,
                        awaiting_from TEXT,
                        decision TEXT
                    );
                    CREATE TABLE IF NOT EXISTS extraction_versions (
                        case_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        extracted_json TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY(case_id, version)
                    );
                    CREATE TABLE IF NOT EXISTS workflow_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        FOREIGN KEY(case_id) REFERENCES cases(case_id)
                    );
                    CREATE TABLE IF NOT EXISTS committee_votes (
                        case_id TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        decision TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        conditions TEXT NOT NULL,
                        conditions_owner TEXT NOT NULL DEFAULT '',
                        conditions_due_date TEXT,
                        occurred_at TEXT NOT NULL,
                        PRIMARY KEY(case_id, actor),
                        FOREIGN KEY(case_id) REFERENCES cases(case_id)
                    );
                    CREATE TABLE IF NOT EXISTS telemetry (
                        telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation TEXT NOT NULL,
                        model TEXT NOT NULL,
                        prompt_version TEXT NOT NULL,
                        latency_ms INTEGER NOT NULL,
                        input_tokens INTEGER,
                        output_tokens INTEGER,
                        success INTEGER NOT NULL,
                        error_type TEXT,
                        occurred_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS conditions (
                        condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id TEXT NOT NULL,
                        description TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        due_date TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'open',
                        completion_evidence TEXT,
                        completed_by TEXT,
                        completed_at TEXT,
                        FOREIGN KEY(case_id) REFERENCES cases(case_id)
                    );
                    """
                )
                columns = {row[1] for row in connection.execute("PRAGMA table_info(cases)")}
                if "policy_evidence_json" not in columns:
                    connection.execute("ALTER TABLE cases ADD COLUMN policy_evidence_json TEXT NOT NULL DEFAULT '[]'")
                if "extraction_version" not in columns:
                    connection.execute("ALTER TABLE cases ADD COLUMN extraction_version INTEGER NOT NULL DEFAULT 1")
                for name, definition in (
                    ("submitted_by", "TEXT NOT NULL DEFAULT 'product-owner-1'"),
                    ("assigned_to", "TEXT"),
                    ("parent_case_id", "TEXT"),
                    ("resume_status", "TEXT"),
                    ("information_request", "TEXT"),
                    ("awaiting_from", "TEXT"),
                    ("decision", "TEXT"),
                ):
                    if name not in columns:
                        connection.execute(f"ALTER TABLE cases ADD COLUMN {name} {definition}")
                vote_columns = {row[1] for row in connection.execute("PRAGMA table_info(committee_votes)")}
                if "conditions_owner" not in vote_columns:
                    connection.execute("ALTER TABLE committee_votes ADD COLUMN conditions_owner TEXT NOT NULL DEFAULT ''")
                if "conditions_due_date" not in vote_columns:
                    connection.execute("ALTER TABLE committee_votes ADD COLUMN conditions_due_date TEXT")

    def create_case(
        self,
        filename: str,
        extracted: ExtractedChangeRequest,
        assessment: RiskAssessmentDraft,
        policy_evidence: list[PolicyEvidence] | None = None,
        *,
        initial_actor: str = "system",
        initial_rationale: str = "Initial model extraction",
        event_actor: str = "system",
        event_rationale: str = "Initial extraction and draft score",
        submitted_by: str = "product-owner-1",
        parent_case_id: str | None = None,
    ) -> CaseRecord:
        now = datetime.now(timezone.utc)
        case = CaseRecord(
            case_id=f"CASE-{uuid4().hex[:10].upper()}",
            filename=filename,
            extracted=extracted,
            assessment=assessment,
            policy_evidence=policy_evidence or [],
            created_at=now,
            updated_at=now,
            submitted_by=submitted_by,
            assigned_to="analyst-1",
            parent_case_id=parent_case_id,
        )
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO cases (case_id, filename, extracted_json, assessment_json, status, created_at, updated_at, policy_evidence_json, extraction_version, submitted_by, assigned_to, parent_case_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        case.case_id,
                        case.filename,
                        extracted.model_dump_json(),
                        assessment.model_dump_json(),
                        case.status.value,
                        now.isoformat(),
                        now.isoformat(),
                        json.dumps([item.model_dump() for item in case.policy_evidence]),
                        case.extraction_version,
                        case.submitted_by,
                        case.assigned_to,
                        case.parent_case_id,
                    ),
                )
                connection.execute(
                    "INSERT INTO extraction_versions VALUES (?, ?, ?, ?, ?, ?)",
                    (case.case_id, 1, extracted.model_dump_json(), initial_actor, initial_rationale, now.isoformat()),
                )
                self._record_event(connection, case.case_id, "case_created", event_actor, event_rationale)
        return case

    def get_case(self, case_id: str) -> CaseRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            return None
        return CaseRecord(
            case_id=row["case_id"],
            filename=row["filename"],
            extracted=ExtractedChangeRequest.model_validate(json.loads(row["extracted_json"])),
            assessment=RiskAssessmentDraft.model_validate(json.loads(row["assessment_json"])),
            policy_evidence=[PolicyEvidence.model_validate(item) for item in json.loads(row["policy_evidence_json"])],
            extraction_version=row["extraction_version"],
            status=CaseStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            submitted_by=row["submitted_by"],
            assigned_to=row["assigned_to"],
            parent_case_id=row["parent_case_id"],
            information_request=row["information_request"],
            awaiting_from=row["awaiting_from"],
            decision=CommitteeDecision(row["decision"]) if row["decision"] else None,
        )

    def list_extraction_versions(self, case_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT version, extracted_json, actor, rationale, created_at FROM extraction_versions WHERE case_id = ? ORDER BY version",
                (case_id,),
            ).fetchall()
        versions = []
        previous = None
        for row in rows:
            extracted = ExtractedChangeRequest.model_validate(json.loads(row["extracted_json"])).model_dump(mode="json")
            changes = []
            if previous is not None:
                changes = [
                    {"field": field, "before": previous[field], "after": extracted[field]}
                    for field in extracted
                    if extracted[field] != previous[field]
                ]
            versions.append(
                {
                    "version": row["version"],
                    "actor": row["actor"],
                    "rationale": row["rationale"],
                    "created_at": row["created_at"],
                    "changes": changes,
                }
            )
            previous = extracted
        return versions

    def submit_case(self, case_id: str, actor: str) -> CaseRecord:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        if case.submitted_by != actor:
            raise ValueError("Only the submitting product owner can submit this case")
        required = {
            "change title": case.extracted.change_title,
            "business unit": case.extracted.business_unit,
            "description": case.extracted.description,
        }
        missing = [label for label, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(f"Complete the required fields before submitting: {', '.join(missing)}")
        return self._transition(case_id, CaseStatus.draft, CaseStatus.analyst_review, actor, "Submitted complete change request for analyst review.")

    def request_information(self, case_id: str, actor: str, rationale: str) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status, submitted_by FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                status = CaseStatus(row["status"])
                if status not in (CaseStatus.analyst_review, CaseStatus.committee_review):
                    raise ValueError("Information can only be requested during analyst or committee review")
                if status == CaseStatus.committee_review:
                    votes = connection.execute("SELECT COUNT(*) FROM committee_votes WHERE case_id = ?", (case_id,)).fetchone()[0]
                    if votes:
                        raise ValueError("Information requests must be made before committee voting starts")
                connection.execute(
                    "UPDATE cases SET status = ?, resume_status = ?, information_request = ?, awaiting_from = ?, updated_at = ? WHERE case_id = ?",
                    (CaseStatus.needs_information.value, status.value, rationale, "product_owner", now.isoformat(), case_id),
                )
                self._record_event(connection, case_id, "information_requested", actor, rationale)
        return self.get_case(case_id)

    def respond_to_information(self, case_id: str, actor: str, response: str) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute(
                    "SELECT status, submitted_by, resume_status FROM cases WHERE case_id = ?",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] != CaseStatus.needs_information.value:
                    raise ValueError("This case is not waiting for information")
                if actor != row["submitted_by"]:
                    raise ValueError("Only the submitting product owner can respond to this information request")
                if not row["resume_status"]:
                    raise ValueError("The case has no recorded workflow stage to resume")
                connection.execute(
                    "UPDATE cases SET status = ?, resume_status = NULL, information_request = NULL, awaiting_from = NULL, updated_at = ? WHERE case_id = ?",
                    (row["resume_status"], now.isoformat(), case_id),
                )
                self._record_event(connection, case_id, "information_received", actor, response)
        return self.get_case(case_id)

    def create_reassessment(self, case_id: str, actor: str) -> CaseRecord:
        original = self.get_case(case_id)
        if original is None:
            raise KeyError(case_id)
        if original.status not in (CaseStatus.decisioned, CaseStatus.conditions_pending, CaseStatus.closed):
            raise ValueError("Only decisioned or closed cases can be reassessed")
        reassessment = self.create_case(
            f"Reassessment of {original.filename}",
            original.extracted,
            original.assessment,
            original.policy_evidence,
            initial_actor=actor,
            initial_rationale=f"Reassessment created from {case_id}.",
            event_actor=actor,
            event_rationale=f"Reassessment created from {case_id}; analyst must review updated facts.",
            submitted_by=original.submitted_by,
            parent_case_id=case_id,
        )
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?",
                    (CaseStatus.analyst_review.value, now.isoformat(), reassessment.case_id),
                )
                self._record_event(connection, reassessment.case_id, "reassessment_started", actor, f"Reassessment of {case_id} opened for analyst review.")
        return self.get_case(reassessment.case_id)

    def review_case(self, case_id: str, review: AnalystReview) -> CaseRecord:
        if review.decision not in (CaseStatus.analyst_accepted, CaseStatus.analyst_rejected):
            raise ValueError("Analyst review must accept or reject the draft")
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] not in (CaseStatus.draft.value, CaseStatus.analyst_review.value):
                    raise ValueError("Only draft or analyst-review cases can be finalized")
                next_status = CaseStatus.analyst_finalized
                connection.execute(
                    "UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?",
                    (CaseStatus.analyst_rejected.value if review.decision == CaseStatus.analyst_rejected else next_status.value, now.isoformat(), case_id),
                )
                self._record_event(connection, case_id, review.decision.value, review.actor, review.rationale)
        return self.get_case(case_id)

    def update_extraction(self, case_id: str, extracted: ExtractedChangeRequest, assessment: RiskAssessmentDraft, actor: str, rationale: str, policy_evidence: list[PolicyEvidence] | None = None) -> CaseRecord:
        return self._save_extraction(
            case_id,
            extracted,
            assessment,
            actor,
            rationale,
            policy_evidence,
            expected_status=CaseStatus.analyst_review,
        )

    def update_draft(self, case_id: str, extracted: ExtractedChangeRequest, assessment: RiskAssessmentDraft, actor: str, rationale: str, policy_evidence: list[PolicyEvidence] | None = None) -> CaseRecord:
        return self._save_extraction(
            case_id,
            extracted,
            assessment,
            actor,
            rationale,
            policy_evidence,
            expected_status=CaseStatus.draft,
        )

    def _save_extraction(
        self,
        case_id: str,
        extracted: ExtractedChangeRequest,
        assessment: RiskAssessmentDraft,
        actor: str,
        rationale: str,
        policy_evidence: list[PolicyEvidence] | None,
        *,
        expected_status: CaseStatus,
    ) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status, extraction_version FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] != expected_status.value:
                    raise ValueError(f"Only {expected_status.value.replace('_', ' ')} cases can be edited")
                version = row["extraction_version"] + 1
                evidence_json = json.dumps([item.model_dump() for item in (policy_evidence or [])])
                connection.execute("UPDATE cases SET extracted_json = ?, assessment_json = ?, policy_evidence_json = ?, extraction_version = ?, updated_at = ? WHERE case_id = ?", (extracted.model_dump_json(), assessment.model_dump_json(), evidence_json, version, now.isoformat(), case_id))
                connection.execute("INSERT INTO extraction_versions VALUES (?, ?, ?, ?, ?, ?)", (case_id, version, extracted.model_dump_json(), actor, rationale, now.isoformat()))
                self._record_event(connection, case_id, "extraction_edited", actor, rationale)
        return self.get_case(case_id)

    def submit_committee(self, case_id: str, actor: str, rationale: str) -> CaseRecord:
        return self._transition(case_id, CaseStatus.analyst_finalized, CaseStatus.committee_review, actor, rationale)

    def decide_committee(self, case_id: str, review: CommitteeReview) -> CaseRecord:
        rationale = review.rationale
        if review.conditions:
            rationale = f"{rationale} Conditions: {review.conditions}"
        self._transition(case_id, CaseStatus.committee_review, CaseStatus.decisioned, review.actor, f"{review.decision.value}: {rationale}")
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "UPDATE cases SET decision = ? WHERE case_id = ?",
                    (review.decision.value, case_id),
                )
        return self.get_case(case_id)

    def cast_committee_vote(self, case_id: str, review: CommitteeReview) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status, submitted_by FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] != CaseStatus.committee_review.value:
                    raise ValueError("Case must be committee_review before committee voting")
                if review.decision == CommitteeDecision.approve_with_conditions:
                    if not self._condition_lines(review.conditions):
                        raise ValueError("Add at least one condition before voting to approve with conditions")
                    if not review.conditions_owner.strip() or not review.conditions_due_date:
                        raise ValueError("Every condition needs an owner and due date")
                if review.conditions.strip() and (not review.conditions_owner.strip() or not review.conditions_due_date):
                    raise ValueError("Every condition needs an owner and due date")
                if review.conditions.strip() and review.conditions_owner != row["submitted_by"]:
                    raise ValueError("Conditions must be assigned to the submitting product owner in this demo")
                existing = connection.execute(
                    "SELECT 1 FROM committee_votes WHERE case_id = ? AND actor = ?",
                    (case_id, review.actor),
                ).fetchone()
                if existing is not None:
                    raise ValueError("Committee member has already voted on this case")
                connection.execute(
                    "INSERT INTO committee_votes (case_id, actor, decision, rationale, conditions, conditions_owner, conditions_due_date, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (case_id, review.actor, review.decision.value, review.rationale, review.conditions, review.conditions_owner, review.conditions_due_date.isoformat() if review.conditions_due_date else None, now.isoformat()),
                )
                vote_rationale = review.rationale
                if review.conditions:
                    vote_rationale = f"{vote_rationale} Conditions: {review.conditions}"
                self._record_event(connection, case_id, "committee_vote", review.actor, f"{review.decision.value}: {vote_rationale}")

                votes = connection.execute(
                    "SELECT decision, rationale, conditions, conditions_owner, conditions_due_date FROM committee_votes WHERE case_id = ? ORDER BY occurred_at",
                    (case_id,),
                ).fetchall()
                approvals = sum(1 for vote in votes if vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value))
                rejections = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.reject.value)
                deferred = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.defer.value)
                if len(votes) >= 3:
                    if approvals >= 2:
                        final_decision = CommitteeDecision.approve_with_conditions.value if any(
                            vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value)
                            and (vote["decision"] == CommitteeDecision.approve_with_conditions.value or vote["conditions"])
                            for vote in votes
                        ) else CommitteeDecision.approve.value
                    elif rejections >= 2:
                        final_decision = CommitteeDecision.reject.value
                    else:
                        final_decision = CommitteeDecision.defer.value
                    conditional = final_decision == CommitteeDecision.approve_with_conditions.value
                    next_status = CaseStatus.conditions_pending if conditional else CaseStatus.decisioned
                    connection.execute(
                        "UPDATE cases SET status = ?, decision = ?, updated_at = ? WHERE case_id = ?",
                        (next_status.value, final_decision, now.isoformat(), case_id),
                    )
                    if conditional:
                        for vote in votes:
                            if vote["decision"] not in (
                                CommitteeDecision.approve.value,
                                CommitteeDecision.approve_with_conditions.value,
                            ):
                                continue
                            for item in self._condition_lines(vote["conditions"]):
                                if not vote["conditions_owner"] or not vote["conditions_due_date"]:
                                    raise ValueError("Every condition needs an owner and due date")
                                connection.execute(
                                    "INSERT INTO conditions (case_id, description, owner, due_date) VALUES (?, ?, ?, ?)",
                                    (case_id, item, vote["conditions_owner"], vote["conditions_due_date"]),
                                )
                    self._record_event(connection, case_id, CaseStatus.decisioned.value, "committee", f"{final_decision}: Vote result {approvals} approvals, {rejections} rejections, {deferred} deferrals")
        return self.get_case(case_id)

    def list_committee_votes(self, case_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT actor, decision, rationale, conditions, conditions_owner, conditions_due_date, occurred_at FROM committee_votes WHERE case_id = ? ORDER BY occurred_at",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _condition_lines(text: str) -> list[str]:
        return [line.strip(" -\t") for line in text.splitlines() if line.strip(" -\t")]

    def list_conditions(self, case_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT condition_id, description, owner, due_date, status, completion_evidence, completed_by, completed_at FROM conditions WHERE case_id = ? ORDER BY condition_id",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def complete_condition(self, case_id: str, condition_id: int, actor: str, evidence: str) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                case = connection.execute("SELECT submitted_by, status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if case is None:
                    raise KeyError(case_id)
                if case["submitted_by"] != actor:
                    raise ValueError("Only the submitting product owner can complete this condition")
                if case["status"] != CaseStatus.conditions_pending.value:
                    raise ValueError("Conditions can only be completed while the case is awaiting conditions")
                updated = connection.execute(
                    "UPDATE conditions SET status = 'completed', completion_evidence = ?, completed_by = ?, completed_at = ? WHERE case_id = ? AND condition_id = ? AND status = 'open'",
                    (evidence, actor, now.isoformat(), case_id, condition_id),
                )
                if updated.rowcount != 1:
                    raise ValueError("Condition not found or already completed")
                self._record_event(connection, case_id, "condition_completed", actor, evidence)
        return self.get_case(case_id)

    def close_case(self, case_id: str, actor: str, rationale: str) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status, assessment_json FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] not in (CaseStatus.decisioned.value, CaseStatus.conditions_pending.value, CaseStatus.analyst_finalized.value):
                    raise ValueError("Only decided cases can be closed")
                if row["status"] == CaseStatus.analyst_finalized.value:
                    assessment = RiskAssessmentDraft.model_validate(json.loads(row["assessment_json"]))
                    if assessment.requires_committee_review:
                        raise ValueError("High/critical assessments must complete committee review before closure")
                open_count = connection.execute(
                    "SELECT COUNT(*) FROM conditions WHERE case_id = ? AND status != 'completed'",
                    (case_id,),
                ).fetchone()[0]
                if open_count:
                    raise ValueError("Complete all decision conditions before closing the case")
                connection.execute(
                    "UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?",
                    (CaseStatus.closed.value, now.isoformat(), case_id),
                )
                self._record_event(connection, case_id, "case_closed", actor, rationale)
        return self.get_case(case_id)

    def committee_vote_summary(self, case_id: str) -> dict:
        votes = self.list_committee_votes(case_id)
        approvals = sum(1 for vote in votes if vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value))
        rejections = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.reject.value)
        deferred = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.defer.value)
        votes_cast = len(votes)
        if votes_cast < 3:
            result = "Pending"
        elif approvals >= 2:
            result = "Approved"
        elif rejections >= 2:
            result = "Rejected"
        else:
            result = "Deferred"
        return {
            "approvals": approvals,
            "rejections": rejections,
            "deferred": deferred,
            "votes_cast": votes_cast,
            "votes_needed": 3,
            "result": result,
            "votes": votes,
        }

    def _transition(self, case_id: str, expected: CaseStatus, target: CaseStatus, actor: str, rationale: str) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] != expected.value:
                    raise ValueError(f"Case must be {expected.value} before {target.value}")
                connection.execute("UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?", (target.value, now.isoformat(), case_id))
                self._record_event(connection, case_id, target.value, actor, rationale)
        return self.get_case(case_id)

    def record_telemetry(self, telemetry: TelemetryRecord):
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("INSERT INTO telemetry (operation, model, prompt_version, latency_ms, input_tokens, output_tokens, success, error_type, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (telemetry.operation, telemetry.model, telemetry.prompt_version, telemetry.latency_ms, telemetry.input_tokens, telemetry.output_tokens, int(telemetry.success), telemetry.error_type, datetime.now(timezone.utc).isoformat()))

    def list_committee_cases(self) -> list[CaseRecord]:
        with closing(self._connect()) as connection:
            ids = [row[0] for row in connection.execute("SELECT case_id FROM cases WHERE status = ?", (CaseStatus.committee_review.value,))]
        return [self.get_case(case_id) for case_id in ids]

    def list_cases(self, statuses: tuple[CaseStatus, ...] | None = None) -> list[CaseRecord]:
        with closing(self._connect()) as connection:
            if statuses:
                placeholders = ", ".join("?" for _ in statuses)
                values = tuple(status.value for status in statuses)
                rows = connection.execute(
                    f"SELECT case_id FROM cases WHERE status IN ({placeholders}) ORDER BY updated_at DESC",
                    values,
                ).fetchall()
            else:
                rows = connection.execute("SELECT case_id FROM cases ORDER BY updated_at DESC").fetchall()
        return [self.get_case(row[0]) for row in rows]

    def list_events(self, case_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT event_type, actor, rationale, occurred_at FROM workflow_events WHERE case_id = ? ORDER BY event_id",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _record_event(connection, case_id: str, event_type: str, actor: str, rationale: str):
        connection.execute(
            "INSERT INTO workflow_events (case_id, event_type, actor, rationale, occurred_at) VALUES (?, ?, ?, ?, ?)",
            (case_id, event_type, actor, rationale, datetime.now(timezone.utc).isoformat()),
        )
