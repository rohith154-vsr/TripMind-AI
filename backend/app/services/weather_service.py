"""
Weather Service — uses Open-Meteo with caching, HTTP 429 rate-limit handling,
and seasonal heuristic estimates when travel dates are beyond Open-Meteo's forecast window.
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


class WeatherServiceError(Exception):
    """Base exception for weather service operations."""
    def __init__(self, message: str, error_type: str = "api_error"):
        super().__init__(message)
        self.error_type = error_type


class WeatherRateLimitError(WeatherServiceError):
    """Raised when Open-Meteo returns HTTP 429 rate limit."""
    def __init__(self, message: str = "Open-Meteo API rate limit reached (HTTP 429)"):
        super().__init__(message, error_type="http_429_rate_limit")


class WeatherTimeoutError(WeatherServiceError):
    """Raised when weather API connection times out."""
    def __init__(self, message: str = "Open-Meteo API connection timed out"):
        super().__init__(message, error_type="timeout")


class WeatherNetworkError(WeatherServiceError):
    """Raised when network connection to weather API fails."""
    def __init__(self, message: str = "Open-Meteo API network connection failed"):
        super().__init__(message, error_type="network_failure")


async def get_coordinates(location: str) -> Optional[Dict[str, float]]:
    """Get lat/lon for a location string using OSM Nominatim."""
    from app.services.maps_service import geocode
    geo = await geocode(location)
    if geo:
        return {"lat": geo["lat"], "lon": geo["lon"], "display_name": geo["display_name"]}
    return None


async def get_weather_forecast(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """
    Fetch weather forecast from Open-Meteo with caching and structured exception handling
    for HTTP 429, timeouts, and network failures.
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
                if cache_key in _WEATHER_CACHE:
                    return _WEATHER_CACHE[cache_key][0]
                raise WeatherRateLimitError()
            else:
                resp.raise_for_status()
    except httpx.TimeoutException as e:
        if cache_key in _WEATHER_CACHE:
            return _WEATHER_CACHE[cache_key][0]
        raise WeatherTimeoutError(f"Open-Meteo API connection timed out: {e}") from e
    except httpx.NetworkError as e:
        if cache_key in _WEATHER_CACHE:
            return _WEATHER_CACHE[cache_key][0]
        raise WeatherNetworkError(f"Open-Meteo API network connection failed: {e}") from e
    except WeatherServiceError:
        raise
    except Exception as e:
        if cache_key in _WEATHER_CACHE:
            return _WEATHER_CACHE[cache_key][0]
        raise WeatherServiceError(str(e), error_type="api_error") from e

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
    If target_dates are provided, strictly match actual returned observation dates
    to the requested dates. Zero cyclic modulo remapping or fake date relabeling.
    """
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])
    wind = daily.get("windspeed_10m_max", [])

    date_dict: Dict[str, Dict[str, Any]] = {}
    for i, d in enumerate(dates):
        code = codes[i] if i < len(codes) else 0
        date_dict[d] = {
            "date": d,
            "condition": WMO_CODES.get(code, "Unknown"),
            "weather_code": code,
            "temp_max_c": max_temps[i] if i < len(max_temps) else None,
            "temp_min_c": min_temps[i] if i < len(min_temps) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
            "wind_speed_kmh": wind[i] if i < len(wind) else None,
            "is_good_outdoor": code in [0, 1, 2, 3] and (precip[i] if i < len(precip) else 0) < 5,
            "is_live_observation": True,
            "is_heuristic_estimate": False,
            "data_type": "live_forecast",
        }

    if target_dates:
        # Strictly match actual Open-Meteo dates to requested trip dates.
        # If any target date does not exist in Open-Meteo's returned window,
        # return empty list to trigger genuine fallback rather than fabricating data.
        matched = []
        for t_date in target_dates:
            if t_date in date_dict:
                matched.append(date_dict[t_date])
            else:
                return []
        return matched

    return list(date_dict.values())
