# Genius Hacks 2026 Submission Assessment

Assessment date: 2026-09-24

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

The app addresses the central problem substantially and is suitable for a credible demonstration. It is not yet a production-ready banking platform. The largest remaining risks are prototype-level authentication, incomplete residual-risk/control modeling, limited measured cost optimization, and limited preservation of the actual AI output/review trail for the requirements and design stages.

Estimated current rubric position: approximately **59.25/100**. This is an engineering estimate, not an official judging score. The assessment reflects verified policy citations, explicit six-stage delivery evidence, improved scoring signals, synchronized governance documentation, and 24 passing tests. The latest live evaluation is unavailable because all eight provider calls failed with `APIConnectionError`.

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
- three-member committee voting for approve, reject, defer, and conditional-approval decisions;
- timestamped workflow events;
- synthetic evaluation PDFs and JSON fixtures;
- model latency and token telemetry.

Partial or missing:

- control effectiveness and residual-risk scoring;
- FCRM approval of the published supervisory-framework mapping;
- immutable audit enforcement at the database permission layer;
- real identity and role management;
- production committee identity and decision policy beyond the demo three-vote quorum;
- source-page citations and document hashes;
- production database, object storage, and background processing.

## 2. AI Across the Six Delivery Stages

### Stage 01: Requirements

**Status: Partial**

Evidence:

- `docs/requirements/spec.md`
- `docs/requirements/open-questions.md`
- `docs/requirements/supervisory-frameworks.md`
- `ai/prompts/sdlc_delivery.md`
- `docs/sdlc/ai-delivery-evidence.md`

The repository expands the brief into personas, workflow, acceptance criteria, scope, open-question decisions, human gates, and reusable AI instructions. It still does not preserve a complete transcript of generated outputs and human approval history from the requirements phase.

### Stage 02: Design

**Status: Partial**

Evidence:

- `docs/architecture/overview.md`
- `docs/architecture/data-model.md`
- `docs/architecture/decisions.md`
- `docs/sdlc/ai-delivery-evidence.md`

The architecture, data model, workflow, AI/deterministic boundary, and design-stage AI guidance are documented. Evidence of AI-generated alternatives, design critiques, UX decisions, and rejected designs is limited.

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

Latest recorded live run:

- 0/8 successful calls; all attempts ended with `APIConnectionError`;
- no model-quality accuracy or risk-agreement measurement;
- 24 automated tests passing.

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
| AI harness and agent orchestration | 30% | 50% | 15.0 | Structured extraction, versioned prompts, targeted policy evidence, context boundary, telemetry, and deterministic workflow. No multi-agent orchestration or production RAG. |
| SDLC automation | 20% | 50% | 10.0 | Six-stage AI delivery guidance, human gates, CI, and requirements/design/development/testing/deployment/ops artifacts. |
| Human-in-the-loop and governance | 15% | 75% | 11.25 | Analyst edit/finalize, versioning, committee queue/decisions, rationale, role gates, and audit events. Real identity, quorum, and immutable DB enforcement remain. |
| Evaluation framework | 10% | 75% | 7.5 | Eight fixtures/PDFs, live runner, retries, field accuracy, risk agreement, latency, and 19 regression tests. |
| Context engineering and requirements | 10% | 65% | 6.5 | Open-question decisions, explicit extraction rules, untrusted-document boundary, targeted citations, and published source mapping. |
| Production readiness | 5% | 45% | 2.25 | Docker, Compose, CI, upload limits, health endpoint, telemetry, and free-first runbook. Production identity, migrations, object storage, and alerting remain. |
| Token efficiency | 5% | 55% | 2.75 | `gpt-4o-mini`, bounded input, captured token fields, and evaluation latency. Cost comparison remains. |
| Engineering judgement | 5% | 80% | 4.0 | Strong AI/deterministic boundary, narrow risk-signal rules, explicit gates, and reproducible evaluation. Residual-risk governance remains. |
| **Estimated total** | **100%** |  | **59.25** |  |

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

The final editable PowerPoint deck is present at
`docs/presentation/Risk_Assessment_Workbench_Genius_Hacks_2026.pptx`, generated
from `tools/generate_presentation.py`. The pushed repository contains three
meaningful commits covering the initial submission, rubric improvements, and
presentation deck.

## 5. Required Documents

| Artifact | Current status |
|---|---|
| Expanded requirements | Present in `docs/requirements/spec.md` |
| Open questions | Present in `docs/requirements/open-questions.md` |
| Supervisory-framework research | Official sources and prototype mapping present; FCRM approval remains |
| Architecture overview | Present |
| Data model | Present, but residual-risk/control model is incomplete |
| Decision log | Present |
| Governance gates | Present and synchronized with current committee implementation |
| Evaluation definitions | Present in `evals/README.md` and runner |
| Synthetic datasets | Present in JSON and generated PDFs |
| Evaluation results | Present in `evals/results/` |
| Automated tests | Present; 19 pass |
| Deployment approach | Present in `ops/` |
| Monitoring approach | Present, but no dashboard or alerts |
| Token analysis | Present, but measured cost analysis is limited |
| Prompt and agent configuration | Present in `/ai` |
| Presentation | Editable PPTX present, with outline and demo script |
| Commit history | Present in the pushed repository: three meaningful commits |

## 6. Other Page Details That Matter

### Commit history

The page says a repository that appears fully formed in a single commit tells the panel little about how the team worked. This repository now has separate commits for the initial submission, rubric improvements, and presentation deck. Continue preserving prompt/evaluation iterations.

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

- full automated suite: **24 passed**;
- Python compilation for application, tests, tools, and evals: passed;
- eight generated PDF inputs: validated through the app's PDF extractor;
- live evaluation: latest recorded run had 0/8 successful calls because of `APIConnectionError`;
- live field accuracy and risk-level agreement: not measurable from the latest run;
- live expanded workflow: upload, edit, rescore, finalize, committee queue, decisioned status, and five audit events.

The test suite reported one ReportLab deprecation warning. It does not currently fail the tests.

## 8. Priority Actions Before Submission

1. Obtain FCRM approval for the cited supervisory-framework mapping and scoring taxonomy.
2. Add controls, control effectiveness, residual-risk scoring, remediation conditions, and source-page evidence.
3. Replace demo headers with real authentication if claiming production readiness.
4. Add multi-member committee votes, quorum, and conflict-of-interest handling.
5. Add a measured token/cost report and optimization comparison.
6. Preserve prompt/evaluation failure iterations as dated artifacts.
7. Verify `.env`, SQLite databases, API keys, caches, and generated local state are excluded from the GitHub submission.

## Final Verdict

The app is a strong, testable prototype and a credible demonstration of the core Risk Assessment Workbench idea. It substantially addresses the problem statement and demonstrates meaningful AI, deterministic scoring, governance, evaluation, and operations work.

It should be presented as a governed prototype rather than a production banking platform. The highest scoring upside now comes from the remaining domain and production evidence: approved framework mapping, controls and residual risk, real authentication, multi-member governance, measured cost optimization, and preserved AI-output review history across requirements and design.
