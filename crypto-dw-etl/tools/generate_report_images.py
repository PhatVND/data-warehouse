"""
Generate all charts/images needed by the LaTeX report from raw Binance CSVs.

Reads: crypto-dw-etl/raw/<SYMBOL>_raw.csv  (10 coins)
Writes:
    _Data_Warehouse__Báo_cáo/Images/visualization/*.png
    _Data_Warehouse__Báo_cáo/Images/OLAP/*.png
    _Data_Warehouse__Báo_cáo/Images/Data_mining/K-means.png

Run from any working directory.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# ---------- Paths ----------
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RAW = PROJECT / "raw"
REPORT_ROOT = (PROJECT.parent / "_Data_Warehouse" / "_Data_Warehouse__Báo_cáo")
IMG = REPORT_ROOT / "Images"
DIR_VIS = IMG / "visualization"
DIR_OLAP = IMG / "OLAP"
DIR_DM = IMG / "Data_mining"
for d in (DIR_VIS, DIR_OLAP, DIR_DM):
    d.mkdir(parents=True, exist_ok=True)

COIN_META = {
    "BTC": ("Bitcoin", "L1"),
    "ETH": ("Ethereum", "L1"),
    "BNB": ("BNB", "L1"),
    "SOL": ("Solana", "L1"),
    "XRP": ("XRP", "Payment"),
    "ADA": ("Cardano", "L1"),
    "DOGE": ("Dogecoin", "Meme"),
    "TRX": ("TRON", "L1"),
    "DOT": ("Polkadot", "L1"),
    "MATIC": ("Polygon", "L2"),
}
COINS = list(COIN_META.keys())
PALETTE = sns.color_palette("tab10", len(COINS))
COLOR = dict(zip(COINS, PALETTE))

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 130,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ---------- Load ----------
def load_one(symbol: str) -> pd.DataFrame:
    p = RAW / f"{symbol}_raw.csv"
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["volume_usd"] = df["close"] * df["volume"]
    df["return_pct"] = (df["close"] - df["open"]) / df["open"] * 100
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["volatility"] = df["high"] - df["low"]
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    df["symbol"] = symbol
    return df

print("Loading raw CSVs ...")
data = {s: load_one(s) for s in COINS}
for s, df in data.items():
    print(f"  {s:>5}  rows={len(df):4d}  range={df['date'].min().date()} -> {df['date'].max().date()}")

# Wide tables for cross-coin metrics
close_wide = pd.concat({s: df.set_index("date")["close"] for s, df in data.items()}, axis=1)
logret_wide = pd.concat({s: df.set_index("date")["log_return"] for s, df in data.items()}, axis=1)
vol_usd_wide = pd.concat({s: df.set_index("date")["volume_usd"] for s, df in data.items()}, axis=1)

# =====================================================================
# 1. PER-COIN CLOSE CHARTS  (visualization/<SYM>_close_chart.png)
# =====================================================================
def plot_close(symbol: str):
    df = data[symbol]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(df["date"], df["close"], color=COLOR[symbol], lw=1.6)
    ax.set_title(f"{COIN_META[symbol][0]} ({symbol}) — Daily Close (USDT)")
    ax.set_xlabel("Date"); ax.set_ylabel("Close (USDT)")
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    out = DIR_VIS / f"{symbol}_close_chart.png"
    fig.savefig(out); plt.close(fig)
    return out

for s in COINS:
    plot_close(s)
print("  close charts: 10 written")

# =====================================================================
# 2. AVERAGE VOLUME (USD) BAR CHART
# =====================================================================
avg_vol = (vol_usd_wide.mean() / 1e6).sort_values(ascending=False)  # in $M
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(avg_vol.index, avg_vol.values, color=[COLOR[c] for c in avg_vol.index])
ax.set_title("Khối lượng Giao dịch Trung bình (USD) — Top 10 Coin")
ax.set_xlabel("Coin"); ax.set_ylabel("Avg Daily Volume (Million USD)")
ax.grid(axis="y", alpha=0.3)
for b, v in zip(bars, avg_vol.values):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.0f}M", ha="center", va="bottom", fontsize=9)
fig.savefig(DIR_VIS / "AverageVolumn.png"); plt.close(fig)
print("  AverageVolumn.png")

# =====================================================================
# 3. CUMULATIVE LOG RETURN (normalised growth of $1)
# =====================================================================
cum_growth = np.exp(logret_wide.fillna(0).cumsum())
fig, ax = plt.subplots(figsize=(11, 5.5))
for c in COINS:
    ax.plot(cum_growth.index, cum_growth[c], label=c, color=COLOR[c], lw=1.4)
ax.axhline(1.0, color="red", ls="--", lw=1, alpha=0.7)
ax.set_title("So sánh Hiệu suất Đầu tư — Cumulative Growth of $1")
ax.set_xlabel("Date"); ax.set_ylabel("Cumulative Growth (×)")
ax.legend(ncol=5, fontsize=9, loc="upper left")
ax.grid(alpha=0.3)
fig.savefig(DIR_VIS / "CumulativeLogReturn.png"); plt.close(fig)
print("  CumulativeLogReturn.png")

# =====================================================================
# 4. ROLLING VOLATILITY (20 / 60 day)  — std of daily log_return
# =====================================================================
def plot_rolling_vol(window: int, fname: str):
    rv = logret_wide.rolling(window).std()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for c in COINS:
        ax.plot(rv.index, rv[c], label=c, color=COLOR[c], lw=1.2)
    ax.set_title(f"Rolling Volatility {window} ngày (std log-return)")
    ax.set_xlabel("Date"); ax.set_ylabel("Std (daily log-return)")
    ax.legend(ncol=5, fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    fig.savefig(DIR_VIS / fname); plt.close(fig)

plot_rolling_vol(20, "RollingVolatility20.png")
plot_rolling_vol(60, "RollingVolatility60.png")
print("  RollingVolatility20/60.png")

# =====================================================================
# 5. BOXPLOT OF DAILY LOG-RETURNS  (boxplot_rui_ro.png)
# =====================================================================
melt = logret_wide.melt(var_name="coin", value_name="log_return").dropna()
fig, ax = plt.subplots(figsize=(11, 5.5))
sns.boxplot(data=melt, x="coin", y="log_return", order=COINS,
            palette=[COLOR[c] for c in COINS], ax=ax, fliersize=2)
ax.axhline(0, color="red", ls="--", lw=1)
ax.set_title("Phân phối Log-Return Hàng ngày — Top 10 Coin")
ax.set_xlabel("Coin"); ax.set_ylabel("Log Return (daily)")
ax.grid(axis="y", alpha=0.3)
fig.savefig(DIR_VIS / "boxplot_rui_ro.png"); plt.close(fig)
print("  boxplot_rui_ro.png")

# =====================================================================
# 6. VOLUME-SPIKE vs RETURN  (scatter + bar)
# =====================================================================
spike_rows = []
abs_means = []
for s, df in data.items():
    d = df.copy()
    rolling_med = d["volume_usd"].rolling(20, min_periods=5).median()
    d["is_spike"] = d["volume_usd"] > 2 * rolling_med
    spike_rows.append(d[["date", "symbol", "volume_usd", "return_pct", "is_spike"]])
    sp = d.loc[d["is_spike"], "return_pct"].abs().mean()
    nsp = d.loc[~d["is_spike"], "return_pct"].abs().mean()
    abs_means.append({"coin": s, "spike": sp, "non_spike": nsp})

spike_df = pd.concat(spike_rows, ignore_index=True)
abs_df = pd.DataFrame(abs_means)

# 6a. Scatter (volume_usd vs return_pct, color by is_spike)
fig, ax = plt.subplots(figsize=(11, 5.5))
non = spike_df[~spike_df["is_spike"]]
spk = spike_df[spike_df["is_spike"]]
ax.scatter(non["volume_usd"] / 1e9, non["return_pct"], s=10, alpha=0.4,
           color="steelblue", label="Non-Spike (False)")
ax.scatter(spk["volume_usd"] / 1e9, spk["return_pct"], s=18, alpha=0.7,
           color="crimson", label="Volume Spike (True)")
ax.axhline(0, color="black", lw=0.6)
ax.set_title("Volume Spike vs Daily Return — Top 10 Coin")
ax.set_xlabel("Volume (Billion USD)"); ax.set_ylabel("Daily Return (%)")
ax.legend(); ax.grid(alpha=0.3)
fig.savefig(DIR_VIS / "VolumeSpikeVsReturn.png"); plt.close(fig)

# 6b. Bar |Return| Spike vs Non-Spike per coin
fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(COINS))
w = 0.38
ax.bar(x - w / 2, abs_df.set_index("coin").loc[COINS, "non_spike"], width=w,
       color="steelblue", label="Mean |Return| — Non-Spike")
ax.bar(x + w / 2, abs_df.set_index("coin").loc[COINS, "spike"], width=w,
       color="orange", label="Mean |Return| — Spike")
ax.set_xticks(x); ax.set_xticklabels(COINS)
ax.set_title("So sánh |Return| trung bình: Spike vs Non-Spike")
ax.set_ylabel("Mean |Daily Return| (%)"); ax.legend(); ax.grid(axis="y", alpha=0.3)
fig.savefig(DIR_VIS / "SpikeVsNon-Spike.png"); plt.close(fig)

# 6c. Is_Spike_Day (count of spike days per coin)
spike_count = spike_df.groupby("symbol")["is_spike"].sum().reindex(COINS)
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.bar(spike_count.index, spike_count.values,
       color=[COLOR[c] for c in spike_count.index])
ax.set_title("Số ngày Volume Spike theo Coin")
ax.set_ylabel("Spike Days"); ax.grid(axis="y", alpha=0.3)
for i, v in enumerate(spike_count.values):
    ax.text(i, v, str(int(v)), ha="center", va="bottom", fontsize=9)
fig.savefig(DIR_VIS / "Is_Spike_Day.png"); plt.close(fig)
print("  Volume-Spike charts (3)")

# =====================================================================
# 7. CORRELATION & COVARIANCE HEATMAPS
# =====================================================================
corr = logret_wide.corr()
fig, ax = plt.subplots(figsize=(8, 6.5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            vmin=-1, vmax=1, square=True, cbar_kws={"shrink": 0.8}, ax=ax)
ax.set_title("Heatmap Tương quan Lợi suất (Daily Log-Return)")
fig.savefig(DIR_VIS / "HeatmapLoiSuat.png"); plt.close(fig)

cov = logret_wide.cov()
fig, ax = plt.subplots(figsize=(8, 6.5))
sns.heatmap(cov, annot=True, fmt=".1e", cmap="viridis",
            square=True, cbar_kws={"shrink": 0.8}, ax=ax)
ax.set_title("Heatmap Đồng biến động (Hiệp phương sai Log-Return)")
fig.savefig(DIR_VIS / "HeatmapDongBienDong.png"); plt.close(fig)
print("  Heatmaps (2)")

# =====================================================================
# 8. OLAP: combined price trend, volume 2025, heatmap price
# =====================================================================
# 8a. Price trend (normalised so all visible on same axis)
norm = close_wide / close_wide.iloc[0]
fig, ax = plt.subplots(figsize=(11, 5.5))
for c in COINS:
    ax.plot(norm.index, norm[c], label=c, color=COLOR[c], lw=1.3)
ax.set_title("Combined Price Trend (Normalised to 1.0 at start) — Top 10 Coin")
ax.set_xlabel("Date"); ax.set_ylabel("Normalised Close")
ax.legend(ncol=5, fontsize=9, loc="upper left"); ax.grid(alpha=0.3)
fig.savefig(DIR_OLAP / "01_combined_price_trend.png"); plt.close(fig)

# 8b. Volume 2025 (sum of volume_usd in 2025 per coin)
vol_2025 = (vol_usd_wide.loc["2025-01-01":].sum() / 1e9).sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(vol_2025.index, vol_2025.values,
              color=[COLOR[c] for c in vol_2025.index])
ax.set_title("Tổng Khối lượng Giao dịch năm 2025 (Billion USD)")
ax.set_ylabel("Volume YTD 2025 (Billion USD)"); ax.grid(axis="y", alpha=0.3)
for b, v in zip(bars, vol_2025.values):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.0f}B",
            ha="center", va="bottom", fontsize=9)
fig.savefig(DIR_OLAP / "02_combined_volume_2025.png"); plt.close(fig)

# 8c. Heatmap: monthly mean return % per coin
month_ret = (logret_wide.resample("ME").sum() * 100)
month_ret.index = [d.strftime("%Y-%m") for d in month_ret.index]
fig, ax = plt.subplots(figsize=(13, 6.5))
sns.heatmap(month_ret.T, annot=True, fmt=".1f", cmap="RdYlGn", center=0,
            cbar_kws={"shrink": 0.7, "label": "Monthly Return (%)"}, ax=ax,
            annot_kws={"fontsize": 7})
ax.set_title("Heatmap Lợi suất Tháng theo Coin")
ax.set_xlabel("Month"); ax.set_ylabel("Coin")
plt.setp(ax.get_xticklabels(), rotation=60, ha="right")
fig.savefig(DIR_OLAP / "03_combined_heatmap_price.png"); plt.close(fig)
print("  OLAP charts (3)")

# =====================================================================
# 9. K-MEANS CLUSTERING (Data_mining/K-means.png) + summary table
# =====================================================================
features = []
for s, df in data.items():
    feats = {
        "coin": s,
        "return_avg": df["log_return"].mean() * 100,
        "vol_avg": df["log_return"].std() * 100,
        "vol_usd_avg": np.log10(max(df["volume_usd"].mean(), 1)),
        "drawdown": ((df["close"] / df["close"].cummax()) - 1).min() * 100,
    }
    features.append(feats)
feat_df = pd.DataFrame(features).set_index("coin").loc[COINS]

X = StandardScaler().fit_transform(feat_df.values)
km = KMeans(n_clusters=3, random_state=42, n_init=10).fit(X)
labels = km.labels_
pcs = PCA(n_components=2, random_state=42).fit_transform(X)

cluster_palette = ["#1f77b4", "#ff7f0e", "#2ca02c"]
fig, ax = plt.subplots(figsize=(9, 6.5))
for k in range(3):
    mask = labels == k
    ax.scatter(pcs[mask, 0], pcs[mask, 1], s=180,
               c=cluster_palette[k], label=f"Cluster {k}", edgecolor="black", alpha=0.85)
for i, c in enumerate(feat_df.index):
    ax.annotate(c, (pcs[i, 0], pcs[i, 1]), xytext=(7, 5),
                textcoords="offset points", fontsize=10, fontweight="bold")
ax.axhline(0, color="grey", lw=0.5); ax.axvline(0, color="grey", lw=0.5)
ax.set_title("K-Means Clustering (k=3) — Top 10 Coin (PCA 2D)")
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
ax.legend(); ax.grid(alpha=0.3)
fig.savefig(DIR_DM / "K-means.png"); plt.close(fig)

# Save cluster summary so the LaTeX can quote it
summary = feat_df.copy()
summary["cluster"] = labels
summary["category"] = [COIN_META[c][1] for c in summary.index]
summary_path = HERE / "kmeans_summary.json"
summary_path.write_text(summary.reset_index().to_json(orient="records", indent=2))
print(f"  K-means clustering done — summary: {summary_path}")

# =====================================================================
# 10. ANOMALY SUMMARY (used in DataMining text)
# =====================================================================
anomaly_rows = []
for s, df in data.items():
    d = df.copy()
    mu = d["close"].rolling(30, min_periods=10).mean()
    sd = d["close"].rolling(30, min_periods=10).std()
    d["z"] = (d["close"] - mu) / sd
    n_anom = int((d["z"].abs() > 2).sum())
    anomaly_rows.append({"coin": s, "n_anomaly": n_anom,
                         "rate_pct": round(100 * n_anom / len(d), 2)})
anomaly_df = pd.DataFrame(anomaly_rows)
(HERE / "anomaly_summary.json").write_text(anomaly_df.to_json(orient="records", indent=2))
print(f"  anomaly_summary.json written")

print("\nDONE — all images regenerated.")
