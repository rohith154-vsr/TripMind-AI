import pytest
from app.services.currency_service import convert_amount, get_exchange_rate
from app.services.weather_service import parse_weather, WMO_CODES
from app.services.fallback_generator import generate_fallback_for_prompt
from app.services.llm_service import _is_api_key_configured, _clean_json

def test_api_key_check():
    assert _is_api_key_configured("") is False
    assert _is_api_key_configured("your_gemini_api_key_here") is False
    assert _is_api_key_configured("placeholder") is False
    assert _is_api_key_configured("AIzaSyD-valid-key-example") is True

def test_clean_json():
    raw = "```json\n{\"test\": 123}\n```"
    assert _clean_json(raw) == '{"test": 123}'

def test_fallback_generator_destination():
    prompt = "Destination: Tokyo\nOrigin: London\nTravel Style: Adventure\nInterests: Food, Nature\ndestination_overview"
    res = generate_fallback_for_prompt(prompt, "Destination Research Agent")
    assert "destination_overview" in res
    assert res["destination_overview"]["name"] == "Tokyo"
    assert len(res["top_attractions"]) >= 5

def test_fallback_generator_weather():
    prompt = "Destination: Rome\nprecipitation_risk"
    res = generate_fallback_for_prompt(prompt, "Weather Intelligence Agent")
    assert "weather_summary" in res
    assert "daily_forecast" in res
    assert len(res["daily_forecast"]) > 0

def test_fallback_generator_budget():
    prompt = "Destination: Paris\nTotal Budget: 1500 USD\nexpense_breakdown"
    res = generate_fallback_for_prompt(prompt, "Budget Management Agent")
    assert "budget_summary" in res
    assert "expense_breakdown" in res
    assert "accommodation" in res["expense_breakdown"]

def test_parse_weather():
    dummy_data = {
        "daily": {
            "time": ["2026-06-01"],
            "temperature_2m_max": [25.0],
            "temperature_2m_min": [15.0],
            "precipitation_sum": [0.0],
            "weathercode": [0],
            "windspeed_10m_max": [10.0],
        }
    }
    parsed = parse_weather(dummy_data)
    assert len(parsed) == 1
    assert parsed[0]["condition"] == "Clear sky"
    assert parsed[0]["is_good_outdoor"] is True

@pytest.mark.asyncio
async def test_currency_same_currency():
    rate = await get_exchange_rate("USD", "USD")
    assert rate == 1.0
