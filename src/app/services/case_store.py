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
                        updated_at TEXT NOT NULL
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
                    """
                )
                columns = {row[1] for row in connection.execute("PRAGMA table_info(cases)")}
                if "policy_evidence_json" not in columns:
                    connection.execute("ALTER TABLE cases ADD COLUMN policy_evidence_json TEXT NOT NULL DEFAULT '[]'")
                if "extraction_version" not in columns:
                    connection.execute("ALTER TABLE cases ADD COLUMN extraction_version INTEGER NOT NULL DEFAULT 1")

    def create_case(
        self,
        filename: str,
        extracted: ExtractedChangeRequest,
        assessment: RiskAssessmentDraft,
        policy_evidence: list[PolicyEvidence] | None = None,
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
        )
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO cases (case_id, filename, extracted_json, assessment_json, status, created_at, updated_at, policy_evidence_json, extraction_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    ),
                )
                connection.execute(
                    "INSERT INTO extraction_versions VALUES (?, ?, ?, ?, ?, ?)",
                    (case.case_id, 1, extracted.model_dump_json(), "system", "Initial model extraction", now.isoformat()),
                )
                self._record_event(connection, case.case_id, "case_created", "system", "Initial extraction and draft score")
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
        )

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
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status, extraction_version FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] not in (CaseStatus.draft.value, CaseStatus.analyst_review.value):
                    raise ValueError("Only draft cases can be edited")
                version = row["extraction_version"] + 1
                evidence_json = json.dumps([item.model_dump() for item in (policy_evidence or [])])
                connection.execute("UPDATE cases SET extracted_json = ?, assessment_json = ?, policy_evidence_json = ?, extraction_version = ?, status = ?, updated_at = ? WHERE case_id = ?", (extracted.model_dump_json(), assessment.model_dump_json(), evidence_json, version, CaseStatus.analyst_review.value, now.isoformat(), case_id))
                connection.execute("INSERT INTO extraction_versions VALUES (?, ?, ?, ?, ?, ?)", (case_id, version, extracted.model_dump_json(), actor, rationale, now.isoformat()))
                self._record_event(connection, case_id, "extraction_edited", actor, rationale)
        return self.get_case(case_id)

    def submit_committee(self, case_id: str, actor: str, rationale: str) -> CaseRecord:
        return self._transition(case_id, CaseStatus.analyst_finalized, CaseStatus.committee_review, actor, rationale)

    def decide_committee(self, case_id: str, review: CommitteeReview) -> CaseRecord:
        rationale = review.rationale
        if review.conditions:
            rationale = f"{rationale} Conditions: {review.conditions}"
        return self._transition(case_id, CaseStatus.committee_review, CaseStatus.decisioned, review.actor, f"{review.decision.value}: {rationale}")

    def cast_committee_vote(self, case_id: str, review: CommitteeReview) -> CaseRecord:
        if review.decision == CommitteeDecision.defer:
            raise ValueError("Committee voting accepts approve, reject, or approve with conditions")
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute("SELECT status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] != CaseStatus.committee_review.value:
                    raise ValueError("Case must be committee_review before committee voting")
                existing = connection.execute(
                    "SELECT 1 FROM committee_votes WHERE case_id = ? AND actor = ?",
                    (case_id, review.actor),
                ).fetchone()
                if existing is not None:
                    raise ValueError("Committee member has already voted on this case")
                connection.execute(
                    "INSERT INTO committee_votes VALUES (?, ?, ?, ?, ?, ?)",
                    (case_id, review.actor, review.decision.value, review.rationale, review.conditions, now.isoformat()),
                )
                vote_rationale = review.rationale
                if review.conditions:
                    vote_rationale = f"{vote_rationale} Conditions: {review.conditions}"
                self._record_event(connection, case_id, "committee_vote", review.actor, f"{review.decision.value}: {vote_rationale}")

                votes = connection.execute(
                    "SELECT decision, rationale, conditions FROM committee_votes WHERE case_id = ? ORDER BY occurred_at",
                    (case_id,),
                ).fetchall()
                approvals = sum(1 for vote in votes if vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value))
                rejections = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.reject.value)
                counted_votes = approvals + rejections
                if counted_votes >= 3:
                    if approvals >= 2:
                        final_decision = CommitteeDecision.approve_with_conditions.value if any(vote["decision"] == CommitteeDecision.approve_with_conditions.value or vote["conditions"] for vote in votes) else CommitteeDecision.approve.value
                    else:
                        final_decision = CommitteeDecision.reject.value
                    connection.execute(
                        "UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?",
                        (CaseStatus.decisioned.value, now.isoformat(), case_id),
                    )
                    self._record_event(connection, case_id, CaseStatus.decisioned.value, "committee", f"{final_decision}: Vote result {approvals} approvals, {rejections} rejections")
        return self.get_case(case_id)

    def list_committee_votes(self, case_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT actor, decision, rationale, conditions, occurred_at FROM committee_votes WHERE case_id = ? ORDER BY occurred_at",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def committee_vote_summary(self, case_id: str) -> dict:
        votes = self.list_committee_votes(case_id)
        approvals = sum(1 for vote in votes if vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value))
        rejections = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.reject.value)
        return {
            "approvals": approvals,
            "rejections": rejections,
            "votes_cast": approvals + rejections,
            "votes_needed": 3,
            "result": "Approved" if approvals >= 2 and approvals + rejections >= 3 else "Rejected" if rejections >= 2 and approvals + rejections >= 3 else "Pending",
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
