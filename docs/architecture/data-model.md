# Data Model

The current Pydantic contracts are in `src/app/models/schemas.py`; SQLite
tables and serialization are implemented in
`src/app/services/case_store.py`. This is the prototype's persistence model,
not a database-enforced governance or immutability layer.

## Case Record

The `cases` table stores a generated case ID, source filename, current
structured extraction, draft risk assessment, workflow status, UTC creation
and update timestamps, serialized policy evidence, and the current extraction
version. The `CaseRecord` response model exposes these values to the app.
Uploaded PDF bytes and source text are not persisted, so the source document
cannot be retrieved from the case store.

## Extraction and Assessment

`ExtractedChangeRequest` contains the extracted fields and model-reported
confidence. `RiskAssessmentDraft` contains category scores and rationales,
weighted overall score, risk level, committee-review flag, and scoring-method
label. Analyst edits replace the current extraction/assessment values and
increment the version number; the prior extraction JSON is retained in
`extraction_versions`. Prompt/model configuration is not stored as a complete
per-case immutable snapshot.

The assessment has no control inventory, control effectiveness, residual-risk
calculation, approved rule-set version, or source-page/span citations.

## Workflow Events

`workflow_events` stores case ID, event type, actor string, rationale, and UTC
timestamp. Application paths insert events for case creation, analyst review,
edits, committee submission, votes, and finalization. The application does not
provide update/delete endpoints for event rows, but SQLite permissions,
triggers, or external write-once storage do not enforce immutability. Actor
strings in the database are not independently verified identities.

## Committee Votes

`committee_votes` stores case ID, actor, decision, rationale, optional
conditions, and UTC timestamp. Its primary key `(case_id, actor)` prevents the
same actor string from voting twice. The HTTP voting route validates the
committee demo cookie identity and uses that username as the actor. The case
store itself enforces only actor-string uniqueness, not the identity mapping.

The prototype endpoint accepts approve, reject, and approve-with-conditions;
it rejects defer. A case becomes decisioned after three votes, with at least
two approvals producing approval (conditional if a conditional vote or
conditions are present); otherwise it is rejected. This implementation is
not an institutionally approved decision policy.

## Telemetry and Policy Evidence

The `telemetry` table stores operation, model, prompt-version label, latency,
optional input/output token counts, success flag, optional error type, and UTC
timestamp. Policy evidence is serialized on the case and records its source
path, retrieval method, and optional semantic similarity score. Policy content
in this prototype is synthetic and is not approved supervisory guidance.

## Production Extensions

Before production use, add consistent endpoint authorization and real identity,
database migrations and a persistence adapter, protected source-document
storage with retention controls, source-page evidence, control effectiveness
and residual risk, immutable scoring/prompt/rule versions, approved policy and
decision rules, and database-enforced or external append-only audit storage.
