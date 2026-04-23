# TV3 - Gold Layer, Transform va OLAP

## Muc tieu

TV3 phu trach logic bien doi va lop gold cho MVP CryptoDW-ETL:

- Bien doi du lieu tu staging thanh `staging.fact_prep`.
- Tao star schema `gold` gom 3 dimension va 1 fact table.
- Nap `gold.fact_market_daily` theo co che full load.
- Cung cap OLAP views de TV4/TV5 dung cho BI, AI notebook va truy van SQL.

## Deliverables

- `etl/pdi/02_transform.kjb`
- `sql/02_gold_ddl.sql`
- `sql/02_transform_fallback.sql`
- `sql/03_load_gold.sql`
- `sql/04_olap_views.sql`
- `docs/03_gold.md`

## Trang thai hien tai cua repo

- Da co raw CSV cho du 10 coin trong thu muc `raw/`.
- Da co `seed/dim_coin.csv`, `seed/dim_category.csv`.
- Da co `sql/dim_date_seed.sql`.
- Chua co `sql/01_staging_ddl.sql` va chua co Pentaho cleaning job.

Vi vay TV3 duoc code theo huong **co the chay doc lap voi TV2**:

1. Neu team da co `staging.ohlcv_raw` va `staging.fact_prep`, co the dung `03_load_gold.sql` nhu flow chuan.
2. Neu TV2 chua xong, co the dung `02_transform_fallback.sql` de tinh `staging.fact_prep` truc tiep tu `staging.ohlcv_raw`.

## Gold star schema

### `gold.dim_category`

- Nguon: `seed/dim_category.csv`
- Khoa: `category_id`
- Rule:
  - `risk_level` chi nhan `Low`, `Mid`, `High`

### `gold.dim_coin`

- Nguon: `seed/dim_coin.csv`
- Khoa: `coin_id`
- FK: `category_id -> gold.dim_category(category_id)`

### `gold.dim_date`

- Nguon: `sql/dim_date_seed.sql`
- Khoa: `date_id = YYYYMMDD`

### `gold.fact_market_daily`

- Grain: **1 dong / 1 coin / 1 ngay**
- PK: `(date_id, coin_id)`

## Cong thuc business

Tat ca cong thuc duoc giu o SQL de de verify va de TV4/TV5 co the doi chieu:

- `return_pct = (close - open) / open * 100`
- `log_return = ln(close) - ln(open)`
- `volatility = high - low`
- `average_price = (high + low) / 2`
- `volume_usd = close * volume_base`
- `z_score_close = (close - rolling_mean_30d) / rolling_std_30d`
- `is_anomaly = ABS(z_score_close) > 2`
- `volume_rank = RANK() OVER (PARTITION BY date_id ORDER BY volume_usd DESC)`
- `market_dominance_pct = volume_usd / SUM(volume_usd theo ngay) * 100`
- `regime_label`:
  - `Bull` neu `return_pct > 3`
  - `Bear` neu `return_pct < -3`
  - `Sideways` cho cac truong hop con lai

## Rolling 30 ngay

`z_score_close` duoc tinh theo tung coin, cua so:

- `PARTITION BY coin_id`
- `ORDER BY full_date`
- `ROWS BETWEEN 29 PRECEDING AND CURRENT ROW`

Neu rolling standard deviation bang `0` hoac `NULL`, `z_score_close` duoc gan `NULL`.

## OLAP views

### `gold.v_weekly_return_by_category`

Muc dich:

- Tong hop theo tuan va category.
- Phuc vu Power BI KPI, trend va phan tich tong hop.

Cot chinh:

- `year`, `week`, `week_start_date`, `week_end_date`
- `category_name`, `risk_level`
- `avg_return_pct`, `avg_log_return`, `avg_volatility`
- `total_volume_usd`, `trading_rows`, `anomaly_rows`

### `gold.v_volume_leaderboard`

Muc dich:

- Bang xep hang volume theo ngay.
- Phuc vu dashboard leaderboard va top-volume analysis.

Cot chinh:

- `full_date`, `volume_rank`
- `symbol`, `full_name`, `category_name`
- `volume_base`, `volume_usd`, `market_dominance_pct`
- `return_pct`, `regime_label`

### `gold.v_top_anomalies`

Muc dich:

- Liet ke cac dong bat thuong de TV5 dung cho notebook va dashboard.

Cot chinh:

- `full_date`, `symbol`, `category_name`
- `close`, `return_pct`, `log_return`, `volatility`
- `volume_usd`, `z_score_close`, `abs_z_score_close`
- `market_dominance_pct`, `regime_label`

## Thu tu chay de xac minh

1. Chay `sql/02_gold_ddl.sql`
2. Load seed `dim_category.csv`, `dim_coin.csv` vao `gold.dim_category`, `gold.dim_coin`
3. Chay `sql/dim_date_seed.sql`
4. Dam bao `staging.ohlcv_raw` da co du lieu
5. Chay `sql/02_transform_fallback.sql` neu chua co `staging.fact_prep`
6. Chay `sql/03_load_gold.sql`
7. Chay `sql/04_olap_views.sql`

## Verify bat buoc

- Verify 1: `gold.dim_date`, `gold.dim_coin`, `gold.dim_category` co du lieu truoc khi load fact.
- Verify 2: `SELECT COUNT(*) FROM staging.fact_prep;` phai xap xi 7300 dong neu du 10 coin x 730 ngay.
- Verify 3: `SELECT COUNT(*) FROM gold.fact_market_daily;` phai bang so dong trong `staging.fact_prep`.
- Verify 4: `SELECT date_id, COUNT(*) FROM gold.fact_market_daily GROUP BY date_id HAVING COUNT(*) > 10;` phai khong tra ve dong nao.
- Verify 5: `SELECT date_id, ROUND(SUM(market_dominance_pct), 3) FROM gold.fact_market_daily GROUP BY date_id;` moi ngay phai xap xi `100`.
- Verify 6: doi chieu thu cong it nhat 3 dong cho cong thuc `return_pct`, `log_return`, `volume_usd`, `z_score_close`.
- Verify 7: ca 3 view `gold.v_weekly_return_by_category`, `gold.v_volume_leaderboard`, `gold.v_top_anomalies` phai `SELECT` duoc.

## Han che hien tai

- Chua the verify runtime Pentaho trong workspace hien tai vi chua co PDI va chua co JDBC/PostgreSQL local de chay thu.
- `02_transform.kjb` duoc tao theo huong dong goi luong transform TV3, nhung can import/chay tren Pentaho de xac nhan XML hop le trong moi truong team.
