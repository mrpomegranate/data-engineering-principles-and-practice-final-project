"""
Warehouse helper — shared by all load steps.

Provides the Postgres connection and cached dimension lookups so loaders
can resolve foreign keys (ticker -> company_id, source name -> source_id,
date -> date_id) without a query per row.

Daily-grain date lookups match date_dim rows where hour/minute are NULL.
"""

import os
from datetime import date

import psycopg
from dotenv import load_dotenv

load_dotenv(override=True)


def get_connection():
    """Open a PostgreSQL connection from environment settings."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "stock_sentiment"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "change_me_locally"),
    )


class DimCache:
    """
    In-memory cache of the three dimension tables' keys.

    Load once per pipeline run; lookups are then dict reads instead of
    per-row SQL queries.
    """

    def __init__(self, conn):
        self._company = {}   # ticker -> company_id
        self._source = {}    # source_name -> source_id
        self._date = {}      # date -> date_id (daily grain: hour/minute NULL)

        with conn.cursor() as cur:
            cur.execute("SELECT ticker, company_id FROM company_dim")
            self._company = {t: cid for t, cid in cur.fetchall()}

            cur.execute("SELECT source_name, source_id FROM source_dim")
            self._source = {s: sid for s, sid in cur.fetchall()}

            cur.execute(
                "SELECT full_date, date_id FROM date_dim "
                "WHERE hour IS NULL AND minute IS NULL"
            )
            self._date = {d: did for d, did in cur.fetchall()}

    def company_id(self, ticker: str):
        """company_id for a ticker, or None if not a tracked company."""
        return self._company.get(ticker.upper())

    def source_id(self, source_name: str):
        """source_id for a source name, or None if unknown."""
        return self._source.get(source_name)

    def date_id(self, d: date):
        """date_id for a calendar date (daily grain), or None if outside
        the populated date_dim range."""
        return self._date.get(d)