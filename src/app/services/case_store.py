import hashlib
import json
import os
import sqlite3
import statistics
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.app.models.governance import GovernanceRules, load_governance_rules
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

    def __init__(
        self,
        database_path: str = "risk_workbench.db",
        source_document_dir: str | None = None,
        governance_rules: GovernanceRules | None = None,
    ):
        self.database_path = database_path
        self.source_document_dir = Path(
            source_document_dir
            if source_document_dir is not None
            else (Path(database_path).with_suffix(".documents") if database_path != ":memory:" else "source_documents")
        )
        self.governance_rules = governance_rules or load_governance_rules()
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _canonical_event_payload(event: dict) -> bytes:
        payload = {
            "event_id": event["event_id"],
            "case_id": event["case_id"],
            "event_type": event["event_type"],
            "actor": event["actor"],
            "rationale": event["rationale"],
            "occurred_at": event["occurred_at"],
            "stage": event["stage"],
            "metadata_json": event["metadata_json"],
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    @classmethod
    def _event_digest(cls, previous_hash: str, event: dict) -> str:
        return hashlib.sha256(previous_hash.encode("ascii") + cls._canonical_event_payload(event)).hexdigest()

    @staticmethod
    def _source_pages_digest(source_pages: list[str]) -> str:
        canonical = json.dumps(source_pages, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

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
                        stage TEXT NOT NULL DEFAULT 'legacy',
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        prev_hash TEXT NOT NULL DEFAULT '',
                        event_hash TEXT,
                        FOREIGN KEY(case_id) REFERENCES cases(case_id)
                    );
                    CREATE TABLE IF NOT EXISTS source_documents (
                        case_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        storage_key TEXT NOT NULL,
                        sha256 TEXT NOT NULL,
                        byte_length INTEGER NOT NULL,
                        uploaded_at TEXT NOT NULL,
                        FOREIGN KEY(case_id) REFERENCES cases(case_id)
                    );
                    CREATE TABLE IF NOT EXISTS source_pages (
                        case_id TEXT NOT NULL,
                        page_number INTEGER NOT NULL,
                        page_text TEXT NOT NULL,
                        PRIMARY KEY(case_id, page_number),
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
                    ("source_sha256", "TEXT"),
                    ("ruleset_version", "TEXT NOT NULL DEFAULT 'legacy-unversioned'"),
                    ("ruleset_sha256", "TEXT NOT NULL DEFAULT ''"),
                    ("ruleset_snapshot_json", "TEXT NOT NULL DEFAULT '{}'"),
                ):
                    if name not in columns:
                        connection.execute(f"ALTER TABLE cases ADD COLUMN {name} {definition}")
                event_columns = {row[1] for row in connection.execute("PRAGMA table_info(workflow_events)")}
                for name, definition in (
                    ("stage", "TEXT NOT NULL DEFAULT 'legacy'"),
                    ("metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
                    ("prev_hash", "TEXT NOT NULL DEFAULT ''"),
                    ("event_hash", "TEXT"),
                ):
                    if name not in event_columns:
                        connection.execute(f"ALTER TABLE workflow_events ADD COLUMN {name} {definition}")
                vote_columns = {row[1] for row in connection.execute("PRAGMA table_info(committee_votes)")}
                if "conditions_owner" not in vote_columns:
                    connection.execute("ALTER TABLE committee_votes ADD COLUMN conditions_owner TEXT NOT NULL DEFAULT ''")
                if "conditions_due_date" not in vote_columns:
                    connection.execute("ALTER TABLE committee_votes ADD COLUMN conditions_due_date TEXT")
                self._backfill_event_hashes(connection)

    def _backfill_event_hashes(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT event_id, case_id, event_type, actor, rationale, occurred_at, stage, metadata_json, prev_hash, event_hash "
            "FROM workflow_events WHERE event_hash IS NULL ORDER BY case_id, event_id"
        ).fetchall()
        previous_by_case: dict[str, str] = {}
        for row in rows:
            case_id = row["case_id"]
            if case_id not in previous_by_case:
                last = connection.execute(
                    "SELECT event_hash FROM workflow_events WHERE case_id = ? AND event_hash IS NOT NULL AND event_id < ? ORDER BY event_id DESC LIMIT 1",
                    (case_id, row["event_id"]),
                ).fetchone()
                previous_by_case[case_id] = last["event_hash"] if last else ""
            previous_hash = previous_by_case[case_id]
            event = dict(row)
            event["prev_hash"] = previous_hash
            digest = self._event_digest(previous_hash, event)
            connection.execute(
                "UPDATE workflow_events SET prev_hash = ?, event_hash = ? WHERE event_id = ?",
                (previous_hash, digest, row["event_id"]),
            )
            previous_by_case[case_id] = digest

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
        source_document_bytes: bytes | None = None,
        source_pages: list[str] | None = None,
    ) -> CaseRecord:
        now = datetime.now(timezone.utc)
        source_sha256 = hashlib.sha256(source_document_bytes).hexdigest() if source_document_bytes is not None else None
        rules_snapshot = assessment.ruleset_snapshot
        ruleset_version = assessment.ruleset_version
        ruleset_sha256 = assessment.ruleset_sha256
        storage_key = f"{uuid4().hex}.pdf" if source_document_bytes is not None else None
        stored_path = self.source_document_dir / storage_key if storage_key else None
        temporary_path = stored_path.with_suffix(".tmp") if stored_path is not None else None
        if stored_path is not None:
            self.source_document_dir.mkdir(parents=True, exist_ok=True)
            assert temporary_path is not None
            temporary_path.write_bytes(source_document_bytes)
            os.replace(temporary_path, stored_path)
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
            source_sha256=source_sha256,
            ruleset_version=ruleset_version,
            ruleset_sha256=ruleset_sha256,
            ruleset_snapshot=rules_snapshot,
        )
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        "INSERT INTO cases (case_id, filename, extracted_json, assessment_json, status, created_at, updated_at, policy_evidence_json, extraction_version, submitted_by, assigned_to, parent_case_id, source_sha256, ruleset_version, ruleset_sha256, ruleset_snapshot_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            case.case_id,
                            case.filename,
                            extracted.model_dump_json(),
                            assessment.model_dump_json(),
                            case.status.value,
                            now.isoformat(),
                            now.isoformat(),
                            json.dumps([item.model_dump(mode="json") for item in case.policy_evidence]),
                            case.extraction_version,
                            case.submitted_by,
                            case.assigned_to,
                            case.parent_case_id,
                            source_sha256,
                            ruleset_version,
                            ruleset_sha256,
                            json.dumps(rules_snapshot, sort_keys=True),
                        ),
                    )
                    connection.execute(
                        "INSERT INTO extraction_versions VALUES (?, ?, ?, ?, ?, ?)",
                        (case.case_id, 1, extracted.model_dump_json(), initial_actor, initial_rationale, now.isoformat()),
                    )
                    if stored_path is not None and storage_key is not None and source_document_bytes is not None:
                        connection.execute(
                            "INSERT INTO source_documents (case_id, filename, storage_key, sha256, byte_length, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (case.case_id, filename, storage_key, source_sha256, len(source_document_bytes), now.isoformat()),
                        )
                    if source_pages:
                        connection.executemany(
                            "INSERT INTO source_pages (case_id, page_number, page_text) VALUES (?, ?, ?)",
                            [(case.case_id, number, text) for number, text in enumerate(source_pages, start=1)],
                        )
                    self._record_event(
                        connection,
                        case.case_id,
                        "case_created",
                        event_actor,
                        event_rationale,
                        metadata={
                            "source_sha256": source_sha256,
                            "source_pages_sha256": self._source_pages_digest(source_pages) if source_pages is not None else None,
                            "ruleset_version": ruleset_version,
                            "ruleset_sha256": ruleset_sha256,
                            "extracted_sha256": hashlib.sha256(extracted.model_dump_json().encode("utf-8")).hexdigest(),
                            "assessment_sha256": hashlib.sha256(assessment.model_dump_json().encode("utf-8")).hexdigest(),
                        },
                    )
        except Exception:
            if stored_path is not None:
                stored_path.unlink(missing_ok=True)
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
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
            source_sha256=row["source_sha256"],
            ruleset_version=row["ruleset_version"],
            ruleset_sha256=row["ruleset_sha256"],
            ruleset_snapshot=json.loads(row["ruleset_snapshot_json"]),
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
        source_document = self.get_source_document(case_id)
        source_bytes = self.read_source_document(case_id)[1] if source_document else None
        source_pages = self.list_source_pages(case_id) if source_document else []
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
            source_document_bytes=source_bytes,
            source_pages=[page["page_text"] for page in source_pages],
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
                connection.execute(
                    "UPDATE cases SET extracted_json = ?, assessment_json = ?, policy_evidence_json = ?, extraction_version = ?, "
                    "ruleset_version = ?, ruleset_sha256 = ?, ruleset_snapshot_json = ?, updated_at = ? WHERE case_id = ?",
                    (
                        extracted.model_dump_json(),
                        assessment.model_dump_json(),
                        evidence_json,
                        version,
                        assessment.ruleset_version,
                        assessment.ruleset_sha256,
                        json.dumps(assessment.ruleset_snapshot, sort_keys=True),
                        now.isoformat(),
                        case_id,
                    ),
                )
                connection.execute("INSERT INTO extraction_versions VALUES (?, ?, ?, ?, ?, ?)", (case_id, version, extracted.model_dump_json(), actor, rationale, now.isoformat()))
                self._record_event(
                    connection,
                    case_id,
                    "extraction_edited",
                    actor,
                    rationale,
                    metadata={
                        "extraction_version": version,
                        "extracted_sha256": hashlib.sha256(extracted.model_dump_json().encode("utf-8")).hexdigest(),
                        "assessment_sha256": hashlib.sha256(assessment.model_dump_json().encode("utf-8")).hexdigest(),
                        "ruleset_version": assessment.ruleset_version,
                        "ruleset_sha256": assessment.ruleset_sha256,
                    },
                )
        return self.get_case(case_id)

    def submit_committee(self, case_id: str, actor: str, rationale: str) -> CaseRecord:
        return self._transition(case_id, CaseStatus.analyst_finalized, CaseStatus.committee_review, actor, rationale)

    def decide_committee(self, case_id: str, review: CommitteeReview) -> CaseRecord:
        raise ValueError("Direct committee decisions are disabled; record the required distinct member votes.")

    def cast_committee_vote(self, case_id: str, review: CommitteeReview) -> CaseRecord:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute(
                    "SELECT status, submitted_by, ruleset_snapshot_json FROM cases WHERE case_id = ?",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(case_id)
                if row["status"] != CaseStatus.committee_review.value:
                    raise ValueError("Case must be committee_review before committee voting")
                rules = self._workflow_rules(row["ruleset_snapshot_json"])
                workflow_rules = rules.workflow
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
                self._record_event(
                    connection,
                    case_id,
                    "committee_vote",
                    review.actor,
                    f"{review.decision.value}: {vote_rationale}",
                    metadata={
                        "decision": review.decision.value,
                        "conditions": review.conditions,
                        "conditions_owner": review.conditions_owner,
                        "conditions_due_date": review.conditions_due_date.isoformat() if review.conditions_due_date else None,
                        "ruleset_version": rules.version,
                    },
                )

                votes = connection.execute(
                    "SELECT decision, rationale, conditions, conditions_owner, conditions_due_date FROM committee_votes WHERE case_id = ? ORDER BY occurred_at",
                    (case_id,),
                ).fetchall()
                approvals = sum(1 for vote in votes if vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value))
                rejections = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.reject.value)
                deferred = sum(1 for vote in votes if vote["decision"] == CommitteeDecision.defer.value)
                if len(votes) >= workflow_rules.committee_votes_required:
                    if approvals >= workflow_rules.committee_majority_required:
                        final_decision = CommitteeDecision.approve_with_conditions.value if any(
                            vote["decision"] in (CommitteeDecision.approve.value, CommitteeDecision.approve_with_conditions.value)
                            and (vote["decision"] == CommitteeDecision.approve_with_conditions.value or vote["conditions"])
                            for vote in votes
                        ) else CommitteeDecision.approve.value
                    elif rejections >= workflow_rules.committee_majority_required:
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
                    self._record_event(
                        connection,
                        case_id,
                        CaseStatus.decisioned.value,
                        "committee",
                        f"{final_decision}: Vote result {approvals} approvals, {rejections} rejections, {deferred} deferrals",
                        metadata={
                            "decision": final_decision,
                            "approvals": approvals,
                            "rejections": rejections,
                            "deferred": deferred,
                            "ruleset_version": rules.version,
                        },
                    )
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
                self._record_event(
                    connection,
                    case_id,
                    "condition_completed",
                    actor,
                    evidence,
                    metadata={"condition_id": condition_id},
                )
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
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        rules = GovernanceRules.model_validate(case.ruleset_snapshot) if case.ruleset_snapshot else self.governance_rules
        votes_needed = rules.workflow.committee_votes_required
        majority_needed = rules.workflow.committee_majority_required
        if votes_cast < votes_needed:
            result = "Pending"
        elif approvals >= majority_needed:
            result = "Approved"
        elif rejections >= majority_needed:
            result = "Rejected"
        else:
            result = "Deferred"
        return {
            "approvals": approvals,
            "rejections": rejections,
            "deferred": deferred,
            "votes_cast": votes_cast,
            "votes_needed": votes_needed,
            "majority_needed": majority_needed,
            "result": result,
            "votes": votes,
        }

    def _workflow_rules(self, snapshot_json: str) -> GovernanceRules:
        snapshot = json.loads(snapshot_json) if snapshot_json else {}
        return GovernanceRules.model_validate(snapshot) if snapshot else self.governance_rules

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
                "SELECT event_id, event_type, actor, rationale, occurred_at, stage, metadata_json, prev_hash, event_hash "
                "FROM workflow_events WHERE case_id = ? ORDER BY event_id",
                (case_id,),
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["metadata"] = json.loads(event.pop("metadata_json"))
            events.append(event)
        return events

    def get_source_document(self, case_id: str) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT filename, storage_key, sha256, byte_length, uploaded_at "
                "FROM source_documents WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return dict(row) if row else None

    def read_source_document(self, case_id: str) -> tuple[dict, bytes]:
        document = self.get_source_document(case_id)
        if document is None:
            raise KeyError(case_id)
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        if case.source_sha256 != document["sha256"]:
            raise ValueError("Source document hash does not match the case record")
        storage_key = Path(document["storage_key"])
        if storage_key.name != document["storage_key"]:
            raise ValueError("Invalid source document storage key")
        path = self.source_document_dir / storage_key
        content = path.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != document["sha256"]:
            raise ValueError("Source document integrity verification failed")
        return document, content

    def list_source_pages(self, case_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT page_number, page_text FROM source_pages WHERE case_id = ? ORDER BY page_number",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def verify_audit_chain(self, case_id: str) -> dict:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT event_id, case_id, event_type, actor, rationale, occurred_at, stage, metadata_json, prev_hash, event_hash "
                "FROM workflow_events WHERE case_id = ? ORDER BY event_id",
                (case_id,),
            ).fetchall()
        if not rows:
            return {
                "valid": False,
                "events_checked": 0,
                "first_invalid_event_id": None,
                "chain_head": "",
                "error": "No workflow events are recorded for this case.",
            }
        previous_hash = ""
        for row in rows:
            event = dict(row)
            if event["prev_hash"] != previous_hash:
                return {
                    "valid": False,
                    "events_checked": len(rows),
                    "first_invalid_event_id": event["event_id"],
                    "chain_head": previous_hash,
                }
            expected_hash = self._event_digest(previous_hash, event)
            if event["event_hash"] != expected_hash:
                return {
                    "valid": False,
                    "events_checked": len(rows),
                    "first_invalid_event_id": event["event_id"],
                    "chain_head": previous_hash,
                }
            previous_hash = expected_hash
        creation_event = next(
            (dict(row) for row in rows if row["event_type"] == "case_created"),
            None,
        )
        if creation_event is not None:
            creation_metadata = json.loads(creation_event["metadata_json"])
            expected_pages_hash = creation_metadata.get("source_pages_sha256")
            if expected_pages_hash is not None:
                actual_pages_hash = self._source_pages_digest(
                    [page["page_text"] for page in self.list_source_pages(case_id)]
                )
                if actual_pages_hash != expected_pages_hash:
                    return {
                        "valid": False,
                        "events_checked": len(rows),
                        "first_invalid_event_id": creation_event["event_id"],
                        "chain_head": previous_hash,
                    }
            expected_source_hash = creation_metadata.get("source_sha256")
            if expected_source_hash is not None:
                try:
                    document, content = self.read_source_document(case_id)
                except (KeyError, OSError, ValueError):
                    return {
                        "valid": False,
                        "events_checked": len(rows),
                        "first_invalid_event_id": creation_event["event_id"],
                        "chain_head": previous_hash,
                    }
                if (
                    document["sha256"] != expected_source_hash
                    or hashlib.sha256(content).hexdigest() != expected_source_hash
                ):
                    return {
                        "valid": False,
                        "events_checked": len(rows),
                        "first_invalid_event_id": creation_event["event_id"],
                        "chain_head": previous_hash,
                    }
        return {
            "valid": True,
            "events_checked": len(rows),
            "first_invalid_event_id": None,
            "chain_head": previous_hash,
        }

    def cycle_time_metrics(self, case_id: str, now: datetime | None = None) -> dict:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        rules = GovernanceRules.model_validate(case.ruleset_snapshot) if case.ruleset_snapshot else self.governance_rules
        events = self.list_events(case_id)
        start_index = next(
            (index for index, event in enumerate(events) if event["stage"] == CaseStatus.analyst_review.value),
            None,
        )
        if start_index is None:
            return {
                "case_id": case_id,
                "status": "not_submitted",
                "submitted_at": None,
                "decision_ready_at": None,
                "decided_at": None,
                "total_elapsed_hours": None,
                "active_elapsed_hours": None,
                "end_to_end_sla_hours": rules.workflow.end_to_end_sla_hours,
                "stage_sla_hours": rules.workflow.stage_sla_hours,
                "sla_met": None,
                "stage_hours": {},
                "breached_stages": [],
            }

        timed_events = events[start_index:]
        start_at = datetime.fromisoformat(timed_events[0]["occurred_at"])
        is_high_risk = case.assessment.requires_committee_review
        decision_ready_at = None
        decided_at = None
        stage_hours: dict[str, float] = {}
        end_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        final_stages = {CaseStatus.decisioned.value, CaseStatus.conditions_pending.value, CaseStatus.closed.value}

        for index, event in enumerate(timed_events):
            event_at = datetime.fromisoformat(event["occurred_at"]).astimezone(timezone.utc)
            stage = event["stage"]
            if decision_ready_at is None and stage in (
                CaseStatus.committee_review.value,
                CaseStatus.analyst_finalized.value,
                CaseStatus.analyst_rejected.value,
            ):
                decision_ready_at = event_at
            low_risk_analyst_decision = (
                stage == CaseStatus.analyst_finalized.value and not is_high_risk
            )
            if stage == CaseStatus.analyst_rejected.value or stage in final_stages or low_risk_analyst_decision:
                decided_at = event_at
                end_at = event_at
                timed_events = timed_events[: index + 1]
                break

        for index, event in enumerate(timed_events):
            event_at = datetime.fromisoformat(event["occurred_at"]).astimezone(timezone.utc)
            next_at = (
                datetime.fromisoformat(timed_events[index + 1]["occurred_at"]).astimezone(timezone.utc)
                if index + 1 < len(timed_events)
                else end_at
            )
            seconds = max(0.0, (next_at - event_at).total_seconds())
            stage_hours[event["stage"]] = stage_hours.get(event["stage"], 0.0) + seconds / 3600

        total_hours = max(0.0, (end_at - start_at).total_seconds() / 3600)
        active_hours = sum(hours for stage, hours in stage_hours.items() if stage != CaseStatus.needs_information.value)
        target = rules.workflow.end_to_end_sla_hours
        completed = decided_at is not None
        stage_targets = rules.workflow.stage_sla_hours
        breached_stages = sorted(
            stage for stage, hours in stage_hours.items()
            if stage in stage_targets and hours > stage_targets[stage]
        )
        return {
            "case_id": case_id,
            "status": "complete" if completed else "in_progress",
            "submitted_at": start_at.isoformat(),
            "decision_ready_at": decision_ready_at.isoformat() if decision_ready_at else None,
            "decided_at": decided_at.isoformat() if decided_at else None,
            "total_elapsed_hours": round(total_hours, 2),
            "active_elapsed_hours": round(active_hours, 2),
            "decision_ready_hours": round((decision_ready_at - start_at).total_seconds() / 3600, 2) if decision_ready_at else None,
            "end_to_end_sla_hours": target,
            "stage_sla_hours": stage_targets,
            "sla_met": total_hours <= target if completed else None,
            "stage_hours": {stage: round(hours, 2) for stage, hours in stage_hours.items()},
            "breached_stages": breached_stages,
        }

    def cycle_time_report(self) -> dict:
        cases = self.list_cases()
        metrics = [self.cycle_time_metrics(case.case_id) for case in cases]
        submitted = [item for item in metrics if item["submitted_at"]]
        completed = [item for item in submitted if item["sla_met"] is not None]
        elapsed = [item["total_elapsed_hours"] for item in completed]
        decision_ready_elapsed = [
            item["decision_ready_hours"]
            for item in submitted
            if item["decision_ready_hours"] is not None
        ]
        return {
            "target_hours": self.governance_rules.workflow.end_to_end_sla_hours,
            "submitted_cases": len(submitted),
            "completed_cases": len(completed),
            "sla_met_cases": sum(1 for item in completed if item["sla_met"]),
            "sla_attainment_percent": round(
                100 * sum(1 for item in completed if item["sla_met"]) / len(completed), 1
            ) if completed else None,
            "median_decision_hours": statistics.median(elapsed) if elapsed else None,
            "median_decision_ready_hours": statistics.median(decision_ready_elapsed) if decision_ready_elapsed else None,
            "cases": metrics,
        }

    @classmethod
    def _record_event(
        cls,
        connection: sqlite3.Connection,
        case_id: str,
        event_type: str,
        actor: str,
        rationale: str,
        metadata: dict | None = None,
    ):
        case_row = connection.execute("SELECT status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if case_row is None:
            raise KeyError(case_id)
        occurred_at = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        previous = connection.execute(
            "SELECT event_hash FROM workflow_events WHERE case_id = ? ORDER BY event_id DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else ""
        cursor = connection.execute(
            "INSERT INTO workflow_events (case_id, event_type, actor, rationale, occurred_at, stage, metadata_json, prev_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (case_id, event_type, actor, rationale, occurred_at, case_row["status"], metadata_json, previous_hash),
        )
        event = {
            "event_id": cursor.lastrowid,
            "case_id": case_id,
            "event_type": event_type,
            "actor": actor,
            "rationale": rationale,
            "occurred_at": occurred_at,
            "stage": case_row["status"],
            "metadata_json": metadata_json,
        }
        digest = cls._event_digest(previous_hash, event)
        connection.execute("UPDATE workflow_events SET event_hash = ? WHERE event_id = ?", (digest, cursor.lastrowid))
