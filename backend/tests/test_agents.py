import pytest
from app.agents import (
    destination_agent,
    weather_agent,
    local_discovery_agent,
    budget_agent,
    itinerary_agent,
    coordinator
)

@pytest.mark.asyncio
async def test_destination_agent(sample_preferences):
    result = await destination_agent.run(sample_preferences)
    assert result is not None
    assert result.get("agent") == "destination_research"
    assert "destination_overview" in result
    assert "top_attractions" in result

@pytest.mark.asyncio
async def test_weather_agent(sample_preferences):
    result = await weather_agent.run(sample_preferences)
    assert result is not None
    assert result.get("agent") == "weather_intelligence"
    assert "weather_summary" in result
    assert "daily_forecast" in result

@pytest.mark.asyncio
async def test_local_discovery_agent(sample_preferences):
    result = await local_discovery_agent.run(sample_preferences)
    assert result is not None
    assert result.get("agent") == "local_discovery"
    assert "featured_restaurants" in result or "top_attractions" in result

@pytest.mark.asyncio
async def test_budget_agent(sample_preferences):
    result = await budget_agent.run(sample_preferences)
    assert result is not None
    assert result.get("agent") == "budget_management"
    assert "budget_summary" in result

@pytest.mark.asyncio
async def test_itinerary_agent(sample_preferences):
    result = await itinerary_agent.run(sample_preferences, {})
    assert result is not None
    assert result.get("agent") == "itinerary_planning"
    assert "itinerary_overview" in result
    assert "days" in result
