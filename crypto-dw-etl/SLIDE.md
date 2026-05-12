# SLIDE.md - Nội dung slide báo cáo cho Thành viên 3

## TV3 rốt cuộc báo cáo phần nào?

Theo `DeTai.md`, `docs/03_gold.md`, report `main.pdf` và code hiện tại, **Thành viên 3 không báo cáo phần fetch API, không báo cáo dashboard, không báo cáo AI notebook**.  
TV3 nên báo cáo phần:

- Transform dữ liệu từ `staging.ohlcv_raw` sang `staging.fact_prep`.
- Thiết kế Gold layer theo **Star Schema**.
- Load `gold.fact_market_daily` bằng Full Load.
- Tính các business metrics: return, log return, volatility, z-score, anomaly, rank, market dominance, regime.
- Tạo 3 OLAP views để phục vụ Power BI, Streamlit và phân tích.

Evidence đã chạy bằng `tools/run_tv3_gold_evidence.ps1`, kết quả nằm trong `slide_assets/tv3_run/`.

## Kết quả đã chạy code, lấy ở đâu?

Trong repo hiện có **2 bộ kết quả đã chạy**:

**1. Bộ kết quả full pipeline - nên dùng để báo cáo với thầy**

Nguồn: `crypto-dw-etl/docs/06_e2e_evidence.md`

Đây là evidence end-to-end sau khi chạy pipeline đầy đủ:

- `staging.fact_prep`: **7,300 rows** - mục V1.
- `gold.fact_market_daily`: **7,300 rows** - mục V2.
- `gold.fact_market_daily` không có ngày nào > 10 coin - mục V3.
- Tổng `market_dominance_pct` mỗi ngày xấp xỉ 100% - mục V4.
- 3 OLAP views select được - mục V5:
  - `v_weekly_return_by_category`: **423 rows**
  - `v_volume_leaderboard`: **7,300 rows**
  - `v_top_anomalies`: **874 rows**
- Regime/anomaly summary:
  - Sideways: **5,025**
  - Bear: **1,160**
  - Bull: **1,115**
  - Anomaly rows: **874**

**2. Bộ kết quả TV3 local evidence - dùng để chứng minh công thức TV3**

Nguồn: `crypto-dw-etl/slide_assets/tv3_run/tv3_gold_run_summary.json`  
Command đã chạy:

```powershell
powershell -ExecutionPolicy Bypass -File crypto-dw-etl/tools/run_tv3_gold_evidence.ps1
```

Kết quả local evidence:

- Raw rows: **7,300**
- `staging.fact_prep`: **7,300 rows**
- `gold.fact_market_daily`: **7,300 rows**
- Anomaly rows: **874**
- Formula sample: `slide_assets/tv3_run/formula_sample_btc.csv`

**Ghi chú quan trọng:** `v_weekly_return_by_category` trong local evidence ra **426 rows**, còn full pipeline evidence ra **423 rows** do local script mô phỏng week grouping ngoài PostgreSQL. Khi làm slide báo cáo chính thức, dùng **423 rows từ `docs/06_e2e_evidence.md`** vì đó là kết quả chạy pipeline thật.

---

## Slide 1 - TV3 phụ trách lớp Transform và Gold

**Hình chèn:** `slide_assets/tv3_run/01_tv3_flow.png`

**Nội dung ghi trên slide**

**TV3: Transform -> Gold -> OLAP**

- Nhận dữ liệu sạch từ `staging.ohlcv_raw`.
- Tính các metric phân tích vào `staging.fact_prep`.
- Full-load dữ liệu vào `gold.fact_market_daily`.
- Tạo 3 OLAP views cho BI, Streamlit và notebook.

**Kết quả chính**

- `staging.fact_prep`: **7,300 rows**
- `gold.fact_market_daily`: **7,300 rows**
- OLAP views: **3 views**

**Lời trình bày**

"Phần của em bắt đầu sau bước cleaning. Em nhận dữ liệu OHLCV đã sạch, tính các chỉ số phân tích, nạp vào Gold layer theo Star Schema và tạo các view OLAP để các phần sau như Power BI, Streamlit và notebook sử dụng."

---

## Slide 2 - Input và Output của phần TV3

**Hình chèn:** `slide_assets/tv3_run/03_tv3_evidence_counts.png`

**Nội dung ghi trên slide**

**Input**

- `staging.ohlcv_raw`
- 10 coin, mỗi coin 730 dòng
- Tổng dữ liệu đầu vào: **7,300 rows**

**Output**

- `staging.fact_prep`: **7,300 rows**
- `gold.fact_market_daily`: **7,300 rows**
- `gold.v_weekly_return_by_category`: **423 rows**
- `gold.v_volume_leaderboard`: **7,300 rows**
- `gold.v_top_anomalies`: **874 rows**

**Nguồn số liệu để đưa vào slide**

- `7,300 raw rows`: report `Contents/TienXuLy.tex`, dòng kết quả đầu ra: 10 CSV raw và khoảng 7,300 dòng.
- `staging.fact_prep = 7,300`: `docs/06_e2e_evidence.md`, mục **V1**.
- `gold.fact_market_daily = 7,300`: `docs/06_e2e_evidence.md`, mục **V2**.
- `v_weekly_return_by_category = 423`, `v_volume_leaderboard = 7,300`, `v_top_anomalies = 874`: `docs/06_e2e_evidence.md`, mục **V5**.
- `874 anomalies`: report `Contents/ketluan.tex`, mục **Anomaly Detection**.

**Lời trình bày**

"Các số này lấy từ evidence end-to-end của pipeline và được đối chiếu với report. Điểm chính là số dòng từ `fact_prep` sang `fact_market_daily` giữ nguyên 7,300, còn ba OLAP view đều select được và có số dòng cụ thể."

---

## Slide 3 - Gold Layer dùng Star Schema

**Hình chèn:** `slide_assets/report/star-dwh.png`

**Nội dung ghi trên slide**

**Gold Star Schema**

- Fact table trung tâm: `gold.fact_market_daily`
- Dimension tables:
  - `gold.dim_date`
  - `gold.dim_coin`
  - `gold.dim_category`
- Grain của fact: **1 coin / 1 ngày**
- Primary key: **`(date_id, coin_id)`**

**Vì sao chọn Star Schema?**

- Ít JOIN, truy vấn nhanh.
- Dễ dùng cho Power BI và Streamlit.
- Phù hợp quy mô MVP: 10 coin, 4 category.

**Lời trình bày**

"Theo report, nhóm chọn Star Schema thay vì Snowflake vì dữ liệu không quá lớn và cần đơn giản cho phân tích. Fact table lưu dữ liệu thị trường hằng ngày, còn ba bảng dimension giúp phân tích theo thời gian, coin và nhóm tài sản."

---

## Slide 4 - Thiết kế các bảng Gold

**Hình chèn:** `slide_assets/report/star-dwh.png`

**Nội dung ghi trên slide**

**Dimension**

- `dim_date`: ngày, tuần, tháng, quý, năm, cuối tuần.
- `dim_coin`: symbol, full name, launch year, category.
- `dim_category`: L1, L2, Meme, Payment và risk level.

**Fact**

- `fact_market_daily` lưu OHLCV và metric phân tích.
- Các ràng buộc chính:
  - `high >= low`
  - `volume_base >= 0`
  - `volume_usd >= 0`
  - `regime_label` chỉ nhận Bull / Bear / Sideways.

**Lời trình bày**

"Gold layer không chỉ lưu dữ liệu mà còn đặt ràng buộc để bảo vệ chất lượng. Ví dụ giá high không được nhỏ hơn low, volume không được âm, và nhãn regime chỉ nhận ba giá trị hợp lệ."

---

## Slide 5 - Transform: các metric được tính

**Hình chèn:** `slide_assets/tv3_run/02_tv3_metrics.png`

**Nội dung ghi trên slide**

**Metric tính ở `staging.fact_prep`**

- `return_pct = (close - open) / open * 100`
- `log_return = ln(close) - ln(open)`
- `volatility = high - low`
- `average_price = (high + low) / 2`
- `volume_usd = close * volume_base`
- `z_score_close`: rolling 30 ngày theo từng coin

**Ý nghĩa**

- Biến dữ liệu OHLCV thô thành dữ liệu phân tích.
- Là đầu vào cho anomaly detection, regime analysis và OLAP.

**Lời trình bày**

"Đây là phần quan trọng nhất của transform. Dữ liệu OHLCV ban đầu chỉ là giá và volume, còn sau bước này nhóm có các chỉ số phân tích như lợi suất, biến động, volume quy đổi USD và z-score."

---

## Slide 6 - Load Gold: business logic bổ sung

**Hình chèn:** `slide_assets/tv3_run/06_tv3_regime_distribution.png`

**Nội dung ghi trên slide**

**`03_load_gold.sql`**

- Full Load: `TRUNCATE + INSERT`
- Nạp dữ liệu từ `staging.fact_prep` vào `gold.fact_market_daily`

**Business logic tại Gold**

- `is_anomaly = ABS(z_score_close) > 2`
- `volume_rank`: rank volume theo từng ngày
- `market_dominance_pct`: tỷ trọng volume trong ngày
- `regime_label`:
  - Bull nếu `return_pct > 3`
  - Bear nếu `return_pct < -3`
  - Sideways nếu còn lại

**Kết quả regime**

- Bear: **1,160**
- Bull: **1,115**
- Sideways: **5,025**

**Lời trình bày**

"Khi load vào Gold, em bổ sung các logic nghiệp vụ như anomaly flag, rank volume, market dominance và regime label. Đây là các chỉ số giúp dashboard và OLAP không phải tính lại từ đầu."

---

## Slide 7 - Kiểm chứng kết quả chạy TV3

**Hình chèn:** `slide_assets/tv3_run/03_tv3_evidence_counts.png`

**Nội dung ghi trên slide**

**Evidence run**

- Raw rows: **7,300**
- `staging.fact_prep`: **7,300**
- `gold.fact_market_daily`: **7,300**
- Rows match: **True**

**Data quality checks**

- Không có ngày nào nhiều hơn 10 coin.
- 1,323/1,323 ngày có tổng `market_dominance_pct` xấp xỉ 100%.
- Số dòng anomaly: **874**

**Nguồn số liệu để đưa vào slide**

- `Raw rows`, `fact_prep`, `fact_market_daily`, `rows_match`: `docs/06_e2e_evidence.md`, mục **V1** và **V2**.
- `Không có ngày nào > 10 coin`: `docs/06_e2e_evidence.md`, mục **V3**.
- `1,323/1,323 ngày dominance xấp xỉ 100%`: `docs/06_e2e_evidence.md`, mục **V4**.
- `874 anomaly rows`: `docs/06_e2e_evidence.md`, mục **V5** và report `Contents/ketluan.tex`.

**Lời trình bày**

"Em kiểm chứng không chỉ bằng số dòng mà còn bằng logic. Mỗi ngày không vượt quá 10 coin, market dominance cộng lại xấp xỉ 100%, và số anomaly được phát hiện là 874 dòng."

---

## Slide 8 - Kiểm tra công thức bằng mẫu BTC

**Hình chèn:** `slide_assets/tv3_run/05_tv3_formula_sample.png`

**Nội dung ghi trên slide**

**Formula verification sample - BTC**

| date_id | open | close | return_pct | log_return | volume_usd |
|---|---:|---:|---:|---:|---:|
| 20240427 | 63770 | 63461.98 | -0.483 | -0.004842 | 1.328B |
| 20240428 | 63461.98 | 63118.62 | -0.541 | -0.005425 | 1.070B |
| 20240429 | 63118.62 | 63866 | 1.1841 | 0.011771 | 1.798B |

**Kết luận**

- `return_pct`, `log_return`, `volume_usd` khớp công thức SQL.

**Lời trình bày**

"Để chứng minh công thức đúng, em lấy ba dòng BTC đầu tiên và kiểm tra lại return, log return, volume USD. Các giá trị khớp với công thức trong SQL transform."

---

## Slide 9 - OLAP views được TV3 tạo

**Hình chèn:** `slide_assets/tv3_run/07_tv3_olap_views.png`

**Nội dung ghi trên slide**

**3 OLAP views**

- `v_weekly_return_by_category`
  - Phân tích return, log return, volatility theo tuần và category.
  - Evidence: **423 rows**
- `v_volume_leaderboard`
  - Xếp hạng volume theo ngày, có market dominance.
  - Evidence: **7,300 rows**
- `v_top_anomalies`
  - Danh sách phiên bất thường với `ABS(z_score) > 2`.
  - Evidence: **874 rows**

**Nguồn số liệu để đưa vào slide**

- Danh sách 3 OLAP views: report `Contents/OLAP.tex`, mục **Các view OLAP cốt lõi**.
- Số dòng 3 view: `docs/06_e2e_evidence.md`, mục **V5. 3 OLAP views select được**.
- Hình minh họa OLAP trong report:
  - `slide_assets/report/olap_volume_2025.png`
  - `slide_assets/report/olap_heatmap_monthly_return.png`

**Lời trình bày**

"Ba view này là lớp phục vụ phân tích. Nhờ có view, Power BI hoặc notebook chỉ cần đọc bảng đã tổng hợp thay vì tự join và group từ fact table."

---

## Slide 10 - Kết quả OLAP minh họa và kết luận TV3

**Hình chèn ưu tiên từ report:** `slide_assets/report/olap_volume_2025.png`  
**Có thể chèn thêm:** `slide_assets/report/olap_heatmap_monthly_return.png`  
**Hình tự chạy lại nếu muốn tiếng Anh:** `slide_assets/tv3_run/04_tv3_volume_2025.png`

**Nội dung ghi trên slide**

**Ví dụ OLAP output từ report: Volume leaderboard 2025**

- BTC đứng đầu thanh khoản.
- ETH và SOL là nhóm theo sau.
- Nhóm còn lại có volume thấp hơn rõ rệt.
- Hình này lấy từ `Images/OLAP/02_combined_volume_2025.png` trong report.

**Kết luận TV3**

- Đã hoàn thành Gold Star Schema.
- Đã tính đầy đủ metric phân tích từ OHLCV.
- Đã Full-load `fact_market_daily` với **7,300 rows**.
- Đã tạo 3 OLAP views cho BI, Streamlit và notebook.

**Lời trình bày**

"Tóm lại, phần TV3 biến dữ liệu sạch thành dữ liệu phân tích. Sau bước này, nhóm có fact table chuẩn Star Schema và các OLAP view sẵn sàng phục vụ trực quan hóa và khai phá dữ liệu."

---

## Hình cần chèn

| Slide | Hình |
|---|---|
| Slide 1 | `slide_assets/tv3_run/01_tv3_flow.png` |
| Slide 2 | `slide_assets/tv3_run/03_tv3_evidence_counts.png` |
| Slide 3 | `slide_assets/report/star-dwh.png` |
| Slide 4 | `slide_assets/report/star-dwh.png` |
| Slide 5 | `slide_assets/tv3_run/02_tv3_metrics.png` |
| Slide 6 | `slide_assets/tv3_run/06_tv3_regime_distribution.png` |
| Slide 7 | `slide_assets/tv3_run/03_tv3_evidence_counts.png` |
| Slide 8 | `slide_assets/tv3_run/05_tv3_formula_sample.png` |
| Slide 9 | `slide_assets/tv3_run/07_tv3_olap_views.png` |
| Slide 10 | `slide_assets/report/olap_volume_2025.png` |

## Nguồn số liệu chính

| Số liệu | Giá trị dùng trên slide | Nguồn |
|---|---:|---|
| Raw data | khoảng 7,300 dòng | Report `Contents/TienXuLy.tex` và `Contents/MoTaBaiToan.tex` |
| `staging.fact_prep` | 7,300 rows | `docs/06_e2e_evidence.md` mục V1 |
| `gold.fact_market_daily` | 7,300 rows | `docs/06_e2e_evidence.md` mục V2 |
| `v_weekly_return_by_category` | 423 rows | `docs/06_e2e_evidence.md` mục V5 |
| `v_volume_leaderboard` | 7,300 rows | `docs/06_e2e_evidence.md` mục V5 |
| `v_top_anomalies` | 874 rows | `docs/06_e2e_evidence.md` mục V5 |
| Anomaly Detection | 874 phiên bất thường | Report `Contents/ketluan.tex` |
| OLAP volume chart | BTC dẫn đầu volume 2025 | Report `Images/OLAP/02_combined_volume_2025.png` |
| OLAP heatmap | monthly return by coin | Report `Images/OLAP/03_combined_heatmap_price.png` |

## Evidence

| File | Nội dung |
|---|---|
| `slide_assets/tv3_run/tv3_gold_run_summary.json` | Summary kết quả chạy TV3 |
| `slide_assets/tv3_run/fact_market_daily_evidence.csv` | Fact output mô phỏng Gold |
| `slide_assets/tv3_run/formula_sample_btc.csv` | Mẫu BTC kiểm tra công thức |
| `slide_assets/tv3_run/tv3_run_talking_points.md` | Ý nói nhanh |

## Câu trả lời nhanh nếu thầy hỏi

- **TV3 khác TV2 thế nào?** TV2 làm sạch raw; TV3 tính metric, nạp Gold và tạo OLAP views.
- **Vì sao Star Schema?** Ít join, dễ truy vấn, phù hợp Power BI và dữ liệu MVP.
- **Vì sao Full Load?** Dữ liệu chỉ 7,300 dòng, chạy lại nhanh và tránh phức tạp incremental.
- **TV3 có kiểm chứng chưa?** Có, evidence cho thấy `fact_prep` và `fact_market_daily` đều 7,300 dòng, formulas khớp mẫu BTC.

## Chạy lại evidence TV3

```powershell
powershell -ExecutionPolicy Bypass -File crypto-dw-etl/tools/run_tv3_gold_evidence.ps1
```
