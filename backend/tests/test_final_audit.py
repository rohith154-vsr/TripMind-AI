"""
Final Targeted Audit Automated Tests
Validates:
1. Strict OSM establishment verification (rejecting hallucinated venues with valid coordinates).
2. Weather LLM provenance separation and accurate heuristic terminology.
3. Weather error classification (HTTP 429, timeout, network failure).
4. Currency pair isolation and original currency preservation (INR, USD, EUR, GBP).
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import date, timedelta

from app.agents import local_discovery_agent, weather_agent
from app.services import weather_service, currency_service
from app.services.weather_service import (
    WeatherRateLimitError,
    WeatherTimeoutError,
    WeatherNetworkError,
)
from app.services.currency_service import (
    convert_amount,
    get_exchange_rate_with_metadata,
)


@pytest.mark.asyncio
async def test_osm_hallucination_with_valid_coordinates_is_rejected():
    """
    Verify that an LLM-suggested establishment with valid non-zero coordinates
    is strictly rejected if its name does not match any genuine OSM POI record,
    and never marked is_verified_osm=True.
    """
    mock_pois = [
        {
            "name": "Nahata Sweets",
            "lat": 11.4102,
            "lon": 76.6950,
            "category": "food",
            "type": "restaurant",
            "cuisine": "Indian Sweets",
            "is_verified_osm": True,
        },
        {
            "name": "Botanical Garden Viewpoint",
            "lat": 11.4150,
            "lon": 76.7050,
            "category": "attraction",
            "type": "tourism",
            "is_verified_osm": True,
        }
    ]

    # LLM hallucinates one fake venue with plausible coordinates,
    # one venue with matching name but fake far-away coordinates,
    # and includes one authentic venue.
    mock_llm_response = {
        "featured_restaurants": [
            {
                "name": "Nahata Sweets",
                "cuisine": "Regional Sweets",
                "lat": 11.4102,
                "lon": 76.6950,
                "price_range": "$",
                "best_for": "snacks",
            },
            {
                "name": "Grand European Palace Bistro",  # Hallucinated name with plausible coords!
                "cuisine": "French",
                "lat": 11.4108,
                "lon": 76.6954,
                "price_range": "$$$$",
                "best_for": "dinner",
            },
            {
                "name": "Nahata Sweets",  # Matching name but coordinates in New York!
                "cuisine": "Sweets",
                "lat": 40.7128,
                "lon": -74.0060,
                "price_range": "$",
                "best_for": "snacks",
            }
        ],
        "top_attractions": [
            {
                "name": "Botanical Garden Viewpoint",
                "type": "viewpoint",
                "lat": 11.4150,
                "lon": 76.7050,
            },
            {
                "name": "Fictional Eiffel Tower Ooty",  # Hallucinated attraction
                "type": "tower",
                "lat": 11.4152,
                "lon": 76.7052,
            }
        ],
        "general_dining_suggestions": ["Sample local tea and bakery specialties"],
        "general_activity_suggestions": ["Walk through scenic tea estates"],
        "neighborhood_guides": [],
        "local_tips": ["Wear comfortable shoes"],
    }

    with patch("app.agents.local_discovery_agent.find_pois", new_callable=AsyncMock) as mock_find, \
         patch("app.agents.local_discovery_agent.geocode", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.local_discovery_agent.llm_service.generate_json_with_provenance", new_callable=AsyncMock) as mock_llm:

        mock_geo.return_value = {"lat": 11.4135, "lon": 76.7032, "display_name": "Ooty, Tamil Nadu"}
        mock_find.return_value = mock_pois
        mock_llm.return_value = (mock_llm_response, {"provider_used": "gemini", "is_fallback": False, "model": "gemini-2.5-flash-lite", "error": None})

        prefs = {
            "origin": "Bangalore",
            "destination": "Ooty",
            "travel_style": "Adventure",
            "interests": ["Sightseeing", "Food"],
            "budget": 15000,
            "currency": "INR",
        }

        result = await local_discovery_agent.run(prefs)

        restaurant_names = [r["name"] for r in result["featured_restaurants"]]
        attraction_names = [a["name"] for a in result["top_attractions"]]

        # Hallucinated venues must be REJECTED
        assert "Grand European Palace Bistro" not in restaurant_names
        assert "Fictional Eiffel Tower Ooty" not in attraction_names

        # Authentic venue must be preserved and verified
        assert "Nahata Sweets" in restaurant_names
        assert "Botanical Garden Viewpoint" in attraction_names

        # All returned establishments must be verified against genuine OSM records
        for r in result["featured_restaurants"]:
            assert r.get("is_verified_osm") is True
            assert abs(r["lat"] - 11.4102) < 0.005
        for a in result["top_attractions"]:
            assert a.get("is_verified_osm") is True
            assert abs(a["lat"] - 11.4150) < 0.005


@pytest.mark.asyncio
async def test_weather_agent_provenance_separation_and_terminology():
    """
    Verify Weather Agent separates weather data provenance from LLM provenance in metadata,
    and uses accurate heuristic estimate terminology (no false historical claims).
    """
    today = date.today()
    future_dep = (today + timedelta(days=40)).strftime("%Y-%m-%d")
    future_ret = (today + timedelta(days=43)).strftime("%Y-%m-%d")

    prefs = {
        "destination": "Ooty",
        "departure_date": future_dep,
        "return_date": future_ret,
        "travel_style": "Nature",
        "interests": ["Sightseeing"],
    }

    result = await weather_agent.run(prefs)
    assert result is not None
    assert "metadata" in result

    meta = result["metadata"]
    assert "weather_provenance" in meta
    assert "llm_provenance" in meta

    wp = meta["weather_provenance"]
    assert wp["source_type"] == "heuristic_seasonal_estimate"
    assert wp["is_live"] is False
    assert wp["is_heuristic"] is True
    assert "historical" not in wp["source_type"].lower()

    # Verify daily forecast items use correct terminology
    forecast = result["daily_forecast"]
    assert len(forecast) == 4
    for day in forecast:
        assert day["is_live_observation"] is False
        assert day["is_heuristic_estimate"] is True
        assert day["data_type"] == "heuristic_seasonal_estimate"

    # Verify LLM provenance is populated
    lp = meta["llm_provenance"]
    assert "provider_used" in lp
    assert "is_fallback" in lp


@pytest.mark.asyncio
async def test_weather_error_classification():
    """
    Verify Weather Agent accurately classifies HTTP 429, timeouts, and network failures.
    """
    today = date.today()
    live_dep = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    live_ret = (today + timedelta(days=4)).strftime("%Y-%m-%d")

    prefs = {
        "destination": "Bangalore",
        "departure_date": live_dep,
        "return_date": live_ret,
    }

    # Test HTTP 429
    with patch("app.agents.weather_agent.get_coordinates", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.weather_agent.get_weather_forecast", new_callable=AsyncMock) as mock_wf:
        mock_geo.return_value = {"lat": 12.9716, "lon": 77.5946}
        mock_wf.side_effect = WeatherRateLimitError()

        res_429 = await weather_agent.run(prefs)
        wp_429 = res_429["metadata"]["weather_provenance"]
        assert wp_429["error_classification"] == "http_429_rate_limit"

    # Test Timeout
    with patch("app.agents.weather_agent.get_coordinates", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.weather_agent.get_weather_forecast", new_callable=AsyncMock) as mock_wf:
        mock_geo.return_value = {"lat": 12.9716, "lon": 77.5946}
        mock_wf.side_effect = WeatherTimeoutError()

        res_timeout = await weather_agent.run(prefs)
        wp_timeout = res_timeout["metadata"]["weather_provenance"]
        assert wp_timeout["error_classification"] == "timeout"

    # Test Network failure
    with patch("app.agents.weather_agent.get_coordinates", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.weather_agent.get_weather_forecast", new_callable=AsyncMock) as mock_wf:
        mock_geo.return_value = {"lat": 12.9716, "lon": 77.5946}
        mock_wf.side_effect = WeatherNetworkError()

        res_net = await weather_agent.run(prefs)
        wp_net = res_net["metadata"]["weather_provenance"]
        assert wp_net["error_classification"] == "network_failure"


@pytest.mark.asyncio
async def test_currency_conversion_pair_isolation_and_preservation():
    """
    Verify currency conversion rigorously tracks source and target currencies,
    computes distinct cross-rates for INR, USD, EUR, and GBP, and preserves
    original currency if conversion is unavailable.
    """
    # 1. USD -> INR
    usd_inr = await convert_amount(100.0, "USD", "INR")
    assert usd_inr["original_currency"] == "USD"
    assert usd_inr["target_currency"] == "INR"
    assert usd_inr["converted_amount"] > 8000.0  # ~8650 INR

    # 2. EUR -> INR must NOT equal USD -> INR rate
    eur_inr = await convert_amount(100.0, "EUR", "INR")
    assert eur_inr["original_currency"] == "EUR"
    assert eur_inr["target_currency"] == "INR"
    assert eur_inr["exchange_rate"] != usd_inr["exchange_rate"]
    assert eur_inr["converted_amount"] > usd_inr["converted_amount"]  # 1 EUR > 1 USD

    # 3. GBP -> INR must NOT equal USD -> INR or EUR -> INR rate
    gbp_inr = await convert_amount(100.0, "GBP", "INR")
    assert gbp_inr["original_currency"] == "GBP"
    assert gbp_inr["target_currency"] == "INR"
    assert gbp_inr["exchange_rate"] != usd_inr["exchange_rate"]
    assert gbp_inr["exchange_rate"] != eur_inr["exchange_rate"]
    assert gbp_inr["converted_amount"] > eur_inr["converted_amount"]  # 1 GBP > 1 EUR

    # 4. Same currency identity
    inr_inr = await convert_amount(500.0, "INR", "INR")
    assert inr_inr["exchange_rate"] == 1.0
    assert inr_inr["converted_amount"] == 500.0

    # 5. Unsupported currency preserves original amount and currency
    unsupported = await convert_amount(250.0, "UNKNOWN_CURRENCY", "INR")
    assert unsupported is not None
    assert unsupported["original_currency"] == "UNKNOWN_CURRENCY"
    assert unsupported["target_currency"] == "INR"
    assert unsupported["converted_amount"] == 250.0  # Original preserved
    assert unsupported["conversion_successful"] is False
    assert unsupported["preserved_original"] is True
