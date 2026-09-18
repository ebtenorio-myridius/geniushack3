# Risk Assessment Workbench — Starter Scaffold

FastAPI + Jinja2 + HTMX workbench for Genius Hacks 2026. The current vertical
slice is **upload a PDF -> extract text -> LLM drafts a structured change
request -> deterministic risk score -> persist case -> analyst review**.

## Stack

- **FastAPI** — backend, routing, async OpenAI calls
- **Jinja2** — server-rendered HTML templates
- **HTMX** — partial page updates without a JS framework (loaded via CDN in `base.html`)
- **OpenAI Python SDK** — structured outputs (`.parse()`) for the extraction step
- **pypdf** — PDF text extraction
- **pytest** — tests

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then add your OPENAI_API_KEY

uvicorn src.app.main:app --reload --port 8000
```

Open http://localhost:8000 — you'll land on the intake form. Upload a PDF
(synthetic only — see hackathon constraints), and the page will show the
extracted fields and a draft risk score without a full page reload.

For the free-first Docker deployment, see
[ops/free-first-deployment.md](ops/free-first-deployment.md). The local
containers are free to run; OpenAI model calls may incur API charges.

## Where things live (maps to the hackathon's required repo layout)

```
/src            application code (this scaffold)
/ai             prompts + agent/LLM config — see ai/prompts/extract_change_request.md
/docs           requirements, architecture, governance write-ups
/evals          synthetic eval definitions, fixtures, and results
/tests          automated tests
/ops            deployment, monitoring, token analysis notes
```

## Submission checklist

The required repository areas are present:

- `/src` - application code and workflow routes/services
- `/ai` - prompts and model/orchestration configuration
- `/docs/requirements` - expanded specification and framework research
- `/docs/architecture` - architecture, data model, and decision log
- `/docs/governance` - human review gates and audit rationale
- `/evals` - synthetic cases, PDF fixture, and evaluation guidance
- `/tests` - automated PDF, scoring, fixture, and workflow tests
- `/ops` - deployment, monitoring, and token-usage notes
- `/docs/presentation` - deck outline, demo script, and judging evidence matrix

The presentation pack is in [docs/presentation](docs/presentation). It reflects
the current implementation and identifies remaining production increments such
as real authentication, multi-member quorum, residual-risk controls, and
operational dashboards.

For end-user instructions, see the [user manual](docs/manual/user-manual.md).

For command-line startup and testing steps, see the
[implementation runbook](docs/implementations/run-app-and-test.md).

## Deliberate design choices worth defending in the presentation

- **Extraction is an LLM call. Scoring is not.** `services/risk_scoring.py` is
  plain deterministic Python. That's an explicit "engineering judgement" call —
  document why in `/docs/architecture`.
- **Structured outputs, not free text.** The LLM call in `services/llm_service.py`
  is constrained to a Pydantic schema, so a malformed or hallucinated field fails
  loudly instead of silently corrupting downstream data.
- **The extraction result is a review step, not an auto-decision.** Each case is
  persisted with a case ID. Analyst accept/reject actions require a rationale
  and are recorded as workflow events.

## Current limitations and next steps

The current demo implements analyst editing/rescoring, policy evidence lookup,
committee decisions, demo role headers, telemetry, and live evaluation. The
remaining production increments are:

1. Replace demo headers with real authentication and authorization.
2. Add controls, residual-risk scoring, and cited published supervisory mappings.
3. Replace SQLite with PostgreSQL and add migrations, object storage, and
  background extraction workers.
4. Add multi-member committee voting, quorum, dashboards, and alerting.
