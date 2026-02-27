# -*- coding: utf-8 -*-
"""
HCMC Air Quality Monitoring Dashboard
2 tabs: Dashboard (city overview + per-station cards) | EDA (charts & analysis)
Design: Dark navy theme matching Figma mockup
"""

from datetime import date, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─────────────────────────────────────────────────────────────
# PATHS  ← chỉnh nếu cần
# ─────────────────────────────────────────────────────────────
CITY_CSV     = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"
STATIONS_CSV = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
NON_AQI = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
ALL_COL  = ["AQI"] + NON_AQI

AQI_BANDS = [
    (0,   50,  "#22c55e", "Good"),
    (51,  100, "#eab308", "Moderate"),
    (101, 150, "#f97316", "USG"),
    (151, 200, "#ef4444", "Unhealthy"),
    (201, 300, "#a855f7", "Very Unhealthy"),
    (301, 999, "#7f1d1d", "Hazardous"),
]

# ─────────────────────────────────────────────────────────────
# CSS — dark navy, Figma-faithful
# ─────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Reset & base ── */
html, body, [data-testid="stApp"] {
    background: #0d1117 !important;
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stAppViewContainer"] { padding-top: 0 !important; }
[data-testid="stMainBlockContainer"] { padding: 0 1.5rem 2rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none; }

/* ── Top navbar ── */
.navbar {
    position: sticky; top: 0; z-index: 200;
    background: #161b22;
    border-bottom: 1px solid #21262d;
    padding: 0 28px;
    height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 -1.5rem 0;
}
.navbar-left { display: flex; align-items: center; gap: 10px; }
.navbar-logo {
    color: #58a6ff;
    font-size: 20px;
    font-weight: 700;
}
.navbar-brand {
    color: #e2e8f0;
    font-size: 14px;
    font-weight: 600;
}
.navbar-right { display: flex; align-items: center; gap: 8px; }
.nav-btn {
    background: none; border: 1px solid #30363d;
    color: #8b949e; font-size: 13px; font-family: 'Inter', sans-serif;
    padding: 6px 14px; border-radius: 6px; cursor: pointer;
    transition: all 0.15s;
}
.nav-btn:hover { background: #21262d; color: #e2e8f0; }
.nav-btn-primary {
    background: #1f6feb; border: 1px solid #1f6feb;
    color: #fff; font-size: 13px; font-family: 'Inter', sans-serif;
    padding: 6px 14px; border-radius: 6px; cursor: pointer;
    font-weight: 600;
}

/* ── Page hero ── */
.page-hero {
    padding: 32px 0 24px;
}
.page-hero h1 {
    font-size: 32px; font-weight: 800;
    color: #f0f6fc; margin: 0 0 6px;
    line-height: 1.2;
}
.page-hero p {
    font-size: 14px; color: #8b949e; margin: 0;
}

/* ── KPI cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 32px;
}
.kpi-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 24px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}
.kpi-label {
    font-size: 11px; font-weight: 600;
    letter-spacing: 1.2px; color: #8b949e;
    text-transform: uppercase; margin-bottom: 10px;
}
.kpi-number {
    font-size: 40px; font-weight: 800;
    color: #f0f6fc; line-height: 1;
    font-family: 'JetBrains Mono', monospace;
}
.kpi-badge {
    display: inline-block;
    font-size: 11px; font-weight: 600;
    padding: 3px 10px; border-radius: 20px;
    margin-top: 8px;
    border: 1px solid;
}
.kpi-icon {
    font-size: 22px;
    opacity: 0.7;
    margin-top: 2px;
}

/* ── Section heading ── */
.section-heading {
    font-size: 20px; font-weight: 700;
    color: #f0f6fc; margin: 0 0 16px;
}

/* ── Station cards grid ── */
.station-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 32px;
}
.station-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 22px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.station-card:hover {
    border-color: #388bfd44;
    box-shadow: 0 0 0 1px #388bfd22;
}
.station-card-header {
    display: flex; justify-content: space-between;
    align-items: flex-start; margin-bottom: 4px;
}
.station-name {
    font-size: 15px; font-weight: 700;
    color: #f0f6fc;
}
.station-addr {
    font-size: 12px; color: #6e7681;
    margin-bottom: 14px;
}
.station-aqi {
    font-size: 48px; font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    color: #f0f6fc; line-height: 1; margin-bottom: 6px;
}
.station-badge {
    display: inline-block;
    font-size: 11px; font-weight: 700;
    padding: 3px 12px; border-radius: 20px;
    margin-bottom: 16px;
    border: 1px solid;
}
.station-divider {
    height: 1px; background: #21262d;
    margin-bottom: 14px;
}
.pollutant-row {
    display: flex; gap: 24px;
}
.pollutant-item { }
.pollutant-label {
    font-size: 11px; color: #6e7681;
    font-weight: 500; margin-bottom: 2px;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.pollutant-value {
    font-size: 16px; font-weight: 700;
    color: #e2e8f0;
    font-family: 'JetBrains Mono', monospace;
}
.live-badge {
    background: #1a2f1a; color: #3fb950;
    border: 1px solid #238636;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px;
    letter-spacing: 0.5px;
}
.no-data-badge {
    background: #1c1f24; color: #6e7681;
    border: 1px solid #30363d;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px;
}

/* ── EDA section ── */
.eda-hero { padding: 32px 0 20px; }
.eda-hero h1 { font-size: 32px; font-weight: 800; color: #f0f6fc; margin: 0 0 6px; }
.eda-hero p  { font-size: 14px; color: #8b949e; margin: 0 0 20px; }
.eda-toolbar {
    display: flex; align-items: center; gap: 10px;
    flex-wrap: wrap; margin-bottom: 24px;
}
.filter-chip {
    background: #1c2128; border: 1px solid #30363d;
    color: #e2e8f0; font-size: 13px; font-weight: 500;
    padding: 6px 14px; border-radius: 6px;
}
.ref-label { font-size: 12px; color: #6e7681; margin-right: 4px; }
.ref-good     { color: #3fb950; font-weight: 600; font-size: 12px; }
.ref-moderate { color: #d29922; font-weight: 600; font-size: 12px; }
.ref-unhealthy{ color: #f85149; font-weight: 600; font-size: 12px; }

.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 24px;
}
.stat-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 18px 20px;
}
.stat-label { font-size: 13px; color: #8b949e; margin-bottom: 8px; display: flex; justify-content: space-between; }
.stat-value { font-size: 32px; font-weight: 800; font-family: 'JetBrains Mono', monospace; color: #f0f6fc; line-height: 1; margin-bottom: 4px; }
.stat-delta-pos { font-size: 12px; font-weight: 600; color: #3fb950; background: #1a2f1a; padding: 1px 6px; border-radius: 4px; }
.stat-delta-neg { font-size: 12px; font-weight: 600; color: #f85149; background: #2d1214; padding: 1px 6px; border-radius: 4px; }
.stat-sub { font-size: 11px; color: #6e7681; }

.chart-panel {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 16px;
}
.chart-panel-title {
    font-size: 16px; font-weight: 700;
    color: #f0f6fc; margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
}
.chart-panel-sub { font-size: 12px; color: #6e7681; margin-bottom: 16px; }

/* ── Tab switcher ── */
.tab-bar {
    display: flex; gap: 0;
    border-bottom: 1px solid #21262d;
    margin-bottom: 0;
}
.tab-item {
    font-size: 14px; font-weight: 500;
    padding: 10px 18px;
    cursor: pointer;
    color: #8b949e;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: color 0.15s;
}
.tab-item.active {
    color: #58a6ff;
    border-bottom-color: #58a6ff;
    font-weight: 600;
}
.tab-item:hover { color: #e2e8f0; }

/* Streamlit widget overrides */
.stSelectbox > label, .stMultiSelect > label,
.stDateInput > label, .stRadio > label { color: #8b949e !important; font-size: 12px !important; }
div[data-baseweb="select"] { background: #1c2128 !important; }
div[data-baseweb="select"] * { color: #e2e8f0 !important; }
.stRadio [data-baseweb="radio"] { color: #e2e8f0 !important; }
</style>
"""

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _num(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def aqi_info(v) -> tuple:
    """Returns (category_str, hex_color) for an AQI value."""
    try:
        val = float(v)
        if np.isnan(val):
            return "N/A", "#6e7681"
    except Exception:
        return "N/A", "#6e7681"
    for lo, hi, color, label in AQI_BANDS:
        if lo <= val <= hi:
            return label, color
    return "N/A", "#6e7681"


def _fmt(v, dec: int = 1) -> str:
    try:
        f = float(v)
        return f"{f:.{dec}f}" if not np.isnan(f) else "—"
    except Exception:
        return "—"


def _corr(df: pd.DataFrame, x: str, y: str) -> float:
    t = df[[x, y]].dropna()
    return float(t[x].corr(t[y])) if len(t) >= 3 else float("nan")


def _iqr_outliers(s: pd.Series) -> int:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())


# ─────────────────────────────────────────────────────────────
# PREPROCESS
# ─────────────────────────────────────────────────────────────

def load_city() -> pd.DataFrame:
    df = pd.read_csv(CITY_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = _num(df, ALL_COL)
    return df.sort_values("date").reset_index(drop=True)


def load_stations() -> pd.DataFrame:
    df = pd.read_csv(STATIONS_CSV)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    if "station_name" not in df.columns:
        df["station_name"] = df["station_slug"]
    df = _num(df, ALL_COL)
    return df.sort_values(["station_name", "date"]).reset_index(drop=True)


@st.cache_data(ttl=600)
def get_city() -> pd.DataFrame:    return load_city()

@st.cache_data(ttl=600)
def get_stations() -> pd.DataFrame: return load_stations()


# ─────────────────────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────────────────────
_P = dict(
    paper_bgcolor="#161b22",
    plot_bgcolor="#0d1117",
    font=dict(family="Inter, sans-serif", color="#8b949e", size=11),
    margin=dict(l=8, r=8, t=8, b=8),
    legend=dict(bgcolor="#161b22", bordercolor="#21262d", borderwidth=1,
                font=dict(size=10, color="#e2e8f0")),
)
_A = dict(gridcolor="#21262d", zeroline=False,
          linecolor="#30363d", tickfont=dict(size=9, color="#6e7681"))
_CFG = dict(displayModeBar=False)


def _theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**_P)
    fig.update_xaxes(**_A)
    fig.update_yaxes(**_A)
    return fig


# ─────────────────────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────────────────────

def chart_city_trend(df: pd.DataFrame) -> go.Figure:
    v = df[["date", "AQI"]].dropna().sort_values("date")
    r = v.set_index("date")["AQI"].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    for lo, hi, c, _ in AQI_BANDS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.06, layer="below", line_width=0)
    fig.add_trace(go.Scatter(
        x=v["date"], y=v["AQI"], name="AQI Daily",
        mode="lines", line=dict(color="#58a6ff", width=1.2), opacity=0.5,
    ))
    fig.add_trace(go.Scatter(
        x=r["date"], y=r["AQI"], name="7-day MA",
        mode="lines", line=dict(color="#f0f6fc", width=2.5),
    ))
    _theme(fig)
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
        yaxis_title="AQI",
    )
    return fig


def chart_station_detail(df: pd.DataFrame, station: str) -> go.Figure:
    sub = df[df["station_name"] == station][["date", "AQI"]].dropna().sort_values("date")
    if sub.empty:
        return go.Figure()
    roll = sub.set_index("date")["AQI"].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    for lo, hi, c, _ in AQI_BANDS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.07, layer="below", line_width=0)
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["AQI"], name="AQI Daily",
        mode="lines", line=dict(color="#58a6ff", width=1.2), opacity=0.5,
    ))
    fig.add_trace(go.Scatter(
        x=roll["date"], y=roll["AQI"], name="7-day MA",
        mode="lines", line=dict(color="#f0f6fc", width=2.5),
    ))
    _theme(fig)
    fig.update_layout(hovermode="x unified", yaxis_title="AQI",
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    return fig


def chart_aqi_freq(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: count of days in each AQI category."""
    cats  = df["AQI"].dropna().apply(lambda x: aqi_info(x)[0]).value_counts()
    order = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
    cats  = cats.reindex([c for c in order if c in cats.index])
    colors = [next((c for _, _, c, l in AQI_BANDS if l == k), "#6e7681") for k in cats.index]
    fig = go.Figure(go.Bar(
        x=cats.values, y=cats.index, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=cats.values, textposition="outside",
        textfont=dict(color="#e2e8f0", size=10),
        hovertemplate="%{y}: %{x} ngày<extra></extra>",
    ))
    _theme(fig)
    fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
    return fig


def chart_scatter_corr(df: pd.DataFrame, x_col: str, y_col: str,
                       trendline: bool = True) -> go.Figure:
    if x_col not in df.columns or y_col not in df.columns:
        return go.Figure()
    tmp = df[[x_col, y_col, "AQI"]].dropna().copy()
    if tmp.empty:
        return go.Figure()
    tmp["cat"] = tmp["AQI"].apply(lambda v: aqi_info(v)[0])
    clr = {l: c for _, _, c, l in AQI_BANDS}

    fig = px.scatter(
        tmp, x=x_col, y=y_col, color="cat",
        category_orders={"cat": ["Good","Moderate","USG","Unhealthy","Very Unhealthy","Hazardous"]},
        color_discrete_map=clr,
        opacity=0.7,
        trendline="ols" if trendline else None,
    )
    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
    r = _corr(tmp, x_col, y_col)
    _theme(fig)
    fig.update_layout(
        legend=dict(title=None, font=dict(size=10)),
        annotations=[dict(
            x=0.02, y=0.97, xref="paper", yref="paper",
            text=f"r = {r:.3f}" if not np.isnan(r) else "r = N/A",
            showarrow=False,
            font=dict(size=12, color="#58a6ff", family="JetBrains Mono"),
            bgcolor="#1c2128", bordercolor="#388bfd",
            borderwidth=1, borderpad=6,
        )],
    )
    return fig


def chart_pollutant_time(df: pd.DataFrame, col: str) -> go.Figure:
    tmp = df[["date", col]].dropna().sort_values("date")
    if tmp.empty:
        return go.Figure()
    roll = tmp.set_index("date")[col].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tmp["date"], y=tmp[col], name=col,
        mode="lines", line=dict(color="#58a6ff", width=1), opacity=0.45,
    ))
    fig.add_trace(go.Scatter(
        x=roll["date"], y=roll[col], name="7-day MA",
        mode="lines", line=dict(color="#f0f6fc", width=2.2),
    ))
    _theme(fig)
    fig.update_layout(
        hovermode="x unified", yaxis_title=col,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
    )
    return fig


def chart_heatmap_monthly(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"]  = tmp["date"].dt.year
    pivot = tmp.pivot_table(index="year", columns="month", values="AQI", aggfunc="mean")
    mlbls = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    xlbls = [mlbls[m - 1] for m in pivot.columns]
    zv = pivot.values.astype(float)
    txt = np.where(np.isnan(zv), "", np.round(zv, 0).astype("int").astype("str"))
    fig = go.Figure(go.Heatmap(
        z=zv, x=xlbls, y=[str(y) for y in pivot.index],
        colorscale=[[0,"#22c55e"],[0.25,"#eab308"],[0.5,"#f97316"],
                    [0.75,"#ef4444"],[1,"#7f1d1d"]],
        zmin=0, zmax=150,
        text=txt, texttemplate="%{text}",
        textfont=dict(size=10, color="#f0f6fc"),
        hovertemplate="Năm %{y} – %{x}: AQI %{z:.1f}<extra></extra>",
        showscale=True,
        colorbar=dict(thickness=10, len=0.85,
                      tickfont=dict(size=9, color="#8b949e"),
                      title=dict(text="AQI", font=dict(color="#8b949e", size=10))),
    ))
    _theme(fig)
    return fig


def chart_boxplot_stations(df: pd.DataFrame) -> go.Figure:
    order = (df.groupby("station_name")["AQI"].median()
               .dropna().sort_values(ascending=False).index)
    palette = ["#58a6ff","#3fb950","#e3b341","#f85149","#a371f7",
               "#79c0ff","#56d364","#ff7b72","#d2a8ff","#ffa657"]
    fig = go.Figure()
    for i, stn in enumerate(order):
        vals = df[df["station_name"] == stn]["AQI"].dropna()
        if len(vals) < 2:
            continue
        c = palette[i % len(palette)]
        short = stn[:22] + "…" if len(stn) > 22 else stn
        fig.add_trace(go.Box(
            x=vals, y=[short] * len(vals), name=short,
            orientation="h", boxmean=True,
            marker=dict(size=3, opacity=0.4, color=c),
            line=dict(color=c, width=1.5),
            hovertemplate=f"<b>{stn}</b><br>AQI: %{{x:.0f}}<extra></extra>",
        ))
    _theme(fig)
    fig.update_layout(showlegend=False, hovermode="closest",
                      yaxis=dict(autorange="reversed"))
    return fig


def chart_radar_station(df: pd.DataFrame, station: str) -> go.Figure:
    avail = [c for c in NON_AQI if c in df.columns and df[c].notna().sum() > 5]
    if len(avail) < 3:
        return go.Figure()
    sub   = df[df["station_name"] == station][avail].mean()
    all_m = df[avail].mean()
    # Normalize to 0-1 vs city average
    scale = all_m.replace(0, np.nan)
    norm_stn  = (sub  / scale).fillna(0).clip(0, 2)
    norm_city = (all_m / scale).fillna(0).clip(0, 2)
    cats = avail + [avail[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=norm_city.tolist() + [norm_city.iloc[0]],
        theta=cats, name="City Avg", fill="toself",
        opacity=0.3, line=dict(color="#6e7681", width=1.5),
        fillcolor="#6e768133",
    ))
    fig.add_trace(go.Scatterpolar(
        r=norm_stn.tolist() + [norm_stn.iloc[0]],
        theta=cats, name=station[:20], fill="toself",
        opacity=0.6, line=dict(color="#58a6ff", width=2),
        fillcolor="#58a6ff33",
    ))
    _theme(fig)
    fig.update_layout(
        polar=dict(
            bgcolor="#0d1117",
            radialaxis=dict(visible=True, range=[0, 2],
                            tickfont=dict(size=8, color="#6e7681"),
                            gridcolor="#21262d", linecolor="#21262d"),
            angularaxis=dict(tickfont=dict(size=9, color="#8b949e"),
                             gridcolor="#21262d"),
        ),
        legend=dict(font=dict(size=10)),
    )
    return fig


def chart_missing_heatmap(df: pd.DataFrame) -> go.Figure:
    """Missing data heatmap per station × pollutant."""
    poll = [c for c in ALL_COL if c in df.columns]
    miss = df.groupby("station_name")[poll].apply(lambda g: g.isna().mean() * 100)
    fig = go.Figure(go.Heatmap(
        z=miss.values, x=miss.columns.tolist(),
        y=[s[:22] + "…" if len(s) > 22 else s for s in miss.index],
        colorscale=[[0,"#1f6feb"],[0.5,"#e3b341"],[1,"#f85149"]],
        zmin=0, zmax=100,
        text=np.round(miss.values, 0).astype("int").astype("str"),
        texttemplate="%{text}%",
        textfont=dict(size=9, color="#f0f6fc"),
        hovertemplate="%{y} – %{x}: %{z:.1f}% missing<extra></extra>",
        showscale=True,
        colorbar=dict(thickness=10, ticksuffix="%",
                      tickfont=dict(size=9, color="#8b949e")),
    ))
    _theme(fig)
    return fig


def chart_yearly_trend(df_city: pd.DataFrame, df_st: pd.DataFrame) -> go.Figure:
    """Multi-line: yearly mean AQI — city + each station."""
    fig = go.Figure()
    palette = ["#58a6ff","#3fb950","#e3b341","#f85149","#a371f7",
               "#79c0ff","#56d364","#ff7b72","#d2a8ff"]

    # City
    cg = df_city.copy()
    cg["year"] = cg["date"].dt.year
    city_y = cg.groupby("year")["AQI"].mean().reset_index()
    fig.add_trace(go.Scatter(
        x=city_y["year"], y=city_y["AQI"], name="City (AQICN)",
        mode="lines+markers", line=dict(color="#f0f6fc", width=3),
        marker=dict(size=7),
    ))
    # Stations
    sg = df_st.copy()
    sg["year"] = sg["date"].dt.year
    for i, stn in enumerate(sg["station_name"].unique()):
        sub = sg[sg["station_name"] == stn].groupby("year")["AQI"].mean().reset_index()
        if sub["AQI"].notna().sum() < 2:
            continue
        short = stn[:20] + "…" if len(stn) > 20 else stn
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["AQI"], name=short,
            mode="lines+markers",
            line=dict(color=palette[i % len(palette)], width=1.5, dash="dot"),
            marker=dict(size=5),
        ))
    _theme(fig)
    fig.update_layout(
        hovermode="x unified",
        xaxis=dict(dtick=1),
        yaxis_title="AQI moyen annuel",
        legend=dict(font=dict(size=10)),
    )
    return fig


# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Air Quality Monitoring – HCMC",
    page_icon="🌫️", layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────
with st.spinner("Loading data..."):
    try:
        df_city = get_city()
    except Exception as e:
        st.error(f"Cannot load City CSV: {e}")
        st.stop()
    try:
        df_st = get_stations()
    except Exception as e:
        st.error(f"Cannot load Stations CSV: {e}")
        st.stop()

# ─────────────────────────────────────────────────────────────
# NAVBAR
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="navbar">
  <div class="navbar-left">
    <span class="navbar-logo">⇌</span>
    <span class="navbar-brand">Air Quality Monitoring – HCMC</span>
  </div>
  <div class="navbar-right">
    <button class="nav-btn">🔔 Notifications</button>
    <button class="nav-btn-primary">👤 Profile</button>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB SWITCHER
# ─────────────────────────────────────────────────────────────
tab = st.radio(
    label="tab",
    options=["Dashboard", "EDA"],
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("---")

# ═════════════════════════════════════════════════════════════
#  TAB 1 – DASHBOARD
# ═════════════════════════════════════════════════════════════
if tab == "Dashboard":

    # ── filters (inline above hero) ──
    with st.expander("🔧 Bộ lọc thời gian", expanded=False):
        min_d = df_city["date"].min().date()
        max_d = df_city["date"].max().date()
        d_range = st.date_input(
            "Khoảng thời gian",
            value=(date(2025, 1, 1), date.today()),
            min_value=min_d, max_value=max_d,
            key="dash_dates",
        )
        if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
            ts0, ts1 = pd.Timestamp(d_range[0]), pd.Timestamp(d_range[1])
        else:
            ts0, ts1 = pd.Timestamp(min_d), pd.Timestamp(max_d)

    df_cf = df_city[(df_city["date"] >= ts0) & (df_city["date"] <= ts1)].copy()
    df_sf = df_st[(df_st["date"] >= ts0)   & (df_st["date"] <= ts1)].copy()

    # ── Hero ──
    city_aqi_s = df_cf["AQI"].dropna()
    city_avg   = city_aqi_s.mean() if len(city_aqi_s) else None
    city_cat, city_color = aqi_info(city_avg)
    n_stations = df_sf["station_name"].nunique()
    n_unhealthy = int((df_sf.groupby("station_name")["AQI"].mean() > 100).sum())

    st.markdown(f"""
    <div class="page-hero">
      <h1>Ho Chi Minh City Air Quality Dashboard</h1>
      <p>Real-time air quality monitoring across {n_stations} monitoring stations in Ho Chi Minh City</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 3 KPI cards ──
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div>
          <div class="kpi-label">City Average AQI</div>
          <div class="kpi-number">{_fmt(city_avg, 0)}</div>
          <span class="kpi-badge" style="color:{city_color};border-color:{city_color}44;background:{city_color}15">{city_cat}</span>
        </div>
        <div class="kpi-icon">📈</div>
      </div>
      <div class="kpi-card">
        <div>
          <div class="kpi-label">Active Stations</div>
          <div class="kpi-number">{n_stations}</div>
          <span class="kpi-badge" style="color:#3fb950;border-color:#23863644;background:#1a2f1a">All Online</span>
        </div>
        <div class="kpi-icon">📍</div>
      </div>
      <div class="kpi-card">
        <div>
          <div class="kpi-label">Unhealthy Areas</div>
          <div class="kpi-number">{n_unhealthy}</div>
          <span class="kpi-badge" style="color:#f85149;border-color:#f8514944;background:#2d1214">AQI &gt; 100</span>
        </div>
        <div class="kpi-icon">⚠️</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── City trend chart ──
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-title">📈 City-level AQI Trend</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-sub">Daily AQI + 7-day rolling average from AQICN city index</div>', unsafe_allow_html=True)
    if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_city_trend(df_cf), use_container_width=True, config=_CFG)
    else:
        st.info("No city data in selected range.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Monitoring stations section ──
    st.markdown('<p class="section-heading">Monitoring Stations</p>', unsafe_allow_html=True)

    # Build per-station latest data
    station_meta = (df_st[["station_name", "latitude", "longitude"]]
                    .drop_duplicates("station_name")
                    .set_index("station_name"))
    stations = df_sf["station_name"].unique().tolist()

    def station_card_html(name: str, df_f: pd.DataFrame) -> str:
        sub = df_f[df_f["station_name"] == name].sort_values("date")
        has_data = sub["AQI"].notna().any()
        last = sub.dropna(subset=["AQI"]).tail(1)
        aqi_val  = float(last["AQI"].iloc[0]) if not last.empty else None
        cat, color = aqi_info(aqi_val)
        badge_html = f'<span class="live-badge">LIVE</span>' if has_data else '<span class="no-data-badge">NO DATA</span>'

        # Pollutants from latest row
        def poll(col):
            v = last[col].iloc[0] if not last.empty and col in last.columns and pd.notna(last[col].iloc[0]) else None
            return _fmt(v, 0) if v is not None else "—"

        pm25 = poll("PM2,5")
        pm10 = poll("PM10")
        o3   = poll("O3")

        aqi_str = _fmt(aqi_val, 0) if aqi_val else "—"
        cat_str = cat if cat != "N/A" else "—"

        return f"""
        <div class="station-card">
          <div class="station-card-header">
            <div class="station-name">{name}</div>
            {badge_html}
          </div>
          <div class="station-addr">Ho Chi Minh City</div>
          <div class="station-aqi">{aqi_str}</div>
          <span class="station-badge"
            style="color:{color};border-color:{color}55;background:{color}18">{cat_str}</span>
          <div class="station-divider"></div>
          <div class="pollutant-row">
            <div class="pollutant-item">
              <div class="pollutant-label">PM2.5</div>
              <div class="pollutant-value">{pm25}</div>
            </div>
            <div class="pollutant-item">
              <div class="pollutant-label">PM10</div>
              <div class="pollutant-value">{pm10}</div>
            </div>
            <div class="pollutant-item">
              <div class="pollutant-label">O3</div>
              <div class="pollutant-value">{o3}</div>
            </div>
          </div>
        </div>
        """

    # Render station cards in rows of 3
    for i in range(0, len(stations), 3):
        batch = stations[i:i+3]
        cols  = st.columns(len(batch))
        for col, stn in zip(cols, batch):
            with col:
                st.markdown(station_card_html(stn, df_sf), unsafe_allow_html=True)

    # ── Per-station detail expander ──
    st.markdown("---")
    st.markdown('<p class="section-heading">Station Detail View</p>', unsafe_allow_html=True)

    sel_station = st.selectbox(
        "Chọn trạm để xem chi tiết",
        stations,
        key="detail_station",
    )
    if sel_station:
        sub_st = df_sf[df_sf["station_name"] == sel_station]
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-panel-title">📈 AQI Trend – {sel_station}</div>',
                        unsafe_allow_html=True)
            fig = chart_station_detail(df_sf, sel_station)
            if fig.data:
                st.plotly_chart(fig, use_container_width=True, config=_CFG)
            else:
                st.info("No AQI data for this station in selected range.")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-panel-title">🕸️ Pollutant Profile vs City Avg</div>',
                        unsafe_allow_html=True)
            fig_r = chart_radar_station(df_sf, sel_station)
            if fig_r.data:
                st.plotly_chart(fig_r, use_container_width=True, config=_CFG)
            else:
                st.info("Insufficient pollutant data for radar.")
            st.markdown('</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════
#  TAB 2 – EDA
# ═════════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div class="eda-hero">
      <h1>Exploratory Data Analysis</h1>
      <p>Deep dive into pollutant correlations, frequency distributions, and station variances
         across Ho Chi Minh City's monitoring network.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── EDA Filters ──
    c_f1, c_f2, c_f3, c_f4 = st.columns([1.5, 1.5, 1.5, 3])
    with c_f1:
        eda_src = st.selectbox("Nguồn dữ liệu", ["City CSV", "Stations CSV", "Cả hai"], key="eda_src")
    with c_f2:
        min_d2 = df_city["date"].min().date()
        max_d2 = df_city["date"].max().date()
        d2 = st.date_input("Từ ngày", value=date(2022, 1, 1), min_value=min_d2, max_value=max_d2, key="eda_d0")
        d3 = st.date_input("Đến ngày", value=date.today(), min_value=min_d2, max_value=max_d2, key="eda_d1")
    with c_f3:
        poll_choice = st.selectbox("Chỉ số chính", ["AQI"] + NON_AQI, key="eda_poll")
    with c_f4:
        st.markdown("""
        <div style="padding-top:24px;font-size:12px;color:#6e7681;">
          <span class="ref-label">Reference:</span>
          <span class="ref-good">■ Good (0–50)</span>&nbsp;
          <span class="ref-moderate">■ Moderate (51–100)</span>&nbsp;
          <span class="ref-unhealthy">■ Unhealthy (&gt;150)</span>
        </div>""", unsafe_allow_html=True)

    ts_a, ts_b = pd.Timestamp(d2), pd.Timestamp(d3)
    df_ca = df_city[(df_city["date"] >= ts_a) & (df_city["date"] <= ts_b)].copy()
    df_sa = df_st[(df_st["date"] >= ts_a)   & (df_st["date"] <= ts_b)].copy()

    if eda_src == "City CSV":
        eda_df = df_ca
    elif eda_src == "Stations CSV":
        eda_df = df_sa
    else:
        eda_df = pd.concat([df_ca, df_sa], ignore_index=True)

    # ── Stat cards ──
    col_data = eda_df[poll_choice].dropna() if poll_choice in eda_df.columns else pd.Series(dtype=float)
    r_val    = _corr(eda_df, "PM2,5", "CO") if "PM2,5" in eda_df.columns and "CO" in eda_df.columns else float("nan")
    std_val  = col_data.std() if len(col_data) > 1 else float("nan")
    mean_val = col_data.mean() if len(col_data) else float("nan")
    n_samples = len(col_data)
    n_outliers = _iqr_outliers(col_data) if len(col_data) > 4 else 0

    st.markdown(f"""
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">Pearson Correlation (r) <span>📈</span></div>
        <div class="stat-value">{f"{r_val:.2f}" if not np.isnan(r_val) else "N/A"}</div>
        <div class="stat-sub">PM2.5 vs CO</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Standard Deviation <span>〜</span></div>
        <div class="stat-value">{f"{std_val:.1f}" if not np.isnan(std_val) else "N/A"}</div>
        <div class="stat-sub">Dispersion from mean (μ={_fmt(mean_val, 1)})</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Samples <span>🗄</span></div>
        <div class="stat-value">{n_samples:,}</div>
        <div class="stat-sub">Valid readings in selected range</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Outliers Detected <span>⚠</span></div>
        <div class="stat-value">{n_outliers}</div>
        <div class="stat-sub">Using IQR method (&gt;1.5 × IQR)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ROW A: Scatter + AQI Frequency ──
    ca1, ca2 = st.columns([1.6, 1])
    with ca1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        sc_x = st.selectbox("X", NON_AQI, index=0, key="sc_x")
        sc_y = st.selectbox("Y", NON_AQI, index=1, key="sc_y")
        tl   = st.checkbox("Trend line", value=True, key="tl")
        st.markdown(f'<div class="chart-panel-title">🔗 Correlation Analysis: {sc_x} vs {sc_y}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="chart-panel-sub">Relationship between {sc_x} and {sc_y}, coloured by AQI category</div>',
                    unsafe_allow_html=True)
        fig_sc = chart_scatter_corr(eda_df, sc_x, sc_y, tl)
        if fig_sc.data:
            st.plotly_chart(fig_sc, use_container_width=True, config=_CFG)
        else:
            st.info(f"No data for {sc_x} / {sc_y}.")
        st.markdown('</div>', unsafe_allow_html=True)

    with ca2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">🎯 AQI Frequency</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">Distribution of Air Quality Index readings</div>',
                    unsafe_allow_html=True)
        fig_fr = chart_aqi_freq(eda_df)
        if fig_fr.data:
            st.plotly_chart(fig_fr, use_container_width=True, config=_CFG)
        else:
            st.info("No AQI data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── ROW B: Pollutant time series + Heatmap ──
    cb1, cb2 = st.columns([1.4, 1])
    with cb1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-panel-title">📊 {poll_choice} – Time Series</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">Daily values + 7-day rolling average</div>',
                    unsafe_allow_html=True)
        fig_ts = chart_pollutant_time(eda_df, poll_choice)
        if fig_ts.data:
            st.plotly_chart(fig_ts, use_container_width=True, config=_CFG)
        else:
            st.info(f"No {poll_choice} data in range.")
        st.markdown('</div>', unsafe_allow_html=True)

    with cb2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">🗓️ AQI Heatmap – Month × Year</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">City-level monthly average AQI</div>',
                    unsafe_allow_html=True)
        if not df_ca.empty and df_ca["AQI"].notna().sum() > 0:
            st.plotly_chart(chart_heatmap_monthly(df_ca), use_container_width=True, config=_CFG)
        else:
            st.info("No city AQI data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── ROW C: Station boxplot + Yearly trend ──
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">📦 AQI Distribution by Station</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">Box plot showing spread, median and outliers per station</div>',
                    unsafe_allow_html=True)
        if not df_sa.empty and df_sa["AQI"].notna().sum() > 0:
            st.plotly_chart(chart_boxplot_stations(df_sa), use_container_width=True, config=_CFG)
        else:
            st.info("No station AQI data.")
        st.markdown('</div>', unsafe_allow_html=True)

    with cc2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">📅 Yearly Mean AQI Trend</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">City index vs individual stations year-over-year</div>',
                    unsafe_allow_html=True)
        if not df_ca.empty:
            st.plotly_chart(chart_yearly_trend(df_ca, df_sa),
                            use_container_width=True, config=_CFG)
        else:
            st.info("No data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── ROW D: Missing data heatmap (full width) ──
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-title">🔍 Data Completeness – Station × Pollutant (% Missing)</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-sub">Blue = complete, yellow = partial, red = mostly missing</div>',
                unsafe_allow_html=True)
    if not df_sa.empty:
        st.plotly_chart(chart_missing_heatmap(df_sa), use_container_width=True, config=_CFG)
    else:
        st.info("No station data.")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:24px 0 12px;
     font-family:'JetBrains Mono',monospace;font-size:10px;
     color:#30363d;letter-spacing:2px;">
  AIR QUALITY MONITORING – HCMC · 2022–2026 · AQICN DATA
</div>
""", unsafe_allow_html=True)