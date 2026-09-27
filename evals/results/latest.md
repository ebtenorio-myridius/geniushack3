# Live Extraction Evaluation (latest recorded run)

Generated from `evals/run_extraction_eval.py` against the eight synthetic
cases using `gpt-4o-mini`. The comparison normalizes case and list ordering;
missing fields and semantic mismatches still count as incorrect. Detailed model
outputs are recorded in `evals/results/latest.json`.

- Cases attempted: 8
- Successful calls: 8 of 8
- Field accuracy: 67.5% (54 of 80 expected fields)
- Risk-level agreement: 100% (8 of 8 cases)
- Mean latency: 2,790 ms per case
- Provider errors: none

| Case | Field accuracy | Risk agreement | Latency |
| --- | ---: | --- | ---: |
| SYN-001 | 8/10 (80%) | Yes (low) | 3,313 ms |
| SYN-002 | 7/10 (70%) | Yes (medium) | 2,867 ms |
| SYN-003 | 7/10 (70%) | Yes (critical) | 2,200 ms |
| SYN-004 | 6/10 (60%) | Yes (medium) | 2,651 ms |
| SYN-005 | 5/10 (50%) | Yes (medium) | 2,813 ms |
| SYN-006 | 7/10 (70%) | Yes (low) | 2,455 ms |
| SYN-007 | 7/10 (70%) | Yes (medium) | 2,960 ms |
| SYN-008 | 7/10 (70%) | Yes (high) | 3,061 ms |

This is a small synthetic evaluation, not a production accuracy estimate.
Risk-level agreement reflects the deterministic scorer applied to extracted
fields; it does not establish that the extracted fields themselves are all
correct. Re-run the explicitly paid live evaluation with
`python evals/run_extraction_eval.py` after changing the prompt, model, or
extraction schema.