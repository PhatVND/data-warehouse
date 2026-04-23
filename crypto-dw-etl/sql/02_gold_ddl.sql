-- ============================================================================
-- Script: 02_gold_ddl.sql
-- Purpose: Create the gold star schema for the CryptoDW-ETL MVP.
-- Notes:
--   1. This script is idempotent and can be re-run safely.
--   2. Seed loading for dim_category and dim_coin is expected to be done
--      separately from seed CSV files after this DDL completes.
--   3. dim_date is populated by sql/dim_date_seed.sql.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_category (
    category_id      INT PRIMARY KEY,
    category_name    VARCHAR(32) NOT NULL UNIQUE,
    risk_level       VARCHAR(8) NOT NULL,
    CONSTRAINT ck_dim_category_risk_level
        CHECK (risk_level IN ('Low', 'Mid', 'High'))
);

CREATE TABLE IF NOT EXISTS gold.dim_coin (
    coin_id          INT PRIMARY KEY,
    symbol           VARCHAR(10) NOT NULL UNIQUE,
    full_name        VARCHAR(64) NOT NULL,
    launch_year      SMALLINT,
    category_id      INT NOT NULL,
    CONSTRAINT fk_dim_coin_category
        FOREIGN KEY (category_id) REFERENCES gold.dim_category (category_id)
);

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_id          INT PRIMARY KEY,
    full_date        DATE NOT NULL UNIQUE,
    day              SMALLINT NOT NULL,
    week             SMALLINT NOT NULL,
    month            SMALLINT NOT NULL,
    quarter          SMALLINT NOT NULL,
    year             SMALLINT NOT NULL,
    day_of_week      VARCHAR(10) NOT NULL,
    is_weekend       BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.fact_market_daily (
    date_id                INT NOT NULL,
    coin_id                INT NOT NULL,
    category_id            INT NOT NULL,
    open                   NUMERIC(18,8) NOT NULL,
    high                   NUMERIC(18,8) NOT NULL,
    low                    NUMERIC(18,8) NOT NULL,
    close                  NUMERIC(18,8) NOT NULL,
    volume_base            NUMERIC(20,4) NOT NULL,
    volume_usd             NUMERIC(20,2) NOT NULL,
    return_pct             NUMERIC(10,4),
    log_return             NUMERIC(10,6),
    volatility             NUMERIC(18,8) NOT NULL,
    average_price          NUMERIC(18,8) NOT NULL,
    z_score_close          NUMERIC(10,4),
    is_anomaly             BOOLEAN NOT NULL,
    volume_rank            INT NOT NULL,
    market_dominance_pct   NUMERIC(6,3),
    regime_label           VARCHAR(16) NOT NULL,
    CONSTRAINT pk_fact_market_daily
        PRIMARY KEY (date_id, coin_id),
    CONSTRAINT fk_fact_market_daily_date
        FOREIGN KEY (date_id) REFERENCES gold.dim_date (date_id),
    CONSTRAINT fk_fact_market_daily_coin
        FOREIGN KEY (coin_id) REFERENCES gold.dim_coin (coin_id),
    CONSTRAINT fk_fact_market_daily_category
        FOREIGN KEY (category_id) REFERENCES gold.dim_category (category_id),
    CONSTRAINT ck_fact_market_daily_prices
        CHECK (high >= low),
    CONSTRAINT ck_fact_market_daily_volume_base
        CHECK (volume_base >= 0),
    CONSTRAINT ck_fact_market_daily_volume_usd
        CHECK (volume_usd >= 0),
    CONSTRAINT ck_fact_market_daily_regime
        CHECK (regime_label IN ('Bull', 'Bear', 'Sideways'))
);

CREATE INDEX IF NOT EXISTS idx_fact_market_daily_coin_id
    ON gold.fact_market_daily (coin_id);

CREATE INDEX IF NOT EXISTS idx_fact_market_daily_category_id
    ON gold.fact_market_daily (category_id);

CREATE INDEX IF NOT EXISTS idx_fact_market_daily_date_volume_rank
    ON gold.fact_market_daily (date_id, volume_rank);
