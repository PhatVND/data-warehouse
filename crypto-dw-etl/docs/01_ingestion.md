# TV1 - Ingestion & Parsers

## Muc tieu

TV1 phu trach lop ingestion cua pipeline MVP:

- Doc danh sach 10 coin tu seed data.
- Goi Binance REST API `/api/v3/klines` voi interval `1d`.
- Xuat raw CSV cho tung coin de TV2 su dung trong Pentaho cleaning.
- Cung cap bo parser dung chung cho gia, volume va ngay thang.

## Deliverables

- `scripts/1_fetch_binance.py`
- `scripts/parsers.py`
- `seed/dim_coin.csv`
- `seed/dim_category.csv`
- `sql/dim_date_seed.sql`
- `tests/test_parsers.py`

## Luong chay ingestion

1. `1_fetch_binance.py` doc `seed/dim_coin.csv`.
2. Moi symbol duoc doi thanh cap giao dich `SYMBOLUSDT`.
3. Script goi Binance klines API voi `limit=730`, `interval=1d`.
4. Ket qua duoc ghi de vao `raw/<SYMBOL>_raw.csv`.
5. Pentaho doc cac file raw nay de clean va load vao `staging.ohlcv_raw`.

## Format output raw CSV

Moi file CSV co header:

`symbol, open_time, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore_field`

`symbol` duoc them vao dau dong de downstream join va filter de hon.

## Retry va rate limit

- Retry toi da 3 lan cho moi coin.
- Dung exponential backoff: 2s, 4s, 8s... toi da 60s.
- Xu ly rieng cho HTTP `418`, `429` va nhom loi `5xx`.
- Co delay ngan giua cac coin de han che burst request.
- Khi JSON tra ve khong dung dinh dang hoac request fail qua so lan retry, script bo qua coin do va ghi log.

## Parsers

`parsers.py` cung cap 3 ham:

- `parse_number`: chuyen chuoi so thanh `float`, xu ly comma va khoang trang.
- `parse_volume`: ho tro gia tri crypto precision va suffix `K`, `M`, `B`.
- `parse_date`: uu tien dung dang ISO (`YYYY-MM-DD`) va ho tro epoch milliseconds tu Binance.

## Test

`tests/test_parsers.py` bao gom:

- Test don vi cho `parse_number`, `parse_volume`, `parse_date`.
- 5 mau mock klines Binance de xac nhan parser hoat dong dung voi du lieu thuc te.

Chay nhanh:

```bash
python -m unittest tests.test_parsers
```

## Phu thuoc voi team khac

- TV2 phu thuoc vao `raw/*.csv` va quy uoc cot du lieu.
- TV3/TV4 phu thuoc vao `seed/*.csv` va `sql/dim_date_seed.sql`.
- TV4 se goi `scripts/1_fetch_binance.py` trong `run_pipeline.bat`.
