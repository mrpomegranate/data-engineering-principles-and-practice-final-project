# Flask API Specification — MarketPulse

The data contract between the Flask API and the React dashboard. The API is the
**only** component that touches PostgreSQL; the dashboard consumes these
endpoints exclusively. Column names align with the final 9-table dimensional
warehouse (3 dims + 5 facts + pipeline_run_log).

The React dashboard is a stretch/polish layer — the rubric requires the API,
not the dashboard. These endpoints stand on their own and are demonstrable in a
browser or via curl regardless of whether the dashboard is built.

## Conventions

- **Base URL:** `http://localhost:5000` (host) / `http://api:5000` (inside the
  Docker network, using the compose service name).
- **Format:** plain JSON. Lists return a top-level JSON array; single objects
  return a JSON object. No envelope wrapper.
- **Auth:** none. The API is reachable only within the Docker Compose network
  plus the published port for local dashboard development. (Document this as a
  deliberate scoping decision — production would add auth + TLS.)
- **Read-only (MVP):** the Flask API only reads from PostgreSQL and returns
  JSON. It does not write to the database. All writes (raw → Mongo, cleaned →
  Postgres, run status → `pipeline_run_log`) are handled by the scheduled
  pipeline. Responsibility split: pipeline writes, API reads, dashboard
  consumes API responses only.
- **Dashboard is optional:** these endpoints are the core web API deliverable
  and can be demonstrated independently using a browser, Postman, or curl — the
  React dashboard is a polish layer, not a requirement.
- **Dates:** ISO 8601 (`YYYY-MM-DD` for days, full timestamps with `Z` for
  events).
- **Tickers:** uppercase. Unknown ticker → `404`.
- **Errors:** JSON `{"error": "message"}` with an appropriate status code
  (`400` bad params, `404` not found, `500` server error).
- **CORS:** enabled (flask-cors) so the React dev server can call the API
  cross-origin.

---

## Endpoints

### 1. Health & metadata

#### `GET /health`
Liveness check — used by docker-compose healthcheck and the grader to confirm
the service is up.
```json
{ "status": "ok", "database": "connected" }
```

#### `GET /companies`
List every tracked company (from `company_dim`). Powers the dashboard's ticker
selector.
```json
[
  { "ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ" },
  { "ticker": "NVDA", "company_name": "NVIDIA Corp.", "sector": "Technology", "exchange": "NASDAQ" }
]
```

---

### 2. Raw data endpoints (drill-down / inspection)

#### `GET /headlines/{ticker}`
Recent scored headlines for one company. Joins `headline_fact` to `source_dim`
and returns the `sentiment_label` and `sentiment_score` stored on each headline
row. (Per-headline scores live in `headline_fact`, not in
`sentiment_aggregate_fact` — the aggregate table holds daily rollups only.)

Query params:
- `limit` (int, default 50, max 200)
- `from`, `to` (ISO date, optional range filter)
- `source_type` (optional: `news_api`, `social_media`, `sec_filing`)

```json
[
  {
    "headline_id": 1432,
    "published_at": "2026-06-12T14:05:00Z",
    "title": "Apple unveils new AI chip lineup",
    "source_name": "Reuters",
    "source_type": "news_api",
    "author": null,
    "sentiment_label": "positive",
    "sentiment_score": 0.62,
    "article_url": "https://..."
  }
]
```

#### `GET /prices/{ticker}`
Daily OHLCV rows from `stock_price_fact`. Powers the price line on the chart.

Query params: `from`, `to` (ISO date), `limit` (default 90).
```json
[
  { "trading_date": "2026-06-12", "open_price": 291.7, "high_price": 297.0, "low_price": 290.4, "close_price": 295.6, "adjusted_close_price": 295.6, "volume": 42523300, "average_volume": 51230000 }
]
```

---

### 3. Aggregate endpoints (the analysis — primary dashboard data)

#### `GET /sentiment/{ticker}`
Daily aggregated sentiment from `sentiment_aggregate_fact`. The core series the
dashboard plots against price.

Query params: `days` (int, default 30, max 365).
```json
[
  {
    "date": "2026-06-12",
    "headline_count": 18,
    "avg_sentiment_score": 0.34,
    "positive_count": 11,
    "neutral_count": 4,
    "negative_count": 3
  }
]
```

#### `GET /sentiment-vs-price/{ticker}`
**The headline endpoint of the project.** Joins daily sentiment aggregates to
daily price change — this is the SQL join you demo in Module 8 and the analysis
the whole pipeline exists to produce.

Query params: `days` (int, default 30).
```json
[
  {
    "date": "2026-06-12",
    "avg_sentiment_score": 0.34,
    "headline_count": 18,
    "close": 295.6,
    "pct_change_1day": 1.4,
    "next_day_pct_change": -0.8
  }
]
```

#### `GET /reactions/{ticker}`
Per-headline price reaction windows from `price_reaction_fact`. Supports the
"do specific headlines move the price?" view. Intraday windows may be null for
after-hours headlines (documented data-quality rule).

Query params: `limit` (default 50).
```json
[
  {
    "headline_id": 1432,
    "published_at": "2026-06-12T14:05:00Z",
    "title": "Apple unveils new AI chip lineup",
    "sentiment_score": 0.62,
    "price_at_publish": 294.1,
    "pct_change_15min": 0.3,
    "pct_change_1hr": 0.7,
    "pct_change_1day": 1.4
  }
]
```

#### `GET /report`
The single aggregated analytical report across all tracked tickers — satisfies
the rubric's "aggregated view or analytical report" requirement directly.
Returns one summary row per company.
```json
[
  {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "headline_count": 244,
    "avg_sentiment_score": 0.21,
    "avg_daily_pct_change": 0.4,
    "sentiment_price_correlation": 0.18
  }
]
```

#### `GET /status` (optional, supports the run log)
Most recent pipeline run results from `pipeline_run_log` — useful for the
dashboard's "last updated" indicator and for demoing that the pipeline logs its
own runs.
```json
[
  { "run_timestamp": "2026-06-12T02:00:00Z", "pipeline_step": "load", "source_name": "finnhub", "status": "success", "records_extracted": 244, "records_loaded": 244, "error_message": null }
]
```

---

## Mapping to the rubric

| Requirement | Endpoint(s) |
|---|---|
| API to export/consume an aggregated view | `/report`, `/sentiment-vs-price/{ticker}` |
| Query the data, readable format | all endpoints, JSON |
| Demonstrable join (Module 8) | SQL behind `/sentiment-vs-price/{ticker}` |
| Drill-down for documentation screenshots | `/headlines`, `/prices`, `/reactions` |

## Build order suggestion

1. `/health` — proves the API is running and can connect to the database.
2. `/status` — proves `pipeline_run_log` is populated; exposes latest run status.
3. `/companies` — proves `company_dim` is loaded.
4. `/prices/{ticker}` — simple read from `stock_price_fact`.
5. `/sentiment/{ticker}` — simple read from `sentiment_aggregate_fact`.
6. `/sentiment-vs-price/{ticker}` — main analytical join endpoint.
7. `/report` — cross-ticker aggregate report.
8. `/headlines/{ticker}` — drill-down endpoint.
9. `/reactions/{ticker}` — lower-priority / stretch drill-down endpoint.

## Minimal implementation skeleton

```python
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2.extras

app = Flask(__name__)
CORS(app)

def query(sql, params=()):
    conn = get_connection()          # reads POSTGRES_* from env
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()

@app.get("/health")
def health():
    try:
        query("SELECT 1")
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        return jsonify({"status": "error", "database": "unreachable"}), 500

@app.get("/sentiment/<ticker>")
def sentiment(ticker):
    days = min(int(request.args.get("days", 30)), 365)
    rows = query(
        """
        SELECT s.window_start::date AS date, s.headline_count,
               s.avg_sentiment_score, s.positive_count,
               s.neutral_count, s.negative_count
        FROM sentiment_aggregate_fact s
        JOIN company_dim c ON c.company_id = s.company_id
        WHERE c.ticker = %s
          AND s.window_start >= NOW() - (%s || ' days')::interval
        ORDER BY s.window_start
        """,
        (ticker.upper(), days),
    )
    if not rows:
        return jsonify({"error": f"No data for ticker {ticker}"}), 404
    return jsonify(rows)
```

Use parameterized queries everywhere (`%s`, never f-strings) — that's your
Module 12 SQL-injection-prevention talking point, demonstrated in code.
