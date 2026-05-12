# CryptoDW-ETL — Cryptocurrency Data Warehouse & ETL Pipeline

> **Môn học:** Kho dữ liệu (Data Warehouse) — BTL MVP 14 ngày  
> **Hướng:** ETL / Data Engineering — triển khai 100% local, tái dụng ≥ 70% codebase cũ  
> **Dữ liệu:** Top 10 coin theo Binance · 730 nến ngày · ~7 300 dòng trong Gold layer

---

## 📐 Kiến trúc tổng quan

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Binance REST    │ →   │  Python fetch   │ →   │  CSV raw/        │
│  /api/v3/klines  │     │  (parsers.py)   │     │  raw/*.csv       │
└──────────────────┘     └─────────────────┘     └────────┬─────────┘
                                                           │ psql \copy / Pentaho 01_clean.kjb
                                                           ▼
                                                  ┌─────────────────────┐
                                                  │  staging.ohlcv_raw  │
                                                  └────────┬────────────┘
                                              02_transform_fallback.sql
                                              hoặc Pentaho 02_transform.kjb
                                                           ▼
                                                  ┌─────────────────────┐
                                                  │  staging.fact_prep  │
                                                  └────────┬────────────┘
                                                  03_load_gold.sql (TRUNCATE + INSERT)
                                                           ▼
                                         ┌─────────────────────────────────┐
                                         │  PostgreSQL — schema: gold       │
                                         │  ┌────────────────────────────┐  │
                                         │  │  Star Schema (Full Load)   │  │
                                         │  │  fact_market_daily         │  │
                                         │  │  dim_date / dim_coin /     │  │
                                         │  │  dim_category              │  │
                                         │  └────────────────────────────┘  │
                                         └──────────────┬──────────────────┘
                              ┌───────────────┬─────────┴──────┬──────────────┐
                              ▼               ▼                ▼              ▼
                        Power BI       Streamlit          AI Notebooks    OLAP Views
                   Crypto_Dashboard  streamlit_crypto.py  ai/*.ipynb   04_olap_views.sql
```

**Orchestration:** `run_pipeline.bat` (Windows) / `run_pipeline.sh` (Linux/WSL)  
Gọi tuần tự: Python → psql/Pentaho → SQL → Views — toàn bộ trong **1 file `.bat`**.

---

## 🗂 Cấu trúc repo

```
crypto-dw-etl/
├── run_pipeline.bat            ← Orchestration chính (TV4)
├── run_pipeline.sh             ← Bản Linux/WSL (TV4)
├── run_pipeline_rollback.bat   ← Rollback + rerun (TV4)
├── run_pipeline_rollback.sh
├── .env.example                ← Template config DB
├── requirements.txt            ← Python dependencies
│
├── scripts/
│   ├── 1_fetch_binance.py      ← Ingest 10 coin từ Binance API (TV1)
│   └── parsers.py              ← parse_number, parse_date, parse_volume (TV1)
│
├── seed/
│   ├── dim_coin.csv            ← 10 coin, launch_year, category_id (TV1)
│   └── dim_category.csv        ← 4 categories + risk_level (TV1)
│
├── etl/pdi/
│   ├── 01_clean.kjb            ← Pentaho: clean ohlcv_raw (TV2)
│   └── 02_transform.kjb        ← Pentaho: tính metrics → fact_prep (TV3)
│
├── sql/
│   ├── 00_db_bootstrap.sql     ← Tạo DB + role (TV4)
│   ├── 01_staging_ddl.sql      ← DDL schema staging (TV2)
│   ├── 02_gold_ddl.sql         ← DDL Star Schema gold (TV3)
│   ├── 02_transform_fallback.sql  ← SQL thay thế Pentaho transform (TV3)
│   ├── 03_load_gold.sql        ← TRUNCATE + INSERT gold.fact_market_daily (TV3)
│   ├── 04_olap_views.sql       ← 3 OLAP views (TV3)
│   └── dim_date_seed.sql       ← Populate dim_date 2023–2025 (TV1)
│
├── ai/
│   ├── 01_regression.ipynb     ← Linear Regression: dự báo close_next_day (TV5)
│   ├── 02_clustering.ipynb     ← K-Means k=3: phân nhóm coin (TV5)
│   └── 03_anomaly.ipynb        ← Z-Score rolling 30d: anomaly detection (TV5)
│
├── bi/
│   └── Crypto_Dashboard.pbix   ← Power BI dashboard (TV5)
│
├── streamlit_crypto.py         ← Web dashboard 5-tab (TV5)
│
├── raw/                        ← Output của fetch_binance.py (*_raw.csv)
├── logs/                       ← Pipeline logs (YYYY-MM-DD.log)
├── tests/
│   └── test_parsers.py         ← Unit tests cho parsers.py (TV1)
├── tools/
│   └── init_local_pg.sh        ← Script khởi tạo PostgreSQL local (TV4)
└── docs/
    ├── 00_setup.md             ← Hướng dẫn cài đặt đầy đủ (TV4)
    ├── 01_ingestion.md         ← Tài liệu ingestion (TV1)
    ├── 02_cleaning.md          ← Rule reject + cleaning (TV2)
    ├── 03_gold.md              ← Business rule + công thức Gold (TV3)
    ├── 05_scheduler.md         ← Windows Task Scheduler (TV4)
    └── 06_e2e_evidence.md      ← Bằng chứng pipeline E2E (TV4)
```

---

## ⚙️ Cài đặt & Chạy

### Yêu cầu

| Phần mềm | Phiên bản | Ghi chú |
|----------|-----------|---------|
| Python | ≥ 3.10 | `pip install -r requirements.txt` |
| PostgreSQL | ≥ 14 | Cổng mặc định 5432 |
| Pentaho PDI | 9.x | Tùy chọn — có thể dùng SQL fallback |
| Power BI Desktop | Mới nhất | Tùy chọn — cần Npgsql ODBC |

### Bước 1 — Cài Python dependencies

```bash
pip install -r requirements.txt
```

### Bước 2 — Cấu hình DB

```bash
# Copy và chỉnh sửa file .env
copy .env.example .env
```

Mở `.env` và cập nhật:

```env
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=crypto_dw_etl
PG_USER=crypto_etl
PG_PASSWORD=your_password
```

### Bước 3 — Khởi tạo database (chạy 1 lần)

```sql
-- Chạy trong psql với quyền superuser:
\i sql/00_db_bootstrap.sql
\i sql/01_staging_ddl.sql
\i sql/02_gold_ddl.sql
\i sql/dim_date_seed.sql

-- Load seed data:
\copy gold.dim_category FROM 'seed/dim_category.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_coin     FROM 'seed/dim_coin.csv'     WITH (FORMAT csv, HEADER true)
```

> 💡 Trên Linux/WSL dùng `tools/init_local_pg.sh init` để tự động hoá toàn bộ bước này.

### Bước 4 — Chạy pipeline

```bash
# Windows
run_pipeline.bat

# Linux / WSL
bash run_pipeline.sh
```

Pipeline chạy tuần tự **5 bước**:

| Bước | Mô tả | Output |
|------|-------|--------|
| STEP 1 | Python fetch 10 coin từ Binance API | `raw/*.csv` |
| STEP 2 | Load `staging.ohlcv_raw` | 7 300 rows |
| STEP 3 | Transform → `staging.fact_prep` (tính metrics) | 7 300 rows |
| STEP 4 | Load `gold.fact_market_daily` | 7 300 rows |
| STEP 5 | Refresh OLAP views | 3 views |

Log được ghi vào `logs/YYYY-MM-DD.log`. Pipeline thành công khi xuất hiện dòng `PIPELINE SUCCESS`.

### Rollback (khi cần rerun từ đầu)

```bash
run_pipeline_rollback.bat           # Windows
bash run_pipeline_rollback.sh       # Linux/WSL
```

---

## 🌟 Gold Schema — Star Schema

```
                   ┌─────────────┐
                   │  dim_date   │
                   │  date_id PK │
                   └──────┬──────┘
                          │ FK
          ┌───────────────┼────────────────┐
          │               ▼                │
  ┌───────┴──────┐  ┌──────────────────┐  │
  │   dim_coin   │  │ fact_market_daily│  │
  │   coin_id PK │→ │ PK(date_id,      │  │
  └──────┬───────┘  │     coin_id)     │  │
         │          │                  │←─┘
         │   ┌──────┴──────────┐
         │   │  dim_category   │
         └──→│  category_id PK │
             └─────────────────┘
```

### Fact table — `gold.fact_market_daily`

| Cột | Kiểu | Công thức |
|-----|------|-----------|
| `open/high/low/close` | NUMERIC(18,8) | Raw từ Binance |
| `volume_base` | NUMERIC(20,4) | Volume đơn vị coin |
| `volume_usd` | NUMERIC(20,2) | `close × volume_base` |
| `return_pct` | NUMERIC(10,4) | `(close−open)/open×100` |
| `log_return` | NUMERIC(10,6) | `ln(close) − ln(open)` |
| `volatility` | NUMERIC(18,8) | `high − low` |
| `average_price` | NUMERIC(18,8) | `(high+low)/2` |
| `z_score_close` | NUMERIC(10,4) | Rolling 30d Z-Score |
| `is_anomaly` | BOOLEAN | `\|z_score\| > 2` |
| `volume_rank` | INT | RANK theo volume_usd mỗi ngày |
| `market_dominance_pct` | NUMERIC(6,3) | `volume_usd / SUM(ngày) × 100` |
| `regime_label` | VARCHAR(16) | Bull / Bear / Sideways |

### OLAP Views

| View | Mô tả |
|------|-------|
| `gold.v_weekly_return_by_category` | Return trung bình theo tuần × category |
| `gold.v_volume_leaderboard` | Bảng xếp hạng volume toàn bộ ngày |
| `gold.v_top_anomalies` | Danh sách ngày anomaly (`is_anomaly = TRUE`) |

---

## 🤖 AI / Machine Learning

### `ai/01_regression.ipynb` — Linear Regression

- **Mục tiêu:** Dự báo `close_next_day` (giá đóng cửa ngày N+1)
- **Features:** OHLCV + return_pct + z_score + lag features + MA7
- **Split:** Time-based 80/20 (không shuffle)
- **Kết quả:** R² ~ 0.99 (do giá crypto có auto-correlation cao)

### `ai/02_clustering.ipynb` — K-Means k=3

- **Mục tiêu:** Phân nhóm 10 coin theo hành vi thị trường
- **Features:** `return_pct_avg`, `volatility_avg`, `volume_usd_avg`
- **Clusters:** Low Volatility (BTC/ETH) · Mid Volatility · High Volatility (Meme)
- **Visualize:** Scatter 2D, PCA projection, Radar chart

### `ai/03_anomaly.ipynb` — Z-Score Anomaly Detection

- **Mục tiêu:** Phát hiện ngày giao dịch bất thường (`|z| > 2`)
- **Nguồn:** Kéo từ `gold.v_top_anomalies` + timeline chart
- **Kết quả:** ~12% anomaly rate — cao hơn lý thuyết chuẩn do crypto biến động phi chuẩn

---

## 📊 Streamlit Dashboard

```bash
streamlit run streamlit_crypto.py
```

Mở trình duyệt tại `http://localhost:8501`

| Tab | Nội dung |
|-----|----------|
| 📊 Overview | Line chart giá, Regime bar, Market Dominance pie |
| 🕯 Price & Volume | Candlestick, Return histogram, Volatility |
| 🚨 Anomaly Detection | Z-Score timeline, Anomaly rate, Top events |
| 🔍 OLAP Views | Weekly return, Correlation heatmap, Volume leaderboard |
| 📋 Data Explorer | Filter, sort, download CSV |

---

## 📦 10 Coin được theo dõi

| Symbol | Full name | Category | Risk |
|--------|-----------|----------|------|
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

> **Lưu ý:** `MATICUSDT` đã bị Binance delist sau khi Polygon rebrand sang `POL` (tháng 9/2024). Dữ liệu MATIC nằm ở cửa sổ 2022–2024, không trùng hoàn toàn với 9 coin còn lại. Xem `docs/06_e2e_evidence.md` mục V7 để biết thêm chi tiết.

---

## 🔄 Chiến lược tái dụng code

| Module | File gốc | File mới | % Reuse |
|--------|----------|----------|---------|
| Parse helpers | `preprocess_stocks.py` | `scripts/parsers.py` | **100%** |
| Công thức tính | `preprocess_stocks.py` L165–176 | Pentaho Calculator / SQL | **100%** |
| Linear Regression | `datamining_analysis.py` phần 2 | `ai/01_regression.ipynb` | **80%** |
| K-Means | `datamining_analysis.py` phần 3 | `ai/02_clustering.ipynb` | **70%** |
| Z-Score | `datamining_analysis.py` phần 4 | `ai/03_anomaly.ipynb` | **80%** |
| OLAP pivot | `olap_analysis.py` | `sql/04_olap_views.sql` | **50%** |
| Streamlit | `streamlit.py` | `streamlit_crypto.py` | **70%** |
| Power BI | `Stock_Analysis_Dashboard.pbix` | `bi/Crypto_Dashboard.pbix` | **60%** |

**Tổng reuse ước tính: ~72%** — đạt ngưỡng ≥ 70% theo yêu cầu BTL.

---

## 👥 Phân chia công việc

| Thành viên | Vai trò | Deliverables chính |
|------------|---------|-------------------|
| **TV1** | Python Ingestion & Parsers | `scripts/`, `seed/`, `sql/dim_date_seed.sql` |
| **TV2** | Pentaho Cleaning | `etl/pdi/01_clean.kjb`, `sql/01_staging_ddl.sql`, `docs/02_cleaning.md` |
| **TV3** | Pentaho Transform + Gold + OLAP | `etl/pdi/02_transform.kjb`, `sql/02–04_*.sql`, `docs/03_gold.md` |
| **TV4** | Orchestration & Integration | `run_pipeline.*`, `docs/00_setup.md`, `docs/05_scheduler.md`, `docs/06_e2e_evidence.md` |
| **TV5** | BI / AI / Documentation | `ai/`, `bi/`, `streamlit_crypto.py`, `README.md` |

---

## 📄 Tài liệu liên quan

- [`docs/00_setup.md`](docs/00_setup.md) — Hướng dẫn cài đặt PostgreSQL + Pentaho
- [`docs/01_ingestion.md`](docs/01_ingestion.md) — Chi tiết ingestion từ Binance
- [`docs/02_cleaning.md`](docs/02_cleaning.md) — Rule reject + Pentaho cleaning
- [`docs/03_gold.md`](docs/03_gold.md) — Business rules + công thức Gold layer
- [`docs/05_scheduler.md`](docs/05_scheduler.md) — Cấu hình Windows Task Scheduler
- [`docs/06_e2e_evidence.md`](docs/06_e2e_evidence.md) — Bằng chứng pipeline E2E (7 verify queries)

---

## 🛡 Giấy phép

Dự án học thuật — HCMUT · Học kỳ 2 · 2025–2026.
