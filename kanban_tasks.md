# MarketPulse — Kanban Task List (18 cards)

Board: **Planned → In Progress → Finished**. All start in Planned, ordered as
the build sequence (top to bottom respects dependencies). Tags: `[phase]`.
Stretch quarantined at the bottom.

Format: **Title** `[phase]` — _done when:_ definition (sub-steps bulleted).

---

1. **Close out Phase 0** `[P0]` — _done when:_ ticker list clean everywhere; `curl_cffi` + `charset_normalizer` added; all teammates post a 5/5 smoke test; scaffold committed with `.env` gitignored.

2. **Write the database schema (DDL)** `[P1]` — _done when:_ split DDL (`01_dims.sql`, `02_facts.sql`, `03_indexes.sql`, `04_views.sql`) creates all 9 tables with PKs, FKs, NOT NULL, nullable stretch fields, idempotency unique constraints, indexes for API queries, and the `sentiment_vs_price` view; runs clean on an empty Postgres.

3. **Schema consistency pass** `[P1]` — _done when:_ all artifacts match the final DDL (table names, column names, nullable fields, view name). Checklist:
   - Flask API spec column/view names match DDL (e.g. `window_start`, `trading_date`, `sentiment_vs_price`)
   - ERD source (Mermaid) matches DDL table/column names
   - Architecture + sequence diagram notes still accurate
   - `.env` / seed / config files use the same ticker and source names
   - README / docs reference the correct table count (9) and view
   - _Re-open this card whenever the schema changes later._

4. **Seed & populate dimensions** `[P1]` — _done when:_ `source_dim` and `company_dim` seeded for all tickers/sources; `date_dim` generated across the project date range with market-session fields.

5. **Module 6 dataset check-in** `[P1]` (course) — _done when:_ 1–2 page concept + per-dataset description + join columns + 10 sample records each; submitted in Canvas.

6. **Stand up databases in Docker** `[P2]` — _done when:_ compose runs Postgres + Mongo; DDL auto-loads via init mount; local pgAdmin connects to `localhost:5432`; 5 Mongo raw collections write/read OK.

7. **Build extraction layer (raw → Mongo)** `[P2]` — _done when:_ shared client (auth/retry/error→`raw_api_errors`); Finnhub, NewsAPI, yfinance extract for **one ticker (AAPL)** into Mongo as raw JSON; Alpha Vantage fallback works; each run logged to `pipeline_run_log`.

8. **Build transform & load (Mongo → Postgres)** `[P2]` — _done when:_ cleaning/normalization (nulls, timezones→ET, dedup); date→date_id mapping; AAPL loaded into `headline_fact`, `stock_price_fact`, `company_metric_fact` with FKs resolved and no dupes; a cross-fact join returns sensible rows (saved for Module 8).

9. **Sentiment scoring & computed facts** `[P3]` — _done when:_ VADER label+score on each headline; `sentiment_aggregate_fact` (daily rollups) and `price_reaction_fact` (1-day; intraday nullable) populated.

10. **Scale to all tickers** `[P3]` — _done when:_ full ticker list runs end to end through extract→transform→load without rate-limit failures.

11. **Build the Flask API** `[P3]` — _done when:_ all endpoints live in build order (`/health`, `/status`, `/companies`, `/prices`, `/sentiment`, `/sentiment-vs-price`, `/report`, `/headlines`, `/reactions`); parameterized queries, JSON errors, CORS enabled.

12. **Automate the pipeline** `[P3]` — _done when:_ `run_pipeline.py` runs the whole thing in one command; scheduled via cron/Airflow in a container; re-run produces no duplicates.

13. **Module 8 pipeline video** `[course]` — _done when:_ 5–6 min team video: each member demos a component, schema shown, 2+ sources loading, join proven, division of labor stated.

14. **Containerize everything** `[P4]` — _done when:_ `Dockerfile.pipeline` + `Dockerfile.api` build; full compose brings up db+mongo+pipeline+api with service-name networking; `.env.example` + README (Docker-only assumption); seed/fallback dataset included.

15. **Verify reproducibility** `[P4]` — _done when:_ two-command rule works; a teammate runs the repo from scratch on a clean machine with only Docker, and anything that breaks is fixed.

16. **ERD as PDF** `[P4]` (docs) — _done when:_ final ERD exported from Draw.io/Lucidchart to PDF, matching the actual schema.

17. **Write documentation PDF** `[P4]` (docs) — _done when:_ intro, dataset overview, transform description, schema description, automation/API, decisions, screenshots, and Docker-only run instructions; includes architecture + sequence diagrams and the GenAI usage reflection.

18. **Module 11 final submission** `[course]` — _done when:_ all deliverables zipped with correct structure and submitted; internal peer review done.

19. **Module 12 external peer review** `[course]` — _done when:_ assigned team's project graded against the rubric in Canvas.

---

**STRETCH (only after MVP is solid):** React dashboard (shell + main chart + distribution/volume panels from the API), intraday reaction windows, and extra sources/models (Reddit, FinBERT, borrow rate). Make these one card each if/when you pull them.

**Recurring:** weekly standup post — handle as a repeating card or checklist, not a one-off.