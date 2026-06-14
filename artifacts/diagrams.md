# MarketPulse — Mermaid Diagrams (v2)

Updated per the project handoff: MongoDB is now a required raw landing zone,
PostgreSQL has 9 tables (3 dims + 5 facts + run log), the pipeline label
reflects the full lifecycle, and the React dashboard is labeled optional.

Paste either block into https://mermaid.live to render/export, or use fenced
```mermaid blocks in Markdown that supports Mermaid (GitHub, GitLab, VS Code).

---

## 1. System Architecture

```mermaid
flowchart TB
    subgraph EXT["External APIs"]
        FIN["Finnhub / NewsAPI<br/>headlines, company news"]
        YF["yfinance / Alpha Vantage<br/>OHLCV, company metrics"]
    end

    subgraph COMPOSE["Docker Compose network (internal)"]
        direction TB
        SCH["Scheduler<br/>cron or Airflow"]
        PIPE["Pipeline container<br/>extract, validate, store raw,<br/>transform, score, load"]
        MONGO[("MongoDB<br/>raw API JSON landing zone")]
        DB[("PostgreSQL<br/>dimensional warehouse + pipeline logs")]
        API["Flask API<br/>analytical JSON endpoints"]
        FE["React dashboard<br/>Chart.js views, optional layer"]
    end

    USER["User browser"]

    FIN --> PIPE
    YF --> PIPE
    SCH -->|triggers| PIPE
    PIPE -->|store raw JSON| MONGO
    PIPE -->|upsert + run log| DB
    DB --> API
    API --> FE
    FE -->|":3000"| USER

    classDef ext fill:#F1EFE8,stroke:#5F5E5A,color:#2C2C2A;
    classDef pipe fill:#EEEDFE,stroke:#534AB7,color:#26215C;
    classDef sched fill:#FAEEDA,stroke:#854F0B,color:#412402;
    classDef store fill:#FAECE7,stroke:#993C1D,color:#4A1B0C;
    classDef mongo fill:#EAF3DE,stroke:#3B6D11,color:#173404;
    classDef api fill:#E6F1FB,stroke:#185FA5,color:#042C53;
    classDef fe fill:#E1F5EE,stroke:#0F6E56,color:#04342C;

    class FIN,YF ext;
    class PIPE pipe;
    class SCH sched;
    class DB store;
    class MONGO mongo;
    class API api;
    class FE,USER fe;
```

Notes:
- The `subgraph COMPOSE` boundary is the security boundary: everything inside
  is on the internal Docker network. Only the frontend port (`:3000`) crosses
  out to the user. Postgres and Mongo publish no host port.
- MongoDB is now solid (required MVP), not dashed — it stores raw API JSON
  before transformation, giving the project both NoSQL and relational storage.
- The dashboard connects only to the Flask API — never to Postgres or the
  external APIs directly.
- Responsibility split: the pipeline writes raw data to Mongo and cleaned data
  to Postgres; the Flask API only reads from Postgres in the MVP (no writes);
  the React dashboard only consumes API responses.
- `[(...)]` is Mermaid's cylinder (database) shape.

---

## 2. Sequence Diagram

```mermaid
sequenceDiagram
    participant SCH as Scheduler
    participant PIPE as Pipeline
    participant API as External APIs
    participant MG as MongoDB
    participant DB as PostgreSQL
    participant FL as Flask API
    participant UI as React dashboard

    Note over SCH,DB: Scheduled run (pipeline writes)
    SCH->>PIPE: trigger run_pipeline.py
    activate PIPE
    PIPE->>API: extract quotes, news, OHLCV, metrics
    activate API
    API-->>PIPE: raw JSON responses
    deactivate API
    PIPE->>MG: store raw API JSON
    activate MG
    MG-->>PIPE: raw documents stored
    deactivate MG
    PIPE->>PIPE: clean, normalize, VADER score
    PIPE->>PIPE: build aggregates
    PIPE->>DB: upsert dim + fact rows
    activate DB
    DB-->>PIPE: rows committed
    deactivate DB
    PIPE->>DB: update pipeline_run_log
    deactivate PIPE

    Note over UI,DB: User flow (Flask reads only)
    UI->>FL: GET /sentiment-vs-price/{ticker}
    activate FL
    FL->>DB: query sentiment-vs-price view/join
    activate DB
    DB-->>FL: result set
    deactivate DB
    FL-->>UI: JSON payload
    deactivate FL
    UI->>UI: render Chart.js view
```

Notes:
- `->>` is a solid (synchronous) call; `-->>` is a dashed return.
- MongoDB now appears as a participant: the pipeline stores raw JSON before
  transforming, and writes a final `pipeline_run_log` update after loading.
- The visual gap between `UI` and `DB`/`API`(external) is intentional — the
  dashboard only ever talks to Flask, which protects rate-limited APIs from
  dashboard traffic.
