"""
Phase 2 Data Integrity & Accounting Regression Tests:
1. Zero synthetic coordinates in Maps Service & Local Discovery
2. Admission fee currency semantics (INR, USD, EUR)
3. Weather date alignment without cyclic modulo remapping
4. Budget accounting: inclusive travel days vs accommodation nights, emergency reserve included in 100%
5. Truthful agent runtime provenance reporting
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.services.maps_service import find_pois
from app.services.knowledge_base import DESTINATION_KNOWLEDGE, classify_destination
from app.services.weather_service import parse_weather
from app.agents import (
    destination_agent,
    weather_agent,
    budget_agent,
    local_discovery_agent,
    itinerary_agent,
    coordinator,
)


@pytest.mark.asyncio
async def test_zero_synthetic_coordinates_when_osm_empty():
    """Verify find_pois never generates fake coordinate offsets or synthetic OSM flags when Overpass/Nominatim are empty."""
    with patch("app.services.maps_service.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        # Mock empty response from both Overpass and Nominatim
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": []}
        mock_instance.post.return_value = mock_resp
        mock_instance.get.return_value = mock_resp
        mock_client.return_value = mock_instance

        # Query for Ooty with random coordinates
        pois = await find_pois(11.4135, 76.7032, destination_name="Ooty")
        # Must strictly return empty list, NEVER append +0.004 synthetic offsets!
        assert pois == []


@pytest.mark.asyncio
async def test_local_discovery_preserves_zero_synthetic_pois():
    """Verify Local Discovery Agent leaves featured_restaurants and top_attractions empty if no real OSM POIs exist."""
    with patch("app.agents.local_discovery_agent.find_pois", new_callable=AsyncMock) as mock_find_pois, \
         patch("app.agents.local_discovery_agent.geocode", new_callable=AsyncMock) as mock_geocode:

        mock_geocode.return_value = {"lat": 11.4135, "lon": 76.7032, "display_name": "Ooty, Tamil Nadu, India"}
        mock_find_pois.return_value = []

        prefs = {
            "origin": "Bangalore",
            "destination": "Ooty",
            "travel_style": "Adventure and food",
            "interests": ["Sightseeing", "Food"],
            "budget": 15000,
            "currency": "INR",
        }
        result = await local_discovery_agent.run(prefs)

        assert result["featured_restaurants"] == []
        assert result["top_attractions"] == []
        assert result["raw_osm_pois"] == []
        assert result["is_live_data"] is False
        assert result["metadata"]["is_fallback"] is True
        assert result["metadata"]["source_type"] == "curated_knowledge"
        # Must not claim Gemini if unconfigured/fallback
        data_sources = result["metadata"]["data_sources"]
        assert "OpenStreetMap / Overpass API" not in data_sources or "Fallback" in str(data_sources)


def test_admission_fee_currency_semantics_in_knowledge_base():
    """Verify curated attractions specify native currency, admission fee, and USD equivalent."""
    ooty_attrs = DESTINATION_KNOWLEDGE["ooty"]["top_attractions"]
    assert len(ooty_attrs) >= 6

    for attr in ooty_attrs:
        assert "admission_fee" in attr
        assert "admission_fee_currency" in attr
        assert attr["admission_fee_currency"] == "INR"
        assert "admission_fee_usd" in attr
        assert isinstance(attr["admission_fee"], (int, float))
        assert isinstance(attr["admission_fee_usd"], (int, float))

    # Verify Botanical Garden has real Indian Rupee fee
    botanical = next(a for a in ooty_attrs if "Botanical" in a["name"])
    assert botanical["admission_fee"] == 50
    assert botanical["admission_fee_currency"] == "INR"
    assert botanical["admission_fee_usd"] == 1


def test_weather_parse_no_cyclic_modulo_remapping():
    """Verify parse_weather strictly matches dates and returns [] when Open-Meteo dates do not cover trip dates."""
    # Mock Open-Meteo daily response for March 2025
    mock_data = {
        "daily": {
            "time": ["2025-03-01", "2025-03-02", "2025-03-03"],
            "temperature_2m_max": [25.0, 26.0, 24.5],
            "temperature_2m_min": [15.0, 16.0, 14.0],
            "precipitation_sum": [0.0, 2.0, 0.0],
            "weathercode": [0, 1, 2],
            "windspeed_10m_max": [10.0, 12.0, 8.0],
        }
    }

    # Request for Nov 2026 dates (completely disjoint)
    future_dates = ["2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"]
    res = parse_weather(mock_data, target_dates=future_dates)
    # Must NOT cyclically remap March 2025 data to Nov 2026! Must return empty list
    assert res == []

    # Request for matching dates
    matching_dates = ["2025-03-01", "2025-03-02"]
    res_matched = parse_weather(mock_data, target_dates=matching_dates)
    assert len(res_matched) == 2
    assert res_matched[0]["date"] == "2025-03-01"
    assert res_matched[1]["date"] == "2025-03-02"


@pytest.mark.asyncio
async def test_weather_agent_future_trip_uses_historical_estimates():
    """Verify weather agent for dates > 16 days ahead uses historical estimates without calling Open-Meteo."""
    today = date.today()
    future_dep = (today + timedelta(days=45)).strftime("%Y-%m-%d")
    future_ret = (today + timedelta(days=48)).strftime("%Y-%m-%d")

    prefs = {
        "destination": "Ooty",
        "departure_date": future_dep,
        "return_date": future_ret,
        "travel_style": "Adventure",
        "interests": ["Nature"],
    }
    result = await weather_agent.run(prefs)
    assert result is not None
    assert result["weather_data_available"] is False

    meta = result["metadata"]
    assert meta["source_type"] in ("heuristic_seasonal_estimate", "historical_estimate")
    assert meta["is_fallback"] is True
    assert "Open-Meteo Meteorological API (Live Forecast)" not in meta["data_sources"]

    # Dates must strictly match future_dep through future_ret
    forecast = result["daily_forecast"]
    assert len(forecast) == 4
    expected_dates = [(today + timedelta(days=45 + i)).strftime("%Y-%m-%d") for i in range(4)]
    assert [d["date"] for d in forecast] == expected_dates
    for d in forecast:
        assert d.get("is_historical_estimate") is True
        assert d.get("is_live_observation") is False


@pytest.mark.asyncio
async def test_budget_accounting_4_day_trip():
    """Verify 4-day trip: 4 inclusive travel days, 3 accommodation nights, emergency reserve included in total."""
    prefs = {
        "origin": "Bangalore",
        "destination": "Ooty",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-22",
        "num_travelers": 2,
        "budget": 15000.0,
        "currency": "INR",
        "travel_style": "Adventure",
        "interests": ["Sightseeing"],
    }
    result = await budget_agent.run(prefs)
    assert result is not None

    summary = result["budget_summary"]
    assert summary["total_budget"] == 15000.0
    assert summary["budget_per_day"] == 3750.0       # 15,000 / 4
    assert summary["budget_per_person"] == 7500.0    # 15,000 / 2
    assert summary["budget_per_person_per_day"] == 1875.0  # 15,000 / (2 * 4)

    eb = result["expense_breakdown"]
    # 4 travel days = 3 accommodation nights
    assert eb["accommodation"]["nights"] == 3
    hotel_total = eb["accommodation"]["estimated_total"]
    assert hotel_total == 5700.0                     # 38% of 15,000
    assert eb["accommodation"]["per_night"] == 1900.0  # 5,700 / 3 nights

    # Emergency buffer is included inside total
    assert eb["emergency_buffer"]["recommended_amount"] == 1500.0  # 10% of 15,000
    assert eb["emergency_buffer"]["is_included_in_total"] is True

    # Sum of categories must equal EXACTLY 15,000 (100% of total budget)
    breakdown_sum = round(
        eb["accommodation"]["estimated_total"] +
        eb["food"]["estimated_total"] +
        eb["local_transport"]["estimated_total"] +
        eb["activities_attractions"]["estimated_total"] +
        eb["shopping_souvenirs"]["estimated_total"] +
        eb["emergency_buffer"]["recommended_amount"],
        2
    )
    assert breakdown_sum == 15000.0
    assert result["total_estimated_cost"] == 15000.0
    assert result["budget_vs_estimate"]["difference"] == 0.0


@pytest.mark.asyncio
async def test_budget_accounting_single_day_trip():
    """Verify single-day trip: 1 travel day, 0 accommodation nights, 0 hotel cost."""
    prefs = {
        "origin": "Bangalore",
        "destination": "Mysore",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-19",
        "num_travelers": 1,
        "budget": 5000.0,
        "currency": "INR",
        "travel_style": "Cultural",
        "interests": ["Palaces"],
    }
    result = await budget_agent.run(prefs)
    assert result is not None

    summary = result["budget_summary"]
    assert summary["total_budget"] == 5000.0
    assert summary["budget_per_day"] == 5000.0
    assert summary["budget_per_person"] == 5000.0

    eb = result["expense_breakdown"]
    assert eb["accommodation"]["nights"] == 0
    assert eb["accommodation"]["estimated_total"] == 0.0
    assert eb["accommodation"]["per_night"] == 0.0

    # Total must equal 5,000 exactly
    breakdown_sum = round(
        eb["accommodation"]["estimated_total"] +
        eb["food"]["estimated_total"] +
        eb["local_transport"]["estimated_total"] +
        eb["activities_attractions"]["estimated_total"] +
        eb["shopping_souvenirs"]["estimated_total"] +
        eb["emergency_buffer"]["recommended_amount"],
        2
    )
    assert breakdown_sum == 5000.0
    assert result["total_estimated_cost"] == 5000.0


@pytest.mark.asyncio
async def test_budget_accounting_2_day_trip():
    """Verify 2-day trip: 2 travel days, 1 accommodation night."""
    prefs = {
        "origin": "Bangalore",
        "destination": "Coorg",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-20",
        "num_travelers": 2,
        "budget": 10000.0,
        "currency": "INR",
        "travel_style": "Nature",
        "interests": ["Coffee plantations"],
    }
    result = await budget_agent.run(prefs)
    assert result is not None

    summary = result["budget_summary"]
    assert summary["budget_per_day"] == 5000.0

    eb = result["expense_breakdown"]
    assert eb["accommodation"]["nights"] == 1
    assert eb["accommodation"]["per_night"] == eb["accommodation"]["estimated_total"]

    breakdown_sum = round(
        eb["accommodation"]["estimated_total"] +
        eb["food"]["estimated_total"] +
        eb["local_transport"]["estimated_total"] +
        eb["activities_attractions"]["estimated_total"] +
        eb["shopping_souvenirs"]["estimated_total"] +
        eb["emergency_buffer"]["recommended_amount"],
        2
    )
    assert breakdown_sum == 10000.0
    assert result["total_estimated_cost"] == 10000.0


@pytest.mark.asyncio
async def test_truthful_provenance_across_agents():
    """Verify agents truthfully report fallback source types and do not claim uncalled live APIs."""
    prefs = {
        "origin": "Bangalore",
        "destination": "Ooty",
        "departure_date": "2026-11-19",
        "return_date": "2026-11-22",
        "num_travelers": 2,
        "budget": 15000.0,
        "currency": "USD",  # When currency is USD, Frankfurter is not called
        "travel_style": "Adventure",
        "interests": ["Sightseeing"],
    }

    # Budget with USD
    b_res = await budget_agent.run(prefs)
    b_meta = b_res["metadata"]
    # When currency is USD, Frankfurter is NOT needed
    assert "Frankfurter Currency Exchange API" not in " ".join(b_meta["data_sources"])
    assert "USD" in " ".join(b_meta["data_sources"])

    # Destination agent fallback
    d_res = await destination_agent.run(prefs)
    d_meta = d_res["metadata"]
    assert d_meta["source_type"] in ("curated_knowledge", "fallback", "llm")
    if d_meta["is_fallback"]:
        assert "Curated Regional Travel" in " ".join(d_meta["data_sources"])
