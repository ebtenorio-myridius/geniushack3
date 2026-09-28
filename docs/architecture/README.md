# Architecture

This folder records the implemented system boundary and the decisions that keep
AI-assisted extraction separate from human-owned risk decisions.

- `overview.md` — system diagram, component responsibilities
- `data-model.md` — current SQLite persistence model and its limitations
- `decisions.md` — the decision log: what was chosen, alternatives
  considered, and why (e.g. "extraction is an LLM call, scoring is
  deterministic — see risk_scoring.py")

The current browser workflow is demo sign-in, PDF text extraction, structured
LLM extraction, deterministic scoring, policy evidence retrieval/fallback,
SQLite persistence, analyst review, and three-member committee voting. The
demo identity is not production authentication, and endpoint authorization is
not consistent: notably, the upload POST and browser-friendly demo committee
queue are not role-gated. Uploaded PDF bytes are not persisted. Production
extensions are called out separately in each file; do not describe the current
SQLite records as tamper-proof or institutionally governed evidence.
