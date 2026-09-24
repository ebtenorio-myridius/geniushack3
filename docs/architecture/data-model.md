# Data Model

## Case

Stores the case ID, source filename, extracted request, draft assessment, workflow status, and created/updated timestamps.

## Extraction and assessment

The extraction is a Pydantic contract versioned by the prompt/model configuration. The assessment records category scores, rationale, overall score, risk level, committee flag, and scoring method.

## Workflow event and committee vote

Each event stores case ID, event type, actor, rationale, and UTC timestamp. Events are append-only so an analyst disagreement is preserved rather than overwritten.

Committee votes store case ID, decision, actor, rationale, and UTC timestamp.
The case store prevents duplicate votes by actor and finalizes the case only
after three distinct committee members have voted. The displayed result uses
the committee vote summary; a production implementation should add explicit
tie/decision policy and database permission enforcement.

## Implemented extensions

The case store also persists policy evidence, extraction versions, workflow
events, and telemetry. Analyst edits create a new extraction version instead of
overwriting the model result.

## Production extensions

Add source-page evidence, control effectiveness, residual risk, rule-version
identifiers, and database-enforced append-only storage before production use.
