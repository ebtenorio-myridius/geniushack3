# Live Demo Script

## Preparation

- Start the application with `uvicorn src.app.main:app --reload --port 8000`.
- Open `http://127.0.0.1:8000/`.
- Use `evals/data/sample_change_request.pdf`.
- Confirm `OPENAI_API_KEY` is configured.
- Keep the synthetic JSON fixture open as a comparison reference.
- The login form starts blank. Enter a supported username and explicitly select its matching role: `product-owner-1`, `analyst-1`, or `committee-1`, `committee-2`, `committee-3`.

## Walkthrough

1. **Sign in:** sign in as `product-owner-1` with the Product owner role. This is a fixed demo identity, not production authentication.
2. **Extraction:** upload the sample PDF and point out that the model maps the document into the Pydantic fields.
3. **Scoring:** show that category scores and the overall risk level come from deterministic Python rules, not an LLM decision.
4. **Traceability:** point out the case ID, draft status, policy evidence, extraction version, and workflow events.
5. **Human gate:** use Sign in / switch role, explicitly select FCRM analyst, enter `analyst-1`, and sign in. Review the case, edit if needed, enter a rationale, and finalize.
6. **Safety:** explain that the prompt treats document text as untrusted and that the system never auto-approves or auto-rejects.
7. **Committee:** submit a high/critical case, then switch among `committee-1`, `committee-2`, and `committee-3` to cast three distinct approve, reject, or approve-with-conditions votes. Two approvals approve; otherwise the result is rejected. The current endpoint does not accept defer.
8. **Auditability:** explain that actor, rationale, versions, and UTC events are persisted in SQLite. The event history is append-only through application behavior, not database-enforced immutability.

## Fallback demonstration

If the live extraction model call is unavailable:

- Do not imply extraction has an offline fallback; the upload flow depends on the configured model provider.
- Show the latest recorded live evaluation report and its caveat: eight synthetic cases, 67.5% field accuracy, and 100% risk-level agreement on that small set.
- Run the deterministic synthetic contract validation.
- Show `evals/data/synthetic_cases.json` and `tests/test_synthetic_cases.py`.
- Explain that deterministic scoring, persistence, and the pytest suite are locally testable; semantic policy retrieval can fall back to rules, but extraction cannot.

## Questions to expect

**Why use AI here?**

PDF submissions are unstructured and vary by author. Extraction and drafting benefit from language understanding; scoring and state transitions need reproducibility.

**What prevents the model from approving a case?**

The model only returns the extraction schema. Workflow decisions require a human review endpoint, and the scoring path is deterministic.

**Is this production-ready?**

It is a credible synthetic-data vertical slice. Production still requires real authentication, Postgres migrations, approved policy mappings, residual-risk controls, database-enforced audit immutability, retries, and measured observability.

**How do you know the model is good?**

The repository contains hand-labeled synthetic cases and deterministic contract tests. The latest recorded live run completed 8/8 calls with 67.5% field accuracy and 100% risk-level agreement. The sample is small and synthetic; field errors remain, and these figures are not a production accuracy estimate.
