from __future__ import annotations

import os
import csv
import json
import time
import logging
import argparse
import threading
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =========================
# STATIONS (9 trạm bạn đưa)
# =========================
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

# =========================
# 7 chỉ số cần crawl (kèm AQI)
# - Mỗi sensor có thể có nhiều "tên" => thử lần lượt
# =========================
SENSORS: List[Tuple[str, List[str]]] = [
    ("CO", ["co"]),
    ("SO2", ["so2"]),
    ("NO2", ["no2"]),
    ("O3", ["o3"]),
    ("PM2.5", ["pm25", "pm2.5", "pm2_5"]),
    ("PM10", ["pm10"]),
    # AQI: tuỳ backend, thường "aqi" hoặc "AQI-IN"
    ("AQI", ["aqi", "AQI-IN", "aqi-in"]),
]

# =========================
# ENDPOINTS
# =========================
AIRQUALITY_BASE = "https://airquality.aqi.in"
AIRQUALITY_YEARLY_PATH = "/api/v1/getYearlyCalenderDataCap2025BySlug"

APISERVER_BASE = "https://apiserver.aqi.in"
APISERVER_STATION_DETAILS_PATH = "/aqi/v2/getLocationDetailsBySlug"


# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("AQI_YEARLY_FULL")


# =========================
# TOKENS (không hardcode token)
# =========================
# Khuyến nghị set env:
#   Windows PowerShell:
#     setx AQI_AIRQUALITY_TOKEN "bearer <token>"
#     setx AQI_APISERVER_TOKEN  "bearer <token>"
#
# Nếu chỉ có 1 token:
#     setx AQI_TOKEN "bearer <token>"
AQI_TOKEN = os.getenv("AQI_TOKEN", "").strip()
AIRQUALITY_TOKEN = os.getenv("AQI_AIRQUALITY_TOKEN", AQI_TOKEN).strip()
APISERVER_TOKEN = os.getenv("AQI_APISERVER_TOKEN", AQI_TOKEN).strip()

def ensure_bearer(token: str) -> str:
    t = token.strip()
    if not t:
        return ""
    return t if t.lower().startswith("bearer ") else f"bearer {t}"


# =========================
# HTTP SESSION (retry + thread-local)
# =========================
_thread_local = threading.local()

def _build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=6,
        connect=6,
        read=6,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        _thread_local.session = _build_session()
    return _thread_local.session


# =========================
# MODELS
# =========================
@dataclass
class StationInfo:
    slug: str
    station_name: str = ""
    station_address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    locationId: Optional[str] = None
    meta_source: str = ""


# =========================
# DATE HELPERS
# =========================
def iter_days_in_year(y: int):
    d = date(y, 1, 1)
    end = date(y, 12, 31)
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


# =========================
# HTTP JSON
# =========================
def http_get_json(url: str, headers: Dict[str, str], params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    sess = get_session()
    r = sess.get(url, headers=headers, params=params, timeout=timeout)
    try:
        return r.json()
    except Exception as e:
        raise RuntimeError(f"Non-JSON response | url={url} | status={r.status_code}") from e


# =========================
# FETCH STATION META (optional)
# =========================
def fetch_station_details(slug: str, timeout: int = 30) -> StationInfo:
    """
    Lấy meta trạm qua apiserver (như bạn capture).
    Nếu fail -> vẫn trả về fallback (không làm dừng crawl).
    """
    token = ensure_bearer(APISERVER_TOKEN)
    if token:
        try:
            url = f"{APISERVER_BASE}{APISERVER_STATION_DETAILS_PATH}"
            headers = {
                "authorization": token,
                "accept": "*/*",
                "origin": "https://www.aqi.in",
                "referer": "https://www.aqi.in/",
                "user-agent": "Mozilla/5.0",
            }
            params = {"slug": slug, "type": 4, "source": "web"}
            data = http_get_json(url, headers=headers, params=params, timeout=timeout)

            if data.get("status") == "success" and data.get("data"):
                r0 = data["data"][0]
                return StationInfo(
                    slug=slug,
                    station_name=str(r0.get("location", "") or ""),
                    station_address=str(r0.get("station", "") or ""),
                    city=str(r0.get("city", "") or ""),
                    state=str(r0.get("state", "") or ""),
                    country=str(r0.get("country", "") or ""),
                    latitude=r0.get("latitude", None),
                    longitude=r0.get("longitude", None),
                    locationId=str(r0.get("locationId", "") or "") or None,
                    meta_source="apiserver",
                )
        except Exception as e:
            logger.warning(f"[station_meta] apiserver fail slug={slug} | {e}")

    # fallback parse từ slug
    station_name = slug.split("/")[-1].replace("-", " ")
    return StationInfo(
        slug=slug,
        station_name=station_name,
        station_address=slug,
        city="",
        state="",
        country="Vietnam",
        latitude=None,
        longitude=None,
        locationId=None,
        meta_source="fallback",
    )


# =========================
# FETCH YEARLY CALENDAR (1 sensor / 1 call)
# =========================
def fetch_yearly_calendar_one(
    slug: str,
    sensorname: str,
    year: int,
    slug_type: str = "locationId",
    timeout: int = 30,
    min_delay_sec: float = 0.0,
) -> Dict[str, Optional[float]]:
    """
    API trả về:
      { status: 1, Data: [{day:"YYYY-MM-DD", value: ...}, ...] }
    """
    token = ensure_bearer(AIRQUALITY_TOKEN)
    if not token:
        raise RuntimeError("Thiếu AIRQUALITY token. Set env AQI_AIRQUALITY_TOKEN (hoặc AQI_TOKEN).")

    if min_delay_sec > 0:
        time.sleep(min_delay_sec)

    url = f"{AIRQUALITY_BASE}{AIRQUALITY_YEARLY_PATH}"
    headers = {
        "authorization": token,
        "accept": "*/*",
        "origin": "https://www.aqi.in",
        "referer": "https://www.aqi.in/",
        "user-agent": "Mozilla/5.0",
        # Các header bạn thấy trong DevTools:
        "sendevid": sensorname,
        "slug": slug,
        "slugType": slug_type,
        "type": "1",
        "year": str(year),
    }
    params = {
        "slug": slug,
        "slugType": slug_type,
        "sensorname": sensorname,
    }

    data = http_get_json(url, headers=headers, params=params, timeout=timeout)

    if data.get("status") != 1:
        raise RuntimeError(f"status!=1 | keys={list(data.keys())}")

    items = data.get("Data") or data.get("data") or []
    out: Dict[str, Optional[float]] = {}

    for it in items:
        d = it.get("day")
        v = it.get("value", None)
        if not d:
            continue
        if v is None:
            out[d] = None
        else:
            try:
                out[d] = float(v)
            except Exception:
                out[d] = None

    return out

def fetch_yearly_calendar_with_candidates(
    slug: str,
    sensor_candidates: List[str],
    year: int,
    timeout: int,
    min_delay_sec: float,
) -> Tuple[str, Dict[str, Optional[float]]]:
    """
    Thử nhiều sensorname cho cùng 1 chỉ số (đặc biệt hữu ích cho AQI).
    Thành công -> trả (used_sensorname, series).
    Fail hết -> raise.
    """
    last_err: Optional[Exception] = None
    for cand in sensor_candidates:
        try:
            series = fetch_yearly_calendar_one(
                slug=slug,
                sensorname=cand,
                year=year,
                slug_type="locationId",
                timeout=timeout,
                min_delay_sec=min_delay_sec,
            )
            # Nếu series rỗng vẫn coi là ok (vì bạn muốn thu thập trước, missing xử lý sau)
            return cand, series
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All candidates failed: {sensor_candidates} | last_err={last_err}")


# =========================
# EXPORT CSV
# =========================
def write_wide_csv(
    out_path: Path,
    station_infos: Dict[str, StationInfo],
    values: Dict[str, Dict[int, Dict[str, Dict[str, Optional[float]]]]],
    years: List[int],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "slug",
        "station_name",
        "station_address",
        "city",
        "state",
        "country",
        "latitude",
        "longitude",
        "locationId",
        "meta_source",
        "date",
        "year",
    ] + [col for col, _cands in SENSORS]

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for slug, info in station_infos.items():
            for y in years:
                for d in iter_days_in_year(y):
                    row = {
                        "slug": slug,
                        "station_name": info.station_name,
                        "station_address": info.station_address,
                        "city": info.city,
                        "state": info.state,
                        "country": info.country,
                        "latitude": info.latitude,
                        "longitude": info.longitude,
                        "locationId": info.locationId,
                        "meta_source": info.meta_source,
                        "date": d,
                        "year": y,
                    }
                    for sensor_col, _cands in SENSORS:
                        v = values.get(slug, {}).get(y, {}).get(sensor_col, {}).get(d, "")
                        row[sensor_col] = "" if v is None else v
                    w.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2022)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--outdir", type=str, default="output_yearly_2022_2026_full")
    parser.add_argument("--min-delay", type=float, default=0.0, help="delay nhỏ giữa request để giảm rate-limit")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    years = list(range(args.start_year, args.end_year + 1))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Station metadata
    logger.info(f"Fetch station meta: {len(STATION_SLUGS)} slugs")
    station_infos: Dict[str, StationInfo] = {slug: fetch_station_details(slug, timeout=args.timeout) for slug in STATION_SLUGS}
    (outdir / "stations_metadata.json").write_text(
        json.dumps({k: asdict(v) for k, v in station_infos.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2) Crawl data
    # values[slug][year][sensor_col][YYYY-MM-DD] = value
    values: Dict[str, Dict[int, Dict[str, Dict[str, Optional[float]]]]] = {slug: {} for slug in station_infos}
    errors: List[Dict[str, Any]] = []
    used_sensorname_map: List[Dict[str, Any]] = []

    jobs: List[Tuple[str, int, str, List[str]]] = []
    for slug in station_infos.keys():
        for y in years:
            for sensor_col, candidates in SENSORS:
                jobs.append((slug, y, sensor_col, candidates))

    logger.info(f"Total requests (station*year*sensor): {len(jobs)}")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def worker(slug: str, y: int, sensor_col: str, candidates: List[str]):
        used_name, series = fetch_yearly_calendar_with_candidates(
            slug=slug,
            sensor_candidates=candidates,
            year=y,
            timeout=args.timeout,
            min_delay_sec=args.min_delay,
        )
        return slug, y, sensor_col, used_name, series

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut_map = {ex.submit(worker, *job): job for job in jobs}
        done = 0
        for fut in as_completed(fut_map):
            slug, y, sensor_col, candidates = fut_map[fut]
            try:
                _slug, _y, _sensor_col, used_name, series = fut.result()
                values.setdefault(_slug, {}).setdefault(_y, {})[_sensor_col] = series
                used_sensorname_map.append({
                    "slug": _slug,
                    "year": _y,
                    "sensor": _sensor_col,
                    "used_sensorname": used_name,
                    "points": len(series),
                })
            except Exception as e:
                # không crash: để series rỗng
                msg = str(e)
                logger.warning(f"FAIL slug={slug} year={y} sensor={sensor_col} candidates={candidates} | {msg}")
                errors.append({
                    "slug": slug,
                    "year": y,
                    "sensor": sensor_col,
                    "candidates": candidates,
                    "error": msg,
                })
                values.setdefault(slug, {}).setdefault(y, {})[sensor_col] = {}

            done += 1
            if done % 20 == 0:
                logger.info(f"Progress: {done}/{len(jobs)}")

    (outdir / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "used_sensorname.json").write_text(json.dumps(used_sensorname_map, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3) Export WIDE CSV (1 row = station + day, 7 chỉ số)
    wide_csv = outdir / f"aqi_daily_wide_{args.start_year}_{args.end_year}_WITH_AQI.csv"
    logger.info(f"Write WIDE CSV: {wide_csv}")
    write_wide_csv(wide_csv, station_infos, values, years)

    # raw dump để debug (có thể khá to)
    raw_json = outdir / f"raw_values_{args.start_year}_{args.end_year}.json"
    logger.info(f"Write RAW JSON: {raw_json}")
    raw_json.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")

    logger.info("DONE ✅")


if __name__ == "__main__":
    main()
