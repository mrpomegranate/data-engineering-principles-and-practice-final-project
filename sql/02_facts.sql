-- ============================================================
-- 02_facts.sql  —  Fact tables + operational log
-- Runs after 01_dims.sql (foreign keys reference the dimensions).
-- Unique constraints marked "idempotency" let loads re-run safely:
-- an upsert on conflict updates instead of duplicating.
-- ============================================================

-- ---------- HEADLINE_FACT ----------
-- One row per headline. Per-headline sentiment (label + score) is stored
-- HERE, not in the aggregate table. article_url uniqueness prevents the
-- same article being ingested twice across runs.
CREATE TABLE headline_fact (
    headline_id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id           INT NOT NULL REFERENCES company_dim(company_id),
    source_id            INT NOT NULL REFERENCES source_dim(source_id),
    date_id              INT NOT NULL REFERENCES date_dim(date_id),
    published_timestamp  TIMESTAMP NOT NULL,
    headline_text        TEXT NOT NULL,
    article_url          VARCHAR(1000),
    author               VARCHAR(255),                 -- nullable: often missing from news APIs
    sentiment_label      VARCHAR(20),                  -- positive | neutral | negative (set during transform)
    sentiment_score      NUMERIC(5,4),                 -- VADER compound, -1.0000 .. 1.0000
    CONSTRAINT uq_headline_url UNIQUE (company_id, article_url, published_timestamp)
);

-- ---------- STOCK_PRICE_FACT ----------
-- Daily grain: one row per company per trading day. close vs current is
-- resolved to a single close_price; adjusted_close handles splits/dividends.
CREATE TABLE stock_price_fact (
    price_id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id            INT NOT NULL REFERENCES company_dim(company_id),
    source_id             INT NOT NULL REFERENCES source_dim(source_id),
    date_id               INT NOT NULL REFERENCES date_dim(date_id),
    trading_date          DATE NOT NULL,
    open_price            NUMERIC(12,4),
    high_price            NUMERIC(12,4),
    low_price             NUMERIC(12,4),
    close_price           NUMERIC(12,4),
    adjusted_close_price  NUMERIC(12,4),
    volume                BIGINT,
    average_volume        BIGINT,
    CONSTRAINT uq_price_company_day UNIQUE (company_id, trading_date)   -- idempotency
);

-- ---------- COMPANY_METRIC_FACT ----------
-- Point-in-time fundamentals snapshot. short_interest nullable (FINRA,
-- bi-monthly, may be absent); borrow_rate intentionally omitted (not on
-- free sources). source_id FK instead of free-text source name.
CREATE TABLE company_metric_fact (
    metric_id            INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id           INT NOT NULL REFERENCES company_dim(company_id),
    source_id            INT NOT NULL REFERENCES source_dim(source_id),
    date_id              INT NOT NULL REFERENCES date_dim(date_id),
    metric_timestamp     TIMESTAMP NOT NULL,
    market_cap           BIGINT,
    pe_ratio             NUMERIC(10,2),
    fifty_two_week_high  NUMERIC(12,4),
    fifty_two_week_low   NUMERIC(12,4),
    short_interest       NUMERIC(8,4),                 -- nullable / stretch
    CONSTRAINT uq_metric_company_ts UNIQUE (company_id, metric_timestamp)  -- idempotency
);

-- ---------- SENTIMENT_AGGREGATE_FACT ----------
-- Daily per-company rollup computed by the pipeline. No source_id: this is
-- derived data, not vendor-sourced. window_start/window_end bound the period.
CREATE TABLE sentiment_aggregate_fact (
    sentiment_agg_id     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id           INT NOT NULL REFERENCES company_dim(company_id),
    date_id              INT NOT NULL REFERENCES date_dim(date_id),
    window_start         TIMESTAMP NOT NULL,
    window_end           TIMESTAMP NOT NULL,
    headline_count       INT NOT NULL DEFAULT 0,
    avg_sentiment_score  NUMERIC(5,4),
    positive_count       INT NOT NULL DEFAULT 0,
    neutral_count        INT NOT NULL DEFAULT 0,
    negative_count       INT NOT NULL DEFAULT 0,
    CONSTRAINT uq_sentiment_company_window UNIQUE (company_id, window_start)  -- idempotency
);

-- ---------- PRICE_REACTION_FACT ----------
-- One row per headline's price reaction. 1-day fields are MVP; 15min/1hr
-- intraday fields are nullable/stretch. Links to the triggering headline.
CREATE TABLE price_reaction_fact (
    reaction_id                INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    headline_id                INT NOT NULL REFERENCES headline_fact(headline_id),
    company_id                 INT NOT NULL REFERENCES company_dim(company_id),
    date_id                    INT NOT NULL REFERENCES date_dim(date_id),
    reaction_window_rule       VARCHAR(50),            -- e.g. "next_open" for after-hours headlines
    market_session_at_publish  VARCHAR(20),
    price_at_event             NUMERIC(12,4),
    price_after_15min          NUMERIC(12,4),          -- nullable / stretch
    price_after_1hr            NUMERIC(12,4),          -- nullable / stretch
    price_after_1day           NUMERIC(12,4),
    percent_change_15min       NUMERIC(8,4),           -- nullable / stretch
    percent_change_1hr         NUMERIC(8,4),           -- nullable / stretch
    percent_change_1day        NUMERIC(8,4),
    CONSTRAINT uq_reaction_headline UNIQUE (headline_id)  -- idempotency: one reaction per headline
);

-- ---------- PIPELINE_RUN_LOG ----------
-- Operational log. source_name is free text (write-once log may reference a
-- source before/without a dim row). One row per pipeline step per run.
CREATE TABLE pipeline_run_log (
    run_id             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date_id            INT REFERENCES date_dim(date_id),
    run_timestamp      TIMESTAMP NOT NULL DEFAULT NOW(),
    pipeline_step      VARCHAR(50)  NOT NULL,          -- extract | transform | load | aggregate
    source_name        VARCHAR(100),
    status             VARCHAR(20)  NOT NULL,          -- success | failure | partial
    records_extracted  INT,
    records_loaded     INT,
    error_message      TEXT
);
