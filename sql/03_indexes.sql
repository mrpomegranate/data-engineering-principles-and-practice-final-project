-- ============================================================
-- 03_indexes.sql  —  Indexes for API query performance
-- Runs after tables exist. Targets the filters the Flask API uses most:
-- lookups by ticker (via company_id) and date-range scans.
-- (Primary keys and UNIQUE constraints are already indexed automatically;
--  these cover the foreign keys and common WHERE/ORDER BY columns.)
-- ============================================================

-- Foreign-key columns: speed up joins to dimensions.
CREATE INDEX idx_headline_company   ON headline_fact (company_id);
CREATE INDEX idx_headline_date      ON headline_fact (date_id);
CREATE INDEX idx_headline_published ON headline_fact (published_timestamp);

CREATE INDEX idx_price_company      ON stock_price_fact (company_id);
CREATE INDEX idx_price_date         ON stock_price_fact (date_id);
CREATE INDEX idx_price_trading_date ON stock_price_fact (trading_date);

CREATE INDEX idx_metric_company     ON company_metric_fact (company_id);
CREATE INDEX idx_metric_date        ON company_metric_fact (date_id);

CREATE INDEX idx_sentiment_company  ON sentiment_aggregate_fact (company_id);
CREATE INDEX idx_sentiment_window   ON sentiment_aggregate_fact (window_start);

CREATE INDEX idx_reaction_company   ON price_reaction_fact (company_id);
CREATE INDEX idx_reaction_headline  ON price_reaction_fact (headline_id);

CREATE INDEX idx_runlog_timestamp   ON pipeline_run_log (run_timestamp);
