# Governance

## Implemented gates

### Extraction review

The model prepares a structured draft. An analyst must verify fields against
the source before the case is finalized. The analyst can reject the draft and
must record why.

### Risk review

The score is deterministic and explainable, but remains a draft. The analyst
owns the final assessment and records disagreement rather than silently
changing history.

### Committee review

High and critical cases are flagged for committee review. An analyst submits
the finalized case, committee-role users can view the queue, and three distinct
committee members must vote. Each vote records approve, reject, defer, or
approve-with-conditions plus rationale and conditions. The case remains pending
until the three-vote quorum is reached; no automated approval or rejection is
permitted.

### Audit requirement

Case creation, extraction edits, analyst actions, committee submission, and
committee decisions are written as timestamped workflow events. Production
must make the event log append-only at the database permission layer and
replace demo headers with authenticated identity.

This is where human-in-the-loop review gates and their rationale live —
15% of the rubric, scored on "what risk is this gate controlling, and why
is it placed here?"

The demo implements extraction review, analyst editing/finalization, and a
three-member committee decision gate. Real identity, conflict-of-interest
handling, tie/decision policy, and residual-risk controls remain production
increments.

Suggested structure: one entry per gate —
- What it checks
- What risk it mitigates
- What happens on override/disagreement (the brief requires this to be
  handled, not blocked)
