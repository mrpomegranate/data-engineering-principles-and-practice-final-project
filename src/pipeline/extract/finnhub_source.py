"""
Finnhub extractor — the primary source.

Pulls four endpoints for a ticker and stores each raw response in Mongo:
    company profile   -> raw_company_profiles
    quote             -> raw_stock_prices
    company news      -> raw_headlines
    basic financials  -> raw_company_metrics   (P/E, 52wk high/low, ...)

News windowing: Finnhub caps each company-news response at ~250 articles,
so ranges longer than CHUNK_DAYS are fetched in 7-day chunks and merged
into ONE raw document (keeps the loader's read-latest-doc logic intact).

Run standalone:
    python -m src.pipeline.extract.finnhub_source AAPL          # last 10 days
    python -m src.pipeline.extract.finnhub_source AAPL 365      # 1-year backfill
"""

import os
import sys
import time
from datetime import date, timedelta

from dotenv import load_dotenv

from .http_client import get_json
from .mongo_store import store_raw, store_error
from .run_logger import log_run

load_dotenv(override=True)

BASE = "https://finnhub.io/api/v1"
SOURCE = "finnhub"
EXPECTED_DOCS = 4
CHUNK_DAYS = 7          # keep each request comfortably under the ~250 cap
CHUNK_PAUSE = 0.3       # polite pacing; stays well within 60 calls/min


def _fetch_news(ticker: str, key: str, days: int) -> list:
    """Fetch company news over `days`, chunking long ranges. Returns one
    merged, de-duplicated (by article id/url) list of articles."""
    end = date.today()
    start = end - timedelta(days=days)
    articles, seen = [], set()

    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS - 1), end)
        batch = get_json(f"{BASE}/company-news", {
            "symbol": ticker,
            "from": chunk_start.isoformat(),
            "to": chunk_end.isoformat(),
            "token": key,
        })
        for art in batch or []:
            dedup_key = art.get("id") or art.get("url")
            if dedup_key and dedup_key not in seen:
                seen.add(dedup_key)
                articles.append(art)
        chunk_start = chunk_end + timedelta(days=1)
        if chunk_start <= end:
            time.sleep(CHUNK_PAUSE)
    return articles


def extract(ticker: str, news_days: int = 10) -> int:
    """Extract profile, quote, news (over news_days), and metrics.
    Returns docs stored."""
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

    # 3) Company news (chunked if long range) -> raw_headlines
    try:
        news = _fetch_news(ticker, key, news_days)
        stored += store_raw("raw_headlines", SOURCE, ticker, news)
        print(f"  news: {len(news)} articles over {news_days} days")
    except Exception as exc:
        store_error(SOURCE, ticker, "news", exc)

    # 4) Basic financials -> raw_company_metrics
    try:
        metrics = get_json(f"{BASE}/stock/metric",
                           {"symbol": ticker, "metric": "all", "token": key})
        stored += store_raw("raw_company_metrics", SOURCE, ticker, metrics)
    except Exception as exc:
        store_error(SOURCE, ticker, "metrics", exc)

    status = ("success" if stored == EXPECTED_DOCS
              else ("partial" if stored else "failure"))
    log_run("extract", SOURCE, status, extracted=stored, loaded=stored)
    return stored


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    n = extract(tk, news_days=days)
    print(f"Finnhub: stored {n} raw documents for {tk}")