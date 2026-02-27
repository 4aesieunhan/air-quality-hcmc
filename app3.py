# -*- coding: utf-8 -*-
"""
HCMC Air Quality Dashboard
- Light theme, high-contrast text
- AQI dùng đúng cột 'AQI' từ CSV (không compute lại)
- Stations: date format dd/MM/yyyy
- Không có undefined trong plotly titles
"""

from datetime import date
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
NON_AQI     = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
ALL_METRICS = ["AQI"] + NON_AQI

STATIONS_CSV_PATH = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"
CITY_CSV_PATH     = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"

# Vibrant slice colors (charts/bars)
AQI_SLICE = {
    "Good":           "#16a34a",
    "Moderate":       "#ca8a04",
    "USG":            "#ea580c",
    "Unhealthy":      "#dc2626",
    "Very Unhealthy": "#7e22ce",
    "Hazardous":      "#450a0a",
}

# ─────────────────────────────────────────
# CSS  (single, clean string)
# ─────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Global ── */
html, body, [data-testid="stApp"] {
    background: #eef1f8 !important;
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: #0f172a;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"]  { display: none; }

/* ── Sidebar (dark navy) ── */
[data-testid="stSidebar"] {
    background: #1e293b !important;
    border-right: 1px solid #334155 !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] label {
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] h3 {
    color: #60a5fa !important;
    font-size: 14px !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stCaption { color: #64748b !important; }
[data-testid="stSidebar"] hr { border-color: #334155 !important; }

/* ── Dashboard header ── */
.dash-header {
    background: #ffffff;
    border-bottom: 2px solid #e2e8f0;
    padding: 14px 24px 12px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 0 0 12px 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.dash-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #1e40af;
    text-transform: uppercase;
}
.dash-subtitle {
    font-size: 11px;
    color: #64748b;
    margin-top: 2px;
}
.dash-badge {
    background: #dbeafe;
    color: #1e40af;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    padding: 4px 10px;
    border-radius: 20px;
    font-weight: 700;
    letter-spacing: 1px;
}

/* ── KPI row ── */
.kpi-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
    margin-bottom: 18px;
}
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s, transform 0.15s;
}
.kpi-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    transform: translateY(-1px);
}
.kpi-accent {
    position: absolute; top: 0; left: 0; right: 0;
    height: 3px; border-radius: 10px 10px 0 0;
}
.kpi-label {
    font-size: 9px; font-weight: 700;
    letter-spacing: 1.5px; color: #64748b;
    text-transform: uppercase; margin-bottom: 6px;
}
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 26px; font-weight: 700;
    color: #0f172a; line-height: 1; margin-bottom: 4px;
}
.kpi-sub  { font-size: 11px; color: #64748b; }
.kpi-good { color: #15803d !important; }
.kpi-warn { color: #b45309 !important; }
.kpi-bad  { color: #b91c1c !important; }
.kpi-blue { color: #1d4ed8 !important; }

/* ── Section titles ── */
.chart-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 700;
    letter-spacing: 2px; color: #1e40af;
    text-transform: uppercase; margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.ct-bar {
    width: 3px; height: 14px;
    background: linear-gradient(180deg, #3b82f6, #1e40af);
    border-radius: 2px; display: inline-block; flex-shrink: 0;
}
.section-sep {
    height: 1px;
    background: linear-gradient(90deg, transparent, #cbd5e1 20%, #cbd5e1 80%, transparent);
    margin: 8px 0 16px;
}

/* ── Misc ── */
.stPlotlyChart { border-radius: 8px; overflow: hidden; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #eef1f8; }
::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 4px; }
</style>
"""

# ─────────────────────────────────────────
# PLOTLY BASE THEME
# ─────────────────────────────────────────
CHART_CFG = dict(displayModeBar=False)

_BASE = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#1e293b", size=11),
    margin=dict(l=8, r=8, t=8, b=8),
    legend=dict(
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#cbd5e1", borderwidth=1,
        font=dict(size=10, color="#1e293b"),
    ),
)
_AXIS = dict(
    gridcolor="#e2e8f0", zeroline=False,
    linecolor="#cbd5e1",
    tickfont=dict(size=9, color="#475569"),
)


def _theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**_BASE)
    fig.update_xaxes(**_AXIS)
    fig.update_yaxes(**_AXIS)
    return fig


# ─────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────

def _safe_num(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def aqi_cat(aqi) -> str:
    try:
        v = float(aqi)
        if np.isnan(v): return "N/A"
    except Exception:
        return "N/A"
    if v <= 50:  return "Good"
    if v <= 100: return "Moderate"
    if v <= 150: return "USG"
    if v <= 200: return "Unhealthy"
    if v <= 300: return "Very Unhealthy"
    return "Hazardous"


def aqi_hex(aqi) -> str:
    return AQI_SLICE.get(aqi_cat(aqi), "#94a3b8")


def kpi_cls(val, lo, hi) -> str:
    try:
        v = float(val)
        if np.isnan(v): return ""
        return "kpi-good" if v <= lo else ("kpi-warn" if v <= hi else "kpi-bad")
    except Exception:
        return ""


def fmt(v, dec: int = 1) -> str:
    try:
        f = float(v)
        return f"{f:.{dec}f}" if not np.isnan(f) else "N/A"
    except Exception:
        return "N/A"


def _corr(df: pd.DataFrame, x: str, y: str) -> float:
    t = df[[x, y]].dropna()
    return float(t[x].corr(t[y])) if len(t) >= 3 else float("nan")


# ─────────────────────────────────────────
# PREPROCESS
# ─────────────────────────────────────────

def prep_city(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if "year" not in df.columns:
        df["year"] = df["date"].dt.year
    df = _safe_num(df, ALL_METRICS)
    return df.sort_values("date").reset_index(drop=True)


def prep_stations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    if "station_name" not in df.columns:
        df["station_name"] = df["station_slug"].astype(str)
    if "year" not in df.columns:
        df["year"] = df["date"].dt.year
    df = _safe_num(df, ALL_METRICS)
    return df.sort_values(["station_slug", "date"]).reset_index(drop=True)


# ─────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────

@st.cache_data(ttl=600)
def load_city() -> pd.DataFrame:
    return prep_city(pd.read_csv(CITY_CSV_PATH))


@st.cache_data(ttl=600)
def load_stations() -> pd.DataFrame:
    return prep_stations(pd.read_csv(STATIONS_CSV_PATH))


# ─────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────

def chart_trend(df: pd.DataFrame) -> go.Figure:
    vals = df[["date", "AQI"]].dropna().sort_values("date")
    roll = (vals.set_index("date")["AQI"]
               .rolling(7, min_periods=1).mean()
               .reset_index())
    fig = go.Figure()
    for lo, hi, c in [(0,50,"#16a34a"),(51,100,"#ca8a04"),
                      (101,150,"#ea580c"),(151,200,"#dc2626"),(201,300,"#7e22ce")]:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.07,
                      layer="below", line_width=0)
    fig.add_trace(go.Scatter(
        x=vals["date"], y=vals["AQI"], name="AQI Daily",
        mode="lines", line=dict(color="#93c5fd", width=1.2), opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=roll["date"], y=roll["AQI"], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.5),
    ))
    _theme(fig)
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                    font=dict(size=10, color="#1e293b")),
    )
    return fig


def chart_donut(df: pd.DataFrame) -> go.Figure:
    order  = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
    counts = df["AQI"].dropna().apply(aqi_cat).value_counts()
    counts = counts.reindex([c for c in order if c in counts.index])
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.58,
        marker=dict(colors=[AQI_SLICE[c] for c in counts.index],
                    line=dict(color="#ffffff", width=2)),
        textinfo="percent+label",
        textfont=dict(size=11, color="#1e293b", family="Plus Jakarta Sans"),
        insidetextorientation="horizontal",
        textposition="outside",
        pull=[0.02] * len(counts),
        hovertemplate="%{label}: %{value} ngày (%{percent})<extra></extra>",
    ))
    _theme(fig)
    fig.update_layout(showlegend=False, margin=dict(l=16, r=16, t=16, b=16))
    return fig


def chart_heatmap(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"]  = tmp["date"].dt.year
    pivot = tmp.pivot_table(index="year", columns="month", values="AQI", aggfunc="mean")
    mlbls = ["Jan","Feb","Mar","Apr","May","Jun",
             "Jul","Aug","Sep","Oct","Nov","Dec"]
    xlbls = [mlbls[m - 1] for m in pivot.columns]
    zv    = pivot.values.astype(float)
    txt   = np.where(np.isnan(zv), "",
                     np.round(zv, 0).astype("int").astype("str"))
    fig = go.Figure(go.Heatmap(
        z=zv, x=xlbls, y=[str(y) for y in pivot.index],
        colorscale=[[0,"#22c55e"],[0.25,"#eab308"],
                    [0.5,"#f97316"],[0.75,"#ef4444"],[1,"#7f1d1d"]],
        zmin=0, zmax=200,
        text=txt, texttemplate="%{text}",
        textfont=dict(size=11, color="#1e293b"),
        hovertemplate="Năm %{y} – %{x}<br>AQI TB: %{z:.1f}<extra></extra>",
        showscale=True,
        colorbar=dict(
            thickness=12, len=0.85,
            title=dict(text="AQI", side="right",
                       font=dict(color="#1e293b", size=10)),
            tickfont=dict(size=9, color="#475569"),
        ),
    ))
    _theme(fig)
    return fig


def chart_monthly_bar(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"]  = tmp["date"].dt.year.astype(str)
    grp = tmp.groupby(["year", "month"])["AQI"].mean().reset_index()
    mlbls = ["Jan","Feb","Mar","Apr","May","Jun",
             "Jul","Aug","Sep","Oct","Nov","Dec"]
    grp["month_name"] = grp["month"].apply(lambda m: mlbls[m - 1])
    fig = px.bar(
        grp, x="month_name", y="AQI", color="year", barmode="group",
        color_discrete_sequence=["#2563eb","#059669","#d97706","#dc2626","#7c3aed"],
        category_orders={"month_name": mlbls},
        labels={"AQI": "AQI TB", "month_name": ""},
    )
    _theme(fig)
    fig.update_layout(
        legend=dict(title=None, font=dict(size=10, color="#1e293b")),
        bargap=0.15, bargroupgap=0.06,
    )
    return fig


def chart_top_stations(df: pd.DataFrame, agg: str, top_n: int) -> go.Figure:
    g = df.groupby("station_name")["AQI"]
    s = g.mean() if agg == "Mean" else (g.median() if agg == "Median" else g.max())
    rank = s.dropna().nlargest(top_n).sort_values()
    fig = go.Figure(go.Bar(
        x=rank.values, y=rank.index, orientation="h",
        marker=dict(color=[aqi_hex(v) for v in rank.values], opacity=0.9,
                    line=dict(width=0)),
        text=[f"{v:.0f}" for v in rank.values],
        textposition="outside",
        textfont=dict(size=10, color="#1e293b"),
        hovertemplate="<b>%{y}</b><br>AQI: %{x:.1f}<extra></extra>",
    ))
    _theme(fig)
    fig.update_layout(showlegend=False)
    return fig


def chart_boxplot(df: pd.DataFrame, top_n: int) -> go.Figure:
    top_stns = df.groupby("station_name")["AQI"].median().nlargest(top_n).index
    sub      = df[df["station_name"].isin(top_stns)]
    palette  = px.colors.qualitative.Safe
    fig = go.Figure()
    for i, stn in enumerate(top_stns[::-1]):
        vals = sub[sub["station_name"] == stn]["AQI"].dropna()
        if len(vals) < 2:
            continue
        c = palette[i % len(palette)]
        fig.add_trace(go.Box(
            y=[stn] * len(vals), x=vals, name=stn, orientation="h",
            boxmean=True,
            marker=dict(size=3, opacity=0.45, color=c),
            line=dict(color=c, width=1.5),
            hovertemplate=f"<b>{stn}</b><br>AQI: %{{x:.0f}}<extra></extra>",
        ))
    _theme(fig)
    fig.update_layout(showlegend=False, hovermode="closest")
    return fig


def chart_radar(df: pd.DataFrame, top_n: int) -> go.Figure:
    avail = [p for p in NON_AQI
             if p in df.columns and df[p].notna().sum() > 10]
    if len(avail) < 3:
        return go.Figure()
    top_stns = df.groupby("station_name")["AQI"].median().nlargest(top_n).index
    sub      = df[df["station_name"].isin(top_stns)]
    means    = sub.groupby("station_name")[avail].mean()
    norm     = (means - means.min()) / (means.max() - means.min() + 1e-9)
    palette  = px.colors.qualitative.Safe
    fig = go.Figure()
    for i, stn in enumerate(top_stns):
        if stn not in norm.index:
            continue
        vals = norm.loc[stn].tolist()
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=avail + [avail[0]],
            name=stn, fill="toself", opacity=0.55,
            line=dict(color=palette[i % len(palette)], width=1.8),
        ))
    _theme(fig)
    fig.update_layout(
        polar=dict(
            bgcolor="#f8fafc",
            radialaxis=dict(visible=True, range=[0, 1],
                            tickfont=dict(size=8, color="#64748b"),
                            gridcolor="#e2e8f0", linecolor="#cbd5e1"),
            angularaxis=dict(tickfont=dict(size=9, color="#1e293b"),
                             gridcolor="#e2e8f0", linecolor="#cbd5e1"),
        ),
        legend=dict(font=dict(size=9, color="#1e293b")),
    )
    return fig


def chart_scatter(df: pd.DataFrame, x_col: str, y_col: str) -> go.Figure:
    if x_col not in df.columns or y_col not in df.columns:
        return go.Figure()
    tmp = df[[x_col, y_col, "AQI", "station_name", "date"]].dropna()
    if tmp.empty:
        return go.Figure()
    tmp = tmp.copy()
    tmp["category"] = tmp["AQI"].apply(aqi_cat)
    r = _corr(tmp, x_col, y_col)
    fig = px.scatter(
        tmp, x=x_col, y=y_col, color="category",
        category_orders={"category": ["Good","Moderate","USG",
                                       "Unhealthy","Very Unhealthy","Hazardous"]},
        color_discrete_map=AQI_SLICE,
        hover_data={"station_name": True, "date": True, "category": False},
        opacity=0.75,
    )
    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
    _theme(fig)
    fig.update_layout(
        legend=dict(title=None, font=dict(size=10, color="#1e293b")),
        annotations=[dict(
            x=0.02, y=0.97, xref="paper", yref="paper",
            text=f"Pearson r = {r:.3f}" if not np.isnan(r) else "r = N/A",
            showarrow=False,
            font=dict(size=11, color="#1d4ed8", family="JetBrains Mono"),
            bgcolor="rgba(219,234,254,0.95)",
            bordercolor="#3b82f6", borderwidth=1, borderpad=6,
        )],
    )
    return fig


# ─────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────
st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    page_icon="🌆", layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# Load
with st.spinner("Đang tải dữ liệu..."):
    try:
        df_city = load_city()
    except Exception as e:
        st.error(f"❌ Không load được City CSV: {e}")
        st.stop()
    try:
        df_st = load_stations()
    except Exception as e:
        st.error(f"❌ Không load được Stations CSV: {e}")
        st.stop()

# ── Sidebar ──
with st.sidebar:
    st.markdown("### ⚙️ Bộ lọc")

    min_d = min(df_st["date"].min(), df_city["date"].min())
    max_d = max(df_st["date"].max(), df_city["date"].max())
    today = pd.Timestamp(date.today())
    d_end   = min(max_d, today)
    d_start = max(min_d, d_end - pd.Timedelta(days=365))

    d_range = st.date_input(
        "Khoảng thời gian",
        value=(d_start.date(), d_end.date()),
        min_value=min_d.date(), max_value=max_d.date(),
    )
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        ts0, ts1 = pd.Timestamp(d_range[0]), pd.Timestamp(d_range[1])
    else:
        ts0, ts1 = d_start, d_end

    agg = st.selectbox("Tổng hợp AQI theo trạm", ["Median", "Mean", "Max"])

    st.divider()
    st.markdown("**🏭 Lọc theo trạm**")
    stn_tbl   = df_st[["station_slug", "station_name"]].drop_duplicates().sort_values("station_name")
    stn_names = stn_tbl["station_name"].tolist()
    n2slug    = dict(zip(stn_tbl["station_name"], stn_tbl["station_slug"]))
    sel_names = st.multiselect("Chọn trạm (bỏ trống = tất cả)", stn_names)
    sel_slugs = [n2slug[n] for n in sel_names] if sel_names else []
    top_n     = st.slider("Top N trạm", 3, 15, 7)

    st.divider()
    st.markdown("**🔗 Scatter tương quan**")
    sc_x = st.selectbox("Trục X", NON_AQI, index=0)
    sc_y = st.selectbox("Trục Y", NON_AQI, index=1)

    st.divider()
    st.caption("HCMC Air Quality Monitor · 2022–2026")

# ── Filter ──
df_cf = df_city[(df_city["date"] >= ts0) & (df_city["date"] <= ts1)].copy()
df_sf = df_st[(df_st["date"] >= ts0)   & (df_st["date"] <= ts1)].copy()
if sel_slugs:
    df_sf = df_sf[df_sf["station_slug"].isin(sel_slugs)].copy()

# ── KPI compute ──
cq       = df_cf["AQI"].dropna()
lr       = df_cf[df_cf["AQI"].notna()].sort_values("date").tail(1)
lat_aqi  = float(lr["AQI"].iloc[0]) if not lr.empty else None
lat_date = lr["date"].iloc[0].strftime("%d/%m/%Y") if not lr.empty else "N/A"
lat_cat  = aqi_cat(lat_aqi)
avg_aqi  = cq.mean() if len(cq) else None
max_aqi  = cq.max()  if len(cq) else None
good_pct = (cq <= 50).mean()  * 100 if len(cq) else 0
bad_pct  = (cq > 150).mean()  * 100 if len(cq) else 0
n_st     = df_sf["station_name"].nunique()
n_days   = df_cf["date"].nunique()

# ── Header ──
st.markdown(f"""
<div class="dash-header">
  <div>
    <div class="dash-title">HCMC AIR QUALITY DASHBOARD</div>
    <div class="dash-subtitle">TP. Hồ Chí Minh · City + {n_st} Trạm · 2022–2026</div>
  </div>
  <div class="dash-badge">LIVE DATA</div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ──
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-accent" style="background:{AQI_SLICE.get(lat_cat,'#94a3b8')}"></div>
    <div class="kpi-label">AQI mới nhất</div>
    <div class="kpi-value {kpi_cls(lat_aqi,50,150)}">{fmt(lat_aqi,0)}</div>
    <div class="kpi-sub">{lat_cat} · {lat_date}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#2563eb"></div>
    <div class="kpi-label">AQI trung bình</div>
    <div class="kpi-value {kpi_cls(avg_aqi,50,100)}">{fmt(avg_aqi)}</div>
    <div class="kpi-sub">Trong kỳ lọc</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:{aqi_hex(max_aqi)}"></div>
    <div class="kpi-label">AQI cao nhất</div>
    <div class="kpi-value kpi-bad">{fmt(max_aqi,0)}</div>
    <div class="kpi-sub">{aqi_cat(max_aqi)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#16a34a"></div>
    <div class="kpi-label">% Ngày tốt</div>
    <div class="kpi-value kpi-good">{good_pct:.1f}%</div>
    <div class="kpi-sub">AQI ≤ 50</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#b91c1c"></div>
    <div class="kpi-label">% Ngày xấu</div>
    <div class="kpi-value {kpi_cls(bad_pct,10,30)}">{bad_pct:.1f}%</div>
    <div class="kpi-sub">AQI > 150</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#7c3aed"></div>
    <div class="kpi-label">Trạm / Ngày</div>
    <div class="kpi-value kpi-blue">{n_st}</div>
    <div class="kpi-sub">{n_days} ngày quan trắc</div>
  </div>
</div>
""", unsafe_allow_html=True)


def sec(icon: str, text: str):
    st.markdown(
        f'<div class="chart-title"><span class="ct-bar"></span>{icon} {text}</div>',
        unsafe_allow_html=True,
    )


sep = '<div class="section-sep"></div>'

# ── ROW 1 ──
c1, c2 = st.columns([2.2, 1], gap="small")
with c1:
    sec("📈", "Xu hướng AQI – City Level (Daily + 7-Day MA)")
    if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_trend(df_cf), use_container_width=True, config=CHART_CFG)
    else:
        st.info("Không có dữ liệu AQI trong khoảng đã chọn.")
with c2:
    sec("🎯", "Phân bổ AQI Category")
    if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_donut(df_cf), use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")

st.markdown(sep, unsafe_allow_html=True)

# ── ROW 2 ──
c3, c4 = st.columns([1.3, 1], gap="small")
with c3:
    sec("🗓️", "Heatmap AQI TB – Tháng × Năm")
    if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_heatmap(df_cf), use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")
with c4:
    sec("📅", "AQI TB theo Tháng, so sánh qua các Năm")
    if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_monthly_bar(df_cf), use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")

st.markdown(sep, unsafe_allow_html=True)

# ── ROW 3 ──
has_st = not df_sf.empty and df_sf["AQI"].notna().sum() > 0
c5, c6, c7 = st.columns([1, 1.4, 1.2], gap="small")
with c5:
    sec("🏭", f"Top {top_n} Trạm ô nhiễm ({agg})")
    if has_st:
        st.plotly_chart(chart_top_stations(df_sf, agg, top_n),
                        use_container_width=True, config=CHART_CFG)
    else:
        st.info("Không đủ dữ liệu AQI theo trạm.")
with c6:
    sec("📦", f"Phân phối AQI – Box Plot")
    if has_st:
        st.plotly_chart(chart_boxplot(df_sf, top_n),
                        use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")
with c7:
    sec("🕸️", f"Radar Profile – Top {min(top_n,6)} Trạm")
    if not df_sf.empty:
        fig_r = chart_radar(df_sf, min(top_n, 6))
        if fig_r.data:
            st.plotly_chart(fig_r, use_container_width=True, config=CHART_CFG)
        else:
            st.info("Không đủ dữ liệu cho radar.")
    else:
        st.info("—")

st.markdown(sep, unsafe_allow_html=True)

# ── ROW 4 ──
sec("🔗", f"Tương quan {sc_x} vs {sc_y} – Station Level (màu theo AQI Category)")
if not df_sf.empty and sc_x in df_sf.columns and sc_y in df_sf.columns:
    fig_sc = chart_scatter(df_sf, sc_x, sc_y)
    if fig_sc.data:
        st.plotly_chart(fig_sc, use_container_width=True, config=CHART_CFG)
    else:
        st.info(f"Không đủ dữ liệu cho cặp {sc_x} – {sc_y}.")
else:
    st.info(f"Cột {sc_x} hoặc {sc_y} không tồn tại trong dữ liệu trạm.")

# ── Footer ──
st.markdown("""
<div style="text-align:center;padding:20px 0 8px;font-size:10px;
     color:#94a3b8;font-family:'JetBrains Mono',monospace;letter-spacing:2px;">
  HCMC AIR QUALITY MONITOR · CITY CSV + STATIONS CSV · 2022 – 2026
</div>
""", unsafe_allow_html=True)