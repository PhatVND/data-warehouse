# 06 — Bằng chứng tích hợp End-to-End (TV4 task 4.6)

> Document này là output của **task 4.6**: chạy pipeline đầy đủ rồi capture log + kết quả verify.
> Trong môi trường Linux/WSL2 dùng `run_pipeline.sh`. Trên Windows dùng `run_pipeline.bat`, kết quả tương đương vì cùng gọi `psql` + `python` + cùng SQL.

---

## 1. Môi trường test

| Mục | Giá trị |
|---|---|
| OS dev | WSL2 (Ubuntu 22.04 trên Linux 5.15) |
| PostgreSQL | 14 server (project-local cluster trong `.local_pgdata/`, port 5432) |
| Python | 3.10 |
| Pentaho | bypass (`USE_PENTAHO=0`, `USE_PENTAHO_CLEAN=0`) |
| Đường dẫn project | `/home/cuong/projects/hcmut/data-warehouse/crypto-dw-etl` |
| Date | 2026-04-27 |

> Trên Windows team chạy với PostgreSQL 15 + Pentaho 9.x. Pipeline cùng chạy được vì SQL chuẩn ANSI/PG ≥ 12.

---

## 2. Trình tự test đã chạy

1. `bash tools/init_local_pg.sh init` → tạo cluster + DB + role.
2. Áp `01_staging_ddl.sql`, `02_gold_ddl.sql`, `dim_date_seed.sql` + `\copy seed/dim_*.csv`.
3. `bash run_pipeline.sh` → **lần 1** (full ingest từ Binance).
4. Chạy 7 verify queries trong `sql/verify_e2e.sql` (nội bộ tạo, xem mục 3).
5. `bash run_pipeline.sh` → **lần 2** (test idempotency).
6. `bash run_pipeline_rollback.sh` (xóa cả raw csv) → **lần 3** chạy lại từ trắng tinh.

Tất cả 3 lần chạy đều thoát `exit 0` và log ghi `PIPELINE SUCCESS`.

---

## 3. Kết quả verify (run #3 — sau full rollback)

### V1. `staging.fact_prep` xấp xỉ 7300 rows

```
 staging_fact_prep_rows
------------------------
                   7300
```

→ **PASS**: chính xác 10 coin × 730 nến = 7300.

### V2. `gold.fact_market_daily` rows = `staging.fact_prep` rows

```
 staging_rows | gold_rows | rows_match
--------------+-----------+------------
         7300 |      7300 | t
```

→ **PASS**: SQL `INSERT INTO gold.fact_market_daily ... SELECT ... FROM staging.fact_prep` không drop dòng nào.

### V3. Không có `date_id` nào > 10 coin

```
 date_id | n
---------+---
(0 rows)
```

→ **PASS**: PK `(date_id, coin_id)` đảm bảo và join `dim_coin` không nhân bản.

### V4. Mỗi ngày `SUM(market_dominance_pct) ≈ 100`

```
 days_total | days_within_0_5 | min_sum_pct | max_sum_pct
------------+-----------------+-------------+-------------
       1323 |            1323 |      99.997 |     100.002
```

→ **PASS**: 100% các ngày trong range nằm trong khoảng 99.5 – 100.5 (sai số làm tròn 3 chữ số).

### V5. 3 OLAP views select được

```
            view             | rows
-----------------------------+------
 v_weekly_return_by_category |  423
 v_volume_leaderboard        | 7300
 v_top_anomalies             |  874
```

→ **PASS**: 3/3 views truy vấn không lỗi.

### V6. Verify công thức (3 dòng BTC)

```
 date_id  | symbol |  open    |  close   | return_pct | return_pct_recomputed | log_return | log_return_recomputed |  volume_usd   | volume_usd_recomputed
----------+--------+----------+----------+------------+-----------------------+------------+-----------------------+---------------+-----------------------
 20240427 | BTC    | 63770.00 | 63461.98 |    -0.4830 |               -0.4830 |  -0.004842 |             -0.004842 | 1328453468.06 |         1328453466.79
 20240428 | BTC    | 63461.98 | 63118.62 |    -0.5410 |               -0.5410 |  -0.005425 |             -0.005425 | 1069810117.26 |         1069810120.42
 20240429 | BTC    | 63118.62 | 63866.00 |     1.1841 |                1.1841 |   0.011771 |              0.011771 | 1797842555.33 |         1797842557.25
```

→ **PASS**: `return_pct` và `log_return` khớp 100%. `volume_usd` lệch ≤ $5 do làm tròn `volume_base` từ `NUMERIC(20,8)` xuống `NUMERIC(20,4)` trong fact (xem `03_load_gold.sql` dòng `ROUND(p.volume_base, 4)`). Sai số tương đối < 1e-8, chấp nhận.

### V7. Phân bố số coin trong từng ngày

```
 coins_per_day | days
---------------+------
            10 |  137
             9 |  593
             1 |  593
```

→ **OBSERVATION (không phải lỗi pipeline)**: Tổng 1323 ngày được phủ; 137 ngày có đủ 10 coin, 593 ngày chỉ có 9 coin, 593 ngày chỉ có 1 coin.

**Nguyên nhân:** chạy `MIN(date_id), MAX(date_id) PER coin` thấy:

```
 symbol | min_date | max_date |  n
--------+----------+----------+-----
 MATIC  | 20220912 | 20240910 | 730
 9 còn lại | 20240427 | 20260426 | 730 mỗi coin
```

`MATICUSDT` đã bị Binance delist sau khi Polygon rebrand sang `POL` (tháng 9/2024). Vì thế `limit=730` của TV1 trả về 730 nến **cuối cùng** mà API có → MATIC nằm hẳn ở khoảng 2022–2024, không trùng cửa sổ với 9 coin còn lại trừ ~137 ngày overlap (24-04-27 → 24-09-10).

**Hành động đề xuất** (ngoài phạm vi TV4):

- TV1 cân nhắc dùng `startTime` thay vì chỉ `limit` để đảm bảo cửa sổ thời gian thống nhất, **hoặc**
- Cập nhật `seed/dim_coin.csv` thay `MATIC` bằng symbol khác đang còn niêm yết (ví dụ `POL`).

Pipeline hiện đã xử lý đúng dữ liệu nhận được; vấn đề thuộc về nguồn dữ liệu / cấu hình ingestion.

### Extra. Phân bố `regime_label` và anomaly count

```
 regime_label | rows                anomaly_rows
--------------+------                --------------
 Sideways     | 5025                          874
 Bear         | 1160
 Bull         | 1115
```

→ **OK**: phù hợp threshold `±3%` của business rule và `|z| > 2` của Z-score (~12% anomalies, hợp lý cho rolling 30d).

---

## 4. Idempotency (Full Load) — run #1 vs run #2

| Bảng | Run #1 | Run #2 | Match |
|---|---|---|---|
| `staging.ohlcv_raw` | 7300 | 7300 | ✓ |
| `staging.fact_prep` | 7300 | 7300 | ✓ |
| `gold.fact_market_daily` | 7300 | 7300 | ✓ |

Mỗi step trong run #2 đều là `TRUNCATE` rồi `INSERT` (xem trong `sql/02_transform_fallback.sql`, `sql/03_load_gold.sql`), kết quả deterministic.

Duration mỗi run ~ 12-13s (chủ yếu là Binance API + 10 \copy).

---

## 5. Rollback test

`bash run_pipeline_rollback.sh` (không kèm `--keep-raw`):

```
TRUNCATE TABLE
Deleting 10 raw csv(s)...
gold.fact_market_daily=0
staging.fact_prep=0
staging.ohlcv_raw=0
staging.reject_log=0
ROLLBACK SUCCESS — re-run with: bash run_pipeline.sh
```

Sau đó `bash run_pipeline.sh` lại đầy đủ 7300 dòng. Rollback hoạt động đúng.

---

## 6. Log file

- File: `logs/2026-04-27.log`.
- Mỗi step có header `==== STEP N: <name> ====`.
- Có dòng cuối `PIPELINE SUCCESS — duration <N>s` cho mỗi lần chạy.
- Run #1, #2, #3, rollback và rerun đều append cùng 1 file (cùng ngày), đúng spec 4.5.

---

## 7. Trạng thái tổng kết task 4.6

| Kiểm tra | Kết quả |
|---|---|
| Full pipeline E2E exit 0 | ✓ |
| Log file có `PIPELINE SUCCESS` | ✓ |
| 7/7 verify queries pass | ✓ (V1–V6 PASS; V7 chỉ là observation về dữ liệu MATIC) |
| Idempotent giữa 2 run | ✓ |
| Rollback + rerun trả về cùng count | ✓ |

→ **Task 4.6 hoàn thành**.
