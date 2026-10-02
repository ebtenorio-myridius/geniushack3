# Expanded Specification

## Users

- Product owner: submits a synthetic change request and tracks its status.
- FCRM analyst: verifies extracted facts, reviews policy evidence, finalizes risk, and records disagreement.
- Risk committee: reviews cases submitted to the queue and casts a vote to approve, reject, defer, or approve with conditions. The demo uses three fixed committee identities.

## Workflow

`Submitted -> Extracted -> Analyst Review -> Analyst Finalized -> Committee Review -> Decisioned`

The happy path is implemented for valid uploads and successful extraction. A
successful extraction creates a durable case; invalid PDFs or failed provider
calls return errors and do not create a case. Analysts can edit/rescore and
finalize a case, then submit it to the committee queue. In the user-facing
committee route, three distinct demo usernames can vote once each: two
approvals approve, two rejections reject, and no majority defers the case.
The lower-level `CaseStore` still has a direct decision method used by a unit
test, so the three-vote invariant is not enforced for every internal caller.

Committee voting is implemented, but high/critical escalation is only flagged
for analyst action; the application does not require committee submission
before a high/critical case can remain finalized. This is an implementation
gap against the intended governance requirement, not a policy decision that
high-risk cases may bypass review.

## Acceptance criteria

- Every valid submission that completes extraction receives a durable case ID.
- The extraction is schema validated and remains a draft until analyst action.
- Analyst actions require an actor and rationale; demo actor values are not consistently bound to the signed-in identity.
- Workflow events are timestamped and inserted by application code. The database does not enforce append-only immutability.
- High and critical drafts are flagged for committee review. Mandatory escalation is not enforced in the current application.
- The user-facing committee route records the three-vote human majority outcome. A lower-level direct-decision helper remains available to internal callers; the quorum is not a store-wide invariant.
- Synthetic documents and data are the demo-use requirement. The upload endpoint does not technically detect or reject real data.

## Scope decisions

The demo covers synthetic PDF intake, structured extraction, deterministic
inherent-risk scoring, policy evidence retrieval, analyst review, and a
three-member committee vote. Synthetic-only use and mandatory high/critical
escalation remain requirements/operating constraints, but the current app does
not technically enforce either one. Production identity, residual-risk
calculation, source-document retention, and institutionally approved scoring
and committee rules are out of scope for the current implementation.

## Current implementation status

Implemented: schema-constrained extraction, deterministic weighted scoring,
policy evidence retrieval with a rule fallback, SQLite case/version/event
storage, telemetry, demo login, analyst review, and three-member committee
voting with deferral on no majority.

Partial or not enforced: mandatory escalation for high/critical cases,
store-wide enforcement of the three-vote quorum, consistent endpoint
authorization, synthetic-only intake, and database-level audit immutability.
Not implemented: real identity, control-effectiveness and residual-risk
scoring, source-document retention/citations, and an approved institutional
scoring or committee decision policy.
