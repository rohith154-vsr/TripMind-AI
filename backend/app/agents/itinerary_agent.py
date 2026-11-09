"""
Itinerary Planning Agent
Creates a detailed, geographically optimized day-by-day itinerary
using verified insights from destination research, weather intelligence,
budget management, and local discovery agents.
Strictly adheres to real destination terrain, correct dates, and currency consistency.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.services.llm_service import llm_service
from app.services.knowledge_base import classify_destination

SYSTEM_PROMPT = """You are the Itinerary Planning Agent for TripMind AI.
Your role is to create realistic, geographically coherent, day-by-day travel itineraries.
STRICT ACCURACY RULES:
1. Use real discovered locations from destination research and local discovery outputs.
2. Geographically cluster activities each day to minimize transit fatigue.
3. Respect terrain and geography: For hill stations or mountain areas (e.g. Ooty), NEVER suggest metro, subways, trams, grand waterfronts, or European-style promenades. Use mountain railways, local tourist cabs, auto-rickshaws, and scenic walking.
4. Never schedule the same attraction more than once across different days.
5. All cost estimates and daily budgets must match the user's requested currency ({currency}).
6. Adhere strictly to the travel dates and duration. Day 1 is {departure_date}, last day is {return_date}.
7. Respond with structured JSON only."""

ITINERARY_PROMPT = """Create a comprehensive day-by-day itinerary for this trip.

Trip Details:
- Origin: {origin}  
- Destination: {destination} ({terrain_note})
- Departure Date: {departure_date}
- Return Date: {return_date}
- Duration: {duration_days} days (travel days included)
- Number of Travelers: {num_travelers}
- Budget: {budget} {currency}
- Expected Daily Budget: {daily_budget_estimate} {currency}/day
- Travel Style: {travel_style}
- Interests: {interests}

Destination Research Available:
{destination_info}

Weather Information:
{weather_info}

Local Discoveries:
{local_info}

Create a detailed itinerary as JSON with this structure:
{{
  "itinerary_overview": {{
    "total_days": {duration_days},
    "theme": "Trip theme based on preferences",
    "highlights": ["Key highlight 1", "Key highlight 2", "Key highlight 3"],
    "pace": "relaxed|moderate|packed",
    "tips": "General itinerary tips"
  }},
  "days": [
    {{
      "day_number": 1,
      "date": "{departure_date}",
      "theme": "Arrival & Orientation",
      "weather_note": "Expected weather and outdoor feasibility",
      "morning": {{
        "time": "08:30 - 12:00",
        "activities": [
          {{
            "time": "09:30",
            "name": "Activity name",
            "type": "attraction|restaurant|transport|leisure|shopping|nature|garden|viewpoint",
            "description": "What to do and see",
            "duration_hours": 2,
            "cost_per_person": 50,
            "location": "Neighborhood or specific venue",
            "tips": "Practical tip (e.g. Local cab or short auto-rickshaw ride. Dress warmly for mountain morning air.)",
            "why_recommended": "Why this suits the traveler's style"
          }}
        ]
      }},
      "afternoon": {{
        "time": "12:30 - 17:00",
        "activities": []
      }},
      "evening": {{
        "time": "17:30 - 21:00",
        "activities": []
      }},
      "meals": {{
        "breakfast": "Breakfast recommendation or neighborhood tiffin room",
        "lunch": "Lunch recommendation or regional cuisine style",
        "dinner": "Dinner recommendation or regional dining quarter"
      }},
      "daily_budget_estimate": {daily_budget_estimate},
      "transportation": "How to get around today (e.g. Local tourist taxi / auto-rickshaw)",
      "notes": "Any special notes for the day"
    }}
  ],
  "travel_logistics": {{
    "arrival_info": "What to do on arrival day",
    "departure_info": "What to do on departure day",
    "airport_transport": "Transit recommendations between airport/station and accommodation",
    "recommended_accommodation_area": "Where to stay and why"
  }},
  "packing_checklist": ["Item 1", "Item 2"],
  "important_bookings": [
    {{
      "item": "What to book in advance",
      "when_to_book": "Book X days in advance",
      "why": "Why advance booking matters"
    }}
  ]
}}

Generate a complete schedule for all {duration_days} days. Day 1 is {departure_date}, last day is {return_date}.
Never repeat the same attraction on multiple days."""


async def run(preferences: Dict[str, Any], agent_outputs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create itinerary using outputs from other agents."""
    destination = preferences["destination"]
    departure_date = preferences.get("departure_date", "")
    return_date = preferences.get("return_date", "")
    budget = preferences.get("budget", 15000)
    currency = preferences.get("currency", "INR").upper()

    # Calculate duration
    duration_days = 4
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        duration_days = max((ret - dep).days + 1, 1)
    except Exception:
        dep = datetime.now() + timedelta(days=14)
        departure_date = dep.strftime("%Y-%m-%d")
        return_date = (dep + timedelta(days=duration_days - 1)).strftime("%Y-%m-%d")

    daily_budget_estimate = round(budget / max(duration_days, 1), 2)

    classification = classify_destination(destination)
    terrain_note = "Highland Hill Station" if classification["is_hill_station"] else "Metropolitan / Urban" if classification["is_metropolitan"] else "Regional Destination"

    # Extract relevant info from other agents
    agent_outputs = agent_outputs or {}

    destination_info = "No destination research available"
    if "destination_research" in agent_outputs:
        dr = agent_outputs["destination_research"]
        if not dr.get("error"):
            attrs = [a["name"] for a in dr.get("top_attractions", [])[:6]]
            destination_info = f"Top attractions: {', '.join(attrs)}. Overview: {dr.get('destination_overview', {}).get('description', '')[:400]}"

    weather_info = "No weather data available"
    if "weather_intelligence" in agent_outputs:
        wr = agent_outputs["weather_intelligence"]
        if not wr.get("error"):
            weather_info = wr.get("weather_summary", "")
            if wr.get("daily_forecast"):
                good_days = [d["date"] for d in wr["daily_forecast"] if d.get("is_good_outdoor")]
                weather_info += f" Good outdoor days: {', '.join(good_days[:5])}"

    local_info = "No verified POI discovery available"
    if "local_discovery" in agent_outputs:
        ld = agent_outputs["local_discovery"]
        if not ld.get("error"):
            restaurants = [r["name"] for r in ld.get("featured_restaurants", [])[:4]]
            attractions = [a["name"] for a in ld.get("top_attractions", [])[:4]]
            if restaurants or attractions:
                local_info = f"Verified restaurants: {', '.join(restaurants) or 'None'}. Verified spots: {', '.join(attractions) or 'None'}"
            elif ld.get("general_dining_suggestions"):
                local_info = f"Regional dining advice: {'; '.join(ld.get('general_dining_suggestions', [])[:2])}"

    interests_str = ", ".join(preferences.get("interests", [])) or "General travel"
    prompt = ITINERARY_PROMPT.format(
        origin=preferences["origin"],
        destination=destination,
        terrain_note=terrain_note,
        departure_date=departure_date,
        return_date=return_date,
        duration_days=duration_days,
        num_travelers=preferences.get("num_travelers", 1),
        budget=budget,
        currency=currency,
        daily_budget_estimate=daily_budget_estimate,
        travel_style=preferences.get("travel_style", "Adventure"),
        interests=interests_str,
        destination_info=destination_info,
        weather_info=weather_info,
        local_info=local_info,
    )

    try:
        result = await llm_service.generate_json(prompt, SYSTEM_PROMPT.format(currency=currency, departure_date=departure_date, return_date=return_date))
    except Exception as e:
        from app.services.fallback_generator import generate_fallback_for_prompt
        result = generate_fallback_for_prompt(prompt, "Itinerary Planning Agent")

    # Enforce correct days and daily_budget_estimate
    if "days" in result:
        for idx, day in enumerate(result["days"]):
            day_date = (dep + timedelta(days=idx)).strftime("%Y-%m-%d")
            day["date"] = day_date
            day["day_number"] = idx + 1
            day["daily_budget_estimate"] = daily_budget_estimate

    result["trip_duration_days"] = duration_days
    result["agent"] = "itinerary_planning"

    is_fallback = "Nilgiri Hill Adventure" in str(result) or "Complete Discovery" in str(result)
    result["metadata"] = {
        "agent_name": "itinerary_planning",
        "display_name": "Itinerary Planning Agent",
        "responsibility": "Generating geographically grouped, non-repeating day-by-day itinerary with realistic travel pacing",
        "source_type": "fallback" if is_fallback else "llm",
        "data_sources": ["Gemini 3.5 Flash Lite", "Synthesized Multi-Agent Intelligence"] if not is_fallback else ["Curated Itinerary Engine (Fallback)"],
        "is_fallback": is_fallback,
        "errors": [],
    }
    return result
