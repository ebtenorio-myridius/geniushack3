# Architecture Overview

```mermaid
flowchart LR
    BROWSER[Browser] --> ROOT[GET /: validate demo cookies]
    ROOT -->|signed out| LOGIN[Blank login form]
    ROOT -->|signed in| DASH[Role dashboard]
    LOGIN -->|valid username + role| COOKIE[Set demo identity cookies]
    COOKIE --> ROOT
    DASH --> INTAKE[GET /intake: validate demo cookies]
    INTAKE --> UPLOAD[POST /intake/upload]
    UPLOAD --> PDF[Extract text with pypdf]
    PDF --> LLM[OpenAI structured extraction]
    LLM --> SCORE[Deterministic weighted score]
    LLM --> POLICY{Policy index + API key?}
    POLICY -->|yes| SEMANTIC[Embedding + cosine ranking]
    POLICY -->|no or error| RULES[Deterministic category fallback]
    SCORE --> STORE[(SQLite case store)]
    SEMANTIC --> STORE
    RULES --> STORE
    STORE --> RESULT[Draft extraction result]
    RESULT --> OWNER[Product owner checks and submits]
    OWNER -->|low or medium| ANALYST[Analyst review/edit]
    OWNER -->|high or critical| COMMITTEE[Committee review; verify unreviewed facts]
    ANALYST -->|finalized; optional escalation| COMMITTEE
    ANALYST -->|low/medium finalized| CLOSE[Analyst closes case]
    COMMITTEE --> VOTE[Three distinct committee votes]
    VOTE -->|approved, rejected, deferred| OUTCOME[Decisioned]
    VOTE -->|approved with conditions| CONDITIONS[Product owner completes conditions]
    CONDITIONS --> CLOSE
    OUTCOME --> CLOSE
    STORE --> EVENTS[(Events, versions, votes, telemetry)]
    COMMITTEE --> EVENTS
```

The root route validates the `demo_user` and `demo_role` cookies against the
fixed demo-user mapping and redirects signed-out browsers to login or
signed-in browsers to the matching dashboard. The `/intake` browser page
performs the same validation. The login form starts blank; a successful login
sets the identity cookies, and the switch-role link clears them before
returning to login.

Workflow routes validate the fixed demo username-role mapping from the
identity cookies; client-supplied role headers do not grant access. The
cookies are demo identity selectors, not signed credentials, and can be
forged by a client. This remains unsuitable for production authorization.

The LLM structures untrusted source text; it does not make an approval
decision. Scoring is deterministic so category scores and thresholds can be
reproduced. Policy evidence uses semantic embedding retrieval only when an
index and API key are available; otherwise it uses a rule-based category
fallback. The policy corpus is synthetic demonstration material, not approved
supervisory guidance.

On product-owner submission, low/medium-risk drafts enter analyst review and
high/critical-risk drafts enter committee review directly. This direct
high/critical route has no analyst verification; committee members are prompted
to verify the extracted facts and score. Analysts can separately escalate a
case after finalizing it. Analyst finalization and committee outcomes do not
close cases automatically: an analyst closes a case after recording closure
rationale, and approval conditions must be completed by the product owner
first.

SQLite stores case data, the current extraction and assessment, policy
evidence, extraction versions, workflow events, committee votes, and telemetry.
The uploaded PDF itself is not persisted. Workflow history is append-only by
application behavior, not protected by database-level immutability. Committee
voting requires three distinct authenticated demo usernames at the voting
route; two approvals approve, two rejections reject, and a full vote without
either majority defers. This is prototype behavior, not an institutionally
approved decision policy. The current committee outcomes (approved, rejected,
deferred, or approved with conditions) are recorded before analyst closure.

SQLite is a deliberately small persistence choice for the synthetic demo. A
production database migration would require a persistence adapter and
migrations; domain contracts can remain stable, but there is not currently a
separate repository abstraction.

Production increments include real identity, database-enforced audit
controls, source-document storage, approved policy and decision mappings, and
control-effectiveness/residual-risk data.
