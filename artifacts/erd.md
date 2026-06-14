# MarketPulse ERD — Mermaid Source

Star schema: three shared dimensions (company, date, source) at the center,
five fact tables radiating out, plus an operational run-log table. The single
fact-to-fact link (headline → price reaction) is what lets you ask "did this
specific headline move the price?".

Paste into https://mermaid.live to render/export, or use a ```mermaid fenced
block in Markdown that supports it (GitHub, VS Code with a Mermaid extension).

Readability notes:
- Entities are declared dimensions-first, then facts, so related tables sit
  near each other and Mermaid routes shorter, straighter connectors.
- Relationship labels are kept to one short word to avoid label collisions.
- If you want even cleaner output for the PDF deliverable, paste this into
  Draw.io or Lucidchart — those give manual control over connector routing
  that Mermaid's auto-layout can't match.

```mermaid
erDiagram
    COMPANY_DIM ||--o{ HEADLINE_FACT : has
    SOURCE_DIM  ||--o{ HEADLINE_FACT : has
    DATE_DIM    ||--o{ HEADLINE_FACT : has

    COMPANY_DIM ||--o{ STOCK_PRICE_FACT : has
    SOURCE_DIM  ||--o{ STOCK_PRICE_FACT : has
    DATE_DIM    ||--o{ STOCK_PRICE_FACT : has

    COMPANY_DIM ||--o{ COMPANY_METRIC_FACT : has
    SOURCE_DIM  ||--o{ COMPANY_METRIC_FACT : has
    DATE_DIM    ||--o{ COMPANY_METRIC_FACT : has

    COMPANY_DIM ||--o{ SENTIMENT_AGGREGATE_FACT : has
    DATE_DIM    ||--o{ SENTIMENT_AGGREGATE_FACT : has

    COMPANY_DIM   ||--o{ PRICE_REACTION_FACT : has
    DATE_DIM      ||--o{ PRICE_REACTION_FACT : has
    HEADLINE_FACT ||--o{ PRICE_REACTION_FACT : triggers

    DATE_DIM ||--o{ PIPELINE_RUN_LOG : has

    COMPANY_DIM {
        int company_id PK
        varchar ticker UK
        varchar company_name
        varchar exchange
        varchar sector
        varchar industry
    }
    SOURCE_DIM {
        int source_id PK
        varchar source_name
        varchar source_type
        varchar base_url
    }
    DATE_DIM {
        int date_id PK
        date full_date
        int year
        int quarter
        int month
        int day
        int day_of_week
        int hour
        int minute
        bool is_market_day
        varchar market_session
    }
    HEADLINE_FACT {
        int headline_id PK
        int company_id FK
        int source_id FK
        int date_id FK
        timestamp published_timestamp
        text headline_text
        varchar article_url
        varchar author
        varchar sentiment_label
        numeric sentiment_score
    }
    STOCK_PRICE_FACT {
        int price_id PK
        int company_id FK
        int source_id FK
        int date_id FK
        date trading_date
        numeric open_price
        numeric high_price
        numeric low_price
        numeric close_price
        numeric adjusted_close_price
        bigint volume
        bigint average_volume
    }
    COMPANY_METRIC_FACT {
        int metric_id PK
        int company_id FK
        int source_id FK
        int date_id FK
        timestamp metric_timestamp
        bigint market_cap
        numeric pe_ratio
        numeric fifty_two_week_high
        numeric fifty_two_week_low
        numeric short_interest
    }
    SENTIMENT_AGGREGATE_FACT {
        int sentiment_agg_id PK
        int company_id FK
        int date_id FK
        timestamp window_start
        timestamp window_end
        int headline_count
        numeric avg_sentiment_score
        int positive_count
        int neutral_count
        int negative_count
    }
    PRICE_REACTION_FACT {
        int reaction_id PK
        int headline_id FK
        int company_id FK
        int date_id FK
        varchar reaction_window_rule
        varchar market_session_at_publish
        numeric price_at_event
        numeric price_after_15min
        numeric price_after_1hr
        numeric price_after_1day
        numeric percent_change_15min
        numeric percent_change_1hr
        numeric percent_change_1day
    }
    PIPELINE_RUN_LOG {
        int run_id PK
        int date_id FK
        timestamp run_timestamp
        varchar pipeline_step
        varchar source_name
        varchar status
        int records_extracted
        int records_loaded
        text error_message
    }
```

## Why star, not snowflake

- Facts join directly to dimensions — no dimension is normalized into
  sub-tables, so queries like /sentiment-vs-price need fewer joins.
- Dimensions are small (companies, sources, dates), so the redundancy a star
  tolerates costs almost nothing here.
- SOURCE_DIM intentionally connects only to the three vendor-sourced facts
  (headline, stock price, company metric). SENTIMENT_AGGREGATE_FACT and
  PRICE_REACTION_FACT are computed by the pipeline, so they have no source FK.
- PIPELINE_RUN_LOG keeps a free-text source_name (not a source_id FK) because
  it is a write-once operational log that may reference a source before a dim
  row exists.
```
