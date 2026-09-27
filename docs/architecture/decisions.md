# Decision Log

## Structured extraction

Use OpenAI structured outputs and Pydantic validation so malformed model output fails at the boundary.

## Deterministic scoring

Keep scoring in Python. The model can extract facts and draft explanations, but a committee needs reproducible scoring that can be challenged and tested.

## Human decision gate

Persist the extraction and draft assessment before review. Analyst accept/reject actions require a rationale and are recorded as append-only events.

## SQLite for the demo

SQLite provides durable local state with no new service dependency. The repository interface is isolated so the deployment target can move to Postgres.

## Semantic policy retrieval over a category lookup table

The original implementation matched a change request to one of three
hardcoded policy snippets by category keyword. That's a lookup table, not
retrieval, and doesn't demonstrate the "modelled, governed data layer" the
brief asks for. Replaced with real retrieval: the synthetic policy docs in
/docs/policies are chunked and embedded offline (tools/embed_policies.py),
and a request is matched by cosine similarity against those chunks at
request time (src/app/services/policy_service.py). No vector database is
introduced at this corpus size — a plain in-memory similarity scan over a
few dozen short chunks is exact, fast, and simple to test. If the corpus
grows past what comfortably fits in memory, swap the scan for pgvector or
similar; the interface callers see doesn't change. A deterministic
category-keyword fallback is kept for when the index or API key isn't
available (CI, provider outage), so the app degrades instead of failing.
