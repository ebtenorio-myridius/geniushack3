# Governance

## Implemented gates

### Extraction review

The model prepares a structured draft. An analyst must verify fields against
the source before finalizing the assessment. The analyst records the rationale;
the committee, not the analyst, records the final case decision.

### Risk review

The score is deterministic and explainable, but remains a draft. The analyst
owns the final assessment and records disagreement rather than silently
changing history.

### Committee review

Every product-owner submission enters analyst review. The analyst verifies the
facts, finalizes the assessment, and submits it to committee; committee-role
users can view the queue and three distinct committee members must vote. Each
vote records approve, reject, defer, or approve-with-conditions plus rationale
and conditions. The case remains pending until three votes are recorded; two
approvals or rejections decide the result, and a full vote without either
majority is deferred. No automated approval or rejection is permitted.

### Audit requirement

Case creation, extraction edits, analyst actions, committee submission, votes,
conditions, and committee decisions are written as timestamped workflow events.
Events are linked by a per-case SHA-256 hash chain, and case views and local
exports verify the chain. This is local tamper-evidence only: an operator who
can alter the SQLite database can rewrite events and recompute the chain.
Production must add externally protected/WORM retention, independent chain
anchoring, database permission controls, and authenticated identity.

## Source evidence and provenance

Uploaded PDFs and page-level extracted text are retained locally. Each PDF is
stored with a SHA-256 digest; downloads and exports verify the bytes against the
recorded digest. Extracted non-empty fields require page-numbered verbatim
quotes that are checked against the retained page text. Analyst and product
owner corrections must cite exact source text for each changed field; the
previous citation is removed when its field changes. Scores expose their input
field names, and each assessment captures its scoring ruleset snapshot and
digest.

The analyst and committee workspaces can download a ZIP examiner-style export
containing case details, source PDF (when retained), source pages, citations,
rules snapshot, workflow events/votes/conditions, timing, audit verification,
and a SHA-256 manifest. This prototype package is not examiner-certified or
immutable. Demo-cookie identity is not independently verified. No regulated
retention period is configured or implied.

## Governed rules and cycle-time measurement

`config/governance_rules.json` is loaded at application startup. It contains
the scoring parameters, risk thresholds, committee quorum, and end-to-end and
stage targets. New cases record the exact rules snapshot and digest used;
rescores and committee voting use that snapshot. The checked-in rules are
explicitly marked `prototype`, owned by the Risk Function, and unapproved.
Changes to active rules require a restart. This file is a local prototype
configuration, not a production risk-function administration interface. The
quorum is bounded by the three committee identities supported by this demo;
unknown stage SLA names are rejected rather than silently left unmeasured.

The illustrative end-to-end target is 48 elapsed hours, with stage targets
also configured in the file. The analyst Cycle-time metrics view reports
recorded elapsed and active hours, completed-case attainment, and stage time.
Information-wait time is excluded from active hours but included in elapsed
hours. In-progress cases are not included in completed-case SLA attainment or
the median. These metrics do not establish that the target has been achieved;
baseline data, approved stage definitions/targets, and operational review are
required before claiming a two-day turnaround.

This is where human-in-the-loop review gates and their rationale live —
15% of the rubric, scored on "what risk is this gate controlling, and why
is it placed here?"

The demo implements extraction review, analyst editing/finalization, and a
configurable multi-member committee decision gate. Real identity,
conflict-of-interest handling, formal approval of the prototype rules, and
residual-risk controls remain production increments.

Suggested structure: one entry per gate —
- What it checks
- What risk it mitigates
- What happens on override/disagreement (the brief requires this to be
  handled, not blocked)
