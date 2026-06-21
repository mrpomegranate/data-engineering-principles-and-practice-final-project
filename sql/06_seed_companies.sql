-- ============================================================
-- 06_seed_companies.sql  —  Seed data for company_dim
-- Runs after sources (05). The 11 tracked tickers. Sector/industry
-- are seeded here as a baseline; the pipeline can later refresh them
-- from Finnhub's company profile if desired.
-- ============================================================
 
INSERT INTO company_dim (ticker, company_name, exchange, sector, industry) VALUES
    ('AAPL', 'Apple Inc.',                         'NASDAQ', 'Technology',  'Consumer Electronics'),
    ('MSFT', 'Microsoft Corporation',              'NASDAQ', 'Technology',  'Software'),
    ('NVDA', 'NVIDIA Corporation',                 'NASDAQ', 'Technology',  'Semiconductors'),
    ('AMD',  'Advanced Micro Devices, Inc.',       'NASDAQ', 'Technology',  'Semiconductors'),
    ('TSLA', 'Tesla, Inc.',                        'NASDAQ', 'Automotive',  'Auto Manufacturers'),
    ('AMZN', 'Amazon.com, Inc.',                   'NASDAQ', 'Consumer Cyclical', 'Internet Retail'),
    ('MU',   'Micron Technology, Inc.',            'NASDAQ', 'Technology',  'Semiconductors'),
    ('ASML', 'ASML Holding N.V.',                  'NASDAQ', 'Technology',  'Semiconductor Equipment'),
    ('INTC', 'Intel Corporation',                  'NASDAQ', 'Technology',  'Semiconductors'),
    ('AMAT', 'Applied Materials, Inc.',            'NASDAQ', 'Technology',  'Semiconductor Equipment'),
    ('ARM',  'Arm Holdings plc',                   'NASDAQ', 'Technology',  'Semiconductors')
ON CONFLICT (ticker) DO NOTHING;
 