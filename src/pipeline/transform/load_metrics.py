"""
Load company metrics: raw Finnhub profile + metrics docs -> company_metric_fact.

Combines two raw documents into one point-in-time snapshot row:
    raw_company_profiles  -> marketCapitalization (reported in MILLIONS
                             by Finnhub; converted to absolute dollars)
    raw_company_metrics   -> metric dict: peTTM (or peBasicExclExtraTTM),
                             52WeekHigh, 52WeekLow

metric_timestamp = the metrics document's ingestion time, so each fresh
extraction produces a new snapshot row while re-loading the same raw doc
upserts the same row (idempotent via (company_id, metric_timestamp)).

short_interest stays NULL (FINRA source is a stretch item).

Run standalone:
    python -m src.pipeline.transform.load_metrics AAPL
"""

import sys

from dotenv import load_dotenv

from ..extract.mongo_store import get_mongo_db
from ..extract.run_logger import log_run
from ..load.warehouse import get_connection, DimCache

load_dotenv(override=True)

SOURCE = "finnhub"

UPSERT_SQL = """
    INSERT INTO company_metric_fact
        (company_id, source_id, date_id, metric_timestamp,
         market_cap, pe_ratio, fifty_two_week_high, fifty_two_week_low)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (company_id, metric_timestamp) DO UPDATE SET
        market_cap          = EXCLUDED.market_cap,
        pe_ratio            = EXCLUDED.pe_ratio,
        fifty_two_week_high = EXCLUDED.fifty_two_week_high,
        fifty_two_week_low  = EXCLUDED.fifty_two_week_low
"""


def _latest(mongo, collection: str, ticker: str):
    return mongo[collection].find_one(
        {"_source": SOURCE, "_ticker": ticker.upper()},
        sort=[("_ingested_at", -1)],
    )


def load(ticker: str) -> int:
    """Combine latest profile + metrics raw docs into one snapshot row."""
    mongo = get_mongo_db()

    metrics_doc = _latest(mongo, "raw_company_metrics", ticker)
    profile_doc = _latest(mongo, "raw_company_profiles", ticker)
    if not metrics_doc:
        log_run("load", SOURCE, "failure",
                error=f"no raw metrics doc for {ticker}")
        print(f"No raw metrics document for {ticker} — run the updated "
              f"Finnhub extractor first.")
        return 0

    m = (metrics_doc.get("payload") or {}).get("metric") or {}
    profile = (profile_doc or {}).get("payload") or {}

    # Finnhub reports market cap in MILLIONS -> absolute dollars for BIGINT
    market_cap_millions = profile.get("marketCapitalization")
    market_cap = (int(market_cap_millions * 1_000_000)
                  if market_cap_millions else None)
    pe_ratio = m.get("peTTM") or m.get("peBasicExclExtraTTM")
    wk52_high = m.get("52WeekHigh")
    wk52_low = m.get("52WeekLow")

    conn = get_connection()
    try:
        cache = DimCache(conn)
        company_id = cache.company_id(ticker)
        source_id = cache.source_id(SOURCE)
        if company_id is None or source_id is None:
            raise RuntimeError(
                f"{ticker} or '{SOURCE}' missing from dimensions")

        snapshot_ts = metrics_doc["_ingested_at"]      # datetime from Mongo
        snapshot_ts = snapshot_ts.replace(tzinfo=None) # TIMESTAMP w/o tz
        date_id = cache.date_id(snapshot_ts.date())
        if date_id is None:
            raise RuntimeError(
                f"{snapshot_ts.date()} not in date_dim — extend the range")

        with conn.cursor() as cur:
            cur.execute(UPSERT_SQL, (
                company_id, source_id, date_id, snapshot_ts,
                market_cap, pe_ratio, wk52_high, wk52_low,
            ))
        conn.commit()
        log_run("load", SOURCE, "success", extracted=1, loaded=1)
    except Exception as exc:
        conn.rollback()
        log_run("load", SOURCE, "failure", error=str(exc))
        raise
    finally:
        conn.close()

    print(f"company_metric_fact: upserted 1 snapshot for {ticker} "
          f"(market_cap={market_cap}, pe={pe_ratio}, "
          f"52wk {wk52_low}-{wk52_high})")
    return 1


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    load(tk)