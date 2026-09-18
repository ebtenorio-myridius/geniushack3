# Architecture Overview

```mermaid
flowchart LR
    PO[Product owner] --> API[FastAPI intake]
    API --> PDF[Deterministic PDF extraction]
    PDF --> LLM[Structured LLM extraction]
    LLM --> SCORE[Deterministic scoring]
    SCORE --> STORE[(SQLite case store)]
    STORE --> ANALYST[FCRM analyst review]
    ANALYST --> AUDIT[(Append-only workflow events)]
```

The LLM structures untrusted source text; it does not make an approval decision. Scoring is deterministic so category scores and thresholds can be reproduced. SQLite is a deliberately small persistence choice for the synthetic demo and can be replaced by Postgres without changing the domain contracts.

The case record stores the extracted version, assessment, status, timestamps, and a stable case ID. Workflow events store the actor and rationale for human actions.
