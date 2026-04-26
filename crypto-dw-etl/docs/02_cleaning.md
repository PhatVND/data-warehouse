# TV2 - Pentaho Cleaning

## Muc tieu

TV2 phu trach lop cleaning cua pipeline MVP:

- Doc toan bo file `raw/*_raw.csv` do TV1 tao ra.
- Chuan hoa symbol (`BTCUSDT` → `BTC`).
- Loc va tu choi cac dong khong hop le, ghi vao `staging.reject_log`.
- Ghi cac dong hop le vao `staging.ohlcv_raw`.

## Deliverables

| File | Mo ta |
|---|---|
| `etl/pdi/01_clean.kjb` | Pentaho Job dieu phoi: truncate → clean → log |
| `etl/pdi/sub_transformations/01_clean_ohlcv.ktr` | Transformation chinh |
| `sql/01_staging_ddl.sql` | DDL tao schema `staging` |
| `docs/02_cleaning.md` | File nay |

## Rejection Rules

| Ma | Ten rule | Dieu kien | Truong reject_reason |
|---|---|---|---|
| R1 | NULL_OHLCV | `open`, `high`, `low`, `close` la NULL hoac rong | `NULL_OHLCV_OR_TIME (R1/R2/R4)` |
| R2 | NULL_VOLUME | `volume` la NULL hoac rong | `NULL_OHLCV_OR_TIME (R1/R2/R4)` |
| R3 | HIGH_LT_LOW | `high < low` | `HIGH_LT_LOW (R3)` |
| R4 | NULL_TIME | `open_time` la NULL hoac rong | `NULL_OHLCV_OR_TIME (R1/R2/R4)` |
| R5 | DUPLICATE | Trung `(symbol, open_time)` — giu dong dau | Khong ghi vao reject_log (drop tham lang) |
| R6 | FUTURE_DATE | `open_time` epoch_ms lon hon thoi diem chay job | `FUTURE_DATE (R6)` |
| R2b | NEGATIVE_VOLUME | `volume < 0` | `NEGATIVE_VOLUME (R2)` |

## Luong ETL chi tiet

```
CSV Input (raw/*.csv)
  │
  ▼
String Operations          ← strip "USDT": BTCUSDT → BTC  [Reuse standardize_columns]
  │
  ▼
Filter Null OHLCV          ← R1, R2, R4
  │ TRUE                   │ FALSE
  ▼                        ▼
Filter High<Low            Add Reject R1R2R4
  │ TRUE   │ FALSE              │
  ▼        ▼                   │
Filter     Add Reject R3        │
Neg Vol    │                   │
  │ TRUE   │ FALSE             │
  ▼        ▼                   │
Filter     Add Reject R2b       │
Future     │                   │
  │ TRUE   │ FALSE             │
  ▼        ▼                   │
Sort by (symbol,open_time)  Add Reject R6
  │                        │   │   │
  ▼                        └───┴───┘
Unique Rows (R5 dedupe)        │
  │                            ▼
  ▼                       Merge Rejects (Append)
Write staging.ohlcv_raw        │
                               ▼
                         Write staging.reject_log
```

## Reuse tu code cu

| Step Pentaho | Nguon reuse |
|---|---|
| String Operations | `standardize_columns()` trong `preprocess_stocks.py` — strip suffix, uppercase |
| Filter Null OHLCV | Khoi null-check trong `preprocess_stocks.py` |
| Unique Rows | Pattern dedup `(symbol, date)` tu codebase cu |
| Reject routing | Pattern `FilterRows → error stream` tai su dung 70% |

## Schema staging

### staging.ohlcv_raw

Bang tiep nhan du lieu raw sau khi clean. Cot kieu `VARCHAR`/`BIGINT` de giu nguyen gia tri Binance API tra ve truoc khi cast o buoc transform.

```
symbol, open_time, open, high, low, close, volume,
close_time, quote_asset_volume, number_of_trades,
taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore_field
```

### staging.reject_log

Ghi lai cac dong bi tu choi voi ly do cu the de audit.

```
reject_id (BIGSERIAL PK), source_file, symbol,
open_time_raw, reject_reason, rejected_at
```

### staging.fact_prep

Bang trung gian chua metrics da tinh (TV3 populate hoac `02_transform_fallback.sql`).

## Chay va kiem tra

### Chay bang Kitchen

```bat
kitchen.bat /file:"etl\pdi\01_clean.kjb" ^
  /param:PG_HOST=127.0.0.1 ^
  /param:PG_PORT=5432 ^
  /param:PG_DATABASE=crypto_dw_etl ^
  /param:PG_USER=postgres ^
  /param:PG_PASSWORD=your_password ^
  /param:RAW_DIR=C:\path\to\raw
```

### Verify sau khi chay

```sql
-- 1. Kiem tra so dong da clean
SELECT COUNT(*) FROM staging.ohlcv_raw;
-- Mong doi ~7300 dong (10 coin x 730 ngay)

-- 2. Xem reject log
SELECT reject_reason, COUNT(*) AS cnt
FROM staging.reject_log
GROUP BY reject_reason
ORDER BY cnt DESC;

-- 3. Kiem tra symbol da duoc chuan hoa
SELECT DISTINCT symbol FROM staging.ohlcv_raw ORDER BY symbol;
-- Phai la: ADA, BNB, BTC, DOGE, DOT, ETH, MATIC, SOL, TRX, XRP

-- 4. Kiem tra khong co high < low
SELECT COUNT(*) FROM staging.ohlcv_raw
WHERE CAST(high AS NUMERIC) < CAST(low AS NUMERIC);
-- Phai = 0

-- 5. Kiem tra khong co duplicate
SELECT symbol, open_time, COUNT(*)
FROM staging.ohlcv_raw
GROUP BY symbol, open_time
HAVING COUNT(*) > 1;
-- Phai khong tra ve dong nao
```

## Idempotency

Job `01_clean.kjb` chay **Full Load**: moi lan chay, buoc dau tien la `TRUNCATE staging.ohlcv_raw` va `TRUNCATE staging.reject_log RESTART IDENTITY`. Dam bao co the rerun an toan nhieu lan.

## Phu thuoc

- **Input:** `raw/*_raw.csv` do TV1 (`1_fetch_binance.py`) tao ra.
- **Output:** `staging.ohlcv_raw` duoc TV3 (`02_transform.kjb`) doc.
- **DDL:** `sql/01_staging_ddl.sql` phai da chay truoc.
- **Bat buoc:** TV4 goi `01_clean.kjb` trong `run_pipeline.bat` sau buoc fetch.
