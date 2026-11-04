"""
Itinerary Planning Agent
Creates a detailed, geographically optimized day-by-day itinerary
using verified insights from destination research, weather intelligence,
budget management, and local discovery agents.
"""
from typing import Dict, Any, List
from app.services.llm_service import llm_service

SYSTEM_PROMPT = """You are the Itinerary Planning Agent for TripMind AI.
Your role is to create realistic, geographically coherent, day-by-day travel itineraries.
STRICT ACCURACY RULES:
1. Use actual discovered locations from the provided agent outputs.
2. Geographically cluster activities for each day to minimize transit fatigue.
3. Never schedule the same attraction more than once across different days.
4. Adhere strictly to the travel dates and duration.
5. Avoid claiming specific opening hours unless explicitly confirmed; otherwise note 'Typical hours; verify locally'.
6. Clearly label estimated travel times between activities (e.g. 'Transit: ~15 mins via metro').
7. Build in buffer time and avoid impossible or exhausting schedules.
8. Respond with structured JSON only."""

ITINERARY_PROMPT = """Create a comprehensive day-by-day itinerary for this trip.

Trip Details:
- Origin: {origin}  
- Destination: {destination}
- Departure Date: {departure_date}
- Return Date: {return_date}
- Duration: {duration_days} days (travel days included)
- Number of Travelers: {num_travelers}
- Budget: {budget} {currency}
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
      "date": "YYYY-MM-DD",
      "theme": "Arrival & Orientation",
      "weather_note": "Expected weather and outdoor feasibility",
      "morning": {{
        "time": "08:00 - 12:00",
        "activities": [
          {{
            "time": "09:00",
            "name": "Activity name",
            "type": "attraction|restaurant|transport|leisure|shopping",
            "description": "What to do and see",
            "duration_hours": 2,
            "cost_per_person": 15,
            "location": "Neighborhood or specific venue",
            "tips": "Practical tip (e.g. Transit: ~15 mins via metro. Typical hours; verify locally)",
            "why_recommended": "Why this suits the traveler's style"
          }}
        ]
      }},
      "afternoon": {{
        "time": "12:00 - 18:00",
        "activities": []
      }},
      "evening": {{
        "time": "18:00 - 22:00",
        "activities": []
      }},
      "meals": {{
        "breakfast": "Breakfast recommendation or neighborhood bakery style",
        "lunch": "Lunch recommendation or local cuisine style",
        "dinner": "Dinner recommendation or regional dining quarter"
      }},
      "daily_budget_estimate": 150,
      "transportation": "How to get around today",
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
    from datetime import datetime

    destination = preferences["destination"]
    departure_date = preferences.get("departure_date", "")
    return_date = preferences.get("return_date", "")

    # Calculate duration
    duration_days = 7
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        duration_days = max((ret - dep).days + 1, 1)
    except Exception:
        pass

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
        departure_date=departure_date,
        return_date=return_date,
        duration_days=duration_days,
        num_travelers=preferences.get("num_travelers", 1),
        budget=preferences.get("budget", 1000),
        currency=preferences.get("currency", "USD"),
        travel_style=preferences.get("travel_style", "Adventure"),
        interests=interests_str,
        destination_info=destination_info,
        weather_info=weather_info,
        local_info=local_info,
    )

    try:
        result = await llm_service.generate_json(prompt, SYSTEM_PROMPT)
    except Exception as e:
        result = {
            "itinerary_overview": {
                "total_days": duration_days,
                "theme": f"Trip to {destination}",
                "highlights": [],
                "tips": f"Itinerary generation fallback: {str(e)}",
            },
            "days": [],
        }

    result["trip_duration_days"] = duration_days
    result["agent"] = "itinerary_planning"

    is_fallback = "Complete Discovery" in str(result)
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
