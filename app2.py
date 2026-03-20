# -*- coding: utf-8 -*-
"""
HCMC Air Quality Dashboard – Light Theme, Fixed AQI Logic
- AQI dùng đúng cột 'AQI' từ CSV (không compute lại từ pollutants)
- Stations date format: dd/MM/yyyy
- Plotly titles truyền rỗng tránh 'undefined'
"""

from datetime import date
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =============================
# CONFIG
# =============================
NON_AQI = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
ALL_METRICS = ["AQI"] + NON_AQI

AQI_COLORS = {
    "Good":          "#2ecc71",
    "Moderate":      "#f1c40f",
    "USG":           "#e67e22",
    "Unhealthy":     "#e74c3c",
    "Very Unhealthy":"#8e44ad",
    "Hazardous":     "#641e16",
}

STATIONS_CSV_PATH = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"
CITY_CSV_PATH     = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"

# =============================
# LIGHT THEME CSS
# =============================
LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stApp"] {
    background: #f0f2f8 !important;
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: #1a2035;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] label {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    color: #64748b !important;
    text-transform: uppercase !important;
}

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
    color: #94a3b8;
    margin-top: 2px;
    letter-spacing: 0.5px;
}
.dash-badge {
    background: #dbeafe;
    color: #1e40af;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    padding: 4px 10px;
    border-radius: 20px;
    font-weight: 600;
    letter-spacing: 1px;
}

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
    letter-spacing: 1.5px; color: #94a3b8;
    text-transform: uppercase; margin-bottom: 6px;
}
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 26px; font-weight: 700;
    color: #1a2035; line-height: 1; margin-bottom: 4px;
}
.kpi-sub { font-size: 11px; color: #94a3b8; }
.kpi-good  { color: #16a34a !important; }
.kpi-warn  { color: #d97706 !important; }
.kpi-bad   { color: #dc2626 !important; }
.kpi-blue  { color: #2563eb !important; }

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
    background: linear-gradient(90deg, transparent, #e2e8f0 20%, #e2e8f0 80%, transparent);
    margin: 8px 0 16px;
}

.stPlotlyChart { border-radius: 8px; overflow: hidden; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #f0f2f8; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
</style>
"""

# =============================
# PLOTLY THEME
# =============================
CHART_CFG = dict(displayModeBar=False)

BASE_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155", size=11),
    margin=dict(l=8, r=8, t=8, b=8),
    legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#e2e8f0",
                borderwidth=1, font=dict(size=10)),
)

AXIS_STYLE = dict(gridcolor="#f1f5f9", zeroline=False,
                  linecolor="#e2e8f0", tickfont=dict(size=9, color="#94a3b8"))


def apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**BASE_LAYOUT)
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    return fig


# =============================
# UTILS
# =============================

def safe_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def aqi_category(aqi) -> str:
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
    return AQI_COLORS.get(aqi_category(aqi), "#94a3b8")


def kpi_cls(val, lo, hi) -> str:
    try:
        v = float(val)
        if np.isnan(v): return ""
        return "kpi-good" if v <= lo else ("kpi-warn" if v <= hi else "kpi-bad")
    except Exception:
        return ""


def corr_val(df: pd.DataFrame, x: str, y: str) -> float:
    tmp = df[[x, y]].dropna()
    return float(tmp[x].corr(tmp[y])) if len(tmp) >= 3 else float("nan")


def fmt(v, dec=1) -> str:
    try:
        return f"{float(v):.{dec}f}" if v is not None and not np.isnan(float(v)) else "N/A"
    except Exception:
        return "N/A"


# =============================
# PREPROCESS
# =============================

def preprocess_city(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if "year" not in df.columns:
        df["year"] = df["date"].dt.year
    df = safe_numeric(df, ALL_METRICS)
    # ✅ Giữ nguyên cột AQI — KHÔNG tính lại từ pollutants
    return df.sort_values("date").reset_index(drop=True)


def preprocess_stations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # ✅ Stations CSV dùng format dd/MM/yyyy
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    if "station_name" not in df.columns:
        df["station_name"] = df["station_slug"].astype(str)
    if "year" not in df.columns:
        df["year"] = df["date"].dt.year
    df = safe_numeric(df, ALL_METRICS)
    return df.sort_values(["station_slug", "date"]).reset_index(drop=True)


# =============================
# CACHE LOAD
# =============================

@st.cache_data(ttl=600)
def load_city() -> pd.DataFrame:
    return preprocess_city(pd.read_csv(CITY_CSV_PATH))


@st.cache_data(ttl=600)
def load_stations() -> pd.DataFrame:
    return preprocess_stations(pd.read_csv(STATIONS_CSV_PATH))


# =============================
# CHART BUILDERS
# =============================

def chart_trend(df: pd.DataFrame) -> go.Figure:
    vals = df[["date", "AQI"]].dropna().sort_values("date")
    roll = vals.set_index("date")["AQI"].rolling(7, min_periods=1).mean().reset_index()

    fig = go.Figure()
    for lo, hi, c in [(0,50,"#2ecc71"),(51,100,"#f1c40f"),(101,150,"#e67e22"),
                      (151,200,"#e74c3c"),(201,300,"#8e44ad")]:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=c, opacity=0.08, layer="below", line_width=0)

    fig.add_trace(go.Scatter(
        x=vals["date"], y=vals["AQI"], name="AQI Daily",
        mode="lines", line=dict(color="#93c5fd", width=1), opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=roll["date"], y=roll["AQI"], name="7-day MA",
        mode="lines", line=dict(color="#1d4ed8", width=2.5),
    ))
    apply_theme(fig)
    fig.update_layout(hovermode="x unified",
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    return fig


def chart_donut(df: pd.DataFrame) -> go.Figure:
    order = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
    counts = df["AQI"].dropna().apply(aqi_category).value_counts()
    counts = counts.reindex([c for c in order if c in counts.index])

    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values, hole=0.60,
        marker=dict(colors=[AQI_COLORS[c] for c in counts.index],
                    line=dict(color="#ffffff", width=2)),
        textinfo="percent", textfont=dict(size=10),
        hovertemplate="%{label}: %{value} ngày (%{percent})<extra></extra>",
    ))
    apply_theme(fig)
    fig.update_layout(showlegend=True,
                      legend=dict(orientation="v", font=dict(size=9), x=1.02))
    return fig


def chart_heatmap(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"]  = tmp["date"].dt.year
    pivot = tmp.pivot_table(index="year", columns="month", values="AQI", aggfunc="mean")
    mlbls = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    xlbls = [mlbls[m-1] for m in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=xlbls, y=[str(y) for y in pivot.index],
        colorscale=[[0,"#2ecc71"],[0.25,"#f1c40f"],[0.5,"#e67e22"],
                    [0.75,"#e74c3c"],[1,"#641e16"]],
        zmin=0, zmax=200,
        text=np.where(np.isnan(pivot.values.astype(float)), "", 
                      np.round(pivot.values.astype(float), 0).astype(int).astype(str)),
        texttemplate="%{text}",
        textfont=dict(size=10),
        hovertemplate="Năm %{y} – %{x}<br>AQI TB: %{z:.1f}<extra></extra>",
        showscale=True,
        colorbar=dict(thickness=10, len=0.85,
                      title=dict(text="AQI", side="right"),
                      tickfont=dict(size=9)),
    ))
    apply_theme(fig)
    return fig


def chart_monthly_bar(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"]  = tmp["date"].dt.year.astype(str)
    grp = tmp.groupby(["year","month"])["AQI"].mean().reset_index()
    mlbls = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    grp["month_name"] = grp["month"].apply(lambda m: mlbls[m-1])

    fig = px.bar(
        grp, x="month_name", y="AQI", color="year", barmode="group",
        color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6"],
        category_orders={"month_name": mlbls},
        labels={"AQI": "AQI TB", "month_name": ""},
    )
    apply_theme(fig)
    fig.update_layout(legend=dict(title=None, font=dict(size=9)),
                      bargap=0.15, bargroupgap=0.06)
    return fig


def chart_top_stations(df: pd.DataFrame, agg: str, top_n: int) -> go.Figure:
    g = df.groupby("station_name")["AQI"]
    s = g.mean() if agg == "Mean" else (g.median() if agg == "Median" else g.max())
    rank = s.dropna().nlargest(top_n).sort_values()

    fig = go.Figure(go.Bar(
        x=rank.values, y=rank.index, orientation="h",
        marker=dict(color=[aqi_hex(v) for v in rank.values], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>AQI: %{x:.1f}<extra></extra>",
    ))
    apply_theme(fig)
    fig.update_layout(showlegend=False)
    return fig


def chart_boxplot(df: pd.DataFrame, top_n: int) -> go.Figure:
    top_stns = df.groupby("station_name")["AQI"].median().nlargest(top_n).index
    sub = df[df["station_name"].isin(top_stns)]
    palette = px.colors.qualitative.Safe

    fig = go.Figure()
    for i, stn in enumerate(top_stns[::-1]):
        vals = sub[sub["station_name"] == stn]["AQI"].dropna()
        if len(vals) < 2:
            continue
        c = palette[i % len(palette)]
        fig.add_trace(go.Box(
            y=[stn]*len(vals), x=vals, name=stn, orientation="h",
            boxmean=True,
            marker=dict(size=3, opacity=0.4, color=c),
            line=dict(color=c, width=1.5),
            hovertemplate=f"<b>{stn}</b><br>AQI: %{{x:.0f}}<extra></extra>",
        ))
    apply_theme(fig)
    fig.update_layout(showlegend=False, hovermode="closest")
    return fig


def chart_radar(df: pd.DataFrame, top_n: int) -> go.Figure:
    avail = [p for p in NON_AQI if p in df.columns and df[p].notna().sum() > 10]
    if len(avail) < 3:
        return go.Figure()

    top_stns = df.groupby("station_name")["AQI"].median().nlargest(top_n).index
    sub  = df[df["station_name"].isin(top_stns)]
    means = sub.groupby("station_name")[avail].mean()
    norm  = (means - means.min()) / (means.max() - means.min() + 1e-9)
    palette = px.colors.qualitative.Safe

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
    apply_theme(fig)
    fig.update_layout(
        polar=dict(
            bgcolor="#f8fafc",
            radialaxis=dict(visible=True, range=[0,1],
                            tickfont=dict(size=8, color="#94a3b8"),
                            gridcolor="#e2e8f0", linecolor="#e2e8f0"),
            angularaxis=dict(tickfont=dict(size=9, color="#475569"),
                             gridcolor="#e2e8f0", linecolor="#e2e8f0"),
        ),
        legend=dict(font=dict(size=9)),
    )
    return fig


def chart_scatter(df: pd.DataFrame, x_col: str, y_col: str) -> go.Figure:
    if x_col not in df.columns or y_col not in df.columns:
        return go.Figure()
    tmp = df[[x_col, y_col, "AQI", "station_name", "date"]].dropna()
    if tmp.empty:
        return go.Figure()
    tmp["category"] = tmp["AQI"].apply(aqi_category)
    r = corr_val(tmp, x_col, y_col)

    fig = px.scatter(
        tmp, x=x_col, y=y_col, color="category",
        category_orders={"category": ["Good","Moderate","USG","Unhealthy","Very Unhealthy","Hazardous"]},
        color_discrete_map=AQI_COLORS,
        hover_data={"station_name": True, "date": True, "category": False},
        opacity=0.7,
    )
    fig.update_traces(marker=dict(size=4, line=dict(width=0)))
    apply_theme(fig)
    fig.update_layout(
        legend=dict(title=None, font=dict(size=9)),
        annotations=[dict(
            x=0.02, y=0.97, xref="paper", yref="paper",
            text=f"r = {r:.3f}" if not np.isnan(r) else "r = N/A",
            showarrow=False,
            font=dict(size=11, color="#1d4ed8", family="JetBrains Mono"),
            bgcolor="rgba(219,234,254,0.9)",
            bordercolor="#93c5fd", borderwidth=1, borderpad=5,
        )],
    )
    return fig


# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    page_icon="🌆", layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# =============================
# LOAD
# =============================
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

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("### ⚙️ Bộ lọc")

    min_date  = min(df_st["date"].min(), df_city["date"].min())
    max_date  = max(df_st["date"].max(), df_city["date"].max())
    today     = pd.Timestamp(date.today())
    def_end   = min(max_date, today)
    def_start = max(min_date, def_end - pd.Timedelta(days=365))

    d_range = st.date_input(
        "Khoảng thời gian",
        value=(def_start.date(), def_end.date()),
        min_value=min_date.date(), max_value=max_date.date(),
    )
    if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
        start_ts, end_ts = pd.Timestamp(d_range[0]), pd.Timestamp(d_range[1])
    else:
        start_ts, end_ts = def_start, def_end

    agg_method = st.selectbox("Tổng hợp AQI theo trạm", ["Median", "Mean", "Max"])

    st.divider()
    st.markdown("**🏭 Lọc theo trạm**")
    stn_list  = df_st[["station_slug","station_name"]].drop_duplicates().sort_values("station_name")
    stn_names = stn_list["station_name"].tolist()
    n2slug    = dict(zip(stn_list["station_name"], stn_list["station_slug"]))
    sel_names = st.multiselect("Chọn trạm (bỏ trống = tất cả)", stn_names)
    sel_slugs = [n2slug[n] for n in sel_names] if sel_names else []
    top_n     = st.slider("Top N trạm", 3, 15, 7)

    st.divider()
    st.markdown("**🔗 Scatter tương quan**")
    sc_x = st.selectbox("Trục X", NON_AQI, index=0)
    sc_y = st.selectbox("Trục Y", NON_AQI, index=1)

    st.divider()
    st.caption("HCMC Air Quality Monitor · 2022–2026")

# =============================
# FILTER
# =============================
df_city_f = df_city[(df_city["date"] >= start_ts) & (df_city["date"] <= end_ts)].copy()
df_st_f   = df_st[(df_st["date"] >= start_ts)   & (df_st["date"] <= end_ts)].copy()
if sel_slugs:
    df_st_f = df_st_f[df_st_f["station_slug"].isin(sel_slugs)].copy()

# =============================
# KPI
# =============================
city_aqi  = df_city_f["AQI"].dropna()
lr        = df_city_f[df_city_f["AQI"].notna()].sort_values("date").tail(1)
lat_aqi   = float(lr["AQI"].iloc[0]) if not lr.empty else None
lat_date  = lr["date"].iloc[0].strftime("%d/%m/%Y") if not lr.empty else "N/A"
lat_cat   = aqi_category(lat_aqi)
avg_aqi   = city_aqi.mean()   if len(city_aqi) else None
max_aqi   = city_aqi.max()    if len(city_aqi) else None
good_pct  = (city_aqi <= 50).mean()  * 100 if len(city_aqi) else 0
bad_pct   = (city_aqi > 50).mean()  * 100 if len(city_aqi) else 0
n_st      = df_st_f["station_name"].nunique()
n_days    = df_city_f["date"].nunique()

# =============================
# HEADER
# =============================
st.markdown(f"""
<div class="dash-header">
  <div>
    <div class="dash-title">HCMC AIR QUALITY DASHBOARD</div>
    <div class="dash-subtitle">TP. Hồ Chí Minh · City + {n_st} Trạm · 2022–2026</div>
  </div>
  <div class="dash-badge">LIVE DATA</div>
</div>
""", unsafe_allow_html=True)

# =============================
# KPI ROW
# =============================
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-accent" style="background:{AQI_COLORS.get(lat_cat,'#94a3b8')}"></div>
    <div class="kpi-label">AQI mới nhất</div>
    <div class="kpi-value {kpi_cls(lat_aqi,50,150)}">{fmt(lat_aqi,0)}</div>
    <div class="kpi-sub">{lat_cat} · {lat_date}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#3b82f6"></div>
    <div class="kpi-label">AQI trung bình</div>
    <div class="kpi-value {kpi_cls(avg_aqi,50,100)}">{fmt(avg_aqi)}</div>
    <div class="kpi-sub">Trong kỳ lọc</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:{aqi_hex(max_aqi)}"></div>
    <div class="kpi-label">AQI cao nhất</div>
    <div class="kpi-value kpi-bad">{fmt(max_aqi,0)}</div>
    <div class="kpi-sub">{aqi_category(max_aqi)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#2ecc71"></div>
    <div class="kpi-label">% Ngày tốt</div>
    <div class="kpi-value kpi-good">{good_pct:.1f}%</div>
    <div class="kpi-sub">AQI ≤ 50</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#e74c3c"></div>
    <div class="kpi-label">% Ngày xấu</div>
    <div class="kpi-value {kpi_cls(bad_pct,10,30)}">{bad_pct:.1f}%</div>
    <div class="kpi-sub">AQI > 150</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-accent" style="background:#8b5cf6"></div>
    <div class="kpi-label">Trạm / Ngày</div>
    <div class="kpi-value kpi-blue">{n_st}</div>
    <div class="kpi-sub">{n_days} ngày quan trắc</div>
  </div>
</div>
""", unsafe_allow_html=True)


def section_title(icon: str, text: str):
    st.markdown(
        f'<div class="chart-title"><span class="ct-bar"></span>{icon} {text}</div>',
        unsafe_allow_html=True,
    )


# =============================
# ROW 1: Trend + Donut
# =============================
col1, col2 = st.columns([2.2, 1], gap="small")
with col1:
    section_title("📈", "Xu hướng AQI – City Level (Daily + 7-Day MA)")
    if not df_city_f.empty and df_city_f["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_trend(df_city_f), use_container_width=True, config=CHART_CFG)
    else:
        st.info("Không có dữ liệu AQI city-level trong khoảng đã chọn.")

with col2:
    section_title("🎯", "Phân bổ AQI Category")
    if not df_city_f.empty and df_city_f["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_donut(df_city_f), use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")

st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

# =============================
# ROW 2: Heatmap + Monthly bar
# =============================
col3, col4 = st.columns([1.3, 1], gap="small")
with col3:
    section_title("🗓️", "Heatmap AQI TB – Tháng × Năm")
    if not df_city_f.empty and df_city_f["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_heatmap(df_city_f), use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")

with col4:
    section_title("📅", "AQI TB theo Tháng so sánh qua các Năm")
    if not df_city_f.empty and df_city_f["AQI"].notna().sum() > 0:
        st.plotly_chart(chart_monthly_bar(df_city_f), use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")

st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

# =============================
# ROW 3: Top stations + Boxplot + Radar
# =============================
col5, col6, col7 = st.columns([1, 1.4, 1.2], gap="small")
with col5:
    section_title("🏭", f"Top {top_n} Trạm ô nhiễm")
    has_st = not df_st_f.empty and df_st_f["AQI"].notna().sum() > 0
    if has_st:
        st.plotly_chart(chart_top_stations(df_st_f, agg_method, top_n),
                        use_container_width=True, config=CHART_CFG)
    else:
        st.info("Không đủ dữ liệu AQI theo trạm.")

with col6:
    section_title("📦", f"Phân phối AQI – Box Plot ({agg_method})")
    if has_st:
        st.plotly_chart(chart_boxplot(df_st_f, top_n),
                        use_container_width=True, config=CHART_CFG)
    else:
        st.info("—")

with col7:
    section_title("🕸️", f"Radar Profile – Top {min(top_n,6)} Trạm")
    if not df_st_f.empty:
        fig_r = chart_radar(df_st_f, min(top_n, 6))
        if fig_r.data:
            st.plotly_chart(fig_r, use_container_width=True, config=CHART_CFG)
        else:
            st.info("Không đủ dữ liệu cho radar.")
    else:
        st.info("—")

st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

# =============================
# ROW 4: Scatter
# =============================
section_title("🔗", f"Tương quan {sc_x} vs {sc_y} – Station Level (màu theo AQI Category)")
if not df_st_f.empty and sc_x in df_st_f.columns and sc_y in df_st_f.columns:
    fig_sc = chart_scatter(df_st_f, sc_x, sc_y)
    if fig_sc.data:
        st.plotly_chart(fig_sc, use_container_width=True, config=CHART_CFG)
    else:
        st.info(f"Không đủ dữ liệu cho cặp {sc_x} – {sc_y}.")
else:
    st.info(f"Cột {sc_x} hoặc {sc_y} không tồn tại trong dữ liệu trạm.")

# =============================
# FOOTER
# =============================
st.markdown("""
<div style="text-align:center;padding:20px 0 8px;font-size:10px;
     color:#94a3b8;font-family:'JetBrains Mono',monospace;letter-spacing:2px;">
  HCMC AIR QUALITY MONITOR · CITY CSV + STATIONS CSV · 2022 – 2026
</div>
""", unsafe_allow_html=True)