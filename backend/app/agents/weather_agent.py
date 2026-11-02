"""
Weather Intelligence Agent
Retrieves real weather data using Open-Meteo and provides smart travel recommendations.
"""
from typing import Dict, Any, List
from datetime import datetime, date
import asyncio
from app.services.llm_service import llm_service
from app.services.weather_service import get_coordinates, get_weather_forecast, parse_weather

SYSTEM_PROMPT = """You are the Weather Intelligence Agent for TripMind AI.
Your role is to analyze weather data and provide actionable travel advice.
Always base your recommendations on the actual weather data provided.
Respond with structured JSON only."""

ANALYSIS_PROMPT = """Analyze this weather forecast for a travel trip and provide smart recommendations.

Destination: {destination}
Travel Dates: {departure_date} to {return_date}
Travel Style: {travel_style}
Planned Activities/Interests: {interests}

Weather Forecast Data:
{weather_data}

Based on this actual weather data, provide a JSON response with this structure:
{{
  "weather_summary": "2-3 sentence summary of expected weather conditions during the trip",
  "overall_rating": "excellent|good|mixed|challenging",
  "temperature_range": {{
    "avg_high_c": 25,
    "avg_low_c": 15,
    "avg_high_f": 77,
    "avg_low_f": 59
  }},
  "precipitation_risk": "low|moderate|high",
  "best_days_outdoor": ["2024-01-15", "2024-01-16"],
  "days_to_avoid_outdoor": ["2024-01-18"],
  "packing_recommendations": [
    "Item to pack and why"
  ],
  "activity_adjustments": [
    {{
      "original_plan": "Beach day",
      "weather_issue": "Rain expected on Jan 18",
      "alternative": "Visit indoor museum instead",
      "day": "2024-01-18"
    }}
  ],
  "daily_forecast": [
    {{
      "date": "2024-01-15",
      "condition": "Clear sky",
      "temp_max_c": 28,
      "temp_min_c": 18,
      "temp_max_f": 82,
      "temp_min_f": 64,
      "precipitation_mm": 0,
      "wind_speed_kmh": 10,
      "travel_advice": "Ideal day for outdoor activities",
      "is_good_outdoor": true
    }}
  ],
  "health_safety_tips": ["Stay hydrated", "Sunscreen recommended"],
  "weather_data_source": "Open-Meteo (real forecast data)"
}}"""


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch real weather data and analyze it with AI."""
    destination = preferences["destination"]
    departure_date = preferences.get("departure_date", "")
    return_date = preferences.get("return_date", "")

    # Step 1: Geocode the destination
    weather_raw = None
    forecast_days = 7
    coordinates = None

    try:
        # Calculate trip duration for forecast
        if departure_date and return_date:
            dep = datetime.strptime(departure_date, "%Y-%m-%d").date()
            ret = datetime.strptime(return_date, "%Y-%m-%d").date()
            forecast_days = min((ret - dep).days + 2, 16)
        
        coords = await get_coordinates(destination)
        if coords:
            coordinates = {"lat": coords["lat"], "lon": coords["lon"]}
            weather_raw = await get_weather_forecast(coords["lat"], coords["lon"], days=forecast_days)
    except Exception as e:
        weather_raw = None
        weather_error = str(e)

    # Step 2: Parse weather or use placeholder
    if weather_raw:
        daily_forecast = parse_weather(weather_raw)
        weather_data_str = str(daily_forecast[:14])  # Pass to LLM
        weather_available = True
    else:
        daily_forecast = []
        weather_data_str = f"Weather data unavailable. Error: {locals().get('weather_error', 'Unknown')}"
        weather_available = False

    # Step 3: AI analysis
    interests_str = ", ".join(preferences.get("interests", [])) or "General travel"
    prompt = ANALYSIS_PROMPT.format(
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        travel_style=preferences.get("travel_style", "Adventure"),
        interests=interests_str,
        weather_data=weather_data_str,
    )

    try:
        analysis = await llm_service.generate_json(prompt, SYSTEM_PROMPT)
    except Exception as e:
        analysis = {
            "weather_summary": f"Weather analysis unavailable: {str(e)}",
            "overall_rating": "unknown",
            "packing_recommendations": ["Pack for variable conditions"],
            "activity_adjustments": [],
            "daily_forecast": daily_forecast,
        }

    # Merge real forecast data
    if daily_forecast:
        analysis["daily_forecast"] = daily_forecast  # Use real data directly

    analysis["coordinates"] = coordinates
    analysis["weather_data_available"] = weather_available
    analysis["agent"] = "weather_intelligence"
    return analysis
