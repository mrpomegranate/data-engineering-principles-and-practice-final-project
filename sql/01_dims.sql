-- ============================================================
-- 01_dims.sql  —  Dimension tables
-- Runs first: facts depend on these via foreign keys.
-- MarketPulse star schema (3 dimensions).
-- ============================================================

-- ---------- COMPANY_DIM ----------
-- One row per tracked company. ticker is the natural key (unique);
-- company_id is the surrogate key used by all fact FKs.
CREATE TABLE company_dim (
    company_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker        VARCHAR(10)  NOT NULL UNIQUE,
    company_name  VARCHAR(255) NOT NULL,
    exchange      VARCHAR(50),
    sector        VARCHAR(100),
    industry      VARCHAR(100)
);

-- ---------- SOURCE_DIM ----------
-- One row per data source (finnhub, newsapi, yfinance, alphavantage).
-- source_type groups them (news_api, market_data, social_media, ...).
CREATE TABLE source_dim (
    source_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name  VARCHAR(100) NOT NULL UNIQUE,
    source_type  VARCHAR(50)  NOT NULL,
    base_url     VARCHAR(255)
);

-- ---------- DATE_DIM ----------
-- Calendar/time dimension. date_id is the surrogate key referenced by
-- all facts. Granularity supports both daily and intraday analysis.
-- is_market_day / market_session help with after-hours headline rules.
CREATE TABLE date_dim (
    date_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_date       DATE    NOT NULL,
    year            INT     NOT NULL,
    quarter         INT     NOT NULL,
    month           INT     NOT NULL,
    day             INT     NOT NULL,
    day_of_week     INT     NOT NULL,           -- 0=Sunday ... 6=Saturday
    hour            INT,                          -- nullable: day-grain rows
    minute          INT,
    is_market_day   BOOLEAN NOT NULL DEFAULT TRUE,
    market_session  VARCHAR(20),                 -- pre_market | regular | after_hours | closed
    CONSTRAINT uq_date_dim_datetime UNIQUE (full_date, hour, minute)
);
