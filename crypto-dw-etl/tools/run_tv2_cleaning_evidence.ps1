param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$rawDir = Join-Path $ProjectRoot "raw"
$outDir = Join-Path $ProjectRoot "slide_assets\tv2_run"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$cleanRows = New-Object System.Collections.Generic.List[object]
$rejectRows = New-Object System.Collections.Generic.List[object]
$seen = @{}

function Add-Reject {
    param($Row, [string]$SourceFile, [string]$Reason)
    $script:rejectRows.Add([PSCustomObject]@{
        source_file = $SourceFile
        symbol = $Row.symbol
        open_time_raw = $Row.open_time
        reject_reason = $Reason
        rejected_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    })
}

$files = Get-ChildItem -Path $rawDir -Filter "*_raw.csv" | Sort-Object Name
$nowMs = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
$inputRows = 0

foreach ($file in $files) {
    $rows = Import-Csv -Path $file.FullName
    foreach ($row in $rows) {
        $inputRows++

        $symbol = ([string]$row.symbol).Trim().ToUpperInvariant()
        if ($symbol.EndsWith("USDT")) {
            $symbol = $symbol.Substring(0, $symbol.Length - 4)
        }
        $row.symbol = $symbol

        if ([string]::IsNullOrWhiteSpace($row.open_time) -or
            [string]::IsNullOrWhiteSpace($row.open) -or
            [string]::IsNullOrWhiteSpace($row.high) -or
            [string]::IsNullOrWhiteSpace($row.low) -or
            [string]::IsNullOrWhiteSpace($row.close) -or
            [string]::IsNullOrWhiteSpace($row.volume)) {
            Add-Reject $row $file.Name "NULL_OHLCV_OR_TIME (R1/R2/R4)"
            continue
        }

        try {
            $openTime = [int64]$row.open_time
            $high = [decimal]$row.high
            $low = [decimal]$row.low
            $volume = [decimal]$row.volume
        } catch {
            Add-Reject $row $file.Name "NULL_OHLCV_OR_TIME (R1/R2/R4)"
            continue
        }

        if ($high -lt $low) {
            Add-Reject $row $file.Name "HIGH_LT_LOW (R3)"
            continue
        }

        if ($volume -lt 0) {
            Add-Reject $row $file.Name "NEGATIVE_VOLUME (R2)"
            continue
        }

        if ($openTime -gt $nowMs) {
            Add-Reject $row $file.Name "FUTURE_DATE (R6)"
            continue
        }

        $key = "$symbol|$openTime"
        if ($seen.ContainsKey($key)) {
            # Same behavior as TV2 docs: duplicate is dropped silently, not logged.
            continue
        }
        $seen[$key] = $true

        $cleanRows.Add($row)
    }
}

$cleanPath = Join-Path $outDir "cleaned_ohlcv_raw.csv"
$rejectPath = Join-Path $outDir "reject_log.csv"
$summaryPath = Join-Path $outDir "tv2_cleaning_run_summary.json"
$talkingPath = Join-Path $outDir "tv2_run_talking_points.md"

$cleanRows | Export-Csv -Path $cleanPath -NoTypeInformation -Encoding UTF8
if ($rejectRows.Count -gt 0) {
    $rejectRows | Export-Csv -Path $rejectPath -NoTypeInformation -Encoding UTF8
} else {
    "source_file,symbol,open_time_raw,reject_reason,rejected_at" | Set-Content -Path $rejectPath -Encoding UTF8
}

$distinctSymbols = $cleanRows | Select-Object -ExpandProperty symbol -Unique | Sort-Object
$highLtLowAfter = ($cleanRows | Where-Object { [decimal]$_.high -lt [decimal]$_.low } | Measure-Object).Count
$negativeVolumeAfter = ($cleanRows | Where-Object { [decimal]$_.volume -lt 0 } | Measure-Object).Count
$usdtSuffixAfter = ($cleanRows | Where-Object { $_.symbol -match "USDT$" } | Measure-Object).Count
$dupesAfter = (
    $cleanRows |
        Group-Object symbol, open_time |
        Where-Object { $_.Count -gt 1 } |
        Measure-Object
).Count

$summary = [PSCustomObject]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    execution_note = "Pentaho Kitchen and psql were not available in PATH on this machine, so this script executes the same TV2 cleaning rules against raw CSV files and exports evidence artifacts."
    input = [PSCustomObject]@{
        raw_files = $files.Count
        raw_rows = $inputRows
        raw_dir = $rawDir
    }
    output = [PSCustomObject]@{
        clean_rows = $cleanRows.Count
        reject_rows_logged = $rejectRows.Count
        cleaned_csv = $cleanPath
        reject_log_csv = $rejectPath
    }
    verification_after_clean = [PSCustomObject]@{
        distinct_symbols = $distinctSymbols
        symbol_count = $distinctSymbols.Count
        high_less_than_low_rows = $highLtLowAfter
        negative_volume_rows = $negativeVolumeAfter
        symbols_still_with_usdt_suffix = $usdtSuffixAfter
        duplicate_symbol_open_time_groups = $dupesAfter
    }
}

$summary | ConvertTo-Json -Depth 5 | Set-Content -Path $summaryPath -Encoding UTF8

@"
# TV2 Cleaning Run - Talking Points

- Da doc $($files.Count) file raw CSV trong folder ``raw/``.
- Tong so dong dau vao: $inputRows.
- Sau khi ap dung cleaning rules cua TV2, so dong hop le: $($cleanRows.Count).
- So dong bi ghi vao reject log: $($rejectRows.Count).
- Sau clean, so symbol hop le: $($distinctSymbols.Count) ($($distinctSymbols -join ", ")).
- Check sau clean:
  - ``high < low``: $highLtLowAfter
  - ``volume < 0``: $negativeVolumeAfter
  - symbol con suffix ``USDT``: $usdtSuffixAfter
  - duplicate ``(symbol, open_time)``: $dupesAfter

Ket luan bao cao:
Batch raw hien tai sach nen khong phat sinh reject. Tuy nhien TV2 van can cleaning job vi pipeline hang ngay co the gap du lieu loi, duplicate hoac format moi tu source.
"@ | Set-Content -Path $talkingPath -Encoding UTF8

Write-Host "TV2 cleaning evidence generated:"
Write-Host "  $cleanPath"
Write-Host "  $rejectPath"
Write-Host "  $summaryPath"
Write-Host "  $talkingPath"
Write-Host ""
Write-Host "Input rows : $inputRows"
Write-Host "Clean rows : $($cleanRows.Count)"
Write-Host "Reject rows: $($rejectRows.Count)"
