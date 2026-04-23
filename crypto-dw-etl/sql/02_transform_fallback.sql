-- ============================================================================
-- Script: 02_transform_fallback.sql
-- Purpose: Populate staging.fact_prep directly from staging.ohlcv_raw when
--          Pentaho cleaning/transform has not been completed yet.
-- Assumptions:
--   - staging.ohlcv_raw has columns matching the raw Binance CSV header:
--     symbol, open_time, open, high, low, close, volume, ...
--   - gold.dim_coin, gold.dim_category and gold.dim_date have already been
--     created and seeded.
--   - open_time is stored as epoch milliseconds from Binance.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

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

TRUNCATE TABLE staging.fact_prep;

WITH typed_source AS (
    SELECT
        CAST(TO_CHAR(((TO_TIMESTAMP(r.open_time::BIGINT / 1000.0) AT TIME ZONE 'UTC')::DATE), 'YYYYMMDD') AS INT)
            AS date_id,
        ((TO_TIMESTAMP(r.open_time::BIGINT / 1000.0) AT TIME ZONE 'UTC')::DATE) AS full_date,
        c.coin_id,
        c.category_id,
        CAST(r.open AS NUMERIC(18,8)) AS open,
        CAST(r.high AS NUMERIC(18,8)) AS high,
        CAST(r.low AS NUMERIC(18,8)) AS low,
        CAST(r.close AS NUMERIC(18,8)) AS close,
        CAST(r.volume AS NUMERIC(20,8)) AS volume_base
    FROM staging.ohlcv_raw AS r
    INNER JOIN gold.dim_coin AS c
        ON UPPER(TRIM(r.symbol)) = UPPER(TRIM(c.symbol))
    WHERE r.symbol IS NOT NULL
      AND r.open_time IS NOT NULL
      AND r.open IS NOT NULL
      AND r.high IS NOT NULL
      AND r.low IS NOT NULL
      AND r.close IS NOT NULL
      AND r.volume IS NOT NULL
),
base_metrics AS (
    SELECT
        s.date_id,
        s.full_date,
        s.coin_id,
        s.category_id,
        s.open,
        s.high,
        s.low,
        s.close,
        s.volume_base,
        ROUND(s.close * s.volume_base, 2) AS volume_usd,
        CASE
            WHEN s.open = 0 THEN NULL
            ELSE ROUND(((s.close - s.open) / s.open) * 100, 4)
        END AS return_pct,
        CASE
            WHEN s.open <= 0 OR s.close <= 0 THEN NULL
            ELSE ROUND(LN(s.close) - LN(s.open), 6)
        END AS log_return,
        ROUND(s.high - s.low, 8) AS volatility,
        ROUND((s.high + s.low) / 2, 8) AS average_price
    FROM typed_source AS s
),
rolling_stats AS (
    SELECT
        m.*,
        AVG(m.close) OVER (
            PARTITION BY m.coin_id
            ORDER BY m.full_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS rolling_mean_close,
        STDDEV_SAMP(m.close) OVER (
            PARTITION BY m.coin_id
            ORDER BY m.full_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS rolling_std_close
    FROM base_metrics AS m
)
INSERT INTO staging.fact_prep (
    date_id,
    coin_id,
    category_id,
    open,
    high,
    low,
    close,
    volume_base,
    volume_usd,
    return_pct,
    log_return,
    volatility,
    average_price,
    z_score_close
)
SELECT
    r.date_id,
    r.coin_id,
    r.category_id,
    r.open,
    r.high,
    r.low,
    r.close,
    r.volume_base,
    r.volume_usd,
    r.return_pct,
    r.log_return,
    r.volatility,
    r.average_price,
    CASE
        WHEN r.rolling_std_close IS NULL OR r.rolling_std_close = 0 THEN NULL
        ELSE ROUND((r.close - r.rolling_mean_close) / r.rolling_std_close, 4)
    END AS z_score_close
FROM rolling_stats AS r
INNER JOIN gold.dim_date AS d
    ON d.date_id = r.date_id;
