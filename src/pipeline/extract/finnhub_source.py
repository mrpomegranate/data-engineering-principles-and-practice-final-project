"""
Finnhub extractor — the primary source.

Pulls three endpoints for a ticker and stores each raw response in Mongo:
    company profile  -> raw_company_profiles
    quote            -> raw_stock_prices
    company news     -> raw_headlines

Run standalone for one ticker:
    python -m src.pipeline.extract.finnhub_source AAPL
"""

import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

from .http_client import get_json
from .mongo_store import store_raw, store_error
from .run_logger import log_run

load_dotenv(override=True)

BASE = "https://finnhub.io/api/v1"
SOURCE = "finnhub"


def extract(ticker: str) -> int:
    """Extract profile, quote, and news for one ticker. Returns docs stored."""
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        log_run("extract", SOURCE, "failure", error="FINNHUB_API_KEY missing")
        raise RuntimeError("FINNHUB_API_KEY missing from environment")

    stored = 0

    # 1) Company profile -> raw_company_profiles
    try:
        profile = get_json(f"{BASE}/stock/profile2",
                           {"symbol": ticker, "token": key})
        stored += store_raw("raw_company_profiles", SOURCE, ticker, profile)
    except Exception as exc:
        store_error(SOURCE, ticker, "profile", exc)

    # 2) Quote -> raw_stock_prices
    try:
        quote = get_json(f"{BASE}/quote", {"symbol": ticker, "token": key})
        stored += store_raw("raw_stock_prices", SOURCE, ticker, quote)
    except Exception as exc:
        store_error(SOURCE, ticker, "quote", exc)

    # 3) Company news (last 10 days) -> raw_headlines
    try:
        today = date.today()
        news = get_json(f"{BASE}/company-news", {
            "symbol": ticker,
            "from": (today - timedelta(days=10)).isoformat(),
            "to": today.isoformat(),
            "token": key,
        })
        # news is a list; store the whole list as one raw document
        stored += store_raw("raw_headlines", SOURCE, ticker, news)
    except Exception as exc:
        store_error(SOURCE, ticker, "news", exc)

    status = "success" if stored == 3 else ("partial" if stored else "failure")
    log_run("extract", SOURCE, status, extracted=stored, loaded=stored)
    return stored


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    n = extract(tk)
    print(f"Finnhub: stored {n} raw documents for {tk}")
