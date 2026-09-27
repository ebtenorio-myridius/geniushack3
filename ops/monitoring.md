# Monitoring

Track request ID and case ID, PDF extraction failures, LLM latency, LLM failures, low-confidence extraction rate, analyst rejection/override rate, committee escalation rate, and workflow age.

Operational alerts should cover repeated model failures, excessive upload rejection, abnormal latency, database errors, and a sudden increase in low-confidence or rejected drafts. Synthetic evaluation cases should run as a release regression check.

## Incident: OpenAI API unreachable from office network (2026-09-2x)

- **Observed**: All 8 calls in a live extraction eval run failed with
  `APIConnectionError` when run from the office network. `evals/results/latest.md`
  recorded 0/8 successful calls at the time.
- **Likely cause**: Outbound traffic to the OpenAI API endpoint is blocked or
  intercepted on the office network (suspected egress filtering or proxy/SSL
  inspection — not yet root-caused with the network team).
- **Detection**: Manual — noticed when the live eval run returned an
  availability failure instead of accuracy results, not via an automated
  alert. The monitoring plan above calls for alerting on repeated model
  failures; this incident predates that alert existing in practice.
- **Resolution**: Re-ran the same code and eval suite from a home network
  with no code changes. All 8 calls succeeded (68.8% field accuracy, 100%
  risk-level agreement — see `evals/results/latest.md`), confirming the
  code path was correct and the failure was network-specific, not a
  provider or application defect.
- **Follow-up**: Get the OpenAI API endpoint allow-listed on the office
  network, or document office-network limitations as a known constraint
  for anyone else running live evals. Until then, run live (non-mocked)
  evaluation and any OpenAI-dependent testing from an unblocked network.
