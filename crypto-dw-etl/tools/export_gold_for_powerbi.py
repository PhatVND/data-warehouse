"""
Export Star Schema (Gold layer) ra 4 file CSV để Power BI import trực tiếp.
Không cần PostgreSQL — đọc thẳng từ raw/*_raw.csv.

Output:
    crypto-dw-etl/bi/data/fact_market_daily.csv   (~7,300 rows)
    crypto-dw-etl/bi/data/dim_coin.csv
    crypto-dw-etl/bi/data/dim_date.csv
    crypto-dw-etl/bi/data/dim_category.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RAW = PROJECT / "raw"
OUT = PROJECT / "bi" / "data"
OUT.mkdir(parents=True, exist_ok=True)

COIN_META = [
    (1, "BTC",  "Bitcoin",  2009, 1),
    (2, "ETH",  "Ethereum", 2015, 1),
    (3, "BNB",  "BNB",      2017, 1),
    (4, "SOL",  "Solana",   2020, 1),
    (5, "XRP",  "XRP",      2012, 4),
    (6, "ADA",  "Cardano",  2017, 1),
    (7, "DOGE", "Dogecoin", 2013, 3),
    (8, "TRX",  "TRON",     2017, 1),
    (9, "DOT",  "Polkadot", 2020, 1),
    (10,"MATIC","Polygon",  2017, 2),
]
CATEGORIES = [
    (1, "L1",      "Low"),
    (2, "L2",      "Mid"),
    (3, "Meme",    "High"),
    (4, "Payment", "Low"),
]

# ---------- DIMENSIONS ----------
dim_coin = pd.DataFrame(COIN_META,
    columns=["coin_id", "symbol", "full_name", "launch_year", "category_id"])
dim_category = pd.DataFrame(CATEGORIES,
    columns=["category_id", "category_name", "risk_level"])

# ---------- FACT (build by reading raw CSVs) ----------
def build_fact_for(symbol: str, coin_id: int) -> pd.DataFrame:
    df = pd.read_csv(RAW / f"{symbol}_raw.csv")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.normalize()
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)

    df["coin_id"]      = coin_id
    df["date_id"]      = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["volume_base"]  = df["volume"]
    df["volume_usd"]   = df["close"] * df["volume"]
    df["return_pct"]   = (df["close"] - df["open"]) / df["open"] * 100
    df["log_return"]   = np.log(df["close"] / df["close"].shift(1))
    df["volatility"]   = df["high"] - df["low"]
    df["average_price"]= (df["high"] + df["low"]) / 2

    # rolling Z-Score 30d
    mu = df["close"].rolling(30, min_periods=10).mean()
    sd = df["close"].rolling(30, min_periods=10).std()
    df["z_score_close"] = (df["close"] - mu) / sd
    df["is_anomaly"]    = (df["z_score_close"].abs() > 2).fillna(False)

    # regime label by 30d return
    r30 = df["close"].pct_change(30) * 100
    df["regime_label"] = np.where(r30 > 10, "Bull",
                          np.where(r30 < -10, "Bear", "Sideways"))

    return df[[
        "date_id", "coin_id", "open", "high", "low", "close",
        "volume_base", "volume_usd", "return_pct", "log_return",
        "volatility", "average_price", "z_score_close",
        "is_anomaly", "regime_label",
    ]]

facts = pd.concat(
    [build_fact_for(s, cid) for cid, s, *_ in COIN_META],
    ignore_index=True,
)

# volume_rank + market_dominance: chỉ tính theo các ngày KHÔNG NaN volume
g = facts.groupby("date_id")
facts["volume_rank"] = g["volume_usd"].rank(method="dense", ascending=False).astype(int)
day_total = g["volume_usd"].transform("sum")
facts["market_dominance_pct"] = (facts["volume_usd"] / day_total * 100).round(3)

# ---------- DIM_DATE (calendar covering all dates in fact) ----------
all_dates = pd.date_range(
    facts["date_id"].astype(str).min(),
    facts["date_id"].astype(str).max(),
    freq="D",
)
dim_date = pd.DataFrame({"full_date": all_dates})
dim_date["date_id"]      = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
dim_date["year"]         = dim_date["full_date"].dt.year
dim_date["quarter"]      = dim_date["full_date"].dt.quarter
dim_date["month"]        = dim_date["full_date"].dt.month
dim_date["month_name"]   = dim_date["full_date"].dt.strftime("%b")
dim_date["day_of_month"] = dim_date["full_date"].dt.day
dim_date["day_name"]     = dim_date["full_date"].dt.strftime("%A")
dim_date["is_weekend"]   = dim_date["full_date"].dt.weekday >= 5
dim_date = dim_date[[
    "date_id", "full_date", "year", "quarter", "month",
    "month_name", "day_of_month", "day_name", "is_weekend",
]]

# ---------- WRITE ----------
facts.to_csv(OUT / "fact_market_daily.csv", index=False)
dim_coin.to_csv(OUT / "dim_coin.csv", index=False)
dim_category.to_csv(OUT / "dim_category.csv", index=False)
dim_date.to_csv(OUT / "dim_date.csv", index=False)

print(f"Output dir: {OUT}")
print(f"  fact_market_daily.csv  rows={len(facts):,}")
print(f"  dim_coin.csv           rows={len(dim_coin)}")
print(f"  dim_category.csv       rows={len(dim_category)}")
print(f"  dim_date.csv           rows={len(dim_date):,}")
print("\nNext: open Power BI Desktop -> Get Data -> Text/CSV -> chon 4 file nay.")
