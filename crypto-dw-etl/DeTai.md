# ĐỀ TÀI BTL: CryptoDW-ETL (MVP 14 ngày)

**Kho dữ liệu & Pipeline ETL cho Thị trường Tiền điện tử Top 10**

*(Cryptocurrency Data Warehouse & ETL Pipeline — MVP version)*

Hướng: **ETL / Data Engineering** — triển khai 100% local, tối giản, tái dụng tối đa codebase cũ.

**Ràng buộc MVP:**
- 14 ngày, 5 thành viên.
- Tái dụng ≥70% code cũ (stock analytics).
- Bỏ Airflow / SCD2 / CDC / CoinGecko — giữ pipeline đơn giản.
- Full Load (Drop & Insert) vì data ~7000 dòng (10 coin × 2 năm × 365 ngày).

---

## 1. Kiến trúc MVP (rút gọn)

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Binance REST    │ →   │  Python fetch   │ →   │   CSV raw/       │ →   │  Pentaho PDI     │
│  /api/v3/klines  │     │  (reuse parsers)│     │  dim_coin.csv    │     │  clean+transform │
└──────────────────┘     └─────────────────┘     └──────────────────┘     └──────────────────┘
                                                                                    │
                                                                                    ▼
                                                              ┌──────────────────────────────┐
                                                              │   PostgreSQL                  │
                                                              │   schema: staging  →  gold    │
                                                              │   (Star Schema, Full Load)    │
                                                              └──────────────────────────────┘
                                                                         │
                        ┌────────────────────────────────────────────────┼────────────────┐
                        ▼                          ▼                     ▼                ▼
                  ┌──────────┐              ┌──────────────┐      ┌──────────────┐  ┌──────────┐
                  │ Power BI │              │   Streamlit  │      │ AI notebooks │  │ OLAP SQL │
                  │ (re-pointed)           │   (reuse)    │      │ (reuse 80%)  │  │  views   │
                  └──────────┘              └──────────────┘      └──────────────┘  └──────────┘

Orchestration:  run_pipeline.bat  (Windows Task Scheduler lịch 01:00 hàng ngày)
                ├── 1_fetch_binance.py
                ├── 2_kitchen.bat  → clean.kjb
                ├── 3_kitchen.bat  → transform_gold.kjb
                └── 4_refresh_views.sql
```

**Luồng ngắn gọn:**
`Binance API → Python CSV → Pentaho (clean → transform → gold) → PostgreSQL → Power BI / Streamlit / AI`

Toàn bộ điều phối gom vào **1 file `.bat`** chạy tuần tự. Không Airflow, không Docker (optional). Windows Task Scheduler trigger 01:00 mỗi ngày.

---

## 2. Chi tiết Star Schema (Gold layer)

### 2.1. Fact_Market_Daily

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `date_id` | INT | FK → Dim_Date |
| `coin_id` | INT | FK → Dim_Coin |
| `category_id` | INT | FK → Dim_Category |
| `open` | NUMERIC(18,8) | Giá mở |
| `high` | NUMERIC(18,8) | Giá cao |
| `low` | NUMERIC(18,8) | Giá thấp |
| `close` | NUMERIC(18,8) | Giá đóng |
| `volume_base` | NUMERIC(20,4) | Volume đơn vị coin |
| `volume_usd` | NUMERIC(20,2) | Volume quy đổi USD (= close × volume_base) |
| `return_pct` | NUMERIC(10,4) | `(close-open)/open*100` — **reuse công thức code cũ** |
| `log_return` | NUMERIC(10,6) | `ln(close) − ln(open)` — **reuse** |
| `volatility` | NUMERIC(18,8) | `high − low` — **reuse** |
| `average_price` | NUMERIC(18,8) | `(high+low)/2` — **reuse** |
| `z_score_close` | NUMERIC(10,4) | Rolling 30d — **reuse Z-Score cũ** |
| `is_anomaly` | BOOLEAN | `ABS(z_score) > 2` |
| `volume_rank` | INT | Rank volume_usd theo ngày |
| `market_dominance_pct` | NUMERIC(6,3) | `volume_usd / SUM(volume_usd day) × 100` |
| `regime_label` | VARCHAR(16) | `Bull` / `Bear` / `Sideways` theo `return_pct` |

**Primary key:** `(date_id, coin_id)`

### 2.2. Dim_Date

| Cột | Kiểu | Mô tả |
|---|---|---|
| `date_id` | INT PK | YYYYMMDD |
| `full_date` | DATE | |
| `day` | SMALLINT | |
| `week` | SMALLINT | Week of year |
| `month` | SMALLINT | |
| `quarter` | SMALLINT | |
| `year` | SMALLINT | |
| `day_of_week` | VARCHAR(10) | Mon/Tue/... |
| `is_weekend` | BOOLEAN | |

Populate bằng 1 script SQL chạy 1 lần cho range 2023-01-01 → 2025-12-31.

### 2.3. Dim_Coin (Type 1 — không SCD)

| Cột | Kiểu | Mô tả |
|---|---|---|
| `coin_id` | INT PK | Auto |
| `symbol` | VARCHAR(10) | BTC, ETH, ... |
| `full_name` | VARCHAR(64) | Bitcoin, Ethereum, ... |
| `launch_year` | SMALLINT | |
| `category_id` | INT FK | |

Load từ file tĩnh `dim_coin.csv` một lần.

### 2.4. Dim_Category

| Cột | Kiểu | Mô tả |
|---|---|---|
| `category_id` | INT PK | Auto |
| `category_name` | VARCHAR(32) | L1 / L2 / Meme / Payment |
| `risk_level` | VARCHAR(8) | Low / Mid / High |

**Mapping 10 coin:**

| Symbol | Full name | Category | Risk |
|---|---|---|---|
| BTC | Bitcoin | L1 | Low |
| ETH | Ethereum | L1 | Low |
| BNB | BNB | L1 | Low |
| SOL | Solana | L1 | Mid |
| XRP | XRP | Payment | Low |
| ADA | Cardano | L1 | Mid |
| DOGE | Dogecoin | Meme | High |
| TRX | TRON | L1 | Mid |
| DOT | Polkadot | L1 | Mid |
| MATIC | Polygon | L2 | Mid |

---

## 3. Pipeline ETL chi tiết (3 bước Transformation)

### 3.1. Data Cleaning (Pentaho `01_clean.kjb`)

| Step | Hành động | Reuse |
|---|---|---|
| CSV Input | Đọc `raw/*.csv` | Mới |
| Filter rows | Loại dòng null OHLC | **Copy `preprocess_stocks.py` logic filter** |
| UDJ Expression | Epoch ms → DATE | **Adapt `parse_date()` cũ** |
| Data Validator | Reject `high<low`, `volume<0` → `staging.reject_log` | Mới nhỏ |
| Remove Duplicates | Dedupe `(symbol,date)` | Pattern reuse |
| String Operations | `BTCUSDT` → `BTC` | **Adapt `standardize_columns`** |
| Table Output | Ghi `staging.ohlcv_raw` (TRUNCATE + INSERT) | Mới |

### 3.2. Data Transformation (Pentaho `02_transform.kjb`)

| Step | Công thức | Reuse |
|---|---|---|
| Calculator | `return_pct = (close-open)/open*100` | **100% reuse** |
| Calculator | `log_return = LN(close) − LN(open)` | **100% reuse** |
| Calculator | `volatility = high − low` | **100% reuse** |
| Calculator | `average_price = (high+low)/2` | **100% reuse** |
| Calculator | `volume_usd = close × volume_base` | Mới 1 dòng |
| Group By (window) | Rolling 30d mean, std → `z_score_close` | **Adapt Z-Score code cũ, đổi scope → rolling** |
| Stream Lookup | Join `dim_coin`, `dim_category`, `dim_date` → lấy FK | Mới |
| Table Output | Ghi `staging.fact_prep` (TRUNCATE + INSERT) | Mới |

### 3.3. Business Logic (Pentaho `03_business.kjb` hoặc SQL view)

Có thể viết bằng Pentaho **hoặc** SQL `INSERT INTO gold.fact_market_daily SELECT ... FROM staging.fact_prep`. Chọn SQL cho gọn MVP.

```sql
INSERT INTO gold.fact_market_daily
SELECT
  date_id, coin_id, category_id,
  open, high, low, close, volume_base, volume_usd,
  return_pct, log_return, volatility, average_price, z_score_close,
  ABS(z_score_close) > 2                           AS is_anomaly,
  RANK() OVER (PARTITION BY date_id ORDER BY volume_usd DESC) AS volume_rank,
  volume_usd * 100.0
    / SUM(volume_usd) OVER (PARTITION BY date_id) AS market_dominance_pct,
  CASE
    WHEN return_pct >  3 THEN 'Bull'
    WHEN return_pct < -3 THEN 'Bear'
    ELSE 'Sideways'
  END                                              AS regime_label
FROM staging.fact_prep;
```

Chạy sau `02_transform.kjb`. **Full load:** trước đó `TRUNCATE gold.fact_market_daily`.

---

## 4. Phân chia công việc (5 thành viên — cân bằng theo effort thực tế, không theo số task)

Nguyên tắc: task tái dụng nhiều thì giao kèm task mới để cân effort. TV4 ít reuse hơn nhưng task thiên về config ngắn nên vẫn cân.

### TV1 — Python Ingestion & Parsers *(reuse 70%)*

| # | Task | Deliverable | Reuse |
|---|---|---|---|
| 1.1 | Viết `fetch_binance.py`: loop 10 coin, gọi `/api/v3/klines` daily 730 nến | `scripts/1_fetch_binance.py` | Mới |
| 1.2 | Module `parsers.py`: `parse_number`, `parse_date`, `parse_volume` | `scripts/parsers.py` | **Copy y nguyên từ `preprocess_stocks.py`** |
| 1.3 | Tạo file tĩnh `dim_coin.csv` + `dim_category.csv` (10 coin, 4 category) | `seed/dim_coin.csv`, `seed/dim_category.csv` | Mới (gõ tay) |
| 1.4 | Retry + rate limit Binance (max 1200 req/min) | Trong `fetch_binance.py` | Mới |
| 1.5 | Unit test parse 5 mẫu raw JSON | `tests/test_parsers.py` | Pattern mới |
| 1.6 | Viết `populate_dim_date.sql` | `sql/dim_date_seed.sql` | Mới |

### TV2 — Pentaho Cleaning *(reuse 60%)*

| # | Task | Deliverable | Reuse |
|---|---|---|---|
| 2.1 | Pentaho `01_clean.kjb` (mục 3.1) | `etl/pdi/01_clean.kjb` + `.ktr` | **Adapt từ `preprocess_stocks.py`** |
| 2.2 | DDL PostgreSQL schema `staging` (`ohlcv_raw`, `reject_log`, `fact_prep`) | `sql/01_staging_ddl.sql` | Mới |
| 2.3 | Test: chạy `01_clean.kjb` với 5 file CSV mẫu, kiểm tra reject log | Ảnh chụp màn hình + commit log | - |
| 2.4 | Viết README `docs/02_cleaning.md` ghi rule reject | `docs/02_cleaning.md` | Mới |

### TV3 — Pentaho Transform + Gold + OLAP *(reuse 50%)*

| # | Task | Deliverable | Reuse |
|---|---|---|---|
| 3.1 | Pentaho `02_transform.kjb` (mục 3.2) | `etl/pdi/02_transform.kjb` | **Copy Calculator công thức cũ** |
| 3.2 | DDL `gold` Star Schema (Fact + 3 Dim) | `sql/02_gold_ddl.sql` | Mới |
| 3.3 | Business logic SQL `03_load_gold.sql` (mục 3.3) | `sql/03_load_gold.sql` | Mới |
| 3.4 | OLAP views: `v_weekly_return_by_category`, `v_volume_leaderboard`, `v_top_anomalies` | `sql/04_olap_views.sql` | **Adapt pivot từ `olap_analysis.py`** |
| 3.5 | Doc business rule + công thức | `docs/03_gold.md` | Mới |

### TV4 — Orchestration, Setup & Integration *(reuse 0% code nhưng ít khối lượng/task)*

| # | Task | Deliverable | Reuse |
|---|---|---|---|
| 4.1 | Cài PostgreSQL 15 + tạo user/db/schema, hướng dẫn cài đặt cho team | `docs/00_setup.md` | Mới |
| 4.2 | Cài Pentaho PDI 9.x + thiết lập JDBC PostgreSQL | trong `docs/00_setup.md` | Mới |
| 4.3 | Script `run_pipeline.bat` gọi tuần tự: Python → Pentaho → SQL | `run_pipeline.bat` | Mới |
| 4.4 | Cấu hình Windows Task Scheduler 01:00 daily + screenshot | `docs/05_scheduler.md` | Mới |
| 4.5 | Log handler: ghi stdout từng step vào `logs/YYYY-MM-DD.log` | Trong `.bat` | Mới |
| 4.6 | **Tích hợp chính:** chạy full pipeline end-to-end + debug, xác nhận Gold có data | Bằng chứng chạy thành công | - |
| 4.7 | Kịch bản rollback khi fail (truncate + rerun) | `run_pipeline_rollback.bat` | Mới |

### TV5 — BI + AI + Documentation *(reuse 80%)*

| # | Task | Deliverable | Reuse |
|---|---|---|---|
| 5.1 | Power BI: mở `Stock_Analysis_Dashboard.pbix`, re-point data source sang PostgreSQL Gold, rename measure | `bi/Crypto_Dashboard.pbix` | **60% template cũ** |
| 5.2 | Thêm visual mới: histogram `return_pct`, candlestick, correlation heatmap | Trong `.pbix` | Mới nhỏ |
| 5.3 | Notebook `01_regression.ipynb`: Linear Regression dự báo `close_next_day` | `ai/01_regression.ipynb` | **Copy từ `datamining_analysis.py` phần 2, đổi `Ticker`→`symbol`** |
| 5.4 | Notebook `02_clustering.ipynb`: K-Means k=3 trên `[return_pct_avg, volatility_avg]` | `ai/02_clustering.ipynb` | **Copy từ `datamining_analysis.py` phần 3** |
| 5.5 | Notebook `03_anomaly.ipynb`: Z-Score rolling 30d | `ai/03_anomaly.ipynb` | **Copy từ `datamining_analysis.py` phần 4** |
| 5.6 | Streamlit app kết nối PostgreSQL Gold | `streamlit_crypto.py` | **70% từ `streamlit.py` cũ** |
| 5.7 | README tổng + kiến trúc + screenshot | `README.md` | Mới |
| 5.8 | Slide thuyết trình + video demo 5 phút | `docs/slide.pdf`, `docs/demo.mp4` | Mới |

### Bảng cân bằng khối lượng (effort thực tế)

| TV | Task mới | Task reuse | % reuse | Effort ước tính (giờ) |
|---|---:|---:|---:|---:|
| TV1 – Python/Parsers | 4 | 2 | 70% | 28h |
| TV2 – PDI Clean | 3 | 1 | 60% | 28h |
| TV3 – PDI Transform + SQL | 3 | 2 | 50% | 30h |
| TV4 – Orchestration & Integration | 7 | 0 | 0% | 30h |
| TV5 – BI/AI/Docs | 4 | 4 | 80% | 28h |

→ Tổng ~145h / 5 người = **29h/người ≈ 2h/ngày × 14 ngày**. Khả thi.

---

## 5. Lịch trình 14 ngày (Day-by-Day)

Quy ước: **(H)** = hội quân/integration — toàn team phải có mặt.

### Tuần 1 — Xây nền + Pipeline skeleton

| Ngày | Mục tiêu chính | TV1 | TV2 | TV3 | TV4 | TV5 |
|---|---|---|---|---|---|---|
| **D1** | Kickoff, chốt scope, tạo repo, setup Git branching | Đọc API Binance doc, test 1 request | Cài Pentaho, thử mở `.kjb` | Đọc lại `preprocess_stocks.py` | **Cài PostgreSQL, tạo DB + schema, viết `00_setup.md`** | Mở file `.pbix` cũ, khảo sát measure |
| **D2** | Env sẵn sàng cho mọi người | **Viết `fetch_binance.py` phiên bản đầu, pull thử BTC 30 ngày** | Phác thảo flow `01_clean.kjb` | **Viết DDL `gold` Star Schema** | Test JDBC PostgreSQL ↔ Pentaho | Copy 3 notebook cũ → `ai/`, đổi tên file |
| **D3** | Ingestion + DDL xong | Hoàn thiện `fetch_binance.py` 10 coin, export `raw/*.csv` | Viết DDL `staging` | Rà soát DDL `gold`, review cross TV2 | Script `run_pipeline.bat` skeleton (echo từng step) | Re-point Power BI sang PostgreSQL (connect empty table) |
| **D4** | **(H) Checkpoint 1** — CSV raw có dữ liệu, DB có schema | Commit `raw/*.csv` mẫu | Import CSV vào Pentaho test | Tạo script `populate_dim_date.sql`, chạy | **Chạy `run_pipeline.bat` đến bước Python, verify CSV xuất hiện** | Tải `dim_coin.csv` + `dim_category.csv` vào DB |
| **D5** | Clean job chạy được | Module `parsers.py` + unit test | **`01_clean.kjb` hoàn thiện, ghi được `staging.ohlcv_raw`** | `02_transform.kjb` skeleton (mới Calculator) | Tích hợp Pentaho step 1 vào `.bat` | Notebook `01_regression.ipynb` adapt xong, test với dữ liệu cũ |
| **D6** | Transform job chạy được | Populate `dim_date` seed | Tinh chỉnh Data Validator + reject log | **`02_transform.kjb` tính được return/log_return/volatility/z_score** | Tích hợp Pentaho step 2 vào `.bat` | Notebook `02_clustering.ipynb` adapt xong |
| **D7** | **(H) Checkpoint 2 — MVP pipeline end-to-end (có thể còn thô)** | Hỗ trợ debug parsers | Review cleaning rule | `03_load_gold.sql` viết xong, chạy thử | **Chạy `run_pipeline.bat` full, xác nhận `gold.fact_market_daily` có data** | Notebook `03_anomaly.ipynb` adapt xong |

### Tuần 2 — Đánh bóng + Báo cáo

| Ngày | Mục tiêu chính | TV1 | TV2 | TV3 | TV4 | TV5 |
|---|---|---|---|---|---|---|
| **D8** | Tinh chỉnh pipeline, log + rollback | Edge case: coin thiếu dữ liệu vài ngày | Xử lý Unicode / encoding reject | OLAP views `04_olap_views.sql` | **Log handler, rollback script** | Power BI: thêm histogram + candlestick |
| **D9** | BI đẹp | Doc `01_ingestion.md` | Doc `02_cleaning.md` | Doc `03_gold.md` | Doc `05_scheduler.md`, cấu hình Task Scheduler | **Power BI hoàn thiện: KPI card + slicer + heatmap** |
| **D10** | Streamlit + AI xong | Refactor code Python | Pentaho: test rerun idempotent | Review full pipeline numbers với TV5 (so sánh notebook vs Gold) | Test rerun pipeline 2 lần, xác nhận Full Load đúng | **Streamlit `streamlit_crypto.py` chạy được**, notebooks chạy clean |
| **D11** | **(H) Checkpoint 3 — Freeze code** | Final review parsers | Final review clean | Final review business SQL | **Full pipeline chạy sạch từ 0 tới Power BI refresh** | Freeze `.pbix` + notebook |
| **D12** | Viết báo cáo | Đóng góp phần ingestion vào báo cáo | Đóng góp phần cleaning | Đóng góp phần gold + OLAP | Đóng góp phần orchestration | **Gom tất cả → `report.docx` + `README.md`** |
| **D13** | Slide + video demo | Luyện demo crawler | Luyện demo cleaning | Luyện demo gold | Luyện demo `.bat` + scheduler | **Slide + quay video demo 5 phút** |
| **D14** | **(H) Tổng duyệt + nộp** | Buffer fix bug phút chót | Buffer | Buffer | **Double-check pipeline chạy sạch lần cuối** | Nộp + thuyết trình thử |

### Các mốc hội quân chính

- **D4 (H):** CSV raw OK + DB ready. Nếu trễ → block mọi người, dồn lực fix.
- **D7 (H):** Pipeline end-to-end chạy được (dù còn thô). **Đây là cột mốc không-thể-trễ**; nếu trễ phải cắt scope (bỏ OLAP views hoặc bỏ Streamlit).
- **D11 (H):** Code freeze — không sửa logic, chỉ doc + demo.
- **D14 (H):** Tổng duyệt + nộp.

### Buffer & risk management

- Mỗi TV dành 10–15% thời gian buffer. Lịch trên đã trừ ra.
- **Rủi ro lớn nhất:** Pentaho JDBC + Windows path trục trặc. → TV4 ưu tiên xử D1–D2.
- **Rủi ro 2:** Binance rate limit / IP ban khi test. → TV1 cache response ra file, không gọi lại.
- **Rủi ro 3:** Power BI không kết nối PostgreSQL. → TV5 cài Npgsql ODBC sẵn D1.

---

## 6. Tóm tắt chiến lược tái dụng (để viết báo cáo)

| Module | File cũ | File mới | Reuse |
|---|---|---|---|
| Parse helpers | `preprocess_stocks.py` hàm `parse_number`, `parse_date`, `parse_volume` | `scripts/parsers.py` | **100%** |
| Công thức tính | `preprocess_stocks.py` dòng 165–176 | Pentaho Calculator steps trong `02_transform.kjb` | **100% công thức** |
| Chuẩn hoá cột | `standardize_columns()` | Pentaho String Operations | **70%** |
| Linear Regression | `datamining_analysis.py` phần 2 | `ai/01_regression.ipynb` | **80%** (đổi `Ticker`→`symbol`) |
| K-Means | `datamining_analysis.py` phần 3 | `ai/02_clustering.ipynb` | **70%** (đổi feature list) |
| Z-Score | `datamining_analysis.py` phần 4 | `ai/03_anomaly.ipynb` + SQL rolling | **80%** (đổi window → rolling 30d) |
| OLAP pivot | `olap_analysis.py` | `sql/04_olap_views.sql` | **50%** (chuyển pandas pivot → SQL view) |
| Streamlit | `streamlit.py` | `streamlit_crypto.py` | **70%** |
| Power BI | `Stock_Analysis_Dashboard.pbix` | `Crypto_Dashboard.pbix` | **60%** |

**Tổng reuse cân theo LOC: ~72%** → đạt ngưỡng ≥70%.

---

## 7. Cấu trúc repo đề xuất

```
crypto-dw-etl/
├── run_pipeline.bat                ← TV4
├── run_pipeline_rollback.bat       ← TV4
├── scripts/
│   ├── 1_fetch_binance.py          ← TV1
│   └── parsers.py                  ← TV1 (copy từ project cũ)
├── seed/
│   ├── dim_coin.csv                ← TV1
│   └── dim_category.csv            ← TV1
├── etl/pdi/
│   ├── 01_clean.kjb                ← TV2
│   ├── 02_transform.kjb            ← TV3
│   └── sub_transformations/*.ktr
├── sql/
│   ├── 01_staging_ddl.sql          ← TV2
│   ├── 02_gold_ddl.sql             ← TV3
│   ├── 03_load_gold.sql            ← TV3
│   ├── 04_olap_views.sql           ← TV3
│   └── dim_date_seed.sql           ← TV1
├── ai/
│   ├── 01_regression.ipynb         ← TV5
│   ├── 02_clustering.ipynb         ← TV5
│   └── 03_anomaly.ipynb            ← TV5
├── bi/
│   └── Crypto_Dashboard.pbix       ← TV5
├── streamlit_crypto.py             ← TV5
├── logs/                           ← runtime
├── raw/                            ← Python output
├── tests/
│   └── test_parsers.py             ← TV1
├── docs/
│   ├── 00_setup.md                 ← TV4
│   ├── 01_ingestion.md             ← TV1
│   ├── 02_cleaning.md              ← TV2
│   ├── 03_gold.md                  ← TV3
│   ├── 05_scheduler.md             ← TV4
│   ├── report.docx                 ← TV5 tổng hợp
│   ├── slide.pdf                   ← TV5
│   └── demo.mp4                    ← TV5
└── README.md                       ← TV5
```
