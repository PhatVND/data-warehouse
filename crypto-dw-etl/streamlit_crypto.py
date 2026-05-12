"""
streamlit_crypto.py — CryptoDW Dashboard (UI v2)
Modernised UI: glassmorphism cards · brand colours per coin · sticky header.
Data loaders unchanged so streamlit_crypto_csv.py wrapper still works.

Run:
    streamlit run streamlit_crypto.py            # PostgreSQL mode
    streamlit run streamlit_crypto_csv.py        # CSV mode
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CryptoDW · Analytics",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand palette ─────────────────────────────────────────────────────────────
BG          = "#0a0e14"
SURFACE     = "#0f1419"
SURFACE_2   = "#161b22"
BORDER      = "#1f2937"
TEXT        = "#e6edf3"
MUTED       = "#7d8590"
ACCENT      = "#58a6ff"
GREEN       = "#3fb950"
RED         = "#f85149"
YELLOW      = "#f7c948"
PURPLE      = "#bc8cff"

# Per-coin colour (official brand-ish)
COIN_COLOR = {
    "BTC":   "#F7931A",
    "ETH":   "#627EEA",
    "BNB":   "#F3BA2F",
    "SOL":   "#14F195",
    "XRP":   "#23292F",
    "ADA":   "#0033AD",
    "DOGE":  "#C2A633",
    "TRX":   "#FF060A",
    "DOT":   "#E6007A",
    "MATIC": "#8247E5",
}

PLOTLY_THEME = "plotly_dark"

# ── CSS styling ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ===== Global ===== */
[data-testid="stAppViewContainer"] {{
    background:
      radial-gradient(circle at 0% 0%,  rgba(88,166,255,.06) 0%, transparent 50%),
      radial-gradient(circle at 100% 0%, rgba(247,147,26,.06) 0%, transparent 50%),
      {BG};
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 1.2rem; }}

/* ===== Hero header ===== */
.hero {{
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(135deg, rgba(88,166,255,.12), rgba(247,147,26,.10));
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 18px 28px;
    margin: 4px 0 22px 0;
    backdrop-filter: blur(8px);
}}
.hero-left {{ display: flex; align-items: center; gap: 16px; }}
.hero-logo {{
    font-size: 2.2rem; line-height: 1;
    background: linear-gradient(135deg, {ACCENT}, {YELLOW});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800;
}}
.hero-title h1 {{
    margin: 0; color: {TEXT}; font-size: 1.55rem;
    font-weight: 700; letter-spacing: -.02em;
}}
.hero-title p {{ margin: 2px 0 0 0; color: {MUTED}; font-size: .9rem; }}
.hero-right {{ display: flex; align-items: center; gap: 16px; }}
.status-pill {{
    display: flex; align-items: center; gap: 8px;
    background: rgba(63,185,80,.12); border: 1px solid {GREEN};
    border-radius: 999px; padding: 6px 14px;
    color: {GREEN}; font-size: .82rem; font-weight: 600;
}}
.status-pill::before {{
    content: ''; width: 8px; height: 8px; border-radius: 50%;
    background: {GREEN}; box-shadow: 0 0 8px {GREEN};
    animation: pulse 1.6s ease-in-out infinite;
}}
@keyframes pulse {{
    0%,100% {{ opacity: 1; }} 50% {{ opacity: .4; }}
}}

/* ===== KPI cards ===== */
.kpi-grid {{
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 14px; margin-bottom: 22px;
}}
.kpi {{
    background: linear-gradient(135deg, {SURFACE_2} 0%, {SURFACE} 100%);
    border: 1px solid {BORDER}; border-radius: 14px;
    padding: 16px 18px; position: relative; overflow: hidden;
    transition: transform .15s ease, border-color .15s ease;
}}
.kpi:hover {{ transform: translateY(-2px); border-color: {ACCENT}; }}
.kpi::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--accent, {ACCENT}), transparent);
}}
.kpi-label {{
    color: {MUTED}; font-size: .72rem; letter-spacing: .12em;
    font-weight: 600; text-transform: uppercase; margin-bottom: 6px;
}}
.kpi-value {{
    color: {TEXT}; font-size: 1.55rem; font-weight: 700;
    letter-spacing: -.01em; line-height: 1.1;
}}
.kpi-sub {{ color: {MUTED}; font-size: .78rem; margin-top: 4px; }}
.kpi-sub.up   {{ color: {GREEN}; }}
.kpi-sub.down {{ color: {RED};   }}

/* ===== Section headers ===== */
.sec {{
    display: flex; align-items: center; gap: 10px;
    margin: 26px 0 12px 0;
}}
.sec-bar {{
    width: 4px; height: 22px; border-radius: 4px;
    background: linear-gradient(180deg, {ACCENT}, {PURPLE});
}}
.sec h3 {{
    margin: 0; color: {TEXT}; font-size: 1.05rem;
    font-weight: 600; letter-spacing: -.01em;
}}
.sec .desc {{ color: {MUTED}; font-size: .85rem; margin-left: auto; }}

/* ===== Tabs ===== */
[data-baseweb="tab-list"] {{
    gap: 4px !important; background: transparent !important;
    border-bottom: 1px solid {BORDER} !important;
}}
[data-baseweb="tab"] {{
    background: transparent !important;
    color: {MUTED} !important;
    border-radius: 10px 10px 0 0 !important;
    padding: 10px 18px !important;
    font-weight: 500 !important;
    transition: all .15s ease;
}}
[data-baseweb="tab"]:hover {{ color: {TEXT} !important; background: rgba(88,166,255,.06) !important; }}
[aria-selected="true"][data-baseweb="tab"] {{
    color: {ACCENT} !important;
    background: rgba(88,166,255,.10) !important;
    border-bottom: 2px solid {ACCENT} !important;
}}

/* ===== Misc ===== */
.stPlotlyChart, [data-testid="stDataFrame"] {{
    background: {SURFACE_2}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 6px;
}}
hr {{ border-color: {BORDER}; }}
[data-testid="stMarkdownContainer"] code {{
    background: rgba(88,166,255,.10);
    color: {ACCENT}; padding: 2px 6px; border-radius: 4px; font-size: .9em;
}}
/* Sidebar items */
.sb-section {{
    color: {MUTED}; font-size: .68rem; letter-spacing: .14em;
    text-transform: uppercase; font-weight: 700; margin: 18px 0 6px 0;
}}
.sb-meta {{
    background: {SURFACE_2}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 10px 12px; margin-top: 14px;
}}
.sb-meta .row {{ display: flex; justify-content: space-between;
                  font-size: .78rem; color: {MUTED}; padding: 3px 0; }}
.sb-meta .row b {{ color: {TEXT}; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)


# ── Plotly default layout helper ──────────────────────────────────────────────
def _layout(fig, height=380, title=None, legend_top=True):
    fig.update_layout(
        template=PLOTLY_THEME,
        height=height,
        margin=dict(l=10, r=10, t=46 if title else 18, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT, size=12),
        title=dict(text=title, x=0.01, y=0.97, font=dict(size=14, color=TEXT))
            if title else None,
        legend=dict(
            orientation="h", y=1.05 if legend_top else -.12, x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        ),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    )
    return fig


# ── DB connection ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to PostgreSQL…")
def get_engine():
    def _env(path):
        cfg = {}
        for p in [path, path.replace(".env", ".env.example")]:
            if os.path.exists(p):
                for line in open(p, encoding="utf-8"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip()
                break
        return cfg

    e = _env(".env")
    dsn = (
        f"postgresql+psycopg2://{e.get('PG_USER','crypto_etl')}"
        f":{e.get('PG_PASSWORD','crypto_etl')}"
        f"@{e.get('PG_HOST','127.0.0.1')}"
        f":{e.get('PG_PORT','5432')}"
        f"/{e.get('PG_DATABASE','crypto_dw_etl')}"
    )
    return create_engine(dsn, pool_pre_ping=True)


# ── Data loaders (PostgreSQL mode — wrapper monkey-patches these) ─────────────
@st.cache_data(ttl=300, show_spinner="Loading market data…")
def load_fact() -> pd.DataFrame:
    sql = """
    SELECT d.full_date, d.year, d.month, d.week, d.quarter,
           c.symbol, c.full_name, cat.category_name, cat.risk_level,
           f.open, f.high, f.low, f.close,
           f.volume_base, f.volume_usd, f.return_pct, f.log_return,
           f.volatility, f.average_price, f.z_score_close,
           f.is_anomaly, f.volume_rank, f.market_dominance_pct, f.regime_label
    FROM gold.fact_market_daily f
    JOIN gold.dim_date d   ON d.date_id  = f.date_id
    JOIN gold.dim_coin c   ON c.coin_id  = f.coin_id
    JOIN gold.dim_category cat ON cat.category_id = f.category_id
    ORDER BY c.symbol, d.full_date
    """
    return pd.read_sql(sql, get_engine(), parse_dates=["full_date"])


@st.cache_data(ttl=300)
def load_weekly() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM gold.v_weekly_return_by_category ORDER BY year, week",
        get_engine(), parse_dates=["week_start_date", "week_end_date"],
    )


@st.cache_data(ttl=300)
def load_anomalies() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM gold.v_top_anomalies ORDER BY abs_z_score_close DESC",
        get_engine(), parse_dates=["full_date"],
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
def sidebar(df: pd.DataFrame):
    st.sidebar.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"padding-bottom:14px;border-bottom:1px solid {BORDER};'>"
        f"<div style='font-size:1.6rem'>₿</div>"
        f"<div><div style='color:{TEXT};font-weight:700;font-size:1.05rem'>CryptoDW</div>"
        f"<div style='color:{MUTED};font-size:.72rem'>Data Warehouse · ETL</div></div>"
        f"</div>", unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sb-section">Coins</div>', unsafe_allow_html=True)
    all_symbols = sorted(df["symbol"].unique())

    # Quick presets
    preset = st.sidebar.radio(
        "Preset", ["All", "Top 5 by Volume", "L1 only", "Custom"],
        horizontal=False, label_visibility="collapsed", key="preset",
    )
    if preset == "All":
        default_coins = all_symbols
    elif preset == "Top 5 by Volume":
        default_coins = (df.groupby("symbol")["volume_usd"].mean()
                          .nlargest(5).index.tolist())
    elif preset == "L1 only":
        default_coins = sorted(df[df["category_name"] == "L1"]["symbol"].unique())
    else:
        default_coins = all_symbols

    selected = st.sidebar.multiselect(
        "Select coins", all_symbols, default=default_coins,
        key="coins", label_visibility="collapsed",
    )

    st.sidebar.markdown('<div class="sb-section">Date Range</div>', unsafe_allow_html=True)
    min_d, max_d = df["full_date"].min().date(), df["full_date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_d, max_d),
        min_value=min_d, max_value=max_d, key="dates",
        label_visibility="collapsed",
    )

    # Meta
    st.sidebar.markdown(
        f'<div class="sb-meta">'
        f'<div class="row"><span>Gold layer</span><b>{len(df):,} rows</b></div>'
        f'<div class="row"><span>Coins</span><b>{df["symbol"].nunique()}</b></div>'
        f'<div class="row"><span>Days</span><b>{(max_d - min_d).days:,}</b></div>'
        f'<div class="row"><span>Refresh</span><b>{pd.Timestamp.now().strftime("%H:%M:%S")}</b></div>'
        f'</div>', unsafe_allow_html=True)

    start = pd.Timestamp(date_range[0]) if len(date_range) > 0 else pd.Timestamp(min_d)
    end   = pd.Timestamp(date_range[1]) if len(date_range) > 1 else pd.Timestamp(max_d)
    return selected, start, end


def apply_filters(df, symbols, start, end):
    return df[(df["symbol"].isin(symbols)) &
              (df["full_date"] >= start) &
              (df["full_date"] <= end)].copy()


# ── Hero + KPI ────────────────────────────────────────────────────────────────
def hero():
    st.markdown(
        f"""
<div style="
    display:flex; align-items:center; justify-content:space-between;
    background: linear-gradient(135deg, rgba(88,166,255,.18), rgba(247,147,26,.12));
    border:1px solid {BORDER}; border-radius:16px;
    padding:20px 28px; margin:6px 0 18px 0;">
  <div style="display:flex; align-items:center; gap:18px;">
    <div style="font-size:2.4rem; font-weight:800;
                background:linear-gradient(135deg,{ACCENT},{YELLOW});
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;">₿</div>
    <div>
      <div style="color:{TEXT}; font-size:1.6rem; font-weight:700;
                  letter-spacing:-.02em; line-height:1.1;">CryptoDW Analytics</div>
      <div style="color:{MUTED}; font-size:.88rem; margin-top:3px;">
        Cryptocurrency Data Warehouse · Gold Layer · Star Schema
      </div>
    </div>
  </div>
  <div style="display:flex; align-items:center; gap:8px;
              background:rgba(63,185,80,.15); border:1px solid {GREEN};
              border-radius:999px; padding:6px 14px;
              color:{GREEN}; font-weight:600; font-size:.82rem;">
    <span style="width:8px;height:8px;border-radius:50%;
                 background:{GREEN};box-shadow:0 0 8px {GREEN};"></span>
    Live
  </div>
</div>
""", unsafe_allow_html=True)


def _kpi_card(col, label, value, sub, sub_color, accent):
    col.markdown(
        f"""
<div style="
    background: linear-gradient(135deg,{SURFACE_2} 0%,{SURFACE} 100%);
    border:1px solid {BORDER}; border-radius:14px;
    padding:14px 18px; position:relative; overflow:hidden;
    border-top:3px solid {accent};">
  <div style="color:{MUTED}; font-size:.7rem; letter-spacing:.12em;
              font-weight:600; text-transform:uppercase; margin-bottom:6px;">{label}</div>
  <div style="color:{TEXT}; font-size:1.5rem; font-weight:700;
              line-height:1.1; letter-spacing:-.01em;">{value}</div>
  <div style="color:{sub_color}; font-size:.78rem; margin-top:4px;">{sub}</div>
</div>
""", unsafe_allow_html=True)


def kpi_row(df: pd.DataFrame):
    total_vol  = df["volume_usd"].sum()
    avg_return = df["return_pct"].mean()
    n_anomaly  = int(df["is_anomaly"].sum())
    n_bull     = int((df["regime_label"] == "Bull").sum())
    n_bear     = int((df["regime_label"] == "Bear").sum())
    days       = df["full_date"].nunique()

    arrow = "▲" if avg_return >= 0 else "▼"
    ret_color = GREEN if avg_return >= 0 else RED

    cols = st.columns(5, gap="small")
    _kpi_card(cols[0], "Total Volume", f"${total_vol/1e9:,.1f}B",
              f"{days:,} trading days", MUTED, ACCENT)
    _kpi_card(cols[1], "Avg Daily Return", f"{avg_return:+.3f}%",
              f"{arrow} all-coin mean", ret_color, ret_color)
    _kpi_card(cols[2], "Anomaly Days", f"{n_anomaly:,}",
              f"{n_anomaly/len(df)*100:.1f}% of rows", YELLOW, YELLOW)
    _kpi_card(cols[3], "Bull / Bear", f"{n_bull:,} / {n_bear:,}",
              "Regime split", MUTED, PURPLE)
    _kpi_card(cols[4], "Coins", f"{df['symbol'].nunique()}",
              "Currently selected", MUTED, "#14F195")
    st.markdown("<div style='margin-bottom:14px'></div>", unsafe_allow_html=True)


def section(title: str, desc: str = ""):
    desc_html = (f'<div style="color:{MUTED}; font-size:.85rem;'
                 f' margin-left:auto;">{desc}</div>') if desc else ""
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:10px; '
        f'margin:22px 0 8px 0;">'
        f'<div style="width:4px; height:22px; border-radius:4px; '
        f'background:linear-gradient(180deg,{ACCENT},{PURPLE});"></div>'
        f'<div style="color:{TEXT}; font-size:1.05rem; '
        f'font-weight:600; letter-spacing:-.01em;">{title}</div>'
        f'{desc_html}'
        f'</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ═══════════════════════════════════════════════════════════════════════════════
def tab_overview(df: pd.DataFrame):
    section("Price Trend", "Normalised close price across selected coins")

    df_norm = df.copy().sort_values("full_date")
    df_norm["close_norm"] = df_norm.groupby("symbol")["close"].transform(
        lambda s: s / s.iloc[0]
    )
    fig = px.line(
        df_norm, x="full_date", y="close_norm", color="symbol",
        color_discrete_map=COIN_COLOR,
        labels={"close_norm": "Normalised Close", "full_date": ""},
    )
    fig.update_traces(line=dict(width=1.7))
    st.plotly_chart(_layout(fig, height=420), use_container_width=True)

    col1, col2 = st.columns([1.2, 1])
    with col1:
        section("Regime Distribution")
        regime_cnt = df.groupby(["symbol", "regime_label"]).size().reset_index(name="days")
        fig2 = px.bar(
            regime_cnt, x="symbol", y="days", color="regime_label",
            barmode="stack",
            color_discrete_map={"Bull": GREEN, "Sideways": YELLOW, "Bear": RED},
            labels={"days": "Trading Days", "regime_label": ""},
        )
        st.plotly_chart(_layout(fig2, height=340), use_container_width=True)

    with col2:
        section("Market Dominance")
        dom = df.groupby("symbol")["volume_usd"].sum().reset_index()
        fig3 = go.Figure(go.Pie(
            labels=dom["symbol"], values=dom["volume_usd"], hole=0.62,
            marker=dict(colors=[COIN_COLOR.get(s, ACCENT) for s in dom["symbol"]],
                        line=dict(color=BG, width=2)),
            textposition="outside", textinfo="label+percent",
            textfont=dict(color=TEXT, size=11),
        ))
        fig3.add_annotation(text=f"<b>${dom['volume_usd'].sum()/1e9:,.0f}B</b><br>"
                                 f"<span style='font-size:11px;color:{MUTED}'>Total Volume</span>",
                            x=0.5, y=0.5, showarrow=False, align="center",
                            font=dict(color=TEXT, size=15))
        st.plotly_chart(_layout(fig3, height=340), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Price & Volume
# ═══════════════════════════════════════════════════════════════════════════════
def tab_price(df: pd.DataFrame):
    available = sorted(df["symbol"].unique())
    coin = st.selectbox("Coin", available, key="price_coin",
                        format_func=lambda s: f"{s} — {df[df['symbol']==s]['full_name'].iloc[0]}")
    df_c = df[df["symbol"] == coin].sort_values("full_date")

    color = COIN_COLOR.get(coin, ACCENT)

    section(f"{coin} — Candlestick + Volume",
            f"Daily OHLCV on {len(df_c):,} sessions")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_c["full_date"], open=df_c["open"], high=df_c["high"],
        low=df_c["low"], close=df_c["close"],
        increasing_line_color=GREEN, decreasing_line_color=RED,
        increasing_fillcolor=GREEN, decreasing_fillcolor=RED,
        name=coin,
    ))
    fig.add_trace(go.Bar(
        x=df_c["full_date"], y=df_c["volume_usd"], yaxis="y2",
        name="Volume USD",
        marker_color=np.where(df_c["return_pct"] >= 0, GREEN, RED),
        opacity=0.35,
    ))
    fig.update_layout(
        yaxis=dict(title="Price (USD)", domain=[0.30, 1], gridcolor=BORDER),
        yaxis2=dict(title="Volume", domain=[0, 0.22], gridcolor=BORDER),
        xaxis=dict(rangeslider=dict(visible=False), gridcolor=BORDER),
    )
    st.plotly_chart(_layout(fig, height=560, title=None), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        section("Return Distribution")
        fig_h = px.histogram(
            df_c, x="return_pct", nbins=50,
            color_discrete_sequence=[color],
            labels={"return_pct": "Daily Return (%)"},
        )
        fig_h.add_vline(x=0,  line_dash="dot",  line_color=MUTED)
        fig_h.add_vline(x=3,  line_dash="dash", line_color=GREEN, annotation_text="+3%",
                        annotation_position="top right",
                        annotation=dict(font_color=GREEN))
        fig_h.add_vline(x=-3, line_dash="dash", line_color=RED, annotation_text="-3%",
                        annotation_position="top left",
                        annotation=dict(font_color=RED))
        st.plotly_chart(_layout(fig_h, height=320), use_container_width=True)

    with col2:
        section("Volatility (High − Low)")
        fig_v = px.area(
            df_c, x="full_date", y="volatility",
            color_discrete_sequence=[color],
            labels={"volatility": "Volatility (USD)", "full_date": ""},
        )
        fig_v.update_traces(line=dict(width=0.8), opacity=0.55)
        st.plotly_chart(_layout(fig_v, height=320), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Anomaly Detection
# ═══════════════════════════════════════════════════════════════════════════════
def tab_anomaly(df: pd.DataFrame, df_top: pd.DataFrame):
    available = sorted(df["symbol"].unique())
    coin = st.selectbox("Coin", available, key="anm_coin",
                        format_func=lambda s: f"{s} — {df[df['symbol']==s]['full_name'].iloc[0]}")
    df_c = df[df["symbol"] == coin].sort_values("full_date")
    df_c_anm = df_c[df_c["is_anomaly"]]

    color = COIN_COLOR.get(coin, ACCENT)

    section(f"{coin} — Z-Score Rolling 30d",
            f"{len(df_c_anm)} anomaly days · {len(df_c_anm)/len(df_c)*100:.1f}% of total")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_c["full_date"], y=df_c["z_score_close"], mode="lines",
        name="Z-Score", line=dict(color=color, width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=df_c_anm["full_date"], y=df_c_anm["z_score_close"], mode="markers",
        name="Anomaly (|z|>2)",
        marker=dict(color=RED, size=10, symbol="circle-open", line=dict(width=2)),
    ))
    fig.add_hrect(y0=-2, y1=2, fillcolor=GREEN, opacity=0.04, line_width=0)
    for thr in (2, -2):
        fig.add_hline(y=thr, line_dash="dash", line_color=YELLOW)
    st.plotly_chart(_layout(fig, height=440), use_container_width=True)

    col1, col2 = st.columns([1, 1.4])
    with col1:
        section("Anomaly Rate per Coin")
        rate = (
            df.groupby("symbol")["is_anomaly"]
              .agg(rate=lambda x: x.mean() * 100, count="sum")
              .reset_index().sort_values("rate", ascending=True)
        )
        fig2 = px.bar(
            rate, x="rate", y="symbol", orientation="h",
            color="rate", color_continuous_scale=["#5b1212", RED, YELLOW],
            labels={"rate": "Anomaly %", "symbol": ""},
        )
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(_layout(fig2, height=380), use_container_width=True)

    with col2:
        section("Top 10 Extreme Anomalies", "Sorted by |z|")
        top10 = df_top.head(10)[
            ["full_date", "symbol", "close", "return_pct",
             "abs_z_score_close", "regime_label"]
        ].copy()
        top10["full_date"] = top10["full_date"].dt.date
        top10.columns = ["Date", "Coin", "Close", "Return %", "|Z|", "Regime"]
        st.dataframe(
            top10.style.format({"Close": "${:,.2f}", "Return %": "{:+.2f}%", "|Z|": "{:.3f}"})
                       .map(lambda v: f"color: {RED}; font-weight: 600"
                            if isinstance(v, (int, float)) and v < 0 else "",
                            subset=["Return %"]),
            use_container_width=True, hide_index=True, height=380,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — OLAP Views
# ═══════════════════════════════════════════════════════════════════════════════
def tab_olap(df_weekly: pd.DataFrame, df: pd.DataFrame):
    section("Weekly Avg Return by Category", "L1 / L2 / Meme / Payment")
    fig = px.line(
        df_weekly, x="week_start_date", y="avg_return_pct",
        color="category_name", facet_col="category_name", facet_col_wrap=2,
        labels={"avg_return_pct": "Avg Return (%)", "week_start_date": ""},
        color_discrete_sequence=[ACCENT, GREEN, YELLOW, PURPLE],
    )
    fig.add_hline(y=0, line_dash="dot", line_color=MUTED)
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1],
                                                font=dict(color=TEXT, size=12)))
    st.plotly_chart(_layout(fig, height=460), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        section("Correlation Heatmap", "Pearson on daily returns")
        pivot_ret = df.pivot_table(index="full_date", columns="symbol",
                                    values="return_pct")
        corr = pivot_ret.corr()
        fig2 = px.imshow(
            corr, text_auto=".2f",
            color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        )
        st.plotly_chart(_layout(fig2, height=420), use_container_width=True)

    with col2:
        section("Volume Leaderboard", "Average daily")
        vol_avg = (df.groupby("symbol")["volume_usd"].mean()
                     .reset_index().sort_values("volume_usd", ascending=True))
        fig3 = px.bar(
            vol_avg, x="volume_usd", y="symbol", orientation="h",
            color="symbol", color_discrete_map=COIN_COLOR,
            labels={"volume_usd": "Avg Volume USD", "symbol": ""},
        )
        fig3.update_traces(texttemplate="$%{x:.2s}", textposition="outside",
                           textfont=dict(color=TEXT))
        fig3.update_layout(showlegend=False)
        st.plotly_chart(_layout(fig3, height=420), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Data Explorer
# ═══════════════════════════════════════════════════════════════════════════════
def tab_data(df: pd.DataFrame):
    section("Raw Data Explorer", f"Filter & download from {len(df):,} rows")

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        regime_filter = st.multiselect(
            "Regime", ["Bull", "Sideways", "Bear"],
            default=["Bull", "Sideways", "Bear"],
        )
    with col_f2:
        anomaly_only = st.checkbox("Anomaly only", value=False)
    with col_f3:
        st.markdown("")  # spacer

    df_show = df[df["regime_label"].isin(regime_filter)]
    if anomaly_only:
        df_show = df_show[df_show["is_anomaly"]]

    display_cols = [
        "full_date", "symbol", "open", "high", "low", "close",
        "volume_usd", "return_pct", "z_score_close", "is_anomaly", "regime_label",
    ]
    st.dataframe(
        df_show[display_cols]
            .sort_values(["symbol", "full_date"])
            .style.format({
                "open": "${:.4f}", "high": "${:.4f}", "low": "${:.4f}",
                "close": "${:.4f}", "volume_usd": "${:,.0f}",
                "return_pct": "{:+.4f}%", "z_score_close": "{:+.3f}",
            })
            .map(lambda v: f"color: {RED}; font-weight: 600"
                 if v is True else "", subset=["is_anomaly"]),
        use_container_width=True, height=500, hide_index=True,
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        st.metric("Filtered", f"{len(df_show):,}")
    with col2:
        csv = df_show[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Download filtered CSV", csv,
            file_name="crypto_gold_filtered.csv", mime="text/csv",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    hero()

    try:
        df_fact    = load_fact()
        df_weekly  = load_weekly()
        df_top_anm = load_anomalies()
    except Exception as e:
        st.error(f"❌ Cannot load data: {e}")
        st.info("Make sure PostgreSQL is running and pipeline has been executed, "
                "or use streamlit_crypto_csv.py for CSV mode.")
        st.stop()

    selected_coins, start_date, end_date = sidebar(df_fact)
    df = apply_filters(df_fact, selected_coins, start_date, end_date)

    if df.empty:
        st.warning("No data for selected filters. Adjust coin or date range.")
        st.stop()

    kpi_row(df)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊  Overview",
        "🕯  Price & Volume",
        "🚨  Anomaly Detection",
        "🔍  OLAP Views",
        "📋  Data Explorer",
    ])
    with tab1: tab_overview(df)
    with tab2: tab_price(df)
    with tab3: tab_anomaly(df, df_top_anm)
    with tab4: tab_olap(df_weekly, df)
    with tab5: tab_data(df)


if __name__ == "__main__":
    main()
