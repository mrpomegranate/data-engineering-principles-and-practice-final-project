"""
Project scaffold generator — creates any missing folders/stubs for the
stock sentiment pipeline project. Safe to run repeatedly: it NEVER
overwrites or modifies anything that already exists.

Usage (from the project root):
    python scaffold.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Directories to ensure exist (empty ones get a .gitkeep so Git tracks them)
DIRECTORIES = [
    "docker",
    "src/pipeline/extract",
    "src/pipeline/transform",
    "src/pipeline/load",
    "src/api",
    "sql",
    "automation",
    "data/samples",
    "data/seed",
    "docs/erd",
    "docs/screenshots",
    "scripts",
    "tests",
]

# Stub files created only if missing: path -> first-line content
STUBS = {
    "src/__init__.py": "",
    "src/pipeline/__init__.py": "",
    "src/pipeline/extract/__init__.py": "",
    "src/pipeline/transform/__init__.py": "",
    "src/pipeline/load/__init__.py": "",
    "src/api/__init__.py": "",
    "src/pipeline/extract/finnhub_source.py":
        '"""Extract: Finnhub quotes, fundamentals, company news -> raw records."""\n',
    "src/pipeline/extract/newsapi_source.py":
        '"""Extract: NewsAPI keyword headlines -> raw records."""\n',
    "src/pipeline/extract/yfinance_source.py":
        '"""Extract: yfinance historical OHLCV backfill -> raw records."""\n',
    "src/pipeline/extract/alphavantage_source.py":
        '"""Extract: Alpha Vantage daily quotes (BACKUP source, ~25 req/day)."""\n',
    "src/pipeline/extract/finra_source.py":
        '"""Extract: FINRA bi-monthly short interest CSV -> raw records."""\n',
    "src/pipeline/transform/clean.py":
        '"""Transform: nulls, timezone normalization, dedup, schema conformance."""\n',
    "src/pipeline/transform/sentiment.py":
        '"""Transform: VADER sentiment scoring for headline_fact."""\n',
    "src/pipeline/transform/aggregate.py":
        '"""Transform: build sentiment_aggregate_fact and price_reaction_fact."""\n',
    "src/pipeline/load/db.py":
        '"""Load: PostgreSQL connection helpers and table loaders."""\n',
    "src/pipeline/run_pipeline.py":
        '"""Entry point: runs extract -> transform -> load end to end."""\n\n\n'
        'def main() -> None:\n'
        '    raise NotImplementedError("Pipeline not built yet — Phase 2")\n\n\n'
        'if __name__ == "__main__":\n'
        '    main()\n',
    "sql/01_create_tables.sql":
        "-- DDL: all dim and fact tables, keys, constraints (Phase 2)\n",
    "sql/02_seed_source_dim.sql":
        "-- Seed reference rows for source_dim (finnhub, newsapi, yfinance, ...)\n",
    "docker-compose.yml":
        "# Orchestrates db + pipeline + api services (Phase 2/4)\n",
    "docker/Dockerfile.pipeline":
        "# Image for the ETL pipeline (Phase 2)\n",
    "docker/Dockerfile.api":
        "# Image for the Flask API (Phase 3)\n",
    ".env.example":
        "# Template — copy to .env and fill in your own keys (see team docs)\n",
}


def main() -> None:
    created_dirs, created_files, skipped = [], [], 0

    for d in DIRECTORIES:
        path = ROOT / d
        if not path.exists():
            path.mkdir(parents=True)
            created_dirs.append(d)

    for rel, content in STUBS.items():
        path = ROOT / rel
        if path.exists():
            skipped += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created_files.append(rel)

    # .gitkeep so Git tracks intentionally-empty folders
    for d in DIRECTORIES:
        path = ROOT / d
        if path.is_dir() and not any(path.iterdir()):
            (path / ".gitkeep").write_text("", encoding="utf-8")
            created_files.append(f"{d}/.gitkeep")

    print(f"Created {len(created_dirs)} directories:")
    for d in created_dirs:
        print(f"  + {d}/")
    print(f"Created {len(created_files)} files:")
    for f in created_files:
        print(f"  + {f}")
    print(f"Skipped {skipped} existing files (never overwritten).")

    reminders = []
    if (ROOT / "smoketest.py").exists():
        reminders.append("Move smoketest.py into scripts/ (git mv smoketest.py scripts/smoke_test.py)")
    if (ROOT / "main.py").exists():
        reminders.append("main.py is likely redundant with src/pipeline/run_pipeline.py — delete or repurpose")
    if (ROOT / "app.py").exists():
        reminders.append("app.py at root should eventually live at src/api/app.py")
    if reminders:
        print("\nManual cleanup suggestions:")
        for r in reminders:
            print(f"  - {r}")


if __name__ == "__main__":
    main()