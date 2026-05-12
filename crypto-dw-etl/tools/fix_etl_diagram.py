"""Generate crypto ETL pipeline diagram (replaces old etl_diagram.png)."""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "_Data_Warehouse" / "_Data_Warehouse__Báo_cáo" / "Images" / "etl_diagram.png"

fig, ax = plt.subplots(figsize=(15, 7))
ax.set_xlim(0, 18); ax.set_ylim(0, 9)
ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Kiến trúc luồng ETL của CryptoDW — Binance → Staging → Gold",
             fontsize=14, fontweight="bold", pad=15)

# 4 stages: Source / Ingest / Transform / Warehouse
def stage(x, y, w, h, title, color):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.05", facecolor=color,
                 edgecolor="black", lw=1.2, alpha=0.25))
    ax.text(x + w / 2, y + h - 0.4, title,
            ha="center", va="top", fontsize=11, fontweight="bold")

stage(0.3, 1, 3.6, 7, "1. SOURCE\nBinance REST API", "#4F8FF7")
stage(4.5, 1, 3.6, 7, "2. INGEST (Python)\nfetch_binance.py", "#7FB069")
stage(8.7, 1, 4.5, 7, "3. TRANSFORM\nPentaho / SQL", "#E2A23B")
stage(13.7, 1, 4.0, 7, "4. WAREHOUSE\nGold Layer (Star Schema)", "#E84A5F")

# Source content: 10 coin tickers
coins = ["BTC", "ETH", "BNB", "SOL", "XRP",
         "ADA", "DOGE", "TRX", "DOT", "MATIC"]
ax.text(2.1, 6.6, "/api/v3/klines", ha="center", va="center",
        fontsize=9, style="italic", color="#1F4E9E",
        bbox=dict(facecolor="white", edgecolor="#1F4E9E", boxstyle="round"))
for i, c in enumerate(coins):
    row, col = divmod(i, 2)
    x = 0.7 + col * 1.6
    y = 5.5 - row * 0.8
    ax.add_patch(mpatches.FancyBboxPatch((x, y - 0.25), 1.4, 0.5,
                 boxstyle="round,pad=0.02", facecolor="white",
                 edgecolor="#1F4E9E", lw=0.8))
    ax.text(x + 0.7, y, c, ha="center", va="center",
            fontsize=9, fontweight="bold")

# Ingest content
ingest_blocks = [
    ("HTTP GET\nklines (1d)",      6.5, 6.5),
    ("Parse JSON\n+ Unix → datetime", 6.5, 5.0),
    ("Normalise\nNUMERIC types",    6.5, 3.5),
    ("Save\nraw/SYMBOL_raw.csv",    6.5, 2.0),
]
for txt, x, y in ingest_blocks:
    ax.add_patch(mpatches.FancyBboxPatch((x - 1.3, y - 0.5), 2.6, 1,
                 boxstyle="round,pad=0.04", facecolor="white",
                 edgecolor="#3F6B27", lw=0.9))
    ax.text(x, y, txt, ha="center", va="center", fontsize=9)

# Transform content
xform_blocks = [
    ("staging.ohlcv_raw\n(7,300 rows)",       11, 6.5),
    ("Compute metrics:\nreturn, log_return,\nz_score, anomaly...", 11, 4.8),
    ("staging.fact_prep",                     11, 3.0),
    ("TRUNCATE + INSERT\ngold.fact_market_daily", 11, 1.7),
]
for txt, x, y in xform_blocks:
    ax.add_patch(mpatches.FancyBboxPatch((x - 1.7, y - 0.55), 3.4, 1.1,
                 boxstyle="round,pad=0.04", facecolor="white",
                 edgecolor="#A87420", lw=0.9))
    ax.text(x, y, txt, ha="center", va="center", fontsize=8.5)

# Warehouse content (Star schema mini) — narrower boxes, stacked cleanly
sh_blocks = [
    ("fact_market_daily",                    15.7, 6.5, "#E84A5F", 3.4, 0.7),
    ("dim_date",                             14.6, 5.1, "#4F8FF7", 1.5, 0.6),
    ("dim_coin",                             16.7, 5.1, "#4F8FF7", 1.5, 0.6),
    ("dim_category",                         15.7, 3.9, "#4F8FF7", 3.4, 0.6),
    ("3 OLAP views\n+ Power BI / Streamlit", 15.7, 2.4, "#7FB069", 3.4, 1.0),
]
for txt, x, y, col, w, h in sh_blocks:
    ax.add_patch(mpatches.FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0.04", facecolor=col,
                 edgecolor="black", lw=0.9, alpha=0.85))
    ax.text(x, y, txt, ha="center", va="center",
            fontsize=8.5, color="white", fontweight="bold")

# Big arrows between stages (offset y so they don't overlap warehouse boxes)
arrow_kw = dict(arrowstyle="->", color="black", lw=2.2)
ax.annotate("", xy=(4.4, 4.5), xytext=(3.95, 4.5), arrowprops=arrow_kw)
ax.annotate("", xy=(8.6, 4.5), xytext=(8.15, 4.5), arrowprops=arrow_kw)
ax.annotate("", xy=(13.6, 1.5), xytext=(13.15, 1.5), arrowprops=arrow_kw)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=140, bbox_inches="tight")
plt.close(fig)
print(f"-> {OUT}")
