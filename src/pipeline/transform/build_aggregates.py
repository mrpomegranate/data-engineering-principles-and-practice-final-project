"""
Build the computed fact tables from scored headlines:

  1. sentiment_aggregate_fact — daily per-company rollups (counts, avg
     score, pos/neu/neg breakdown). Grain: one row per company per day.

  2. price_reaction_fact — the 1-day price reaction per headline (MVP).
     Rule 'prev_close_to_next_close': price_at_event is the close of the
     last trading day ON OR BEFORE publish date; price_after_1day is the
     close of the FIRST trading day AFTER. Weekend/after-hours headlines
     therefore bracket Friday close -> Monday close. Intraday fields
     (15min/1hr) stay NULL per the MVP/stretch line.

Both are pure SQL INSERT..SELECT with ON CONFLICT upserts — idempotent,
and re-runs pick up newly scored headlines automatically.

Run standalone:
    python -m src.pipeline.transform.build_aggregates
"""

from dotenv import load_dotenv

from ..extract.run_logger import log_run
from ..load.warehouse import get_connection

load_dotenv(override=True)

SENTIMENT_AGG_SQL = """
    INSERT INTO sentiment_aggregate_fact
        (company_id, date_id, window_start, window_end, headline_count,
         avg_sentiment_score, positive_count, neutral_count, negative_count)
    SELECT
        h.company_id,
        h.date_id,
        date_trunc('day', h.published_timestamp)                          AS window_start,
        date_trunc('day', h.published_timestamp) + INTERVAL '1 day'
            - INTERVAL '1 second'                                          AS window_end,
        count(*)                                                           AS headline_count,
        round(avg(h.sentiment_score), 4)                                   AS avg_sentiment_score,
        count(*) FILTER (WHERE h.sentiment_label = 'positive')             AS positive_count,
        count(*) FILTER (WHERE h.sentiment_label = 'neutral')              AS neutral_count,
        count(*) FILTER (WHERE h.sentiment_label = 'negative')             AS negative_count
    FROM headline_fact h
    WHERE h.sentiment_score IS NOT NULL
    GROUP BY h.company_id, h.date_id, date_trunc('day', h.published_timestamp)
    ON CONFLICT (company_id, window_start) DO UPDATE SET
        date_id             = EXCLUDED.date_id,
        window_end          = EXCLUDED.window_end,
        headline_count      = EXCLUDED.headline_count,
        avg_sentiment_score = EXCLUDED.avg_sentiment_score,
        positive_count      = EXCLUDED.positive_count,
        neutral_count       = EXCLUDED.neutral_count,
        negative_count      = EXCLUDED.negative_count
"""

PRICE_REACTION_SQL = """
    INSERT INTO price_reaction_fact
        (headline_id, company_id, date_id, reaction_window_rule,
         market_session_at_publish, price_at_event, price_after_1day,
         percent_change_1day)
    SELECT
        h.headline_id,
        h.company_id,
        h.date_id,
        'prev_close_to_next_close',
        dd.market_session,
        p0.close_price,
        p1.close_price,
        CASE WHEN p1.close_price IS NOT NULL
             THEN round((p1.close_price - p0.close_price)
                        / p0.close_price * 100, 4)
        END
    FROM headline_fact h
    JOIN date_dim dd ON dd.date_id = h.date_id
    LEFT JOIN LATERAL (
        SELECT sp.close_price
        FROM stock_price_fact sp
        WHERE sp.company_id = h.company_id
          AND sp.trading_date <= h.published_timestamp::date
        ORDER BY sp.trading_date DESC
        LIMIT 1
    ) p0 ON TRUE
    LEFT JOIN LATERAL (
        SELECT sp.close_price
        FROM stock_price_fact sp
        WHERE sp.company_id = h.company_id
          AND sp.trading_date > h.published_timestamp::date
        ORDER BY sp.trading_date ASC
        LIMIT 1
    ) p1 ON TRUE
    WHERE h.sentiment_score IS NOT NULL
      AND p0.close_price IS NOT NULL
      AND p0.close_price <> 0
    ON CONFLICT (headline_id) DO UPDATE SET
        reaction_window_rule      = EXCLUDED.reaction_window_rule,
        market_session_at_publish = EXCLUDED.market_session_at_publish,
        price_at_event            = EXCLUDED.price_at_event,
        price_after_1day          = EXCLUDED.price_after_1day,
        percent_change_1day       = EXCLUDED.percent_change_1day
"""


def build() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SENTIMENT_AGG_SQL)
            agg_rows = cur.rowcount
        conn.commit()
        log_run("aggregate", "sentiment_aggregate", "success", loaded=agg_rows)
        print(f"sentiment_aggregate_fact: upserted {agg_rows} daily rollups")

        with conn.cursor() as cur:
            cur.execute(PRICE_REACTION_SQL)
            rx_rows = cur.rowcount
        conn.commit()
        log_run("aggregate", "price_reaction", "success", loaded=rx_rows)
        print(f"price_reaction_fact: upserted {rx_rows} headline reactions")
    except Exception as exc:
        conn.rollback()
        log_run("aggregate", "aggregates", "failure", error=str(exc))
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    build()