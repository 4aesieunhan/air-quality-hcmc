# -*- coding: utf-8 -*-
"""
Crawl AQI data for multiple stations + coordinates.

Data sources:
1) Station meta (lat/lon): apiserver.aqi.in/aqi/v3/getLocationDetailsBySlug
2) Yearly calendar (mostly 2022-2025): airquality.aqi.in/api/v1/getYearlyCalenderDataCap2025BySlug
3) Calendar for 2026 (and fallback): apiserver.aqi.in/aqi/getAqiCalender

Output:
- output_all_stations_2022_2026/stations_meta.csv
- output_all_stations_2022_2026/aqi_daily_allstations_2022_2026.csv
- output_all_stations_2022_2026/raw_debug_allstations_2022_2026.json
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests


# =========================================================
# 1) CONFIG - DÁN TOKEN + DS TRẠM + NĂM + CHỈ SỐ
# =========================================================

# ✅ Token của domain airquality.aqi.in (inspect của getYearlyCalenderDataCap2025BySlug)
AIRQUALITY_TOKEN = "bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWlycXVhbGl0eS5hcWkuaW4vYXBpL3YxL2xvZ2luIiwiaWF0IjoxNzcxNjU4MjYxLCJleHAiOjE3NzQwNzc0NjEsIm5iZiI6MTc3MTY1ODI2MSwianRpIjoiV0Voc3VVNVZZYmJEQzdUUyIsInN1YiI6IjI5MTY4IiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.z0lhXv0C7dF3jyZQeY-gyTIRPHeYVvFBguCb2NkKF3o"

# ✅ Token của domain apiserver.aqi.in (inspect của getLocationDetailsBySlug + getAqiCalender)
APISERVER_TOKEN = "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOjEsImlhdCI6MTc3MTY1ODI2MSwiZXhwIjoxNzcyMjYzMDYxfQ.zn7t3HxZW2lxLF6qPP3OkWQeE9jUCp-hNqYokRrWQWk"

STATION_SLUGS = [
    "vietnam/ho-chi-minh/ho-chi-minh-city/hem-108-tran-van-quang",
    "vietnam/ho-chi-minh/ho-chi-minh-city/tp-ho-chi-minh-duong-nguyen-van-tao",
    "vietnam/ho-chi-minh/ho-chi-minh-city/ho-chi-minh-city-us-consulate",
    "vietnam/ho-chi-minh/ho-chi-minh-city/duong-ngo-quang-tham",
    "vietnam/ho-chi-minh/ho-chi-minh-city/long-an-tt-van-hoa-huyen-can-giuoc",
    "vietnam/ho-chi-minh/ho-chi-minh-city/long-an-xa-duc-lap-ha",
    "vietnam/binh-duong/thanh-pho-thu-dau-mot/hiep-thanh",
    "vietnam/ba-ria-vung-tau/thanh-pho-ba-ria/phuoc-hiep",
    "vietnam/ba-ria-vung-tau/vung-tau/phuong-7",
]

YEARS = [2022, 2023, 2024, 2025, 2026]

# 7 chỉ số bạn yêu cầu (AQI sẽ thử fetch; nếu fail thì để trống)
SENSORS: Dict[str, str] = {
    "PM2.5": "pm25",
    "PM10": "pm10",
    "SO2": "so2",
    "O3": "o3",
    "CO": "co",
    "NO2": "no2",
    "AQI": "aqi",  # nhiều trạm có thể fail => OK, mình vẫn giữ cột
}

OUT_DIR = "output_all_stations_2022_2026"

# tránh rate limit
SLEEP_BETWEEN_REQUESTS_SEC = 0.12
TIMEOUT_SEC = 25
MAX_RETRIES = 4

SLUG_TYPE = "locationId"


# =========================================================
# 2) ENDPOINTS
# =========================================================

AIRQUALITY_YEARLY_URL = "https://airquality.aqi.in/api/v1/getYearlyCalenderDataCap2025BySlug"

APISERVER_STATION_META_URL = "https://apiserver.aqi.in/aqi/v3/getLocationDetailsBySlug"
APISERVER_CALENDAR_URL = "https://apiserver.aqi.in/aqi/getAqiCalender"


# =========================================================
# 3) HTTP HELPERS
# =========================================================

BASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://www.aqi.in",
    "referer": "https://www.aqi.in/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

def ensure_out_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def date_range_df(year: int) -> pd.DataFrame:
    start = pd.Timestamp(year=year, month=1, day=1)
    end = pd.Timestamp(year=year, month=12, day=31)
    dts = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": dts.strftime("%Y-%m-%d")})

def build_headers(token: str, slug: str, year: int, sensorname: str) -> Dict[str, str]:
    """
    Theo DevTools Inspect: year/type/slug/sendevid nằm trong headers.
    """
    h = dict(BASE_HEADERS)
    h["authorization"] = token
    h["year"] = str(year)
    h["type"] = "1"
    h["slug"] = slug
    h["sendevid"] = sensorname
    return h

def safe_float(x) -> Optional[float]:
    try:
        if x is None or x == "" or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None

def request_json(session: requests.Session, url: str, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, params=params, headers=headers, timeout=TIMEOUT_SEC)
            data = r.json()
            if isinstance(data, dict):
                return data
            last_err = f"non-dict json (http={r.status_code})"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(0.6 * attempt)
    return {"_error": last_err}


# =========================================================
# 4) FETCH STATION META (lat/lon)
# =========================================================

def fetch_station_meta(session: requests.Session, slug: str) -> Dict[str, Any]:
    """
    GET https://apiserver.aqi.in/aqi/v3/getLocationDetailsBySlug?slug=...&type=4&source=web
    Returns first item from data[]
    """
    params = {"slug": slug, "type": 4, "source": "web"}
    headers = dict(BASE_HEADERS)
    headers["authorization"] = APISERVER_TOKEN

    js = request_json(session, APISERVER_STATION_META_URL, params=params, headers=headers)

    # expected: {"status":"success","data":[{...}]}
    if js.get("status") == "success" and isinstance(js.get("data"), list) and js["data"]:
        r0 = js["data"][0]
        return {
            "station_slug": slug,
            "station_name": r0.get("location") or r0.get("station") or slug,
            "station_address": r0.get("station") or "",
            "city": r0.get("city") or "",
            "state": r0.get("state") or "",
            "country": r0.get("country") or "",
            "latitude": r0.get("latitude"),
            "longitude": r0.get("longitude"),
            "locationId": r0.get("locationId"),
            "uid": r0.get("uid"),
            "meta_raw": r0,  # giữ debug
        }

    # fallback nếu fail
    return {
        "station_slug": slug,
        "station_name": slug.split("/")[-1].replace("-", " ").title(),
        "station_address": "",
        "city": "",
        "state": "",
        "country": "Vietnam",
        "latitude": None,
        "longitude": None,
        "locationId": None,
        "uid": None,
        "meta_raw": js,
    }


# =========================================================
# 5) FETCH TIME SERIES
# =========================================================

def parse_day_value_list(js: Dict[str, Any], data_key: str = "Data") -> Dict[str, Optional[float]]:
    """
    Convert Data = [{day: "...", value: ...}, ...] -> mapping
    """
    out: Dict[str, Optional[float]] = {}
    items = js.get(data_key)
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        day = it.get("day")
        val = it.get("value")
        if isinstance(day, str):
            out[day] = safe_float(val)
    return out

def fetch_year_airquality(session: requests.Session, slug: str, year: int, sensorname: str) -> Tuple[bool, Dict[str, Optional[float]], Dict[str, Any]]:
    """
    airquality yearly calendar (usually works for 2022-2025):
    GET /getYearlyCalenderDataCap2025BySlug?slug=...&slugType=locationId&sensorname=...
    + headers must include year/type/slug/sendevid
    returns {status:1, Data:[...]}
    """
    params = {"slug": slug, "slugType": SLUG_TYPE, "sensorname": sensorname}
    headers = build_headers(AIRQUALITY_TOKEN, slug, year, sensorname)

    js = request_json(session, AIRQUALITY_YEARLY_URL, params=params, headers=headers)

    if js.get("status") == 1 and isinstance(js.get("Data"), list):
        return True, parse_day_value_list(js, "Data"), js
    return False, {}, js

def fetch_year_apiserver_calendar(session: requests.Session, slug: str, year: int, sensorname: str) -> Tuple[bool, Dict[str, Optional[float]], Dict[str, Any]]:
    """
    apiserver calendar:
    GET /aqi/getAqiCalender?slug=...&slugType=locationId&sensorname=...&source=web
    + headers include year/type/slug/sendevid
    returns {status:"success", Data:[...]}
    """
    params = {"slug": slug, "slugType": SLUG_TYPE, "sensorname": sensorname, "source": "web"}
    headers = build_headers(APISERVER_TOKEN, slug, year, sensorname)

    js = request_json(session, APISERVER_CALENDAR_URL, params=params, headers=headers)

    if js.get("status") == "success" and isinstance(js.get("Data"), list):
        return True, parse_day_value_list(js, "Data"), js
    return False, {}, js

def fetch_year_series(session: requests.Session, slug: str, year: int, sensorname: str) -> Tuple[str, bool, Dict[str, Optional[float]], Dict[str, Any]]:
    """
    Strategy:
    - For years <= 2025: try airquality first, fallback apiserver
    - For year == 2026: try apiserver first (vì bạn nói 2026 phải dùng getAqiCalender), fallback airquality
    """
    if year >= 2026:
        ok, mapping, js = fetch_year_apiserver_calendar(session, slug, year, sensorname)
        if ok:
            return "apiserver_getAqiCalender", True, mapping, js
        ok2, mapping2, js2 = fetch_year_airquality(session, slug, year, sensorname)
        return "airquality_yearly_fallback", ok2, mapping2, js2

    # year <= 2025
    ok, mapping, js = fetch_year_airquality(session, slug, year, sensorname)
    if ok:
        return "airquality_yearly", True, mapping, js
    ok2, mapping2, js2 = fetch_year_apiserver_calendar(session, slug, year, sensorname)
    return "apiserver_fallback", ok2, mapping2, js2


# =========================================================
# 6) MAIN
# =========================================================

def main() -> None:
    if "<PASTE_AIRQUALITY_TOKEN_HERE>" in AIRQUALITY_TOKEN or not AIRQUALITY_TOKEN.strip().lower().startswith("bearer"):
        raise SystemExit("❌ Bạn chưa dán AIRQUALITY_TOKEN đúng (phải có 'bearer ...').")
    if "<PASTE_APISERVER_TOKEN_HERE>" in APISERVER_TOKEN or not APISERVER_TOKEN.strip().lower().startswith("bearer"):
        raise SystemExit("❌ Bạn chưa dán APISERVER_TOKEN đúng (phải có 'bearer ...').")

    ensure_out_dir(OUT_DIR)
    session = requests.Session()

    # 1) fetch station meta once
    station_meta_list: List[Dict[str, Any]] = []
    station_meta_map: Dict[str, Dict[str, Any]] = {}

    print(f"INFO | Fetch station meta for {len(STATION_SLUGS)} stations...")
    for slug in STATION_SLUGS:
        meta = fetch_station_meta(session, slug)
        station_meta_list.append(meta)
        station_meta_map[slug] = meta
        time.sleep(0.08)

    # save station meta CSV
    meta_df = pd.DataFrame([
        {
            "station_slug": m["station_slug"],
            "station_name": m["station_name"],
            "station_address": m["station_address"],
            "city": m["city"],
            "state": m["state"],
            "country": m["country"],
            "latitude": m["latitude"],
            "longitude": m["longitude"],
            "locationId": m["locationId"],
            "uid": m["uid"],
        }
        for m in station_meta_list
    ])
    meta_csv = os.path.join(OUT_DIR, "stations_meta.csv")
    meta_df.to_csv(meta_csv, index=False, encoding="utf-8-sig")
    print(f"INFO | Write station meta: {meta_csv}")

    # 2) fetch time series for all station/year/sensor
    raw_debug: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stations": {},
        "notes": {
            "airquality_yearly": AIRQUALITY_YEARLY_URL,
            "apiserver_calendar": APISERVER_CALENDAR_URL,
            "apiserver_station_meta": APISERVER_STATION_META_URL,
        }
    }

    all_frames: List[pd.DataFrame] = []
    total = len(STATION_SLUGS) * len(YEARS) * len(SENSORS)
    done = 0

    print(f"INFO | Total requests (station*year*sensor): {total}")

    for slug in STATION_SLUGS:
        meta = station_meta_map[slug]
        raw_debug["stations"].setdefault(slug, {"meta": meta, "years": {}})

        for year in YEARS:
            df_year = date_range_df(year)
            df_year.insert(0, "station_slug", slug)
            df_year.insert(1, "station_name", meta.get("station_name"))
            df_year.insert(2, "latitude", meta.get("latitude"))
            df_year.insert(3, "longitude", meta.get("longitude"))
            df_year.insert(4, "year", year)

            raw_debug["stations"][slug]["years"].setdefault(str(year), {})

            for label, sensorname in SENSORS.items():
                source, ok, mapping, js = fetch_year_series(session, slug, year, sensorname)

                done += 1
                if done % 20 == 0:
                    print(f"INFO | Progress: {done}/{total}")

                if ok:
                    df_year[label] = df_year["date"].map(mapping)
                    raw_debug["stations"][slug]["years"][str(year)][label] = {
                        "ok": True,
                        "source": source,
                        "sensorname": sensorname,
                        "points": len(mapping),
                        "keys": list(js.keys()) if isinstance(js, dict) else [],
                    }
                    print(f"OK   | {slug} | {year} | {label} ({sensorname}) | source={source} | points={len(mapping)}")
                else:
                    df_year[label] = pd.NA
                    raw_debug["stations"][slug]["years"][str(year)][label] = {
                        "ok": False,
                        "source": source,
                        "sensorname": sensorname,
                        "error": js.get("_error") or js.get("msg") or str(js)[:200],
                        "keys": list(js.keys()) if isinstance(js, dict) else [],
                    }
                    print(f"FAIL | {slug} | {year} | {label} ({sensorname}) | source={source} | msg={js.get('msg')}")

                time.sleep(SLEEP_BETWEEN_REQUESTS_SEC)

            all_frames.append(df_year)

    out_df = pd.concat(all_frames, ignore_index=True)

    # cột chuẩn
    cols = ["station_slug", "station_name", "latitude", "longitude", "year", "date"] + list(SENSORS.keys())
    for c in cols:
        if c not in out_df.columns:
            out_df[c] = pd.NA
    out_df = out_df[cols]

    out_csv = os.path.join(OUT_DIR, "aqi_daily_allstations_2022_2026.csv")
    out_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"INFO | Write data CSV: {out_csv}")

    out_json = os.path.join(OUT_DIR, "raw_debug_allstations_2022_2026.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(raw_debug, f, ensure_ascii=False, indent=2)
    print(f"INFO | Write debug JSON: {out_json}")

    print("DONE ✅")


if __name__ == "__main__":
    main()