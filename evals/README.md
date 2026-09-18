# Evals

## Synthetic baseline dataset

`data/synthetic_cases.json` contains eight non-production cases for the current
extraction schema and deterministic scoring path. Each case includes source
text, a hand-authored expected extraction, and expected risk outcomes.

The cases cover:

- low-risk feature changes;
- new customer segments and products;
- vendor onboarding;
- higher-risk geography and cross-border exposure;
- ambiguous and contradictory source text;
- prompt-injection text embedded in a submitted document; and
- multi-geography, multi-product changes.

Run the fixture regression test with:

```bash
python -m pytest tests/test_synthetic_cases.py -q
```

These are deterministic contract tests, not live LLM accuracy tests. The next
evaluation step is to run each `source_text` through `draft_extraction`, then
compare the model output with `expected_extraction` field by field. Do not add
real customer, account, transaction, or employee data to this directory.

Run the explicit paid live evaluation with:

```bash
python evals/run_extraction_eval.py
```

It writes `evals/results/latest.json` with per-case field accuracy, latency,
errors, and model output. The command is intentionally separate from unit
tests because it calls the configured model provider.

## Sample PDF input

`data/sample_change_request.pdf` is a synthetic, text-layer PDF that maps each
input label to the current extraction schema. It is suitable for manual upload
through the intake page. Regenerate it after changing the PDF template with:

```bash
python tools/generate_sample_pdf.py
```

The generated PDF includes the fields `change_title`, `change_type`,
`business_unit`, `description`, `geographies_involved`,
`customer_segments_involved`, `vendor_involved`, `vendor_name`,
`products_involved`, and `stated_risk_factors`. The model assigns
`extraction_confidence`; it is intentionally not a source fact.

## Case PDFs

The generator also creates one PDF per synthetic evaluation case under
`data/pdfs/`:

```text
data/pdfs/SYN-001.pdf
data/pdfs/SYN-002.pdf
...
data/pdfs/SYN-008.pdf
```

Each document contains the case's labeled extraction fields and source request,
including ambiguous wording and the prompt-injection case. Regenerate all
files after changing `synthetic_cases.json`:

```bash
python tools/generate_sample_pdf.py
```

How you know the extraction and scoring are actually good — 10% of the
rubric, and it's what turns "we built AI features" into "we know they work."

Suggested approach for Week 3:

1. Build a small synthetic dataset (10-20 documents) covering easy,
   ambiguous, and adversarial cases (missing fields, contradictory
   statements, a scanned/image PDF).
2. For extraction: compare model output against hand-labeled expected
   fields — track field-level accuracy, not just "looks right."
3. For scoring: since it's deterministic, this is closer to unit testing
   (see /tests) — but track whether the category weights actually produce
   sensible outcomes across your dataset.
4. Record results here (a simple CSV/markdown table is fine) and note what
   you changed in the prompt or scoring rules in response to failures —
   this iteration story is explicitly part of what's graded.
