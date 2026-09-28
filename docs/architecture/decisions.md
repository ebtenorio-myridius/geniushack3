# Decision Log

## Structured extraction

**Decision:** use OpenAI structured outputs with the Pydantic
`ExtractedChangeRequest` contract.

**Reason:** reject malformed or schema-incompatible output at the model
boundary instead of passing loosely parsed text into scoring and workflow
code.

**Trade-off:** extraction requires a configured OpenAI provider; unlike policy
retrieval, it has no deterministic offline fallback. Source text is truncated
to a 12,000-character bound and source-page citations are not retained.

## Deterministic scoring

**Decision:** calculate category scores, weighted overall score, risk level,
and escalation flag in deterministic Python.

**Reason:** the calculation is reproducible and testable; the LLM is used to
structure submitted text, not choose a risk rating or human outcome.

**Trade-off:** category weights and rules are prototype values, not approved
supervisory mappings. Controls and residual risk are not represented.

## Human decision gate

**Decision:** persist a draft case before review; analyst review and committee
votes require rationales and create workflow records. Analyst edits create new
extraction versions rather than discarding the prior extraction.

**Reason:** preserve the review sequence and make the prototype workflow
inspectable.

**Boundary:** append-only describes current application behavior only. The
SQLite database does not enforce write-once event storage, and actor values
are not uniformly bound to verified identity. The inline analyst form uses a
fixed demo analyst header. This is not a production audit or authorization
control.

## SQLite for the demo

**Decision:** use local SQLite for case state, versions, workflow events,
committee votes, and telemetry.

**Reason:** it keeps the synthetic demo self-contained and supports durable
local state.

**Trade-off:** the service currently instantiates and uses `CaseStore`
directly; there is no separate persistence/repository interface. Moving to
Postgres will require a persistence adapter and migrations, even if the
Pydantic domain contracts remain stable. SQLite is not a production
concurrency, backup, or tamper-proof audit solution.

## Semantic policy retrieval with deterministic fallback

**Decision:** retrieve policy evidence semantically when the offline-built
`ai/policy_index.json` index and API key are available; otherwise use a
deterministic category-rule fallback.

**Reason:** at the current small corpus size, an in-memory cosine-similarity
scan is simple and testable without introducing a vector database. The
`PolicyEvidence` contract records the source path and whether evidence came
from semantic retrieval or fallback.

**Boundary:** the policy documents and index are synthetic demonstration
content. This is not approved supervisory guidance or production RAG. The
embedding request is synchronous in the async request path; a production
implementation should use an async client or thread executor. The fallback
keeps policy lookup available when the index, key, or provider is unavailable;
it does not make PDF extraction available offline.

## Demo identity and endpoint authorization

**Decision:** use a fixed demo username-to-role map and HTTP-only cookies for
the browser demo. The root and `/intake` page routes validate the username and
role pair; login and switch-role flows set or clear these cookies.

**Reason:** allow a repeatable hackathon walkthrough without implementing an
identity provider.

**Boundary:** this is not authentication suitable for production. Endpoint
checks are inconsistent: the PDF upload POST and `/intake/committee-queue/demo`
are not role-gated, the regular committee queue checks only the role string,
and actor handling is not uniformly tied to the signed-in principal. Do not
use real or sensitive data. Production requires real identity and consistent
authorization on every page and API endpoint.

## Committee voting rule

**Decision:** require three distinct committee usernames to cast approve,
reject, or approve-with-conditions votes. At least two approvals produce
approval; otherwise the result is rejection. The endpoint does not accept
defer.

**Reason:** demonstrate a multi-member review workflow and preserve each vote
and rationale in the case history.

**Boundary:** this is prototype logic, not an approved institutional decision
policy. Production governance must define quorum, conflicts, abstention,
deferral, tie handling, and decision authority explicitly.
