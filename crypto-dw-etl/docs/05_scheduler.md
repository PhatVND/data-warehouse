# 05 — Scheduler (TV4 task 4.4)

> Hướng dẫn lịch chạy `run_pipeline.bat` mỗi ngày 01:00 sáng.
> Spec yêu cầu **Windows Task Scheduler** + screenshot. Phần dưới còn cover thêm `schtasks.exe` (CLI) và `cron` (Linux/WSL) để dev cũng schedule được.

---

## 1. Windows Task Scheduler — GUI (theo spec)

1. Mở `Task Scheduler` (Start → gõ "Task Scheduler").
2. Trong panel phải, click **Create Basic Task...**.
3. Wizard:
   - **Name**: `CryptoDW-ETL Daily`.
   - **Description**: `Run Binance ingestion + ETL load every night.`.
   - **Trigger**: Daily.
   - **Start time**: `01:00:00`. Recur every: `1` day.
   - **Action**: Start a program.
   - **Program/script**: trỏ đường dẫn tuyệt đối tới `run_pipeline.bat`. Ví dụ:
     ```
     C:\Users\<user>\projects\crypto-dw-etl\run_pipeline.bat
     ```
   - **Start in (optional)**: thư mục project (rất quan trọng — nếu không, đường dẫn relative trong `.bat` hỏng):
     ```
     C:\Users\<user>\projects\crypto-dw-etl
     ```
4. Sau khi finish, mở task vừa tạo → **Properties** → tab **General**:
   - Tích **Run whether user is logged on or not** (cron đêm khi máy logout).
   - Tích **Run with highest privileges** (đảm bảo psql/python execute path đầy đủ).
5. Tab **Settings**:
   - Tích **Allow task to be run on demand**.
   - Tích **If the task fails, restart every: 5 minutes; up to: 3 times**.
   - **Stop the task if it runs longer than: 1 hour** (pipeline chỉ cần ~15s, 1h là buffer rất rộng).
6. **Save**, nhập password Windows nếu Task Scheduler hỏi.

### Test thủ công ngay sau khi save

- Click chuột phải task → **Run**.
- Chờ `Last Run Result` chuyển sang `(0x0)`.
- Mở `logs\<YYYY-MM-DD>.log` → phải thấy dòng `PIPELINE SUCCESS`.

### Ảnh screenshot (placeholder)

> Đặt screenshot tại `docs/img/scheduler.png` khi team chạy thật trên Windows. Yêu cầu chụp 2 khung:
>
> 1. Khung **Triggers** thể hiện `Daily 01:00:00`.
> 2. Khung **Actions** thể hiện đường dẫn `run_pipeline.bat`.

---

## 2. Windows Task Scheduler — CLI (`schtasks`)

Tương đương cấu hình GUI ở trên, dán vào CMD chạy `As Administrator`:

```cmd
schtasks /Create ^
    /SC DAILY ^
    /ST 01:00 ^
    /TN "CryptoDW-ETL Daily" ^
    /TR "\"C:\Users\<user>\projects\crypto-dw-etl\run_pipeline.bat\"" ^
    /RL HIGHEST ^
    /F
```

Verify:

```cmd
schtasks /Query /TN "CryptoDW-ETL Daily" /V /FO LIST
```

Run ngay (test):

```cmd
schtasks /Run /TN "CryptoDW-ETL Daily"
```

Xóa khi không dùng:

```cmd
schtasks /Delete /TN "CryptoDW-ETL Daily" /F
```

---

## 3. Linux / WSL2 — `cron` (alternative)

Nếu dev hoặc CI chạy trên Linux/WSL:

```bash
crontab -e
```

Thêm dòng (chỉnh path):

```cron
0 1 * * * cd /home/<user>/projects/crypto-dw-etl && /usr/bin/bash run_pipeline.sh >> /tmp/cron.crypto-dw-etl.log 2>&1
```

> Nếu chạy trên WSL2, mở terminal Ubuntu phải sang `service cron start` (WSL2 không tự start cron daemon).

Verify:

```bash
crontab -l
sudo grep CRON /var/log/syslog | tail
```

---

## 4. Acceptance checklist

| # | Tiêu chí | Cách kiểm |
|---|---|---|
| 1 | Task tồn tại trong Task Scheduler với tên `CryptoDW-ETL Daily` | `schtasks /Query /TN "CryptoDW-ETL Daily"` |
| 2 | Trigger Daily 01:00 | xem tab Triggers |
| 3 | Action trỏ tới `run_pipeline.bat` | xem tab Actions |
| 4 | Manual run thành công | `schtasks /Run ...` rồi tail `logs/<today>.log` thấy `PIPELINE SUCCESS` |
| 5 | Screenshot lưu tại `docs/img/scheduler.png` | đính vào báo cáo cuối |

---

## 5. Troubleshooting

- **Task chạy nhưng `Last Run Result` ≠ 0x0**: mở `logs\<YYYY-MM-DD>.log`, dò ngược lên dòng `STEP N FAILED (rc=...)`. Reproducer: chạy `run_pipeline.bat` thủ công từ CMD trong cùng thư mục.
- **Path lỗi (psql / python not found)**: Task Scheduler không kế thừa user PATH. Fix bằng cách trong `.env` set tuyệt đối:
  - `PYTHON_BIN=C:\Python310\python.exe`
  - hoặc thêm `set PATH=%PATH%;C:\Program Files\PostgreSQL\15\bin` ở đầu `run_pipeline.bat`.
- **Cron WSL không chạy**: chạy `sudo service cron start` thủ công sau mỗi lần khởi động lại WSL, hoặc set `wsl --shutdown` rồi `wsl` để kích lại.
