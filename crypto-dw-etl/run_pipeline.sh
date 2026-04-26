#!/usr/bin/env bash
# ============================================================================
# run_pipeline.sh — TV4 orchestration (Linux/WSL mirror of run_pipeline.bat)
#
# Sequence:
#   STEP 1  Python ingestion (scripts/1_fetch_binance.py) → raw/*.csv
#   STEP 2  Load staging.ohlcv_raw
#             Phase A (default): TRUNCATE + \copy raw/*.csv via psql
#             Phase B (USE_PENTAHO_CLEAN=1): kitchen.sh 01_clean.kjb (TV2)
#   STEP 3  Build staging.fact_prep
#             SQL path (default): psql -f sql/02_transform_fallback.sql
#             Pentaho path (USE_PENTAHO=1): kitchen.sh 02_transform.kjb (TV3)
#   STEP 4  psql -f sql/03_load_gold.sql        (TRUNCATE + INSERT gold)
#   STEP 5  psql -f sql/04_olap_views.sql        (CREATE OR REPLACE VIEW)
#
# Logging:
#   All stdout+stderr from every step is tee-d to logs/YYYY-MM-DD.log.
#
# Exit code: 0 if all steps succeed, otherwise the failing step's code.
# ============================================================================

set -u
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

# ---------- Load .env (POSIX-friendly) ----------
if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
elif [[ -f .env.example ]]; then
    echo "WARN: .env not found, falling back to .env.example. Copy and edit .env." >&2
    set -a
    # shellcheck disable=SC1091
    source .env.example
    set +a
else
    echo "ERROR: neither .env nor .env.example present." >&2
    exit 1
fi

PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-5432}"
PG_DATABASE="${PG_DATABASE:-crypto_dw_etl}"
PG_USER="${PG_USER:-crypto_etl}"
PG_PASSWORD="${PG_PASSWORD:-crypto_etl}"
USE_PENTAHO="${USE_PENTAHO:-0}"
USE_PENTAHO_CLEAN="${USE_PENTAHO_CLEAN:-0}"
PENTAHO_HOME="${PENTAHO_HOME:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

export PGHOST="${PG_HOST}"
export PGPORT="${PG_PORT}"
export PGDATABASE="${PG_DATABASE}"
export PGUSER="${PG_USER}"
export PGPASSWORD="${PG_PASSWORD}"

# ---------- Logging ----------
TODAY="$(date +%F)"
mkdir -p logs raw
LOG="logs/${TODAY}.log"

log() {
    # tee-friendly log line that always appears in both stdout and the log file.
    printf '%s\n' "$*" | tee -a "${LOG}"
}

step_header() {
    log ""
    log "==== STEP $1: $2 ===="
}

git_rev() {
    if command -v git >/dev/null 2>&1 && git -C "${PROJECT_ROOT}" rev-parse --short HEAD >/dev/null 2>&1; then
        git -C "${PROJECT_ROOT}" rev-parse --short HEAD
    else
        echo "n/a"
    fi
}

START_TS=$(date +%s)
{
    log "=========================================================="
    log "  CryptoDW-ETL pipeline run — $(date '+%Y-%m-%d %H:%M:%S %Z')"
    log "  host=${PG_HOST} port=${PG_PORT} db=${PG_DATABASE} user=${PG_USER}"
    log "  USE_PENTAHO=${USE_PENTAHO}  USE_PENTAHO_CLEAN=${USE_PENTAHO_CLEAN}"
    log "  git=$(git_rev)"
    log "=========================================================="
}

# ---------- Helpers ----------
PSQL_OPTS=(-h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -v ON_ERROR_STOP=1)

run_psql_file() {
    psql "${PSQL_OPTS[@]}" -f "$1" 2>&1 | tee -a "${LOG}"
    return "${PIPESTATUS[0]}"
}

run_psql_cmd() {
    psql "${PSQL_OPTS[@]}" -c "$1" 2>&1 | tee -a "${LOG}"
    return "${PIPESTATUS[0]}"
}

run_kitchen() {
    if [[ -z "${PENTAHO_HOME}" ]]; then
        log "ERROR: PENTAHO_HOME is empty but Pentaho path requested."
        return 2
    fi
    local kjb_file="$1"
    "${PENTAHO_HOME}/kitchen.sh" \
        -file="${kjb_file}" \
        -param:PG_HOST="${PG_HOST}" \
        -param:PG_PORT="${PG_PORT}" \
        -param:PG_DATABASE="${PG_DATABASE}" \
        -param:PG_USER="${PG_USER}" \
        -param:PG_PASSWORD="${PG_PASSWORD}" \
        2>&1 | tee -a "${LOG}"
    return "${PIPESTATUS[0]}"
}

fail() {
    local step=$1
    local rc=$2
    log ""
    log "STEP ${step} FAILED (rc=${rc}). See ${LOG} for details."
    log "PIPELINE FAILURE — duration $(( $(date +%s) - START_TS ))s"
    exit "${rc}"
}

# ---------- STEP 1: Python ingestion ----------
step_header 1 "Python ingestion (Binance → raw/*.csv)"
"${PYTHON_BIN}" scripts/1_fetch_binance.py 2>&1 | tee -a "${LOG}"
rc=${PIPESTATUS[0]}
[[ ${rc} -ne 0 ]] && fail 1 "${rc}"

# ---------- STEP 2: Load staging.ohlcv_raw ----------
step_header 2 "Load staging.ohlcv_raw (USE_PENTAHO_CLEAN=${USE_PENTAHO_CLEAN})"
if [[ "${USE_PENTAHO_CLEAN}" == "1" ]]; then
    run_kitchen "${PROJECT_ROOT}/etl/pdi/01_clean.kjb"
    rc=$?
    [[ ${rc} -ne 0 ]] && fail 2 "${rc}"
else
    run_psql_cmd "TRUNCATE TABLE staging.ohlcv_raw;" || fail 2 "$?"
    shopt -s nullglob
    raw_files=(raw/*_raw.csv)
    shopt -u nullglob
    if [[ ${#raw_files[@]} -eq 0 ]]; then
        log "ERROR: no raw/*_raw.csv files found after STEP 1."
        fail 2 1
    fi
    for f in "${raw_files[@]}"; do
        log "  \\copy ${f}"
        psql "${PSQL_OPTS[@]}" \
            -c "\copy staging.ohlcv_raw FROM '${f}' WITH (FORMAT csv, HEADER true)" \
            2>&1 | tee -a "${LOG}"
        rc=${PIPESTATUS[0]}
        [[ ${rc} -ne 0 ]] && fail 2 "${rc}"
    done
fi

# ---------- STEP 3: Build staging.fact_prep ----------
step_header 3 "Build staging.fact_prep (USE_PENTAHO=${USE_PENTAHO})"
if [[ "${USE_PENTAHO}" == "1" ]]; then
    run_kitchen "${PROJECT_ROOT}/etl/pdi/02_transform.kjb"
    rc=$?
    [[ ${rc} -ne 0 ]] && fail 3 "${rc}"
else
    run_psql_file sql/02_transform_fallback.sql
    rc=$?
    [[ ${rc} -ne 0 ]] && fail 3 "${rc}"
fi

# ---------- STEP 4: Load gold.fact_market_daily ----------
step_header 4 "Load gold.fact_market_daily"
run_psql_file sql/03_load_gold.sql
rc=$?
[[ ${rc} -ne 0 ]] && fail 4 "${rc}"

# ---------- STEP 5: Refresh OLAP views ----------
step_header 5 "Refresh OLAP views"
run_psql_file sql/04_olap_views.sql
rc=$?
[[ ${rc} -ne 0 ]] && fail 5 "${rc}"

# ---------- Final summary ----------
DURATION=$(( $(date +%s) - START_TS ))
log ""
log "=========================================================="
log "  PIPELINE SUCCESS — duration ${DURATION}s"
log "=========================================================="
exit 0
