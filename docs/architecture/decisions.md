# Decision Log

## Structured extraction

Use OpenAI structured outputs and Pydantic validation so malformed model output fails at the boundary.

## Deterministic scoring

Keep scoring in Python. The model can extract facts and draft explanations, but a committee needs reproducible scoring that can be challenged and tested.

## Human decision gate

Persist the extraction and draft assessment before review. Analyst accept/reject actions require a rationale and are recorded as append-only events.

## SQLite for the demo

SQLite provides durable local state with no new service dependency. The repository interface is isolated so the deployment target can move to Postgres.
