"""
Mongo connection helper — the raw JSON landing zone.

All extractors write their untouched API responses here before any
transformation happens. Reads connection settings from environment
(loaded from .env). Collections:
    raw_headlines, raw_stock_prices, raw_company_profiles,
    raw_company_metrics, raw_api_errors
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient

_client = None


def get_mongo_db():
    """Return the marketpulse_raw database, reusing one client connection."""
    global _client
    if _client is None:
        user = os.getenv("MONGO_USER", "marketpulse")
        password = os.getenv("MONGO_PASSWORD", "change_me_locally")
        host = os.getenv("MONGO_HOST", "localhost")
        port = os.getenv("MONGO_PORT", "27017")
        uri = f"mongodb://{user}:{password}@{host}:{port}/"
        _client = MongoClient(uri)
    db_name = os.getenv("MONGO_DB", "marketpulse_raw")
    return _client[db_name]


def store_raw(collection_name: str, source: str, ticker: str, payload) -> int:
    """
    Store a raw API response in the given collection with metadata.

    Wraps the payload so we always know where each document came from and
    when it landed. Returns the number of documents inserted.
    """
    db = get_mongo_db()
    doc = {
        "_source": source,
        "_ticker": ticker,
        "_ingested_at": datetime.now(timezone.utc),
        "payload": payload,
    }
    result = db[collection_name].insert_one(doc)
    return 1 if result.inserted_id else 0


def store_error(source: str, ticker: str, step: str, error: str) -> None:
    """Record a failed extraction in raw_api_errors for later inspection."""
    db = get_mongo_db()
    db["raw_api_errors"].insert_one({
        "_source": source,
        "_ticker": ticker,
        "_step": step,
        "_ingested_at": datetime.now(timezone.utc),
        "error": str(error),
    })
