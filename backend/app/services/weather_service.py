"""
Weather Service — uses Open-Meteo (free, no API key required).
"""
import httpx
from typing import Dict, Any, Optional, List
from app.config import get_settings

settings = get_settings()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


async def get_coordinates(location: str) -> Optional[Dict[str, float]]:
    """Get lat/lon for a location string using OSM Nominatim."""
    params = {
        "q": location,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "TripMind-AI/1.0 (portfolio project)"}
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers=headers)
        resp.raise_for_status()
        results = resp.json()
        if results:
            return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"]), "display_name": results[0]["display_name"]}
    return None


async def get_weather_forecast(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """Fetch weather forecast from Open-Meteo."""
    days = min(days, 16)  # Open-Meteo max forecast is 16 days
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "hourly": "temperature_2m,precipitation_probability,weathercode",
        "timezone": "auto",
        "forecast_days": days,
        "current_weather": True,
    }
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        return resp.json()


WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight showers",
    81: "Moderate showers", 82: "Violent showers", 85: "Slight snow showers",
    86: "Heavy snow showers", 95: "Thunderstorm", 96: "Thunderstorm w/ hail",
    99: "Thunderstorm w/ heavy hail",
}


def parse_weather(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert raw Open-Meteo response to a clean daily list."""
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
    return result
