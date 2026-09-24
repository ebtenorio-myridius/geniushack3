# Run and Test the Risk Assessment Workbench

This runbook explains how to start the app, submit synthetic PDFs, exercise the analyst and committee workflow, run tests, and run the live evaluation.

## 1. Open PowerShell in the Repository

```powershell
Set-Location "C:\GENIUS HACK\GeniusHack3"
```

## 2. Install Dependencies

Install application dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install development and fixture dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

## 3. Configure the Environment

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add the OpenAI key if live extraction is required:

```env
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
DATABASE_PATH=risk_workbench.db
PROMPT_VERSION=extract_change_request_v1
```

Do not commit or share `.env`. It is excluded by `.gitignore`.

OpenAI model calls may incur API charges.

## 4. Start the Application

Run:

```powershell
python -m uvicorn src.app.main:app --reload --port 8000
```

Keep this terminal open.

Open the application in a browser:

```text
http://localhost:8000
```

The root URL redirects to `/intake`; the intake page provides the demo login.

## 5. Check Application Health

Open a second PowerShell window and run:

```powershell
Invoke-WebRequest http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

## 6. Submit a Synthetic PDF

Use one of the generated cases:

```text
evals\data\pdfs\SYN-001.pdf
evals\data\pdfs\SYN-003.pdf
evals\data\pdfs\SYN-008.pdf
```

Recommended cases:

- `SYN-001.pdf` - low-risk feature change;
- `SYN-003.pdf` - critical cross-border vendor/product case;
- `SYN-008.pdf` - high-risk multi-channel product case.

In the browser:

1. Select the PDF file.
2. Select **Submit for extraction**.
3. Wait for the extraction result.
4. Review the case ID, extracted fields, policy evidence, and draft score.

The application flow is:

```text
PDF
-> text extraction
-> structured LLM JSON extraction
-> deterministic risk scoring
-> SQLite case persistence
```

## 7. Analyst Review

The result page provides an analyst review form.

### Edit and rescore

1. Edit any incorrect extracted field.
2. Enter the analyst identity.
3. Enter a rationale for the correction.
4. Select **Save edit and rescore**.

The app then:

- validates the edited extraction;
- creates a new extraction version;
- recalculates the deterministic score;
- refreshes policy evidence; and
- records an audit event.

The original model extraction is retained.

### Accept or reject

1. Enter an analyst identity.
2. Enter a review rationale.
3. Select **Accept draft** or **Reject draft**.

Accepted cases move to analyst-finalized status. Rejected cases remain recorded with the rejection rationale.

## 8. Committee Review

High- and critical-risk cases are flagged for committee review.

After analyst finalization, submit the case to committee review. The committee queue can be accessed with the demo committee role.

Demo analyst headers:

```text
X-Demo-User: analyst-1
X-Demo-Role: analyst
```

Demo committee headers (for direct requests; browser login uses cookies):

```text
X-Demo-User: committee-1
X-Demo-Role: committee
```

These headers are for local demonstration only. They are not production authentication.

Three distinct committee members are required for a final committee result.
Committee votes are:

- approve;
- reject;
- defer; or
- approve with conditions.

A committee decision requires an actor and rationale. Conditions can be added for conditional approval.

The complete workflow is:

```text
Submitted
-> Extracted
-> Analyst Review
-> Analyst Finalized
-> Committee Review
-> Decisioned
```

## 9. SQLite State

The default local database is:

```text
risk_workbench.db
```

It stores:

- cases;
- extracted data;
- extraction versions;
- risk assessments;
- policy evidence;
- workflow events; and
- LLM telemetry.

The database is ignored by Git. Delete it only when you intentionally want to reset local demo state.

## 10. Run Automated Tests

Run the complete test suite:

```powershell
python -m pytest -q
```

Expected result:

```text
24 passed
```

Run focused tests:

```powershell
python -m pytest -q tests\test_pdf_extraction.py
python -m pytest -q tests\test_risk_scoring.py
python -m pytest -q tests\test_synthetic_cases.py
python -m pytest -q tests\test_case_store.py
python -m pytest -q tests\test_policy_service.py
```

Compile all Python files:

```powershell
python -m compileall -q src tests tools evals
```

## 11. Validate Generated PDFs

Regenerate all synthetic PDFs:

```powershell
python tools\generate_sample_pdf.py
```

Generated files are placed in:

```text
evals\data\pdfs\SYN-001.pdf
evals\data\pdfs\SYN-002.pdf
evals\data\pdfs\SYN-003.pdf
evals\data\pdfs\SYN-004.pdf
evals\data\pdfs\SYN-005.pdf
evals\data\pdfs\SYN-006.pdf
evals\data\pdfs\SYN-007.pdf
evals\data\pdfs\SYN-008.pdf
```

Validate PDF extraction through the tests:

```powershell
python -m pytest -q tests\test_pdf_extraction.py tests\test_synthetic_cases.py
```

## 12. Run the Live Eight-Case Evaluation

This command calls the configured OpenAI model and may incur API charges:

```powershell
python evals\run_extraction_eval.py
```

The results are written to:

```text
evals\results\latest.json
evals\results\latest.md
```

The evaluator records:

- successful cases;
- field-level accuracy;
- risk-level agreement;
- latency;
- model outputs; and
- extraction errors.

The latest recorded run is:

- 0/8 successful calls; all attempts ended with `APIConnectionError`;
- field accuracy and risk-level agreement are not measurable from this run.

Run this explicitly when a new model or prompt measurement is needed. Do not run it as part of every unit-test cycle because it uses paid model calls.

## 13. Run Without OpenAI

The deterministic and persistence tests do not require a live OpenAI call:

```powershell
python -m pytest -q tests\test_risk_scoring.py tests\test_synthetic_cases.py tests\test_case_store.py tests\test_policy_service.py
```

The browser upload flow does require a configured model provider because PDF extraction is followed by LLM extraction.

## 14. Docker Compose Option

If Docker Desktop is installed:

```powershell
docker compose build
docker compose up
```

Open:

```text
http://localhost:8000
```

Stop the containers:

```powershell
docker compose down
```

Stop and remove the named SQLite volume:

```powershell
docker compose down -v
```

See [ops/free-first-deployment.md](../../ops/free-first-deployment.md) for the free-first deployment plan and limitations.

## 15. Safe Test Data Rules

Use synthetic data only.

Do not upload:

- real customer information;
- real account or transaction data;
- real employee data;
- real bank documents; or
- production PDFs.

Never commit:

- `.env`;
- API keys;
- `risk_workbench.db`;
- Python caches; or
- local evaluation state that contains secrets.

## 16. Stop the Application

In the terminal running Uvicorn, press:

```text
Ctrl+C
```

## 17. Useful Files

- [User manual](../manual/user-manual.md)
- [Synthetic cases](../../evals/data/synthetic_cases.json)
- [Generated PDFs](../../evals/data/pdfs)
- [Live evaluation runner](../../evals/run_extraction_eval.py)
- [Presentation demo script](../presentation/demo-script.md)
- [Free-first deployment plan](../../ops/free-first-deployment.md)
