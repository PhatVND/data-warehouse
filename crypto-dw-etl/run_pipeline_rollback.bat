@echo off
REM ============================================================================
REM run_pipeline_rollback.bat — TV4 rollback (Windows production target)
REM
REM Purpose:
REM   Bring the warehouse back to an empty state so a clean re-run of
REM   run_pipeline.bat produces deterministic Full Load output.
REM
REM Behavior:
REM   1. TRUNCATE gold.fact_market_daily
REM   2. TRUNCATE staging.fact_prep
REM   3. TRUNCATE staging.ohlcv_raw
REM   4. TRUNCATE staging.reject_log RESTART IDENTITY
REM   5. (optional) DEL raw\*_raw.csv         [skipped if --keep-raw is given]
REM
REM Usage:
REM   run_pipeline_rollback.bat              # truncate + delete raw csvs
REM   run_pipeline_rollback.bat --keep-raw   # truncate but keep raw csvs
REM ============================================================================

setlocal EnableDelayedExpansion
pushd "%~dp0" >nul

set "KEEP_RAW=0"
if /I "%~1"=="--keep-raw" set "KEEP_RAW=1"

REM ---------- Load .env ----------
set "ENVFILE=.env"
if not exist "%ENVFILE%" set "ENVFILE=.env.example"
if exist "%ENVFILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in (`type "%ENVFILE%" ^| findstr /R /V "^[ ]*#" ^| findstr /R /V "^[ ]*$"`) do (
        set "%%A=%%B"
    )
)

if not defined PG_HOST     set "PG_HOST=127.0.0.1"
if not defined PG_PORT     set "PG_PORT=5432"
if not defined PG_DATABASE set "PG_DATABASE=crypto_dw_etl"
if not defined PG_USER     set "PG_USER=crypto_etl"
if not defined PG_PASSWORD set "PG_PASSWORD=crypto_etl"

set "PGHOST=%PG_HOST%"
set "PGPORT=%PG_PORT%"
set "PGDATABASE=%PG_DATABASE%"
set "PGUSER=%PG_USER%"
set "PGPASSWORD=%PG_PASSWORD%"

if not exist logs mkdir logs
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%t"
set "LOG=logs\%TODAY%.log"

call :LOG ""
call :LOG "=========================================================="
call :LOG "  CryptoDW-ETL ROLLBACK"
call :LOG "  host=%PG_HOST% db=%PG_DATABASE% user=%PG_USER%  keep_raw=%KEEP_RAW%"
call :LOG "=========================================================="

psql -v ON_ERROR_STOP=1 -c "TRUNCATE gold.fact_market_daily; TRUNCATE staging.fact_prep; TRUNCATE staging.ohlcv_raw; TRUNCATE staging.reject_log RESTART IDENTITY;" 1>>"%LOG%" 2>&1
if errorlevel 1 (
    call :LOG "ROLLBACK FAILED"
    popd
    endlocal
    exit /b 1
)

if "%KEEP_RAW%"=="0" (
    if exist raw\*_raw.csv (
        call :LOG "Deleting raw\*_raw.csv ..."
        del /Q raw\*_raw.csv
    )
)

REM Print final state
psql -At -c "SELECT 'gold.fact_market_daily=' || COUNT(*) FROM gold.fact_market_daily UNION ALL SELECT 'staging.fact_prep=' || COUNT(*) FROM staging.fact_prep UNION ALL SELECT 'staging.ohlcv_raw=' || COUNT(*) FROM staging.ohlcv_raw UNION ALL SELECT 'staging.reject_log=' || COUNT(*) FROM staging.reject_log;" 1>>"%LOG%" 2>&1

call :LOG ""
call :LOG "ROLLBACK SUCCESS — re-run with: run_pipeline.bat"
popd
endlocal
exit /b 0

:LOG
echo %~1
echo %~1 >> "%LOG%"
goto :eof
