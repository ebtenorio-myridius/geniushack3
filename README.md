# Risk Assessment Workbench

FastAPI + Jinja2 + HTMX workbench for Genius Hacks 2026. The synthetic-data
prototype demonstrates **demo sign-in -> PDF text extraction -> structured LLM
extraction -> explicit product-owner submission -> analyst review and
information requests -> three-member committee vote -> condition tracking,
closure, and linked reassessment**. It prepares evidence for human review; it
is not an automatic approval system or a production banking platform.

## Stack

- **FastAPI** — backend and routing; asynchronous OpenAI extraction call
- **Jinja2** — server-rendered HTML templates
- **HTMX** — partial page updates without a JS framework (loaded via CDN in `base.html`)
- **OpenAI Python SDK** — structured outputs (`.parse()`) for PDF extraction; the call can incur API charges
- **pypdf** — PDF text extraction
- **pytest** — tests

## Live demo

The app is currently running on Render at:

- https://risk-management-smtv.onrender.com/intake/login

This is a free-tier deployment, so the service may sleep after inactivity and the SQLite database resets on restart. The public instance is intended for demo use and should not be treated as a production system.

For the step-by-step Render setup, see [docs/deployment/Render_Free_Tier_Deployment_Guide.md](docs/deployment/Render_Free_Tier_Deployment_Guide.md). The required environment variables are `OPENAI_API_KEY`, `OPENAI_MODEL`, and `DATABASE_PATH=/tmp/risk_workbench.db`.

## Quick start

From the repository root in PowerShell, create an environment and install
application dependencies:

```powershell
py -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`). Do not
commit `.env`. PDF extraction requires a working OpenAI key and may incur
charges. If `ai/policy_index.json` is present, policy evidence retrieval can
use semantic matching; otherwise, and when semantic retrieval is unavailable,
the app uses a deterministic rule-based fallback.

Start the app:

```powershell
python -m uvicorn src.app.main:app --reload --port 8000
```

On macOS/Linux, create and activate the environment with `python3 -m venv
.venv` and `source .venv/bin/activate`, install dependencies with
`python -m pip install -r requirements.txt`, copy `.env.example` to `.env`,
then use the same `python -m uvicorn` command.

Open http://127.0.0.1:8000/. Signed-out browsers go to the login page; signed-in
browsers go to the dashboard for their role. The login form starts blank: enter
one of the supported demo usernames and explicitly choose its matching role:

| Role | Demo username |
| --- | --- |
| Product owner | `product-owner-1` |
| FCRM analyst | `analyst-1` |
| Risk committee member | `committee-1`, `committee-2`, or `committee-3` |

After product-owner sign-in, select **Upload case** and submit a synthetic,
text-based PDF from `/intake`. The intake page redirects signed-out or invalid
sessions to login. Use **Sign in / switch role** to clear the current demo
identity cookies and sign in as another demo user. The extraction result shows
the extracted fields, any returned policy evidence, and the draft risk score.
See the [user manual](docs/manual/user-manual.md) for analyst and committee
walkthroughs and important security limitations.

For the free-first Docker deployment, see
[ops/free-first-deployment.md](ops/free-first-deployment.md). The local
containers are free to run; OpenAI model calls may incur API charges. Docker
deployment requires a local `.env` file because Compose loads it as an
environment file.

## Where things live (maps to the hackathon's required repo layout)

```
/src            application code (this scaffold)
/ai             prompts + agent/LLM config — see ai/prompts/extract_change_request.md
/docs           requirements, architecture, governance write-ups
/evals          synthetic eval definitions, fixtures, and results
/tests          automated tests
/ops            deployment, monitoring, token analysis notes
```

## Repository evidence map

- `/src` - application code and workflow routes/services
- `/ai` - prompts and model/orchestration configuration
- `/docs/requirements` - expanded specification and framework research
- `/docs/architecture` - architecture, data model, and decision log
- `/docs/governance` - human review gates and audit rationale
- `/evals` - synthetic cases, PDF fixture, and evaluation guidance
- `/tests` - automated PDF, scoring, fixture, and workflow tests
- `/ops` - deployment, monitoring, and token-usage notes
- `/docs/presentation` - deck outline, demo script, and judging evidence matrix

The primary walkthrough is [docs/implementations/run-app-and-test.md](docs/implementations/run-app-and-test.md).
The user-facing flow and demo identities are documented in
[docs/manual/user-manual.md](docs/manual/user-manual.md). The implementation
status and known gaps are summarized in
[docs/assessment/assessment.md](docs/assessment/assessment.md). The automated
quality gate is [.github/workflows/ci.yml](.github/workflows/ci.yml).

The presentation pack is in [docs/presentation](docs/presentation). It reflects
the current implementation and identifies remaining production increments such
as real authentication, immutable database enforcement, residual-risk controls,
and operational dashboards.

For end-user instructions, see the [user manual](docs/manual/user-manual.md).

For command-line startup and testing steps, see the
[implementation runbook](docs/implementations/run-app-and-test.md).

## Deliberate design choices worth defending in the presentation

- **Extraction is an LLM call. Scoring is not.** `services/risk_scoring.py` is
  plain deterministic Python. That's an explicit "engineering judgement" call —
  document why in `/docs/architecture`.
- **Structured outputs, not free text.** The LLM call in `services/llm_service.py`
  is constrained to a Pydantic schema, so schema-invalid output fails at the
  boundary. Schema validation does not guarantee that semantically extracted
  values are factually correct; analysts must verify them against the source.
- **The extraction result is a review step, not an auto-decision.** Each case is
  persisted with a case ID. Analyst accept/reject actions require a rationale
  and are recorded as workflow events.
- **Policy retrieval is conditional.** Semantic retrieval requires an existing
  `ai/policy_index.json` and a configured provider; deterministic category rules
  are the fallback. The policy material is synthetic, not approved supervisory
  guidance.

## Current Verification

The latest recorded live extraction evaluation completed all 8 synthetic cases:

- 8/8 successful provider calls;
- 67.5% field accuracy (54/80 expected fields);
- 100% deterministic risk-level agreement (8/8 cases); and
- 2,790 ms mean latency.

This small synthetic evaluation is not a production accuracy estimate; perfect
risk-level agreement does not mean the extracted fields were all correct. The
full automated test suite passed **76 tests on 2026-10-09** (two
third-party deprecation warnings). Run the tests and inspect the current
[evaluation report](evals/results/latest.md) before presenting these figures,
as results can change.

## Current limitations and next steps

The current demo implements PDF text extraction, structured extraction,
deterministic scoring, SQLite persistence, analyst editing/rescoring, policy
evidence lookup with fallback, three-member committee voting, product-owner
submission and information-response loops, condition ownership/due dates and
evidence, case closure, linked reassessments, case ownership and queue aging,
demo login, telemetry, and a live evaluation runner. Important prototype
limitations:

- Demo identities and cookies are not production authentication.
- Workflow endpoints are role-gated using demo identities, not production
  authentication or institution-managed authorization.
- Workflow events are append-only by application behavior, not
  database-enforced or tamper-proof. Actor values are not uniformly tied to a
  verified identity.
- Committee voting is prototype logic, not an institutionally approved
  decision policy; the endpoint accepts approve, reject, or approve with
  conditions, and requires three distinct demo voters.
- Case queues display elapsed waiting days but have no configured case-stage
  service-level targets. Conditions have individual due dates and overdue
  indicators.
- Policy documents and evaluation inputs are synthetic. Scoring weights are
  placeholders; controls and residual-risk assessment are not implemented.
- Uploaded PDF bytes are not persisted; OCR for image-only PDFs is unavailable.

Do not upload real customer, account, transaction, employee, or banking data.

Remaining production increments include:

1. Add real identity and consistent authorization to every endpoint.
2. Add approved supervisory and committee decision mappings, control
   effectiveness, and residual-risk scoring.
3. Add database migrations, protected source-document storage, and background
   extraction workers.
4. Enforce audit integrity at the database or external write-once storage
   layer and add production monitoring, alerting, and cost controls.
