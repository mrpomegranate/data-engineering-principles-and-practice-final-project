"""
Load stock prices: raw yfinance documents (Mongo) -> stock_price_fact (Postgres).

Transform steps:
  1. Read the LATEST raw yfinance document for the ticker (raw zone keeps
     every ingestion; we conform only the most recent).
  2. Parse each daily bar: date string -> date, numeric fields -> floats.
  3. Resolve FKs via DimCache (company_id, source_id, date_id).
  4. Upsert with ON CONFLICT (company_id, trading_date) DO UPDATE — re-runs
     refresh rows instead of duplicating (idempotent).

Notes:
  - yfinance history() uses auto-adjusted prices by default, so Close is
    already split/dividend adjusted; we store it in both close_price and
    adjusted_close_price and document that decision.
  - average_volume is left NULL here (it comes from Finnhub metrics later).
  - Rows whose date falls outside date_dim's populated range are skipped
    and counted, not fatal.

Run standalone:
    python -m src.pipeline.transform.load_prices AAPL
"""

import sys
from datetime import datetime

from dotenv import load_dotenv

from ..extract.mongo_store import get_mongo_db
from ..extract.run_logger import log_run
from ..load.warehouse import get_connection, DimCache

load_dotenv(override=True)

SOURCE = "yfinance"

UPSERT_SQL = """
    INSERT INTO stock_price_fact
        (company_id, source_id, date_id, trading_date,
         open_price, high_price, low_price, close_price,
         adjusted_close_price, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (company_id, trading_date) DO UPDATE SET
        source_id            = EXCLUDED.source_id,
        date_id              = EXCLUDED.date_id,
        open_price           = EXCLUDED.open_price,
        high_price           = EXCLUDED.high_price,
        low_price            = EXCLUDED.low_price,
        close_price          = EXCLUDED.close_price,
        adjusted_close_price = EXCLUDED.adjusted_close_price,
        volume               = EXCLUDED.volume
"""


def load(ticker: str) -> int:
    """Transform + load the latest yfinance raw doc. Returns rows upserted."""
    mongo = get_mongo_db()
    doc = mongo["raw_stock_prices"].find_one(
        {"_source": SOURCE, "_ticker": ticker.upper()},
        sort=[("_ingested_at", -1)],
    )
    if not doc:
        log_run("load", SOURCE, "failure", error=f"no raw doc for {ticker}")
        print(f"No raw {SOURCE} document found for {ticker} — run the "
              f"extractor first.")
        return 0

    records = doc["payload"]
    conn = get_connection()
    loaded = skipped = 0
    try:
        cache = DimCache(conn)
        company_id = cache.company_id(ticker)
        source_id = cache.source_id(SOURCE)
        if company_id is None or source_id is None:
            log_run("load", SOURCE, "failure",
                    error=f"missing dim row: company={company_id}, "
                          f"source={source_id}")
            raise RuntimeError(
                f"{ticker} or '{SOURCE}' not found in dimensions — check "
                f"seed data.")

        rows = []
        for rec in records:
            # Date arrives like '2021-07-06 00:00:00-04:00' — first 10
            # chars are the calendar date.
            trading_date = datetime.strptime(
                str(rec["Date"])[:10], "%Y-%m-%d").date()
            date_id = cache.date_id(trading_date)
            if date_id is None:
                skipped += 1          # outside date_dim's populated range
                continue
            close = round(float(rec["Close"]), 4)
            rows.append((
                company_id, source_id, date_id, trading_date,
                round(float(rec["Open"]), 4),
                round(float(rec["High"]), 4),
                round(float(rec["Low"]), 4),
                close,
                close,                # auto-adjusted: Close == adjusted
                int(rec["Volume"]),
            ))

        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)
        conn.commit()
        loaded = len(rows)
        log_run("load", SOURCE, "success", extracted=len(records),
                loaded=loaded)
    except Exception as exc:
        conn.rollback()
        log_run("load", SOURCE, "failure", error=str(exc))
        raise
    finally:
        conn.close()

    print(f"stock_price_fact: upserted {loaded} rows for {ticker}"
          + (f" (skipped {skipped} outside date_dim range)" if skipped else ""))
    return loaded


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    load(tk)