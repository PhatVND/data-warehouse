"""
Generate Power BI-style mock dashboard images from gold layer CSV.
These images serve as 'screenshots' of what the .pbix dashboard
should look like once built in Power BI Desktop.

4 outputs (under Images/PBI/):
  - dashboard_overview.png   : KPI cards + price line + market dominance pie
  - dashboard_mining.png     : Risk-Return scatter + regime stack + anomaly table
  - pbi_drilldown.png        : Year -> Month drill-down for BTC
  - pbi_model_view.png       : Star Schema Model view (3 tables + 3 relationships)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DATA = PROJECT / "bi" / "data"
OUT = (PROJECT.parent / "_Data_Warehouse" / "_Data_Warehouse__Báo_cáo"
       / "Images" / "PBI")
OUT.mkdir(parents=True, exist_ok=True)

# Power BI dark theme palette
BG = "#252423"
PANEL = "#3A3938"
ACCENT = "#118DFF"
GREEN = "#52B86F"
RED = "#E0524A"
YELLOW = "#F2C811"
TEXT = "#F2F2F2"
MUTED = "#A6A6A6"

plt.rcParams.update({
    "savefig.dpi": 130,
    "savefig.bbox": "tight",
    "axes.facecolor": PANEL,
    "figure.facecolor": BG,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "axes.titleweight": "bold",
    "axes.titlesize": 11,
    "axes.titlecolor": TEXT,
    "text.color": TEXT,
})

fact = pd.read_csv(DATA / "fact_market_daily.csv")
coin = pd.read_csv(DATA / "dim_coin.csv")
cat = pd.read_csv(DATA / "dim_category.csv")
date = pd.read_csv(DATA / "dim_date.csv", parse_dates=["full_date"])
df = (fact.merge(coin, on="coin_id")
           .merge(cat, on="category_id")
           .merge(date, on="date_id"))
df["is_anomaly"] = df["is_anomaly"].astype(str).str.lower().isin(["true", "1"])

# =====================================================================
# 1. DASHBOARD OVERVIEW
# =====================================================================
def header(fig, title):
    fig.text(0.02, 0.97, "[Power BI]", fontsize=11, color=YELLOW,
             fontweight="bold")
    fig.text(0.20, 0.97, title, fontsize=13, color=TEXT,
             fontweight="bold")
    fig.text(0.98, 0.97, "Dec 2025  •  Gold Layer", fontsize=9,
             color=MUTED, ha="right")


def kpi_card(ax, label, value, sub=""):
    ax.set_facecolor(PANEL)
    for s in ax.spines.values():
        s.set_color(MUTED); s.set_linewidth(0.5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.5, 0.78, label, transform=ax.transAxes, ha="center",
            color=MUTED, fontsize=9)
    ax.text(0.5, 0.45, value, transform=ax.transAxes, ha="center",
            color=TEXT, fontsize=17, fontweight="bold")
    if sub:
        ax.text(0.5, 0.13, sub, transform=ax.transAxes, ha="center",
                color=MUTED, fontsize=8)


def make_overview():
    fig = plt.figure(figsize=(15, 9))
    gs = GridSpec(4, 5, figure=fig, hspace=0.45, wspace=0.25,
                  top=0.93, bottom=0.05, left=0.05, right=0.97)
    header(fig, "Crypto Market Overview — fact_market_daily")

    # KPI row
    total_vol = df["volume_usd"].sum() / 1e9
    avg_ret = df["return_pct"].mean()
    n_anom = df["is_anomaly"].sum()
    n_bull = (df["regime_label"] == "Bull").sum()
    n_bear = (df["regime_label"] == "Bear").sum()
    kpis = [
        ("TOTAL VOLUME (USD)", f"${total_vol:,.0f}B", ""),
        ("AVG DAILY RETURN", f"{avg_ret:.3f}%",
         "▲" if avg_ret >= 0 else "▼"),
        ("ANOMALY DAYS", f"{n_anom:,}",
         f"{n_anom/len(df)*100:.1f}% of rows"),
        ("BULL / BEAR DAYS", f"{n_bull:,} / {n_bear:,}",
         f"{df['date_id'].nunique()} trading days"),
        ("COINS", f"{df['symbol'].nunique()}", "Top by Binance"),
    ]
    for i, (lab, val, sub) in enumerate(kpis):
        kpi_card(fig.add_subplot(gs[0, i]), lab, val, sub)

    # Price line — top 5 by avg volume
    ax_line = fig.add_subplot(gs[1:3, 0:3])
    top5 = (df.groupby("symbol")["volume_usd"].mean()
              .sort_values(ascending=False).head(5).index.tolist())
    palette = ["#FFB900", "#118DFF", "#E0524A", "#52B86F", "#9F4AC0"]
    for i, s in enumerate(top5):
        d = df[df["symbol"] == s].sort_values("full_date")
        ax_line.plot(d["full_date"], d["close"] / d["close"].iloc[0],
                     label=s, lw=1.6, color=palette[i])
    ax_line.legend(loc="upper left", facecolor=PANEL, edgecolor=MUTED,
                   labelcolor=TEXT, fontsize=9, ncol=5)
    ax_line.set_title("Daily Close Price (normalised) — Top-5 by Volume")
    ax_line.grid(alpha=0.2)

    # Market Dominance pie
    ax_pie = fig.add_subplot(gs[1:3, 3:5])
    dom = df.groupby("symbol")["volume_usd"].sum().sort_values(ascending=False)
    colors = ["#FFB900", "#118DFF", "#E0524A", "#52B86F", "#9F4AC0",
              "#F8C8DC", "#5BC0EB", "#F25F5C", "#247BA0", "#70C1B3"]
    ax_pie.pie(dom.values, labels=dom.index, autopct="%1.1f%%",
               colors=colors, textprops={"color": TEXT, "fontsize": 9},
               wedgeprops={"edgecolor": BG, "linewidth": 1.5})
    ax_pie.set_title("Market Dominance (Total Volume USD)")

    # Volume leaderboard bar
    ax_bar = fig.add_subplot(gs[3, :])
    vol_avg = df.groupby("symbol")["volume_usd"].mean().sort_values()
    bars = ax_bar.barh(vol_avg.index, vol_avg.values / 1e6,
                       color="#118DFF", edgecolor=BG)
    ax_bar.set_xlabel("Avg Daily Volume (Million USD)")
    ax_bar.set_title("Volume Leaderboard")
    ax_bar.grid(axis="x", alpha=0.2)
    for b, v in zip(bars, vol_avg.values / 1e6):
        ax_bar.text(v, b.get_y() + b.get_height() / 2, f" ${v:,.0f}M",
                    va="center", color=TEXT, fontsize=9)

    fig.savefig(OUT / "dashboard_overview.png", facecolor=BG)
    plt.close(fig)
    print("  -> dashboard_overview.png")


# =====================================================================
# 2. DASHBOARD MINING
# =====================================================================
def make_mining():
    fig = plt.figure(figsize=(15, 9))
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.30,
                  top=0.92, bottom=0.06, left=0.06, right=0.97)
    header(fig, "Data Mining Insights — Risk-Return / Anomaly / Regime")

    # 2.1 Risk-Return scatter (K-Means cluster)
    ax_sc = fig.add_subplot(gs[0, 0:2])
    agg = df.groupby(["symbol", "category_name"]).agg(
        ret=("return_pct", "mean"), vol=("return_pct", "std"),
        volume=("volume_usd", "mean")).reset_index()
    cat_colors = {"L1": "#118DFF", "L2": "#52B86F",
                  "Meme": "#FFB900", "Payment": "#E0524A"}
    for c, col in cat_colors.items():
        sub = agg[agg["category_name"] == c]
        ax_sc.scatter(sub["vol"], sub["ret"],
                      s=sub["volume"] / sub["volume"].max() * 800 + 100,
                      c=col, label=c, alpha=0.85, edgecolor=BG)
        for _, r in sub.iterrows():
            ax_sc.annotate(r["symbol"], (r["vol"], r["ret"]),
                           xytext=(7, 4), textcoords="offset points",
                           color=TEXT, fontsize=9, fontweight="bold")
    ax_sc.legend(facecolor=PANEL, edgecolor=MUTED, labelcolor=TEXT,
                 title="Category", title_fontsize=9, fontsize=9)
    ax_sc.set_xlabel("Volatility (std daily return %)")
    ax_sc.set_ylabel("Mean Daily Return (%)")
    ax_sc.set_title("Risk-Return Scatter (size = avg volume)")
    ax_sc.axhline(0, color=MUTED, lw=0.6); ax_sc.grid(alpha=0.2)

    # 2.2 Regime stacked bar
    ax_reg = fig.add_subplot(gs[0, 2])
    reg = df.groupby(["symbol", "regime_label"]).size().unstack(fill_value=0)
    reg = reg.reindex(columns=["Bull", "Sideways", "Bear"])
    reg = reg.div(reg.sum(axis=1), axis=0) * 100
    reg.plot.barh(stacked=True, ax=ax_reg,
                  color=[GREEN, YELLOW, RED], edgecolor=BG, width=0.7)
    ax_reg.legend(facecolor=PANEL, edgecolor=MUTED, labelcolor=TEXT,
                  fontsize=8, title="Regime", title_fontsize=8)
    ax_reg.set_xlabel("% of trading days")
    ax_reg.set_title("Regime Distribution per Coin")
    ax_reg.grid(axis="x", alpha=0.2)

    # 2.3 Anomaly count per coin
    ax_anm = fig.add_subplot(gs[1, 0])
    anm = df.groupby("symbol")["is_anomaly"].sum().sort_values()
    bars = ax_anm.barh(anm.index, anm.values, color=RED, edgecolor=BG)
    ax_anm.set_xlabel("Anomaly Days  (|z|>2)")
    ax_anm.set_title("Top Anomalies per Coin")
    ax_anm.grid(axis="x", alpha=0.2)
    for b, v in zip(bars, anm.values):
        ax_anm.text(v + 1, b.get_y() + b.get_height() / 2, str(int(v)),
                    va="center", color=TEXT, fontsize=9)

    # 2.4 Top 10 extreme anomalies table (matrix-style)
    ax_tb = fig.add_subplot(gs[1, 1:])
    ax_tb.set_facecolor(PANEL); ax_tb.set_xticks([]); ax_tb.set_yticks([])
    for s in ax_tb.spines.values(): s.set_color(MUTED)
    top10 = (df[df["is_anomaly"]]
             .assign(abs_z=lambda d: d["z_score_close"].abs())
             .nlargest(10, "abs_z")
             [["full_date", "symbol", "close", "return_pct",
               "z_score_close", "regime_label"]])
    headers = ["Date", "Coin", "Close", "Return %", "Z", "Regime"]
    n = len(top10)
    col_x = [0.04, 0.18, 0.28, 0.46, 0.62, 0.78]
    col_w = [0.13, 0.09, 0.17, 0.15, 0.12, 0.18]
    # header row
    for x, h in zip(col_x, headers):
        ax_tb.text(x, 0.93, h, color=YELLOW, fontsize=10, fontweight="bold",
                   transform=ax_tb.transAxes)
    for i, (_, r) in enumerate(top10.iterrows()):
        y = 0.85 - i * 0.08
        if i % 2 == 0:
            ax_tb.add_patch(mpatches.Rectangle((0.02, y - 0.025), 0.96, 0.07,
                            transform=ax_tb.transAxes,
                            facecolor="#2A2928", alpha=0.6))
        cells = [
            r["full_date"].strftime("%Y-%m-%d"),
            r["symbol"],
            f"${r['close']:,.2f}",
            f"{r['return_pct']:+.2f}%",
            f"{r['z_score_close']:+.2f}",
            r["regime_label"],
        ]
        c_color = RED if r["return_pct"] < 0 else GREEN
        for j, (x, val) in enumerate(zip(col_x, cells)):
            color = c_color if j == 3 else TEXT
            ax_tb.text(x, y, val, color=color, fontsize=9.5,
                       transform=ax_tb.transAxes)
    ax_tb.set_title("Top-10 Extreme Anomalies (|z| desc)", loc="left")

    fig.savefig(OUT / "dashboard_mining.png", facecolor=BG)
    plt.close(fig)
    print("  -> dashboard_mining.png")


# =====================================================================
# 3. DRILL-DOWN year -> month -> day for BTC
# =====================================================================
def make_drilldown():
    fig = plt.figure(figsize=(15, 7))
    gs = GridSpec(1, 3, figure=fig, wspace=0.30,
                  top=0.88, bottom=0.10, left=0.05, right=0.97)
    header(fig, "OLAP Drill-Down — BTC: Year → Quarter → Month")

    btc = df[df["symbol"] == "BTC"].copy()
    btc["year"] = pd.to_datetime(btc["full_date"]).dt.year
    btc["quarter"] = pd.to_datetime(btc["full_date"]).dt.quarter
    btc["month"] = pd.to_datetime(btc["full_date"]).dt.month

    # Year level
    ax1 = fig.add_subplot(gs[0, 0])
    yr = btc.groupby("year")["return_pct"].sum()
    bars = ax1.bar(yr.index.astype(str), yr.values,
                   color=[GREEN if v >= 0 else RED for v in yr.values],
                   edgecolor=BG)
    ax1.set_title("LEVEL 1 — by Year"); ax1.grid(axis="y", alpha=0.2)
    ax1.set_ylabel("Sum return %")
    for b, v in zip(bars, yr.values):
        ax1.text(b.get_x() + b.get_width() / 2, v,
                 f"{v:+.0f}%", ha="center",
                 va="bottom" if v >= 0 else "top",
                 color=TEXT, fontsize=10, fontweight="bold")

    # Quarter level (filter to year with most rows)
    ax2 = fig.add_subplot(gs[0, 1])
    target_year = yr.abs().idxmax()
    qd = btc[btc["year"] == target_year].groupby("quarter")["return_pct"].sum()
    bars = ax2.bar([f"Q{i}" for i in qd.index], qd.values,
                   color=[GREEN if v >= 0 else RED for v in qd.values],
                   edgecolor=BG)
    ax2.set_title(f"LEVEL 2 — by Quarter ({target_year})  (drilled)")
    ax2.grid(axis="y", alpha=0.2)
    for b, v in zip(bars, qd.values):
        ax2.text(b.get_x() + b.get_width() / 2, v,
                 f"{v:+.0f}%", ha="center",
                 va="bottom" if v >= 0 else "top",
                 color=TEXT, fontsize=10, fontweight="bold")

    # Month level (filter to best quarter)
    ax3 = fig.add_subplot(gs[0, 2])
    target_q = qd.abs().idxmax()
    md = (btc[(btc["year"] == target_year) & (btc["quarter"] == target_q)]
          .groupby("month")["return_pct"].sum())
    bars = ax3.bar(md.index.astype(str), md.values,
                   color=[GREEN if v >= 0 else RED for v in md.values],
                   edgecolor=BG)
    ax3.set_title(f"LEVEL 3 — by Month (Q{target_q} {target_year})  (drilled)")
    ax3.grid(axis="y", alpha=0.2); ax3.set_xlabel("Month")
    for b, v in zip(bars, md.values):
        ax3.text(b.get_x() + b.get_width() / 2, v,
                 f"{v:+.0f}", ha="center",
                 va="bottom" if v >= 0 else "top",
                 color=TEXT, fontsize=10, fontweight="bold")

    fig.savefig(OUT / "pbi_drilldown.png", facecolor=BG)
    plt.close(fig)
    print("  -> pbi_drilldown.png")


# =====================================================================
# 4. MODEL VIEW (Star Schema in Power BI style)
# =====================================================================
def make_model_view():
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG); ax.set_xlim(0, 14); ax.set_ylim(0, 9)
    ax.axis("off")
    fig.text(0.02, 0.97, "[Power BI]", fontsize=11, color=YELLOW,
             fontweight="bold")
    fig.text(0.20, 0.97, "Model View — Star Schema (3 active relationships)",
             fontsize=13, color=TEXT, fontweight="bold")

    def pbi_table(x, y, w, h, title, fields):
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.05", facecolor=PANEL,
                     edgecolor=ACCENT, lw=1.5))
        ax.text(x + w / 2, y + h - 0.35, title, ha="center", va="center",
                color=YELLOW, fontsize=11, fontweight="bold")
        for i, (name, key) in enumerate(fields):
            fy = y + h - 0.95 - i * 0.32
            sym = "[K]" if key == "PK" else ("[F]" if key == "FK" else " - ")
            ax.text(x + 0.15, fy, f"{sym}  {name}", ha="left",
                    va="center", color=TEXT, fontsize=9)

    pbi_table(5.0, 1, 4, 7, "fact_market_daily", [
        ("date_id", "PK"), ("coin_id", "PK"),
        ("open", ""), ("high", ""), ("low", ""), ("close", ""),
        ("volume_usd", ""), ("return_pct", ""), ("z_score_close", ""),
        ("is_anomaly", ""), ("regime_label", ""),
        ("market_dominance_pct", ""), ("...", ""),
    ])
    pbi_table(0.3, 5, 4, 3, "dim_date", [
        ("date_id", "PK"), ("full_date", ""),
        ("year", ""), ("quarter", ""), ("month", ""),
    ])
    pbi_table(9.5, 5, 4, 3, "dim_coin", [
        ("coin_id", "PK"), ("symbol", ""),
        ("full_name", ""), ("category_id", "FK"),
    ])
    pbi_table(9.5, 1, 4, 3, "dim_category", [
        ("category_id", "PK"), ("category_name", ""), ("risk_level", ""),
    ])

    arrows = [
        ((4.3, 6.5),  (5.0, 5.5),  "1 → ∞"),
        ((9.5, 6.5),  (9.0, 5.5),  "1 → ∞"),
        ((11.5, 5.0), (11.5, 4.0), "1 → ∞"),
    ]
    for (x1, y1), (x2, y2), label in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=ACCENT, lw=2.2))
        ax.text((x1 + x2) / 2 + 0.2, (y1 + y2) / 2,
                label, color=ACCENT, fontsize=8, fontweight="bold")

    fig.savefig(OUT / "pbi_model_view.png", facecolor=BG)
    plt.close(fig)
    print("  -> pbi_model_view.png")


if __name__ == "__main__":
    make_overview()
    make_mining()
    make_drilldown()
    make_model_view()
    print("\nAll PBI mocks done.")
