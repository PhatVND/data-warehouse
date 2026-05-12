"""
Streamlit dashboard CSV-mode wrapper for streamlit_crypto.py.

Reads from bi/data/*.csv (no PostgreSQL needed), then monkey-patches the
load_fact/load_weekly/load_anomalies functions in the original module and
calls main() to render the same 5 tabs.

Run:
    streamlit run streamlit_crypto_csv.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "bi" / "data"


@st.cache_data(show_spinner="Loading fact + dimensions from CSV ...")
def _load_fact_csv() -> pd.DataFrame:
    fact = pd.read_csv(DATA / "fact_market_daily.csv")
    coin = pd.read_csv(DATA / "dim_coin.csv")
    cat = pd.read_csv(DATA / "dim_category.csv")
    date = pd.read_csv(DATA / "dim_date.csv", parse_dates=["full_date"])

    df = (fact
          .merge(coin, on="coin_id", how="left")
          .merge(cat, on="category_id", how="left")
          .merge(date, on="date_id", how="left"))

    df["is_anomaly"] = df["is_anomaly"].astype(str).str.lower().isin(["true", "1"])
    df["week"] = df["full_date"].dt.isocalendar().week.astype(int)
    return df


@st.cache_data
def _load_weekly_csv() -> pd.DataFrame:
    df = _load_fact_csv().copy()
    df["week_start_date"] = df["full_date"] - pd.to_timedelta(df["full_date"].dt.dayofweek, unit="d")
    df["week_end_date"] = df["week_start_date"] + pd.Timedelta(days=6)
    weekly = (df.groupby(["year", "week", "week_start_date", "week_end_date", "category_name"], as_index=False)
                ["return_pct"].mean()
                .rename(columns={"return_pct": "avg_return_pct"}))
    return weekly


@st.cache_data
def _load_anomalies_csv() -> pd.DataFrame:
    df = _load_fact_csv()
    a = df[df["is_anomaly"]].copy()
    a["abs_z_score_close"] = a["z_score_close"].abs()
    return a.sort_values("abs_z_score_close", ascending=False)


# Monkey-patch the original module BEFORE main() runs.
import streamlit_crypto as base
base.load_fact = _load_fact_csv
base.load_weekly = _load_weekly_csv
base.load_anomalies = _load_anomalies_csv


if __name__ == "__main__" or True:
    base.main()
