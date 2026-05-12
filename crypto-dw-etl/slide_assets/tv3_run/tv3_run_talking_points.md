# TV3 Gold/Transform/OLAP Run - Talking Points

- TV3 owns transform logic, Gold Star Schema, and OLAP views.
- Evidence script mirrors SQL formulas from 02_transform_fallback.sql and 03_load_gold.sql.
- Input raw rows: 7300.
- staging.fact_prep rows: 7300.
- gold.fact_market_daily rows: 7300.
- Rows match: True.
- Fact grain: 1 row per coin per day, primary key (date_id, coin_id).
- Top anomaly rows: 874.
- OLAP view row counts:
  - v_weekly_return_by_category: 423
  - v_volume_leaderboard: 7300
  - v_top_anomalies: 874
- Regime distribution: Bear=1160, Bull=1115, Sideways=5025.
- 2025 volume leaders: BTC=768.12B, ETH=634.66B, SOL=258.56B.
