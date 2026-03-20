# -*- coding: utf-8 -*-
"""
Crawl CITY-level daily data for Ho Chi Minh City (slugType=cityId, type=2)
Years: 2022-2026
Pollutants: PM2,5 ; PM10 ; CO ; SO2 ; O3 ; NO2

Sources:
- 2022-2025: https://airquality.aqi.in/api/v1/getYearlyCalenderDataCap2025BySlug
- 2026:      https://apiserver.aqi.in/aqi/getAqiCalender

Output:
- output_city_hcmc/hcmc_city_2022_2026_semicolon.csv  (sep=';')  RECOMMENDED
- output_city_hcmc/hcmc_city_2022_2026_comma.csv      (sep=',')
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests


# =========================
# CONFIG (PASTE TOKENS)
# =========================
AIRQUALITY_TOKEN = "bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWlycXVhbGl0eS5hcWkuaW4vYXBpL3YxL2xvZ2luIiwiaWF0IjoxNzcxNjU4MjYxLCJleHAiOjE3NzQwNzc0NjEsIm5iZiI6MTc3MTY1ODI2MSwianRpIjoiZ1MwdGg3SUZBa1NqU2JyOCIsInN1YiI6IjI5MTY4IiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.YvwA3AHFN9-aejoQNZmLWohSUGBK2BQd8Cy6bV4b2RU"   # token của airquality.aqi.in
APISERVER_TOKEN  = "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOjEsImlhdCI6MTc3MTY1ODI2MSwiZXhwIjoxNzcyMjYzMDYxfQ.zn7t3HxZW2lxLF6qPP3OkWQeE9jUCp-hNqYokRrWQWk"    # token của apiserver.aqi.in

CITY_SLUG = "vietnam/ho-chi-minh/ho-chi-minh-city"
SLUG_TYPE = "cityId"      # ✅ theo inspect
HEADER_TYPE = "2"         # ✅ type=2 cho city

YEARS = [2022, 2023, 2024, 2025, 2026]

# ✅ PM2.5 phải viết là PM2,5 (dùng dấu phẩy)
SENSORS = {
    "PM2,5": "pm25",
    "PM10": "pm10",
    "CO": "co",
    "SO2": "so2",
    "O3": "o3",
    "NO2": "no2",
    "AQI": "aqi",
}

OUT_DIR = "output_city_hcmc"
TIMEOUT_SEC = 25
MAX_RETRIES = 4
SLEEP_SEC = 0.12


# =========================
# ENDPOINTS
# =========================
AIRQUALITY_YEARLY_URL = "https://airquality.aqi.in/api/v1/getYearlyCalenderDataCap2025BySlug"
APISERVER_CALENDAR_URL = "https://apiserver.aqi.in/aqi/getAqiCalender"


# =========================
# HELPERS
# =========================
BASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://www.aqi.in",
    "referer": "https://www.aqi.in/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}

def ensure_out_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def date_range_df(year: int) -> pd.DataFrame:
    start = pd.Timestamp(year=year, month=1, day=1)
    end = pd.Timestamp(year=year, month=12, day=31)
    dts = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": dts.strftime("%Y-%m-%d"), "year": year})

def safe_float(x) -> Optional[float]:
    try:
        if x is None or x == "" or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None

def build_headers(token: str, slug: str, year: int, sensorname: str) -> Dict[str, str]:
    """
    Theo DevTools: year/type/slug/sendevid nằm trong headers.
    type=2 cho city
    """
    h = dict(BASE_HEADERS)
    h["authorization"] = token
    h["year"] = str(year)
    h["type"] = HEADER_TYPE
    h["slug"] = slug
    h["sendevid"] = sensorname
    return h

def request_json(session: requests.Session, url: str, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, params=params, headers=headers, timeout=TIMEOUT_SEC)
            js = r.json()
            if isinstance(js, dict):
                return js
            last_err = f"non-dict json http={r.status_code}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(0.6 * attempt)
    return {"_error": last_err}

def parse_day_value_list(js: Dict[str, Any], data_key: str = "Data") -> Dict[str, Optional[float]]:
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


# =========================
# FETCHERS
# =========================
def fetch_year_airquality(session: requests.Session, year: int, sensorname: str) -> Tuple[bool, Dict[str, Optional[float]], Dict[str, Any]]:
    """
    airquality.aqi.in yearly (good for 2022-2025)
    status: 1
    """
    params = {
        "slug": CITY_SLUG,
        "slugType": SLUG_TYPE,
        "sensorname": sensorname,
        "source": "web",     # theo inspect bạn gửi
    }
    headers = build_headers(AIRQUALITY_TOKEN, CITY_SLUG, year, sensorname)
    js = request_json(session, AIRQUALITY_YEARLY_URL, params=params, headers=headers)

    if js.get("status") == 1 and isinstance(js.get("Data"), list):
        return True, parse_day_value_list(js, "Data"), js
    return False, {}, js

def fetch_year_apiserver(session: requests.Session, year: int, sensorname: str) -> Tuple[bool, Dict[str, Optional[float]], Dict[str, Any]]:
    """
    apiserver.aqi.in calendar (for 2026)
    status: "success"
    """
    params = {
        "slug": CITY_SLUG,
        "slugType": SLUG_TYPE,
        "sensorname": sensorname,
        "source": "web",     # theo inspect bạn gửi
    }
    headers = build_headers(APISERVER_TOKEN, CITY_SLUG, year, sensorname)
    js = request_json(session, APISERVER_CALENDAR_URL, params=params, headers=headers)

    if js.get("status") == "success" and isinstance(js.get("Data"), list):
        return True, parse_day_value_list(js, "Data"), js
    return False, {}, js

def fetch_year(session: requests.Session, year: int, sensorname: str) -> Tuple[str, bool, Dict[str, Optional[float]], Dict[str, Any]]:
    # 2026 ưu tiên apiserver
    if year >= 2026:
        ok, m, js = fetch_year_apiserver(session, year, sensorname)
        if ok:
            return "apiserver_getAqiCalender", True, m, js
        ok2, m2, js2 = fetch_year_airquality(session, year, sensorname)
        return "airquality_fallback", ok2, m2, js2

    # <=2025 ưu tiên airquality
    ok, m, js = fetch_year_airquality(session, year, sensorname)
    if ok:
        return "airquality_yearly", True, m, js

    # fallback apiserver (đôi khi vẫn có)
    ok2, m2, js2 = fetch_year_apiserver(session, year, sensorname)
    return "apiserver_fallback", ok2, m2, js2


# =========================
# MAIN
# =========================
def main() -> None:
    if "<PASTE_AIRQUALITY_TOKEN_HERE>" in AIRQUALITY_TOKEN or not AIRQUALITY_TOKEN.strip().lower().startswith("bearer"):
        raise SystemExit("❌ AIRQUALITY_TOKEN chưa đúng (phải là 'bearer ...').")
    if "<PASTE_APISERVER_TOKEN_HERE>" in APISERVER_TOKEN or not APISERVER_TOKEN.strip().lower().startswith("bearer"):
        raise SystemExit("❌ APISERVER_TOKEN chưa đúng (phải là 'bearer ...').")

    ensure_out_dir(OUT_DIR)
    session = requests.Session()

    frames = []

    print(f"INFO | CITY slug={CITY_SLUG} slugType={SLUG_TYPE} type={HEADER_TYPE}")
    print(f"INFO | Years={YEARS}")
    print(f"INFO | Sensors={list(SENSORS.keys())}")

    for year in YEARS:
        df_year = date_range_df(year)

        for col_name, sensorname in SENSORS.items():
            source, ok, mapping, js = fetch_year(session, year, sensorname)
            if ok:
                df_year[col_name] = df_year["date"].map(mapping)
                print(f"OK   | {year} | {col_name} ({sensorname}) | source={source} | points={len(mapping)}")
            else:
                df_year[col_name] = pd.NA
                msg = js.get("msg") or js.get("_error") or str(js)[:120]
                print(f"FAIL | {year} | {col_name} ({sensorname}) | source={source} | {msg}")

            time.sleep(SLEEP_SEC)

        frames.append(df_year)

    out_df = pd.concat(frames, ignore_index=True)
    out_df.insert(0, "city_slug", CITY_SLUG)

    # Lưu 2 bản CSV:
    # 1) semicolon-delimited (khuyên dùng vì có cột PM2,5)
    out_semicolon = os.path.join(OUT_DIR, "hcmc_city_2022_2026_semicolon.csv")
    out_df.to_csv(out_semicolon, index=False, encoding="utf-8-sig", sep=";")

    # 2) comma-delimited chuẩn CSV (cột "PM2,5" sẽ được quote)
    out_comma = os.path.join(OUT_DIR, "hcmc_city_2022_2026_comma.csv")
    out_df.to_csv(out_comma, index=False, encoding="utf-8-sig", sep=",")

    print(f"INFO | Wrote: {out_semicolon}")
    print(f"INFO | Wrote: {out_comma}")
    print("DONE ✅")

if __name__ == "__main__":
    main()