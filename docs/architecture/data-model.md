# Data Model

## Case

Stores the case ID, source filename, extracted request, draft assessment, workflow status, and created/updated timestamps.

## Extraction and assessment

The extraction is a Pydantic contract versioned by the prompt/model configuration. The assessment records category scores, rationale, overall score, risk level, committee flag, and scoring method.

## Workflow event

Each event stores case ID, event type, actor, rationale, and UTC timestamp. Events are append-only so an analyst disagreement is preserved rather than overwritten.

## Planned extensions

Add source-page evidence, policy citations, control effectiveness, residual risk, committee votes, and rule-version identifiers before production use.
