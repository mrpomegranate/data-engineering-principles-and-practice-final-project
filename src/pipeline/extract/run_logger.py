"""
Pipeline run logger — writes one row to pipeline_run_log per step.

Gives every extract/transform/load step an audit trail: what ran, against
which source, success or failure, how many records, and any error. This is
what powers the /status API endpoint and the dashboard's pipeline panel.
"""

import os

import psycopg


def get_pg_connection():
    """Open a PostgreSQL connection from environment settings."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "stock_sentiment"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "change_me_locally"),
    )


def log_run(step: str, source: str, status: str,
            extracted: int = 0, loaded: int = 0, error: str = None) -> None:
    """
    Insert a row into pipeline_run_log.

    status: 'success' | 'failure' | 'partial'
    Uses a parameterized query (never string formatting) — same SQL-injection
    safe pattern used throughout the project.
    """
    sql = """
        INSERT INTO pipeline_run_log
            (pipeline_step, source_name, status,
             records_extracted, records_loaded, error_message)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (step, source, status, extracted, loaded, error))
        conn.commit()
    finally:
        conn.close()
