# Requirements Decisions

The original brief intentionally leaves decisions open. The following decisions make the prototype testable while preserving explicit future work.

| Question | Decision | Owner/gate | Consequence |
|---|---|---|---|
| What is automated? | PDF text extraction, schema-constrained drafting, deterministic scoring, persistence, policy lookup, escalation flagging, and event recording. | Engineering review | Humans remain responsible for finalization and decisions. |
| Where does AI lead? | Unstructured-document extraction, ambiguity surfacing, policy-context drafting, and evaluation-case generation. | FCRM review | Model output is always a draft. |
| Where does deterministic logic lead? | Score combination, thresholds, state transitions, role checks, and audit writes. | Engineering review | Results are reproducible and testable. |
| When is committee review required? | High and critical risk drafts are flagged; analyst submission is required before committee decision. | Analyst gate | A high-risk case cannot silently bypass committee review. |
| What is the policy source? | Synthetic policy documents are used for the demo. Published supervisory material must be mapped and approved before production. | FCRM owner | Demo evidence is not presented as regulatory advice. |
| What happens on disagreement? | Analyst edits create a new extraction version and require rationale; committee decisions record rationale and conditions. | Governance gate | Original model output remains reconstructable. |
| What data is allowed? | Synthetic data only, including generated PDFs and fictional organizations. | Submission gate | No real bank or customer systems are connected. |
| What is the free-first deployment? | Docker Compose, SQLite, local storage, and optional OpenAI inference; Ollama is a future provider adapter. | Release gate | Local infrastructure is free, but OpenAI calls may cost money. |
