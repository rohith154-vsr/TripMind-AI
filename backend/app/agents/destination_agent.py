"""
Destination Research Agent
Researches the destination, identifies attractions, and recommends places based on user preferences.
"""
from typing import Dict, Any
from app.services.llm_service import llm_service
from app.services.maps_service import geocode

SYSTEM_PROMPT = """You are the Destination Research Agent for TripMind AI, a specialized travel intelligence system.
Your role is to research travel destinations thoroughly and provide accurate, useful information.
Always respond with structured JSON. Never fabricate specific facts you are unsure about.
If you don't know something, say so clearly in the data."""

AGENT_PROMPT_TEMPLATE = """Research the travel destination for a trip with these preferences:

- Origin: {origin}
- Destination: {destination}
- Travel Style: {travel_style}
- Interests: {interests}
- Number of Travelers: {num_travelers}
- Travel Dates: {departure_date} to {return_date}

Provide a comprehensive destination research report as JSON with this exact structure:
{{
  "destination_overview": {{
    "name": "Full destination name",
    "country": "Country name",
    "region": "Region/state/province",
    "description": "2-3 paragraph overview of the destination",
    "best_time_to_visit": "When is the best time to visit",
    "language": "Primary language spoken",
    "currency": "Local currency name and code",
    "timezone": "Timezone info",
    "climate_summary": "Brief climate description for the travel period"
  }},
  "top_attractions": [
    {{
      "name": "Attraction name",
      "type": "museum|park|landmark|beach|temple|market|etc",
      "description": "2-3 sentence description",
      "why_visit": "Why this matches the traveler's interests",
      "estimated_duration_hours": 2,
      "admission_fee_usd": 10,
      "best_time": "Morning/Afternoon/Evening",
      "insider_tip": "A useful insider tip"
    }}
  ],
  "recommended_activities": [
    {{
      "name": "Activity name",
      "category": "adventure|cultural|food|relaxation|shopping|photography",
      "description": "Description of activity",
      "duration_hours": 3,
      "estimated_cost_usd": 50,
      "suitable_for": "Who this activity is best for"
    }}
  ],
  "neighborhoods": [
    {{
      "name": "Neighborhood name",
      "character": "Brief character description",
      "best_for": "What it's best for"
    }}
  ],
  "cultural_tips": ["tip1", "tip2", "tip3"],
  "safety_info": "General safety information for the destination",
  "getting_around": "How to get around the destination",
  "must_try_foods": ["food1", "food2", "food3"],
  "research_confidence": "high|medium|low",
  "data_notes": "Any caveats or notes about the information provided"
}}

Include at least 8 top attractions and 5 activities tailored to the traveler's interests ({interests}) and travel style ({travel_style}).
Focus on real, well-known places. Do not invent places."""


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Execute destination research for the given preferences."""
    # Get coordinates for the destination
    geo_data = None
    try:
        geo_data = await geocode(preferences["destination"])
    except Exception as e:
        geo_data = {"error": str(e)}

    # Build the LLM prompt
    interests_str = ", ".join(preferences.get("interests", [])) or "General sightseeing"
    prompt = AGENT_PROMPT_TEMPLATE.format(
        origin=preferences["origin"],
        destination=preferences["destination"],
        travel_style=preferences.get("travel_style", "Adventure"),
        interests=interests_str,
        num_travelers=preferences.get("num_travelers", 1),
        departure_date=preferences.get("departure_date", ""),
        return_date=preferences.get("return_date", ""),
    )

    result = await llm_service.generate_json(prompt, SYSTEM_PROMPT)

    # Attach geocoding data
    if geo_data and "error" not in geo_data:
        result["coordinates"] = {
            "lat": geo_data["lat"],
            "lon": geo_data["lon"],
            "display_name": geo_data["display_name"],
        }
    else:
        result["coordinates"] = None

    is_fallback = "Historic Center & Landmark Plaza" in str(result)
    result["metadata"] = {
        "agent_name": "destination_research",
        "display_name": "Destination Research Agent",
        "responsibility": "Destination research, attraction analysis, and cultural orientation",
        "source_type": "fallback" if is_fallback else "llm",
        "data_sources": ["Nominatim Geocoding", "Gemini 3.5 Flash Lite" if not is_fallback else "Curated Knowledge Base"],
        "is_fallback": is_fallback,
        "errors": [geo_data["error"]] if (geo_data and "error" in geo_data) else [],
    }

    result["agent"] = "destination_research"
    return result
