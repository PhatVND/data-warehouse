# 00 — Setup hướng dẫn (TV4)

> Tài liệu setup môi trường cho **CryptoDW-ETL MVP**.
> Áp dụng cho **Windows** (môi trường chính của team — theo spec) và **Linux/WSL2** (môi trường dev/CI).

---

## 0. Tổng quan

Pipeline cần 3 thành phần:

1. **Python 3.10+** — chạy `scripts/1_fetch_binance.py` để fetch data từ Binance.
2. **PostgreSQL 15** — lưu staging và gold layer.
3. **Pentaho PDI 9.x** — clean (TV2) và transform (TV3).
   *(Trong MVP có flag `USE_PENTAHO=0` để bypass Pentaho và dùng SQL fallback. Xem `run_pipeline.bat`.)*

---

## 1. Python

### Windows

1. Cài Python 3.10+ từ https://www.python.org/downloads/ (đánh dấu "Add Python to PATH").
2. Mở PowerShell ở thư mục project:
   ```powershell
   cd C:\path\to\crypto-dw-etl
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Linux / WSL2

```bash
cd crypto-dw-etl
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Test nhanh:

```bash
python -m unittest tests.test_parsers
```

---

## 2. PostgreSQL

### 2.A. Windows (môi trường production của team)

1. Tải **PostgreSQL 15** từ https://www.postgresql.org/download/windows/ (Installer của EnterpriseDB).
2. Cài đặt với các option:
   - Component: PostgreSQL Server, pgAdmin 4, Command Line Tools.
   - Data directory: mặc định.
   - Password: ghi nhớ mật khẩu cho user `postgres`.
   - Port: `5432` (mặc định).
   - Locale: `C` hoặc mặc định.
3. Sau khi cài xong, thêm `C:\Program Files\PostgreSQL\15\bin` vào `PATH`.
4. Bootstrap role + database (chỉ chạy 1 lần):
   ```cmd
   set PGPASSWORD=<mat_khau_postgres>
   psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -f sql\00_db_bootstrap.sql
   ```
   Script tạo:
   - role `crypto_etl` (LOGIN, SUPERUSER, password `crypto_etl`)
   - database `crypto_dw_etl` owner `crypto_etl`
5. Áp DDL + seed:
   ```cmd
   set PGPASSWORD=crypto_etl
   psql -h 127.0.0.1 -p 5432 -U crypto_etl -d crypto_dw_etl -f sql\01_staging_ddl.sql -f sql\02_gold_ddl.sql -f sql\dim_date_seed.sql
   psql -h 127.0.0.1 -p 5432 -U crypto_etl -d crypto_dw_etl -c "\copy gold.dim_category FROM seed\dim_category.csv CSV HEADER"
   psql -h 127.0.0.1 -p 5432 -U crypto_etl -d crypto_dw_etl -c "\copy gold.dim_coin     FROM seed\dim_coin.csv     CSV HEADER"
   ```
6. Verify:
   ```cmd
   psql -U crypto_etl -d crypto_dw_etl -c "SELECT 'dim_date' tbl, COUNT(*) FROM gold.dim_date UNION ALL SELECT 'dim_coin', COUNT(*) FROM gold.dim_coin UNION ALL SELECT 'dim_category', COUNT(*) FROM gold.dim_category;"
   ```
   Kết quả mong đợi: `dim_date` ≥ 2000, `dim_coin` = 10, `dim_category` = 4.

### 2.B. Linux / WSL2 (dev cluster local — không cần sudo cho lần chạy sau)

Có sẵn helper `tools/init_local_pg.sh` quản lý cluster local trong `.local_pgdata/` (đã có trong `.gitignore`).

```bash
# Lần đầu (cần postgresql-server đã cài, ví dụ: sudo apt install postgresql)
# Nếu PG service hệ thống đang chạy port 5432, stop trước:
sudo service postgresql stop

# Init + start + bootstrap role/db
bash tools/init_local_pg.sh init

# Áp DDL + seed
PGHOST=127.0.0.1 PGPORT=5432 PGUSER=crypto_etl PGPASSWORD=crypto_etl PGDATABASE=crypto_dw_etl \
    psql -v ON_ERROR_STOP=1 \
    -f sql/01_staging_ddl.sql -f sql/02_gold_ddl.sql -f sql/dim_date_seed.sql
PGHOST=127.0.0.1 PGPORT=5432 PGUSER=crypto_etl PGPASSWORD=crypto_etl PGDATABASE=crypto_dw_etl \
    psql -c "\copy gold.dim_category FROM 'seed/dim_category.csv' CSV HEADER"
PGHOST=127.0.0.1 PGPORT=5432 PGUSER=crypto_etl PGPASSWORD=crypto_etl PGDATABASE=crypto_dw_etl \
    psql -c "\copy gold.dim_coin FROM 'seed/dim_coin.csv' CSV HEADER"
```

Sub-commands của helper:

| Lệnh | Tác dụng |
|---|---|
| `init` | initdb + start + chạy `00_db_bootstrap.sql`. |
| `start` | Start cluster nếu đang stop. |
| `stop` | Stop cluster. |
| `status` | Hiện trạng cluster. |
| `reset` | **Xóa sạch** `.local_pgdata` + `.local_pglog`. Hỏi xác nhận. |

> **Lưu ý:** `auth-host=trust` chỉ dùng cho cluster dev local. Bản Windows chính thức của team vẫn dùng `md5` + password.

---

## 3. Pentaho PDI 9.x

> Trong MVP có thể bypass Pentaho (`USE_PENTAHO=0` trong `.env`). Tuy nhiên TV2 (`01_clean.kjb`) và TV3 (`02_transform.kjb`) cần Pentaho để chạy job thực sự. Phần này ghi cách cài.

### 3.A. Windows

1. Tải **Pentaho Data Integration Community Edition 9.x** (file `pdi-ce-9.x.x.x-zip.zip`) từ https://sourceforge.net/projects/pentaho/files/Pentaho/ (chọn bản 9.4 hoặc 9.5).
2. Giải nén vào `crypto-dw-etl\tools\pentaho\` (thư mục `tools/pentaho/` đã được `.gitignore`).
   ```
   crypto-dw-etl\tools\pentaho\data-integration\
       Spoon.bat
       Kitchen.bat
       Pan.bat
       lib\
       ...
   ```
3. Cần Java 8 hoặc 11. Cài nếu chưa có (Adoptium JDK 11 khuyến nghị) và set:
   ```cmd
   setx PENTAHO_JAVA_HOME "C:\Program Files\Eclipse Adoptium\jdk-11"
   ```
4. **JDBC PostgreSQL driver:** tải `postgresql-42.7.x.jar` từ https://jdbc.postgresql.org/download/ và copy vào:
   ```
   crypto-dw-etl\tools\pentaho\data-integration\lib\postgresql-42.7.x.jar
   ```
5. Set env:
   ```cmd
   setx PENTAHO_HOME "C:\path\to\crypto-dw-etl\tools\pentaho\data-integration"
   ```
6. Test mở Spoon: chạy `tools\pentaho\data-integration\Spoon.bat`, mở `etl\pdi\02_transform.kjb`. Phải mở được không lỗi.
7. Test connect DB: trong Spoon → View → Database connections → tạo mới → host `127.0.0.1`, port `5432`, db `crypto_dw_etl`, user `crypto_etl`, password `crypto_etl` → Test → Success.

### 3.B. Linux / WSL2 (optional — chỉ khi cần test Pentaho trên dev)

```bash
mkdir -p tools/pentaho && cd tools/pentaho
# Tải bản 9.4
curl -L -o pdi.zip "https://sourceforge.net/projects/pentaho/files/Pentaho/9.4/client-tools/pdi-ce-9.4.0.0-343.zip/download"
unzip -q pdi.zip
# JDBC driver
curl -L -o data-integration/lib/postgresql-42.7.4.jar \
    https://jdbc.postgresql.org/download/postgresql-42.7.4.jar
chmod +x data-integration/*.sh
export PENTAHO_HOME="$(pwd)/data-integration"
```

---

## 4. Cấu hình `.env`

Project dùng `.env.example` làm template. Copy thành `.env` và điều chỉnh:

```bash
cp .env.example .env
```

Các biến chính:

| Biến | Default | Mô tả |
|---|---|---|
| `PG_HOST` | `127.0.0.1` | PostgreSQL host |
| `PG_PORT` | `5432` | PostgreSQL port |
| `PG_DATABASE` | `crypto_dw_etl` | DB name |
| `PG_USER` | `crypto_etl` | DB user |
| `PG_PASSWORD` | `crypto_etl` | DB password |
| `USE_PENTAHO` | `0` | `1` để chạy Pentaho `02_transform.kjb` thay vì SQL fallback |
| `USE_PENTAHO_CLEAN` | `0` | `1` để chạy Pentaho `01_clean.kjb` thay vì `\copy` |
| `PENTAHO_HOME` | (rỗng) | đường dẫn `data-integration/` |

---

## 5. Sanity check toàn bộ setup

Sau khi xong các bước trên, trên Windows hoặc Linux:

```bash
# Linux
bash run_pipeline.sh
# Windows
run_pipeline.bat
```

Kết quả mong đợi:
- Exit code 0.
- File `logs/<YYYY-MM-DD>.log` có dòng `PIPELINE SUCCESS`.
- `SELECT COUNT(*) FROM gold.fact_market_daily;` ≈ 7300.

Chi tiết verify xem `docs/06_e2e_evidence.md`.
