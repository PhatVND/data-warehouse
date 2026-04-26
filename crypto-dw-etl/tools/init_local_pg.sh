#!/usr/bin/env bash
# ============================================================================
# tools/init_local_pg.sh
# Owner: TV4 (Orchestration & Setup)
# Purpose:
#   Manage a project-local PostgreSQL cluster for Linux/WSL development.
#   Stores data under crypto-dw-etl/.local_pgdata/, logs under .local_pglog/.
#   Default port: 5432 (override with LOCAL_PG_PORT).
#
# Why a local cluster?
#   - No sudo / no system service interference.
#   - Lets the integration test (TV4 task 4.6) run end-to-end on a clean DB.
#   - Both .local_pgdata/ and .local_pglog/ are already in .gitignore.
#
# Sub-commands:
#   init    initdb + start + create role/db (calls sql/00_db_bootstrap.sql)
#   start   pg_ctl start
#   stop    pg_ctl stop
#   status  pg_ctl status
#   reset   stop + rm -rf .local_pgdata .local_pglog (DESTRUCTIVE, prompts)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PGDATA_DIR="${PROJECT_ROOT}/.local_pgdata"
PGLOG_DIR="${PROJECT_ROOT}/.local_pglog"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-5432}"
LOCAL_PG_HOST="127.0.0.1"

# Auto-detect Postgres binaries (pg_ctl, initdb, psql).
detect_pg_bin() {
    local candidates=(
        "/usr/lib/postgresql/15/bin"
        "/usr/lib/postgresql/14/bin"
        "/usr/lib/postgresql/13/bin"
        "/usr/lib/postgresql/16/bin"
    )
    for d in "${candidates[@]}"; do
        if [[ -x "${d}/pg_ctl" ]]; then
            echo "${d}"
            return 0
        fi
    done
    if command -v pg_ctl >/dev/null 2>&1; then
        dirname "$(command -v pg_ctl)"
        return 0
    fi
    echo "ERROR: Cannot find pg_ctl. Install postgresql server (sudo apt install postgresql)." >&2
    exit 1
}

PG_BIN="$(detect_pg_bin)"
PG_CTL="${PG_BIN}/pg_ctl"
INITDB="${PG_BIN}/initdb"
PSQL="${PG_BIN}/psql"

run_init() {
    if [[ -d "${PGDATA_DIR}" && -f "${PGDATA_DIR}/PG_VERSION" ]]; then
        echo "[init] Cluster already exists at ${PGDATA_DIR}. Skipping initdb."
    else
        mkdir -p "${PGDATA_DIR}" "${PGLOG_DIR}"
        echo "[init] Running initdb at ${PGDATA_DIR} ..."
        "${INITDB}" -D "${PGDATA_DIR}" -U "${USER}" --auth-local=trust --auth-host=trust -E UTF8 >/dev/null
        # Configure port and listen_addresses.
        {
            echo ""
            echo "# --- Local CryptoDW-ETL cluster overrides ---"
            echo "port = ${LOCAL_PG_PORT}"
            echo "listen_addresses = '${LOCAL_PG_HOST}'"
            echo "log_destination = 'stderr'"
            echo "logging_collector = on"
            echo "log_directory = '${PGLOG_DIR}'"
            echo "log_filename = 'postgresql-%Y-%m-%d.log'"
            echo "unix_socket_directories = '${PGDATA_DIR}'"
        } >> "${PGDATA_DIR}/postgresql.conf"
        # Note: trust auth is intentional for project-local dev clusters only.
        # Production / Windows install path uses md5 + per-user passwords.
    fi
    run_start
    echo "[init] Bootstrapping role + database via sql/00_db_bootstrap.sql ..."
    "${PSQL}" -h "${LOCAL_PG_HOST}" -p "${LOCAL_PG_PORT}" -U "${USER}" -d postgres \
        -v ON_ERROR_STOP=1 \
        -f "${PROJECT_ROOT}/sql/00_db_bootstrap.sql"
    echo "[init] Done. Connect:  PGPASSWORD=crypto_etl psql -h 127.0.0.1 -p ${LOCAL_PG_PORT} -U crypto_etl -d crypto_dw_etl"
}

run_start() {
    if "${PG_CTL}" -D "${PGDATA_DIR}" status >/dev/null 2>&1; then
        echo "[start] Cluster already running."
        return 0
    fi
    mkdir -p "${PGLOG_DIR}"
    echo "[start] Starting cluster on ${LOCAL_PG_HOST}:${LOCAL_PG_PORT} ..."
    "${PG_CTL}" -D "${PGDATA_DIR}" -l "${PGLOG_DIR}/server.log" -w start
}

run_stop() {
    if ! "${PG_CTL}" -D "${PGDATA_DIR}" status >/dev/null 2>&1; then
        echo "[stop] Cluster not running."
        return 0
    fi
    "${PG_CTL}" -D "${PGDATA_DIR}" -m fast stop
}

run_status() {
    "${PG_CTL}" -D "${PGDATA_DIR}" status || true
}

run_reset() {
    echo "[reset] This will permanently delete ${PGDATA_DIR} and ${PGLOG_DIR}."
    read -r -p "[reset] Type 'yes' to confirm: " ans
    if [[ "${ans}" != "yes" ]]; then
        echo "[reset] Aborted."
        exit 1
    fi
    run_stop || true
    rm -rf "${PGDATA_DIR}" "${PGLOG_DIR}"
    echo "[reset] Done."
}

cmd="${1:-}"
case "${cmd}" in
    init)   run_init ;;
    start)  run_start ;;
    stop)   run_stop ;;
    status) run_status ;;
    reset)  run_reset ;;
    *)
        cat <<EOF
Usage: bash tools/init_local_pg.sh <init|start|stop|status|reset>

  init    Run initdb (if needed), start the cluster, then bootstrap role+DB.
  start   Start the cluster.
  stop    Stop the cluster.
  status  Show cluster status.
  reset   DESTROY the cluster (rm -rf .local_pgdata + .local_pglog).

Env:
  LOCAL_PG_PORT  port to listen on (default 5432)
EOF
        exit 1
        ;;
esac
