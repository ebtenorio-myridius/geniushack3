# Expanded Specification

## Users

- Product owner: submits a synthetic change request and tracks its status.
- FCRM analyst: verifies extracted facts, reviews policy evidence, finalizes risk, and records disagreement.
- Risk committee: reviews escalated assessments and records an approval, rejection, deferral, or conditional approval.

## Workflow

`Submitted -> Extracted -> Analyst Review -> Analyst Finalized -> Committee Review -> Decisioned`

The current implementation delivers `Submitted -> Extracted -> Analyst Review`, including a durable case record and analyst accept/reject event.

## Acceptance criteria

- Every submission receives a durable case ID.
- The extraction is schema validated and remains a draft until analyst action.
- Analyst actions require an actor and rationale.
- Workflow events are append-only and timestamped.
- High and critical drafts are flagged for committee review.
- No system action automatically approves or rejects a change.
- Only synthetic documents and data are used.

## Scope decisions

The first vertical slice prioritizes traceability and human control over broad feature coverage. Policy retrieval, committee voting, residual-risk controls, and role authentication are the next increments.
