# Data Model

The current Pydantic contracts are in `src/app/models/schemas.py`; SQLite
tables and serialization are implemented in
`src/app/services/case_store.py`. This is the prototype's persistence model,
not a database-enforced governance or immutability layer.

## Case Record

The `cases` table stores a generated case ID, source filename, current
structured extraction, draft risk assessment, workflow status, UTC creation
and update timestamps, serialized policy evidence, and the current extraction
version. It also records the submitting product owner, assigned demo analyst,
optional parent case for reassessments, the stage to resume after an
information request, the current request/waiting role, and committee outcome
independently of lifecycle status. Product-owner submission moves a complete
draft into analyst review; reassessment creates a linked case and leaves the
earlier record intact. Uploaded PDF bytes and source text are not persisted,
so the source document cannot be retrieved from the case store.

## Extraction and Assessment

`ExtractedChangeRequest` contains the extracted fields and model-reported
confidence. `RiskAssessmentDraft` contains category scores and rationales,
weighted overall score, risk level, committee-review flag, and scoring-method
label. Analyst edits replace the current extraction/assessment values and
increment the version number; the prior extraction JSON is retained in
`extraction_versions` with editor and rationale. The case workspace compares
those snapshots to show changed fields. Prompt/model configuration is not
stored as a complete per-case immutable snapshot.

## Workflow and Conditions

Lifecycle states include draft, analyst review, needs information, analyst
finalized/rejected, committee review, decisioned, conditions pending, and
closed. Information requests store the workflow stage to resume and pause
committee requests until the submitting product owner responds. Committee
conditions are stored separately with owner, due date, completion evidence,
and completion actor/time. Open conditions block closure; overdue conditions
are flagged in the workspaces. Case queues show elapsed calendar days since
the last update, but no case-stage service-level targets are configured.

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
conditions, condition owner/due date, and UTC timestamp. Its primary key `(case_id, actor)` prevents the
same actor string from voting twice. The HTTP voting route validates the
committee demo cookie identity and uses that username as the actor. The case
store itself enforces only actor-string uniqueness, not the identity mapping.

The prototype endpoint accepts approve, reject, defer, and
approve-with-conditions. A case receives an outcome after three votes. At
least two approvals produce approval (with a conditions-pending lifecycle
state if an approving vote includes conditions); at least two rejections
produce rejection. If neither has a majority, the result is deferred. This
implementation is not an institutionally approved decision policy.

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
