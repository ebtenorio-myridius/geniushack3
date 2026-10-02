# Live PDF Extraction Evaluation (latest recorded run)

Run date: 2026-10-02. Each of the eight PDFs in `evals/data/pdfs/` was submitted
through the app's FastAPI `POST /intake/upload` route using `gpt-4o-mini`. This
exercised PDF text extraction, the live structured OpenAI extraction call,
deterministic scoring, and case creation. Test cases and telemetry used a
temporary SQLite database.

Expected fields were compared with `expected_extraction` in
`evals/data/synthetic_cases.json`, excluding `extraction_confidence`. String
comparisons ignore case and surrounding whitespace; list comparisons ignore
case, surrounding whitespace, and ordering. Missing or different values count
as incorrect.

- PDF uploads attempted: 8
- Successful HTTP responses and saved cases: 8 of 8
- Field accuracy: 100% (80 of 80 expected fields)
- Risk-level agreement: 100% (8 of 8 cases)
- Mean end-to-end latency: 3,615 ms per PDF
- Provider errors: none

| PDF | Field accuracy | Risk agreement | Latency |
| --- | ---: | --- | ---: |
| SYN-001.pdf | 10/10 (100%) | Yes (low) | 5,810 ms |
| SYN-002.pdf | 10/10 (100%) | Yes (medium) | 2,771 ms |
| SYN-003.pdf | 10/10 (100%) | Yes (critical) | 4,444 ms |
| SYN-004.pdf | 10/10 (100%) | Yes (medium) | 3,183 ms |
| SYN-005.pdf | 10/10 (100%) | Yes (medium) | 3,314 ms |
| SYN-006.pdf | 10/10 (100%) | Yes (low) | 2,719 ms |
| SYN-007.pdf | 10/10 (100%) | Yes (medium) | 3,443 ms |
| SYN-008.pdf | 10/10 (100%) | Yes (high) | 3,237 ms |

The temporary database was discarded after the run. Per-case extraction
payloads were not retained; `latest.json` records the measured counts,
latencies, and outcomes. This small synthetic set is not a production accuracy
estimate. Perfect agreement here does not establish general model reliability.

This was an upload-route PDF evaluation, not the separate
`evals/run_extraction_eval.py` source-text run. Running that script writes a new
`latest.json` and replaces these PDF-run results with its source-text metrics.