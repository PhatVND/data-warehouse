@echo off
REM ============================================================================
REM run_pipeline.bat — TV4 orchestration (Windows production target)
REM
REM Sequence:
REM   STEP 1  Python ingestion (scripts\1_fetch_binance.py) -> raw\*.csv
REM   STEP 2  Load staging.ohlcv_raw
REM             Phase A (default): TRUNCATE + \copy raw\*.csv via psql
REM             Phase B (USE_PENTAHO_CLEAN=1): Kitchen 01_clean.kjb (TV2)
REM   STEP 3  Build staging.fact_prep
REM             SQL path (default): psql -f sql\02_transform_fallback.sql
REM             Pentaho path (USE_PENTAHO=1): Kitchen 02_transform.kjb (TV3)
REM   STEP 4  psql -f sql\03_load_gold.sql        (TRUNCATE + INSERT gold)
REM   STEP 5  psql -f sql\04_olap_views.sql        (CREATE OR REPLACE VIEW)
REM
REM Logging:
REM   All stdout+stderr from every step is appended to logs\YYYY-MM-DD.log.
REM
REM Exit code: 0 if all steps succeed, otherwise the failing step's code.
REM ============================================================================

setlocal EnableDelayedExpansion

REM ---------- Resolve project root ----------
pushd "%~dp0" >nul

REM ---------- Load .env (very small parser; ignores blank lines and comments) ----------
set "ENVFILE=.env"
if not exist "%ENVFILE%" set "ENVFILE=.env.example"
if not exist "%ENVFILE%" (
    echo ERROR: neither .env nor .env.example present.
    popd
    exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%A in (`type "%ENVFILE%" ^| findstr /R /V "^[ ]*#" ^| findstr /R /V "^[ ]*$"`) do (
    set "%%A=%%B"
)

REM ---------- Defaults ----------
if not defined PG_HOST           set "PG_HOST=127.0.0.1"
if not defined PG_PORT           set "PG_PORT=5432"
if not defined PG_DATABASE       set "PG_DATABASE=crypto_dw_etl"
if not defined PG_USER           set "PG_USER=crypto_etl"
if not defined PG_PASSWORD       set "PG_PASSWORD=crypto_etl"
if not defined USE_PENTAHO       set "USE_PENTAHO=0"
if not defined USE_PENTAHO_CLEAN set "USE_PENTAHO_CLEAN=0"
if not defined PYTHON_BIN        set "PYTHON_BIN=python"

REM ---------- libpq env variables ----------
set "PGHOST=%PG_HOST%"
set "PGPORT=%PG_PORT%"
set "PGDATABASE=%PG_DATABASE%"
set "PGUSER=%PG_USER%"
set "PGPASSWORD=%PG_PASSWORD%"

REM ---------- Logging setup ----------
if not exist logs mkdir logs
if not exist raw  mkdir raw
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%t"
set "LOG=logs\%TODAY%.log"

call :LOG "=========================================================="
call :LOG "  CryptoDW-ETL pipeline run"
call :LOG "  host=%PG_HOST% port=%PG_PORT% db=%PG_DATABASE% user=%PG_USER%"
call :LOG "  USE_PENTAHO=%USE_PENTAHO%  USE_PENTAHO_CLEAN=%USE_PENTAHO_CLEAN%"
call :LOG "=========================================================="

set "T0=%TIME%"

REM ---------- STEP 1: Python ingestion ----------
call :STEP 1 "Python ingestion (Binance -> raw\*.csv)"
"%PYTHON_BIN%" scripts\1_fetch_binance.py 1>>"%LOG%" 2>&1
if errorlevel 1 (set "RC=%errorlevel%" & call :FAIL 1 !RC!)

REM ---------- STEP 2: Load staging.ohlcv_raw ----------
call :STEP 2 "Load staging.ohlcv_raw (USE_PENTAHO_CLEAN=%USE_PENTAHO_CLEAN%)"
if "%USE_PENTAHO_CLEAN%"=="1" (
    if not defined PENTAHO_HOME (call :LOG "ERROR: PENTAHO_HOME empty" & call :FAIL 2 2)
    call "%PENTAHO_HOME%\Kitchen.bat" -file="%CD%\etl\pdi\01_clean.kjb" -param:PG_HOST=%PG_HOST% -param:PG_PORT=%PG_PORT% -param:PG_DATABASE=%PG_DATABASE% -param:PG_USER=%PG_USER% -param:PG_PASSWORD=%PG_PASSWORD% 1>>"%LOG%" 2>&1
    if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 2 !RC!)
) else (
    psql -v ON_ERROR_STOP=1 -c "TRUNCATE TABLE staging.ohlcv_raw;" 1>>"%LOG%" 2>&1
    if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 2 !RC!)
    for %%F in (raw\*_raw.csv) do (
        call :LOG "  \copy %%F"
        psql -v ON_ERROR_STOP=1 -c "\copy staging.ohlcv_raw FROM '%%F' WITH (FORMAT csv, HEADER true)" 1>>"%LOG%" 2>&1
        if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 2 !RC!)
    )
)

REM ---------- STEP 3: Build staging.fact_prep ----------
call :STEP 3 "Build staging.fact_prep (USE_PENTAHO=%USE_PENTAHO%)"
if "%USE_PENTAHO%"=="1" (
    if not defined PENTAHO_HOME (call :LOG "ERROR: PENTAHO_HOME empty" & call :FAIL 3 2)
    call "%PENTAHO_HOME%\Kitchen.bat" -file="%CD%\etl\pdi\02_transform.kjb" -param:PG_HOST=%PG_HOST% -param:PG_PORT=%PG_PORT% -param:PG_DATABASE=%PG_DATABASE% -param:PG_USER=%PG_USER% -param:PG_PASSWORD=%PG_PASSWORD% 1>>"%LOG%" 2>&1
    if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 3 !RC!)
) else (
    psql -v ON_ERROR_STOP=1 -f sql\02_transform_fallback.sql 1>>"%LOG%" 2>&1
    if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 3 !RC!)
)

REM ---------- STEP 4: Load gold.fact_market_daily ----------
call :STEP 4 "Load gold.fact_market_daily"
psql -v ON_ERROR_STOP=1 -f sql\03_load_gold.sql 1>>"%LOG%" 2>&1
if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 4 !RC!)

REM ---------- STEP 5: Refresh OLAP views ----------
call :STEP 5 "Refresh OLAP views"
psql -v ON_ERROR_STOP=1 -f sql\04_olap_views.sql 1>>"%LOG%" 2>&1
if errorlevel 1 (set "RC=!errorlevel!" & call :FAIL 5 !RC!)

call :LOG ""
call :LOG "=========================================================="
call :LOG "  PIPELINE SUCCESS"
call :LOG "=========================================================="
popd
endlocal
exit /b 0

REM ============================================================================
REM Helpers
REM ============================================================================
:LOG
echo %~1
echo %~1 >> "%LOG%"
goto :eof

:STEP
call :LOG ""
call :LOG "==== STEP %~1: %~2 ===="
goto :eof

:FAIL
call :LOG ""
call :LOG "STEP %~1 FAILED (rc=%~2). See %LOG% for details."
call :LOG "PIPELINE FAILURE"
popd
endlocal
exit /b %~2
