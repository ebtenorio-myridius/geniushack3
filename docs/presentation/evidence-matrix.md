# Judging Evidence Matrix

| Criterion | Weight | Current repository evidence | Status |
|---|---:|---|---|
| AI harness and agent orchestration | 30% | Structured extraction, versioned prompt, bounded document text, policy retrieval with semantic/rule fallback, telemetry, deterministic scoring boundary | Partial; no multi-agent orchestration; policy corpus is synthetic, and extraction requires the provider |
| SDLC automation | 20% | Six-stage delivery artifacts, human review guidance, CI workflow, requirements/design/development/testing/deployment/operations docs | Partial; substantial delivery evidence is documented, while several steps remain manual; hosted CI success is not claimed |
| Human-in-the-loop and governance | 15% | Analyst edit/finalize, committee voting, required rationale, extraction versions, workflow events, demo login and page guards | Partial; demo identities only, authorization is inconsistent across endpoints, and event immutability is application-enforced rather than database-enforced |
| Evaluation framework | 10% | Eight synthetic cases/PDFs, live runner, per-field comparison, risk agreement, latency, regression tests | Latest recorded live run: 8/8 calls succeeded, 54/80 fields correct (67.5%), risk agreement 8/8 (100%); small synthetic sample, not a production estimate |
| Context engineering and requirement expansion | 10% | Expanded requirements, untrusted-document prompt boundary, synthetic policy evidence, open-question decisions | Partial; synthetic policy content is not approved supervisory guidance; source spans and approved production taxonomy remain |
| Production readiness | 5% | Docker, Compose volume, CI configuration, upload limits, MIME check, `/healthz`, free-first runbook | Partial; real identity, consistent endpoint authorization, migrations, object storage, database-enforced audit controls, and alerting remain |
| Token efficiency | 5% | `gpt-4o-mini`, 12,000-character input bound, captured provider token fields and latency | Partial; no measured cost comparison or optimization study |
| Engineering judgement | 5% | Structured outputs for extraction and deterministic scoring/workflow for decisions | Strong prototype boundary; scoring weights and committee decision rule are not institutionally approved |

## Evidence rules

- Present implemented behavior as implemented.
- Present planned functionality as a next increment, not as a claim.
- Use the sample PDF and synthetic cases for the live walkthrough.
- Show the repository folders and point judges to the exact artifacts behind each claim.
- Distinguish guarded browser pages from API endpoint authorization; in particular, the PDF upload POST is not currently role-gated.
- Present the three-vote committee rule as prototype behavior, not approved governance policy; the endpoint accepts approve, reject, and approve-with-conditions, but not defer.
- Quote the latest live-evaluation metrics with the small synthetic sample caveat. Risk-level agreement is not extraction accuracy.
