# Genius Hacks 2026 Submission Assessment

Assessment date: 2026-09-18

Source brief: https://myridius.com/genius-hacks-q3-2026

## Executive Summary

The Risk Assessment Workbench is a functioning synthetic-data prototype with this implemented flow:

```text
PDF
-> text extraction
-> structured OpenAI extraction
-> deterministic risk scoring
-> SQLite persistence
-> analyst edit/rescore
-> analyst finalization
-> committee queue
-> committee decision
```

The app addresses the central problem substantially and is suitable for a credible demonstration. It is not yet a production-ready banking platform. The largest remaining submission risks are stale documentation, lack of Git history, prototype-level authentication, incomplete supervisory-framework grounding, and limited evidence that AI was used throughout all six delivery stages.

Estimated current rubric position: approximately **49/100**. This is an engineering estimate, not an official judging score.

## 1. Problem Statement Compliance

### Hackathon problem

The client is a large, closely supervised bank. FCRM must assess the financial-crime risk of:

- new products;
- feature changes;
- process changes;
- vendor onboarding;
- new geographies; and
- new customer segments.

The current business process relies on email, Word, Excel, and SharePoint. It is slow, inconsistent between analysts, and difficult to reconstruct for examiners.

The requested product is a governed Risk Assessment Workbench that carries a request from intake through assessment to committee decision. AI should be used where it adds value, while humans remain responsible for decisions.

### Current coverage

Implemented:

- PDF intake;
- text extraction with `pypdf`;
- structured LLM extraction validated by Pydantic;
- deterministic scoring with category rationales;
- SQLite case persistence;
- extraction versioning;
- analyst edits and rescoring;
- policy evidence attachment using synthetic policy sources;
- analyst finalization;
- committee queue;
- approve, reject, defer, and conditional-approval decisions;
- timestamped workflow events;
- synthetic evaluation PDFs and JSON fixtures;
- model latency and token telemetry.

Partial or missing:

- control effectiveness and residual-risk scoring;
- complete published supervisory-framework mapping;
- immutable audit enforcement at the database permission layer;
- real identity and role management;
- multi-member committee voting and quorum;
- source-page citations and document hashes;
- production database, object storage, and background processing.

## 2. AI Across the Six Delivery Stages

### Stage 01: Requirements

**Status: Partial**

Evidence:

- `docs/requirements/spec.md`
- `docs/requirements/README.md`
- `docs/requirements/supervisory-frameworks.md`

The repository expands the brief into personas, workflow, acceptance criteria, and scope. It does not yet preserve the actual AI prompts, generated outputs, human edits, and approval history used during requirements discovery.

### Stage 02: Design

**Status: Partial**

Evidence:

- `docs/architecture/overview.md`
- `docs/architecture/data-model.md`
- `docs/architecture/decisions.md`

The architecture, data model, workflow, and AI/deterministic boundary are documented. Evidence of AI-generated alternatives, design critiques, UX decisions, and rejected designs is limited.

### Stage 03: Development

**Status: Demonstrated**

Evidence:

- `src/app/services/llm_service.py`
- `src/app/services/risk_scoring.py`
- `src/app/services/case_store.py`
- `src/app/services/policy_service.py`
- `ai/prompts/extract_change_request.md`
- `ai/agent_config.yaml`

The app uses structured LLM extraction, deterministic scoring, policy lookup, persistence, workflow transitions, and telemetry.

### Stage 04: Testing

**Status: Substantially demonstrated**

Evidence:

- `tests/`
- `evals/data/synthetic_cases.json`
- `evals/data/pdfs/`
- `evals/run_extraction_eval.py`
- `evals/results/latest.json`
- `evals/results/latest.md`

Current measured live baseline:

- 8/8 successful calls after retry handling;
- 66.2% normalized field accuracy;
- 87.5% risk-level agreement;
- 17 automated tests passing.

The evaluation exposes real extraction weaknesses, which is useful evidence. The repository should more explicitly record each failure, prompt change, and subsequent result.

### Stage 05: Deployment

**Status: Partial**

Evidence:

- `Dockerfile`
- `docker-compose.yml`
- `/healthz` endpoint;
- `ops/deployment.md`;
- `ops/free-first-deployment.md`.

The free-first local Docker deployment is documented. Docker was not available in the assessment environment, so Compose execution was not independently verified here.

Missing for production:

- CI build pipeline;
- database migrations;
- TLS and reverse proxy configuration;
- production secret manager;
- rollback automation;
- container and dependency security scanning.

### Stage 06: Operations

**Status: Partial**

Evidence:

- telemetry persistence;
- `ops/monitoring.md`;
- `ops/token-usage.md`;
- live evaluation latency and token fields;
- documented failure handling and free-first operations.

Missing:

- dashboards;
- alerting;
- centralized logs;
- operational feedback UI;
- measured cost report;
- automated continuous-improvement loop.

## 3. Judging Criteria

| Criterion | Weight | Estimated satisfaction | Contribution | Evidence and gaps |
|---|---:|---:|---:|---|
| AI harness and agent orchestration | 30% | 40% | 12.0 | Structured extraction, prompts, policy lookup, context boundary, telemetry. No multi-agent orchestration or full policy RAG. |
| SDLC automation | 20% | 35% | 7.0 | Requirements, architecture, development, tests, deployment, and ops artifacts exist. AI participation evidence across each stage is incomplete. |
| Human-in-the-loop and governance | 15% | 65% | 9.75 | Analyst edit/finalize, rationale, committee queue, decisions, role checks, and audit events. Real identity, immutable enforcement, and quorum are missing. |
| Evaluation framework | 10% | 70% | 7.0 | Eight fixtures, eight PDFs, live evaluation, metrics, retries, and regression tests. Field accuracy needs improvement and iteration history needs expansion. |
| Context engineering and requirements | 10% | 50% | 5.0 | Expanded specification, prompt rules, synthetic policy evidence, and untrusted-document boundary. Published source mapping and source spans are incomplete. |
| Production readiness | 5% | 40% | 2.0 | Docker, Compose, upload limits, health endpoint, SQLite volume, telemetry. No production identity, migrations, object storage, malware scanning, or backup automation. |
| Token efficiency | 5% | 50% | 2.5 | `gpt-4o-mini`, bounded input, token telemetry, and evaluation latency. No cost dashboard or documented optimization experiment. |
| Engineering judgement | 5% | 75% | 3.75 | Strong separation of probabilistic extraction from deterministic scoring and workflow. Prototype scoring rules still need formal governance. |
| **Estimated total** | **100%** |  | **49.0** |  |

## 4. What Must Be Submitted

The hackathon requires two items by **30 September 2026**:

1. One GitHub repository containing the codebase and every supporting artifact.
2. A presentation deck.

The repository is the primary evidence source. The judges specifically expect prompts, agent configuration, evaluations, governance decisions, token analysis, architecture decisions, and commit history.

### Repository structure

Present in the workspace:

- `/src` - application code;
- `/ai` - prompts and model/orchestration configuration;
- `/docs/requirements` - expanded specification and framework research;
- `/docs/architecture` - architecture, data model, and decision log;
- `/docs/governance` - review gates and audit rationale;
- `/evals` - datasets, generated PDFs, evaluation runner, and results;
- `/tests` - automated test suites;
- `/ops` - deployment, monitoring, and token usage;
- `/docs/presentation` - deck outline, demo script, and evidence matrix;
- `README.md` - setup and repository guide.

### Submission gap

`docs/presentation/deck.md` is an outline, not a final PowerPoint, PDF, or slide deck. A real presentation artifact must still be created.

The workspace is not currently a Git repository. The page explicitly says commit history is part of the evidence. A GitHub repository with meaningful incremental commits is still required.

## 5. Required Documents

| Artifact | Current status |
|---|---|
| Expanded requirements | Present in `docs/requirements/spec.md` |
| Open questions | Placeholder-level content in `docs/requirements/README.md`; should be expanded |
| Supervisory-framework research | Plan present; cited, approved mapping incomplete |
| Architecture overview | Present |
| Data model | Present, but residual-risk/control model is incomplete |
| Decision log | Present |
| Governance gates | Present, but portions are stale and should reflect current committee implementation |
| Evaluation definitions | Present in `evals/README.md` and runner |
| Synthetic datasets | Present in JSON and generated PDFs |
| Evaluation results | Present in `evals/results/` |
| Automated tests | Present; 17 pass |
| Deployment approach | Present in `ops/` |
| Monitoring approach | Present, but no dashboard or alerts |
| Token analysis | Present, but measured cost analysis is limited |
| Prompt and agent configuration | Present in `/ai` |
| Presentation | Outline only; final deck still needed |
| Commit history | Missing from current workspace |

## 6. Other Page Details That Matter

### Commit history

The page says a repository that appears fully formed in a single commit tells the panel little about how the team worked. Create meaningful incremental commits and preserve prompt/evaluation iterations.

### Synthetic data only

Do not submit real customer, account, employee, transaction, or banking documents. Keep `.env` and `risk_workbench.db` out of GitHub. They are ignored by `.gitignore`, but verify they are not manually staged.

### No prompt-to-app generators

Lovable, Bolt, v0, Replit Agent, and similar complete prompt-to-app generators are prohibited. AI-assisted coding in a real codebase is allowed. The presentation should show directed decisions, reviews, failures, and iterations.

### Model choice is not scored directly

The judges assess the surrounding design, orchestration, governance, evaluation, and reasoning. The choice of OpenAI, Ollama, or another provider is secondary to the evidence.

### Humans decide

The system must prepare evidence. It must not automatically approve or reject a change. The current committee decision is human-triggered, which aligns with this requirement. Demo header roles are not production authentication.

### Ambiguity is part of the assessment

The original brief is intentionally incomplete. The team is expected to show how it expanded requirements, resolved assumptions, handled contradictory documents, and preserved context.

### Deployment does not have to be public

The page requires a credible deployment and operations approach. A running deployment is stronger evidence, but enterprise-grade reasoning matters more than public uptime. The free-first Docker/SQLite plan is suitable for the demo; it should not be presented as production banking infrastructure.

### Dates

- Registration deadline: 2 September 2026;
- submission deadline: 30 September 2026;
- final presentations: to be announced;
- awards: to be announced.

## 7. Test Evidence

Executed checks:

- full automated suite: **17 passed**;
- Python compilation for application, tests, tools, and evals: passed;
- eight generated PDF inputs: validated through the app's PDF extractor;
- live evaluation: 8/8 successful calls after retries;
- live field accuracy: 66.2%;
- live risk-level agreement: 87.5%;
- live expanded workflow: upload, edit, rescore, finalize, committee queue, decisioned status, and five audit events.

The test suite reported one ReportLab deprecation warning. It does not currently fail the tests.

## 8. Priority Actions Before Submission

1. Create a real Git repository and meaningful incremental commit history.
2. Create the final presentation deck in PDF or PowerPoint format.
3. Update stale documentation that still describes committee workflow, policy retrieval, roles, and telemetry as future work.
4. Add cited published supervisory-framework sources and map each scoring category to them.
5. Add controls, control effectiveness, residual risk, remediation conditions, and source citations.
6. Replace demo headers with real authentication if claiming production readiness.
7. Add multi-member committee votes, quorum, and conflict-of-interest handling.
8. Add a measured token/cost report and optimization comparison.
9. Preserve prompt/evaluation failure iterations as dated artifacts.
10. Verify `.env`, SQLite databases, API keys, caches, and generated local state are excluded from the GitHub submission.

## Final Verdict

The app is a strong, testable prototype and a credible demonstration of the core Risk Assessment Workbench idea. It substantially addresses the problem statement and demonstrates meaningful AI, deterministic scoring, governance, evaluation, and operations work.

It should be presented as a governed prototype rather than a production banking platform. The highest scoring upside now comes from submission evidence: Git history, a finished deck, explicit AI use across all six delivery stages, published-framework grounding, and documented iteration from evaluation failures.
