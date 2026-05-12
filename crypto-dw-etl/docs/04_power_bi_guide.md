# 04 — Hướng dẫn Power BI Dashboard (TV5 task 5.1 & 5.2)

## Yêu cầu trước khi bắt đầu

- Power BI Desktop (phiên bản mới nhất — tải miễn phí tại microsoft.com/power-bi)
- Driver kết nối PostgreSQL: **Npgsql** ODBC — tải tại https://github.com/npgsql/npgsql/releases  
  → Cài file `Npgsql-<version>.msi`, chọn tuỳ chọn **ODBC Driver**
- Pipeline đã chạy xong và Gold layer có dữ liệu (`gold.fact_market_daily`)

---

## Bước 1 — Cài Npgsql ODBC Driver

1. Tải `Npgsql-X.Y.Z.msi` từ link trên
2. Chạy installer, **tick chọn "Npgsql GAC Installation"** và **"ODBC Driver"**
3. Restart máy nếu được yêu cầu
4. Kiểm tra: Mở **ODBC Data Source Administrator** (tìm trong Start) → tab **System DSN** → thấy **PostgreSQL Unicode** là OK

---

## Bước 2 — Kết nối Power BI → PostgreSQL

1. Mở **Power BI Desktop**
2. **Home → Get Data → More…** → tìm **PostgreSQL database** → Connect
3. Điền thông tin:
   - **Server:** `127.0.0.1`
   - **Database:** `crypto_dw_etl`
   - **Data Connectivity mode:** Import *(hoặc DirectQuery nếu muốn realtime)*
4. Click **OK** → nhập credentials:
   - **User name:** `crypto_etl`
   - **Password:** `crypto_etl` *(hoặc theo .env của bạn)*
5. Chọn **Database** → Click **Connect**

---

## Bước 3 — Import các bảng cần thiết

Trong **Navigator**, tích chọn các bảng sau:

| Bảng/View | Mục đích |
|-----------|---------|
| `gold.fact_market_daily` | Bảng fact chính |
| `gold.dim_date` | Dimension ngày |
| `gold.dim_coin` | Dimension coin |
| `gold.dim_category` | Dimension category |
| `gold.v_weekly_return_by_category` | OLAP view — dùng cho trend chart |
| `gold.v_top_anomalies` | OLAP view — dùng cho anomaly table |
| `gold.v_volume_leaderboard` | OLAP view — dùng cho volume rank |

→ Click **Load** (hoặc **Transform Data** nếu cần chỉnh sửa)

---

## Bước 4 — Thiết lập Relationships (Model View)

Vào **Model View** (biểu tượng sơ đồ bên trái). Kiểm tra Power BI đã tự nhận relationship chưa.  
Nếu chưa, tạo thủ công:

| From | To | Cardinality |
|------|----|-------------|
| `fact_market_daily.date_id` | `dim_date.date_id` | Many → One |
| `fact_market_daily.coin_id` | `dim_coin.coin_id` | Many → One |
| `fact_market_daily.category_id` | `dim_category.category_id` | Many → One |

---

## Bước 5 — Tạo Measures (DAX)

Trong **Report View**, click **New Measure** và tạo các measure sau:

```dax
-- Tổng volume USD
Total Volume USD = SUM(fact_market_daily[volume_usd])

-- Giá đóng cửa mới nhất
Latest Close = 
CALCULATE(
    MAX(fact_market_daily[close]),
    LASTDATE(dim_date[full_date])
)

-- Return trung bình (%)
Avg Return % = AVERAGE(fact_market_daily[return_pct])

-- Số ngày anomaly
Anomaly Days = COUNTROWS(FILTER(fact_market_daily, fact_market_daily[is_anomaly] = TRUE()))

-- Tỉ lệ anomaly (%)
Anomaly Rate % = DIVIDE([Anomaly Days], COUNTROWS(fact_market_daily)) * 100

-- Bull day count
Bull Days = COUNTROWS(FILTER(fact_market_daily, fact_market_daily[regime_label] = "Bull"))

-- Bear day count
Bear Days = COUNTROWS(FILTER(fact_market_daily, fact_market_daily[regime_label] = "Bear"))
```

---

## Bước 6 — Xây dựng Dashboard (layout đề xuất)

### Page 1 — Market Overview

| Visual | Fields | Vị trí |
|--------|--------|--------|
| **KPI Card** — Total Volume | `Total Volume USD` | Top-left |
| **KPI Card** — Avg Return % | `Avg Return %` | Top-center |
| **KPI Card** — Anomaly Days | `Anomaly Days` | Top-right |
| **Line Chart** — Giá close theo thời gian | X: `dim_date[full_date]` · Y: `fact[close]` · Legend: `dim_coin[symbol]` | Center |
| **Stacked Bar** — Regime distribution | X: `dim_coin[symbol]` · Y: Count · Legend: `fact[regime_label]` | Bottom-left |
| **Donut** — Market Dominance | Values: `Total Volume USD` · Legend: `dim_coin[symbol]` | Bottom-right |
| **Slicer** — Coin | Field: `dim_coin[symbol]` | Left panel |
| **Slicer** — Date range | Field: `dim_date[full_date]` | Left panel |

### Page 2 — Price Analysis

| Visual | Fields | Ghi chú |
|--------|--------|---------|
| **Candlestick** (Visual mới — cần import) | OHLC từ `fact_market_daily` | Tìm "Candlestick" trong AppSource |
| **Histogram** — Return % distribution | Field: `fact[return_pct]` | Dùng Column Chart với bins |
| **Area Chart** — Volatility | X: `dim_date[full_date]` · Y: `fact[volatility]` | Per coin |
| **Scatter** — Return vs Volatility | X: `Avg Return %` · Y: Avg volatility · Size: volume | Per coin |

### Page 3 — Anomaly & Risk

| Visual | Fields | Ghi chú |
|--------|--------|---------|
| **Line Chart** — Z-Score timeline | X: date · Y: `fact[z_score_close]` | Thêm reference line ±2 |
| **Table** — Top anomalies | Từ `v_top_anomalies` | Sort theo `abs_z_score_close` DESC |
| **Bar** — Anomaly rate per coin | X: coin · Y: `Anomaly Rate %` | |
| **Matrix** — Monthly anomaly heatmap | Rows: Month · Columns: Year · Values: `Anomaly Days` | |

### Page 4 — Volume & OLAP

| Visual | Fields | Ghi chú |
|--------|--------|---------|
| **Clustered Bar** — Volume leaderboard | Từ `v_volume_leaderboard` | Lọc theo ngày |
| **Line Chart** — Weekly return by category | Từ `v_weekly_return_by_category` | X: week_start_date · Y: avg_return_pct |
| **Correlation Heatmap** | Cần Matrix visual hoặc R script visual | Nếu không có, dùng bảng |

---

## Bước 7 — Định dạng & Theme

1. **View → Themes** → chọn **Dark** hoặc import theme JSON dưới đây:

```json
{
  "name": "CryptoDW Dark",
  "dataColors": ["#58a6ff","#3fb950","#f85149","#d29922","#bc8cff","#39d353","#ff7b72","#79c0ff"],
  "background": "#0d1117",
  "foreground": "#e6edf3",
  "tableAccent": "#58a6ff"
}
```

Lưu file trên thành `crypto_theme.json` rồi **Browse for themes** → import.

2. Thêm **logo/title** ở header mỗi trang
3. Dùng **Text box** cho subtitle mô tả từng trang

---

## Bước 8 — Lưu file

- Lưu file vào: `bi/Crypto_Dashboard.pbix`
- Commit vào Git: `git add bi/Crypto_Dashboard.pbix && git commit -m "feat(tv5): add Power BI dashboard"`

---

## Lưu ý quan trọng

> ⚠️ File `.pbix` lưu connection string nhưng **không lưu password**. Mỗi lần mở file, Power BI sẽ hỏi lại credentials → nhập `crypto_etl` / `crypto_etl`.

> 💡 Nếu máy không cài được Npgsql, dùng phương án thay thế:  
> Export Gold layer ra CSV bằng lệnh psql rồi import CSV vào Power BI:
> ```bash
> psql -U crypto_etl -d crypto_dw_etl -c "\copy (SELECT * FROM gold.fact_market_daily) TO 'gold_fact.csv' CSV HEADER"
> ```
