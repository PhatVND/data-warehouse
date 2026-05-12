param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Add-Type -AssemblyName System.Drawing

$assetsDir = Join-Path $ProjectRoot "slide_assets"
New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

$rawDir = Join-Path $ProjectRoot "raw"
$csvFiles = Get-ChildItem -Path $rawDir -Filter "*_raw.csv" | Sort-Object Name
$rows = @()
foreach ($file in $csvFiles) {
    $data = Import-Csv -Path $file.FullName
    foreach ($row in $data) {
        $rows += $row
    }
}

$coinStats = foreach ($file in $csvFiles) {
    $data = Import-Csv -Path $file.FullName
    [PSCustomObject]@{
        Coin = $file.BaseName.Replace("_raw", "")
        Rows = $data.Count
        SizeKB = [math]::Round($file.Length / 1KB, 1)
    }
}

$nowMs = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
$nullRows = 0
$highLowRows = 0
$negativeVolumeRows = 0
$futureRows = 0
$badSymbolRows = 0
$dupeMap = @{}

foreach ($row in $rows) {
    if ([string]::IsNullOrWhiteSpace($row.open_time) -or
        [string]::IsNullOrWhiteSpace($row.open) -or
        [string]::IsNullOrWhiteSpace($row.high) -or
        [string]::IsNullOrWhiteSpace($row.low) -or
        [string]::IsNullOrWhiteSpace($row.close) -or
        [string]::IsNullOrWhiteSpace($row.volume)) {
        $nullRows++
    }

    $high = [decimal]$row.high
    $low = [decimal]$row.low
    $volume = [decimal]$row.volume
    $openTime = [int64]$row.open_time

    if ($high -lt $low) { $highLowRows++ }
    if ($volume -lt 0) { $negativeVolumeRows++ }
    if ($openTime -gt $nowMs) { $futureRows++ }
    if ($row.symbol -match "USDT$") { $badSymbolRows++ }

    $key = "$($row.symbol)|$($row.open_time)"
    if ($dupeMap.ContainsKey($key)) {
        $dupeMap[$key]++
    } else {
        $dupeMap[$key] = 1
    }
}

$duplicateRows = ($dupeMap.Values | Where-Object { $_ -gt 1 } | Measure-Object -Sum).Sum
if ($null -eq $duplicateRows) { $duplicateRows = 0 }

$summary = [PSCustomObject]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    raw_files = $csvFiles.Count
    total_rows = $rows.Count
    rows_per_coin = $coinStats
    cleaning_checks = [PSCustomObject]@{
        null_ohlcv_or_time = $nullRows
        high_less_than_low = $highLowRows
        negative_volume = $negativeVolumeRows
        future_date = $futureRows
        symbol_still_has_usdt_suffix = $badSymbolRows
        duplicate_symbol_open_time_rows = $duplicateRows
    }
}
$summary | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $assetsDir "asset_summary.json") -Encoding UTF8

function New-Canvas {
    param([int]$Width = 1600, [int]$Height = 900)
    $bmp = New-Object System.Drawing.Bitmap $Width, $Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    $g.Clear([System.Drawing.Color]::FromArgb(250, 252, 255))
    return @{ Bitmap = $bmp; Graphics = $g; Width = $Width; Height = $Height }
}

function Save-Canvas {
    param($Canvas, [string]$FileName)
    $path = Join-Path $assetsDir $FileName
    $Canvas.Bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $Canvas.Graphics.Dispose()
    $Canvas.Bitmap.Dispose()
}

function Font {
    param([float]$Size, [string]$Style = "Regular")
    $fontStyle = [System.Drawing.FontStyle]::$Style
    return New-Object System.Drawing.Font "Segoe UI", $Size, $fontStyle
}

function Brush {
    param([int]$R, [int]$G, [int]$B)
    return New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($R, $G, $B))
}

function Pen {
    param([int]$R, [int]$G, [int]$B, [float]$Width = 2)
    return New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb($R, $G, $B)), $Width
}

function Draw-Title {
    param($G, [string]$Title, [string]$Subtitle = "")
    $G.DrawString($Title, (Font 34 "Bold"), (Brush 25 43 70), 60, 42)
    if ($Subtitle) {
        $G.DrawString($Subtitle, (Font 17), (Brush 87 99 120), 62, 94)
    }
}

function Draw-RoundedRect {
    param($G, [int]$X, [int]$Y, [int]$W, [int]$H, $Fill, $Border)
    $r = 20
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc($X, $Y, $r, $r, 180, 90)
    $path.AddArc($X + $W - $r, $Y, $r, $r, 270, 90)
    $path.AddArc($X + $W - $r, $Y + $H - $r, $r, $r, 0, 90)
    $path.AddArc($X, $Y + $H - $r, $r, $r, 90, 90)
    $path.CloseFigure()
    $G.FillPath($Fill, $path)
    $G.DrawPath($Border, $path)
    $path.Dispose()
}

function Draw-Arrow {
    param($G, [int]$X1, [int]$Y1, [int]$X2, [int]$Y2)
    $p = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(71, 85, 105)), 4
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap 6, 7
    $p.CustomEndCap = $cap
    $G.DrawLine($p, $X1, $Y1, $X2, $Y2)
    $p.Dispose()
}

# 01 pipeline overview
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Vi tri TV2 trong pipeline" "Cleaning nam giua raw CSV va PostgreSQL staging"
$labels = @("Binance API", "Python fetch", "raw/*.csv", "Pentaho Cleaning`nTV2", "staging tables", "Transform / Gold")
$xs = @(70, 315, 560, 805, 1050, 1295)
for ($i = 0; $i -lt $labels.Count; $i++) {
    $fill = if ($i -eq 3) { Brush 219 234 254 } else { Brush 255 255 255 }
    $border = if ($i -eq 3) { Pen 37 99 235 4 } else { Pen 203 213 225 3 }
    Draw-RoundedRect $g $xs[$i] 330 185 110 $fill $border
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = "Center"; $sf.LineAlignment = "Center"
    $g.DrawString($labels[$i], (Font 18 "Bold"), (Brush 30 41 59), (New-Object System.Drawing.RectangleF $xs[$i],330,185,110), $sf)
    if ($i -lt $labels.Count - 1) { Draw-Arrow $g ($xs[$i] + 190) 385 ($xs[$i+1] - 10) 385 }
}
$g.DrawString("Input cua TV2: 10 file CSV, moi file 730 dong", (Font 20), (Brush 37 99 235), 315, 520)
$g.DrawString("Output cua TV2: staging.ohlcv_raw + staging.reject_log", (Font 20), (Brush 37 99 235), 820, 565)
Save-Canvas $c "01_pipeline_tv2.png"

# 02 deliverables map
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Deliverables cua Thanh vien 2" "4 dau ra chinh cua phan Pentaho Cleaning"
$items = @(
    @("01_clean.kjb", "Job dieu phoi: truncate -> clean -> log"),
    @("01_clean_ohlcv.ktr", "Transformation doc CSV, validate, dedupe"),
    @("01_staging_ddl.sql", "Tao staging.ohlcv_raw, reject_log, fact_prep"),
    @("02_cleaning.md", "Tai lieu rule reject va query verify")
)
$colors = @(@(239,246,255), @(240,253,244), @(255,247,237), @(245,243,255))
for ($i = 0; $i -lt 4; $i++) {
    $x = 130 + (($i % 2) * 690)
    $y = 240 + ([math]::Floor($i / 2) * 230)
    $fill = Brush $colors[$i][0] $colors[$i][1] $colors[$i][2]
    Draw-RoundedRect $g $x $y 570 150 $fill (Pen 148 163 184 3)
    $g.DrawString($items[$i][0], (Font 24 "Bold"), (Brush 15 23 42), ($x + 30), ($y + 30))
    $g.DrawString($items[$i][1], (Font 18), (Brush 71 85 105), ($x + 30), ($y + 82))
}
Save-Canvas $c "02_deliverables_tv2.png"

# 03 raw volume
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Du lieu raw dau vao TV2" "Thong ke doc truc tiep tu folder raw/"
$maxRows = ($coinStats.Rows | Measure-Object -Maximum).Maximum
$barX = 170; $barY = 190; $barW = 92; $gap = 35; $chartH = 470
$axisPen = Pen 100 116 139 2
$g.DrawLine($axisPen, 110, 670, 1490, 670)
$g.DrawLine($axisPen, 110, 180, 110, 670)
for ($i = 0; $i -lt $coinStats.Count; $i++) {
    $h = [int](($coinStats[$i].Rows / $maxRows) * $chartH)
    $x = $barX + $i * ($barW + $gap)
    $y = 670 - $h
    $fill = Brush 14 165 233
    $g.FillRectangle($fill, $x, $y, $barW, $h)
    $g.DrawString([string]$coinStats[$i].Rows, (Font 15 "Bold"), (Brush 15 23 42), ($x + 19), ($y - 30))
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = "Center"
    $g.DrawString($coinStats[$i].Coin, (Font 16 "Bold"), (Brush 51 65 85), (New-Object System.Drawing.RectangleF $x, 690, $barW, 35), $sf)
}
$g.DrawString("Tong: $($rows.Count) dong = $($csvFiles.Count) coin x 730 ngay", (Font 24 "Bold"), (Brush 37 99 235), 540, 760)
Save-Canvas $c "03_raw_input_counts.png"

# 04 staging schema
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Schema staging cho lop Cleaning" "TV2 tao bang tiep nhan raw, bang reject va bang trung gian"
$tables = @(
    @("staging.ohlcv_raw", "Du lieu hop le sau clean", "symbol, open_time, open/high/low/close, volume..."),
    @("staging.reject_log", "Audit dong bi loai", "reject_id, source_file, symbol, open_time_raw, reject_reason"),
    @("staging.fact_prep", "Bang trung gian cho TV3", "date_id, coin_id, metrics da tinh o buoc transform")
)
$tx = @(130, 575, 1020)
for ($i = 0; $i -lt 3; $i++) {
    Draw-RoundedRect $g $tx[$i] 255 360 285 (Brush 255 255 255) (Pen 148 163 184 3)
    $g.FillRectangle((Brush 30 64 175), $tx[$i], 255, 360, 62)
    $g.DrawString($tables[$i][0], (Font 21 "Bold"), (Brush 255 255 255), ($tx[$i] + 22), 272)
    $g.DrawString($tables[$i][1], (Font 19 "Bold"), (Brush 15 23 42), ($tx[$i] + 24), 350)
    $rect = New-Object System.Drawing.RectangleF ($tx[$i] + 24), 405, 310, 95
    $g.DrawString($tables[$i][2], (Font 16), (Brush 71 85 105), $rect)
}
Draw-Arrow $g 492 398 570 398
Draw-Arrow $g 935 398 1015 398
$g.DrawString("Full Load: truncate staging truoc moi lan chay de rerun an toan", (Font 23 "Bold"), (Brush 37 99 235), 390, 680)
Save-Canvas $c "04_staging_schema.png"

# 05 cleaning flow
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Flow xu ly trong Pentaho Cleaning" "Dong hop le di sang ohlcv_raw, dong loi di sang reject_log"
$steps = @("CSV Input", "Normalize`nsymbol", "Null`nOHLCV?", "High >= Low?", "Volume >= 0?", "Future date?", "Sort +`nDedupe", "Write`nohlcv_raw")
$x0 = 70
for ($i = 0; $i -lt $steps.Count; $i++) {
    $x = $x0 + $i * 185
    $fill = if ($i -ge 2 -and $i -le 5) { Brush 254 243 199 } else { Brush 255 255 255 }
    Draw-RoundedRect $g $x 315 140 100 $fill (Pen 148 163 184 3)
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = "Center"; $sf.LineAlignment = "Center"
    $g.DrawString($steps[$i], (Font 15 "Bold"), (Brush 15 23 42), (New-Object System.Drawing.RectangleF $x,315,140,100), $sf)
    if ($i -lt $steps.Count - 1) { Draw-Arrow $g ($x + 145) 365 ($x + 180) 365 }
}
Draw-RoundedRect $g 520 590 560 105 (Brush 254 226 226) (Pen 220 38 38 3)
$sf = New-Object System.Drawing.StringFormat
$sf.Alignment = "Center"; $sf.LineAlignment = "Center"
$g.DrawString("Reject stream: gan reject_reason -> staging.reject_log", (Font 22 "Bold"), (Brush 127 29 29), (New-Object System.Drawing.RectangleF 520,590,560,105), $sf)
Draw-Arrow $g 660 420 660 585
Draw-Arrow $g 850 420 850 585
Draw-Arrow $g 1035 420 1035 585
Save-Canvas $c "05_cleaning_flow.png"

# 06 rejection rules table
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Bo rule reject cua TV2" "Moi dong loi duoc tach ly do de de audit va sua nguon"
$headers = @("Rule", "Dieu kien", "reject_reason / xu ly")
$colX = @(95, 250, 820)
$colW = @(130, 520, 650)
$rowY = 190
$rowH = 72
$g.FillRectangle((Brush 30 64 175), 80, $rowY, 1410, $rowH)
for ($i = 0; $i -lt 3; $i++) {
    $g.DrawString($headers[$i], (Font 18 "Bold"), (Brush 255 255 255), $colX[$i], $rowY + 20)
}
$rules = @(
    @("R1/R2/R4", "Null open/high/low/close/volume/open_time", "NULL_OHLCV_OR_TIME"),
    @("R3", "Gia high nho hon low", "HIGH_LT_LOW"),
    @("R2b", "Volume am", "NEGATIVE_VOLUME"),
    @("R6", "open_time lon hon thoi diem chay job", "FUTURE_DATE"),
    @("R5", "Trung symbol va open_time", "Giu dong dau, drop duplicate")
)
for ($r = 0; $r -lt $rules.Count; $r++) {
    $y = $rowY + $rowH + $r * $rowH
    $fill = if ($r % 2 -eq 0) { Brush 248 250 252 } else { Brush 255 255 255 }
    $g.FillRectangle($fill, 80, $y, 1410, $rowH)
    for ($i = 0; $i -lt 3; $i++) {
        $font = if ($i -eq 0) { Font 18 "Bold" } else { Font 17 }
        $g.DrawString($rules[$r][$i], $font, (Brush 30 41 59), $colX[$i], $y + 20)
    }
}
$g.DrawRectangle((Pen 148 163 184 2), 80, $rowY, 1410, $rowH * 6)
Save-Canvas $c "06_rejection_rules.png"

# 07 real validation
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Ket qua verify tu raw CSV hien tai" "Cac check duoc tinh truc tiep tu 7,300 dong CSV trong repo"
$checks = @(
    @("Tong dong raw", "$($rows.Count)", "10 coin x 730 ngay"),
    @("Null OHLCV/time", "$nullRows", "Can reject neu > 0"),
    @("high < low", "$highLowRows", "Bat buoc = 0 sau clean"),
    @("volume < 0", "$negativeVolumeRows", "Bat buoc = 0 sau clean"),
    @("future date", "$futureRows", "Khong lay du lieu tuong lai"),
    @("duplicate key", "$duplicateRows", "Trung symbol-open_time")
)
for ($i = 0; $i -lt $checks.Count; $i++) {
    $x = 120 + (($i % 3) * 470)
    $y = 210 + ([math]::Floor($i / 3) * 250)
    $fill = if ($i -eq 0) { Brush 219 234 254 } elseif ($checks[$i][1] -eq "0") { Brush 220 252 231 } else { Brush 254 226 226 }
    Draw-RoundedRect $g $x $y 380 170 $fill (Pen 148 163 184 3)
    $g.DrawString($checks[$i][0], (Font 20 "Bold"), (Brush 30 41 59), ($x + 25), ($y + 25))
    $g.DrawString($checks[$i][1], (Font 42 "Bold"), (Brush 37 99 235), ($x + 25), ($y + 70))
    $g.DrawString($checks[$i][2], (Font 15), (Brush 71 85 105), ($x + 25), ($y + 128))
}
Save-Canvas $c "07_validation_results.png"

# 08 reuse mapping
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Tai su dung logic tu project cu" "TV2 chuyen logic preprocessing Python thanh cac step Pentaho"
$left = @("standardize_columns()", "Null-check OHLCV", "Dedupe symbol-date", "Filter -> error stream")
$right = @("String Operations", "Filter Null OHLCV", "Sort + Unique Rows", "Reject stream -> reject_log")
for ($i = 0; $i -lt 4; $i++) {
    $y = 210 + $i * 135
    Draw-RoundedRect $g 150 $y 410 85 (Brush 255 255 255) (Pen 203 213 225 3)
    Draw-RoundedRect $g 1035 $y 410 85 (Brush 239 246 255) (Pen 37 99 235 3)
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = "Center"; $sf.LineAlignment = "Center"
    $g.DrawString($left[$i], (Font 19 "Bold"), (Brush 30 41 59), (New-Object System.Drawing.RectangleF 150,$y,410,85), $sf)
    $g.DrawString($right[$i], (Font 19 "Bold"), (Brush 30 64 175), (New-Object System.Drawing.RectangleF 1035,$y,410,85), $sf)
    Draw-Arrow $g 575 ($y + 42) 1020 ($y + 42)
}
$g.DrawString("Reuse muc tieu cua TV2: khoang 60%", (Font 24 "Bold"), (Brush 37 99 235), 585, 765)
Save-Canvas $c "08_reuse_mapping.png"

# 09 idempotency
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Full Load va kha nang rerun" "Moi lan chay cleaning deu reset staging truoc khi nap lai"
$steps = @("Run 01_clean.kjb", "TRUNCATE`nohlcv_raw + reject_log", "Read raw CSV", "Validate + dedupe", "Insert clean rows")
$xs = @(100, 390, 680, 970, 1260)
for ($i = 0; $i -lt $steps.Count; $i++) {
    $fill = if ($i -eq 1) { Brush 254 243 199 } else { Brush 255 255 255 }
    Draw-RoundedRect $g $xs[$i] 330 205 115 $fill (Pen 148 163 184 3)
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = "Center"; $sf.LineAlignment = "Center"
    $g.DrawString($steps[$i], (Font 17 "Bold"), (Brush 15 23 42), (New-Object System.Drawing.RectangleF $xs[$i],330,205,115), $sf)
    if ($i -lt $steps.Count - 1) { Draw-Arrow $g ($xs[$i] + 210) 388 ($xs[$i+1] - 10) 388 }
}
$g.DrawString("Y nghia: chay lai nhieu lan khong nhan doi du lieu staging", (Font 24 "Bold"), (Brush 37 99 235), 430, 580)
$g.DrawString("Unique index (symbol, open_time) la lop bao ve bo sung o PostgreSQL", (Font 20), (Brush 71 85 105), 435, 630)
Save-Canvas $c "09_full_load_idempotency.png"

# 10 conclusion
$c = New-Canvas
$g = $c.Graphics
Draw-Title $g "Ket luan phan TV2" "Cleaning la cong kiem soat chat luong du lieu truoc Gold layer"
$points = @(
    "Nhan 7,300 dong raw CSV tu Binance",
    "Chuan hoa symbol va validate OHLCV",
    "Tach du lieu hop le va du lieu reject",
    "Ghi staging de TV3 transform sang Gold",
    "Ho tro Full Load va rerun an toan"
)
for ($i = 0; $i -lt $points.Count; $i++) {
    $y = 215 + $i * 95
    $g.FillEllipse((Brush 37 99 235), 180, $y + 10, 28, 28)
    $g.DrawString($points[$i], (Font 25 "Bold"), (Brush 30 41 59), 235, $y)
}
Draw-RoundedRect $g 360 720 880 85 (Brush 219 234 254) (Pen 37 99 235 3)
$sf = New-Object System.Drawing.StringFormat
$sf.Alignment = "Center"; $sf.LineAlignment = "Center"
$g.DrawString("Raw CSV -> Clean + Validate -> staging.ohlcv_raw + reject_log", (Font 23 "Bold"), (Brush 30 64 175), (New-Object System.Drawing.RectangleF 360,720,880,85), $sf)
Save-Canvas $c "10_tv2_conclusion.png"

Write-Host "Generated slide assets in: $assetsDir"
Get-ChildItem -Path $assetsDir -Filter "*.png" | Select-Object Name, Length
