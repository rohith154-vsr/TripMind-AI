"""
Tests for Data Integrity, Zero Fabricated Establishments,
Provenance Labelling, and Multi-Agent Transparency.
"""
import pytest
from app.services.fallback_generator import _generate_local_discovery
from app.services.currency_service import get_exchange_rate_with_metadata, convert_amount, _RATE_CACHE
from app.agents import (
    destination_agent,
    weather_agent,
    local_discovery_agent,
    budget_agent,
    itinerary_agent,
)


def test_fabrication_prevention_on_fallback():
    """Verify fallback local discovery never produces synthetic business names or 0.0 coordinates."""
    res = _generate_local_discovery("Plan for Bangalore")
    
    # Must NOT have synthetic venues or fake coordinates
    assert res["featured_restaurants"] == [], "Fallback must not invent restaurant names"
    assert res["top_attractions"] == [], "Fallback must not invent synthetic attractions"
    assert res["hidden_gems"] == [], "Fallback must not invent synthetic hidden gems"
    assert res["is_live_data"] is False, "Fallback must be marked as not live"
    assert "api_status_message" in res
    assert "data_source" in res
    assert len(res["general_dining_suggestions"]) > 0, "Must provide cultural dining advice instead"


@pytest.mark.asyncio
async def test_currency_caching_and_provenance():
    """Verify currency conversion returns provenance and leverages in-memory caching."""
    # Convert USD to EUR
    conv1 = await convert_amount(100.0, "USD", "EUR")
    assert conv1 is not None
    assert "is_live_rate" in conv1
    assert "rate_source" in conv1
    assert "exchange_rate" in conv1
    assert conv1["converted_amount"] > 0

    # Ensure cached
    cache_key = ("USD", "EUR")
    assert cache_key in _RATE_CACHE

    # Second call should use cache
    rate, is_live, source = await get_exchange_rate_with_metadata("USD", "EUR")
    assert rate == conv1["exchange_rate"]
    assert "Cached" in source or "Live" in source


@pytest.mark.asyncio
async def test_all_agents_have_transparency_metadata(sample_preferences):
    """Verify that every agent's output dictionary contains a standardized transparency block."""
    # 1. Destination Research
    dest_res = await destination_agent.run(sample_preferences)
    assert "metadata" in dest_res
    meta = dest_res["metadata"]
    assert meta["agent_name"] == "destination_research"
    assert "responsibility" in meta
    assert "source_type" in meta
    assert "data_sources" in meta

    # 2. Weather Agent
    weather_res = await weather_agent.run(sample_preferences)
    assert "metadata" in weather_res
    meta = weather_res["metadata"]
    assert meta["agent_name"] == "weather_intelligence"
    assert "responsibility" in meta

    # 3. Local Discovery
    local_res = await local_discovery_agent.run(sample_preferences)
    assert "metadata" in local_res
    meta = local_res["metadata"]
    assert meta["agent_name"] == "local_discovery"
    # Ensure no restaurant has 0.0, 0.0
    for r in local_res.get("featured_restaurants", []):
        assert abs(r["lat"]) > 0.0001
        assert abs(r["lon"]) > 0.0001

    # 4. Budget Agent
    budget_res = await budget_agent.run(sample_preferences)
    assert "metadata" in budget_res
    meta = budget_res["metadata"]
    assert meta["agent_name"] == "budget_management"

    # 5. Itinerary Agent
    itin_res = await itinerary_agent.run(sample_preferences, {
        "destination_research": dest_res,
        "weather_intelligence": weather_res,
        "local_discovery": local_res,
        "budget_management": budget_res,
    })
    assert "metadata" in itin_res
    meta = itin_res["metadata"]
    assert meta["agent_name"] == "itinerary_planning"
