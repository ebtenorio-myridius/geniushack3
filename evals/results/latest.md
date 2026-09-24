# Live Extraction Evaluation (latest recorded run)

Generated from `evals/run_extraction_eval.py` against the eight synthetic
cases. The comparison normalizes case and list ordering; it does not hide
missing fields or semantic mismatches.

- Cases attempted: 8
- Successful calls: 0 of 8
- Field accuracy: 0%
- Risk-level agreement: 0%
- Failure: all eight calls ended with `APIConnectionError`
- The runner retries connection, timeout, and rate-limit failures up to three
  times.

This latest recorded run is an availability failure, not a model-quality
measurement. The older 8/8, 66.2%, and 87.5% figures must not be presented as
the current baseline. Rerun `python evals/run_extraction_eval.py` with a working
provider configuration before making accuracy claims.