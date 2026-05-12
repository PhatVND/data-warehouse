# CryptoDW-ETL · Cryptocurrency Data Warehouse

> **BTL — Môn CO4031 Kho dữ liệu và Hệ hỗ trợ quyết định**
> Khoa KH&KT Máy tính · ĐH Bách Khoa TP.HCM · HK 251 (2025–2026)

[![Built with Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pentaho PDI](https://img.shields.io/badge/Pentaho-PDI%209.x-orange)](https://www.hitachivantara.com/en-us/products/pentaho-data-integration-analytics.html)
[![License](https://img.shields.io/badge/license-Academic-lightgrey)]()

---

## 🎯 Mục tiêu

Xây dựng pipeline ETL hoàn chỉnh + Kho dữ liệu chuẩn **Star Schema** cho **10 đồng coin top theo Binance** (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, TRX, DOT, MATIC), với **730 nến ngày** mỗi coin (~7 300 dòng Gold layer). Pipeline chạy **100% local**, có cả Pentaho và SQL fallback.

## 🏗 Kiến trúc

```
┌──────────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  Binance REST    │ →  │  Python     │ →  │  PostgreSQL      │ →  │  Power BI / Streamlit│
│  /api/v3/klines  │    │  + Pentaho  │    │  Star Schema     │    │  + Jupyter (AI)      │
└──────────────────┘    └─────────────┘    └──────────────────┘    └─────────────────────┘
```

Chi tiết: [crypto-dw-etl/README.md](crypto-dw-etl/README.md).

## 📂 Cấu trúc repo

```
data-warehouse/
├── BaoCao_CryptoDW.pdf              ← Báo cáo PDF (51 trang) — deliverable chính
│
├── crypto-dw-etl/                   ← Source code
│   ├── ai/                          ← 3 Jupyter notebook (Regression, K-Means, Anomaly)
│   ├── bi/                          ← Power BI dashboard + 4 mock screenshots
│   │   ├── Crypto_Dashboard.pbix    ← Power BI Desktop file
│   │   └── data/                    ← 4 CSV xuất từ Gold layer (cho PBI Import mode)
│   ├── docs/                        ← Documentation từng phần (00–06)
│   ├── etl/pdi/                     ← Pentaho jobs (.kjb / .ktr)
│   ├── raw/                         ← Output ingestion: 10 file <SYMBOL>_raw.csv
│   ├── scripts/                     ← Python ingestion + parsers
│   ├── seed/                        ← dim_coin.csv + dim_category.csv
│   ├── sql/                         ← DDL + Transform + OLAP views
│   ├── tests/                       ← Unit tests cho parsers
│   ├── tools/                       ← Utility scripts (export PBI, gen images, screenshots)
│   ├── streamlit_crypto.py          ← Web dashboard (PostgreSQL mode)
│   ├── streamlit_crypto_csv.py      ← Wrapper đọc CSV (không cần PostgreSQL)
│   ├── run_pipeline.bat / .sh       ← Orchestration ETL (Win/Linux)
│   └── requirements.txt
│
└── _Data_Warehouse/                 ← LaTeX source của báo cáo
    └── _Data_Warehouse__Báo_cáo/
        ├── main.tex
        ├── Configuration/preamble.sty
        ├── Contents/                ← 11 chương (.tex)
        └── Images/                  ← Tất cả ảnh dùng trong báo cáo
```

## 🚀 Quick start

### Mode 1 — Chỉ xem dashboard (không cần PostgreSQL)

```bash
cd crypto-dw-etl
pip install -r requirements.txt

# Streamlit web dashboard
python -m streamlit run streamlit_crypto_csv.py
# → http://localhost:8501
```

### Mode 2 — Full pipeline (cần PostgreSQL)

```bash
cd crypto-dw-etl
cp .env.example .env             # Chỉnh password DB
psql -U postgres -f sql/00_db_bootstrap.sql

# Chạy toàn bộ pipeline (5 bước)
run_pipeline.bat                 # Windows
bash run_pipeline.sh             # Linux/WSL
```

### Mode 3 — Build báo cáo PDF

```bash
cd _Data_Warehouse/_Data_Warehouse__Báo_cáo
xelatex main.tex     # hoặc pdflatex
xelatex main.tex     # chạy 2 lần để fix cross-references
```

## 📊 Kết quả chính

| Hạng mục | Số liệu |
|---|---|
| Coin được phân tích | 10 (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, TRX, DOT, MATIC) |
| Khoảng dữ liệu | 27/04/2024 → 26/04/2026 (730 ngày/coin) |
| Bản ghi Gold layer | ~7 300 |
| Linear Regression $R^2$ | 0.92 – 0.98 |
| K-Means clusters | 3 (Leaders / Mid-cap / Speculative) |
| Anomaly rate | ~12% (cao gấp 2.5× phân phối Gauss) |
| OLAP views | 3 (`v_weekly_return_by_category`, `v_volume_leaderboard`, `v_top_anomalies`) |


**Giảng viên hướng dẫn:** ThS. Bùi Tiến Đức — Lớp L02

## 📜 License

Dự án học thuật — chỉ dùng cho mục đích giáo dục.

---
*Generated as part of CO4031 Final Project · HCMUT · Semester 252(2025–2026)*
