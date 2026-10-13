# Judging Evidence Matrix

| Criterion | Weight | Current repository evidence | Status |
|---|---:|---|---|
| AI harness and agent orchestration | 30% | Structured extraction, prompt boundary for untrusted documents, Pydantic schema, verified page-quote citations, bounded input, policy retrieval with semantic/rule fallback, telemetry, deterministic scoring boundary | Partial; no multi-agent orchestration; policy corpus is synthetic; extraction requires the configured provider |
| SDLC automation | 20% | Requirements and architecture artifacts, AI delivery evidence, tests, CI workflow, deployment and operations docs | Partial; several delivery steps remain manual; hosted CI success is not claimed |
| Human-in-the-loop and governance | 15% | Product-owner draft correction/submission, analyst edit/rescore/finalize, information requests, three distinct committee votes, condition evidence, closure, reassessment, role-gated demo routes | Partial; identities are fixed demo accounts; scoring and committee rules are not institutionally approved |
| Evaluation framework | 10% | Eight synthetic PDF cases, live upload-route runner, per-field comparison, risk agreement, latency, failure and regression tests | Latest recorded run (2026-10-02): 8/8 successful calls, 80/80 fields correct (100%), risk agreement 8/8 (100%), mean latency 3,615 ms; small synthetic sample, not a production estimate |
| Context engineering and requirement expansion | 10% | Expanded requirements, untrusted-document prompt boundary, source-page quote citations, synthetic policy evidence, open-question decisions | Partial; policy content is not approved supervisory guidance; production taxonomy/mappings still need approval |
| Production readiness | 5% | Docker, Compose volume, role checks on workflow pages/actions including upload, PDF validation/size limit, `/healthz`, retained source with SHA-256 checks, verifiable event hash chain, examiner export | Partial; demo identity is not real authentication; external audit anchoring, production storage/retention, migrations/backups, and alerting remain |
| Token efficiency | 5% | `gpt-4o-mini`, bounded document input, captured provider token fields and latency | Partial; no measured cost comparison or optimization study |
| Engineering judgement | 5% | Structured extraction, deterministic scoring and workflow transitions, persisted governance-rule snapshot | Strong prototype boundary; scoring weights, thresholds, and committee decision rule are not institutionally approved |

## Evidence rules

- Present implemented behavior as implemented and distinguish it from planned
  functionality.
- Use synthetic data only. The live upload flow rejects non-PDF, oversize,
  malformed, or textless files; extraction requires the configured model
  provider.
- All product-owner submissions, regardless of risk level, enter analyst
  review before committee review.
- State that the workflow routes check the fixed demo username/role cookies.
  These cookies are not production authentication or independently verified
  identities.
- Do not claim the upload endpoint lacks role checking: it requires the
  product-owner demo role. Continue to frame the identity system as a
  prototype boundary.
- The committee rule requires three distinct voters; two approvals approve,
  two rejections reject, and neither majority defers. This is implementation
  behavior, not approved governance policy.
- Source PDF hashes, source-page hashes, and the event hash chain are checked
  by the application. They provide integrity verification, not immutable
  storage against an administrator/database owner.
- The examiner-style ZIP includes case data, source material when retained,
  workflow and review records, verification data, and a file-hash manifest.
  It is a local prototype export, not examiner-certified evidence.
- Quote live evaluation results with the small-synthetic-sample caveat.
  Risk-level agreement is not extraction accuracy, and neither is a
  production-performance claim.
- Report the local pytest count only after running tests; do not infer hosted
  CI success from workflow configuration.
