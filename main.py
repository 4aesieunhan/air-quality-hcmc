# -*- coding: utf-8 -*-
"""
Crawl AQI data for multiple stations + coordinates.

Outputs:
1) output_all_stations_2022_2026/stations.csv
   station_slug, station_name, city, country, latitude, longitude

2) output_all_stations_2022_2026/aqi_daily.csv
   station_slug, date, year, pollutants  (pollutants is JSON string)

Optional:
- output_all_stations_2022_2026/aqi_daily.jsonl  (NDJSON; pollutants as real object)
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
# 1) CONFIG
# =========================================================

AIRQUALITY_TOKEN = "bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWlycXVhbGl0eS5hcWkuaW4vYXBpL3YxL2xvZ2luIiwiaWF0IjoxNzcxNjU4MjYxLCJleHAiOjE3NzQwNzc0NjEsIm5iZiI6MTc3MTY1ODI2MSwianRpIjoiV0Voc3VVNVZZYmJEQzdUUyIsInN1YiI6IjI5MTY4IiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.z0lhXv0C7dF3jyZQeY-gyTIRPHeYVvFBguCb2NkKF3o"
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

# 7 chỉ số
SENSORS: Dict[str, str] = {
    "AQI": "aqi",
    "PM2.5": "pm25",
    "PM10": "pm10",
    "CO": "co",
    "SO2": "so2",
    "O3": "o3",
    "NO2": "no2",
}

OUT_DIR = "output_all_stations_2022_2026"

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
# 4) STATION META
# =========================================================
def fetch_station_meta(session: requests.Session, slug: str) -> Dict[str, Any]:
    params = {"slug": slug, "type": 4, "source": "web"}
    headers = dict(BASE_HEADERS)
    headers["authorization"] = APISERVER_TOKEN

    js = request_json(session, APISERVER_STATION_META_URL, params=params, headers=headers)

    if js.get("status") == "success" and isinstance(js.get("data"), list) and js["data"]:
        r0 = js["data"][0]
        return {
            "station_slug": slug,
            "station_name": r0.get("location") or r0.get("station") or slug,
            "city": r0.get("city") or "",
            "country": r0.get("country") or "",
            "latitude": safe_float(r0.get("latitude")),
            "longitude": safe_float(r0.get("longitude")),
            "meta_raw": r0,
        }

    return {
        "station_slug": slug,
        "station_name": slug.split("/")[-1].replace("-", " ").title(),
        "city": "",
        "country": "Vietnam",
        "latitude": None,
        "longitude": None,
        "meta_raw": js,
    }


# =========================================================
# 5) TIME SERIES FETCH
# =========================================================
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

def fetch_year_airquality(session: requests.Session, slug: str, year: int, sensorname: str) -> Tuple[bool, Dict[str, Optional[float]], Dict[str, Any]]:
    params = {"slug": slug, "slugType": SLUG_TYPE, "sensorname": sensorname}
    headers = build_headers(AIRQUALITY_TOKEN, slug, year, sensorname)
    js = request_json(session, AIRQUALITY_YEARLY_URL, params=params, headers=headers)

    if js.get("status") == 1 and isinstance(js.get("Data"), list):
        return True, parse_day_value_list(js, "Data"), js
    return False, {}, js

def fetch_year_apiserver_calendar(session: requests.Session, slug: str, year: int, sensorname: str) -> Tuple[bool, Dict[str, Optional[float]], Dict[str, Any]]:
    params = {"slug": slug, "slugType": SLUG_TYPE, "sensorname": sensorname, "source": "web"}
    headers = build_headers(APISERVER_TOKEN, slug, year, sensorname)
    js = request_json(session, APISERVER_CALENDAR_URL, params=params, headers=headers)

    if js.get("status") == "success" and isinstance(js.get("Data"), list):
        return True, parse_day_value_list(js, "Data"), js
    return False, {}, js

def fetch_year_series(session: requests.Session, slug: str, year: int, sensorname: str) -> Tuple[str, bool, Dict[str, Optional[float]], Dict[str, Any]]:
    # 2026 ưu tiên apiserver
    if year >= 2026:
        ok, mapping, js = fetch_year_apiserver_calendar(session, slug, year, sensorname)
        if ok:
            return "apiserver_getAqiCalender", True, mapping, js
        ok2, mapping2, js2 = fetch_year_airquality(session, slug, year, sensorname)
        return "airquality_yearly_fallback", ok2, mapping2, js2

    # <=2025 ưu tiên airquality
    ok, mapping, js = fetch_year_airquality(session, slug, year, sensorname)
    if ok:
        return "airquality_yearly", True, mapping, js
    ok2, mapping2, js2 = fetch_year_apiserver_calendar(session, slug, year, sensorname)
    return "apiserver_fallback", ok2, mapping2, js2


# =========================================================
# 6) EXPORT HELPERS (2 CSV schema)
# =========================================================
def build_pollutants_json_row(row: pd.Series) -> str:
    obj = {}
    for label in SENSORS.keys():
        v = row.get(label, None)
        if pd.isna(v):
            obj[label] = None
        else:
            obj[label] = float(v)
    return json.dumps(obj, ensure_ascii=False)

def export_two_csvs(meta_df: pd.DataFrame, wide_df: pd.DataFrame) -> None:
    """
    meta_df: station meta (already)
    wide_df: columns include station_slug, date, year, and pollutant columns
    """
    # 1) stations.csv
    stations_df = meta_df[["station_slug", "station_name", "city", "country", "latitude", "longitude"]].copy()
    stations_path = os.path.join(OUT_DIR, "stations.csv")
    stations_df.to_csv(stations_path, index=False, encoding="utf-8-sig")

    # 2) aqi_daily.csv with pollutants JSON string
    aqi_daily_df = wide_df[["station_slug", "date", "year"] + list(SENSORS.keys())].copy()
    aqi_daily_df["pollutants"] = aqi_daily_df.apply(build_pollutants_json_row, axis=1)
    aqi_daily_df = aqi_daily_df[["station_slug", "date", "year", "pollutants"]].copy()

    daily_path = os.path.join(OUT_DIR, "aqi_daily.csv")
    aqi_daily_df.to_csv(daily_path, index=False, encoding="utf-8-sig")

    # Optional: NDJSON để import MongoDB chuẩn object luôn
    jsonl_path = os.path.join(OUT_DIR, "aqi_daily.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for _, r in aqi_daily_df.iterrows():
            doc = {
                "station_slug": r["station_slug"],
                "date": r["date"],   # string YYYY-MM-DD, Mongo có thể parse sau
                "year": int(r["year"]),
                "pollutants": json.loads(r["pollutants"]),
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")


# =========================================================
# 7) MAIN
# =========================================================
def main() -> None:
    if "<PASTE_AIRQUALITY_TOKEN_HERE>" in AIRQUALITY_TOKEN or not AIRQUALITY_TOKEN.strip().lower().startswith("bearer"):
        raise SystemExit("❌ Bạn chưa dán AIRQUALITY_TOKEN đúng (bearer ...).")
    if "<PASTE_APISERVER_TOKEN_HERE>" in APISERVER_TOKEN or not APISERVER_TOKEN.strip().lower().startswith("bearer"):
        raise SystemExit("❌ Bạn chưa dán APISERVER_TOKEN đúng (bearer ...).")

    ensure_out_dir(OUT_DIR)
    session = requests.Session()

    # 1) Station meta once
    print(f"INFO | Fetch station meta for {len(STATION_SLUGS)} stations...")
    station_meta_list: List[Dict[str, Any]] = []
    station_meta_map: Dict[str, Dict[str, Any]] = {}

    for slug in STATION_SLUGS:
        meta = fetch_station_meta(session, slug)
        station_meta_list.append(meta)
        station_meta_map[slug] = meta
        time.sleep(0.08)

    meta_df = pd.DataFrame(station_meta_list)
    # Save full meta debug
    meta_df.to_csv(os.path.join(OUT_DIR, "stations_meta_full_debug.csv"), index=False, encoding="utf-8-sig")

    # 2) Crawl time-series
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
            df_year.insert(1, "year", year)

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
                else:
                    df_year[label] = pd.NA
                    raw_debug["stations"][slug]["years"][str(year)][label] = {
                        "ok": False,
                        "source": source,
                        "sensorname": sensorname,
                        "error": js.get("_error") or js.get("msg") or str(js)[:200],
                        "keys": list(js.keys()) if isinstance(js, dict) else [],
                    }

                time.sleep(SLEEP_BETWEEN_REQUESTS_SEC)

            all_frames.append(df_year)

    wide_df = pd.concat(all_frames, ignore_index=True)

    # 3) Export 2 CSV theo schema bạn muốn
    export_two_csvs(meta_df, wide_df)

    # 4) Save debug json
    out_json = os.path.join(OUT_DIR, "raw_debug_allstations_2022_2026.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(raw_debug, f, ensure_ascii=False, indent=2)

    print(f"INFO | Write stations.csv: {os.path.join(OUT_DIR, 'stations.csv')}")
    print(f"INFO | Write aqi_daily.csv: {os.path.join(OUT_DIR, 'aqi_daily.csv')}")
    print(f"INFO | Write aqi_daily.jsonl: {os.path.join(OUT_DIR, 'aqi_daily.jsonl')}")
    print("DONE ✅")


if __name__ == "__main__":
    main()