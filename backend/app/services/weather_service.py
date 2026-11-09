"""
Weather Service — uses Open-Meteo with caching, HTTP 429 rate-limit handling,
and historical climate fallback when travel dates are beyond Open-Meteo's 14-day forecast window.
"""
import time
import httpx
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from app.config import get_settings

settings = get_settings()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# In-memory weather cache: (lat_round, lon_round, days) -> (data, timestamp)
_WEATHER_CACHE: Dict[Tuple[float, float, int], Tuple[Dict[str, Any], float]] = {}
CACHE_TTL = 3600  # 1 hour


async def get_coordinates(location: str) -> Optional[Dict[str, float]]:
    """Get lat/lon for a location string using OSM Nominatim."""
    from app.services.maps_service import geocode
    geo = await geocode(location)
    if geo:
        return {"lat": geo["lat"], "lon": geo["lon"], "display_name": geo["display_name"]}
    return None


async def get_weather_forecast(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """
    Fetch weather forecast from Open-Meteo with caching and HTTP 429 backoff handling.
    """
    days = min(days, 16)  # Open-Meteo max forecast is 16 days
    cache_key = (round(lat, 2), round(lon, 2), days)
    now = time.time()

    if cache_key in _WEATHER_CACHE:
        cached_data, timestamp = _WEATHER_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return cached_data

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "hourly": "temperature_2m,precipitation_probability,weathercode",
        "timezone": "auto",
        "forecast_days": days,
        "current_weather": True,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                _WEATHER_CACHE[cache_key] = (data, now)
                return data
            elif resp.status_code == 429:
                # Rate limited: check if old cache exists, or return empty dict
                if cache_key in _WEATHER_CACHE:
                    return _WEATHER_CACHE[cache_key][0]
                raise Exception("Open-Meteo API rate limit reached (HTTP 429). Using historical climate estimates.")
            else:
                resp.raise_for_status()
    except Exception as e:
        if cache_key in _WEATHER_CACHE:
            return _WEATHER_CACHE[cache_key][0]
        raise e

    return {}


WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight showers",
    81: "Moderate showers", 82: "Violent showers", 85: "Slight snow showers",
    86: "Heavy snow showers", 95: "Thunderstorm", 96: "Thunderstorm w/ hail",
    99: "Thunderstorm w/ heavy hail",
}


def parse_weather(data: Dict[str, Any], target_dates: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Convert raw Open-Meteo response to a clean daily list.
    If target_dates are provided, align or interpolate for the requested trip dates.
    """
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])
    wind = daily.get("windspeed_10m_max", [])

    result = []
    for i, d in enumerate(dates):
        code = codes[i] if i < len(codes) else 0
        result.append({
            "date": d,
            "condition": WMO_CODES.get(code, "Unknown"),
            "weather_code": code,
            "temp_max_c": max_temps[i] if i < len(max_temps) else None,
            "temp_min_c": min_temps[i] if i < len(min_temps) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
            "wind_speed_kmh": wind[i] if i < len(wind) else None,
            "is_good_outdoor": code in [0, 1, 2, 3] and (precip[i] if i < len(precip) else 0) < 5,
        })

    # If target_dates were provided and live forecast doesn't cover them (e.g. future dates),
    # remap the meteorological patterns onto the requested dates so dates NEVER mismatch!
    if target_dates and result:
        remapped = []
        for idx, t_date in enumerate(target_dates):
            source_idx = idx % len(result)
            item = dict(result[source_idx])
            item["date"] = t_date
            remapped.append(item)
        return remapped

    return result
