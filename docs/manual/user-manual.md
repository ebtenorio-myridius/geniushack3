# Risk Assessment Workbench User Manual

## 1. Purpose

The Risk Assessment Workbench helps you submit a change request, review the extracted information, understand the draft financial-crime risk score, and record a human review or committee decision.

The system prepares evidence. It does not make an automatic approval or rejection decision.

## 2. What You Need

Before using the app, make sure:

- the application is running at `http://localhost:8000`;
- the model provider is configured if live extraction is enabled;
- you are using synthetic data only;
- your input is a text-based PDF;
- the PDF is no larger than 10 MB.

Scanned image-only PDFs are not supported by the current text extraction path.

## 3. User Roles

Open `http://localhost:8000/intake/login` to select a demo role. Enter a user
name and choose either **FCRM analyst** or **Risk committee member**. The app
stores the selected demo identity in local cookies and redirects you to the
matching workspace.

Use **Sign in / switch role** in the header to change roles. Select logout by
posting to `/intake/logout` when resetting the demo session.

### Product owner

Use the intake page to submit a change request PDF.

### FCRM analyst

Review the extracted fields, edit incorrect information, rescore the case, and accept or reject the assessment draft.

For the local demo, analyst access is represented by:

```text
X-Demo-User: analyst-1
X-Demo-Role: analyst
```

These headers are for demonstration only and are not production authentication.

### Risk committee member

Review escalated cases and record a decision.

For the local demo, committee access is represented by:

```text
X-Demo-User: committee-1
X-Demo-Role: committee
```

## 4. Submit a Change Request

1. Open `http://localhost:8000`.
2. Select a PDF change request.
3. Select **Submit for extraction**.
4. Wait while the system reads the document and drafts the extraction.

The system performs these steps:

```text
PDF
-> text extraction
-> structured JSON extraction
-> deterministic risk scoring
-> case persistence
```

## 5. Role Workspaces

For the local demo, the workspaces are available from the intake page or by
opening these URLs:

- Analyst workspace: `http://localhost:8000/intake/analyst/dashboard/demo`
- Committee workspace: `http://localhost:8000/intake/committee/dashboard/demo`

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
- related synthetic policy evidence.

Treat the extraction and score as a draft. Check every important field against the source PDF.

## 6. Edit and Rescore

If the extraction is incomplete or incorrect:

1. Edit the fields in **Edit extraction and rescore**.
2. Enter the analyst identity.
3. Enter a rationale explaining the correction.
4. Select **Save edit and rescore**.

The system:

- validates the edited fields;
- creates a new extraction version;
- recalculates the deterministic score;
- refreshes the policy evidence; and
- records the edit as an audit event.

The original model extraction is retained. Do not use the edit form to invent facts that are not supported by the PDF.

## 7. Accept or Reject the Draft

To finalize the analyst review:

1. Enter the analyst identity.
2. Enter a rationale.
3. Select **Accept draft** or **Reject draft**.

An accepted case moves to analyst-finalized status. A rejected case records the rejection and rationale.

A rationale should explain what was checked and why the decision is appropriate. For example:

```text
The extracted fields were checked against the synthetic source PDF. The geography, product, and stated risk factors are supported by the document.
```

## 8. Low- and Medium-Risk Workflow

Use this path when the draft assessment does not require committee review.

Use one of these sample files:

- Low risk: `evals/data/pdfs/SYN-001.pdf` - online banking dashboard accessibility refresh.
- Medium risk: `evals/data/pdfs/SYN-004.pdf` - vendor onboarding for document digitization.

1. Upload the PDF.
2. Review the extracted fields, score, rationales, and policy evidence.
3. Edit and rescore if any extracted value is incomplete or incorrect.
4. Enter the analyst identity and review rationale.
5. Select **Accept draft**.

The case moves to:

```text
Draft
-> Analyst review
-> Analyst finalized
```

The case is not automatically approved or rejected. The analyst's finalization and rationale are recorded in SQLite as an audit event.

If the analyst does not support the assessment, select **Reject draft** instead. The case moves to `analyst_rejected` and the rejection rationale is retained.

## 9. High- and Critical-Risk Workflow

Use this path when the draft is flagged for committee review.

Use one of these sample files:

- Critical risk: `evals/data/pdfs/SYN-003.pdf` - cross-border remittance product with vendor and sanctions exposure.
- High risk: `evals/data/pdfs/SYN-008.pdf` - new invoice-financing product across multiple channels.

1. Upload the PDF.
2. Review the extraction, score, rationales, and policy evidence.
3. Edit and rescore if needed.
4. Select **Accept draft** and finalize the analyst review.
5. Enter the escalation rationale in **Submit to committee**.
6. Select **Submit committee review**.
7. A committee member opens the committee queue.
8. Review the finalized assessment and analyst rationale.
9. Select one committee decision:
	- **Approve**
	- **Reject**
	- **Defer**
	- **Approve with conditions**
10. Enter the committee identity, rationale, and conditions when applicable.

The case moves to:

```text
Draft
-> Analyst review
-> Analyst finalized
-> Committee review
-> Decisioned
```

The committee decision, rationale, conditions, actor, and timestamp are recorded as workflow evidence. The system does not decide on behalf of the committee.

For the local demo, use:

```text
X-Demo-User: analyst-1
X-Demo-Role: analyst
```

for analyst actions, and:

```text
X-Demo-User: committee-1
X-Demo-Role: committee
```

for committee actions. These headers are demonstration-only authentication.

## 10. Workflow States

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

## 11. Risk Score Interpretation

The current prototype uses four deterministic categories:

- Customer and geography: 35%
- Product and channel: 30%
- Third party/vendor: 20%
- Change complexity: 15%

Each category receives a score from 1 to 5 with a rationale. The weighted result produces a low, medium, high, or critical risk level.

The current rules are prototype rules. They must be governed and approved by the risk function before production use.

Controls reduce risk; they do not eliminate it. The prototype does not yet calculate a complete residual-risk assessment.

## 12. Policy Evidence

The result may show synthetic policy evidence related to:

- products and channels;
- customer segments and geography; or
- vendor involvement.

Each evidence item includes a policy identifier, section, excerpt, relevance statement, and repository source path.

The current policy documents are synthetic demonstration material. They are not regulatory advice and must not replace approved supervisory-framework guidance.

## 13. Auditability

The app records workflow events for:

- case creation;
- extraction edits;
- analyst review;
- committee submission; and
- committee decision.

Events include an actor, rationale, and timestamp. Extraction versions preserve the original model output and later analyst edits.

## 14. Handling Errors

### Non-PDF upload

Only PDFs are accepted. Select a PDF and try again.

### File too large

The current upload limit is 10 MB.

### No extractable text

The PDF may be scanned or image-only. Use a text-layer PDF for the current demo.

### Model extraction failure

Check that the model provider configuration is available and retry. The source PDF remains a draft input until a valid structured extraction is produced.

### Unauthorized action

Use the correct demo role for the action. In production, the demo headers must be replaced by real authentication.

## 15. Recommended Demo Walkthrough

Use `evals/data/pdfs/SYN-001.pdf` for a simple case or a higher-risk PDF such as `SYN-003.pdf` or `SYN-008.pdf`.

1. Submit the PDF.
2. Show the extracted JSON-compatible fields.
3. Explain the category scores and rationales.
4. Show policy evidence.
5. Edit one field and explain the correction.
6. Rescore the case.
7. Accept and finalize the analyst review.
8. Submit a high-risk case to committee review.
9. Record a conditional committee decision.
10. Explain the audit events and extraction version.

## 16. Important Limitations

This is a synthetic-data demonstration and prototype. It does not currently provide:

- production authentication;
- multi-member committee quorum;
- full residual-risk and control-effectiveness scoring;
- production PostgreSQL persistence;
- object storage for uploaded documents;
- malware scanning;
- OCR for scanned PDFs; or
- production dashboards and alerting.

Do not upload real customer, account, transaction, employee, or banking documents.
