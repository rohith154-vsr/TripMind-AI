"""
Tests for Ooty Destination Intelligence, Budget Consistency, Weather Dates,
and System Quality Improvements.
"""
import pytest
from datetime import datetime, timezone
from app.services.knowledge_base import classify_destination, DESTINATION_KNOWLEDGE
from app.services.fallback_generator import generate_fallback_for_prompt
from app.models.trip import _format_dt
from app.agents import (
    destination_agent,
    weather_agent,
    budget_agent,
    itinerary_agent,
    coordinator,
)


def test_ooty_destination_classification():
    """Verify Ooty is classified as a Nilgiri hill station with verified landmarks and no European templates."""
    info = classify_destination("Ooty")
    assert info["is_curated"] is True
    assert info["is_hill_station"] is True
    assert info["country"] == "India"
    assert "Tamil Nadu" in info["region"]

    data = info["data"]
    attraction_names = [a["name"] for a in data["top_attractions"]]
    assert "Government Botanical Garden" in attraction_names
    assert "Nilgiri Mountain Railway (Toy Train)" in attraction_names
    assert "Doddabetta Peak" in attraction_names
    assert "Ooty Lake & Boat House" in attraction_names

    # Verify foods
    foods_str = " ".join(data["must_try_foods"])
    assert "Nilgiri" in foods_str
    assert "Varkey" in foods_str
    assert "Chocolates" in foods_str

    # Verify transit doesn't mention metro/trams
    getting_around = data["getting_around"].lower()
    assert "metro" not in getting_around
    assert "tram" not in getting_around
    assert "subway" not in getting_around
    assert "taxis" in getting_around or "auto-rickshaws" in getting_around


@pytest.mark.asyncio
async def test_ooty_destination_agent_fallback():
    """Verify destination agent generates authentic Nilgiris data when fallback is used."""
    prompt = """Research the travel destination for a trip with these preferences:
Destination: Ooty
Origin: Bangalore
Travel Style: Adventure and food
Interests: Sightseeing, Nature, Food
Number of Travelers: 2
Travel Dates: 2026-11-19 to 2026-11-22
"""
    result = generate_fallback_for_prompt(prompt, "Destination Research Agent")
    assert result is not None
    overview = result.get("destination_overview", {})
    assert overview.get("country") == "India"
    assert "Tamil Nadu" in overview.get("region", "")
    assert "2,240" in overview.get("description", "") or "hill" in overview.get("description", "").lower()

    # Verify no fake European metropolitan landmarks
    result_str = str(result)
    assert "Historic Center & Landmark Plaza" not in result_str
    assert "Grand Waterfront Promenade" not in result_str
    assert "Panoramic Sky Observation Deck" not in result_str
    assert "National Museum of Art & History" not in result_str


@pytest.mark.asyncio
async def test_ooty_budget_currency_and_math():
    """Verify budget agent handles INR 15,000 for 4 days (2026-11-19 to 2026-11-22) with exact math."""
    prefs = {
        "origin": "Bangalore",
        "destination": "Ooty",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-22",
        "num_travelers": 2,
        "budget": 15000.0,
        "currency": "INR",
        "travel_style": "Adventure and food",
        "interests": ["Sightseeing", "Nature", "Food"],
    }
    result = await budget_agent.run(prefs)
    assert result is not None
    summary = result.get("budget_summary", {})

    # Currency verification: strictly INR, no USD
    assert summary.get("currency") == "INR"
    assert summary.get("total_budget") == 15000.0

    # Mathematical consistency:
    # 4 days inclusive (Nov 19, 20, 21, 22): 15,000 / 4 = 3,750 INR/day
    assert summary.get("budget_per_day") == 3750.0

    # 2 travelers: 15,000 / 2 = 7,500 INR/person
    assert summary.get("budget_per_person") == 7500.0

    # 15,000 / (2 * 4) = 1,875 INR/person/day
    assert summary.get("budget_per_person_per_day") == 1875.0

    # Verify no USD '$' in notes
    result_str = str(result)
    assert "$3750" not in result_str
    assert "$15000" not in result_str


@pytest.mark.asyncio
async def test_ooty_weather_dates_and_provenance():
    """Verify weather forecast dates strictly match requested trip dates (2026-11-19 to 2026-11-22)."""
    prefs = {
        "destination": "Ooty",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-22",
        "travel_style": "Adventure and food",
        "interests": ["Sightseeing", "Nature", "Food"],
    }
    result = await weather_agent.run(prefs)
    assert result is not None

    forecast = result.get("daily_forecast", [])
    assert len(forecast) == 4

    forecast_dates = [d["date"] for d in forecast]
    expected_dates = ["2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"]
    assert forecast_dates == expected_dates

    # Ensure current dates did NOT leak into the forecast
    current_year = datetime.now().strftime("%Y-%m")
    if current_year != "2026-11":
        for d in forecast_dates:
            assert not d.startswith(current_year), f"Current date {d} leaked into 2026 forecast!"

    # Verify transparent provenance
    meta = result.get("metadata", {})
    assert meta.get("source_type") in ("historical_estimate", "fallback", "live_api")
    data_source_str = " ".join(meta.get("data_sources", []))
    assert "Historical" in data_source_str or "Open-Meteo" in data_source_str


@pytest.mark.asyncio
async def test_ooty_itinerary_consistency():
    """Verify itinerary agent generates 4 days with correct dates, daily budget, and Nilgiri activities."""
    prefs = {
        "origin": "Bangalore",
        "destination": "Ooty",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-22",
        "num_travelers": 2,
        "budget": 15000.0,
        "currency": "INR",
        "travel_style": "Adventure and food",
        "interests": ["Sightseeing", "Nature", "Food"],
    }
    result = await itinerary_agent.run(prefs, {})
    assert result is not None
    days = result.get("days", [])
    assert len(days) == 4

    dates = [d["date"] for d in days]
    assert dates == ["2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"]

    for d in days:
        assert d.get("daily_budget_estimate") == 3750.0

    # Ensure no metro/tram or European waterfront references
    result_str = str(result)
    assert "Grand Waterfront" not in result_str
    assert "tram" not in result_str.lower()
    assert "metro" not in result_str.lower()


def test_timestamp_serialization():
    """Verify datetime serialization produces valid ISO 8601 UTC strings ending with Z."""
    now = datetime(2026, 11, 4, 12, 30, 45, tzinfo=timezone.utc)
    s = _format_dt(now)
    assert s == "2026-11-04T12:30:45Z"
    assert s.endswith("Z")

    naive = datetime(2026, 11, 4, 12, 30, 45)
    s_naive = _format_dt(naive)
    assert s_naive == "2026-11-04T12:30:45Z"

    # Verify string already formatted
    assert _format_dt("2026-11-04T12:30:45+00:00") == "2026-11-04T12:30:45Z"
    assert _format_dt(None) is None


def test_coordinator_fallback_completion_count():
    """Verify coordinator reports 6 of 6 agents successful in data_quality."""
    prompt = 'Synthesize travel plan for "destination": "Ooty"'
    result = generate_fallback_for_prompt(prompt, "Travel Coordinator Agent")
    assert result is not None
    dq = result.get("data_quality", {})
    assert dq.get("agents_successful") == 6
    assert dq.get("agents_failed") == 0
