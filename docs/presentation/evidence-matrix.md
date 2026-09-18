# Judging Evidence Matrix

| Criterion | Weight | Current repository evidence | Status |
|---|---:|---|---|
| AI harness and agent orchestration | 30% | Structured extraction in `src/app/services/llm_service.py`; prompt and model config in `/ai`; deterministic scoring boundary | Partial; no policy retrieval or multi-agent workflow |
| SDLC automation | 20% | Requirements, architecture, development, tests, Docker, deployment and operations artifacts across the repository | Partial; no CI pipeline or complete committee workflow |
| Human-in-the-loop and governance | 15% | Draft-only result, persisted case ID, analyst accept/reject, required rationale, workflow events | Partial; committee vote and authorization remain |
| Evaluation framework | 10% | Eight synthetic cases, PDF fixture, schema/scoring contract tests, documented next metrics | Partial; no live LLM baseline yet |
| Context engineering and requirement expansion | 10% | Expanded specification, prompt instructions, untrusted-document boundary, framework research plan | Partial; no retrieval citations or source spans |
| Production readiness | 5% | Docker, Compose volume, environment config, upload limit, MIME check, `/healthz` | Partial; no auth, migrations, retries, or production telemetry |
| Token efficiency | 5% | `gpt-4o-mini`, bounded input, token-usage plan | Partial; no measured usage report |
| Engineering judgement | 5% | Structured outputs for extraction and deterministic scoring/workflow for decisions | Strong prototype; scoring weights still need governance |

## Evidence rules

- Present implemented behavior as implemented.
- Present planned functionality as a next increment, not as a claim.
- Use the sample PDF and synthetic cases for the live walkthrough.
- Show the repository folders and point judges to the exact artifacts behind each claim.
