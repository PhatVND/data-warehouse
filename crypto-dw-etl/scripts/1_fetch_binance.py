import requests
import time
import csv
import os
import logging


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_FILE = os.path.join(BASE_DIR, "seed", "dim_coin.csv")
RAW_DIR = os.path.join(BASE_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BINANCE_URL = "https://api.binance.com/api/v3/klines"
LIMIT = 730
INTERVAL = "1d"


def get_coins_from_seed():
    """Read seed data to get configured coin symbols."""
    coins = []
    try:
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                coins.append(row["symbol"])
        logging.info("Da load %s ma coin tu seed.", len(coins))
        return coins
    except Exception as e:
        logging.error("Loi khi doc file seed: %s", e)
        return []


def fetch_binance_data(symbol, max_retries=3):
    """Fetch daily Binance klines with simple retry handling."""
    pair = f"{symbol}USDT"
    params = {"symbol": pair, "interval": INTERVAL, "limit": LIMIT}

    for attempt in range(1, max_retries + 1):
        try:
            logging.info("Dang fetch data cho %s (lan thu %s/%s)...", symbol, attempt, max_retries)
            response = requests.get(BINANCE_URL, params=params, timeout=10)

            if response.status_code == 429:
                logging.warning("Bi rate limit cho %s. Cho 60s roi thu lai...", symbol)
                time.sleep(60)
                continue

            response.raise_for_status()
            data = response.json()
            logging.info("Fetch thanh cong %s ban ghi cho %s.", len(data), symbol)
            return data
        except requests.exceptions.RequestException as e:
            logging.error("Loi network khi goi API cho %s: %s", symbol, e)
            if attempt < max_retries:
                time.sleep(5)
            else:
                logging.error("Vuot qua so lan retry cho %s. Bo qua.", symbol)
                return []

    return []


def save_to_csv(symbol, data):
    """Write raw Binance data to CSV for downstream ETL."""
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

            count = 0
            for row in data:
                writer.writerow([symbol] + row)
                count += 1

        logging.info("Da luu file %s (%s lines).", filename, count)
    except Exception as e:
        logging.error("Loi luu file CSV cho %s: %s", symbol, e)


def main():
    logging.info("===== BAT DAU QUA TRINH INGESTION TU BINANCE =====")
    coins = get_coins_from_seed()

    if not coins:
        logging.error("Khong co configs. Huy thao tac.")
        return

    for symbol in coins:
        raw_data = fetch_binance_data(symbol)
        if raw_data:
            save_to_csv(symbol, raw_data)
        time.sleep(1)

    logging.info("===== HOAN TAT FETCH DATA =====")


if __name__ == "__main__":
    main()
