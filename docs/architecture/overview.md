# Architecture Overview

```mermaid
flowchart LR
    PO[Product owner] --> API[FastAPI intake]
    API --> PDF[Deterministic PDF extraction]
    PDF --> LLM[Structured LLM extraction]
    LLM --> SCORE[Deterministic scoring]
    SCORE --> STORE[(SQLite case store)]
    STORE --> ANALYST[FCRM analyst review]
    ANALYST --> QUEUE[Committee queue]
    QUEUE --> COMMITTEE[Three-member committee vote]
    COMMITTEE --> AUDIT[(Workflow events and vote records)]
```

The LLM structures untrusted source text; it does not make an approval decision. Scoring is deterministic so category scores and thresholds can be reproduced. SQLite is a deliberately small persistence choice for the synthetic demo and can be replaced by Postgres without changing the domain contracts.

The case record stores the extracted version, assessment, status, timestamps,
policy evidence, and a stable case ID. Workflow events store the actor and
rationale for human actions. Committee votes are stored separately, reject
duplicate voters, and require three distinct demo committee members before a
case becomes decisioned. The demo store is application-enforced; production
still needs database-level immutability and real identity.
