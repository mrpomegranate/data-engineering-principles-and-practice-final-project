"""
NewsAPI extractor — keyword headlines for a ticker.

Pulls recent articles matching the company and stores the raw response in
raw_headlines. Free tier delays articles ~24h and caps requests, so keep
the page size modest.

Run standalone:
    python -m src.pipeline.extract.newsapi_source AAPL
"""

import os
import sys

from dotenv import load_dotenv

from .http_client import get_json
from .mongo_store import store_raw, store_error
from .run_logger import log_run

load_dotenv(override=True)

BASE = "https://newsapi.org/v2/everything"
SOURCE = "newsapi"

# Map ticker -> a search query that captures the company by name, not just
# the symbol (the bare symbol returns noise). Extend as tickers are added.
QUERY_MAP = {
    "AAPL": "Apple stock",
    "MSFT": "Microsoft stock",
    "NVDA": "NVIDIA stock",
    "AMD":  "AMD stock",
    "TSLA": "Tesla stock",
    "AMZN": "Amazon stock",
    "MU":   "Micron stock",
    "ASML": "ASML stock",
    "INTC": "Intel stock",
    "AMAT": "Applied Materials stock",
    "ARM":  "Arm Holdings stock",
}


def extract(ticker: str) -> int:
    """Extract keyword headlines for one ticker. Returns docs stored."""
    key = os.getenv("NEWSAPI_KEY")
    if not key:
        log_run("extract", SOURCE, "failure", error="NEWSAPI_KEY missing")
        raise RuntimeError("NEWSAPI_KEY missing from environment")

    query = QUERY_MAP.get(ticker, f"{ticker} stock")
    stored = 0
    try:
        data = get_json(BASE, {
            "q": query,
            "pageSize": 20,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": key,
        })
        # store the whole response (articles list + metadata) as one raw doc
        stored += store_raw("raw_headlines", SOURCE, ticker, data)
        status = "success"
    except Exception as exc:
        store_error(SOURCE, ticker, "everything", exc)
        status = "failure"

    log_run("extract", SOURCE, status, extracted=stored, loaded=stored)
    return stored


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    n = extract(tk)
    print(f"NewsAPI: stored {n} raw document(s) for {tk}")
