# Judging Evidence Matrix

| Criterion | Weight | Current repository evidence | Status |
|---|---:|---|---|
| AI harness and agent orchestration | 30% | Bounded structured extraction, prompt boundary for untrusted documents, Pydantic schema, verified page-quote citations, policy retrieval with semantic/rule fallback, telemetry, deterministic scoring boundary | Partial; intentionally single extraction step, not multi-agent orchestration; policy corpus is synthetic; extraction requires the configured provider |
| SDLC automation | 20% | Requirements and architecture artifacts, AI delivery evidence, tests, CI workflow, deployment docs, analyst-requested AI Operations review (`src/app/services/operations_service.py`, `tests/test_operations_service.py`) | Partial; Operations advice uses bounded aggregate telemetry and checked metric references, with human verification; no scheduled monitoring, automated alerting, or remediation; live-provider review quality and hosted CI success are not claimed |
| Human-in-the-loop and governance | 15% | Product-owner draft correction/submission, analyst edit/rescore/finalize, information requests, three distinct committee votes, condition evidence, closure, reassessment, role-gated demo routes | Partial; identities are fixed demo accounts; scoring and committee rules are not institutionally approved |
| Evaluation framework | 10% | Eight synthetic PDF cases, live upload-route runner, per-field comparison, risk agreement, latency, failure and regression tests | Latest recorded run (2026-10-02): 8/8 successful calls, 80/80 fields correct (100%), risk agreement 8/8 (100%), mean latency 3,615 ms; small synthetic sample, not a production estimate; token totals not included |
| Context engineering and requirement expansion | 10% | Expanded requirements, untrusted-document prompt boundary, source-page quote citations, synthetic policy evidence, open-question decisions | Partial; policy content is not approved supervisory guidance; production taxonomy/mappings still need approval |
| Production readiness | 5% | Docker, Compose volume, role checks on workflow pages/actions including upload, PDF validation/size limit, `/healthz`, retained source with SHA-256 checks, verifiable event hash chain, examiner export | Partial; demo identity is not real authentication; external audit anchoring, production storage/retention, migrations/backups, and alerting remain |
| Token efficiency | 5% | `gpt-4o-mini`, 12,000-character input bound, provider input/output token fields when returned, latency, prompt version, and retry policy | Partial; character limit is not a token guarantee; PDF evaluation has no token totals; no measured cost comparison or optimization study |
| Engineering judgement | 5% | Structured extraction, deterministic scoring and workflow transitions, persisted governance-rule snapshot | Strong prototype boundary; scoring weights, thresholds, and committee decision rule are not institutionally approved |

## Iteration Evidence

Selected dated commits shown in the deck:

| Commit | Date | Evidence |
|---|---|---|
| `a5fb733` | 2026-10-12 | Prompt/flow re-aligned to the brief |
| `a88b252` | 2026-10-13 | Presentation materials aligned to the current app flow |
| `99834b9` | 2026-10-13 | Prompt and evaluation evidence refreshed |
| `8f0d781`, `3250a6f` | 2026-10-21 | UI and presentation-generator iterations |

These are illustrative milestones rather than a complete history or proof of
automated delivery. The actual repository log remains the source of truth.

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
