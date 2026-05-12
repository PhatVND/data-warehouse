"""
Compute real analytics for the report:

  1. Linear Regression for each of 10 coins (R^2, MSE, coefficients)
     using time-based 80/20 split, predicting close_T+1 from
     OHLCV_T + MA7_T + Z_score_T.

  2. K-Means validation: inertia and silhouette across k=2..6.

  3. Anomaly case study: pick the BTC date with largest |z_score|,
     return date + price + return%.

Outputs JSON files (consumed when writing tex) and 1 PNG (Elbow chart).
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RAW = PROJECT / "raw"
REPORT_IMG = (PROJECT.parent / "_Data_Warehouse" / "_Data_Warehouse__Báo_cáo" / "Images")
DIR_DM = REPORT_IMG / "Data_mining"
DIR_DM.mkdir(parents=True, exist_ok=True)

COINS = ["BTC", "ETH", "BNB", "SOL", "XRP",
         "ADA", "DOGE", "TRX", "DOT", "MATIC"]


def load_one(symbol):
    df = pd.read_csv(RAW / f"{symbol}_raw.csv")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    df["volume_usd"] = df["close"] * df["volume"]
    df["MA7"] = df["close"].rolling(7).mean()
    mu = df["close"].rolling(30, min_periods=10).mean()
    sd = df["close"].rolling(30, min_periods=10).std()
    df["z_score"] = (df["close"] - mu) / sd
    df["close_next"] = df["close"].shift(-1)
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    return df.dropna().reset_index(drop=True)

# =====================================================================
# 1. LINEAR REGRESSION — predict close_{T+1}
# =====================================================================
features = ["open", "high", "low", "close", "volume", "MA7", "z_score"]
results = []

for s in COINS:
    df = load_one(s)
    X = df[features].values
    y = df["close_next"].values

    n = len(df)
    cut = int(n * 0.8)
    X_tr, X_te = X[:cut], X[cut:]
    y_tr, y_te = y[:cut], y[cut:]

    model = LinearRegression().fit(X_tr, y_tr)
    y_hat = model.predict(X_te)

    row = {
        "coin": s,
        "n_train": int(cut),
        "n_test": int(n - cut),
        "r2": round(r2_score(y_te, y_hat), 4),
        "mse": round(mean_squared_error(y_te, y_hat), 6),
        "intercept": round(float(model.intercept_), 6),
    }
    for i, f in enumerate(features):
        row[f"coef_{f}"] = round(float(model.coef_[i]), 6)
    results.append(row)

(HERE / "regression_results.json").write_text(
    json.dumps(results, indent=2))
print("Regression — 10 coins ✓")
for r in results:
    print(f"  {r['coin']:>5}  R2={r['r2']:.4f}  MSE={r['mse']:.4g}")


# =====================================================================
# 2. K-MEANS validation: inertia + silhouette across k=2..6
# =====================================================================
feat_rows = []
for s in COINS:
    df = load_one(s)
    feat_rows.append({
        "coin": s,
        "return_avg": df["log_return"].mean() * 100,
        "vol_avg": df["log_return"].std() * 100,
        "vol_usd_avg": np.log10(max(df["volume_usd"].mean(), 1)),
        "drawdown": ((df["close"] / df["close"].cummax()) - 1).min() * 100,
    })
feat_df = pd.DataFrame(feat_rows).set_index("coin").loc[COINS]
X = StandardScaler().fit_transform(feat_df.values)

ks = list(range(2, 7))
inertias = []
silhouettes = []
for k in ks:
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    inertias.append(round(float(km.inertia_), 4))
    silhouettes.append(round(float(silhouette_score(X, km.labels_)), 4))

(HERE / "kmeans_validation.json").write_text(json.dumps({
    "k": ks, "inertia": inertias, "silhouette": silhouettes
}, indent=2))

# Plot Elbow + Silhouette
fig, ax1 = plt.subplots(figsize=(9, 5))
color1, color2 = "#E84A5F", "#4F8FF7"
ax1.set_xlabel("Số cụm k")
ax1.set_ylabel("Inertia (trong-cụm SSE)", color=color1)
ax1.plot(ks, inertias, "o-", color=color1, lw=2, label="Inertia")
ax1.tick_params(axis="y", labelcolor=color1)

ax2 = ax1.twinx()
ax2.set_ylabel("Silhouette score", color=color2)
ax2.plot(ks, silhouettes, "s--", color=color2, lw=2, label="Silhouette")
ax2.tick_params(axis="y", labelcolor=color2)

# annotate chosen k=3
best_k = ks[int(np.argmax(silhouettes))]
ax1.axvline(best_k, color="green", ls=":", alpha=0.6)
ax1.annotate(f"k={best_k}\n(silhouette cao nhất)",
             xy=(best_k, inertias[ks.index(best_k)]),
             xytext=(best_k + 0.4, max(inertias) * 0.7),
             fontsize=10, color="green",
             arrowprops=dict(arrowstyle="->", color="green"))
plt.title("Validation K-Means: Elbow + Silhouette")
fig.tight_layout()
fig.savefig(DIR_DM / "kmeans_validation.png", dpi=140)
plt.close(fig)
print(f"K-Means validation ✓  best_k={best_k}  silhouette={max(silhouettes)}")


# =====================================================================
# 3. ANOMALY CASE STUDY — pick BTC + ETH most extreme |z|
# =====================================================================
case_studies = []
for s in ["BTC", "ETH", "DOGE"]:
    df = load_one(s)
    df["abs_z"] = df["z_score"].abs()
    top = df.nlargest(5, "abs_z")[["date", "close", "log_return", "z_score", "abs_z"]]
    case_studies.append({
        "coin": s,
        "top5": [
            {
                "date":   r["date"].strftime("%Y-%m-%d"),
                "close":  round(float(r["close"]), 4),
                "return_pct": round(float(r["log_return"] * 100), 3),
                "z_score": round(float(r["z_score"]), 3),
            }
            for _, r in top.iterrows()
        ]
    })

(HERE / "anomaly_cases.json").write_text(json.dumps(case_studies, indent=2))
print("Anomaly case studies ✓")
for c in case_studies:
    print(f"  {c['coin']}:")
    for t in c["top5"]:
        print(f"    {t['date']}  close=${t['close']:>12,.2f}  z={t['z_score']:+.2f}  ret={t['return_pct']:+.2f}%")
