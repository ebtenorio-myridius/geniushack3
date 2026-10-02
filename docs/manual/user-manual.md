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
Owner dashboard to open `/intake`. Product owners can track submitted cases and
open read-only case details from that dashboard.

### FCRM analyst

The extraction result contains inline forms to edit/rescore and accept/reject
the draft. Analyst case-detail pages reached later from the dashboard are
read-only; review actions are not available there. The inline forms include a
fixed demo analyst header and an editable actor field, so they do not provide a
secure or authenticated role boundary.

### Risk committee member

After signing in as a committee member, select **Cases to review** from the
Committee dashboard. Three distinct committee demo identities must vote before
the case is finalized. Use **Sign in / switch role** to change identities
between votes.

## 4. Submit a Change Request

1. Open `http://127.0.0.1:8000/`.
2. For the product-owner submission flow, sign in as `product-owner-1` and explicitly select **Product owner**.
3. From the Product Owner dashboard, select **Upload case**. Signed-out or invalid sessions at `/intake` are redirected to login.
4. Select a PDF change request and select **Submit for extraction**.
5. Wait while the system reads the document and drafts the extraction.

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

The Product Owner workspace shows submitted cases and read-only case details.
It is used to raise and track change requests.

The analyst workspace shows every submitted case, regardless of risk level. It
also links to cases already decisioned and to cases waiting for committee
review. The analyst can return to the intake page to upload another PDF.

The committee workspace shows cases currently waiting for committee review. A
separate **Decisioned cases** link provides completed decisions for reference.

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

Use the **Edit extraction and rescore** form in the extraction result while it
is still open. Analyst case-detail pages reached later from the dashboard are
read-only.

If the extraction is incomplete or incorrect:

1. Edit the fields in **Edit extraction and rescore**.
2. Enter the actor name to record with this edit.
3. Enter a rationale explaining the correction.
4. Select **Save edit and rescore**.

The system:

- validates the edited fields;
- creates a new extraction version;
- recalculates the deterministic score;
- refreshes the policy evidence; and
- records the edit as an audit event.

The original model extraction is retained. Do not use the edit form to invent
facts that are not supported by the PDF. The inline form currently supplies a
fixed demo analyst header; the actor field is not proof of a real authenticated
identity.

## 8. Accept or Reject the Draft

To review an open case, sign in as an FCRM analyst and open it from the Analyst
dashboard. Draft and analyst-review cases provide a review form on the case
detail page. After extraction, the upload result also provides the same review
actions.

To finalize the analyst review:

1. Enter a rationale.
2. Select **Finalize assessment** or **Reject draft**.

An accepted case moves to analyst-finalized status. A rejected case records the
rejection and rationale. On the analyst case-detail route, the event actor is
the signed-in demo analyst. This demo identity is not production authentication.
The upload result's inline forms remain demo-only and should not be treated as a
security boundary.

A rationale should explain what was checked and why the decision is appropriate. For example:

```text
The extracted fields were checked against the synthetic source PDF. The geography, product, and stated risk factors are supported by the document.
```

## 9. Low- and Medium-Risk Workflow

Use this path when the draft assessment does not require committee review.

Use one of these sample files:

- Low risk: `evals/data/pdfs/SYN-001.pdf` - online banking dashboard accessibility refresh.
- Medium risk: `evals/data/pdfs/SYN-004.pdf` - vendor onboarding for document digitization.

1. Sign in as the product owner and upload the PDF from `/intake`, or open an existing draft from the analyst dashboard.
2. Sign in as `analyst-1` with the FCRM analyst role and open the case detail.
3. Review the extracted fields, score, rationales, and policy evidence.
4. Enter a review rationale and select **Finalize assessment**.

The case moves to:

```text
Draft
-> Analyst review
-> Analyst finalized
```

The case is not automatically approved or rejected. The analyst action and
rationale are recorded in SQLite as a workflow event.

If the analyst does not support the assessment, select **Reject draft** instead. The case moves to `analyst_rejected` and the rejection rationale is retained.

## 10. High- and Critical-Risk Workflow

Use this path when the draft is flagged for committee review.

Use one of these sample files:

- Critical risk: `evals/data/pdfs/SYN-003.pdf` - cross-border remittance product with vendor and sanctions exposure.
- High risk: `evals/data/pdfs/SYN-008.pdf` - new invoice-financing product across multiple channels.

1. Sign in as the product owner and upload the PDF, or open an existing draft from the analyst dashboard.
2. Sign in as `analyst-1` with the FCRM analyst role and open the case detail.
3. Review the extraction, score, rationales, and policy evidence; edit and rescore if needed.
4. Finalize the analyst review with a rationale.
5. Enter the escalation rationale and select **Submit to committee**.
6. A committee member signs in and opens **Cases to review** from the Committee dashboard.
7. Review the finalized assessment and analyst rationale.
8. Each committee member signs in separately and casts one vote:
   - **Approve**
   - **Reject**
   - **Defer**
   - **Approve with conditions**
9. Enter the committee rationale and conditions when applicable.
10. Repeat with `committee-1`, `committee-2`, and `committee-3` until three votes are recorded.

The case remains pending until three distinct votes are recorded. After the
third vote, two or more approvals (including **Approve with conditions**)
produce approval; two or more rejections produce rejection; otherwise the
result is deferred. This is prototype behavior, not an institutionally
approved decision policy.

The case moves to:

```text
Draft
-> Analyst review
-> Analyst finalized
-> Committee review
-> Decisioned
```

Each vote's rationale, conditions, demo actor, and timestamp are recorded as
workflow evidence. The final result follows the prototype vote-count rule; it
is not an independently governed policy decision.

Committee pages show the vote count, the pending or final result, and each
committee member's vote and rationale. A committee member can vote only once on
the same case.

Decisioned case lists show the specific final result rather than only the
workflow status. The visible outcomes are:

- **Approved**;
- **Rejected**; or
- **Approved with conditions**.

Use the login form to sign in separately as `committee-1`, `committee-2`, and
`committee-3` for the three votes. The demo queue URL is a browser convenience,
not an authorization boundary; use only synthetic data.

## 11. Workflow States

A case moves through the following states:

```text
Draft
-> Analyst review
-> Analyst finalized
-> Committee review
-> Decisioned
```

A case may also be rejected during analyst review.

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
users to login, but endpoint authorization is inconsistent: the PDF upload
POST is not role-gated, the inline analyst forms use a fixed demo header, and
the demo committee queue route is not role-gated. These are prototype
limitations, not security controls. Do not use real data.

## 16. Recommended Demo Walkthrough

Use `evals/data/pdfs/SYN-001.pdf` for a simple case or a higher-risk PDF such as `SYN-003.pdf` or `SYN-008.pdf`.

1. Sign in as `product-owner-1` with the Product owner role.
2. Open **Upload case** and submit the PDF.
3. Show the extracted fields, category scores, rationales, policy evidence if present, case ID, and draft status.
4. Use the inline edit/review forms to demonstrate correction and analyst finalization; explain that these forms use a fixed demo analyst header and are not a real role boundary.
5. For a high/critical case, submit it to committee review.
6. Sign in as `committee-1`, cast the first vote, and show the case is pending.
7. Repeat with `committee-2` and `committee-3`; after the third vote show the prototype rule's result.
8. Explain the vote history, application-level workflow events, and extraction versions, including their non-production audit limitations.

## 17. Important Limitations

This is a synthetic-data demonstration and prototype. It does not currently provide:

- production authentication or consistent endpoint authorization;
- secure separation between product-owner and analyst actions in the inline result forms;
- database-enforced, tamper-proof audit storage;
- an institutionally approved committee decision policy;
- full residual-risk and control-effectiveness scoring;
- production PostgreSQL persistence;
- object storage for uploaded documents;
- malware scanning;
- OCR for scanned PDFs; or
- production dashboards and alerting.

Do not upload real customer, account, transaction, employee, or banking documents.
