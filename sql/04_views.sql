-- ============================================================
-- 04_views.sql  —  Analytical views
-- Runs last: depends on all tables existing.
-- ============================================================

-- ---------- sentiment_vs_price ----------
-- The core analytical join behind GET /sentiment-vs-price/{ticker}.
-- Pairs each day's sentiment rollup with that day's price and the
-- next day's percent change, so the API (and ad-hoc SQL) can read the
-- whole analysis from one place instead of re-joining in Python.
--
-- Join logic:
--   - sentiment_aggregate_fact gives daily avg sentiment + counts
--   - stock_price_fact gives that day's close
--   - LEAD() looks ahead one trading day per company to get the
--     next-day close, used to compute next_day_pct_change
CREATE VIEW sentiment_vs_price AS
WITH price_with_next AS (
    SELECT
        sp.company_id,
        sp.trading_date,
        sp.close_price,
        LEAD(sp.close_price) OVER (
            PARTITION BY sp.company_id ORDER BY sp.trading_date
        ) AS next_close_price
    FROM stock_price_fact sp
)
SELECT
    c.ticker,
    c.company_name,
    sa.window_start::date            AS analysis_date,
    sa.headline_count,
    sa.avg_sentiment_score,
    sa.positive_count,
    sa.neutral_count,
    sa.negative_count,
    p.close_price,
    p.next_close_price,
    ROUND(
        CASE WHEN p.close_price IS NOT NULL AND p.close_price <> 0
             THEN (p.next_close_price - p.close_price) / p.close_price * 100
        END, 4
    )                                AS next_day_pct_change
FROM sentiment_aggregate_fact sa
JOIN company_dim c
       ON c.company_id = sa.company_id
LEFT JOIN price_with_next p
       ON p.company_id = sa.company_id
      AND p.trading_date = sa.window_start::date
ORDER BY c.ticker, analysis_date;
