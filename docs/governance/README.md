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

High and critical cases are flagged for committee review. Committee decision
endpoints and role-based authorization remain the next implementation
increment. No automated approval or rejection is permitted.

### Audit requirement

Case creation and analyst actions are written as timestamped workflow events.
Production must make the event log append-only at the database permission
layer and include authenticated identity.

This is where human-in-the-loop review gates and their rationale live —
15% of the rubric, scored on "what risk is this gate controlling, and why
is it placed here?"

The current scaffold has one gate already implicit: the extraction result
is rendered as an editable review, not applied automatically. Document it
here properly, plus the gates you add as the workflow grows (analyst
finalization, committee vote, override/dissent handling).

Suggested structure: one entry per gate —
- What it checks
- What risk it mitigates
- What happens on override/disagreement (the brief requires this to be
  handled, not blocked)
