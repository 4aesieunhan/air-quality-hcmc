from __future__ import annotations

import csv
import json
import os
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None  # nếu máy bạn quá cũ, ta sẽ fallback parsing date bằng chuỗi


# =========================
# CẤU HÌNH
# =========================

BASE_URL = "https://apiserver.aqi.in"

# Endpoint theo đúng bạn capture trên DevTools
LOCATION_DETAILS_PATH = "/aqi/v2/getLocationDetailsBySlug"
HISTORY_30D_PATH = "/aqi/getLast30DaysHistory"

# Danh sách trạm (nhiều trạm)
STATION_SLUGS = [
    # ví dụ từ bạn:
    "vietnam/ho-chi-minh/ho-chi-minh-city/hem-108-tran-van-quang",
    # trạm khác bạn đang dùng trong code:
    "vietnam/ho-chi-minh/ho-chi-minh-city/tp-ho-chi-minh-duong-nguyen-van-tao",
    # thêm slug khác vào đây...
    "vietnam/ho-chi-minh/ho-chi-minh-city/ho-chi-minh-city-us-consulate",
    "vietnam/ho-chi-minh/ho-chi-minh-city/duong-ngo-quang-tham",
    "vietnam/ho-chi-minh/ho-chi-minh-city/long-an-tt-van-hoa-huyen-can-giuoc",
    "vietnam/ho-chi-minh/ho-chi-minh-city/long-an-xa-duc-lap-ha",
    "vietnam/binh-duong/thanh-pho-thu-dau-mot/hiep-thanh",
    "vietnam/ba-ria-vung-tau/thanh-pho-ba-ria/phuoc-hiep",
    "vietnam/ba-ria-vung-tau/vung-tau/phuong-7"
]

# 7 chỉ số cần lấy
# - key = tên cột trong bảng output
# - candidates = thử nhiều tên sensor nếu API có biến thể
SENSORS: List[Tuple[str, List[str]]] = [
    ("CO", ["co"]),
    ("SO2", ["so2"]),
    ("NO2", ["no2"]),
    ("O3", ["o3"]),
    ("PM2.5", ["pm25", "pm2.5", "pm2_5"]),
    ("PM10", ["pm10"]),
    ("AQI", ["aqi", "AQI-IN", "aqi-in", "AQI"]),
]

# Múi giờ bạn muốn quy đổi ngày (optional)
LOCAL_TZ = "Asia/Ho_Chi_Minh"

# Output
OUTPUT_DIR = Path("output_aqi")
DAILY_CSV = OUTPUT_DIR / "aqi_last30days_daily_all_stations.csv"
SUMMARY_CSV = OUTPUT_DIR / "aqi_last30days_summary_all_stations.csv"
FULL_JSON = OUTPUT_DIR / "aqi_last30days_full.json"

# Token: nên set ENV để an toàn (không commit token lên git)
# Windows PowerShell:
#   setx AQI_TOKEN "bearer eyJhbGciOi..."
# CMD:
#   setx AQI_TOKEN "bearer eyJhbGciOi..."
AUTH_TOKEN = os.getenv("AQI_TOKEN", "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOjEsImlhdCI6MTc2OTc2MTY3MSwiZXhwIjoxNzcwMzY2NDcxfQ.AYc0Br1M9H24-wXYAoMV79qfq5GchfCR46UqfNsLkVU").strip()

# Nếu bạn muốn hardcode (không khuyến nghị), dán vào đây:
# AUTH_TOKEN = "bearer eyJhbGciOi..."


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("aqi_last30days")


# =========================
# DATA MODELS
# =========================

@dataclass
class StationInfo:
    slug: str
    locationId: Optional[str]
    station: str
    location: str
    city: str
    state: str
    country: str
    latitude: Optional[float]
    longitude: Optional[float]
    time_zone: Optional[str]
    updated_at: Optional[str]


# =========================
# UTILS
# =========================

def ensure_bearer(token: str) -> str:
    token = token.strip()
    if not token:
        return ""
    return token if token.lower().startswith("bearer ") else f"bearer {token}"

def safe_get(d: Dict[str, Any], key: str, default: Any = "") -> Any:
    v = d.get(key, default)
    return default if v is None else v

def parse_date_key(ts: str) -> str:
    """
    Convert timeArray element -> YYYY-MM-DD key.
    API bạn đưa thường dạng: 2026-01-29T00:00:00.000Z
    """
    if not ts:
        return ""
    # Fast path nếu chuỗi có YYYY-MM-DD ở đầu
    if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
        yyyy_mm_dd = ts[:10]
    else:
        yyyy_mm_dd = ts

    # Nếu có zoneinfo thì parse chuẩn + đổi tz (nếu muốn)
    if ZoneInfo is not None and ("T" in ts):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            tz = ZoneInfo(LOCAL_TZ) if LOCAL_TZ else None
            if tz:
                dt = dt.astimezone(tz)
            return dt.date().isoformat()
        except Exception:
            return yyyy_mm_dd

    return yyyy_mm_dd

def mk_session() -> requests.Session:
    """
    Session có retry để giảm lỗi 429/5xx.
    """
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# =========================
# CLIENT
# =========================

class AQIClient:
    def __init__(self, auth_token: str, base_url: str = BASE_URL, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = mk_session()

        token = ensure_bearer(auth_token)
        if not token:
            raise SystemExit(
                "Bạn chưa có token. Hãy set biến môi trường AQI_TOKEN "
                "hoặc gán AUTH_TOKEN trong code."
            )

        self.headers = {
            "authorization": token,
            "accept": "*/*",
            "origin": "https://www.aqi.in",
            "referer": "https://www.aqi.in/",
            "user-agent": "Mozilla/5.0",
        }

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, headers=self.headers, params=params, timeout=self.timeout)
        # nếu server trả non-JSON thì raise rõ ràng
        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Non-JSON response from {url} | HTTP {resp.status_code}") from e

        # Không raise theo status_code vì có khi API trả 200 nhưng status=error
        return data

    def get_station_details(self, slug: str) -> StationInfo:
        params = {"slug": slug, "type": 4, "source": "web"}
        data = self._get_json(LOCATION_DETAILS_PATH, params=params)

        if data.get("status") != "success":
            raise RuntimeError(f"Location details failed for slug={slug} | payload={data}")

        rows = data.get("data") or []
        if not rows:
            raise RuntimeError(f"Location details empty for slug={slug} | payload={data}")

        r0 = rows[0]
        return StationInfo(
            slug=slug,
            locationId=str(safe_get(r0, "locationId", "")) or None,
            station=str(safe_get(r0, "station", "")),
            location=str(safe_get(r0, "location", "")),
            city=str(safe_get(r0, "city", "")),
            state=str(safe_get(r0, "state", "")),
            country=str(safe_get(r0, "country", "")),
            latitude=safe_get(r0, "latitude", None),
            longitude=safe_get(r0, "longitude", None),
            time_zone=str(safe_get(r0, "time_zone", "")) or None,
            updated_at=str(safe_get(r0, "updated_at", "")) or None,
        )

    def get_last30_history(
        self,
        slug_value: str,
        sensorname: str,
        slug_type: str = "locationId",
    ) -> Dict[str, Any]:
        """
        Return raw history payload:
        data: { minValue, maxValue, avgValue, averageArray, timeArray }
        """
        params = {
            "slug": slug_value,
            "sensorname": sensorname,
            "slugType": slug_type,
            "source": "web",
        }
        data = self._get_json(HISTORY_30D_PATH, params=params)
        if data.get("status") != "success":
            raise RuntimeError(
                f"History failed slug={slug_value} slugType={slug_type} sensor={sensorname} | payload={data}"
            )

        d = data.get("data") or {}
        if not d.get("timeArray") or not d.get("averageArray"):
            raise RuntimeError(
                f"History missing arrays slug={slug_value} slugType={slug_type} sensor={sensorname} | payload={data}"
            )
        return d

    def get_sensor_series_for_station(
        self,
        station: StationInfo,
        sensor_candidates: List[str],
    ) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
        """
        Try multiple candidates sensor names and multiple ways to call slug/slugType,
        returns:
          - used_sensorname
          - series: {YYYY-MM-DD: value}
          - summary: {minValue,maxValue,avgValue}
        """
        # Theo capture của bạn: slug là location slug string, slugType=locationId
        attempts: List[Tuple[str, str]] = [
            (station.slug, "locationId"),
            (station.slug, "slug"),
        ]

        # Nếu có locationId thì thử thêm
        if station.locationId:
            attempts.append((station.locationId, "locationId"))

        last_err: Optional[Exception] = None

        for candidate in sensor_candidates:
            for slug_value, slug_type in attempts:
                try:
                    raw = self.get_last30_history(slug_value=slug_value, sensorname=candidate, slug_type=slug_type)
                    time_arr = raw["timeArray"]
                    avg_arr = raw["averageArray"]

                    if len(time_arr) != len(avg_arr):
                        raise RuntimeError(
                            f"Length mismatch timeArray({len(time_arr)}) != averageArray({len(avg_arr)}) "
                            f"sensor={candidate} station={station.slug}"
                        )

                    series: Dict[str, float] = {}
                    for ts, v in zip(time_arr, avg_arr):
                        date_key = parse_date_key(str(ts))
                        # v có thể là int/float
                        try:
                            series[date_key] = float(v)
                        except Exception:
                            # nếu value bị null/string lạ => bỏ
                            continue

                    summary = {
                        "minValue": raw.get("minValue"),
                        "maxValue": raw.get("maxValue"),
                        "avgValue": raw.get("avgValue"),
                    }
                    return candidate, series, summary

                except Exception as e:
                    last_err = e
                    continue

        raise RuntimeError(
            f"Không lấy được dữ liệu cho sensor_candidates={sensor_candidates} tại station={station.slug}. "
            f"Lỗi cuối: {last_err}"
        )


# =========================
# MERGE + EXPORT
# =========================

def merge_station_daily_rows(
    station: StationInfo,
    sensor_series: Dict[str, Dict[str, float]],
) -> List[Dict[str, Any]]:
    """
    sensor_series: {"CO": {"2026-01-01": 123, ...}, "SO2": {...}, ...}
    Return rows per date with all sensors in one row.
    """
    all_dates = set()
    for s, series in sensor_series.items():
        all_dates.update(series.keys())

    dates_sorted = sorted(all_dates)
    rows: List[Dict[str, Any]] = []

    for d in dates_sorted:
        row: Dict[str, Any] = {
            "station_name": station.location or station.station,
            "station_address": station.station,
            "city": station.city,
            "state": station.state,
            "country": station.country,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "locationId": station.locationId,
            "slug": station.slug,
            "date": d,
        }
        # fill sensor columns
        for sensor_key, _cands in SENSORS:
            row[sensor_key] = sensor_series.get(sensor_key, {}).get(d, "")

        rows.append(row)

    return rows

def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main() -> None:
    client = AQIClient(auth_token=AUTH_TOKEN)

    all_daily_rows: List[Dict[str, Any]] = []
    all_summary_rows: List[Dict[str, Any]] = []

    # lưu đầy đủ theo từng station để debug dễ
    stations_payload: List[Dict[str, Any]] = []

    for idx, slug in enumerate(STATION_SLUGS, 1):
        logger.info(f"[{idx}/{len(STATION_SLUGS)}] Fetch station details: {slug}")
        try:
            station = client.get_station_details(slug)
        except Exception as e:
            logger.error(f"❌ Không lấy được station details cho slug={slug}: {e}")
            continue

        sensor_series: Dict[str, Dict[str, float]] = {}
        sensor_meta: Dict[str, Any] = {}

        for sensor_key, candidates in SENSORS:
            logger.info(f"  - Fetch 30d history: {sensor_key} ({candidates})")
            try:
                used_name, series, summary = client.get_sensor_series_for_station(station, candidates)
                sensor_series[sensor_key] = series
                sensor_meta[sensor_key] = {
                    "used_sensorname": used_name,
                    "summary": summary,
                    "points": len(series),
                }

                all_summary_rows.append({
                    "station_name": station.location or station.station,
                    "station_address": station.station,
                    "city": station.city,
                    "state": station.state,
                    "country": station.country,
                    "locationId": station.locationId,
                    "slug": station.slug,
                    "sensor": sensor_key,
                    "used_sensorname": used_name,
                    "minValue": summary.get("minValue"),
                    "maxValue": summary.get("maxValue"),
                    "avgValue": summary.get("avgValue"),
                    "points": len(series),
                })

            except Exception as e:
                logger.error(f"    ⚠️ Lỗi lấy {sensor_key} cho station={slug}: {e}")
                # vẫn tiếp tục lấy sensor khác
                sensor_series[sensor_key] = {}
                sensor_meta[sensor_key] = {"error": str(e), "points": 0}

        daily_rows = merge_station_daily_rows(station, sensor_series)
        logger.info(f"  ✅ Merged daily rows: {len(daily_rows)}")

        all_daily_rows.extend(daily_rows)

        stations_payload.append({
            "station": station.__dict__,
            "sensor_meta": sensor_meta,
            "daily_rows_count": len(daily_rows),
        })

    # Export 1 bảng duy nhất cho tất cả trạm
    daily_fieldnames = [
        "station_name", "station_address", "city", "state", "country",
        "latitude", "longitude", "locationId", "slug", "date",
        "CO", "SO2", "NO2", "O3", "PM2.5", "PM10", "AQI"
    ]

    summary_fieldnames = [
        "station_name", "station_address", "city", "state", "country",
        "locationId", "slug", "sensor", "used_sensorname",
        "minValue", "maxValue", "avgValue", "points"
    ]

    logger.info(f"📄 Write DAILY CSV: {DAILY_CSV} | rows={len(all_daily_rows)}")
    write_csv(DAILY_CSV, all_daily_rows, daily_fieldnames)

    logger.info(f"📄 Write SUMMARY CSV: {SUMMARY_CSV} | rows={len(all_summary_rows)}")
    write_csv(SUMMARY_CSV, all_summary_rows, summary_fieldnames)

    full_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "base_url": BASE_URL,
        "stations_requested": STATION_SLUGS,
        "stations": stations_payload,
        "daily_rows": all_daily_rows,
        "summary_rows": all_summary_rows,
    }

    logger.info(f"🧾 Write FULL JSON: {FULL_JSON}")
    write_json(FULL_JSON, full_payload)

    logger.info("🎉 DONE!")

if __name__ == "__main__":
    main()
