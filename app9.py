# -*- coding: utf-8 -*-
"""
HCMC Air Quality Monitoring Dashboard
- Tab Dashboard: KPI + station cards (click → EDA station) + city trend + station detail
- Tab EDA: charts theo city hoặc station được chọn
- Light theme, st.container(border=True) cho chart panels
- fillcolor rgba() compatible
"""

from datetime import date
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────
CITY_CSV     = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"
STATIONS_CSV = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"

NON_AQI = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
ALL_COL = ["AQI"] + NON_AQI

AQI_BANDS = [
    (0,   50,  "#16a34a", "Good"),
    (51,  100, "#ca8a04", "Moderate"),
    (101, 150, "#ea580c", "USG"),
    (151, 200, "#dc2626", "Unhealthy"),
    (201, 300, "#7e22ce", "Very Unhealthy"),
    (301, 999, "#7f1d1d", "Hazardous"),
]

# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stApp"] {
    background: #f0f4f8 !important;
    font-family: 'Inter', sans-serif !important;
    color: #1a202c !important;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"]  { display: none !important; }
[data-testid="stMainBlockContainer"] { padding: 0 1.5rem 2rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"]     { display: none !important; }
.block-container { padding-top: 0 !important; }

/* ── White widgets ── */
div[data-baseweb="select"],
div[data-baseweb="select"] > div,
div[data-baseweb="input"],
div[data-baseweb="base-input"],
[data-testid="stDateInput"] div,
input, textarea {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #1a202c !important;
}
ul[data-baseweb="menu"], li[data-baseweb="menu-item"],
div[role="listbox"], div[role="option"] {
    background: #ffffff !important; color: #1a202c !important;
}
li[data-baseweb="menu-item"]:hover { background: #eff6ff !important; }
div[data-baseweb="select"] span,
div[data-baseweb="select"] p { color: #1a202c !important; }

/* ── Widget labels ── */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
.stSelectbox label, .stDateInput label, .stCheckbox label,
.stRadio label, div[role="radiogroup"] label,
div[role="radiogroup"] span, div[role="radiogroup"] p {
    color: #1a202c !important; font-weight: 600 !important;
}
div[role="radiogroup"] label:has(input:checked) span { color: #2563eb !important; }

/* ── All text dark ── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] { color: #1a202c !important; }

/* ── Container border style ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}
/* Remove stray empty blocks */
[data-testid="stVerticalBlock"] > div:empty { display: none !important; }
[data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
div[data-testid="stHorizontalBlock"] { gap: 12px !important; }

/* ── Navbar ── */
.navbar {
    position: sticky; top: 0; z-index: 999;
    background: #ffffff; border-bottom: 1px solid #e2e8f0;
    padding: 0 28px; height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 -1.5rem 0;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}
.nb-left  { display: flex; align-items: center; gap: 10px; }
.nb-logo  { color: #2563eb; font-size: 22px; }
.nb-brand { color: #1a202c !important; font-size: 14px; font-weight: 700; }
.nb-right { display: flex; gap: 8px; }
.nb-btn   { background: none; border: 1px solid #e2e8f0; color: #4a5568 !important;
            font-size: 13px; padding: 6px 14px; border-radius: 6px; cursor: pointer; }
.nb-btn-p { background: #2563eb; border: none; color: #fff !important;
            font-size: 13px; font-weight: 600; padding: 6px 14px; border-radius: 6px; cursor: pointer; }

/* ── Hero ── */
.hero { padding: 18px 0 12px; }
.hero h1 { font-size: 26px; font-weight: 800; color: #1a202c !important; margin: 0 0 4px; }
.hero p  { font-size: 13px; color: #718096 !important; margin: 0; }

/* ── KPI cards ── */
.kpi-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card {
    background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 16px 20px; display: flex; justify-content: space-between;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.kpi-lbl  { font-size: 10px; font-weight: 700; letter-spacing: 1px;
            color: #718096 !important; text-transform: uppercase; margin-bottom: 8px; }
.kpi-val  { font-size: 36px; font-weight: 800; font-family: 'JetBrains Mono', monospace;
            color: #1a202c !important; line-height: 1; }
.kpi-bdg  { display: inline-block; font-size: 11px; font-weight: 600;
            padding: 2px 9px; border-radius: 20px; margin-top: 6px; border: 1px solid; }
.kpi-ico  { font-size: 20px; opacity: 0.4; }

/* ── Section heading ── */
.sec-head { font-size: 17px; font-weight: 700; color: #1a202c !important; margin: 16px 0 10px; }

/* ── Station cards ── */
.stn-card {
    background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow .2s, border-color .2s;
}
.stn-card:hover { box-shadow: 0 4px 14px rgba(37,99,235,0.1); border-color: #bfdbfe; }
.stn-hdr  { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2px; }
.stn-name { font-size: 13px; font-weight: 700; color: #1a202c !important; }
.stn-addr { font-size: 11px; color: #a0aec0 !important; margin-bottom: 10px; }
.stn-aqi  { font-size: 40px; font-weight: 800; font-family: 'JetBrains Mono', monospace;
            color: #1a202c !important; line-height: 1; margin-bottom: 4px; }
.stn-bdg  { display: inline-block; font-size: 10px; font-weight: 700;
            padding: 2px 9px; border-radius: 20px; margin-bottom: 10px; border: 1px solid; }
.stn-div  { height: 1px; background: #e2e8f0; margin-bottom: 10px; }
.stn-row  { display: flex; gap: 18px; }
.stn-plbl { font-size: 10px; color: #a0aec0 !important; text-transform: uppercase; margin-bottom: 2px; }
.stn-pval { font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace;
            color: #2d3748 !important; }
.live-bdg { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0;
            font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; }
.nd-bdg   { background: #f7fafc; color: #a0aec0; border: 1px solid #e2e8f0;
            font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; }

/* ── Reference chips ── */
.ref-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.ref-ttl { font-size: 10px; font-weight: 700; color: #718096 !important;
           text-transform: uppercase; letter-spacing: 0.8px; }
.ref-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 11px;
            font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid; }
.ref-dot  { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }

/* ── EDA station selector ── */
.stn-sel-bar {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 10px; padding: 10px 16px; margin-bottom: 14px;
    display: flex; align-items: center; gap: 10px;
}
.stn-sel-label { font-size: 12px; font-weight: 600; color: #1d4ed8 !important; }
.stn-sel-name  { font-size: 13px; font-weight: 700; color: #1a202c !important; }

/* ── Chart panel titles (inside containers) ── */
.cp-title { font-size: 14px; font-weight: 700; color: #1a202c !important; margin: 0 0 2px; }
.cp-sub   { font-size: 11px; color: #718096 !important; margin: 0 0 6px; }

/* ── Plotly ── */
.stPlotlyChart { border-radius: 8px; overflow: hidden; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #f0f4f8; }
::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 4px; }
</style>
"""

# ──────────────────────────────────────────────
# PLOTLY THEME
# ──────────────────────────────────────────────
_CFG = dict(displayModeBar=False)
_PL  = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#f8fafc",
    font=dict(family="Inter, sans-serif", color="#4a5568", size=11),
    margin=dict(l=8, r=8, t=8, b=8),
    legend=dict(bgcolor="rgba(255,255,255,0.95)", bordercolor="#e2e8f0",
                borderwidth=1, font=dict(size=10, color="#1a202c")),
)
_AX = dict(gridcolor="#e2e8f0", zeroline=False, linecolor="#cbd5e0",
           tickfont=dict(size=9, color="#718096"))

def _theme(fig):
    fig.update_layout(**_PL); fig.update_xaxes(**_AX); fig.update_yaxes(**_AX)
    return fig

# ──────────────────────────────────────────────
# UTILS
# ──────────────────────────────────────────────
def _num(df, cols):
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def aqi_info(v):
    try:
        val = float(v)
        if np.isnan(val): return "N/A", "#a0aec0"
    except: return "N/A", "#a0aec0"
    for lo, hi, color, label in AQI_BANDS:
        if lo <= val <= hi: return label, color
    return "N/A", "#a0aec0"

def _fmt(v, dec=1):
    try:
        f = float(v); return f"{f:.{dec}f}" if not np.isnan(f) else "—"
    except: return "—"

def _rgba(h, a=0.15):
    hx = h.lstrip("#")
    r, g, b = int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16)
    return f"rgba({r},{g},{b},{a})"

def _corr(df, x, y):
    t = df[[x,y]].dropna()
    return float(t[x].corr(t[y])) if len(t) >= 3 else float("nan")

def _iqr_out(s):
    q1, q3 = s.quantile(.25), s.quantile(.75)
    iqr = q3 - q1
    return int(((s < q1-1.5*iqr) | (s > q3+1.5*iqr)).sum())

# ──────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_city():
    df = pd.read_csv(CITY_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return _num(df.dropna(subset=["date"]), ALL_COL).sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=600)
def get_stations():
    df = pd.read_csv(STATIONS_CSV)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    if "station_name" not in df.columns: df["station_name"] = df["station_slug"]
    return _num(df.dropna(subset=["date"]), ALL_COL).sort_values(["station_name","date"]).reset_index(drop=True)

# ──────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────
def _aqi_bands(fig):
    for lo, hi, c, _ in AQI_BANDS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.06, layer="below", line_width=0)

def chart_trend(df, col="AQI", ylab="AQI"):
    v = df[["date", col]].dropna().sort_values("date")
    r = v.set_index("date")[col].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    if col == "AQI": _aqi_bands(fig)
    fig.add_trace(go.Scatter(x=v["date"], y=v[col], name=col,
        mode="lines", line=dict(color="#93c5fd", width=1.2), opacity=0.7))
    fig.add_trace(go.Scatter(x=r["date"], y=r[col], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.5)))
    _theme(fig)
    fig.update_layout(hovermode="x unified", yaxis_title=ylab,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    return fig

def chart_radar(df, station):
    avail = [c for c in NON_AQI if c in df.columns and df[c].notna().sum() > 5]
    if len(avail) < 3: return go.Figure()
    sub   = df[df["station_name"]==station][avail].mean()
    all_m = df[avail].mean()
    scale = all_m.replace(0, np.nan)
    ns = (sub/scale).fillna(0).clip(0,2)
    nc = (all_m/scale).fillna(0).clip(0,2)
    cats = avail + [avail[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=nc.tolist()+[nc.iloc[0]], theta=cats,
        name="City Avg", fill="toself", opacity=0.4,
        line=dict(color="#94a3b8", width=1.5), fillcolor="rgba(148,163,184,0.15)"))
    fig.add_trace(go.Scatterpolar(r=ns.tolist()+[ns.iloc[0]], theta=cats,
        name=station[:22], fill="toself", opacity=0.7,
        line=dict(color="#2563eb", width=2), fillcolor="rgba(37,99,235,0.18)"))
    _theme(fig)
    fig.update_layout(
        polar=dict(bgcolor="#f8fafc",
            radialaxis=dict(visible=True, range=[0,2],
                tickfont=dict(size=8, color="#94a3b8"), gridcolor="#e2e8f0", linecolor="#e2e8f0"),
            angularaxis=dict(tickfont=dict(size=9, color="#4a5568"), gridcolor="#e2e8f0")),
        legend=dict(font=dict(size=10, color="#1a202c")))
    return fig

def chart_aqi_freq(df):
    order = [l for _,_,_,l in AQI_BANDS]
    cats  = df["AQI"].dropna().apply(lambda x: aqi_info(x)[0]).value_counts()
    cats  = cats.reindex([c for c in order if c in cats.index])
    cols  = [next((c for _,_,c,l in AQI_BANDS if l==k), "#94a3b8") for k in cats.index]
    fig   = go.Figure(go.Bar(
        x=cats.values, y=cats.index, orientation="h",
        marker=dict(color=cols, line=dict(width=0)),
        text=cats.values, textposition="outside",
        textfont=dict(color="#1a202c", size=10),
        hovertemplate="%{y}: %{x} ngày<extra></extra>"))
    _theme(fig)
    fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
    return fig

def chart_scatter(df, x_col, y_col, tl=True):
    if x_col not in df.columns or y_col not in df.columns: return go.Figure()
    tmp = df[[x_col, y_col, "AQI"]].dropna().copy()
    if tmp.empty: return go.Figure()
    tmp["cat"] = tmp["AQI"].apply(lambda v: aqi_info(v)[0])
    clr = {l: c for _,_,c,l in AQI_BANDS}
    r   = _corr(tmp, x_col, y_col)
    fig = px.scatter(tmp, x=x_col, y=y_col, color="cat",
        category_orders={"cat": [l for _,_,_,l in AQI_BANDS]},
        color_discrete_map=clr, opacity=0.7,
        trendline="ols" if tl else None)
    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
    _theme(fig)
    fig.update_layout(legend=dict(title=None, font=dict(size=10)),
        annotations=[dict(x=0.02, y=0.97, xref="paper", yref="paper",
            text=f"r = {r:.3f}" if not np.isnan(r) else "r = N/A",
            showarrow=False, font=dict(size=12, color="#1d4ed8", family="JetBrains Mono"),
            bgcolor="rgba(219,234,254,0.95)", bordercolor="#3b82f6", borderwidth=1, borderpad=6)])
    return fig

def chart_pollutant_ts(df, col):
    tmp = df[["date", col]].dropna().sort_values("date")
    if tmp.empty: return go.Figure()
    r = tmp.set_index("date")[col].rolling(7, min_periods=1).mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tmp["date"], y=tmp[col], name=col,
        mode="lines", line=dict(color="#93c5fd", width=1), opacity=0.5))
    fig.add_trace(go.Scatter(x=r["date"], y=r[col], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.2)))
    _theme(fig)
    fig.update_layout(hovermode="x unified", yaxis_title=col,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    return fig

def chart_heatmap(df):
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"]  = tmp["date"].dt.year
    pivot = tmp.pivot_table(index="year", columns="month", values="AQI", aggfunc="mean")
    ml  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    xl  = [ml[m-1] for m in pivot.columns]
    zv  = pivot.values.astype(float)
    txt = np.where(np.isnan(zv), "", np.round(zv,0).astype("int").astype("str"))
    fig = go.Figure(go.Heatmap(z=zv, x=xl, y=[str(y) for y in pivot.index],
        colorscale=[[0,"#22c55e"],[.25,"#eab308"],[.5,"#f97316"],[.75,"#ef4444"],[1,"#7f1d1d"]],
        zmin=0, zmax=150, text=txt, texttemplate="%{text}",
        textfont=dict(size=10, color="#1a202c"),
        hovertemplate="Năm %{y} – %{x}: AQI %{z:.1f}<extra></extra>",
        showscale=True,
        colorbar=dict(thickness=10, len=.85,
            tickfont=dict(size=9, color="#4a5568"),
            title=dict(text="AQI", font=dict(color="#4a5568", size=10)))))
    _theme(fig)
    return fig

def chart_boxplot(df):
    order = df.groupby("station_name")["AQI"].median().dropna().sort_values(ascending=False).index
    pal   = ["#2563eb","#16a34a","#ca8a04","#dc2626","#7e22ce",
             "#0891b2","#059669","#ea580c","#c026d3","#d97706"]
    fig   = go.Figure()
    for i, stn in enumerate(order):
        vals  = df[df["station_name"]==stn]["AQI"].dropna()
        if len(vals) < 2: continue
        c     = pal[i % len(pal)]
        short = stn[:22]+"…" if len(stn)>22 else stn
        fig.add_trace(go.Box(x=vals, y=[short]*len(vals), name=short,
            orientation="h", boxmean=True,
            marker=dict(size=3, opacity=0.4, color=c),
            line=dict(color=c, width=1.5),
            hovertemplate=f"<b>{stn}</b><br>AQI: %{{x:.0f}}<extra></extra>"))
    _theme(fig)
    fig.update_layout(showlegend=False, hovermode="closest",
                      yaxis=dict(autorange="reversed"))
    return fig

def chart_yearly(df_city, df_st):
    pal = ["#2563eb","#16a34a","#ca8a04","#dc2626","#7e22ce",
           "#0891b2","#059669","#ea580c","#c026d3"]
    fig = go.Figure()
    cg  = df_city.copy(); cg["year"] = cg["date"].dt.year
    cy  = cg.groupby("year")["AQI"].mean().reset_index()
    fig.add_trace(go.Scatter(x=cy["year"], y=cy["AQI"], name="City (AQICN)",
        mode="lines+markers", line=dict(color="#1a202c", width=3),
        marker=dict(size=7, color="#1a202c")))
    sg = df_st.copy(); sg["year"] = sg["date"].dt.year
    for i, stn in enumerate(sg["station_name"].unique()):
        sub = sg[sg["station_name"]==stn].groupby("year")["AQI"].mean().reset_index()
        if sub["AQI"].notna().sum() < 2: continue
        short = stn[:20]+"…" if len(stn)>20 else stn
        fig.add_trace(go.Scatter(x=sub["year"], y=sub["AQI"], name=short,
            mode="lines+markers",
            line=dict(color=pal[i%len(pal)], width=1.5, dash="dot"),
            marker=dict(size=5)))
    _theme(fig)
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=1),
        yaxis_title="AQI TB theo năm", legend=dict(font=dict(size=10)))
    return fig

def chart_missing(df):
    poll = [c for c in ALL_COL if c in df.columns]
    miss = df.groupby("station_name")[poll].apply(lambda g: g.isna().mean()*100)
    fig  = go.Figure(go.Heatmap(z=miss.values, x=miss.columns.tolist(),
        y=[s[:22]+"…" if len(s)>22 else s for s in miss.index],
        colorscale=[[0,"#22c55e"],[.5,"#eab308"],[1,"#dc2626"]],
        zmin=0, zmax=100,
        text=np.round(miss.values,0).astype("int").astype("str"),
        texttemplate="%{text}%", textfont=dict(size=9, color="#1a202c"),
        hovertemplate="%{y} – %{x}: %{z:.1f}% missing<extra></extra>",
        showscale=True, colorbar=dict(thickness=10, ticksuffix="%",
            tickfont=dict(size=9, color="#4a5568"))))
    _theme(fig)
    return fig

# ──────────────────────────────────────────────
# STATION DETAIL EDA (shared between tabs)
# ──────────────────────────────────────────────
def render_station_eda(df_st_full, station_name, df_city_full):
    """Render full EDA for a single station."""
    df_s = df_st_full[df_st_full["station_name"] == station_name].copy()

    ref_chips = "".join([
        f'<span class="ref-chip" style="color:{c};border-color:{c};background:{_rgba(c,.12)}">'
        f'<span class="ref-dot" style="background:{c}"></span>{l}</span>'
        for _,_,c,l in AQI_BANDS
    ])
    st.markdown(f'<div class="ref-bar"><span class="ref-ttl">AQI Reference:</span>{ref_chips}</div>',
                unsafe_allow_html=True)

    # ROW 1: AQI trend + Radar
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.markdown(f'<p class="cp-title">📈 AQI Trend – {station_name}</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Daily AQI + 7-day rolling average</p>', unsafe_allow_html=True)
            fig_t = chart_trend(df_s)
            if fig_t.data: st.plotly_chart(fig_t, use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu AQI.")
    with c2:
        with st.container(border=True):
            st.markdown('<p class="cp-title">🕸️ Pollutant Profile vs City Avg</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Chuẩn hóa theo trung bình toàn mạng lưới</p>', unsafe_allow_html=True)
            fig_r = chart_radar(df_st_full, station_name)
            if fig_r.data: st.plotly_chart(fig_r, use_container_width=True, config=_CFG)
            else: st.info("Không đủ dữ liệu.")

    # ROW 2: AQI Freq + Scatter
    c3, c4 = st.columns([1, 1.6])
    with c3:
        with st.container(border=True):
            st.markdown('<p class="cp-title">🎯 AQI Frequency</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Phân bố số ngày theo mức AQI</p>', unsafe_allow_html=True)
            fig_fr = chart_aqi_freq(df_s)
            if fig_fr.data: st.plotly_chart(fig_fr, use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")
    with c4:
        with st.container(border=True):
            sx = st.selectbox("Trục X", NON_AQI, index=0, key=f"sx_{station_name}")
            sy = st.selectbox("Trục Y", NON_AQI, index=1, key=f"sy_{station_name}")
            tl = st.checkbox("Trend line", value=True, key=f"tl_{station_name}")
            st.markdown(f'<p class="cp-title">🔗 Correlation: {sx} vs {sy}</p>', unsafe_allow_html=True)
            fig_sc = chart_scatter(df_s, sx, sy, tl)
            if fig_sc.data: st.plotly_chart(fig_sc, use_container_width=True, config=_CFG)
            else: st.info(f"Không có dữ liệu {sx}/{sy}.")

    # ROW 3: Pollutant time series per column
    avail_poll = [c for c in NON_AQI if c in df_s.columns and df_s[c].notna().sum() > 5]
    if avail_poll:
        st.markdown('<p class="sec-head">📊 Diễn biến từng chỉ số theo thời gian</p>', unsafe_allow_html=True)
        poll_col = st.selectbox("Chọn chỉ số", avail_poll, key=f"poll_{station_name}")
        with st.container(border=True):
            st.markdown(f'<p class="cp-title">📊 {poll_col} – {station_name}</p>', unsafe_allow_html=True)
            fig_p = chart_pollutant_ts(df_s, poll_col)
            if fig_p.data: st.plotly_chart(fig_p, use_container_width=True, config=_CFG)
            else: st.info(f"Không có dữ liệu {poll_col}.")


# ──────────────────────────────────────────────
# CITY-LEVEL EDA
# ──────────────────────────────────────────────
def render_city_eda(df_city, df_st):
    ref_chips = "".join([
        f'<span class="ref-chip" style="color:{c};border-color:{c};background:{_rgba(c,.12)}">'
        f'<span class="ref-dot" style="background:{c}"></span>{l}</span>'
        for _,_,c,l in AQI_BANDS
    ])
    st.markdown(f'<div class="ref-bar"><span class="ref-ttl">AQI Reference:</span>{ref_chips}</div>',
                unsafe_allow_html=True)

    # ROW 1: AQI trend + AQI freq
    c1, c2 = st.columns([1.6, 1])
    with c1:
        with st.container(border=True):
            st.markdown('<p class="cp-title">📈 City AQI Trend</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Daily AQI + 7-day rolling average · Nguồn: AQICN</p>', unsafe_allow_html=True)
            fig_t = chart_trend(df_city)
            if fig_t.data: st.plotly_chart(fig_t, use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")
    with c2:
        with st.container(border=True):
            st.markdown('<p class="cp-title">🎯 AQI Frequency</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Phân bố số ngày theo mức AQI</p>', unsafe_allow_html=True)
            fig_fr = chart_aqi_freq(df_city)
            if fig_fr.data: st.plotly_chart(fig_fr, use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")

    # ROW 2: Heatmap + Yearly trend
    c3, c4 = st.columns([1, 1])
    with c3:
        with st.container(border=True):
            st.markdown('<p class="cp-title">🗓️ AQI Heatmap – Month × Year</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">City-level monthly average AQI</p>', unsafe_allow_html=True)
            if not df_city.empty and df_city["AQI"].notna().sum() > 0:
                st.plotly_chart(chart_heatmap(df_city), use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")
    with c4:
        with st.container(border=True):
            st.markdown('<p class="cp-title">📅 Yearly Mean AQI Trend</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">City index vs individual stations year-over-year</p>', unsafe_allow_html=True)
            if not df_city.empty:
                st.plotly_chart(chart_yearly(df_city, df_st), use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")

    # ROW 3: Boxplot + Missing
    c5, c6 = st.columns([1, 1])
    with c5:
        with st.container(border=True):
            st.markdown('<p class="cp-title">📦 AQI Distribution by Station</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Median, IQR and outliers per station</p>', unsafe_allow_html=True)
            if not df_st.empty and df_st["AQI"].notna().sum() > 0:
                st.plotly_chart(chart_boxplot(df_st), use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")
    with c6:
        with st.container(border=True):
            st.markdown('<p class="cp-title">🔍 Data Completeness (% Missing)</p>', unsafe_allow_html=True)
            st.markdown('<p class="cp-sub">Green = complete · Yellow = partial · Red = mostly missing</p>', unsafe_allow_html=True)
            if not df_st.empty:
                st.plotly_chart(chart_missing(df_st), use_container_width=True, config=_CFG)
            else: st.info("Không có dữ liệu.")

    # ROW 4: Pollutant time series city
    poll_choice = st.selectbox("Chỉ số theo thời gian", ["AQI"] + NON_AQI, key="city_poll")
    with st.container(border=True):
        st.markdown(f'<p class="cp-title">📊 {poll_choice} Time Series – City Level</p>', unsafe_allow_html=True)
        fig_p = chart_pollutant_ts(df_city, poll_choice)
        if fig_p.data: st.plotly_chart(fig_p, use_container_width=True, config=_CFG)
        else: st.info(f"Không có dữ liệu {poll_choice}.")


# ──────────────────────────────────────────────
# APP INIT
# ──────────────────────────────────────────────
st.set_page_config(page_title="Air Quality Monitoring – HCMC",
                   page_icon="🌫️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

with st.spinner("Loading data..."):
    try:    df_city = get_city()
    except Exception as e: st.error(f"Cannot load City CSV: {e}"); st.stop()
    try:    df_st   = get_stations()
    except Exception as e: st.error(f"Cannot load Stations CSV: {e}"); st.stop()

# ──────────────────────────────────────────────
# NAVBAR
# ──────────────────────────────────────────────
st.markdown("""
<div class="navbar">
  <div class="nb-left">
    <span class="nb-logo">⇌</span>
    <span class="nb-brand">Air Quality Monitoring – HCMC</span>
  </div>
  <div class="nb-right">
    <button class="nb-btn">🔔 Notifications</button>
    <button class="nb-btn-p">👤 Profile</button>
  </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# TAB SWITCHER
# ──────────────────────────────────────────────
tab = st.radio("", ["🏠 Dashboard", "📊 EDA"], horizontal=True, label_visibility="collapsed")
st.divider()

# ══════════════════════════════════════════════
#  DASHBOARD TAB
# ══════════════════════════════════════════════
if tab == "🏠 Dashboard":

    # ── Date filter ──
    st.markdown('<p class="sec-head" style="margin-top:0">🗓 Bộ lọc thời gian</p>', unsafe_allow_html=True)
    f1, f2 = st.columns([1.5, 3])
    with f1:
        d_range = st.date_input("", label_visibility="collapsed",
            value=(date(2024,1,1), date.today()),
            min_value=df_city["date"].min().date(),
            max_value=df_city["date"].max().date(), key="dash_dates")

    ts0 = pd.Timestamp(d_range[0] if isinstance(d_range,(list,tuple)) and len(d_range)==2 else df_city["date"].min())
    ts1 = pd.Timestamp(d_range[1] if isinstance(d_range,(list,tuple)) and len(d_range)==2 else df_city["date"].max())
    df_cf = df_city[(df_city["date"]>=ts0) & (df_city["date"]<=ts1)].copy()
    df_sf = df_st  [(df_st["date"]  >=ts0) & (df_st["date"]  <=ts1)].copy()

    # ── KPIs ──
    cq   = df_cf["AQI"].dropna()
    cavg = cq.mean() if len(cq) else None
    ccat, ccol = aqi_info(cavg)
    n_stn = df_sf["station_name"].nunique()
    n_bad = int((df_sf.groupby("station_name")["AQI"].mean().dropna() > 50).sum())

    st.markdown(f"""
    <div class="hero">
      <h1>Ho Chi Minh City Air Quality Dashboard</h1>
      <p>Giám sát chất lượng không khí tại {n_stn} trạm quan trắc TP.HCM</p>
    </div>
    <div class="kpi-row">
      <div class="kpi-card">
        <div>
          <div class="kpi-lbl">City Average AQI</div>
          <div class="kpi-val">{_fmt(cavg,0)}</div>
          <span class="kpi-bdg" style="color:{ccol};border-color:{ccol};background:{_rgba(ccol,.1)}">{ccat}</span>
        </div>
        <div class="kpi-ico">📈</div>
      </div>
      <div class="kpi-card">
        <div>
          <div class="kpi-lbl">Active Stations</div>
          <div class="kpi-val">{n_stn}</div>
          <span class="kpi-bdg" style="color:#16a34a;border-color:#16a34a;background:rgba(22,163,74,.1)">All Online</span>
        </div>
        <div class="kpi-ico">📍</div>
      </div>
      <div class="kpi-card">
        <div>
          <div class="kpi-lbl">Unhealthy Areas</div>
          <div class="kpi-val">{n_bad}</div>
          <span class="kpi-bdg" style="color:#dc2626;border-color:#dc2626;background:rgba(220,38,38,.1)">AQI &gt; 50</span>
        </div>
        <div class="kpi-ico">⚠️</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── City trend ──
    with st.container(border=True):
        st.markdown('<p class="cp-title">📈 City-level AQI Trend</p>', unsafe_allow_html=True)
        st.markdown('<p class="cp-sub">Daily AQI + 7-day rolling average · Nguồn: AQICN city index</p>', unsafe_allow_html=True)
        if not df_cf.empty and df_cf["AQI"].notna().sum() > 0:
            st.plotly_chart(chart_trend(df_cf), use_container_width=True, config=_CFG)
        else:
            st.info("Không có dữ liệu trong khoảng thời gian đã chọn.")

    # ── Station Cards ──
    st.markdown('<p class="sec-head">Monitoring Stations</p>', unsafe_allow_html=True)

    stations = df_sf["station_name"].unique().tolist()

    def _stn_card(name):
        sub   = df_sf[df_sf["station_name"]==name].sort_values("date")
        last  = sub.dropna(subset=["AQI"]).tail(1)
        av    = float(last["AQI"].iloc[0]) if not last.empty else None
        cat, col = aqi_info(av)
        badge = '<span class="live-bdg">LIVE</span>' if av is not None else '<span class="nd-bdg">NO DATA</span>'
        def _p(c):
            if last.empty or c not in last.columns: return "—"
            v = last[c].iloc[0]; return _fmt(v,0) if pd.notna(v) else "—"
        return f"""<div class="stn-card">
  <div class="stn-hdr"><div class="stn-name">{name}</div>{badge}</div>
  <div class="stn-addr">Ho Chi Minh City</div>
  <div class="stn-aqi">{_fmt(av,0) if av else "—"}</div>
  <span class="stn-bdg" style="color:{col};border-color:{col};background:{_rgba(col,.1)}">{cat}</span>
  <div class="stn-div"></div>
  <div class="stn-row">
    <div><div class="stn-plbl">PM2.5</div><div class="stn-pval">{_p("PM2,5")}</div></div>
    <div><div class="stn-plbl">PM10</div><div class="stn-pval">{_p("PM10")}</div></div>
    <div><div class="stn-plbl">O3</div><div class="stn-pval">{_p("O3")}</div></div>
  </div>
</div>"""

    # Render 3 cards per row — no buttons, just cards
    for i in range(0, len(stations), 3):
        batch = stations[i:i+3]
        cols  = st.columns(3)
        for co, stn in zip(cols, batch):
            with co:
                st.markdown(_stn_card(stn), unsafe_allow_html=True)

    # ── Selected station detail (trend + radar) ──
    st.divider()
    st.markdown('<p class="sec-head">Station Detail View</p>', unsafe_allow_html=True)
    sel = st.selectbox("Chọn trạm", stations, key="det_stn")
    if sel:
        d1, d2 = st.columns([2, 1])
        with d1:
            with st.container(border=True):
                st.markdown(f'<p class="cp-title">📈 AQI Trend – {sel}</p>', unsafe_allow_html=True)
                sub_s = df_sf[df_sf["station_name"]==sel][["date","AQI"]].dropna().sort_values("date")
                if not sub_s.empty:
                    roll = sub_s.set_index("date")["AQI"].rolling(7,min_periods=1).mean().reset_index()
                    fig2 = go.Figure()
                    _aqi_bands(fig2)
                    fig2.add_trace(go.Scatter(x=sub_s["date"], y=sub_s["AQI"], name="AQI Daily",
                        mode="lines", line=dict(color="#93c5fd", width=1.2), opacity=0.65))
                    fig2.add_trace(go.Scatter(x=roll["date"], y=roll["AQI"], name="7-day MA",
                        mode="lines", line=dict(color="#1d4ed8", width=2.5)))
                    _theme(fig2)
                    fig2.update_layout(hovermode="x unified", yaxis_title="AQI",
                        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
                    st.plotly_chart(fig2, use_container_width=True, config=_CFG)
                else:
                    st.info("Không có dữ liệu AQI.")
        with d2:
            with st.container(border=True):
                st.markdown('<p class="cp-title">🕸️ Pollutant Profile</p>', unsafe_allow_html=True)
                fig_r = chart_radar(df_sf, sel)
                if fig_r.data: st.plotly_chart(fig_r, use_container_width=True, config=_CFG)
                else: st.info("Không đủ dữ liệu.")


# ══════════════════════════════════════════════
#  EDA TAB
# ══════════════════════════════════════════════
else:
    st.markdown("""
    <div class="hero">
      <h1>Exploratory Data Analysis</h1>
      <p>Phân tích sâu tương quan chỉ số ô nhiễm, phân bố AQI và biến thiên theo trạm quan trắc</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Source selector: City / Station ──
    eda_mode = st.radio("Nguồn dữ liệu EDA", ["🏙️ Toàn thành phố", "📍 Theo trạm"],
                        horizontal=True, label_visibility="visible", key="eda_mode")

    # ── Date filter ──
    fe1, fe2 = st.columns([2, 3])
    with fe1:
        dr2 = st.date_input("Khoảng thời gian",
            value=(date(2022,1,1), date.today()),
            min_value=df_city["date"].min().date(),
            max_value=df_city["date"].max().date(), key="edr")
        ta = pd.Timestamp(dr2[0] if isinstance(dr2,(list,tuple)) and len(dr2)==2 else df_city["date"].min())
        tb = pd.Timestamp(dr2[1] if isinstance(dr2,(list,tuple)) and len(dr2)==2 else df_city["date"].max())

    df_ca = df_city[(df_city["date"]>=ta) & (df_city["date"]<=tb)].copy()
    df_sa = df_st  [(df_st["date"]  >=ta) & (df_st["date"]  <=tb)].copy()

    if eda_mode == "🏙️ Toàn thành phố":
        render_city_eda(df_ca, df_sa)

    else:
        # ── Station picker ──
        all_stns = df_sa["station_name"].unique().tolist()
        chosen = st.selectbox("Chọn trạm", all_stns, key="eda_stn_pick")

        # Banner
        st.markdown(f"""
        <div class="stn-sel-bar">
          <span class="stn-sel-label">📍 Đang xem EDA của trạm:</span>
          <span class="stn-sel-name">{chosen}</span>
        </div>""", unsafe_allow_html=True)

        render_station_eda(df_sa, chosen, df_ca)

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:20px 0 8px;
     font-family:'JetBrains Mono',monospace;font-size:10px;
     color:#cbd5e0;letter-spacing:2px;">
  AIR QUALITY MONITORING – HCMC · 2022–2026 · AQICN DATA
</div>
""", unsafe_allow_html=True)