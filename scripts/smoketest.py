"""
Phase 0 smoke test — verifies every team member's API keys work.

Usage:
    1. Make sure .env sits in this folder (copy .env.example if needed)
    2. pip install -r requirements.txt
    3. python smoke_test.py

Pulls one tiny piece of data per source and prints PASS / FAIL / SKIP.
- Uses the first ticker from TICKERS in .env (falls back to AAPL).
- Optional sources (Reddit) report SKIP when credentials are blank;
  skips don't count against the exit code.
- Safe to run repeatedly EXCEPT Alpha Vantage (~25 requests/day free tier).
"""

import os
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

TICKER = (os.getenv("TICKERS", "AAPL").split(",")[0] or "AAPL").strip().upper()
TIMEOUT = 15
results = {}  # name -> "pass" | "fail" | "skip"


def report(name: str, status: str, detail: str) -> None:
    results[name] = status
    print(f"[{status.upper():4}] {name}: {detail}")


def test_finnhub() -> None:
    """Real-time quote — feeds stock_price_fact."""
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        report("Finnhub", "fail", "FINNHUB_API_KEY missing from .env")
        return
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": TICKER, "token": key},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        price = data.get("c")  # current price
        if price:
            report("Finnhub", "pass",
                   f"{TICKER} current price = {price}, open = {data.get('o')}, "
                   f"high = {data.get('h')}, prev close = {data.get('pc')}")
        else:
            report("Finnhub", "fail", f"Unexpected response: {data}")
    except Exception as exc:
        report("Finnhub", "fail", str(exc))


def test_finnhub_news() -> None:
    """Company news — feeds headline_fact (your real-time headline source)."""
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        report("Finnhub news", "fail", "FINNHUB_API_KEY missing from .env")
        return
    try:
        today = date.today()
        r = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": TICKER,
                "from": (today - timedelta(days=10)).isoformat(),
                "to": today.isoformat(),
                "token": key,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        articles = r.json()
        if isinstance(articles, list) and articles:
            first = articles[0]
            report("Finnhub news", "pass",
                   f"{len(articles)} headlines in last 10 days, e.g. "
                   f"'{first.get('headline', '')[:60]}...' from {first.get('source')}")
        else:
            report("Finnhub news", "fail",
                   f"No articles returned for {TICKER}: {articles}")
    except Exception as exc:
        report("Finnhub news", "fail", str(exc))


def test_newsapi() -> None:
    """Keyword headlines — feeds headline_fact (free tier delays ~24h)."""
    key = os.getenv("NEWSAPI_KEY")
    if not key:
        report("NewsAPI", "fail", "NEWSAPI_KEY missing from .env")
        return
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": f"{TICKER} stock", "pageSize": 3,
                    "sortBy": "publishedAt", "apiKey": key},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles", [])
        if articles:
            first = articles[0]
            report("NewsAPI", "pass",
                   f"{data.get('totalResults')} total results, latest: "
                   f"'{first.get('title', '')[:60]}...' at {first.get('publishedAt')}")
        else:
            report("NewsAPI", "fail",
                   f"Status {data.get('status')}: {data.get('message')}")
    except Exception as exc:
        report("NewsAPI", "fail", str(exc))


def test_alpha_vantage() -> None:
    """Daily quote — BACKUP price source. CAREFUL: ~25 requests/day free."""
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        report("Alpha Vantage", "fail", "ALPHAVANTAGE_API_KEY missing from .env")
        return
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": TICKER, "apikey": key},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        quote = data.get("Global Quote", {})
        price = quote.get("05. price")
        if price:
            report("Alpha Vantage", "pass",
                   f"{TICKER} price = {price}, volume = {quote.get('06. volume')}")
        elif "Note" in data or "Information" in data:
            report("Alpha Vantage", "fail",
                   "Rate limited (free tier ~25/day). Key likely valid — retry tomorrow.")
        else:
            report("Alpha Vantage", "fail", f"Unexpected response: {data}")
    except Exception as exc:
        report("Alpha Vantage", "fail", str(exc))


def test_yfinance() -> None:
    """Historical OHLCV backfill — no key needed."""
    try:
        import yfinance as yf
    except ImportError:
        report("yfinance", "fail", "Not installed — run: pip install yfinance")
        return
    try:
        hist = yf.Ticker(TICKER).history(period="5d")
        if not hist.empty:
            last = hist.iloc[-1]
            report("yfinance", "pass",
                   f"{len(hist)} daily bars, latest close = "
                   f"{round(float(last['Close']), 2)}, volume = {int(last['Volume'])}")
        else:
            report("yfinance", "fail", "Empty history returned")
    except Exception as exc:
        report("yfinance", "fail", str(exc))


def test_reddit() -> None:
    """Optional social source — SKIPs until credentials are filled in."""
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        report("Reddit", "skip",
               "No credentials in .env yet (optional — fill in if app approved)")
        return
    try:
        import praw
    except ImportError:
        report("Reddit", "fail",
               "Credentials present but praw not installed — run: pip install praw")
        return
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=os.getenv("REDDIT_USER_AGENT", "stock-sentiment-pipeline/0.1"),
        )
        post = next(reddit.subreddit("stocks").new(limit=1))
        report("Reddit", "pass", f"Latest r/stocks post: '{post.title[:60]}...'")
    except Exception as exc:
        report("Reddit", "fail", str(exc))


if __name__ == "__main__":
    print(f"Phase 0 smoke test — ticker {TICKER}\n" + "-" * 50)
    test_finnhub()
    test_finnhub_news()
    test_newsapi()
    test_alpha_vantage()
    test_yfinance()
    # test_reddit()
    print("-" * 50)
    passed = sum(1 for s in results.values() if s == "pass")
    failed = sum(1 for s in results.values() if s == "fail")
    skipped = sum(1 for s in results.values() if s == "skip")
    print(f"{passed} passed, {failed} failed, {skipped} skipped")
    sys.exit(0 if failed == 0 else 1)