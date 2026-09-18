# AI-Assisted SDLC Guidance

These prompts are the reusable delivery instructions for the six hackathon stages. Each run must save the AI output, human edits, decision owner, date, and resulting repository artifact. AI proposes; the team reviews and owns the decision.

## Stage 01 - Requirements

```text
Given the Genius Hacks Risk Assessment Workbench brief, expand it into personas,
workflow states, acceptance criteria, assumptions, risks, non-functional
requirements, and open questions. Separate facts from assumptions. Identify
which questions require domain-owner approval. Do not invent supervisory rules.
```

Human gate: FCRM owner approves the expanded specification and open-question decisions.

## Stage 02 - Design

```text
Given the approved requirements, propose two architectures and compare them for
traceability, human control, synthetic-data safety, cost, reliability, and
operability. Produce a data model, state machine, API boundaries, UX flow, and
failure modes. Recommend one option and explain rejected alternatives.
```

Human gate: engineering and risk owners approve the architecture decision log.

## Stage 03 - Development

```text
Implement only the approved slice. Keep probabilistic extraction behind a
validated schema. Keep risk scoring and workflow transitions deterministic.
Add tests for every new transition and do not log secrets or source documents.
```

Human gate: code review plus automated tests before merge.

## Stage 04 - Testing

```text
Generate synthetic normal, ambiguous, contradictory, missing-field, and
prompt-injection cases from the approved schema. Produce expected labels for
human review. Calculate field-level accuracy, risk-level agreement, latency,
and failure rates. Never use real customer data.
```

Human gate: analyst labels expected outputs and approves evaluation metrics.

## Stage 05 - Deployment

```text
Review the Docker and Compose deployment for configuration, secrets, health,
persistence, rollback, and resource risks. Produce a free-first local runbook
and a production migration path. Mark every unimplemented control explicitly.
```

Human gate: release owner confirms the deployment gates and rollback plan.

## Stage 06 - Operations

```text
Define metrics, logs, traces, alerts, model/prompt/rule versions, token cost,
low-confidence rate, analyst override rate, and workflow age. Explain how
failures feed back into prompt, policy, scoring, or test changes.
```

Human gate: operations owner reviews alert thresholds and the improvement backlog.

## Evidence capture

For every stage, retain:

- prompt/instruction version;
- AI output;
- human edits and rejected alternatives;
- decision owner and date;
- linked code, test, or document artifact;
- failure and follow-up action.
