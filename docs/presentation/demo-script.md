# Live Demo Script

## Preparation

- Start the application with `uvicorn src.app.main:app --reload --port 8000`.
- Open `http://localhost:8000`.
- Use `evals/data/sample_change_request.pdf`.
- Confirm `OPENAI_API_KEY` is configured.
- Keep the synthetic JSON fixture open as a comparison reference.

## Walkthrough

1. **Intake:** explain that the product owner submits a change request as a PDF.
2. **Extraction:** upload the sample PDF and point out that the model maps the document into the Pydantic fields.
3. **Scoring:** show that category scores and the overall risk level come from deterministic Python rules, not an LLM decision.
4. **Traceability:** point out the case ID and the draft status.
5. **Human gate:** enter `synthetic-analyst` and a short rationale, then accept or reject the draft.
6. **Auditability:** explain that the action is persisted with actor, rationale, and UTC timestamp.
7. **Safety:** explain that the document is treated as untrusted data and that the system never auto-approves or auto-rejects.

## Fallback demonstration

If the live model call is unavailable:

- Run the deterministic synthetic contract validation.
- Show `evals/data/synthetic_cases.json` and `tests/test_synthetic_cases.py`.
- Run the direct case-store workflow check or the focused pytest test once pytest is installed.
- Explain that the UI integration depends on the configured model provider, while scoring and persistence are locally testable.

## Questions to expect

**Why use AI here?**

PDF submissions are unstructured and vary by author. Extraction and drafting benefit from language understanding; scoring and state transitions need reproducibility.

**What prevents the model from approving a case?**

The model only returns the extraction schema. Workflow decisions require a human review endpoint, and the scoring path is deterministic.

**Is this production-ready?**

It is a credible synthetic-data vertical slice. Production still requires authentication, Postgres migrations, policy citations, residual-risk controls, committee voting, retries, and measured observability.

**How do you know the model is good?**

The repository contains hand-labeled synthetic cases and deterministic contract tests. The next evaluation run measures field-level live extraction accuracy and feeds failures back into the prompt.
