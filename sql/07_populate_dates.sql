-- ============================================================
-- 07_populate_dates.sql  —  Populate date_dim
-- Runs after companies (06). Generates one row per calendar day from
-- 2021-01-01 through 2026-06-30 using generate_series, rather than
-- hand-writing ~2,000 rows.
--
-- Grain: daily (hour/minute left NULL — intraday rows, if ever needed,
-- can be added separately without conflicting with these).
-- is_market_day: TRUE for weekdays (Mon-Fri), FALSE for weekends.
--   NOTE: this is a simplified rule — it does NOT exclude US market
--   holidays. Good enough for joining daily facts; documented as a
--   known simplification.
-- market_session: 'regular' for weekdays, 'closed' for weekends (daily
--   grain has no intraday session, so this is a coarse label).
-- ============================================================

INSERT INTO date_dim (
    full_date, year, quarter, month, day, day_of_week,
    hour, minute, is_market_day, market_session
)
SELECT
    d::date                                   AS full_date,
    EXTRACT(YEAR    FROM d)::int               AS year,
    EXTRACT(QUARTER FROM d)::int               AS quarter,
    EXTRACT(MONTH   FROM d)::int               AS month,
    EXTRACT(DAY     FROM d)::int               AS day,
    EXTRACT(DOW     FROM d)::int               AS day_of_week,   -- 0=Sun .. 6=Sat
    NULL::int                                  AS hour,
    NULL::int                                  AS minute,
    (EXTRACT(DOW FROM d) BETWEEN 1 AND 5)      AS is_market_day, -- Mon-Fri
    CASE WHEN EXTRACT(DOW FROM d) BETWEEN 1 AND 5
         THEN 'regular' ELSE 'closed' END      AS market_session
FROM generate_series(
        '2021-01-01'::date,
        '2026-06-30'::date,
        '1 day'::interval
     ) AS d
ON CONFLICT (full_date, hour, minute) DO NOTHING;