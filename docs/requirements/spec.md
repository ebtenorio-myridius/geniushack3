# Expanded Specification

## Users

- Product owner: submits a synthetic change request and tracks its status.
- FCRM analyst: verifies extracted facts, reviews policy evidence, finalizes risk, and records disagreement.
- Risk committee: reviews cases submitted to the queue and casts a vote to approve, reject, defer, or approve with conditions. The demo uses three fixed committee identities.

## Workflow

```text
Upload -> Draft extraction and risk score
-> Product-owner submission
   -> Low/medium risk: Analyst review -> Analyst finalized -> Closed
   -> High/critical risk: Committee review -> Decisioned/conditions pending -> Closed
```

The happy path is implemented for valid uploads and successful extraction. A
successful extraction creates a durable draft; invalid PDFs or failed provider
calls return errors and do not create a case. On product-owner submission,
low/medium-risk cases enter analyst review, while high/critical-risk cases go
directly to committee review. Directly submitted high/critical cases have not
had analyst verification; committee members are prompted to verify the facts
and score. Analysts can also escalate a case to the committee after finalizing
it. An accepted low/medium analyst review is finalized but not closed
automatically; an analyst closes it separately. In the user-facing committee
route, three distinct demo usernames can vote once each: two approvals approve,
two rejections reject, and no majority defers the case. Approval with
conditions creates follow-up work owned by the product owner; all conditions
must be completed before an analyst can close the case. Committee outcomes
also require analyst closure. The lower-level `CaseStore` still has a direct
decision method used by a unit test, so the three-vote invariant is not
enforced for every internal caller.

## Acceptance criteria

- Every valid submission that completes extraction receives a durable case ID.
- The extraction is schema validated and remains a draft until product-owner submission.
- Analyst actions require an actor and rationale; demo actor values are not consistently bound to the signed-in identity.
- Workflow events are timestamped and inserted by application code. The database does not enforce append-only immutability.
- High and critical submissions are routed to the committee; low and medium submissions are routed to analysts.
- Analyst finalization and committee outcomes do not automatically close a case; closure is a separate analyst action. Product-owner evidence is required for committee approval conditions.
- The user-facing committee route records the three-vote human majority outcome. A lower-level direct-decision helper remains available to internal callers; the quorum is not a store-wide invariant.
- Synthetic documents and data are the demo-use requirement. The upload endpoint does not technically detect or reject real data.

## Scope decisions

The demo covers synthetic PDF intake, structured extraction, deterministic
inherent-risk scoring, policy evidence retrieval, risk-based analyst or
committee review, and a three-member committee vote. Synthetic-only use
remains an operating constraint but is not technically enforced. Production
identity, residual-risk calculation, source-document retention, and
institutionally approved scoring and committee rules are out of scope for the
current implementation.

## Current implementation status

Implemented: schema-constrained extraction, deterministic weighted scoring,
policy evidence retrieval with a rule fallback, SQLite case/version/event
storage, telemetry, demo login, analyst review, and three-member committee
voting with deferral on no majority.

Partial or not enforced: store-wide enforcement of the three-vote quorum,
consistent endpoint authorization, synthetic-only intake, and database-level
audit immutability.
Not implemented: real identity, control-effectiveness and residual-risk
scoring, source-document retention/citations, and an approved institutional
scoring or committee decision policy.
