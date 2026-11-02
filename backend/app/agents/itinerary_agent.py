"""
Itinerary Planning Agent
Creates a detailed day-by-day itinerary using insights from other agents.
"""
from typing import Dict, Any, List
from app.services.llm_service import llm_service

SYSTEM_PROMPT = """You are the Itinerary Planning Agent for TripMind AI.
Your role is to create detailed, practical, day-by-day travel itineraries.
Consider geography (group nearby attractions), opening hours, travel time, and traveler preferences.
Avoid overly packed schedules. Build in rest time and spontaneity.
Respond with structured JSON only."""

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
      "theme": "Arrival & First Impressions",
      "weather_note": "Expected weather and how it affects plans",
      "morning": {{
        "time": "08:00 - 12:00",
        "activities": [
          {{
            "time": "08:00",
            "name": "Activity name",
            "type": "attraction|restaurant|transport|leisure|shopping",
            "description": "What to do and see",
            "duration_hours": 2,
            "cost_per_person": 15,
            "location": "Area/neighborhood name",
            "tips": "Practical tip for this activity",
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
        "breakfast": "Where to have breakfast",
        "lunch": "Lunch recommendation",
        "dinner": "Dinner recommendation"
      }},
      "daily_budget_estimate": 150,
      "transportation": "How to get around today",
      "notes": "Any special notes for the day"
    }}
  ],
  "travel_logistics": {{
    "arrival_info": "What to do on arrival day",
    "departure_info": "What to do on departure day",
    "airport_transport": "How to get from airport to accommodation",
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

Create a FULL itinerary for all {duration_days} days. Day 1 is arrival ({departure_date}), last day is departure ({return_date}).
Keep daily budget within the overall budget. Weather notes should reference actual weather data if available.
Activities should be geographically clustered where possible."""


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
            attrs = [a["name"] for a in dr.get("top_attractions", [])[:5]]
            destination_info = f"Top attractions: {', '.join(attrs)}. {dr.get('destination_overview', {}).get('description', '')[:500]}"

    weather_info = "No weather data available"
    if "weather_intelligence" in agent_outputs:
        wr = agent_outputs["weather_intelligence"]
        if not wr.get("error"):
            weather_info = wr.get("weather_summary", "")
            if wr.get("daily_forecast"):
                good_days = [d["date"] for d in wr["daily_forecast"] if d.get("is_good_outdoor")]
                weather_info += f" Good outdoor days: {', '.join(good_days[:5])}"

    local_info = "No local discovery data available"
    if "local_discovery" in agent_outputs:
        ld = agent_outputs["local_discovery"]
        if not ld.get("error"):
            restaurants = [r["name"] for r in ld.get("featured_restaurants", [])[:3]]
            attractions = [a["name"] for a in ld.get("top_attractions", [])[:3]]
            local_info = f"Top restaurants: {', '.join(restaurants)}. Top local spots: {', '.join(attractions)}"

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
                "tips": f"Itinerary generation failed: {str(e)}",
            },
            "days": [],
        }

    result["trip_duration_days"] = duration_days
    result["agent"] = "itinerary_planning"
    return result
