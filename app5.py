# -*- coding: utf-8 -*-
"""
HCMC Air Quality Monitoring Dashboard
- 2 tabs: Dashboard | EDA
- Light theme (Figma-style)
- fillcolor dùng rgba() — tương thích mọi phiên bản Plotly
"""

from datetime import date
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
CITY_CSV     = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"
STATIONS_CSV = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
NON_AQI  = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
ALL_COL  = ["AQI"] + NON_AQI

AQI_BANDS = [
    (0,   50,  "#16a34a", "Good"),
    (51,  100, "#ca8a04", "Moderate"),
    (101, 150, "#ea580c", "USG"),
    (151, 200, "#dc2626", "Unhealthy"),
    (201, 300, "#7e22ce", "Very Unhealthy"),
    (301, 999, "#450a0a", "Hazardous"),
]

# ─────────────────────────────────────────────────────────────
# CSS — Light theme, Figma-faithful
# ─────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Reset & base ── */
html, body, [data-testid="stApp"] {
    background: #f0f4f8 !important;
    font-family: 'Inter', sans-serif;
    color: #1a202c;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"]  { display: none; }
[data-testid="stMainBlockContainer"] {
    padding: 0 1.5rem 2rem !important;
    max-width: 100% !important;
}
section[data-testid="stSidebar"] { display: none; }

/* ── Navbar ── */
.navbar {
    position: sticky; top: 0; z-index: 200;
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 0 28px;
    height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 -1.5rem 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.navbar-left  { display: flex; align-items: center; gap: 10px; }
.navbar-logo  { color: #2563eb; font-size: 20px; font-weight: 700; }
.navbar-brand { color: #1a202c; font-size: 14px; font-weight: 600; }
.navbar-right { display: flex; align-items: center; gap: 8px; }
.nav-btn {
    background: none; border: 1px solid #e2e8f0;
    color: #4a5568; font-size: 13px; font-family: 'Inter', sans-serif;
    padding: 6px 14px; border-radius: 6px; cursor: pointer;
    transition: all 0.15s;
}
.nav-btn:hover { background: #f7fafc; color: #1a202c; border-color: #cbd5e0; }
.nav-btn-primary {
    background: #2563eb; border: 1px solid #2563eb;
    color: #fff; font-size: 13px; font-family: 'Inter', sans-serif;
    padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600;
}

/* ── Page hero ── */
.page-hero { padding: 32px 0 20px; }
.page-hero h1 {
    font-size: 30px; font-weight: 800;
    color: #1a202c; margin: 0 0 6px; line-height: 1.2;
}
.page-hero p { font-size: 14px; color: #718096; margin: 0; }

/* ── KPI cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px; margin-bottom: 28px;
}
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    display: flex; justify-content: space-between; align-items: flex-start;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.kpi-label {
    font-size: 11px; font-weight: 600;
    letter-spacing: 1px; color: #718096;
    text-transform: uppercase; margin-bottom: 10px;
}
.kpi-number {
    font-size: 40px; font-weight: 800;
    color: #1a202c; line-height: 1;
    font-family: 'JetBrains Mono', monospace;
}
.kpi-badge {
    display: inline-block; font-size: 11px; font-weight: 600;
    padding: 3px 10px; border-radius: 20px; margin-top: 8px; border: 1px solid;
}
.kpi-icon { font-size: 22px; opacity: 0.5; margin-top: 2px; }

/* ── Section heading ── */
.section-heading {
    font-size: 20px; font-weight: 700;
    color: #1a202c; margin: 0 0 16px;
}

/* ── Station cards ── */
.station-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s, border-color 0.2s;
    margin-bottom: 4px;
}
.station-card:hover {
    box-shadow: 0 4px 16px rgba(37,99,235,0.12);
    border-color: #bfdbfe;
}
.station-card-header {
    display: flex; justify-content: space-between;
    align-items: flex-start; margin-bottom: 4px;
}
.station-name  { font-size: 15px; font-weight: 700; color: #1a202c; }
.station-addr  { font-size: 12px; color: #a0aec0; margin-bottom: 14px; }
.station-aqi   {
    font-size: 48px; font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    color: #1a202c; line-height: 1; margin-bottom: 6px;
}
.station-badge {
    display: inline-block; font-size: 11px; font-weight: 700;
    padding: 3px 12px; border-radius: 20px; margin-bottom: 16px; border: 1px solid;
}
.station-divider { height: 1px; background: #e2e8f0; margin-bottom: 14px; }
.pollutant-row  { display: flex; gap: 24px; }
.pollutant-label {
    font-size: 11px; color: #a0aec0; font-weight: 500;
    margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px;
}
.pollutant-value {
    font-size: 16px; font-weight: 700; color: #2d3748;
    font-family: 'JetBrains Mono', monospace;
}
.live-badge {
    background: #f0fdf4; color: #16a34a;
    border: 1px solid #bbf7d0; font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;
}
.no-data-badge {
    background: #f7fafc; color: #a0aec0;
    border: 1px solid #e2e8f0; font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px;
}

/* ── EDA hero ── */
.eda-hero { padding: 32px 0 16px; }
.eda-hero h1 { font-size: 30px; font-weight: 800; color: #1a202c; margin: 0 0 6px; }
.eda-hero p  { font-size: 14px; color: #718096; margin: 0; }

/* ── EDA stat cards ── */
.stat-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 14px; margin-bottom: 20px;
}
.stat-card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stat-label {
    font-size: 13px; color: #718096; margin-bottom: 8px;
    display: flex; justify-content: space-between;
}
.stat-value {
    font-size: 30px; font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    color: #1a202c; line-height: 1; margin-bottom: 4px;
}
.stat-sub { font-size: 11px; color: #a0aec0; }

/* ── Chart panel ── */
.chart-panel {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 20px 22px; margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.chart-panel-title {
    font-size: 15px; font-weight: 700; color: #1a202c;
    margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
}
.chart-panel-sub { font-size: 12px; color: #718096; margin-bottom: 14px; }

/* ── Reference badges ── */
.ref-label    { font-size: 12px; color: #718096; margin-right: 4px; }
.ref-good     { color: #16a34a; font-weight: 700; font-size: 12px; }
.ref-moderate { color: #ca8a04; font-weight: 700; font-size: 12px; }
.ref-unhealthy{ color: #dc2626; font-weight: 700; font-size: 12px; }

/* ── Streamlit overrides ── */
.stSelectbox > label, .stMultiSelect > label,
.stDateInput > label, .stRadio > label {
    color: #4a5568 !important; font-size: 12px !important; font-weight: 600 !important;
}
.stPlotlyChart { border-radius: 8px; overflow: hidden; }
div[data-testid="column"] > div { padding: 2px !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #f0f4f8; }
::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 4px; }
</style>
"""

# ─────────────────────────────────────────────────────────────
# PLOTLY LIGHT THEME
# ─────────────────────────────────────────────────────────────
_CFG = dict(displayModeBar=False)

_P = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(family="Inter, sans-serif", color="#4a5568", size=11),
    margin=dict(l=8, r=8, t=8, b=8),
    legend=dict(
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#e2e8f0", borderwidth=1,
        font=dict(size=10, color="#1a202c"),
    ),
)
_A = dict(
    gridcolor="#e2e8f0", zeroline=False,
    linecolor="#cbd5e0",
    tickfont=dict(size=9, color="#718096"),
)


def _theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**_P)
    fig.update_xaxes(**_A)
    fig.update_yaxes(**_A)
    return fig


# ─────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────

def _num(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def aqi_info(v) -> tuple:
    """Returns (label, hex_color) for an AQI value."""
    try:
        val = float(v)
        if np.isnan(val):
            return "N/A", "#a0aec0"
    except Exception:
        return "N/A", "#a0aec0"
    for lo, hi, color, label in AQI_BANDS:
        if lo <= val <= hi:
            return label, color
    return "N/A", "#a0aec0"


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


def _hex_to_rgba(hex_color: str, alpha: float = 0.2) -> str:
    """Convert '#rrggbb' → 'rgba(r,g,b,alpha)' — safe for all Plotly versions."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────

def _load_city() -> pd.DataFrame:
    df = pd.read_csv(CITY_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = _num(df, ALL_COL)
    return df.sort_values("date").reset_index(drop=True)


def _load_stations() -> pd.DataFrame:
    df = pd.read_csv(STATIONS_CSV)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    if "station_name" not in df.columns:
        df["station_name"] = df["station_slug"]
    df = _num(df, ALL_COL)
    return df.sort_values(["station_name", "date"]).reset_index(drop=True)


@st.cache_data(ttl=600)
def get_city() -> pd.DataFrame:     return _load_city()

@st.cache_data(ttl=600)
def get_stations() -> pd.DataFrame: return _load_stations()


# ─────────────────────────────────────────────────────────────
# CHARTS — Dashboard
# ─────────────────────────────────────────────────────────────

def chart_city_trend(df: pd.DataFrame) -> go.Figure:
    v = df[["date", "AQI"]].dropna().sort_values("date")
    r = v.set_index("date")["AQI"].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    for lo, hi, c, _ in AQI_BANDS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.06,
                      layer="below", line_width=0)
    fig.add_trace(go.Scatter(
        x=v["date"], y=v["AQI"], name="AQI Daily",
        mode="lines", line=dict(color="#93c5fd", width=1.2), opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=r["date"], y=r["AQI"], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.5),
    ))
    _theme(fig)
    fig.update_layout(
        hovermode="x unified",
        yaxis_title="AQI",
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
    )
    return fig


def chart_station_detail(df: pd.DataFrame, station: str) -> go.Figure:
    sub = df[df["station_name"] == station][["date", "AQI"]].dropna().sort_values("date")
    if sub.empty:
        return go.Figure()
    roll = sub.set_index("date")["AQI"].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    for lo, hi, c, _ in AQI_BANDS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.07,
                      layer="below", line_width=0)
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["AQI"], name="AQI Daily",
        mode="lines", line=dict(color="#93c5fd", width=1.2), opacity=0.65,
    ))
    fig.add_trace(go.Scatter(
        x=roll["date"], y=roll["AQI"], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.5),
    ))
    _theme(fig)
    fig.update_layout(
        hovermode="x unified", yaxis_title="AQI",
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
    )
    return fig


def chart_radar_station(df: pd.DataFrame, station: str) -> go.Figure:
    """Radar chart — station pollutant profile vs city-wide average.
    fillcolor uses rgba() for full Plotly compatibility."""
    avail = [c for c in NON_AQI if c in df.columns and df[c].notna().sum() > 5]
    if len(avail) < 3:
        return go.Figure()

    sub   = df[df["station_name"] == station][avail].mean()
    all_m = df[avail].mean()
    scale = all_m.replace(0, np.nan)
    norm_stn  = (sub   / scale).fillna(0).clip(0, 2)
    norm_city = (all_m / scale).fillna(0).clip(0, 2)
    cats = avail + [avail[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=norm_city.tolist() + [norm_city.iloc[0]],
        theta=cats, name="City Avg", fill="toself",
        opacity=0.4,
        line=dict(color="#94a3b8", width=1.5),
        fillcolor="rgba(148,163,184,0.15)",      # ← rgba, NO 8-char hex
    ))
    fig.add_trace(go.Scatterpolar(
        r=norm_stn.tolist() + [norm_stn.iloc[0]],
        theta=cats, name=station[:22], fill="toself",
        opacity=0.7,
        line=dict(color="#2563eb", width=2),
        fillcolor="rgba(37,99,235,0.18)",        # ← rgba
    ))
    _theme(fig)
    fig.update_layout(
        polar=dict(
            bgcolor="#f8fafc",
            radialaxis=dict(
                visible=True, range=[0, 2],
                tickfont=dict(size=8, color="#94a3b8"),
                gridcolor="#e2e8f0", linecolor="#e2e8f0",
            ),
            angularaxis=dict(
                tickfont=dict(size=9, color="#4a5568"),
                gridcolor="#e2e8f0",
            ),
        ),
        legend=dict(font=dict(size=10, color="#1a202c")),
    )
    return fig


# ─────────────────────────────────────────────────────────────
# CHARTS — EDA
# ─────────────────────────────────────────────────────────────

def chart_aqi_freq(df: pd.DataFrame) -> go.Figure:
    order  = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
    cats   = df["AQI"].dropna().apply(lambda x: aqi_info(x)[0]).value_counts()
    cats   = cats.reindex([c for c in order if c in cats.index])
    colors = [next((c for _, _, c, l in AQI_BANDS if l == k), "#94a3b8") for k in cats.index]
    fig = go.Figure(go.Bar(
        x=cats.values, y=cats.index, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=cats.values, textposition="outside",
        textfont=dict(color="#1a202c", size=10),
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
    r   = _corr(tmp, x_col, y_col)
    fig = px.scatter(
        tmp, x=x_col, y=y_col, color="cat",
        category_orders={"cat": ["Good","Moderate","USG",
                                  "Unhealthy","Very Unhealthy","Hazardous"]},
        color_discrete_map=clr,
        opacity=0.7,
        trendline="ols" if trendline else None,
    )
    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
    _theme(fig)
    fig.update_layout(
        legend=dict(title=None, font=dict(size=10)),
        annotations=[dict(
            x=0.02, y=0.97, xref="paper", yref="paper",
            text=f"r = {r:.3f}" if not np.isnan(r) else "r = N/A",
            showarrow=False,
            font=dict(size=12, color="#1d4ed8", family="JetBrains Mono"),
            bgcolor="rgba(219,234,254,0.95)",
            bordercolor="#3b82f6", borderwidth=1, borderpad=6,
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
        mode="lines", line=dict(color="#93c5fd", width=1), opacity=0.5,
    ))
    fig.add_trace(go.Scatter(
        x=roll["date"], y=roll[col], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.2),
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
    zv  = pivot.values.astype(float)
    txt = np.where(np.isnan(zv), "", np.round(zv, 0).astype("int").astype("str"))
    fig = go.Figure(go.Heatmap(
        z=zv, x=xlbls, y=[str(y) for y in pivot.index],
        colorscale=[[0,"#22c55e"],[0.25,"#eab308"],
                    [0.5,"#f97316"],[0.75,"#ef4444"],[1,"#7f1d1d"]],
        zmin=0, zmax=150,
        text=txt, texttemplate="%{text}",
        textfont=dict(size=10, color="#1a202c"),
        hovertemplate="Năm %{y} – %{x}: AQI %{z:.1f}<extra></extra>",
        showscale=True,
        colorbar=dict(
            thickness=10, len=0.85,
            tickfont=dict(size=9, color="#4a5568"),
            title=dict(text="AQI", font=dict(color="#4a5568", size=10)),
        ),
    ))
    _theme(fig)
    return fig


def chart_boxplot_stations(df: pd.DataFrame) -> go.Figure:
    order   = df.groupby("station_name")["AQI"].median().dropna().sort_values(ascending=False).index
    palette = ["#2563eb","#16a34a","#ca8a04","#dc2626","#7e22ce",
               "#0891b2","#059669","#ea580c","#c026d3","#d97706"]
    fig = go.Figure()
    for i, stn in enumerate(order):
        vals = df[df["station_name"] == stn]["AQI"].dropna()
        if len(vals) < 2:
            continue
        c     = palette[i % len(palette)]
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


def chart_yearly_trend(df_city: pd.DataFrame, df_st: pd.DataFrame) -> go.Figure:
    palette = ["#2563eb","#16a34a","#ca8a04","#dc2626","#7e22ce",
               "#0891b2","#059669","#ea580c","#c026d3"]
    fig = go.Figure()
    # City
    cg = df_city.copy(); cg["year"] = cg["date"].dt.year
    cy = cg.groupby("year")["AQI"].mean().reset_index()
    fig.add_trace(go.Scatter(
        x=cy["year"], y=cy["AQI"], name="City (AQICN)",
        mode="lines+markers",
        line=dict(color="#1a202c", width=3),
        marker=dict(size=7, color="#1a202c"),
    ))
    # Stations
    sg = df_st.copy(); sg["year"] = sg["date"].dt.year
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
        yaxis_title="AQI TB theo năm",
        legend=dict(font=dict(size=10)),
    )
    return fig


def chart_missing_heatmap(df: pd.DataFrame) -> go.Figure:
    poll = [c for c in ALL_COL if c in df.columns]
    miss = df.groupby("station_name")[poll].apply(lambda g: g.isna().mean() * 100)
    fig = go.Figure(go.Heatmap(
        z=miss.values, x=miss.columns.tolist(),
        y=[s[:22] + "…" if len(s) > 22 else s for s in miss.index],
        colorscale=[[0,"#22c55e"],[0.5,"#eab308"],[1,"#dc2626"]],
        zmin=0, zmax=100,
        text=np.round(miss.values, 0).astype("int").astype("str"),
        texttemplate="%{text}%",
        textfont=dict(size=9, color="#1a202c"),
        hovertemplate="%{y} – %{x}: %{z:.1f}% missing<extra></extra>",
        showscale=True,
        colorbar=dict(
            thickness=10, ticksuffix="%",
            tickfont=dict(size=9, color="#4a5568"),
        ),
    ))
    _theme(fig)
    return fig


# ─────────────────────────────────────────────────────────────
# PAGE CONFIG + INIT
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Air Quality Monitoring – HCMC",
    page_icon="🌫️", layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)

with st.spinner("Loading data..."):
    try:
        df_city = get_city()
    except Exception as e:
        st.error(f"Cannot load City CSV: {e}"); st.stop()
    try:
        df_st = get_stations()
    except Exception as e:
        st.error(f"Cannot load Stations CSV: {e}"); st.stop()

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
tab = st.radio("tab", ["Dashboard", "EDA"], horizontal=True, label_visibility="collapsed")
st.markdown("---")

# ═════════════════════════════════════════════════════════════
#  TAB 1 – DASHBOARD
# ═════════════════════════════════════════════════════════════
if tab == "Dashboard":

    # Filters
    with st.expander("🔧 Bộ lọc thời gian", expanded=False):
        d_range = st.date_input(
            "Khoảng thời gian",
            value=(date(2024, 1, 1), date.today()),
            min_value=df_city["date"].min().date(),
            max_value=df_city["date"].max().date(),
            key="dash_dates",
        )
    ts0 = pd.Timestamp(d_range[0] if isinstance(d_range, (list, tuple)) and len(d_range) == 2 else df_city["date"].min())
    ts1 = pd.Timestamp(d_range[1] if isinstance(d_range, (list, tuple)) and len(d_range) == 2 else df_city["date"].max())

    df_cf = df_city[(df_city["date"] >= ts0) & (df_city["date"] <= ts1)].copy()
    df_sf = df_st[(df_st["date"]   >= ts0) & (df_st["date"]   <= ts1)].copy()

    # KPIs
    cq         = df_cf["AQI"].dropna()
    city_avg   = cq.mean() if len(cq) else None
    city_cat, city_col = aqi_info(city_avg)
    n_stations  = df_sf["station_name"].nunique()
    stn_means   = df_sf.groupby("station_name")["AQI"].mean().dropna()
    n_unhealthy = int((stn_means > 100).sum())

    # Hero
    st.markdown(f"""
    <div class="page-hero">
      <h1>Ho Chi Minh City Air Quality Dashboard</h1>
      <p>Real-time air quality monitoring across {n_stations} monitoring stations in Ho Chi Minh City</p>
    </div>
    """, unsafe_allow_html=True)

    # 3 KPI cards
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div>
          <div class="kpi-label">City Average AQI</div>
          <div class="kpi-number">{_fmt(city_avg, 0)}</div>
          <span class="kpi-badge" style="color:{city_col};border-color:{city_col};background:{_hex_to_rgba(city_col,0.1)}">{city_cat}</span>
        </div>
        <div class="kpi-icon">📈</div>
      </div>
      <div class="kpi-card">
        <div>
          <div class="kpi-label">Active Stations</div>
          <div class="kpi-number">{n_stations}</div>
          <span class="kpi-badge" style="color:#16a34a;border-color:#16a34a;background:rgba(22,163,74,0.1)">All Online</span>
        </div>
        <div class="kpi-icon">📍</div>
      </div>
      <div class="kpi-card">
        <div>
          <div class="kpi-label">Unhealthy Areas</div>
          <div class="kpi-number">{n_unhealthy}</div>
          <span class="kpi-badge" style="color:#dc2626;border-color:#dc2626;background:rgba(220,38,38,0.1)">AQI &gt; 100</span>
        </div>
        <div class="kpi-icon">⚠️</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # City trend
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-title">📈 City-level AQI Trend</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-sub">Daily AQI + 7-day rolling average from AQICN city index</div>', unsafe_allow_html=True)
    if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_city_trend(df_cf), use_container_width=True, config=_CFG)
    else:
        st.info("No city data in selected range.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Station cards
    st.markdown('<p class="section-heading">Monitoring Stations</p>', unsafe_allow_html=True)
    stations = df_sf["station_name"].unique().tolist()

    def _station_card(name: str) -> str:
        sub  = df_sf[df_sf["station_name"] == name].sort_values("date")
        last = sub.dropna(subset=["AQI"]).tail(1)
        aqi_val      = float(last["AQI"].iloc[0]) if not last.empty else None
        cat, col     = aqi_info(aqi_val)
        badge        = '<span class="live-badge">LIVE</span>' if aqi_val is not None else '<span class="no-data-badge">NO DATA</span>'

        def _p(c):
            if last.empty or c not in last.columns: return "—"
            v = last[c].iloc[0]
            return _fmt(v, 0) if pd.notna(v) else "—"

        return f"""
        <div class="station-card">
          <div class="station-card-header">
            <div class="station-name">{name}</div>
            {badge}
          </div>
          <div class="station-addr">Ho Chi Minh City</div>
          <div class="station-aqi">{_fmt(aqi_val, 0) if aqi_val else "—"}</div>
          <span class="station-badge"
            style="color:{col};border-color:{col};background:{_hex_to_rgba(col,0.1)}">{cat}</span>
          <div class="station-divider"></div>
          <div class="pollutant-row">
            <div class="pollutant-item">
              <div class="pollutant-label">PM2.5</div>
              <div class="pollutant-value">{_p("PM2,5")}</div>
            </div>
            <div class="pollutant-item">
              <div class="pollutant-label">PM10</div>
              <div class="pollutant-value">{_p("PM10")}</div>
            </div>
            <div class="pollutant-item">
              <div class="pollutant-label">O3</div>
              <div class="pollutant-value">{_p("O3")}</div>
            </div>
          </div>
        </div>"""

    for i in range(0, len(stations), 3):
        batch = stations[i:i+3]
        cols  = st.columns(len(batch))
        for col_obj, stn in zip(cols, batch):
            with col_obj:
                st.markdown(_station_card(stn), unsafe_allow_html=True)

    # Station detail
    st.markdown("---")
    st.markdown('<p class="section-heading">Station Detail View</p>', unsafe_allow_html=True)
    sel = st.selectbox("Chọn trạm để xem chi tiết", stations, key="det_stn")
    if sel:
        d1, d2 = st.columns([2, 1])
        with d1:
            st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-panel-title">📈 AQI Trend – {sel}</div>', unsafe_allow_html=True)
            fig = chart_station_detail(df_sf, sel)
            if fig.data:
                st.plotly_chart(fig, use_container_width=True, config=_CFG)
            else:
                st.info("No AQI data for this station.")
            st.markdown('</div>', unsafe_allow_html=True)
        with d2:
            st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
            st.markdown('<div class="chart-panel-title">🕸️ Pollutant Profile vs City Avg</div>', unsafe_allow_html=True)
            fig_r = chart_radar_station(df_sf, sel)
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
      <p>Deep dive into pollutant correlations, frequency distributions,
         and station variances across Ho Chi Minh City's monitoring network.</p>
    </div>
    """, unsafe_allow_html=True)

    # EDA Filters
    ef1, ef2, ef3, ef4 = st.columns([1.2, 1.2, 1.2, 2])
    with ef1:
        eda_src = st.selectbox("Nguồn dữ liệu", ["City CSV", "Stations CSV", "Cả hai"], key="esrc")
    with ef2:
        ed0 = st.date_input("Từ ngày", value=date(2022, 1, 1),
                            min_value=df_city["date"].min().date(),
                            max_value=df_city["date"].max().date(), key="ed0")
        ed1 = st.date_input("Đến ngày", value=date.today(),
                            min_value=df_city["date"].min().date(),
                            max_value=df_city["date"].max().date(), key="ed1")
    with ef3:
        poll_choice = st.selectbox("Chỉ số chính", ["AQI"] + NON_AQI, key="epoll")
    with ef4:
        st.markdown("""
        <div style="padding-top:26px;font-size:12px;color:#718096">
          <span class="ref-label">Reference:</span>
          <span class="ref-good">■ Good</span>&nbsp;&nbsp;
          <span class="ref-moderate">■ Moderate</span>&nbsp;&nbsp;
          <span class="ref-unhealthy">■ Unhealthy</span>
        </div>""", unsafe_allow_html=True)

    ta, tb = pd.Timestamp(ed0), pd.Timestamp(ed1)
    df_ca = df_city[(df_city["date"] >= ta) & (df_city["date"] <= tb)].copy()
    df_sa = df_st[(df_st["date"]     >= ta) & (df_st["date"]   <= tb)].copy()
    if eda_src == "City CSV":
        eda_df = df_ca
    elif eda_src == "Stations CSV":
        eda_df = df_sa
    else:
        eda_df = pd.concat([df_ca, df_sa], ignore_index=True)

    # Stat cards
    col_s    = eda_df[poll_choice].dropna() if poll_choice in eda_df.columns else pd.Series(dtype=float)
    r_pm_co  = _corr(eda_df, "PM2,5", "CO") if all(c in eda_df.columns for c in ["PM2,5","CO"]) else float("nan")
    std_val  = col_s.std()  if len(col_s) > 1 else float("nan")
    mean_val = col_s.mean() if len(col_s) else float("nan")
    n_samp   = len(col_s)
    n_out    = _iqr_outliers(col_s) if len(col_s) > 4 else 0

    st.markdown(f"""
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">Pearson Correlation (r) <span>📈</span></div>
        <div class="stat-value">{f"{r_pm_co:.2f}" if not np.isnan(r_pm_co) else "N/A"}</div>
        <div class="stat-sub">PM2.5 vs CO</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Standard Deviation <span>〜</span></div>
        <div class="stat-value">{f"{std_val:.1f}" if not np.isnan(std_val) else "N/A"}</div>
        <div class="stat-sub">Dispersion — mean = {_fmt(mean_val, 1)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Samples <span>🗄</span></div>
        <div class="stat-value">{n_samp:,}</div>
        <div class="stat-sub">Valid readings in selected range</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Outliers Detected <span>⚠</span></div>
        <div class="stat-value">{n_out}</div>
        <div class="stat-sub">Using IQR method (&gt;1.5 × IQR)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ROW A: Scatter + AQI Frequency
    ra1, ra2 = st.columns([1.6, 1])
    with ra1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        sx = st.selectbox("X", NON_AQI, index=0, key="sx")
        sy = st.selectbox("Y", NON_AQI, index=1, key="sy")
        tl = st.checkbox("Trend line", value=True, key="tl")
        st.markdown(f'<div class="chart-panel-title">🔗 Correlation: {sx} vs {sy}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-panel-sub">Coloured by AQI category</div>', unsafe_allow_html=True)
        fig_sc = chart_scatter_corr(eda_df, sx, sy, tl)
        if fig_sc.data:
            st.plotly_chart(fig_sc, use_container_width=True, config=_CFG)
        else:
            st.info(f"No data for {sx} / {sy}.")
        st.markdown('</div>', unsafe_allow_html=True)

    with ra2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">🎯 AQI Frequency</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">Distribution of AQI readings by category</div>', unsafe_allow_html=True)
        fig_fr = chart_aqi_freq(eda_df)
        if fig_fr.data:
            st.plotly_chart(fig_fr, use_container_width=True, config=_CFG)
        else:
            st.info("No AQI data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ROW B: Time series + Heatmap
    rb1, rb2 = st.columns([1.4, 1])
    with rb1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-panel-title">📊 {poll_choice} Time Series</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">Daily values + 7-day rolling average</div>', unsafe_allow_html=True)
        fig_ts = chart_pollutant_time(eda_df, poll_choice)
        if fig_ts.data:
            st.plotly_chart(fig_ts, use_container_width=True, config=_CFG)
        else:
            st.info(f"No {poll_choice} data.")
        st.markdown('</div>', unsafe_allow_html=True)

    with rb2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">🗓️ AQI Heatmap – Month × Year</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">City-level monthly average AQI</div>', unsafe_allow_html=True)
        if not df_ca.empty and df_ca["AQI"].notna().sum() > 0:
            st.plotly_chart(chart_heatmap_monthly(df_ca), use_container_width=True, config=_CFG)
        else:
            st.info("No city AQI data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ROW C: Boxplot + Yearly trend
    rc1, rc2 = st.columns([1, 1])
    with rc1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">📦 AQI Distribution by Station</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">Median, IQR and outliers per station</div>', unsafe_allow_html=True)
        if not df_sa.empty and df_sa["AQI"].notna().sum() > 0:
            st.plotly_chart(chart_boxplot_stations(df_sa), use_container_width=True, config=_CFG)
        else:
            st.info("No station AQI data.")
        st.markdown('</div>', unsafe_allow_html=True)

    with rc2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-title">📅 Yearly Mean AQI Trend</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-panel-sub">City index vs individual stations year-over-year</div>', unsafe_allow_html=True)
        if not df_ca.empty:
            st.plotly_chart(chart_yearly_trend(df_ca, df_sa), use_container_width=True, config=_CFG)
        else:
            st.info("No data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ROW D: Missing data heatmap (full width)
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-title">🔍 Data Completeness – Station × Pollutant (% Missing)</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-panel-sub">Green = complete · Yellow = partial · Red = mostly missing</div>', unsafe_allow_html=True)
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
     color:#cbd5e0;letter-spacing:2px;">
  AIR QUALITY MONITORING – HCMC · 2022–2026 · AQICN DATA
</div>
""", unsafe_allow_html=True)