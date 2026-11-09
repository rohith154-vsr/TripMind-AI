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


@pytest.mark.asyncio
async def test_regression_a_osm_parks_museums_no_restaurants_returns_empty_restaurants():
    """
    Regression Test A:
    When OSM returns parks/museums but zero restaurants, featured_restaurants MUST be empty [].
    No park, museum, or viewpoint can ever be classified as a restaurant substitute.
    """
    mock_pois = [
        {
            "name": "Botanical Gardens",
            "lat": 11.4172,
            "lon": 76.7112,
            "category": "attraction",
            "type": "garden",
            "is_verified_osm": True,
        },
        {
            "name": "Government Museum Ooty",
            "lat": 11.4190,
            "lon": 76.7020,
            "category": "attraction",
            "type": "museum",
            "is_verified_osm": True,
        },
        {
            "name": "Doddabetta Peak Viewpoint",
            "lat": 11.4010,
            "lon": 76.7350,
            "category": "leisure",
            "type": "viewpoint",
            "is_verified_osm": True,
        },
    ]

    prefs = {
        "destination": "Ooty",
        "travel_style": "Nature",
        "interests": ["Nature"],
        "num_travelers": 2,
        "budget": 1000,
    }

    with patch("app.agents.local_discovery_agent.geocode", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.local_discovery_agent.find_pois", new_callable=AsyncMock) as mock_find, \
         patch("app.agents.local_discovery_agent.llm_service.generate_json_with_provenance", new_callable=AsyncMock) as mock_llm:
        mock_geo.return_value = {"lat": 11.41, "lon": 76.70, "display_name": "Ooty, Tamil Nadu"}
        mock_find.return_value = mock_pois
        mock_llm.return_value = (
            {
                "featured_restaurants": [
                    {"name": "Nonexistent Royal Diner", "cuisine": "Multi-Cuisine", "lat": 11.41, "lon": 76.70}
                ],
                "top_attractions": [
                    {"name": "Botanical Gardens", "type": "garden", "lat": 11.4172, "lon": 76.7112}
                ],
                "general_dining_suggestions": ["Sample Nilgiri tea and homemade chocolates."],
                "general_activity_suggestions": ["Walk the garden trails."],
            },
            {"provider_used": "gemini", "is_fallback": False, "model": "gemini-2.5-flash"},
        )

        res = await local_discovery_agent.run(prefs)

        # MUST be empty list - zero food POIs were found in OSM!
        assert res["featured_restaurants"] == [], "Must be empty when no authentic food POIs exist"
        for r in res["featured_restaurants"]:
            assert "garden" not in r["name"].lower()
            assert "museum" not in r["name"].lower()
            assert "viewpoint" not in r["name"].lower()

        # Legitimate attraction must be preserved and verified
        assert len(res["top_attractions"]) >= 1
        assert res["top_attractions"][0]["name"] == "Botanical Gardens"
        assert res["top_attractions"][0]["is_verified_osm"] is True


@pytest.mark.asyncio
async def test_regression_b_osm_restaurants_no_attractions_returns_empty_attractions():
    """
    Regression Test B:
    When OSM returns only restaurants and zero attractions, top_attractions MUST be empty [].
    No restaurant can ever be classified as an attraction substitute.
    """
    mock_pois = [
        {
            "name": "Earl's Secret Restaurant",
            "lat": 11.4120,
            "lon": 76.6980,
            "category": "food",
            "type": "restaurant",
            "cuisine": "Continental",
            "is_verified_osm": True,
        },
        {
            "name": "Willy's Coffee Pub",
            "lat": 11.4110,
            "lon": 76.6970,
            "category": "food",
            "type": "cafe",
            "cuisine": "Bakery",
            "is_verified_osm": True,
        },
    ]

    prefs = {
        "destination": "Ooty",
        "travel_style": "Food",
        "interests": ["Food"],
        "num_travelers": 2,
        "budget": 1000,
    }

    with patch("app.agents.local_discovery_agent.geocode", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.local_discovery_agent.find_pois", new_callable=AsyncMock) as mock_find, \
         patch("app.agents.local_discovery_agent.llm_service.generate_json_with_provenance", new_callable=AsyncMock) as mock_llm:
        mock_geo.return_value = {"lat": 11.41, "lon": 76.70, "display_name": "Ooty, Tamil Nadu"}
        mock_find.return_value = mock_pois
        mock_llm.return_value = (
            {
                "featured_restaurants": [
                    {"name": "Earl's Secret Restaurant", "cuisine": "Continental", "lat": 11.4120, "lon": 76.6980}
                ],
                "top_attractions": [
                    {"name": "Fictional Castle of Ooty", "type": "castle", "lat": 11.41, "lon": 76.70}
                ],
                "general_dining_suggestions": ["Enjoy local dining."],
                "general_activity_suggestions": ["Town walk."],
            },
            {"provider_used": "gemini", "is_fallback": False, "model": "gemini-2.5-flash"},
        )

        res = await local_discovery_agent.run(prefs)

        # MUST be empty list - zero attraction POIs were found in OSM!
        assert res["top_attractions"] == [], "Must be empty when no authentic attraction POIs exist"
        for a in res["top_attractions"]:
            assert "restaurant" not in a["name"].lower()
            assert "cafe" not in a["name"].lower()

        # Legitimate restaurant must be preserved and verified
        assert len(res["featured_restaurants"]) >= 1
        assert res["featured_restaurants"][0]["name"] == "Earl's Secret Restaurant"
        assert res["featured_restaurants"][0]["is_verified_osm"] is True


@pytest.mark.asyncio
async def test_regression_c_heuristic_weather_flags_and_absence_of_historical_flags():
    """
    Regression Test C:
    When weather estimate is heuristic, is_heuristic_estimate is True,
    data_type is 'heuristic_seasonal_estimate', and is_historical_estimate is NOT present.
    """
    today = date.today()
    future_dep = (today + timedelta(days=45)).strftime("%Y-%m-%d")
    future_ret = (today + timedelta(days=48)).strftime("%Y-%m-%d")

    prefs = {
        "destination": "Ooty",
        "departure_date": future_dep,
        "return_date": future_ret,
    }

    with patch("app.agents.weather_agent.get_coordinates", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.weather_agent.llm_service.generate_json_with_provenance", new_callable=AsyncMock) as mock_llm:
        mock_geo.return_value = {"lat": 11.41, "lon": 76.70, "display_name": "Ooty"}
        mock_llm.return_value = (
            {
                "weather_summary": "Heuristic seasonal estimate.",
                "overall_rating": "good",
                "temperature_range": {"avg_high_c": 20.0, "avg_low_c": 11.0},
                "precipitation_risk": "low",
                "best_days_outdoor": [future_dep],
                "days_to_avoid_outdoor": [],
                "packing_recommendations": ["Layered clothing"],
                "activity_adjustments": [],
            },
            {"provider_used": "gemini", "is_fallback": False, "model": "gemini-2.5-flash"},
        )

        res = await weather_agent.run(prefs)
        forecast = res["daily_forecast"]
        assert len(forecast) == 4
        for day in forecast:
            assert day.get("is_heuristic_estimate") is True
            assert day.get("data_type") == "heuristic_seasonal_estimate"
            assert "is_historical_estimate" not in day, "is_historical_estimate must be completely removed"
            assert day.get("is_live_observation") is False

        wp = res["metadata"]["weather_provenance"]
        assert wp["is_heuristic"] is True
        assert wp["is_live"] is False
        assert "historical" not in wp["source_type"].lower()


@pytest.mark.asyncio
async def test_regression_d_local_discovery_provenance_gemini_vs_fallback():
    """
    Regression Test D:
    Local Discovery provenance distinguishes Live OSM + Gemini from Live OSM + Fallback enrichment.
    """
    mock_pois = [
        {
            "name": "Nahata Sweets",
            "lat": 11.4102,
            "lon": 76.6950,
            "category": "food",
            "type": "restaurant",
            "is_verified_osm": True,
        }
    ]

    prefs = {
        "destination": "Ooty",
        "travel_style": "Culture",
        "interests": ["Food"],
    }

    # Case 1: Live OSM + Gemini
    with patch("app.agents.local_discovery_agent.geocode", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.local_discovery_agent.find_pois", new_callable=AsyncMock) as mock_find, \
         patch("app.agents.local_discovery_agent.llm_service.generate_json_with_provenance", new_callable=AsyncMock) as mock_llm:
        mock_geo.return_value = {"lat": 11.41, "lon": 76.70, "display_name": "Ooty"}
        mock_find.return_value = mock_pois
        mock_llm.return_value = (
            {
                "featured_restaurants": [{"name": "Nahata Sweets", "cuisine": "Sweets", "lat": 11.4102, "lon": 76.6950}],
                "top_attractions": [],
                "general_dining_suggestions": ["Enjoy sweets"],
            },
            {"provider_used": "gemini", "is_fallback": False, "model": "gemini-2.5-flash"},
        )

        res_live = await local_discovery_agent.run(prefs)
        meta_live = res_live["metadata"]
        assert meta_live["source_type"] == "live_api"
        assert meta_live["is_fallback"] is False
        assert meta_live["poi_provenance"]["provider"] == "OpenStreetMap / Overpass API"
        assert meta_live["poi_provenance"]["has_live_pois"] is True
        assert meta_live["llm_provenance"]["provider_used"] == "gemini"
        assert meta_live["llm_provenance"]["is_fallback"] is False
        assert meta_live["verification_status"] == "matched_against_osm_records"

    # Case 2: Live OSM + Fallback LLM enrichment (e.g. Gemini failed)
    with patch("app.agents.local_discovery_agent.geocode", new_callable=AsyncMock) as mock_geo, \
         patch("app.agents.local_discovery_agent.find_pois", new_callable=AsyncMock) as mock_find, \
         patch("app.agents.local_discovery_agent.llm_service.generate_json_with_provenance", new_callable=AsyncMock) as mock_llm:
        mock_geo.return_value = {"lat": 11.41, "lon": 76.70, "display_name": "Ooty"}
        mock_find.return_value = mock_pois
        mock_llm.side_effect = RuntimeError("Gemini quota exceeded")

        res_hybrid = await local_discovery_agent.run(prefs)
        meta_hybrid = res_hybrid["metadata"]
        assert meta_hybrid["source_type"] == "hybrid"
        assert meta_hybrid["is_fallback"] is True
        assert meta_hybrid["poi_provenance"]["has_live_pois"] is True
        assert meta_hybrid["llm_provenance"]["is_fallback"] is True
        assert meta_hybrid["verification_status"] == "matched_against_osm_records"
        assert "Gemini quota exceeded" in meta_hybrid["errors"][0]



