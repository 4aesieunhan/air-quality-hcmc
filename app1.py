# -*- coding: utf-8 -*-
"""
HCMC Air Quality Dashboard – Single-Page Professional Layout
Tất cả charts trong 1 viewport kiểu CRM Dashboard
"""

from datetime import date
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# =============================
# CONFIG
# =============================
POLLUTANTS = ["AQI", "PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
NON_AQI = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]

STATIONS_CSV_PATH = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"
CITY_CSV_PATH = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"

AQI_COLORS = {
    "Good": "#00e400",
    "Moderate": "#ffff00",
    "USG": "#ff7e00",
    "Unhealthy": "#ff0000",
    "Very Unhealthy": "#8f3f97",
    "Hazardous": "#7e0023",
}

CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,20,40,0.6)",
    font=dict(family="IBM Plex Sans, monospace", color="#c9d1e0", size=11),
    margin=dict(l=10, r=10, t=32, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
)

# =============================
# CSS INJECTION – Dark Dashboard Style
# =============================
DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

/* Root & App */
html, body, [data-testid="stApp"] {
    background: #0a0f1e !important;
    font-family: 'IBM Plex Sans', sans-serif;
    color: #c9d1e0;
}

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* Dashboard title bar */
.dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 24px 10px;
    border-bottom: 1px solid rgba(99,179,237,0.15);
    background: rgba(10,15,30,0.95);
    backdrop-filter: blur(10px);
    position: sticky;
    top: 0;
    z-index: 100;
    margin-bottom: 16px;
}
.dash-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 4px;
    color: #63b3ed;
    text-transform: uppercase;
}
.dash-subtitle { font-size: 11px; color: #667eea; opacity: 0.8; }

/* KPI Cards */
.kpi-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
    padding: 0 4px 16px;
}
.kpi-card {
    background: linear-gradient(135deg, rgba(20,27,55,0.9), rgba(15,20,40,0.95));
    border: 1px solid rgba(99,179,237,0.12);
    border-radius: 8px;
    padding: 12px 14px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #63b3ed, #667eea);
}
.kpi-card:hover { border-color: rgba(99,179,237,0.35); }
.kpi-label { font-size: 9px; letter-spacing: 2px; color: #667eea; text-transform: uppercase; margin-bottom: 4px; }
.kpi-value { font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 700; color: #f0f4ff; line-height: 1; }
.kpi-sub { font-size: 10px; color: #63b3ed; margin-top: 4px; }
.kpi-good { color: #48bb78 !important; }
.kpi-warn { color: #ed8936 !important; }
.kpi-bad  { color: #fc8181 !important; }

/* Chart grid layout */
.chart-grid {
    display: grid;
    gap: 10px;
    padding: 0 4px;
}
.chart-grid-1 { grid-template-columns: 2fr 1fr; }
.chart-grid-2 { grid-template-columns: 1fr 1fr 1fr; }
.chart-grid-3 { grid-template-columns: 3fr 2fr; }
.chart-grid-full { grid-template-columns: 1fr; }

.chart-card {
    background: rgba(15,20,40,0.8);
    border: 1px solid rgba(99,179,237,0.08);
    border-radius: 10px;
    padding: 14px;
    backdrop-filter: blur(6px);
}
.chart-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: #63b3ed;
    text-transform: uppercase;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.chart-title::before {
    content: '';
    width: 3px; height: 12px;
    background: #667eea;
    border-radius: 2px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #070b17 !important;
    border-right: 1px solid rgba(99,179,237,0.1) !important;
}
[data-testid="stSidebar"] * { color: #c9d1e0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stDateInput label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stRadio label { font-size: 11px !important; letter-spacing: 1px !important; }

/* Streamlit elements theming */
.stPlotlyChart { border-radius: 6px; overflow: hidden; }
div[data-testid="column"] { padding: 4px !important; }

/* Section dividers */
.section-sep {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,179,237,0.2), transparent);
    margin: 16px 0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0f1e; }
::-webkit-scrollbar-thumb { background: #63b3ed44; border-radius: 4px; }
</style>
"""

# =============================
# UTILS
# =============================

def safe_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def aqi_category(aqi: float) -> str:
    if aqi is None or np.isnan(aqi):
        return "N/A"
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Moderate"
    if aqi <= 150:  return "USG"
    if aqi <= 200:  return "Unhealthy"
    if aqi <= 300:  return "Very Unhealthy"
    return "Hazardous"


def aqi_color(aqi: float) -> str:
    cat = aqi_category(aqi)
    return AQI_COLORS.get(cat, "#888")


def corr_value(df: pd.DataFrame, x: str, y: str) -> float:
    tmp = df[[x, y]].dropna()
    if len(tmp) < 3:
        return float("nan")
    return float(tmp[x].corr(tmp[y]))


def preprocess_stations(df: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "station_slug"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Stations CSV thiếu cột: {missing}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    if "station_name" not in df.columns:
        df["station_name"] = df["station_slug"].astype(str)
    if "year" not in df.columns:
        df["year"] = df["date"].dt.year
    df = safe_numeric(df, POLLUTANTS)
    df["AQI_COMPUTED"] = df[NON_AQI].max(axis=1, skipna=True)
    return df.sort_values(["station_slug", "date"])


def preprocess_city(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns:
        raise ValueError("City CSV thiếu cột 'date'.")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    if "year" not in df.columns:
        df["year"] = df["date"].dt.year
    if "AQI" not in df.columns:
        df["AQI"] = np.nan
    df = safe_numeric(df, POLLUTANTS)
    df["AQI_COMPUTED"] = df[NON_AQI].max(axis=1, skipna=True)
    return df.sort_values("date")


def apply_theme(fig, title: str = "") -> go.Figure:
    """Apply dark dashboard theme to any plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=11, family="IBM Plex Mono", color="#63b3ed"),
                   x=0, xanchor="left", pad=dict(l=4, b=8)) if title else None,
        **CHART_THEME
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False,
                     tickfont=dict(size=9), linecolor="rgba(255,255,255,0.1)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False,
                     tickfont=dict(size=9), linecolor="rgba(255,255,255,0.1)")
    return fig


# =============================
# CHART BUILDERS
# =============================

def build_trend_chart(df_city: pd.DataFrame, df_st: pd.DataFrame, aqi_col: str, agg: str) -> go.Figure:
    """Line chart: city AQI vs rolling 7d average."""
    fig = go.Figure()

    city_vals = df_city[["date", aqi_col]].dropna()
    if not city_vals.empty:
        rolling = city_vals.set_index("date")[aqi_col].rolling(7, min_periods=1).mean().reset_index()
        fig.add_trace(go.Scatter(
            x=city_vals["date"], y=city_vals[aqi_col],
            mode="lines", name="AQI Daily",
            line=dict(color="#63b3ed", width=1), opacity=0.45
        ))
        fig.add_trace(go.Scatter(
            x=rolling["date"], y=rolling[aqi_col],
            mode="lines", name="7-day MA",
            line=dict(color="#f6ad55", width=2.5)
        ))

    # AQI category threshold bands
    bands = [(0, 50, "#00e400"), (51, 100, "#ffff00"), (101, 150, "#ff7e00"),
             (151, 200, "#ff0000"), (201, 300, "#8f3f97")]
    for lo, hi, color in bands:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=color, opacity=0.04, layer="below", line_width=0)

    apply_theme(fig)
    fig.update_layout(hovermode="x unified", showlegend=True,
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    return fig


def build_aqi_category_pie(df_city: pd.DataFrame, aqi_col: str) -> go.Figure:
    """Donut chart: % days per AQI category."""
    tmp = df_city[aqi_col].dropna().apply(aqi_category)
    counts = tmp.value_counts()
    order = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
    counts = counts.reindex([c for c in order if c in counts.index])

    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.62,
        marker=dict(colors=[AQI_COLORS[c] for c in counts.index],
                    line=dict(color="#0a0f1e", width=2)),
        textinfo="percent",
        textfont=dict(size=10),
        hovertemplate="%{label}: %{value} ngày (%{percent})<extra></extra>",
    ))
    apply_theme(fig)
    fig.update_layout(showlegend=True,
                      legend=dict(orientation="v", font=dict(size=9), x=1))
    return fig


def build_station_boxplot(df_st: pd.DataFrame, aqi_col: str, top_n: int) -> go.Figure:
    """Box plot: AQI distribution per station (top N by median)."""
    medians = df_st.groupby("station_name")[aqi_col].median().nlargest(top_n).index
    sub = df_st[df_st["station_name"].isin(medians)]

    fig = go.Figure()
    for stn in medians[::-1]:
        vals = sub[sub["station_name"] == stn][aqi_col].dropna()
        if len(vals) < 2:
            continue
        fig.add_trace(go.Box(
            y=[stn] * len(vals), x=vals,
            name=stn, orientation="h",
            boxmean=True,
            marker=dict(size=3, opacity=0.5),
            line=dict(width=1.2),
            hovertemplate=f"<b>{stn}</b><br>AQI: %{{x:.0f}}<extra></extra>",
        ))
    apply_theme(fig)
    fig.update_layout(showlegend=False, hovermode="closest")
    return fig


def build_heatmap_monthly(df_city: pd.DataFrame, aqi_col: str) -> go.Figure:
    """Heatmap: year × month average AQI."""
    tmp = df_city.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"] = tmp["date"].dt.year
    pivot = tmp.pivot_table(index="year", columns="month", values=aqi_col, aggfunc="mean")
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    col_labels = [month_names[m - 1] for m in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=col_labels,
        y=[str(y) for y in pivot.index],
        colorscale=[
            [0.0,  "#00e400"], [0.2,  "#ffff00"],
            [0.4,  "#ff7e00"], [0.6,  "#ff0000"],
            [0.8,  "#8f3f97"], [1.0,  "#7e0023"],
        ],
        zmin=0, zmax=300,
        text=np.round(pivot.values, 0).astype("object"),
        texttemplate="%{text:.0f}",
        textfont=dict(size=10, color="white"),
        hovertemplate="Năm %{y} | Tháng %{x}<br>AQI: %{z:.1f}<extra></extra>",
        showscale=True,
        colorbar=dict(thickness=10, len=0.8, title=dict(text="AQI", side="right"),
                      tickfont=dict(size=9)),
    ))
    apply_theme(fig)
    return fig


def build_radar_stations(df_st: pd.DataFrame, top_n: int) -> go.Figure:
    """Radar/spider chart: pollutant profile per station (top N by AQI)."""
    avail = [p for p in NON_AQI if p in df_st.columns]
    if not avail:
        return go.Figure()

    top_stns = df_st.groupby("station_name")["AQI_COMPUTED"].median().nlargest(top_n).index
    sub = df_st[df_st["station_name"].isin(top_stns)]

    # Normalize each pollutant 0–1 for radar shape
    means = sub.groupby("station_name")[avail].mean()
    norm = (means - means.min()) / (means.max() - means.min() + 1e-6)

    colors = px.colors.qualitative.Set2[:top_n]
    fig = go.Figure()
    for i, stn in enumerate(top_stns):
        if stn not in norm.index:
            continue
        vals = norm.loc[stn].tolist()
        vals += [vals[0]]
        cats = avail + [avail[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=cats, name=stn,
            fill="toself", opacity=0.65,
            line=dict(color=colors[i % len(colors)], width=1.5),
        ))
    apply_theme(fig)
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=8),
                            gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(tickfont=dict(size=9), gridcolor="rgba(255,255,255,0.08)"),
        ),
        showlegend=True,
        legend=dict(font=dict(size=9)),
    )
    return fig


def build_top_stations_bar(df_st: pd.DataFrame, aqi_col: str, top_n: int, agg: str) -> go.Figure:
    """Horizontal bar: top N polluted stations."""
    g = df_st.groupby("station_name")[aqi_col]
    s = g.mean() if agg == "Mean" else (g.median() if agg == "Median" else g.max())
    rank = s.dropna().nlargest(top_n).sort_values()

    colors = [aqi_color(v) for v in rank.values]
    fig = go.Figure(go.Bar(
        x=rank.values,
        y=rank.index,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>AQI: %{x:.1f}<extra></extra>",
    ))
    apply_theme(fig)
    fig.update_layout(showlegend=False)
    return fig


def build_scatter_corr(df_st: pd.DataFrame, x_col: str, y_col: str) -> go.Figure:
    """Scatter correlation between 2 pollutants, colored by AQI category."""
    tmp = df_st[[x_col, y_col, "AQI_COMPUTED", "station_name", "date"]].dropna()
    tmp["category"] = tmp["AQI_COMPUTED"].apply(aqi_category)
    cat_order = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
    color_map = AQI_COLORS

    r = corr_value(tmp, x_col, y_col)
    fig = px.scatter(
        tmp, x=x_col, y=y_col,
        color="category",
        category_orders={"category": cat_order},
        color_discrete_map=color_map,
        hover_data={"station_name": True, "date": True, "category": False},
        opacity=0.7,
    )
    fig.update_traces(marker=dict(size=4, line=dict(width=0)))
    apply_theme(fig)
    fig.update_layout(
        legend=dict(title=None, font=dict(size=9)),
        annotations=[dict(
            x=0.02, y=0.97, xref="paper", yref="paper",
            text=f"r = {r:.3f}", showarrow=False,
            font=dict(size=11, color="#f6ad55", family="IBM Plex Mono"),
            bgcolor="rgba(0,0,0,0.4)", bordercolor="#f6ad55",
            borderwidth=1, borderpad=4,
        )],
    )
    return fig


def build_monthly_trend_bar(df_city: pd.DataFrame, aqi_col: str) -> go.Figure:
    """Bar chart: monthly average AQI for each year as grouped bars."""
    tmp = df_city.copy()
    tmp["month"] = tmp["date"].dt.month
    tmp["year"] = tmp["date"].dt.year
    grp = tmp.groupby(["year", "month"])[aqi_col].mean().reset_index()
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    grp["month_name"] = grp["month"].apply(lambda m: month_names[m - 1])

    fig = px.bar(grp, x="month_name", y=aqi_col, color="year",
                 barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Pastel,
                 category_orders={"month_name": month_names},
                 hover_data={"year": True},
                 labels={aqi_col: "AQI", "month_name": ""})
    apply_theme(fig)
    fig.update_layout(legend=dict(title=None, font=dict(size=9)),
                      bargap=0.15, bargroupgap=0.05)
    return fig


# =============================
# LOAD DATA
# =============================
@st.cache_data(ttl=600)
def load_stations() -> pd.DataFrame:
    return preprocess_stations(pd.read_csv(STATIONS_CSV_PATH))


@st.cache_data(ttl=600)
def load_city() -> pd.DataFrame:
    return preprocess_city(pd.read_csv(CITY_CSV_PATH))


# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    page_icon="🌆",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(DARK_CSS, unsafe_allow_html=True)

# =============================
# LOAD
# =============================
with st.spinner("Đang tải dữ liệu..."):
    try:
        df_st = load_stations()
    except Exception as e:
        st.error(f"Không load được STATIONS CSV: {e}")
        st.stop()
    try:
        df_city = load_city()
    except Exception as e:
        st.error(f"Không load được CITY CSV: {e}")
        st.stop()

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("### 🔧 Bộ lọc")

    min_date = min(df_st["date"].min(), df_city["date"].min())
    max_date = max(df_st["date"].max(), df_city["date"].max())
    today = pd.Timestamp(date.today())
    default_end = min(max_date, today)
    default_start = max(min_date, default_end - pd.Timedelta(days=365))

    start_date, end_date = st.date_input(
        "Khoảng thời gian",
        value=(default_start.date(), default_end.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
    start_ts, end_ts = pd.Timestamp(start_date), pd.Timestamp(end_date)

    agg_method = st.selectbox("Tổng hợp theo trạm", ["Median", "Mean", "Max"])

    aqi_mode = st.radio(
        "Cột AQI sử dụng",
        ["AQI (raw)", "AQI_COMPUTED (max 6 chỉ số)"],
        index=1
    )
    aqi_col = "AQI" if "raw" in aqi_mode else "AQI_COMPUTED"

    st.divider()

    station_list = df_st[["station_slug", "station_name"]].drop_duplicates().sort_values("station_name")
    station_names = station_list["station_name"].tolist()
    name2slug = dict(zip(station_list["station_name"], station_list["station_slug"]))

    selected_names = st.multiselect("Chọn trạm (bỏ trống = tất cả)", station_names, default=[])
    selected_slugs = [name2slug[n] for n in selected_names] if selected_names else []

    top_n = st.slider("Top N trạm", 3, 20, 8)

    st.divider()
    scatter_x = st.selectbox("Scatter – Trục X", NON_AQI, index=0)
    scatter_y = st.selectbox("Scatter – Trục Y", NON_AQI, index=1)

    st.divider()
    st.caption("HCMC Air Quality · 2022–2026")

# =============================
# FILTER
# =============================
df_st_f = df_st[(df_st["date"] >= start_ts) & (df_st["date"] <= end_ts)].copy()
df_city_f = df_city[(df_city["date"] >= start_ts) & (df_city["date"] <= end_ts)].copy()
if selected_slugs:
    df_st_f = df_st_f[df_st_f["station_slug"].isin(selected_slugs)].copy()

# =============================
# DASHBOARD HEADER
# =============================
st.markdown("""
<div class="dash-header">
    <div>
        <div class="dash-title">HCMC AIR QUALITY DASHBOARD</div>
        <div class="dash-subtitle">TP. Hồ Chí Minh · Real-time Station + City Index · 2022–2026</div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================
# KPI ROW
# =============================
latest_city_date = df_city_f["date"].max() if not df_city_f.empty else None
latest_row = df_city_f[df_city_f["date"] == latest_city_date] if latest_city_date else pd.DataFrame()
latest_aqi = float(latest_row[aqi_col].dropna().iloc[0]) if not latest_row.empty and latest_row[aqi_col].notna().any() else None
aqi_cat = aqi_category(latest_aqi) if latest_aqi is not None else "N/A"

avg_aqi = df_city_f[aqi_col].mean()
max_aqi = df_city_f[aqi_col].max()
n_stations = df_st_f["station_name"].nunique()
n_days = df_city_f["date"].nunique()
good_pct = (df_city_f[aqi_col].dropna() <= 50).mean() * 100 if not df_city_f.empty else 0
unhealthy_pct = (df_city_f[aqi_col].dropna() > 150).mean() * 100 if not df_city_f.empty else 0

def kpi_color_class(val, thresholds):
    """Returns CSS class based on value thresholds (good, warn, bad)."""
    if val is None or np.isnan(val): return ""
    if val <= thresholds[0]: return "kpi-good"
    if val <= thresholds[1]: return "kpi-warn"
    return "kpi-bad"

kpi_html = f"""
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">AQI mới nhất</div>
        <div class="kpi-value {kpi_color_class(latest_aqi, [50, 150])}">{f"{latest_aqi:.0f}" if latest_aqi else "N/A"}</div>
        <div class="kpi-sub">{aqi_cat}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">AQI trung bình</div>
        <div class="kpi-value {kpi_color_class(avg_aqi, [50, 150])}">{f"{avg_aqi:.1f}" if avg_aqi else "N/A"}</div>
        <div class="kpi-sub">Trong kỳ lọc</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">AQI cao nhất</div>
        <div class="kpi-value kpi-bad">{f"{max_aqi:.0f}" if max_aqi else "N/A"}</div>
        <div class="kpi-sub">{aqi_category(max_aqi) if max_aqi else ""}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">% Ngày tốt</div>
        <div class="kpi-value kpi-good">{good_pct:.1f}%</div>
        <div class="kpi-sub">AQI ≤ 50</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">% Ngày xấu</div>
        <div class="kpi-value {kpi_color_class(unhealthy_pct, [10, 30])}">{unhealthy_pct:.1f}%</div>
        <div class="kpi-sub">AQI > 150</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Trạm / Ngày</div>
        <div class="kpi-value">{n_stations}</div>
        <div class="kpi-sub">{n_days} ngày quan trắc</div>
    </div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# =============================
# ROW 1: Trend + Donut
# =============================
CHART_H = 260
col1, col2 = st.columns([2.2, 1], gap="small")

with col1:
    st.markdown('<div class="chart-title">📈 Xu hướng AQI – City Level (Daily + 7-Day MA)</div>', unsafe_allow_html=True)
    if not df_city_f.empty:
        fig = build_trend_chart(df_city_f, df_st_f, aqi_col, agg_method)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="trend")
    else:
        st.info("Không có dữ liệu city-level.")

with col2:
    st.markdown('<div class="chart-title">🎯 Phân bổ AQI Category</div>', unsafe_allow_html=True)
    if not df_city_f.empty:
        fig = build_aqi_category_pie(df_city_f, aqi_col)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="donut")
    else:
        st.info("—")

st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

# =============================
# ROW 2: Monthly Heatmap + Bar seasonal
# =============================
col3, col4 = st.columns([1.3, 1], gap="small")

with col3:
    st.markdown('<div class="chart-title">🗓️ Heatmap AQI Trung bình – Tháng × Năm</div>', unsafe_allow_html=True)
    if not df_city_f.empty:
        fig = build_heatmap_monthly(df_city_f, aqi_col)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="heatmap")
    else:
        st.info("—")

with col4:
    st.markdown('<div class="chart-title">📅 AQI Trung bình theo Tháng (theo Năm)</div>', unsafe_allow_html=True)
    if not df_city_f.empty:
        fig = build_monthly_trend_bar(df_city_f, aqi_col)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="monthly_bar")
    else:
        st.info("—")

st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

# =============================
# ROW 3: Top stations + Boxplot + Radar
# =============================
col5, col6, col7 = st.columns([1, 1.4, 1.2], gap="small")

with col5:
    st.markdown(f'<div class="chart-title">🏭 Top {top_n} Trạm Ô nhiễm</div>', unsafe_allow_html=True)
    if not df_st_f.empty:
        fig = build_top_stations_bar(df_st_f, aqi_col, top_n, agg_method)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="top_bar")
    else:
        st.info("—")

with col6:
    st.markdown(f'<div class="chart-title">📦 Phân phối AQI theo Trạm (Box Plot)</div>', unsafe_allow_html=True)
    if not df_st_f.empty:
        fig = build_station_boxplot(df_st_f, aqi_col, top_n)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="boxplot")
    else:
        st.info("—")

with col7:
    st.markdown(f'<div class="chart-title">🕸️ Radar Profile Ô nhiễm – Top {min(top_n, 6)} Trạm</div>', unsafe_allow_html=True)
    if not df_st_f.empty:
        fig = build_radar_stations(df_st_f, min(top_n, 6))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="radar")
    else:
        st.info("—")

st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

# =============================
# ROW 4: Scatter Correlation (full width)
# =============================
st.markdown(f'<div class="chart-title">🔗 Tương quan {scatter_x} vs {scatter_y} – Station Level (màu theo AQI Category)</div>', unsafe_allow_html=True)
if not df_st_f.empty and scatter_x in df_st_f.columns and scatter_y in df_st_f.columns:
    fig = build_scatter_corr(df_st_f, scatter_x, scatter_y)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="scatter")
else:
    st.info("Không đủ dữ liệu tương quan.")

# Footer
st.markdown("""
<div style="text-align:center; padding: 20px 0 8px; font-size: 10px; color: rgba(99,179,237,0.4); font-family: 'IBM Plex Mono', monospace; letter-spacing: 2px;">
    HCMC AIR QUALITY MONITOR · STATIONS CSV + CITY CSV · 2022–2026
</div>
""", unsafe_allow_html=True)