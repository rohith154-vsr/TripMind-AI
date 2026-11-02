"""
Local Discovery Agent
Uses OpenStreetMap Overpass API to find real restaurants, attractions, and POIs.
"""
from typing import Dict, Any, List
from app.services.llm_service import llm_service
from app.services.maps_service import geocode, find_pois

SYSTEM_PROMPT = """You are the Local Discovery Agent for TripMind AI.
Your role is to find and curate local restaurants, attractions, and hidden gems.
Analyze real POI data and enrich it with helpful context.
Respond with structured JSON only."""

ENRICHMENT_PROMPT = """You have retrieved real points of interest data from OpenStreetMap for {destination}.

Real POI Data (from OpenStreetMap):
{poi_data}

User Preferences:
- Travel Style: {travel_style}
- Interests: {interests}
- Number of Travelers: {num_travelers}
- Budget Level: {budget_level}

Based on this real data, provide a curated local discovery report as JSON:
{{
  "featured_restaurants": [
    {{
      "name": "Restaurant name",
      "cuisine": "Cuisine type",
      "description": "Brief description based on what you know",
      "price_range": "$|$$|$$$|$$$$",
      "best_for": "lunch|dinner|breakfast|all_day",
      "lat": 0.0,
      "lon": 0.0,
      "opening_hours": "Hours if available",
      "recommendation_reason": "Why this suits the traveler"
    }}
  ],
  "top_attractions": [
    {{
      "name": "Attraction name",
      "type": "museum|park|landmark|historic|beach|market",
      "description": "Description",
      "lat": 0.0,
      "lon": 0.0,
      "estimated_time_hours": 2,
      "best_time_to_visit": "morning|afternoon|evening|any",
      "crowd_level": "low|moderate|high"
    }}
  ],
  "hidden_gems": [
    {{
      "name": "Name",
      "description": "Why it's special",
      "category": "food|culture|nature|shopping|nightlife",
      "lat": 0.0,
      "lon": 0.0
    }}
  ],
  "neighborhood_guides": [
    {{
      "name": "Neighborhood name",
      "vibe": "Description of the area",
      "top_spots": ["spot1", "spot2"]
    }}
  ],
  "local_tips": [
    "Practical tip for getting the most out of the destination"
  ],
  "data_source": "OpenStreetMap / Overpass API",
  "poi_count_retrieved": 0
}}

Use the actual names and coordinates from the POI data. Fill in descriptions based on your knowledge.
If POI data is limited, note this in local_tips."""


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Find local restaurants and attractions using real OSM data."""
    destination = preferences["destination"]
    travel_style = preferences.get("travel_style", "Adventure")
    interests = preferences.get("interests", [])
    num_travelers = preferences.get("num_travelers", 1)
    budget = preferences.get("budget", 1000)
    budget_level = "budget" if budget < 500 else "mid-range" if budget < 2000 else "luxury"

    # Step 1: Geocode destination
    geo = None
    pois = []
    coordinates = None
    try:
        geo = await geocode(destination)
        if geo:
            coordinates = {"lat": geo["lat"], "lon": geo["lon"]}
            # Choose categories based on interests
            categories = ["tourism", "amenity=restaurant", "historic", "leisure"]
            if "Food" in interests:
                categories.extend(["amenity=cafe", "amenity=bar"])
            if "Historical Places" in interests:
                categories.append("historic=monument")
            if "Nature" in interests:
                categories.extend(["leisure=park", "natural=peak"])
            
            pois = await find_pois(geo["lat"], geo["lon"], radius_m=8000, categories=categories)
    except Exception as e:
        pois = []

    # Step 2: Enrich with LLM
    interests_str = ", ".join(interests) or "General sightseeing"
    poi_data_str = str(pois[:30]) if pois else "No POI data available from OpenStreetMap for this location."

    prompt = ENRICHMENT_PROMPT.format(
        destination=destination,
        poi_data=poi_data_str,
        travel_style=travel_style,
        interests=interests_str,
        num_travelers=num_travelers,
        budget_level=budget_level,
    )

    try:
        result = await llm_service.generate_json(prompt, SYSTEM_PROMPT)
    except Exception as e:
        result = {
            "featured_restaurants": [],
            "top_attractions": [],
            "hidden_gems": [],
            "neighborhood_guides": [],
            "local_tips": [f"Local discovery data unavailable: {str(e)}"],
        }

    result["raw_osm_pois"] = pois[:20]  # Include raw data for map
    result["coordinates"] = coordinates
    result["poi_count_retrieved"] = len(pois)
    result["agent"] = "local_discovery"
    return result
