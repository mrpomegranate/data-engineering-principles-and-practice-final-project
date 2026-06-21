"""
Shared HTTP client with retry + exponential backoff.

Transient failures (timeouts, 5xx, connection blips) are retried a few
times with increasing waits, so one network hiccup doesn't fail a run.
Permanent failures (4xx like a bad key) are NOT retried — retrying won't
help, so we surface them immediately.
"""

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

TIMEOUT = 15


class TransientHTTPError(Exception):
    """Raised for retryable failures (timeouts, 5xx)."""


@retry(
    retry=retry_if_exception_type(TransientHTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def get_json(url: str, params: dict = None) -> dict:
    """
    GET a URL and return parsed JSON, retrying transient errors up to 3x.

    Raises TransientHTTPError on timeouts/5xx (which triggers retry) and
    requests.HTTPError on 4xx (which does not — a bad key won't fix itself).
    """
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
    except (requests.Timeout, requests.ConnectionError) as exc:
        raise TransientHTTPError(str(exc)) from exc

    if resp.status_code >= 500:
        raise TransientHTTPError(f"{resp.status_code} server error from {url}")
    resp.raise_for_status()  # raises requests.HTTPError on other 4xx
    return resp.json()
