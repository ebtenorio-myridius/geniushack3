# Live Extraction Baseline

Generated from `evals/run_extraction_eval.py` against the eight synthetic
cases. The comparison normalizes case and list ordering; it does not hide
missing fields or semantic mismatches.

- Cases: 8
- Successful calls: 8 of 8
- Field accuracy: 66.2%
- Risk-level agreement: 87.5%
- The runner retries connection, timeout, and rate-limit failures up to three
  times.

The result is a baseline, not a production quality claim. The next iteration
should improve product and risk-factor extraction for the lower-scoring cases,
then rerun this command and compare the JSON output.