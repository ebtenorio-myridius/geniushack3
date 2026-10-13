# Live Demo Script

## Preparation

- Start the application with `uvicorn src.app.main:app --reload --port 8000`.
- Open `http://127.0.0.1:8000/`.
- Use `evals/data/sample_change_request.pdf` and confirm `OPENAI_API_KEY` is
  configured. Live extraction has no offline fallback.
- The login form starts blank. Enter a supported username and explicitly
  select its matching role: `product-owner-1`, `analyst-1`, or
  `committee-1`, `committee-2`, `committee-3`.
- Keep the synthetic fixtures and the latest evaluation report available as
  fallback evidence.
- To demonstrate closure, use a case whose committee vote includes an
  approval with conditions and provide an owner and due date.

## Walkthrough

1. **Owner sign-in and upload:** sign in as `product-owner-1` with the Product
   owner role. Upload the sample PDF from the Product Owner dashboard.
2. **Extraction and draft:** show the structured fields, page-quote
   citations, deterministic score and rationales, synthetic policy evidence,
   case ID, and draft status. Explain that the source PDF and extracted page
   text are retained with integrity hashes.
3. **Owner submission:** check required title, business unit, and description.
   If needed, correct the draft with source citations and a rationale. Submit
   the complete case for analyst review.
4. **Analyst review:** use **Sign in / switch role**, explicitly select FCRM
   analyst, and sign in as `analyst-1`. Verify the fields against the source;
   edit/rescore with citations and rationale when needed, then finalize the
   assessment and submit it to the committee. This analyst-first path applies
   to every risk level.
5. **Committee decision:** switch among `committee-1`, `committee-2`, and
   `committee-3` and cast three distinct votes. Two approvals approve, two
   rejections reject, and no majority defers. The vote rule is prototype
   configuration, not approved institutional policy.
6. **Conditional closure (recommended end-to-end path):** include an
   approve-with-conditions vote, assign each condition to the product owner,
   and set a due date. After the final committee outcome, switch to the owner
   to record evidence for every condition, then switch back to the analyst
   and close the case. Without open conditions, the analyst can close a
   decisioned case directly.
7. **Audit and export:** show the versions, rationale-bearing workflow
   events, source-document integrity details, and cycle-time view. Download
   the examiner export and point out its case record, retained source,
   verification result, and file-hash manifest. The hash chain is verifiable
   but not immutable against a database owner.

## Optional branch: request information

During analyst review, or during committee review before any committee vote,
request information with a rationale. Switch to the submitting product owner
and respond. The case resumes at the review stage it was in before the
request. Committee cannot request information after voting has started.

## Optional branch: reassessment

From a decisioned, conditions-pending, or closed case, an analyst can create a
linked reassessment. It reuses the prior request/source as a starting point
and returns to analyst review; it does not alter the earlier committee
outcome.

## Fallback demonstration

If the live extraction call is unavailable:

- Do not imply extraction has an offline fallback. Show the explicit
  provider-failure behavior instead.
- Show `evals/results/latest.md` and explain the result in `latest.json`:
  eight synthetic PDF cases, 80/80 fields correct, 100% risk-level agreement,
  and 3,615 ms mean latency for the 2026-10-02 run. This is a small synthetic
  sample, not a production accuracy or latency estimate.
- Show `evals/data/synthetic_cases.json` and
  `tests/test_synthetic_cases.py`; run the relevant local tests if time
  permits.
- Explain that deterministic scoring, persistence, workflow transitions,
  evidence validation, audit verification, and policy rule fallback are
  locally testable even when model extraction is not.

## Questions to expect

**Why use AI here?**

PDF submissions are unstructured and vary by author. Extraction benefits
from language understanding; scoring and workflow transitions need
reproducibility.

**What prevents the model from approving a case?**

The model returns structured extraction only. A product owner submits the
draft, an analyst verifies and finalizes the assessment, and committee members
record the final decision through separate workflow steps.

**Is this production-ready?**

It is a synthetic-data prototype with role-gated demo workspaces, not
production identity. Production still needs real authentication and hardened
authorization, approved policy/scoring/decision rules, migrations and
backups, protected source retention, residual-risk controls, and an audit
anchor outside the database owner’s control.

**How do you know the model is good?**

The repository has hand-labeled synthetic cases, source-evidence checks, and
workflow tests. The latest recorded PDF evaluation completed 8/8 calls with
80/80 fields correct and 8/8 risk-level agreement. That small synthetic
sample does not establish production reliability; field accuracy and risk
agreement are different measures.
