-- ============================================================================
-- Script: 03_load_gold.sql
-- Purpose: Full-load gold.fact_market_daily from staging.fact_prep.
-- Notes:
--   - Run this only after staging.fact_prep has been fully refreshed.
--   - This script intentionally keeps business logic in SQL so TV4/TV5 can
--     validate outputs without depending on Pentaho internals.
-- ============================================================================

TRUNCATE TABLE gold.fact_market_daily;

WITH prepared AS (
    SELECT
        fp.date_id,
        fp.coin_id,
        fp.category_id,
        fp.open,
        fp.high,
        fp.low,
        fp.close,
        fp.volume_base,
        fp.volume_usd,
        fp.return_pct,
        fp.log_return,
        fp.volatility,
        fp.average_price,
        fp.z_score_close,
        SUM(fp.volume_usd) OVER (PARTITION BY fp.date_id) AS day_total_volume_usd
    FROM staging.fact_prep AS fp
)
INSERT INTO gold.fact_market_daily (
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
    z_score_close,
    is_anomaly,
    volume_rank,
    market_dominance_pct,
    regime_label
)
SELECT
    p.date_id,
    p.coin_id,
    p.category_id,
    p.open,
    p.high,
    p.low,
    p.close,
    ROUND(p.volume_base, 4) AS volume_base,
    ROUND(p.volume_usd, 2) AS volume_usd,
    p.return_pct,
    p.log_return,
    p.volatility,
    p.average_price,
    p.z_score_close,
    COALESCE(ABS(p.z_score_close) > 2, FALSE) AS is_anomaly,
    RANK() OVER (
        PARTITION BY p.date_id
        ORDER BY p.volume_usd DESC, p.coin_id
    ) AS volume_rank,
    CASE
        WHEN COALESCE(p.day_total_volume_usd, 0) = 0 THEN NULL
        ELSE ROUND((p.volume_usd * 100.0) / p.day_total_volume_usd, 3)
    END AS market_dominance_pct,
    CASE
        WHEN p.return_pct > 3 THEN 'Bull'
        WHEN p.return_pct < -3 THEN 'Bear'
        ELSE 'Sideways'
    END AS regime_label
FROM prepared AS p;
