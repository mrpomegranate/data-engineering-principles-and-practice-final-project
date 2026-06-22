"""
yfinance extractor — historical daily OHLCV backfill.

Unlike the API sources, yfinance is a Python library (no HTTP client, no
API key). It returns a pandas DataFrame, which we convert to JSON records
and store in raw_stock_prices. This is the source of price HISTORY (years
back), versus Finnhub's single current quote.

Run standalone:
    python -m src.pipeline.extract.yfinance_source AAPL
"""

import sys

import yfinance as yf
from dotenv import load_dotenv

from .mongo_store import store_raw, store_error
from .run_logger import log_run

load_dotenv(override=True)

SOURCE = "yfinance"


def extract(ticker: str, period: str = "5y") -> int:
    """
    Extract historical daily OHLCV for one ticker. Returns docs stored.

    period: how far back to pull (e.g. '5y', '1y', '6mo'). The raw daily
    bars are stored as a list of records under one Mongo document.
    """
    stored = 0
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d")
        if hist.empty:
            store_error(SOURCE, ticker, "history", "empty DataFrame returned")
            log_run("extract", SOURCE, "failure", error="empty history")
            return 0

        # DataFrame -> JSON-serializable records. Reset index so the Date
        # becomes a column; convert timestamps to ISO strings.
        hist = hist.reset_index()
        hist["Date"] = hist["Date"].astype(str)
        records = hist.to_dict(orient="records")

        stored += store_raw("raw_stock_prices", SOURCE, ticker, records)
        log_run("extract", SOURCE, "success",
                extracted=len(records), loaded=stored)
    except Exception as exc:
        store_error(SOURCE, ticker, "history", exc)
        log_run("extract", SOURCE, "failure", error=str(exc))

    return stored


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    n = extract(tk)
    print(f"yfinance: stored {n} raw document(s) for {tk}")
