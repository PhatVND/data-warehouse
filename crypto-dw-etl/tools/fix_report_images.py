"""
Fix 2 image issues found in PDF review:
  1. Replace stocks-based star-dwh.png + snowflake-dwh.png with crypto schema diagrams.
  2. Re-generate OLAP combined price trend so MATIC (delisted, different date range)
     does not hide the other 9 coins.
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RAW = PROJECT / "raw"
REPORT_ROOT = (PROJECT.parent / "_Data_Warehouse" / "_Data_Warehouse__Báo_cáo")
IMG = REPORT_ROOT / "Images"
DIR_OLAP = IMG / "OLAP"

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 140,
                     "savefig.bbox": "tight", "axes.titleweight": "bold"})

# =====================================================================
# 1. STAR SCHEMA diagram (crypto)
# =====================================================================

def draw_table(ax, x, y, w, h, title, rows, color="#4F8FF7"):
    """Draw a 'table' rectangle with a coloured header and field rows."""
    # header
    ax.add_patch(mpatches.Rectangle((x, y + h - 0.5), w, 0.5,
                                    facecolor=color, edgecolor="black"))
    ax.text(x + w / 2, y + h - 0.25, title, ha="center", va="center",
            color="white", fontsize=10, fontweight="bold")
    # body
    ax.add_patch(mpatches.Rectangle((x, y), w, h - 0.5,
                                    facecolor="white", edgecolor="black"))
    n = len(rows)
    row_h = (h - 0.5) / n
    for i, (name, typ, key) in enumerate(rows):
        ry = y + h - 0.5 - (i + 1) * row_h
        # row separator
        if i > 0:
            ax.plot([x, x + w], [ry + row_h, ry + row_h],
                    color="lightgray", lw=0.5)
        prefix = ""
        if "PK" in key: prefix = "[PK] "
        elif "FK" in key: prefix = "[FK] "
        else: prefix = "     "
        ax.text(x + 0.05, ry + row_h / 2, f"{prefix}{name}",
                ha="left", va="center", fontsize=8.5)
        ax.text(x + w - 0.05, ry + row_h / 2, typ,
                ha="right", va="center", fontsize=7.5,
                color="gray", style="italic")


def draw_star_schema():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 16); ax.set_ylim(0, 9)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Star Schema — Kho dữ liệu Crypto (gold layer)",
                 fontsize=14, pad=18)

    # Fact table (centre)
    fact_rows = [
        ("date_id",              "int",            "PK,FK"),
        ("coin_id",              "int",            "PK,FK"),
        ("open",                 "numeric(18,8)",  ""),
        ("high",                 "numeric(18,8)",  ""),
        ("low",                  "numeric(18,8)",  ""),
        ("close",                "numeric(18,8)",  ""),
        ("volume_base",          "numeric(20,4)",  ""),
        ("volume_usd",           "numeric(20,2)",  ""),
        ("return_pct",           "numeric(10,4)",  ""),
        ("log_return",           "numeric(10,6)",  ""),
        ("volatility",           "numeric(18,8)",  ""),
        ("z_score_close",        "numeric(10,4)",  ""),
        ("is_anomaly",           "bool",           ""),
        ("volume_rank",          "int",            ""),
        ("market_dominance_pct", "numeric(6,3)",   ""),
        ("regime_label",         "varchar(16)",    ""),
    ]
    fx, fy, fw, fh = 6, 1, 4, 7
    draw_table(ax, fx, fy, fw, fh, "fact_market_daily", fact_rows,
               color="#E84A5F")

    # Dim_Date (top-left)
    date_rows = [
        ("date_id",      "int",           "PK"),
        ("full_date",    "date",          ""),
        ("year",         "int",           ""),
        ("quarter",      "int",           ""),
        ("month",        "int",           ""),
        ("week",         "int",           ""),
        ("day_name",     "varchar(10)",   ""),
        ("is_weekend",   "bool",          ""),
    ]
    dx, dy, dw, dh = 0.5, 5.2, 3.5, 3.5
    draw_table(ax, dx, dy, dw, dh, "dim_date", date_rows, color="#4F8FF7")

    # Dim_Coin (top-right)
    coin_rows = [
        ("coin_id",      "int",           "PK"),
        ("symbol",       "varchar(10)",   ""),
        ("full_name",    "varchar(50)",   ""),
        ("launch_year",  "int",           ""),
        ("category_id",  "int",           "FK"),
    ]
    cx, cy, cw, ch = 12, 5.5, 3.5, 3
    draw_table(ax, cx, cy, cw, ch, "dim_coin", coin_rows, color="#4F8FF7")

    # Dim_Category (bottom-right)
    cat_rows = [
        ("category_id",   "int",         "PK"),
        ("category_name", "varchar(20)", ""),
        ("risk_level",    "varchar(10)", ""),
    ]
    catx, caty, catw, cath = 12, 2, 3.5, 2
    draw_table(ax, catx, caty, catw, cath, "dim_category", cat_rows,
               color="#4F8FF7")

    # Connecting lines (1-to-many, fact in centre)
    ax.annotate("", xy=(fx, fy + fh - 1), xytext=(dx + dw, dy + 1),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))
    ax.annotate("", xy=(fx + fw, fy + fh - 1.5), xytext=(cx, cy + 1),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))
    # cat -> coin (snowflake-like in star? no, coin -> category is FK)
    ax.annotate("", xy=(cx + cw / 2, cy), xytext=(catx + catw / 2, caty + cath),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))

    out = IMG / "star-dwh.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


def draw_snowflake_schema():
    """Snowflake variant: dim_coin further normalised into dim_blockchain
    and dim_protocol."""
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(0, 17); ax.set_ylim(0, 10)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Snowflake Schema — Phương án chuẩn hoá (crypto)",
                 fontsize=14, pad=18)

    # Fact (centre)
    fact_rows = [
        ("date_id",      "int",          "PK,FK"),
        ("coin_id",      "int",          "PK,FK"),
        ("OHLCV...",     "numeric",      ""),
        ("return_pct",   "numeric(10,4)",""),
        ("z_score_close","numeric(10,4)",""),
        ("regime_label", "varchar(16)",  ""),
    ]
    fx, fy, fw, fh = 6, 3, 4, 4
    draw_table(ax, fx, fy, fw, fh, "fact_market_daily", fact_rows,
               color="#E84A5F")

    # Dim_Date (top-left)
    date_rows = [("date_id","int","PK"),("full_date","date",""),
                 ("year","int",""),("quarter","int",""),("month","int","")]
    draw_table(ax, 0.5, 5.5, 3.5, 3, "dim_date", date_rows)

    # Dim_Coin (right of fact)
    coin_rows = [("coin_id","int","PK"),("symbol","varchar(10)",""),
                 ("full_name","varchar(50)",""),
                 ("blockchain_id","int","FK"),
                 ("protocol_id",  "int","FK"),
                 ("category_id",  "int","FK")]
    draw_table(ax, 11, 5, 3.5, 3.5, "dim_coin", coin_rows)

    # Dim_Category (bottom-right)
    cat_rows = [("category_id","int","PK"),
                ("category_name","varchar(20)",""),
                ("risk_level","varchar(10)","")]
    draw_table(ax, 11, 1.5, 3.5, 2.2, "dim_category", cat_rows)

    # Dim_Blockchain (top-right snowflake child)
    bc_rows = [("blockchain_id","int","PK"),
               ("name","varchar(20)",""),
               ("consensus","varchar(10)","")]
    draw_table(ax, 14.5, 7, 2.5, 2.2, "dim_blockchain", bc_rows,
               color="#7FB069")

    # Dim_Protocol (right of coin)
    pr_rows = [("protocol_id","int","PK"),
               ("name","varchar(20)",""),
               ("vm_type","varchar(15)","")]
    draw_table(ax, 14.5, 4, 2.5, 2.2, "dim_protocol", pr_rows,
               color="#7FB069")

    # Lines
    ax.annotate("", xy=(fx, fy + fh / 2 + 1),
                xytext=(0.5 + 3.5, 5.5 + 1.5),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))
    ax.annotate("", xy=(fx + fw, fy + fh / 2 + 0.5),
                xytext=(11, 6.5),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))
    ax.annotate("", xy=(11 + 3.5, 7.5), xytext=(14.5, 8.1),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))
    ax.annotate("", xy=(11 + 3.5, 6.5), xytext=(14.5, 5.1),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))
    ax.annotate("", xy=(11 + 3.5 / 2, 5), xytext=(11 + 3.5 / 2, 3.7),
                arrowprops=dict(arrowstyle="-", color="black", lw=1))

    out = IMG / "snowflake-dwh.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


# =====================================================================
# 2. REGENERATE OLAP combined price trend WITHOUT the MATIC date-range bug
# =====================================================================
def fix_price_trend():
    coins = ["BTC","ETH","BNB","SOL","XRP","ADA","DOGE","TRX","DOT","MATIC"]
    palette = sns.color_palette("tab10", len(coins))
    color = dict(zip(coins, palette))

    series = {}
    for s in coins:
        df = pd.read_csv(RAW / f"{s}_raw.csv")
        df["date"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["close"]).sort_values("date")
        series[s] = df.set_index("date")["close"]

    # Use the date range of BTC (the 9-coin range: 2024-04-27 -> 2026-04-26)
    # Drop MATIC entirely from the OVERVIEW chart since its window doesn't overlap.
    base_range = series["BTC"].index
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for s in coins:
        if s == "MATIC":
            continue  # different time window — would skew the chart
        s_data = series[s].reindex(base_range)
        s_norm = s_data / s_data.iloc[0]
        ax.plot(s_norm.index, s_norm.values, label=s, color=color[s], lw=1.4)
    ax.axhline(1.0, color="red", ls="--", lw=1, alpha=0.6)
    ax.set_title("Combined Price Trend (Normalised to 1.0 at start) — 9 Coin"
                 "  *MATIC bị loại do khung thời gian khác (delist 09/2024)")
    ax.set_xlabel("Date"); ax.set_ylabel("Normalised Close")
    ax.legend(ncol=5, fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    out = DIR_OLAP / "01_combined_price_trend.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    print("Drawing crypto Star Schema ...")
    draw_star_schema()
    print("Drawing crypto Snowflake Schema ...")
    draw_snowflake_schema()
    print("Fixing OLAP combined price trend ...")
    fix_price_trend()
    print("\nDONE — recompile pdflatex to see changes.")
