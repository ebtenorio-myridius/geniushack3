# Risk Assessment Workbench User Manual

## 1. Purpose

The Risk Assessment Workbench helps you submit a change request, review the extracted information, understand the draft financial-crime risk score, and record a human review or committee decision.

The system prepares evidence. It does not make an automatic approval or rejection decision.

## 2. What You Need

Before using the app, make sure:

- the application is running at `http://127.0.0.1:8000`;
- an OpenAI API key is configured for live PDF extraction;
- you are using synthetic data only;
- your input is a text-based PDF;
- the PDF is no larger than 10 MB.

Scanned image-only PDFs are not supported by the current text extraction path.
Policy evidence may fall back to deterministic rules; extraction has no offline
fallback.

## 3. User Roles

Open `http://127.0.0.1:8000/`. A signed-out browser is sent to login; a signed-in
browser is sent to its role dashboard. The login form starts with the username
and role blank. Enter a username and explicitly select **Product owner**,
**FCRM analyst**, or **Risk committee member**. Selecting a role does not fill
the username. A successful login stores the demo identity in browser cookies
and opens the matching workspace.

Recommended demo usernames are:

```text
Product owner: product-owner-1
Analyst: analyst-1
Committee members: committee-1, committee-2, committee-3
```

These are the supported demo identities. The app checks the username-role
pair before creating the demo session:

- `product-owner-1` can sign in only as a product owner;
- `analyst-1` can sign in only as an FCRM analyst;
- `committee-1`, `committee-2`, and `committee-3` can sign in only as risk committee members.

A mismatched username and role is rejected. These are demo identities, not
production accounts.

Use **Sign in / switch role** in the header to end the current demo session.
That link clears the app's `demo_user` and `demo_role` cookies and opens login.
Enter the username and select the role again. Other workbench pages show the
current user and role in the header, for example:

```text
Signed in as analyst-1 · FCRM analyst
```

The login page does not display the previous identity while switching roles.

### Product owner

After signing in as `product-owner-1`, select **Upload case** from the Product
Owner dashboard to open `/intake`. The extraction result is a draft. Check the
required title, business unit, and description, then submit the case to the
review queue indicated by its draft risk: low/medium-risk cases go to an
analyst; high/critical-risk cases go directly to the committee. The product
owner dashboard tracks owned cases, their next action, and elapsed waiting
days. Product owners can respond to analyst or committee information requests
and provide completion evidence for assigned decision conditions.

### FCRM analyst

The analyst dashboard contains low/medium-risk cases submitted for analyst
review and cases paused for product-owner information. Open a case to verify
the extracted fields and score, edit and rescore with a rationale, finalize or
reject, or request additional information. Finalizing an accepted low/medium
case makes it eligible for closure by an analyst; it does not automatically
close the case. Analysts can also submit a finalized case to committee review
when escalation is needed. Analyst actions use the signed-in demo identity.
The dashboard also links to committee cases and completed decisions.

### Risk committee member

After signing in as a committee member, select **Cases to review** from the
Committee dashboard. The committee packet includes the current assessment, policy evidence,
extraction-version changes, and vote status. A high/critical case submitted
directly by its product owner has not had analyst verification; committee
members are prompted to verify its extracted facts and score. For cases that
were reviewed by an analyst, the packet also includes the analyst rationale.
Before voting starts, the committee may pause review and request information
from the product owner. Three distinct committee demo identities must vote
before a final outcome is recorded. Use **Sign in / switch role** to change
identities between votes.

## 4. Submit a Change Request

1. Open `http://127.0.0.1:8000/`.
2. For the product-owner submission flow, sign in as `product-owner-1` and explicitly select **Product owner**.
3. From the Product Owner dashboard, select **Upload case**. Signed-out or invalid sessions at `/intake` are redirected to login.
4. Select a PDF change request and select **Submit for extraction**.
5. Wait while the system reads the document and drafts the extraction.
6. Check the draft fields and select the submit button for the review queue
   shown for its risk level: low/medium goes to analyst review; high/critical
   goes directly to committee review. A request with a blank title, business
   unit, or description cannot be submitted.

The system performs these steps:

```text
PDF
-> text extraction
-> structured JSON extraction
-> deterministic risk scoring
-> case persistence
```

## 5. Role Workspaces

After signing in with a matching demo role, open the corresponding dashboard
or list:

- Analyst workspace: `http://127.0.0.1:8000/intake/analyst/dashboard/demo`
- Product Owner workspace: `http://127.0.0.1:8000/intake/product-owner/dashboard/demo`
- Committee workspace: `http://127.0.0.1:8000/intake/committee/dashboard/demo`
- Analyst decisioned cases: `http://127.0.0.1:8000/intake/analyst/decisioned`
- Committee decisioned cases: `http://127.0.0.1:8000/intake/committee/decisioned`
- Committee review queue: open **Cases to review** from the Committee dashboard. The underlying `/intake/committee-queue/demo` URL is a demo convenience and is not itself role-gated.

The Product Owner workspace shows cases submitted by the signed-in demo owner,
including drafts, cases waiting on a response, committee outcomes, and
conditions awaiting evidence.

The analyst workspace shows active analyst reviews and cases waiting on the
product owner. Separate lists link to cases awaiting committee review and
decisioned, condition-tracking, or closed cases. Queue rows show the request
owner, assigned analyst, next action, and elapsed days since the last update.

The committee workspace shows cases currently waiting for committee review. A
separate **Decisioned cases** link provides completed decisions for reference.
The committee's browser-friendly queue URL is also role-gated.

These are browser-friendly demo workspaces. Production use requires real login,
role-based authorization, and authenticated actors.

## 6. Review the Draft

After processing, the page displays:

- case title;
- source filename;
- case ID;
- extracted change type;
- business unit;
- description;
- geographies;
- customer segments;
- vendor information;
- products;
- stated risk factors;
- extraction confidence;
- category risk scores;
- score rationales;
- overall risk level;
- committee-review flag; and
- related synthetic policy evidence, when any evidence is returned.

Treat the extraction and score as a draft. Check every important field against the source PDF.

## 7. Edit and Rescore

Open a submitted case from the analyst dashboard. Editing and rescoring are
available while the case is in analyst review.

If the extraction is incomplete or incorrect:

1. Edit the extracted fields in the analyst case workspace.
2. Enter a rationale explaining the correction.
3. Save the edit and rescore.

The system:

- validates the edited fields;
- creates a new extraction version;
- recalculates the deterministic score;
- refreshes the policy evidence; and
- records the edit as an audit event.

The original model extraction is retained. The review packet shows version
history, changed fields, editor, and rationale. Do not enter facts that are not
supported by the source. Demo identities are not production authentication.

## 8. Accept or Reject the Draft

To review a case, sign in as an FCRM analyst and open a submitted case from the
Analyst dashboard. Drafts do not enter the review queue until the product
owner explicitly submits them.

To finalize the analyst review:

1. Enter a rationale.
2. Select **Finalize assessment** or **Reject draft**.

An accepted case moves to analyst-finalized status. A rejected case records the
rejection and rationale. The event actor is the signed-in demo analyst.

If information is missing, use **Request more information** and state exactly
what the product owner must provide. The case pauses in `needs_information`;
only its submitting product owner can respond. The response is recorded in the
case history and restores the review stage that requested it.

A rationale should explain what was checked and why the decision is appropriate. For example:

```text
The extracted fields were checked against the synthetic source PDF. The geography, product, and stated risk factors are supported by the document.
```

## 9. Low- and Medium-Risk Workflow

Use this path when the draft assessment is low or medium risk and does not
require committee review.

Use one of these sample files:

- Low risk: `evals/data/pdfs/SYN-001.pdf` - online banking dashboard accessibility refresh.
- Medium risk: `evals/data/pdfs/SYN-004.pdf` - vendor onboarding for document digitization.

1. Sign in as the product owner, upload the PDF from `/intake`, check the extraction, and submit it for analyst review.
2. Sign in as `analyst-1` with the FCRM analyst role and open the case detail.
3. Review the extracted fields, score, rationales, and policy evidence.
4. Enter a review rationale and select **Finalize assessment**.
5. Close the case with a closure rationale once analyst work is complete.

The case moves to:

```text
Draft
-> Product owner submission
-> Analyst review
-> Analyst finalized
-> Closed
```

Analyst finalization records the assessment and rationale; it does not close
the case automatically. An analyst closes the case separately with a closure
rationale. The analyst action and rationale are recorded in SQLite as a
workflow event.

If the analyst does not support the assessment, select **Reject draft** instead. The case moves to `analyst_rejected` and the rejection rationale is retained.

## 10. High- and Critical-Risk Workflow

Use this path when the draft is high or critical risk and is flagged for
committee review.

Use one of these sample files:

- Critical risk: `evals/data/pdfs/SYN-003.pdf` - cross-border remittance product with vendor and sanctions exposure.
- High risk: `evals/data/pdfs/SYN-008.pdf` - new invoice-financing product across multiple channels.

1. Sign in as the product owner, upload the PDF, check the extraction, and select **Submit for committee review**.
2. The case appears in the committee queue without analyst verification. The committee is prompted to verify the extracted facts and score.
3. A committee member signs in and opens **Cases to review** from the Committee dashboard.
4. Review the assessment, policy evidence, extraction changes, and vote status. Before any vote is cast, the committee may request information and pause the review.
5. Each committee member signs in separately and casts one vote:
   - **Approve**
   - **Reject**
   - **Defer**
   - **Approve with conditions**
6. Enter the committee rationale. For conditions, enter one condition per line, its owner, and due date.
7. Repeat with `committee-1`, `committee-2`, and `committee-3` until three votes are recorded.

The case remains pending until three distinct votes are recorded. After the third vote, two or more approvals (including **Approve with conditions**)
produce approval; two or more rejections produce rejection; otherwise the
result is deferred. This is prototype behavior, not an institutionally
approved decision policy.

The case moves to:

```text
Draft
-> Product owner submission
-> Committee review (high/critical risk; no analyst verification)
-> Decisioned or conditions pending
-> Closed
```

Analyst escalation is also available for a case that has completed analyst
review and was finalized for committee review. This is separate from the
direct-to-committee path for high/critical cases submitted by the product
owner.

After the committee vote, the case has a recorded approved, rejected, deferred,
or approved-with-conditions outcome. A committee outcome does not close the
case automatically: an analyst closes it separately. For approval with
conditions, the product owner supplies completion evidence and open conditions
must be completed before closure.

Each vote's rationale, conditions, demo actor, and timestamp are recorded as
workflow evidence. The final result follows the prototype vote-count rule; it
is not an independently governed policy decision.

Committee pages show the vote count, the pending or final result, and each
committee member's vote and rationale. A committee member can vote only once on
the same case.

An approval with conditions creates tracked follow-up items. In this demo, the
submitting product owner owns the conditions, provides a due date, and submits
completion evidence. Open items block case closure; overdue items are flagged.
An analyst closes the case after all conditions are complete. Cases with a
recorded outcome can be reassessed by an analyst; a reassessment is linked to
the earlier case and does not overwrite its decision.

Queue rows show elapsed calendar days since the last case update. No case-stage
service-level targets are configured, so case age is not labeled overdue.

Decisioned case lists show the specific final result rather than only the
workflow status. The visible outcomes are:

- **Approved**;
- **Rejected**; or
- **Deferred**; or
- **Approved with conditions**.

Use the login form to sign in separately as `committee-1`, `committee-2`, and
`committee-3` for the three votes. The demo queue URL is a browser convenience,
and requires a valid committee demo session. Use only synthetic data.

## 11. Workflow States

A case moves through the following states:

```text
Draft
-> Product-owner submission
   -> Low/medium risk: Analyst review
      -> Analyst finalized -> Closed (analyst closes separately)
      -> Analyst rejected
      -> Committee review (optional analyst escalation after finalization)
   -> High/critical risk: Committee review (direct; not analyst-verified)
-> Needs information (optional; returns to the stage that requested it)
-> Committee review
   -> Decisioned (approved, rejected, or deferred) -> Closed (analyst closes separately)
   -> Conditions pending (product owner supplies evidence) -> Closed
```

A case may be rejected during analyst review. Analyst-finalized low/medium-risk
cases may be closed without a committee decision. A committee decision requires
the configured number of distinct member votes; the current demo rules require
three votes and a two-vote majority for approval or rejection. A closed or
decisioned case may be reassessed; the new case links to the previous case.

Invalid transitions are refused. For example, a case cannot be sent to the committee before analyst finalization.

## 12. Risk Score Interpretation

The current prototype uses four deterministic categories:

- Customer and geography: 35%
- Product and channel: 30%
- Third party/vendor: 20%
- Change complexity: 15%

Each category receives a score from 1 to 5 with a rationale. The weighted result produces a low, medium, high, or critical risk level.

The current rules are prototype rules. They must be governed and approved by the risk function before production use.

Controls reduce risk; they do not eliminate it. The prototype does not yet calculate a complete residual-risk assessment.

## 13. Policy Evidence

The result may show synthetic policy evidence related to:

- products and channels;
- customer segments and geography; or
- vendor involvement.

Each evidence item includes a policy identifier, section, excerpt, relevance statement, and repository source path.

The current policy documents are synthetic demonstration material. They are not regulatory advice and must not replace approved supervisory-framework guidance.

## 14. Auditability

The app records workflow events for:

- case creation;
- extraction edits;
- analyst review;
- committee submission;
- committee votes; and
- committee final decision.

Events include an actor value, rationale, and UTC timestamp. Extraction
versions preserve the original model output and later analyst edits. Event
history is append-only through application behavior, not database-enforced
tamper-proof storage; entered actor values are not equivalent to verified
identity.

## 15. Handling Errors

### Non-PDF upload

Only PDFs are accepted. Select a PDF and try again.

### File too large

The current upload limit is 10 MB.

### No extractable text

The PDF may be scanned or image-only. Use a text-layer PDF for the current demo.

### Model extraction failure

Check that the OpenAI provider configuration is available and retry the upload.
The app does not create a case or store the source PDF when extraction fails.

### Unauthorized action

Sign in with a supported username/role pair. `/intake` redirects signed-out
users to login. Workflow endpoints check the signed-in demo username and role,
but those demo cookies are not production authentication or security controls.
Do not use real data.

## 16. Recommended Demo Walkthrough

Use `evals/data/pdfs/SYN-001.pdf` for a simple case or a higher-risk PDF such as `SYN-003.pdf` or `SYN-008.pdf`.

1. Sign in as `product-owner-1` with the Product owner role.
2. Open **Upload case** and submit the PDF.
3. Show the extracted fields, category scores, policy evidence if present, case ID, and draft status.
4. Explicitly submit the request to the risk-appropriate queue: analyst for low/medium or committee for high/critical.
5. For a low/medium case, open the analyst workspace and demonstrate analyst review, finalization, and separate closure. For a high/critical case, open the committee workspace and verify the extracted facts and score.
6. For a high/critical case, sign in as committee members and cast three votes; optionally approve with conditions and capture an owner and due date.
7. Complete any conditions with product-owner evidence, then close the case as an analyst; alternatively, create a linked reassessment.
8. Explain the workflow history, vote rule, and the prototype's non-production audit limitations.

## 17. Important Limitations

This is a synthetic-data demonstration and prototype. It does not currently provide:

- production authentication or consistent endpoint authorization;
- institution-managed user and role administration;
- database-enforced, tamper-proof audit storage;
- an institutionally approved committee decision policy;
- full residual-risk and control-effectiveness scoring;
- production PostgreSQL persistence;
- object storage for uploaded documents;
- malware scanning;
- OCR for scanned PDFs; or
- production dashboards and alerting.

The demo queues show elapsed days but do not yet apply case-stage SLAs. A
reassessment copies the prior extracted facts as a starting point; analysts
must update them with evidence for the changed initiative.

Do not upload real customer, account, transaction, employee, or banking documents.
