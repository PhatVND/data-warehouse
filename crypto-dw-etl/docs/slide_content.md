# Slide Thuyết trình — CryptoDW-ETL

> **Nội dung slide cho task 5.8**  
> Tổng thời gian thuyết trình: ~10 phút | Demo video: 5 phút  
> Định dạng gợi ý: PowerPoint / Google Slides / Canva

---

## SLIDE 1 — Trang bìa

**Tiêu đề:**
```
CryptoDW-ETL
Cryptocurrency Data Warehouse & ETL Pipeline
```

**Phụ đề:**
```
BTL Môn Kho Dữ Liệu — Nhóm 5 thành viên
HCMUT · Học kỳ 2 · 2025–2026
```

**Visual:** Logo Bitcoin/Ethereum trên nền dark gradient (#0d1117 → #161b22)  
**Màu accent:** `#58a6ff`

---

## SLIDE 2 — Vấn đề & Mục tiêu

**Tiêu đề:** Bài toán đặt ra

**Nội dung:**
- 🔍 Thị trường crypto biến động mạnh — cần hệ thống theo dõi tự động
- 📊 Phân tích 10 coin Top theo Binance: ~7.300 điểm dữ liệu / ngày
- 🎯 **Mục tiêu:** Xây dựng Data Warehouse + ETL pipeline hoàn chỉnh

**3 cột mục tiêu:**
| Ingestion | Transform | Analytics |
|-----------|-----------|-----------|
| Tự động fetch từ Binance API | Làm sạch, tính toán metrics | BI Dashboard + AI/ML |

**Ràng buộc:**
- 14 ngày · 5 thành viên · Tái dụng ≥ 70% code cũ · 100% local

---

## SLIDE 3 — Kiến trúc hệ thống

**Tiêu đề:** Pipeline Architecture

**Sơ đồ (dùng SmartArt hoặc hình vẽ):**

```
[Binance API]
     ↓ Python fetch_binance.py
[raw/*.csv]
     ↓ psql \copy / Pentaho 01_clean.kjb
[staging.ohlcv_raw]
     ↓ SQL fallback / Pentaho 02_transform.kjb
[staging.fact_prep]
     ↓ 03_load_gold.sql (TRUNCATE + INSERT)
[gold.fact_market_daily]  ←  Star Schema
     ↓
┌─────────────────────────────┐
│ Power BI │ Streamlit │ AI   │
└─────────────────────────────┘
```

**Orchestration:** `run_pipeline.bat` — 1 click chạy toàn bộ  
**Scheduler:** Windows Task Scheduler 01:00 hàng ngày

---

## SLIDE 4 — Star Schema (Gold Layer)

**Tiêu đề:** Thiết kế kho dữ liệu — Star Schema

**Sơ đồ:**
- `fact_market_daily` ở trung tâm
- 3 dimension: `dim_date`, `dim_coin`, `dim_category`

**Fact table — các metrics quan trọng:**

| Metric | Công thức |
|--------|-----------|
| `return_pct` | `(close−open)/open×100` |
| `log_return` | `ln(close) − ln(open)` |
| `volatility` | `high − low` |
| `z_score_close` | Rolling 30d Z-Score |
| `is_anomaly` | `\|z_score\| > 2` |
| `regime_label` | Bull / Bear / Sideways |
| `market_dominance_pct` | `volume_usd / SUM(ngày) × 100` |

**Số liệu:**
- **7.300 dòng** trong Gold (10 coin × 730 nến)
- **Full Load** — TRUNCATE + INSERT mỗi lần chạy

---

## SLIDE 5 — ETL Pipeline chi tiết

**Tiêu đề:** 3 bước Transformation

**Timeline dạng arrows:**

```
STEP 1: Ingestion          STEP 2: Clean           STEP 3: Transform
─────────────────          ──────────────          ─────────────────
Python fetch               Pentaho PDI             SQL / Pentaho PDI
10 coin × 730 nến  →  Filter null/invalid  →  Tính metrics + FK join
Binance /klines            Epoch → DATE            Insert gold layer
Retry + rate limit         Dedup (symbol,date)     OLAP views refresh
```

**Reuse highlights:**
- ✅ `parsers.py` — copy 100% từ `preprocess_stocks.py`
- ✅ Công thức return/volatility — reuse 100%
- ✅ Z-Score logic — adapt từ `datamining_analysis.py`

---

## SLIDE 6 — Kết quả Pipeline

**Tiêu đề:** Bằng chứng Pipeline E2E

**KPI boxes (4 ô):**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   7,300      │  │   3 lần      │  │   7/7        │  │  ~12–13s     │
│  Gold rows   │  │  chạy thành  │  │  verify      │  │  mỗi lần    │
│  (10×730)    │  │  công        │  │  queries OK  │  │  chạy       │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

**Verify queries (trích từ `docs/06_e2e_evidence.md`):**
- V1: `staging.fact_prep` = 7.300 rows ✅
- V2: `gold.fact_market_daily` = `staging.fact_prep` rows ✅
- V4: `SUM(market_dominance_pct)` ≈ 100 cho 100% ngày ✅
- V6: Công thức `return_pct`, `log_return` khớp 100% ✅

**Idempotency:** Run 2 lần → cùng kết quả ✅

---

## SLIDE 7 — AI / Machine Learning

**Tiêu đề:** 3 Phân tích AI từ Gold Layer

**3 cột:**

### 🤖 Linear Regression
- Dự báo `close_next_day`
- Features: OHLCV + MA7 + lag
- R² ~ 0.99 (auto-correlation crypto)

### 🎯 K-Means Clustering (k=3)
- Phân nhóm 10 coin
- **Cụm 1:** BTC, ETH — Low Volatility (Stable)
- **Cụm 2:** BNB, ADA, XRP — Mid Volatility
- **Cụm 3:** DOGE — High Volatility (Speculative)

### 🚨 Z-Score Anomaly Detection
- Rolling window 30 ngày
- Threshold `|z| > 2` → **874 ngày anomaly (~12%)**
- Anomaly tập trung vào Bull/Bear events

---

## SLIDE 8 — Streamlit Dashboard (Demo)

**Tiêu đề:** Web Dashboard — Streamlit

**Screenshot placeholder (chụp màn hình app):**
> *Chèn screenshot `streamlit_crypto.py` đang chạy*

**5 tabs:**
1. 📊 Overview — Line chart + Regime + Dominance
2. 🕯 Price & Volume — Candlestick + Histogram
3. 🚨 Anomaly Detection — Z-Score timeline
4. 🔍 OLAP Views — Correlation heatmap
5. 📋 Data Explorer — Filter + Download CSV

**Highlight:** Dark theme · Plotly interactive · Kết nối trực tiếp PostgreSQL Gold

---

## SLIDE 9 — Power BI Dashboard (Demo)

**Tiêu đề:** Power BI — Business Intelligence

**Screenshot placeholder:**
> *Chèn screenshot `bi/Crypto_Dashboard.pbix`*

**4 trang dashboard:**
1. Market Overview — KPI cards + Slicers
2. Price Analysis — Candlestick + Return distribution
3. Anomaly & Risk — Z-Score chart + Top anomaly table
4. Volume & OLAP — Leaderboard + Correlation heatmap

---

## SLIDE 10 — Chiến lược tái dụng code

**Tiêu đề:** Reuse ≥ 70% — Đạt yêu cầu

**Bảng:**

| Module | File cũ | File mới | Reuse |
|--------|---------|----------|-------|
| Parse helpers | `preprocess_stocks.py` | `parsers.py` | **100%** |
| Công thức tính | `preprocess_stocks.py` | Pentaho / SQL | **100%** |
| Linear Regression | `datamining_analysis.py` | `01_regression.ipynb` | **80%** |
| K-Means | `datamining_analysis.py` | `02_clustering.ipynb` | **70%** |
| Z-Score | `datamining_analysis.py` | `03_anomaly.ipynb` | **80%** |
| Streamlit | `streamlit.py` | `streamlit_crypto.py` | **70%** |
| Power BI | `Stock_Dashboard.pbix` | `Crypto_Dashboard.pbix` | **60%** |

**Tổng: ~72% reuse** ✅

---

## SLIDE 11 — Phân chia công việc

**Tiêu đề:** 5 thành viên — Cân bằng effort

**Bảng:**

| TV | Vai trò | Deliverables | Effort |
|----|---------|-------------|--------|
| TV1 | Python Ingestion | `fetch_binance.py`, `parsers.py`, seed data | ~28h |
| TV2 | Pentaho Cleaning | `01_clean.kjb`, staging DDL, reject rules | ~28h |
| TV3 | Transform + Gold + OLAP | `02_transform.kjb`, gold DDL, SQL, OLAP views | ~30h |
| TV4 | Orchestration | `run_pipeline.bat`, scheduler, E2E test | ~30h |
| TV5 | BI / AI / Docs | Power BI, Streamlit, 3 notebooks, README | ~28h |

**Tổng: ~144h / 5 người = ~29h/người ≈ 2h/ngày × 14 ngày**

---

## SLIDE 12 — Kết luận & Demo

**Tiêu đề:** Kết luận

**Đạt được:**
- ✅ Pipeline ETL hoàn chỉnh end-to-end (Binance → Gold)
- ✅ Star Schema chuẩn — 7.300 dòng, idempotent
- ✅ 3 OLAP views phục vụ BI
- ✅ 3 AI notebooks (Regression, Clustering, Anomaly)
- ✅ Streamlit Dashboard 5-tab
- ✅ Power BI Dashboard 4-page
- ✅ Tái dụng ~72% code cũ (vượt ngưỡng 70%)

**Hướng phát triển:**
- 🔄 Thêm SCD Type 2 khi Polygon rebrand POL thay MATIC
- 📈 LSTM / Prophet để cải thiện dự báo giá
- ☁️ Migrate lên cloud (AWS RDS + Airflow)

---

## SLIDE 13 — Q&A

**Tiêu đề:**

```
Cảm ơn thầy/cô và các bạn!

Q & A
```

**Thông tin nhóm:**
- GitHub repo: `[link repo]`
- Demo chạy tại: `http://localhost:8501`

---

## Hướng dẫn làm slide

### Công cụ đề xuất
- **Canva** (dark template sẵn có) — nhanh nhất
- **Google Slides** — dễ share, cộng tác
- **PowerPoint** — chuyên nghiệp hơn

### Màu sắc (GitHub Dark theme)
```
Background:  #0d1117
Surface:     #161b22
Border:      #30363d
Text:        #e6edf3
Muted text:  #8b949e
Blue:        #58a6ff
Green:       #3fb950
Red:         #f85149
Yellow:      #d29922
```

### Font
- **Tiêu đề:** Inter Bold hoặc Montserrat Bold
- **Body:** Inter Regular hoặc Roboto

### Kịch bản video demo (5 phút)

| Thời gian | Nội dung | Người trình bày |
|-----------|----------|----------------|
| 0:00–0:30 | Giới thiệu đề tài, kiến trúc | TV5 |
| 0:30–1:30 | Demo chạy `run_pipeline.bat` — thấy PIPELINE SUCCESS | TV4 |
| 1:30–2:30 | Demo Power BI — overview + anomaly page | TV5 |
| 2:30–3:30 | Demo Streamlit — các tab | TV5 |
| 3:30–4:30 | Demo 1 notebook AI (regression hoặc clustering) | TV5 |
| 4:30–5:00 | Kết luận — đạt 72% reuse, 7300 rows | TV5 |
