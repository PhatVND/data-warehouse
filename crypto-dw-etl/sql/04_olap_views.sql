-- ============================================================================
-- Script: 04_olap_views.sql
-- Purpose: Create OLAP-friendly gold views for BI, notebooks and ad-hoc SQL.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.v_weekly_return_by_category AS
SELECT
    d.year,
    d.week,
    MIN(d.full_date) AS week_start_date,
    MAX(d.full_date) AS week_end_date,
    c.category_name,
    c.risk_level,
    ROUND(AVG(f.return_pct), 4) AS avg_return_pct,
    ROUND(AVG(f.log_return), 6) AS avg_log_return,
    ROUND(AVG(f.volatility), 8) AS avg_volatility,
    ROUND(SUM(f.volume_usd), 2) AS total_volume_usd,
    COUNT(*) AS trading_rows,
    SUM(CASE WHEN f.is_anomaly THEN 1 ELSE 0 END) AS anomaly_rows
FROM gold.fact_market_daily AS f
INNER JOIN gold.dim_date AS d
    ON d.date_id = f.date_id
INNER JOIN gold.dim_category AS c
    ON c.category_id = f.category_id
GROUP BY
    d.year,
    d.week,
    c.category_name,
    c.risk_level;

CREATE OR REPLACE VIEW gold.v_volume_leaderboard AS
SELECT
    d.full_date,
    d.year,
    d.month,
    d.week,
    f.volume_rank,
    coin.symbol,
    coin.full_name,
    cat.category_name,
    cat.risk_level,
    f.volume_base,
    f.volume_usd,
    f.market_dominance_pct,
    f.return_pct,
    f.regime_label
FROM gold.fact_market_daily AS f
INNER JOIN gold.dim_date AS d
    ON d.date_id = f.date_id
INNER JOIN gold.dim_coin AS coin
    ON coin.coin_id = f.coin_id
INNER JOIN gold.dim_category AS cat
    ON cat.category_id = f.category_id;

CREATE OR REPLACE VIEW gold.v_top_anomalies AS
SELECT
    d.full_date,
    d.year,
    d.month,
    coin.symbol,
    coin.full_name,
    cat.category_name,
    f.close,
    f.return_pct,
    f.log_return,
    f.volatility,
    f.volume_usd,
    f.z_score_close,
    ABS(f.z_score_close) AS abs_z_score_close,
    f.market_dominance_pct,
    f.regime_label
FROM gold.fact_market_daily AS f
INNER JOIN gold.dim_date AS d
    ON d.date_id = f.date_id
INNER JOIN gold.dim_coin AS coin
    ON coin.coin_id = f.coin_id
INNER JOIN gold.dim_category AS cat
    ON cat.category_id = f.category_id
WHERE f.is_anomaly = TRUE;
