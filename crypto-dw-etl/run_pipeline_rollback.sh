#!/usr/bin/env bash
# ============================================================================
# run_pipeline_rollback.sh — TV4 rollback (Linux/WSL mirror of .bat)
#
# Purpose:
#   Bring the warehouse back to an empty state so a clean re-run of
#   run_pipeline.sh produces deterministic Full Load output.
#
# Behavior (in order):
#   1. TRUNCATE gold.fact_market_daily
#   2. TRUNCATE staging.fact_prep
#   3. TRUNCATE staging.ohlcv_raw
#   4. TRUNCATE staging.reject_log RESTART IDENTITY
#   5. (optional) Delete raw/*.csv     [skipped if --keep-raw is given]
#
# OLAP views (CREATE OR REPLACE) and dimension tables are left untouched.
#
# Usage:
#   bash run_pipeline_rollback.sh           # truncate + delete raw csvs
#   bash run_pipeline_rollback.sh --keep-raw  # truncate but keep raw csvs
# ============================================================================

set -u
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

KEEP_RAW=0
for arg in "$@"; do
    case "${arg}" in
        --keep-raw) KEEP_RAW=1 ;;
        -h|--help)
            sed -n '2,25p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown arg: ${arg}" >&2
            exit 1
            ;;
    esac
done

# Load .env
if [[ -f .env ]]; then
    set -a; source .env; set +a
elif [[ -f .env.example ]]; then
    set -a; source .env.example; set +a
fi

PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-5432}"
PG_DATABASE="${PG_DATABASE:-crypto_dw_etl}"
PG_USER="${PG_USER:-crypto_etl}"
PG_PASSWORD="${PG_PASSWORD:-crypto_etl}"

export PGHOST="${PG_HOST}" PGPORT="${PG_PORT}" PGDATABASE="${PG_DATABASE}" \
       PGUSER="${PG_USER}" PGPASSWORD="${PG_PASSWORD}"

mkdir -p logs
LOG="logs/$(date +%F).log"

log() { printf '%s\n' "$*" | tee -a "${LOG}"; }

log ""
log "=========================================================="
log "  CryptoDW-ETL ROLLBACK — $(date '+%Y-%m-%d %H:%M:%S %Z')"
log "  host=${PG_HOST} db=${PG_DATABASE} user=${PG_USER}  keep_raw=${KEEP_RAW}"
log "=========================================================="

psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" \
    -v ON_ERROR_STOP=1 \
    -c "TRUNCATE gold.fact_market_daily;
        TRUNCATE staging.fact_prep;
        TRUNCATE staging.ohlcv_raw;
        TRUNCATE staging.reject_log RESTART IDENTITY;" \
    2>&1 | tee -a "${LOG}"
rc=${PIPESTATUS[0]}
if [[ ${rc} -ne 0 ]]; then
    log "ROLLBACK FAILED (rc=${rc})"
    exit "${rc}"
fi

if [[ ${KEEP_RAW} -eq 0 ]]; then
    shopt -s nullglob
    csvs=(raw/*_raw.csv)
    shopt -u nullglob
    if [[ ${#csvs[@]} -gt 0 ]]; then
        log "Deleting ${#csvs[@]} raw csv(s)..."
        rm -f "${csvs[@]}"
    fi
fi

# Final state
psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -At \
    -c "SELECT 'gold.fact_market_daily=' || COUNT(*) FROM gold.fact_market_daily
        UNION ALL SELECT 'staging.fact_prep=' || COUNT(*) FROM staging.fact_prep
        UNION ALL SELECT 'staging.ohlcv_raw=' || COUNT(*) FROM staging.ohlcv_raw
        UNION ALL SELECT 'staging.reject_log=' || COUNT(*) FROM staging.reject_log;" \
    | tee -a "${LOG}"

log ""
log "ROLLBACK SUCCESS — re-run with: bash run_pipeline.sh"
exit 0
