# -*- coding: utf-8 -*-
"""
Fetch yearly calendar data (daily) for ONE station (Hem 108 Trần Văn Quang)
for years 2024-2026 and sensors: CO, SO2, O3, NO2, PM2.5, PM10.

Key point (based on your DevTools Inspect):
- Query params: slug, slugType, sensorname
- Required headers: authorization, year, type, slug, sendevid (+ origin/referer/user-agent)

Outputs:
- output_108_tran_van_quang_2024_2026/aqi_daily_108_tran_van_quang_2024_2026.csv
- output_108_tran_van_quang_2024_2026/raw_108_tran_van_quang_2024_2026.json
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import requests
import pandas as pd

# =========================
# 1) CONFIG - EDIT HERE
# =========================

# ✅ 
AQI_TOKEN = "bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWlycXVhbGl0eS5hcWkuaW4vYXBpL3YxL2xvZ2luIiwiaWF0IjoxNzY5OTI2ODY4LCJleHAiOjE3NzIzNDYwNjgsIm5iZiI6MTc2OTkyNjg2OCwianRpIjoiY1BkRjZVNWQ5M2hqb1QwOSIsInN1YiI6IjI5MTY4IiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.2YuhyFDQPDl3UAQVJ9KGVYhaghcMdgwO44e3ePBD_AU"

BASE_URL = "https://airquality.aqi.in/api/v1/getYearlyCalenderDataCap2025BySlug"
SLUG_TYPE = "locationId"

STATION_SLUG = "vietnam/ho-chi-minh/ho-chi-minh-city/duong-ngo-quang-tham"
STATION_NAME = "Ngo Quang Tham, Ho Chi Minh City"

YEARS = [2022, 2023, 2024, 2025, 2026]

# 6 chỉ số bạn yêu cầu
SENSORS = {
    "PM2.5": "pm25",
    "PM10": "pm10",
    "CO": "co",
    "SO2": "so2",
    "O3": "o3",
    "NO2": "no2",
}

OUT_DIR = "output_HCM_Ngo_Quang_Tham_2022_2026"


# =========================
# 2) HTTP + PARSE
# =========================

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

def build_headers(slug: str, year: int, sensorname: str) -> Dict[str, str]:
    """
    Bắt chước Inspect:
      authorization: bearer ...
      year: 2024
      type: 1
      slug: <slug>
      sendevid: <sensorname>  (ví dụ pm25)
    """
    h = dict(BASE_HEADERS)
    h["authorization"] = AQI_TOKEN
    h["year"] = str(year)
    h["type"] = "1"
    h["slug"] = slug
    h["sendevid"] = sensorname
    return h

def fetch_year_sensor(
    session: requests.Session,
    slug: str,
    year: int,
    sensorname: str,
    slug_type: str,
    max_retries: int = 4,
    timeout_s: int = 25,
) -> Tuple[bool, Optional[str], Dict[str, float], Optional[Dict[str, Any]]]:
    """
    Return:
      ok, err_msg, {day: value}, raw_payload
    """
    params = {
        "slug": slug,
        "slugType": slug_type,
        "sensorname": sensorname,
        # NOTE: Inspect không có year/type trong query -> KHÔNG đưa vào params
    }
    headers = build_headers(slug, year, sensorname)

    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(BASE_URL, params=params, headers=headers, timeout=timeout_s)

            # luôn là JSON theo inspect
            payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
            if not isinstance(payload, dict):
                last_err = f"Non-JSON response (http={r.status_code})"
                time.sleep(0.6 * attempt)
                continue

            if payload.get("status") != 1:
                last_err = f"status!=1 (http={r.status_code}) msg={payload.get('msg')}"
                time.sleep(0.6 * attempt)
                continue

            data = payload.get("Data")
            if not isinstance(data, list):
                last_err = f"Missing Data[] (http={r.status_code})"
                time.sleep(0.6 * attempt)
                continue

            out: Dict[str, float] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                day = item.get("day")
                val = item.get("value")
                if isinstance(day, str):
                    try:
                        out[day] = float(val) if val is not None else None  # type: ignore
                    except Exception:
                        # bỏ qua value lỗi
                        pass

            return True, None, out, payload

        except Exception as e:
            last_err = f"exception={type(e).__name__}: {e}"
            time.sleep(0.6 * attempt)

    return False, last_err, {}, None


# =========================
# 3) BUILD TABLE + SAVE
# =========================

def date_range_df(year: int) -> pd.DataFrame:
    start = pd.Timestamp(year=year, month=1, day=1)
    end = pd.Timestamp(year=year, month=12, day=31)
    dts = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": dts.strftime("%Y-%m-%d")})

def ensure_out_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def main() -> None:
    if (not AQI_TOKEN) or ("<PASTE_YOUR_TOKEN_HERE>" in AQI_TOKEN):
        raise SystemExit("❌ Bạn chưa dán token vào biến AQI_TOKEN trong file python.")

    ensure_out_dir(OUT_DIR)

    session = requests.Session()

    raw_store: Dict[str, Any] = {
        "meta": {
            "base_url": BASE_URL,
            "slug": STATION_SLUG,
            "slugType": SLUG_TYPE,
            "years": YEARS,
            "sensors": SENSORS,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "data": {}  # year -> sensor_label -> raw payload
    }

    all_year_frames: List[pd.DataFrame] = []

    total = len(YEARS) * len(SENSORS)
    done = 0

    print(f"INFO | Station: {STATION_NAME} | slug={STATION_SLUG}")
    print(f"INFO | Years: {YEARS}")
    print(f"INFO | Sensors: {list(SENSORS.keys())}")
    print(f"INFO | Total requests: {total}")

    for year in YEARS:
        df = date_range_df(year)
        df.insert(0, "station_slug", STATION_SLUG)
        df.insert(1, "station_name", STATION_NAME)
        df.insert(2, "year", year)

        raw_store["data"].setdefault(str(year), {})

        for label, sensorname in SENSORS.items():
            ok, err, mapping, raw_payload = fetch_year_sensor(
                session=session,
                slug=STATION_SLUG,
                year=year,
                sensorname=sensorname,
                slug_type=SLUG_TYPE,
            )

            done += 1

            if ok:
                df[label] = df["date"].map(mapping)
                raw_store["data"][str(year)][label] = {
                    "ok": True,
                    "sensorname": sensorname,
                    "count": len(mapping),
                    "payload": raw_payload,
                }
                print(f"OK   | {year} | {label} ({sensorname}) | points={len(mapping)}")
            else:
                df[label] = pd.NA
                raw_store["data"][str(year)][label] = {
                    "ok": False,
                    "sensorname": sensorname,
                    "error": err,
                    "payload": raw_payload,
                }
                print(f"FAIL | {year} | {label} ({sensorname}) | {err}")

            # nghỉ nhẹ tránh spam
            time.sleep(0.12)

        all_year_frames.append(df)

    out_df = pd.concat(all_year_frames, ignore_index=True)

    # sort columns
    cols = ["station_slug", "station_name", "year", "date"] + list(SENSORS.keys())
    out_df = out_df[cols]

    csv_path = os.path.join(OUT_DIR, "aqi_daily_HCM_Ngo_Quang_Tham_2022_2026.csv")
    json_path = os.path.join(OUT_DIR, "raw_HCM_Ngo_Quang_Tham_2022_2026.json")

    out_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_store, f, ensure_ascii=False, indent=2)

    print(f"INFO | Write CSV : {csv_path}")
    print(f"INFO | Write JSON: {json_path}")
    print("DONE ✅")


if __name__ == "__main__":
    main()
