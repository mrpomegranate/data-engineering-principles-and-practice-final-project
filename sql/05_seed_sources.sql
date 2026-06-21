-- ============================================================
-- 05_seed_sources.sql  —  Seed data for source_dim
-- Runs after the schema (04). These are the known data sources;
-- they don't come from an API, so we insert them once at setup.
-- ============================================================

INSERT INTO source_dim (source_name, source_type, base_url) VALUES
    ('finnhub',       'market_data', 'https://finnhub.io/api/v1'),
    ('newsapi',       'news_api',    'https://newsapi.org/v2'),
    ('yfinance',      'market_data', 'https://finance.yahoo.com'),
    ('alphavantage',  'market_data', 'https://www.alphavantage.co/query')
ON CONFLICT (source_name) DO NOTHING;