import csv
import logging
import os
import time

import requests


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_FILE = os.path.join(BASE_DIR, "seed", "dim_coin.csv")
RAW_DIR = os.path.join(BASE_DIR, "raw")
BINANCE_URL = "https://api.binance.com/api/v3/klines"
LIMIT = 730
INTERVAL = "1d"
BASE_DELAY_SECONDS = 2
RATE_LIMIT_DELAY_SECONDS = 1

os.makedirs(RAW_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_coins_from_seed():
    """Read the configured coin list from seed data."""
    coins = []
    try:
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("symbol", "").strip().upper()
                if symbol:
                    coins.append(symbol)
        logging.info("Da load %s ma coin tu seed.", len(coins))
        return coins
    except Exception as e:
        logging.error("Loi khi doc file seed: %s", e)
        return []


def calculate_backoff(attempt):
    """Use bounded exponential backoff for transient Binance/API issues."""
    return min(BASE_DELAY_SECONDS * (2 ** (attempt - 1)), 60)


def fetch_binance_data(symbol, max_retries=3):
    """Fetch daily Binance klines with retry and rate-limit handling."""
    pair = f"{symbol}USDT"
    params = {"symbol": pair, "interval": INTERVAL, "limit": LIMIT}

    for attempt in range(1, max_retries + 1):
        try:
            logging.info("Dang fetch data cho %s (%s/%s)...", symbol, attempt, max_retries)
            response = requests.get(BINANCE_URL, params=params, timeout=10)

            if response.status_code in (418, 429):
                wait_seconds = calculate_backoff(attempt)
                logging.warning(
                    "Binance rate limit cho %s (HTTP %s). Cho %ss roi thu lai.",
                    symbol,
                    response.status_code,
                    wait_seconds,
                )
                if attempt < max_retries:
                    time.sleep(wait_seconds)
                    continue
                logging.error("Vuot qua so lan retry do rate limit cho %s.", symbol)
                return []

            if 500 <= response.status_code < 600:
                wait_seconds = calculate_backoff(attempt)
                logging.warning(
                    "Binance tam thoi loi server cho %s (HTTP %s). Cho %ss roi thu lai.",
                    symbol,
                    response.status_code,
                    wait_seconds,
                )
                if attempt < max_retries:
                    time.sleep(wait_seconds)
                    continue

            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                logging.error("Response JSON khong dung dinh dang list cho %s.", symbol)
                return []

            logging.info("Fetch thanh cong %s ban ghi cho %s.", len(data), symbol)
            return data
        except ValueError as e:
            logging.error("Loi parse JSON khi goi API cho %s: %s", symbol, e)
            return []
        except requests.exceptions.Timeout as e:
            logging.error("Timeout khi goi API cho %s: %s", symbol, e)
            if attempt < max_retries:
                wait_seconds = calculate_backoff(attempt)
                logging.info("Thu lai %s sau %ss.", symbol, wait_seconds)
                time.sleep(wait_seconds)
            else:
                logging.error("Vuot qua so lan retry cho %s. Bo qua.", symbol)
                return []
        except requests.exceptions.RequestException as e:
            logging.error("Loi network khi goi API cho %s: %s", symbol, e)
            if attempt < max_retries:
                wait_seconds = calculate_backoff(attempt)
                logging.info("Thu lai %s sau %ss.", symbol, wait_seconds)
                time.sleep(wait_seconds)
            else:
                logging.error("Vuot qua so lan retry cho %s. Bo qua.", symbol)
                return []

    return []


def save_to_csv(symbol, data):
    """Write Binance kline rows to a raw CSV file for downstream ETL."""
    headers = [
        "symbol",
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore_field",
    ]
    filename = os.path.join(RAW_DIR, f"{symbol}_raw.csv")

    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in data:
                writer.writerow([symbol] + row)
        logging.info("Da luu file %s (%s lines).", filename, len(data))
    except Exception as e:
        logging.error("Loi luu file CSV cho %s: %s", symbol, e)


def main():
    logging.info("===== BAT DAU QUA TRINH INGESTION TU BINANCE =====")
    coins = get_coins_from_seed()

    if not coins:
        logging.error("Khong co cau hinh coin. Huy thao tac.")
        return

    for symbol in coins:
        raw_data = fetch_binance_data(symbol)
        if raw_data:
            save_to_csv(symbol, raw_data)
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

    logging.info("===== HOAN TAT FETCH DATA =====")


if __name__ == "__main__":
    main()
