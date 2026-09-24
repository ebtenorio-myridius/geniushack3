# Judging Evidence Matrix

| Criterion | Weight | Current repository evidence | Status |
|---|---:|---|---|
| AI harness and agent orchestration | 30% | Structured extraction, versioned prompts, targeted policy evidence, telemetry, and deterministic workflow boundary | Partial; no multi-agent orchestration or production RAG |
| SDLC automation | 20% | Six-stage AI delivery guidance, human gates, CI, requirements/design/development/testing/deployment/ops artifacts | Partial; delivery evidence is documented rather than fully automated |
| Human-in-the-loop and governance | 15% | Analyst edit/finalize, committee queue, three-member vote quorum, required rationale, workflow events, demo role gates | Partial; real identity, decision policy, and immutable DB enforcement remain |
| Evaluation framework | 10% | Eight synthetic cases/PDFs, live runner, retries, field accuracy, risk agreement, latency, regression tests | Contract tests pass; latest live run was unavailable (8 API connection failures) |
| Context engineering and requirement expansion | 10% | Open-question decisions, untrusted-document boundary, targeted policy citations, published source mapping | Partial; source spans and approved production taxonomy remain |
| Production readiness | 5% | Docker, Compose volume, CI, upload limits, MIME check, `/healthz`, free-first runbook | Partial; production identity, migrations, object storage, and alerting remain |
| Token efficiency | 5% | `gpt-4o-mini`, bounded input, captured token fields, explicit evaluation telemetry | Partial; provider usage and optimization comparison remain |
| Engineering judgement | 5% | Structured outputs for extraction and deterministic scoring/workflow for decisions | Strong prototype; scoring weights still need governance |

## Evidence rules

- Present implemented behavior as implemented.
- Present planned functionality as a next increment, not as a claim.
- Use the sample PDF and synthetic cases for the live walkthrough.
- Show the repository folders and point judges to the exact artifacts behind each claim.
