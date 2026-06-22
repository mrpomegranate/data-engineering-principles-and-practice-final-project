
"""
Alpha Vantage extractor — BACKUP daily quote source.

Used only as a fallback for prices (Finnhub is primary, yfinance is the
history backfill). Free tier is ~25 requests/DAY, so this detects and
reports rate-limiting distinctly from a real failure.

Run standalone:
    python -m src.pipeline.extract.alphavantage_source AAPL
"""

import os
import sys

from dotenv import load_dotenv

from .http_client import get_json
from .mongo_store import store_raw, store_error
from .run_logger import log_run

load_dotenv(override=True)

BASE = "https://www.alphavantage.co/query"
SOURCE = "alphavantage"


def extract(ticker: str) -> int:
    """Extract a daily global quote for one ticker. Returns docs stored."""
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        log_run("extract", SOURCE, "failure", error="ALPHAVANTAGE_API_KEY missing")
        raise RuntimeError("ALPHAVANTAGE_API_KEY missing from environment")

    stored = 0
    try:
        data = get_json(BASE, {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": key,
        })

        # Rate limit / info messages come back as 200 OK with a Note/Information
        # key instead of data — detect that explicitly.
        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information")
            store_error(SOURCE, ticker, "global_quote", f"rate limited: {msg}")
            log_run("extract", SOURCE, "partial", error="rate limited")
            return 0

        if not data.get("Global Quote"):
            store_error(SOURCE, ticker, "global_quote", f"unexpected: {data}")
            log_run("extract", SOURCE, "failure", error="no Global Quote")
            return 0

        stored += store_raw("raw_stock_prices", SOURCE, ticker, data)
        log_run("extract", SOURCE, "success", extracted=stored, loaded=stored)
    except Exception as exc:
        store_error(SOURCE, ticker, "global_quote", exc)
        log_run("extract", SOURCE, "failure", error=str(exc))

    return stored


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    n = extract(tk)
    print(f"Alpha Vantage: stored {n} raw document(s) for {tk}")