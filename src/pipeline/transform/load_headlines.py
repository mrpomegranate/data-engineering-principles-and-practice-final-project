"""
Load headlines: raw Finnhub + NewsAPI documents (Mongo) -> headline_fact.

The two sources return structurally different JSON — this module conforms
both to the same fact rows:

  Finnhub  payload = LIST of articles:
      {datetime (unix seconds), headline, source, url, summary, ...}
  NewsAPI  payload = OBJECT:
      {status, totalResults, articles: [{source:{name}, author, title,
       url, publishedAt (ISO), ...}]}

Transform steps per source:
  1. Read the LATEST raw document for the ticker.
  2. Parse each article: timestamp -> UTC datetime, extract text/url/author.
  3. Resolve FKs via DimCache (company_id, source_id, date_id from the
     published date).
  4. Insert with ON CONFLICT (company_id, article_url, published_timestamp)
     DO NOTHING — headlines are immutable, so re-runs and cross-run
     duplicates are silently skipped (idempotent dedup via the constraint).

sentiment_label / sentiment_score are left NULL here — card 9 (VADER)
scores them in a separate pass.

Run standalone:
    python -m src.pipeline.transform.load_headlines AAPL
"""

import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from ..extract.mongo_store import get_mongo_db
from ..extract.run_logger import log_run
from ..load.warehouse import get_connection, DimCache

load_dotenv(override=True)

INSERT_SQL = """
    INSERT INTO headline_fact
        (company_id, source_id, date_id, published_timestamp,
         headline_text, article_url, author)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (company_id, article_url, published_timestamp) DO NOTHING
"""


def _parse_finnhub(payload):
    """Yield (published_dt, text, url, author) from a Finnhub article list."""
    for art in payload:
        ts = art.get("datetime")
        text = (art.get("headline") or "").strip()
        url = art.get("url")
        if not ts or not text or not url:
            continue
        published = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        yield published, text, url, None  # Finnhub has no author field


def _parse_newsapi(payload):
    """Yield (published_dt, text, url, author) from a NewsAPI response."""
    for art in payload.get("articles", []):
        raw_ts = art.get("publishedAt")          # e.g. 2026-06-10T21:15:33Z
        text = (art.get("title") or "").strip()
        url = art.get("url")
        if not raw_ts or not text or not url:
            continue
        published = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        yield published, text, url, art.get("author")


PARSERS = {
    "finnhub": _parse_finnhub,
    "newsapi": _parse_newsapi,
}


def load(ticker: str) -> int:
    """Transform + load latest headline docs from both sources.
    Returns total rows inserted (duplicates excluded)."""
    mongo = get_mongo_db()
    conn = get_connection()
    total_inserted = 0
    try:
        cache = DimCache(conn)
        company_id = cache.company_id(ticker)
        if company_id is None:
            raise RuntimeError(f"{ticker} not found in company_dim")

        for source_name, parser in PARSERS.items():
            doc = mongo["raw_headlines"].find_one(
                {"_source": source_name, "_ticker": ticker.upper()},
                sort=[("_ingested_at", -1)],
            )
            if not doc:
                log_run("load", source_name, "partial",
                        error=f"no raw headlines doc for {ticker}")
                print(f"{source_name}: no raw document for {ticker} — "
                      f"skipping (run the extractor first)")
                continue

            source_id = cache.source_id(source_name)
            rows, skipped = [], 0
            for published, text, url, author in parser(doc["payload"]):
                date_id = cache.date_id(published.date())
                if date_id is None:
                    skipped += 1     # outside date_dim's populated range
                    continue
                # strip tz for the TIMESTAMP (without tz) column, keep UTC
                rows.append((company_id, source_id, date_id,
                             published.replace(tzinfo=None),
                             text[:10000], url[:1000],
                             (author or None)))

            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, rows)
                inserted = cur.rowcount if cur.rowcount != -1 else len(rows)
            conn.commit()
            total_inserted += max(inserted, 0)
            log_run("load", source_name, "success",
                    extracted=len(rows), loaded=max(inserted, 0))
            print(f"{source_name}: parsed {len(rows)} headlines"
                  + (f", skipped {skipped} outside date range" if skipped else ""))
    except Exception as exc:
        conn.rollback()
        log_run("load", "headlines", "failure", error=str(exc))
        raise
    finally:
        conn.close()

    print(f"headline_fact: {total_inserted} new rows for {ticker} "
          f"(duplicates skipped via unique constraint)")
    return total_inserted


if __name__ == "__main__":
    tk = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    load(tk)