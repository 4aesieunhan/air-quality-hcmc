# -*- coding: utf-8 -*-
from datetime import date
from typing import List, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# =============================
# CONFIG
# =============================
POLLUTANTS = ["AQI", "PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]
NON_AQI = ["PM2,5", "PM10", "CO", "SO2", "O3", "NO2"]

# ✅ chỉnh lại đúng path của bạn nếu cần
STATIONS_CSV_PATH = "output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv"
CITY_CSV_PATH = "output_city_hcmc/hcmc_city_2022_2026_comma.csv"


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
    if aqi <= 50:
        return "Good (0–50)"
    if aqi <= 100:
        return "Moderate (51–100)"
    if aqi <= 150:
        return "USG (101–150)"
    if aqi <= 200:
        return "Unhealthy (151–200)"
    if aqi <= 300:
        return "Very Unhealthy (201–300)"
    return "Hazardous (301+)"


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

    # AQI_COMPUTED = max of non-AQI pollutants
    df["AQI_COMPUTED"] = df[NON_AQI].max(axis=1, skipna=True)

    return df.sort_values(["station_slug", "date"])


def preprocess_city(df: pd.DataFrame) -> pd.DataFrame:
    # city csv: city_slug,date,year,PM2,5,PM10,CO,SO2,O3,NO2 (AQI có thể không có)
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


def city_aggregate_from_stations(df: pd.DataFrame, value_col: str, agg: str) -> pd.DataFrame:
    g = df.groupby("date")[value_col]
    if agg == "Mean":
        s = g.mean()
    elif agg == "Median":
        s = g.median()
    else:
        s = g.max()

    cnt = g.count()
    out = pd.DataFrame({"date": s.index, "value": s.values, "stations_reporting": cnt.values})
    return out.sort_values("date")


def station_rank(df: pd.DataFrame, value_col: str, agg: str) -> pd.DataFrame:
    g = df.groupby(["station_slug", "station_name"])[value_col]
    if agg == "Mean":
        s = g.mean()
    elif agg == "Median":
        s = g.median()
    else:
        s = g.max()
    out = s.reset_index().rename(columns={value_col: "value"})
    return out.dropna(subset=["value"]).sort_values("value", ascending=False)


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
# APP
# =============================
st.set_page_config(page_title="HCMC Air Quality Dashboard", layout="wide")
st.title("🌆 Dashboard Chất lượng không khí – TP.HCM (City + Stations)")

# Load both
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
# SIDEBAR FILTERS
# =============================
with st.sidebar:
    st.header("Bộ lọc chung")

    min_date = min(df_st["date"].min(), df_city["date"].min())
    max_date = max(df_st["date"].max(), df_city["date"].max())
    today = pd.Timestamp(date.today())

    default_end = min(max_date, today)
    default_start = max(min_date, default_end - pd.Timedelta(days=180))

    start_date, end_date = st.date_input(
        "Khoảng thời gian",
        value=(default_start.date(), default_end.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    agg_method = st.selectbox("Tổng hợp TP.HCM từ trạm (Median/Mean/Max)", ["Median", "Mean", "Max"], index=0)

    aqi_mode = st.radio(
        "AQI dùng trong dashboard",
        ["AQI (raw nếu có)", "AQI_COMPUTED (max 6 chỉ số)"],
        index=1,
    )
    aqi_col = "AQI" if aqi_mode.startswith("AQI (raw") else "AQI_COMPUTED"

    st.divider()
    st.header("Bộ lọc theo trạm (station-level)")
    station_list = df_st[["station_slug", "station_name"]].drop_duplicates().sort_values("station_name")
    station_names = station_list["station_name"].tolist()
    name2slug = dict(zip(station_list["station_name"], station_list["station_slug"]))

    selected_station_names = st.multiselect(
        "Chọn trạm (để trống = tất cả)",
        options=station_names,
        default=station_names[:3],
    )
    selected_slugs = [name2slug[n] for n in selected_station_names] if selected_station_names else []

    top_n = st.slider("Top N trạm ô nhiễm", 3, 20, 10)

# =============================
# FILTER DATA
# =============================
df_st_f = df_st[(df_st["date"] >= start_ts) & (df_st["date"] <= end_ts)].copy()
df_city_f = df_city[(df_city["date"] >= start_ts) & (df_city["date"] <= end_ts)].copy()

if selected_slugs:
    df_st_f = df_st_f[df_st_f["station_slug"].isin(selected_slugs)].copy()

if df_city_f.empty:
    st.warning("City CSV không có dữ liệu trong khoảng thời gian bạn chọn.")
if df_st_f.empty:
    st.warning("Stations CSV không có dữ liệu trong khoảng thời gian / trạm bạn chọn.")

# =============================
# SECTION A: CITY-LEVEL
# =============================
st.header("A) TP.HCM – City-level (từ City CSV)")

if not df_city_f.empty:
    latest_city_date = df_city_f["date"].max()
    latest_city_row = df_city_f[df_city_f["date"] == latest_city_date]

    city_latest_val = None
    if not latest_city_row.empty and latest_city_row[aqi_col].notna().any():
        city_latest_val = float(latest_city_row[aqi_col].dropna().iloc[0])

    c1, c2, c3 = st.columns(3)
    c1.metric("Ngày mới nhất (City)", latest_city_date.strftime("%Y-%m-%d"))
    c2.metric(f"{aqi_col} TP.HCM (City CSV)", f"{city_latest_val:.2f}" if city_latest_val is not None else "N/A")
    c3.metric("Phân loại (tham khảo)", aqi_category(city_latest_val) if city_latest_val is not None else "N/A")

    st.subheader("A1) Line chart – biến động các chỉ số TP.HCM theo thời gian (City CSV)")
    sel_city = st.multiselect("Chọn chỉ số (city-level)", ["AQI"] + NON_AQI, default=["AQI", "PM2,5", "PM10"])
    series = []
    for p in sel_city:
        col = aqi_col if p == "AQI" else p
        if col not in df_city_f.columns:
            continue
        tmp = df_city_f[["date", col]].dropna().rename(columns={col: "value"}).copy()
        tmp["pollutant"] = p
        series.append(tmp)

    if series:
        city_all = pd.concat(series, ignore_index=True)
        fig_city = px.line(city_all, x="date", y="value", color="pollutant",
                           title="TP.HCM – City-level time series (City CSV)")
        st.plotly_chart(fig_city, use_container_width=True)
    else:
        st.info("Không đủ dữ liệu để vẽ city-level line chart.")
else:
    st.info("Không có dữ liệu city-level trong khoảng thời gian đã chọn.")

st.divider()

# =============================
# SECTION B: STATION-LEVEL
# =============================
st.header("B) Theo trạm – Station-level (từ All Stations CSV)")

if not df_st_f.empty:
    # B1) Top stations
    st.subheader("B1) Top trạm ô nhiễm theo chỉ số (Bar chart – station-level)")
    metric_choice = st.selectbox("Chọn chỉ số để xếp hạng", ["AQI"] + NON_AQI, index=0)
    metric_col = aqi_col if metric_choice == "AQI" else metric_choice

    rank_df = station_rank(df_st_f, metric_col, agg_method).head(top_n)
    if not rank_df.empty:
        fig_rank = px.bar(
            rank_df.sort_values("value"),
            x="value",
            y="station_name",
            orientation="h",
            title=f"Top {top_n} trạm theo {metric_choice} ({agg_method})",
            hover_data=["station_slug"],
        )
        st.plotly_chart(fig_rank, use_container_width=True)
    else:
        st.info("Không đủ dữ liệu để xếp hạng.")

    st.divider()

    # B2) AQI line by station
    st.subheader("B2) Line chart – AQI theo trạm (Station-level)")
    df_line = df_st_f.copy()
    fig_aqi = px.line(
        df_line,
        x="date",
        y=aqi_col,
        color="station_name",
        title=f"{aqi_col} theo thời gian (theo trạm)",
        hover_data=["station_slug"],
    )
    # ✅ tránh “đứt đoạn” do NaN (chỉ nối hình)
    fig_aqi.update_traces(connectgaps=True)
    st.plotly_chart(fig_aqi, use_container_width=True)

    st.divider()

    # B3) Scatter correlation (station-level)
    st.subheader("B3) Scatter tương quan (non-AQI) – chọn City-level hoặc Station-level")
    mode_scatter = st.radio(
        "Chế độ Scatter",
        ["Station-level (raw)", "City-level (aggregate theo ngày từ stations)"],
        horizontal=True
    )

    x_col = st.selectbox("X", NON_AQI, index=0, key="scatter_x")
    y_col = st.selectbox("Y", NON_AQI, index=1, key="scatter_y")

    if mode_scatter.startswith("Station"):
        tmp = df_st_f[[x_col, y_col, "station_name", "date"]].dropna()
        r = corr_value(tmp, x_col, y_col)
        st.caption(f"Pearson r ≈ {r:.3f}" if not np.isnan(r) else "Không đủ dữ liệu.")
        fig = px.scatter(tmp, x=x_col, y=y_col, color="station_name", hover_data=["date"],
                         title=f"Station-level scatter: {x_col} vs {y_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        cx = city_aggregate_from_stations(df_st_f, x_col, agg_method).rename(columns={"value": x_col})
        cy = city_aggregate_from_stations(df_st_f, y_col, agg_method).rename(columns={"value": y_col})
        tmp = cx.merge(cy, on="date", how="inner").dropna()
        r = corr_value(tmp, x_col, y_col)
        st.caption(f"Pearson r (city aggregate) ≈ {r:.3f}" if not np.isnan(r) else "Không đủ dữ liệu.")
        fig = px.scatter(tmp, x=x_col, y=y_col, hover_data=["date"],
                         title=f"City-aggregate scatter: {x_col} vs {y_col} ({agg_method})")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # B4) Histogram (mode)
    st.subheader("B4) Histogram – tần suất (City-level hoặc Station-level)")
    mode_hist = st.radio(
        "Chế độ Histogram",
        ["Station-level (raw)", "City-level (aggregate theo ngày từ stations)"],
        horizontal=True
    )
    hist_col = st.selectbox("Chỉ số", ["AQI"] + NON_AQI, index=0, key="hist_col")
    hist_metric = aqi_col if hist_col == "AQI" else hist_col
    nbins = st.slider("Số bins", 10, 80, 30, key="hist_bins")

    if mode_hist.startswith("Station"):
        tmp = df_st_f[[hist_metric, "station_name"]].dropna()
        fig = px.histogram(tmp, x=hist_metric, color="station_name", nbins=nbins, barmode="overlay",
                           title=f"Station-level histogram: {hist_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        tmp = city_aggregate_from_stations(df_st_f, hist_metric, agg_method).dropna()
        fig = px.histogram(tmp, x="value", nbins=nbins,
                           title=f"City-aggregate histogram: {hist_col} ({agg_method})")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Debug: % missing theo trạm (để hiểu vì sao đường có thể đứt)", expanded=False):
        miss = df_st_f.groupby("station_name")[aqi_col].apply(lambda s: s.isna().mean()).sort_values(ascending=False)
        st.write(miss.head(20))

else:
    st.info("Không có dữ liệu station-level trong khoảng thời gian/trạm đã chọn.")

st.caption("✅ Một trang gồm cả TP.HCM (City CSV) + Theo trạm (Stations CSV).")