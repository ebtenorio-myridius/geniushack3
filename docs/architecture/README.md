# Architecture

This folder records the implemented system boundary and the decisions that keep
AI-assisted extraction separate from human-owned risk decisions.

- `overview.md` — system diagram, component responsibilities
- `data-model.md` — the governed data layer the brief asks for
- `decisions.md` — the decision log: what was chosen, alternatives
  considered, and why (e.g. "extraction is an LLM call, scoring is
  deterministic — see risk_scoring.py")

The current workflow is PDF text extraction, structured LLM extraction,
deterministic scoring, SQLite persistence, analyst review, and three-member
committee voting. Production extensions are called out separately in each file.
