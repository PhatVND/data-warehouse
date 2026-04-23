-- ============================================================================
-- Script: 01_staging_ddl.sql
-- Purpose: Create staging tables required by the CryptoDW-ETL MVP.
-- Notes:
--   - ohlcv_raw is intentionally permissive because raw CSV lands here first.
--   - reject_log is reserved for TV2 cleaning/Pentaho reject handling.
--   - fact_prep can be populated either by Pentaho 02_transform or by
--     sql/02_transform_fallback.sql.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.ohlcv_raw (
    symbol                        VARCHAR(16),
    open_time                     BIGINT,
    open                          VARCHAR(64),
    high                          VARCHAR(64),
    low                           VARCHAR(64),
    close                         VARCHAR(64),
    volume                        VARCHAR(64),
    close_time                    BIGINT,
    quote_asset_volume            VARCHAR(64),
    number_of_trades              INT,
    taker_buy_base_asset_volume   VARCHAR(64),
    taker_buy_quote_asset_volume  VARCHAR(64),
    ignore_field                  VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS staging.reject_log (
    reject_id         BIGSERIAL PRIMARY KEY,
    source_file       VARCHAR(255),
    symbol            VARCHAR(16),
    open_time_raw     VARCHAR(64),
    reject_reason     VARCHAR(255) NOT NULL,
    rejected_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staging.fact_prep (
    date_id          INT NOT NULL,
    coin_id          INT NOT NULL,
    category_id      INT NOT NULL,
    open             NUMERIC(18,8) NOT NULL,
    high             NUMERIC(18,8) NOT NULL,
    low              NUMERIC(18,8) NOT NULL,
    close            NUMERIC(18,8) NOT NULL,
    volume_base      NUMERIC(20,8) NOT NULL,
    volume_usd       NUMERIC(20,2) NOT NULL,
    return_pct       NUMERIC(10,4),
    log_return       NUMERIC(10,6),
    volatility       NUMERIC(18,8) NOT NULL,
    average_price    NUMERIC(18,8) NOT NULL,
    z_score_close    NUMERIC(10,4),
    PRIMARY KEY (date_id, coin_id)
);

TRUNCATE TABLE staging.ohlcv_raw;
TRUNCATE TABLE staging.reject_log RESTART IDENTITY;
