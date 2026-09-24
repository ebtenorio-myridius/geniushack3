# Office Chat History - Risk Assessment Workbench

This file records the office-session collaboration history for the Risk Assessment Workbench app. Exact per-message timestamps were not available in the chat context, so entries are grouped by the known conversation dates and kept in chronological order. Secrets, API keys, and credentials are intentionally omitted.

## 2026-09-23 - Repository Setup and Local Run

### Request
The repository had just been cloned. The request was to analyze the whole folder and install the tools/apps needed to run the app locally.

### Actions
- Reviewed repository setup files:
  - `README.md`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `Dockerfile`
  - `docker-compose.yml`
  - `src/app/config.py`
  - `src/app/main.py`
  - `src/app/services/llm_service.py`
- Identified app stack:
  - FastAPI
  - Jinja2
  - HTMX
  - SQLite
  - OpenAI structured outputs
  - pypdf
  - pytest
- Checked local tooling.
- Found installed Python was 3.14, while CI targets Python 3.12.
- Installed Python 3.12.10 locally.
- Created `.venv` with Python 3.12.
- Installed project dependencies from `requirements-dev.txt`.
- Created local `.env` from `.env.example`.
- Ran local validation.

### Results
- Python 3.12.10 installed.
- Virtual environment created successfully.
- Dependencies installed successfully.
- `pip check` passed.
- Compile check passed.
- Test suite passed: `19 passed`.
- Local FastAPI app started successfully.
- `/healthz` returned:

```json
{"status":"ok"}
```

### Notes
Docker was not installed on the office machine, so the Python virtual environment path was used.

## 2026-09-23 - PowerShell Activation Issue

### Request
PowerShell refused to run `.venv\Scripts\Activate.ps1` because execution policies blocked scripts. `uvicorn` was also not recognized because the environment was not activated.

### Diagnosis
PowerShell script activation was blocked, but the virtual environment itself was valid.

### Resolution
Recommended running Uvicorn directly through the virtual environment Python executable:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.app.main:app --reload --port 8000
```

Also provided a temporary process-scope bypass option:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
uvicorn src.app.main:app --reload --port 8000
```

## 2026-09-23 - Free Hosting and Deployment Recommendations

### Request
Suggest free hosting and free tools where the app could be deployed for demo purposes.

### Actions
- Reviewed existing deployment and operations notes:
  - `ops/free-first-deployment.md`
  - `ops/deployment.md`
  - `ops/monitoring.md`
- Compared hosting options:
  - Render Free Web Service
  - Google Cloud Run
  - Oracle Cloud Always Free VM
  - Supabase PostgreSQL
  - Railway
  - Hugging Face Spaces
  - Cloudflare Workers

### Findings
Recommended options:

1. **Render Free Web Service**
   - Best for quick public demo.
   - Supports Docker/FastAPI.
   - Free HTTPS URL.
   - Sleeps after inactivity.
   - SQLite data is ephemeral.

2. **Oracle Cloud Always Free VM**
   - Best for persistent SQLite without code changes.
   - Can run Docker Compose.
   - Requires more server administration.

3. **Cloud Run + Supabase PostgreSQL**
   - Better cloud-native path.
   - Requires migrating from SQLite to PostgreSQL.

### Security Note
A real-looking OpenAI key was present in `.env` during review. Recommendation was to rotate/revoke the exposed key and avoid committing `.env`.

## 2026-09-23 - Deployment Documentation

### Request
Put deployment recommendations and related steps into documentation.

### Actions
- Created `docs/deployment.md` because it did not yet exist.
- Added sections covering:
  - target selection matrix
  - local deployment
  - Docker Compose
  - Render Free Web Service
  - Google Cloud Run
  - Oracle Cloud Always Free VM
  - Supabase PostgreSQL migration
  - validation gates
  - hosting options not recommended
  - production gaps

### Later Reorganization
The user requested a `docs/deployment` folder. The file was moved to:

```text
docs/deployment/deployment.md
```

## 2026-09-23 - Git Push and Authentication Issues

### Request
The user encountered:

```text
error: src refspec main does not match any
```

### Diagnosis
- Local branch was `master`, not `main`.
- Remote also used `origin/master`.
- Correct push command was:

```powershell
git push origin master
```

### Follow-up Error
Push failed with:

```text
Permission to ebtenorio-myridius/geniushack3.git denied to ebtenorio.
```

### Diagnosis
GitHub was authenticating as `ebtenorio`, but the intended account was `ebtenorio-myridius`.

### Actions
- Updated remote URL to explicitly target `ebtenorio-myridius`:

```text
https://ebtenorio-myridius@github.com/ebtenorio-myridius/geniushack3.git
```

### Recommendation
Clear cached GitHub credentials from Windows Credential Manager and sign in as `ebtenorio-myridius`.

## 2026-09-23 - OpenAI API Testing and Office Network Issue

### Request
Run the app against all prepared PDFs under `evals/data/pdfs` using the configured OpenAI key.

### Actions
- Identified eight PDFs:
  - `SYN-001.pdf`
  - `SYN-002.pdf`
  - `SYN-003.pdf`
  - `SYN-004.pdf`
  - `SYN-005.pdf`
  - `SYN-006.pdf`
  - `SYN-007.pdf`
  - `SYN-008.pdf`
- Verified all PDFs had extractable text.
- Ran local test suite.
- Ran live extraction evaluation.

### Results
- PDF parsing passed for all eight PDFs.
- Local tests passed.
- Live OpenAI extraction failed for all cases with `APIConnectionError`.
- Detailed traceback showed:

```text
[SSL: CERTIFICATE_VERIFY_FAILED]
self-signed certificate in certificate chain
```

### Diagnosis
The office network likely performs HTTPS inspection and presents a corporate/self-signed certificate not trusted by Python/httpx.

### Confirmation
The user later tested from home and confirmed extraction worked there. This confirmed the app and key were functional, and the office network was the blocker.

### Diagnostic URL
Recommended checking:

```text
https://api.openai.com/v1/models
```

A browser/API response saying missing bearer authentication confirmed OpenAI was reachable, while Python still failed because of certificate trust.

## 2026-09-23 - Local App Run for Manual Testing

### Request
Run the app locally so the user could test it manually.

### Action
Started Uvicorn locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Result
App was available at:

```text
http://127.0.0.1:8000
```

Health check passed.

## 2026-09-23 - Whole-App Assessment

### Request
Assess the app, excluding the known office OpenAI connectivity issue.

### Key Findings
Critical/high concerns identified:

1. Demo headers were not production authentication.
2. Analyst edits could erase vendor risk if vendor involvement was not preserved.
3. Committee escalation was mostly UI-driven rather than fully enforced server-side.
4. Malformed PDFs could produce uncontrolled errors.
5. Analyst-to-committee UI flow had gaps.
6. Upload endpoint could trigger paid model calls without abuse protection.
7. Invalid edit values could become server errors.
8. Committee `defer` existed in schema but was initially not fully represented in UI.
9. Audit records were useful but not yet fully structured for production.
10. SQLite was acceptable for demo but not shared production deployment.

### Overall Conclusion
The app was judged to be a good controlled prototype with a strong engineering story:

- LLM extraction
- deterministic scoring
- human review
- workflow events

But production gaps remained around identity, persistence, audit immutability, and abuse controls.

## 2026-09-23 - Reflection Discussion

### Request
The user asked whether reflection could be incorporated, where the model critiques its response and improves the prompt.

### Recommendation
Reflection is possible, but not recommended for the current demo path.

Reasons:
- Increases OpenAI cost.
- Adds latency.
- Complicates auditability.
- Can destabilize outputs.
- Harder to defend than the current clean architecture.

### Decision
The user agreed it is safer not to incorporate reflection for now.

## 2026-09-23 - Six SDLC Stages and AI Use

### Request
Confirm whether AI is used across all six required stages from the challenge page.

### Findings
Reviewed:
- `docs/sdlc/ai-delivery-evidence.md`
- `ai/prompts/sdlc_delivery.md`
- `docs/presentation/evidence-matrix.md`
- requirements, architecture, evals, deployment, and operations docs

### Conclusion
The repository documents AI use across all six stages:

1. Requirements
2. Design
3. Development
4. Testing
5. Deployment
6. Operations

The strongest evidence is in development, testing, requirements, and design. Deployment and operations are present but more documentation-oriented.

## 2026-09-24 - Committee Seed Cases

### Request
Because office OpenAI API calls were blocked, the user wanted demo data inserted directly so committee users could assess cases.

### Actions
Created synthetic committee-review cases directly through `CaseStore`, scoring, policy evidence, analyst acceptance, and committee submission workflow.

### Seeded Cases
Examples included:

```text
CASE-5F78E0E15B - Cross-border instant payments expansion
CASE-D8786F1B13 - Digital wallet onboarding for non-resident customers
CASE-83BEC19271 - Trade finance onboarding in sanctioned-risk corridors
CASE-297636006A - High-value crypto settlement pilot
```

Some cases were later acted on, so additional cases were seeded to maintain multiple visible committee rows.

## 2026-09-24 - Role-Specific Navigation Fix

### Request
When logged in as Analyst, the Committee dashboard link should not appear because clicking it returns:

```json
{"detail": "A committee role is required"}
```

### Actions
Updated:
- `src/app/routers/intake.py`
- `src/app/templates/intake.html`

### Result
The intake page now shows dashboard links based on the logged-in role:

- Product owner sees Product Owner dashboard.
- Analyst sees Analyst dashboard.
- Committee member sees Committee dashboard.
- Anonymous user sees sign-in link.

### Validation
Focused route checks passed. Full tests passed.

## 2026-09-24 - Theme Color Updates

### Request
Change the site theme to a risk/workbench blue palette:

```text
Primary: #005A9C
Secondary: #0078D4
Background: #F5F7FA
Cards: #FFFFFF
Text: #323130
```

Status colors:

```text
Low Risk = Green
Medium Risk = Amber/Yellow
High Risk = Red
Review Needed = Purple
```

### Actions
Updated only `src/app/static/css/style.css`.

### Follow-up
User noted the page still felt too white. Additional blue styling was applied to:

- header
- panel borders
- active process divider
- form accents
- shadows

### Validation
Full tests passed after CSS-only changes.

## 2026-09-24 - Alternating Row Colors

### Request
Multi-row grids should alternate light blue and white, starting with light blue.

### Actions
Updated `src/app/static/css/style.css` to zebra stripe:

- case tables
- score tables
- queue item lists

### Result
Rows now alternate:

```text
light blue, white, light blue, white, ...
```

## 2026-09-24 - Decisioned Case Status Improvement

### Request
Decisioned cases should show the actual committee decision, not only `decisioned`.

### Actions
Updated:
- `src/app/routers/intake.py`
- `src/app/templates/partials/case_table.html`

### Result
Decisioned case status can now show:

- Approved
- Rejected
- Deferred
- Approved with conditions

### Follow-up Request
Add status background colors.

### Actions
Updated:
- `src/app/routers/intake.py`
- `src/app/templates/partials/case_table.html`
- `src/app/static/css/style.css`

### Result
Decision badges now use:

```text
Approved = Green
Rejected = Red
Deferred = Dark Blue
Approved with conditions = Dark Green
```

## 2026-09-24 - Prompt Token Optimization

### Request
Assess and improve the OpenAI extraction prompt for token efficiency.

### Assessment
The original prompt was reliable but had repeated governance prose. It was not proven optimal for token consumption.

### Actions
Updated `ai/prompts/extract_change_request.md` with a shorter v2 prompt that preserved:

- no-invention rule
- explicit products/services/platform capture
- explicit risk factor preservation
- contradiction handling
- pending vendor handling
- country canonicalization
- untrusted document / prompt injection boundary

### Result
Prompt length became approximately 1012 characters.

### Validation
- Prompt loaded successfully.
- Local tests passed.
- Live eval deferred until outside office network.

## 2026-09-24 - Challenge User Types Review

### Request
Review the challenge page and confirm expected user types.

### Findings
The challenge states the workbench serves three groups:

1. Product Owner
2. FCRM Analyst
3. Risk Committee

Optional recommended demo user:

4. System Administrator

### Current Gap
The app schema already had `product_owner` and `administrator`, but only Analyst and Committee were implemented as explicit demo users.

### Recommendation
Add a lightweight Product Owner demo role and workspace.

## 2026-09-24 - Product Owner Role Added

### Request
Add a new Product Owner user.

### Actions
Updated:
- `src/app/services/auth.py`
- `src/app/routers/intake.py`
- `src/app/templates/login.html`
- `src/app/templates/intake.html`

Added:
- `src/app/templates/product_owner_dashboard.html`
- `src/app/templates/product_owner_case.html`

### Demo User

```text
product-owner-1
```

### Role

```text
product_owner
```

### Behavior
Product Owner can:

- sign in,
- upload a case,
- open a Product Owner dashboard,
- track submitted cases,
- view case details and case history.

Product Owner cannot:

- access Analyst dashboard,
- access Committee dashboard,
- assess/edit/finalize cases,
- decide committee cases.

### Validation
Focused route checks passed. Full test suite passed.

## 2026-09-24 - Header Identity Display

### Request
The header should show which user is logged in and the user type.

### Actions
Updated:
- `src/app/templating.py`
- `src/app/templates/base.html`
- `src/app/static/css/style.css`

### Result
Header now shows examples like:

```text
Signed in as product-owner-1 · Product owner
Signed in as analyst-1 · FCRM analyst
Signed in as committee-1 · Risk committee member
```

Anonymous users do not see the identity line.

### Validation
Focused checks passed for all three demo roles. Full test suite passed.

## 2026-09-24 - Hide Header Identity on Switch Role Page

### Request
When clicking **Sign in / switch role**, the current identity line should disappear. This should apply to Product Owner, Analyst, and Committee users.

### Actions
Updated:
- `src/app/templates/base.html`
- `src/app/routers/intake.py`

### Result
The login/switch-role page now hides the header identity line even if a demo user cookie is still present. Normal workbench pages still show the signed-in user and role.

### Validation
Focused checks confirmed:

- login page hides identity for Product Owner, Analyst, and Committee users;
- intake page still shows identity for all three roles;
- full test suite passed.

## 2026-09-24 - Three-Member Committee Voting Matrix

### Request
The user noted that a committee should logically have three members and provided a decision matrix:

```text
Approvals  Rejections  Result
3          0           Approved
2          1           Approved
1          2           Rejected
0          3           Rejected
1          0           Pending
1          1           Pending
2          0           Pending (waiting for 3rd vote)
```

### Actions
Added committee demo users:

```text
committee-1
committee-2
committee-3
```

Updated:
- `src/app/services/auth.py`
- `src/app/services/case_store.py`
- `src/app/routers/intake.py`
- `src/app/templates/login.html`
- `src/app/templates/committee_case.html`
- `src/app/templates/partials/committee_queue.html`
- `tests/test_case_store.py`

### Implementation Details
Added a persisted `committee_votes` table with one vote per committee member per case.

The committee decision flow now:

1. Keeps the case in `committee_review` while fewer than three approve/reject votes are present.
2. Prevents the same committee member from voting twice on the same case.
3. Derives the voting actor from the logged-in committee cookie rather than trusting a hidden form field.
4. Records each vote as a workflow event.
5. Finalizes the case as `decisioned` after the third counted vote.

Voting interpretation:

- `approve` counts as approval.
- `approve_with_conditions` counts as approval and preserves conditions.
- `reject` counts as rejection.
- `defer` remains a decision label for already-decisioned display, but committee voting accepts approve/reject/approve-with-conditions for the current three-vote matrix.

### Result
Committee pages now show:

- vote count summary;
- approvals and rejections;
- number of votes cast out of three;
- pending/approved/rejected result;
- each committee member's vote and rationale.

### Validation
Focused validations confirmed:

- `committee-1`, `committee-2`, and `committee-3` can vote as distinct committee users;
- `approve`, `approve`, `reject` finalizes as Approved;
- duplicate voting by the same committee member is rejected;
- case remains pending with fewer than three counted votes;
- focused case store tests passed: `6 passed`;
- full test suite passed: `24 passed`.

## 2026-09-24 - Failure Handling and Improvement Through Iteration

### Request
The user asked where the challenge requirement **"Failure handling and how the setup improved through iteration"** is implemented in the app.

### Findings
The evidence is split across runtime app code, evaluation tooling, and documentation rather than a single module.

### Runtime Failure Handling
Implemented in:

- `src/app/routers/intake.py`
- `src/app/services/pdf_extraction.py`
- `src/app/services/llm_service.py`
- `src/app/services/case_store.py`

Runtime failures handled include:

- non-PDF uploads returning `415`;
- files over 10 MB returning `413`;
- textless or scanned PDFs returning `422` through `PdfExtractionError`;
- LLM extraction failures returning `502` and logging the failure;
- invalid workflow transitions being rejected;
- duplicate committee votes being rejected;
- committee votes before committee review being rejected.

The LLM service records extraction telemetry for both success and failure, including:

- operation;
- model;
- prompt version;
- latency;
- input and output token counts when available;
- success flag;
- error type.

### Evaluation Failure Handling
Implemented in:

- `evals/run_extraction_eval.py`
- `evals/results/latest.json`

The live evaluation runner:

- runs each synthetic case through the extraction model;
- retries transient model/provider failures up to three times;
- records success or failure per case;
- records error type;
- records latency;
- calculates field accuracy;
- calculates risk-level agreement;
- writes results to `evals/results/latest.json`.

This was the mechanism that surfaced the office-network `APIConnectionError` during testing.

### Improvement Through Iteration
Documented in:

- `ai/prompts/extract_change_request.md`
- `docs/sdlc/ai-delivery-evidence.md`
- `evals/README.md`

Evidence includes:

- prompt version log showing `v1` baseline and `v2` token-compact prompt;
- SDLC failure-to-improvement loop describing how eval results led to prompt, evaluator, and scoring improvements;
- eval documentation explaining how failures should feed back into prompt changes, scoring rule changes, and synthetic case expansion.

### Explanation for Judges
Suggested explanation:

```text
Failure handling is implemented both at runtime and in the SDLC loop. At runtime, bad PDFs, oversized uploads, invalid workflow transitions, duplicate committee votes, and model failures are handled with controlled responses and telemetry. In evaluation, the live runner records per-case failures, latency, field accuracy, and risk agreement. Those results feed into prompt and scoring-rule iteration, which is documented in the prompt version log and SDLC evidence file.
```

### Remaining Gaps
Known gaps identified:

- no UI dashboard yet for telemetry or failure rates;
- no automatic alerting yet;
- no OCR fallback for scanned PDFs;
- model-provider retry exists in the eval runner but not in the main upload route;
- failure-to-improvement is documented and partially implemented, but it is not a fully automated feedback pipeline.

## Current Demo Roles

```text
product-owner-1     Product owner
analyst-1           FCRM analyst
committee-1         Risk committee member
committee-2         Risk committee member
committee-3         Risk committee member
```

## Current Known Office Limitation

OpenAI live extraction cannot be tested reliably from the office network due to Python TLS certificate verification failure caused by a self-signed certificate in the chain. This is an office network / proxy trust issue, not an application logic failure.

Working around this safely requires either:

- testing from home/mobile network, or
- having IT provide the approved corporate root CA and configuring Python/httpx to trust it.

Do not disable TLS verification.

## Commands Commonly Used

Run locally without activation:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.app.main:app --reload --port 8000
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run live evaluation outside office network:

```powershell
.\.venv\Scripts\python.exe evals\run_extraction_eval.py
```

## Documentation Notes

This file captures the office chat and development decisions. A separate file should be created later for home-session chat history, for example:

```text
chats/chats_home.md
```
