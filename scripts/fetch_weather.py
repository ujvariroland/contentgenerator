"""Check weather for today's outdoor tennis tournament cities and flag anomalies.

Usage:
    python scripts/fetch_weather.py --cities-file data/tournaments_today.json

Reads OPENWEATHERMAP_API_KEY from the environment (.env). Writes matching anomalies
to stdout as JSON (the caller / Claude decides whether to turn this into a draft file),
and appends any found anomalies to data/weather_anomaly_log.json for history.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

from utils import load_config, project_path, read_json, write_json, today_str


def geocode_city(city: str, country: str, api_key: str) -> tuple[float, float] | None:
    url = "https://api.openweathermap.org/geo/1.0/direct"
    resp = requests.get(url, params={"q": f"{city},{country}", "limit": 1, "appid": api_key}, timeout=15)
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return results[0]["lat"], results[0]["lon"]


def fetch_forecast(lat: float, lon: float, api_key: str, units: str, base_url: str) -> dict:
    url = f"{base_url}/forecast"
    resp = requests.get(
        url,
        params={"lat": lat, "lon": lon, "appid": api_key, "units": units},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def detect_anomalies(forecast: dict, thresholds: dict, tournament_name: str, city: str) -> list[dict]:
    anomalies = []
    # Only look at the next ~24h of 3-hour forecast entries (today's play window).
    entries = forecast.get("list", [])[:8]

    max_temp = max((e["main"]["temp_max"] for e in entries), default=None)
    min_temp = min((e["main"]["temp_min"] for e in entries), default=None)
    max_pop = max((e.get("pop", 0) for e in entries), default=0)
    max_rain_3h = max((e.get("rain", {}).get("3h", 0) for e in entries), default=0)
    max_wind_ms = max((e["wind"]["speed"] for e in entries), default=0)
    max_gust_ms = max((e["wind"].get("gust", e["wind"]["speed"]) for e in entries), default=0)

    max_wind_kmh = max_wind_ms * 3.6
    max_gust_kmh = max_gust_ms * 3.6

    if max_temp is not None and max_temp >= thresholds["extreme_heat_c"]:
        anomalies.append({
            "tournament": tournament_name, "city": city, "type": "extreme_heat",
            "severity": "severe" if max_temp >= thresholds["extreme_heat_c"] + 3 else "moderate",
            "detail": f"Forecast high {max_temp:.1f}C, threshold {thresholds['extreme_heat_c']}C",
        })
    if min_temp is not None and min_temp <= thresholds["extreme_cold_c"]:
        anomalies.append({
            "tournament": tournament_name, "city": city, "type": "extreme_cold",
            "severity": "severe" if min_temp <= thresholds["extreme_cold_c"] - 3 else "moderate",
            "detail": f"Forecast low {min_temp:.1f}C, threshold {thresholds['extreme_cold_c']}C",
        })
    if max_pop >= thresholds["heavy_rain_pop"] or max_rain_3h >= thresholds["heavy_rain_mm_3h"]:
        anomalies.append({
            "tournament": tournament_name, "city": city, "type": "heavy_rain",
            "severity": "severe" if max_rain_3h >= thresholds["heavy_rain_mm_3h"] * 2 else "moderate",
            "detail": f"Precipitation probability {max_pop*100:.0f}%, up to {max_rain_3h:.1f}mm/3h",
        })
    if max_wind_kmh >= thresholds["high_wind_kmh"] or max_gust_kmh >= thresholds["high_wind_gust_kmh"]:
        anomalies.append({
            "tournament": tournament_name, "city": city, "type": "high_wind",
            "severity": "severe" if max_gust_kmh >= thresholds["high_wind_gust_kmh"] * 1.3 else "moderate",
            "detail": f"Wind up to {max_wind_kmh:.0f}km/h, gusts up to {max_gust_kmh:.0f}km/h",
        })

    return anomalies


def main() -> int:
    load_dotenv(project_path(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities-file", required=True, help="Path to tournaments_today.json")
    args = parser.parse_args()

    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        print("ERROR: OPENWEATHERMAP_API_KEY not set (check your .env file).", file=sys.stderr)
        return 1

    config = load_config()
    thresholds = config["weather"]["thresholds"]
    units = config["weather"]["units"]
    base_url = config["weather"]["api_base_url"]

    cities_path = Path(args.cities_file)
    if not cities_path.is_absolute():
        cities_path = project_path(args.cities_file)
    data = read_json(cities_path, default={"tournaments": []})

    all_anomalies: list[dict] = []
    for t in data.get("tournaments", []):
        if t.get("indoor"):
            continue
        coords = geocode_city(t["city"], t.get("country", ""), api_key)
        if coords is None:
            print(f"WARNING: could not geocode {t['city']}", file=sys.stderr)
            continue
        forecast = fetch_forecast(coords[0], coords[1], api_key, units, base_url)
        all_anomalies.extend(detect_anomalies(forecast, thresholds, t["name"], t["city"]))

    if all_anomalies:
        log_path = project_path(config["paths"]["weather_anomaly_log"])
        log = read_json(log_path, default={})
        log[today_str()] = all_anomalies
        write_json(log_path, log)

    print(json.dumps({"date": today_str(), "anomalies": all_anomalies}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
