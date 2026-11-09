"""
Local Discovery Agent
Uses OpenStreetMap Overpass API to find authentic restaurants, attractions, and POIs.
Strictly adheres to the Zero Fabricated Establishments Policy:
Never fabricates venue names, street addresses, or coordinates.
Matches and validates any LLM-curated establishments against verified OSM POI records.
"""
from typing import Dict, Any, List, Optional
import re
from app.services.llm_service import llm_service
from app.services.maps_service import geocode, find_pois

SYSTEM_PROMPT = """You are the Local Discovery Agent for TripMind AI.
Your role is to curate authentic local restaurants, attractions, and cultural experiences.
DATA INTEGRITY RULES:
1. NEVER invent fictional restaurant or establishment names.
2. NEVER invent fake street addresses or fake geographic coordinates (never use 0.0, 0.0).
3. If real OpenStreetMap POI data is provided below, select and enrich ONLY establishments present in that data.
4. If POI data is empty or unavailable, leave "featured_restaurants" and "top_attractions" as empty lists []. Provide regional food culture and culinary advice under "general_dining_suggestions".
5. Respond with structured JSON only."""

ENRICHMENT_PROMPT = """You have retrieved points of interest data from OpenStreetMap for {destination}.

Verified OpenStreetMap POI Data:
{poi_data}

User Preferences:
- Travel Style: {travel_style}
- Interests: {interests}
- Number of Travelers: {num_travelers}
- Budget Level: {budget_level}

CRITICAL RULES:
- If POI data contains real establishments, select up to 6 authentic venues directly from the list, keeping their EXACT names, lat, and lon.
- If POI data is empty or has no restaurants, "featured_restaurants" MUST be an empty array [].
- Under "general_dining_suggestions", describe the destination's food culture, famous dishes, popular dining neighborhoods, and etiquette.
- Never output 0.0 for latitude or longitude.

Return JSON with this exact structure:
{{
  "featured_restaurants": [
    {{
      "name": "Exact Name from OSM POI list",
      "cuisine": "Cuisine type",
      "description": "Helpful context about the venue",
      "price_range": "$|$$|$$$|$$$$",
      "best_for": "lunch|dinner|breakfast|all_day",
      "lat": 12.3456,
      "lon": 78.9101,
      "opening_hours": "Hours if known",
      "recommendation_reason": "Why this suits the traveler"
    }}
  ],
  "top_attractions": [
    {{
      "name": "Exact Name from OSM POI list",
      "type": "museum|park|landmark|historic|beach|market",
      "description": "Description",
      "lat": 12.3456,
      "lon": 78.9101,
      "estimated_time_hours": 2,
      "best_time_to_visit": "morning|afternoon|evening|any",
      "crowd_level": "low|moderate|high"
    }}
  ],
  "general_dining_suggestions": [
    "Regional food specialty or cultural dining tip",
    "Popular food market or dining street to explore"
  ],
  "general_activity_suggestions": [
    "Scenic neighborhood walk or cultural activity advice"
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
  ]
}}"""


def _normalize_name(name: str) -> str:
    """Normalize venue name for fuzzy comparison."""
    if not name or not isinstance(name, str):
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    return " ".join(cleaned.split())


def _find_matching_osm_poi(
    venue_name: str,
    venue_lat: Any,
    venue_lon: Any,
    osm_pois: List[Dict[str, Any]],
    coord_tolerance: float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Match an establishment against authentic OSM POI records.
    Strictly prevents marking LLM hallucinations as OSM verified.
    Requires:
    1. Valid non-zero numeric coordinates within proximity tolerance (~500m).
    2. Normalized name correspondence (exact match or bidirectional substring match with length >= 4).
    """
    if not venue_name or not isinstance(venue_name, str):
        return None
    try:
        v_lat = float(venue_lat)
        v_lon = float(venue_lon)
    except (ValueError, TypeError):
        return None

    if abs(v_lat) < 0.0001 and abs(v_lon) < 0.0001:
        return None

    norm_venue = _normalize_name(venue_name)
    if not norm_venue:
        return None

    for poi in osm_pois:
        poi_name = poi.get("name")
        if not poi_name or not isinstance(poi_name, str):
            continue
        try:
            p_lat = float(poi["lat"])
            p_lon = float(poi["lon"])
        except (ValueError, TypeError):
            continue

        # Proximity check
        if abs(v_lat - p_lat) > coord_tolerance or abs(v_lon - p_lon) > coord_tolerance:
            continue

        # Name correspondence
        norm_poi = _normalize_name(poi_name)
        if not norm_poi:
            continue

        if norm_venue == norm_poi or (
            len(norm_venue) >= 4 and len(norm_poi) >= 4 and (
                norm_venue in norm_poi or norm_poi in norm_venue
            )
        ):
            return poi

    return None


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Find authentic local restaurants and attractions using real OSM data."""
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
            coordinates = {"lat": geo["lat"], "lon": geo["lon"], "display_name": geo.get("display_name", destination)}
            categories = ["tourism", "amenity=restaurant", "historic", "leisure"]
            if "Food" in interests:
                categories.extend(["amenity=cafe", "amenity=bar"])
            if "Historical Places" in interests:
                categories.append("historic=monument")
            if "Nature" in interests:
                categories.extend(["leisure=park", "natural=peak"])

            pois = await find_pois(
                geo["lat"],
                geo["lon"],
                radius_m=8000,
                categories=categories,
                destination_name=destination,
            )
    except Exception:
        pois = []

    # Step 2: Prepare prompt for LLM
    interests_str = ", ".join(interests) or "General sightseeing"
    has_live_pois = len(pois) > 0

    if has_live_pois:
        poi_summary = "\n".join([
            f"- {p['name']} ({p.get('category')}, {p.get('type')}): lat={p['lat']}, lon={p['lon']}"
            for p in pois[:25]
        ])
    else:
        poi_summary = "No live POI records returned by OpenStreetMap Overpass for this location."

    prompt = ENRICHMENT_PROMPT.format(
        destination=destination,
        poi_data=poi_summary,
        travel_style=travel_style,
        interests=interests_str,
        num_travelers=num_travelers,
        budget_level=budget_level,
    )

    try:
        result, llm_meta = await llm_service.generate_json_with_provenance(prompt, SYSTEM_PROMPT)
    except Exception as e:
        result = {
            "featured_restaurants": [],
            "top_attractions": [],
            "general_dining_suggestions": [
                f"Explore authentic dining quarters in {destination} where local family-run eateries prepare regional dishes.",
                "Visit local central markets for fresh morning specialties and casual food tastings."
            ],
            "general_activity_suggestions": [
                f"Take a walking exploration through historic avenues in {destination}."
            ],
            "neighborhood_guides": [],
            "local_tips": [f"Local discovery note: {str(e)}"],
        }
        llm_meta = {"provider_used": "fallback", "is_fallback": True, "error": str(e)}

    # Step 3: Strict validation against fabricated venues and coordinates
    # If no live POIs were found, NEVER return fabricated venues
    if not has_live_pois:
        result["featured_restaurants"] = []
        result["top_attractions"] = []
        result["is_live_data"] = False
        result["data_source"] = "Curated Regional Travel Knowledge (Overpass POIs Unavailable)"
        result["api_status_message"] = (
            "Live OpenStreetMap POI discovery is currently unavailable. "
            "In strict compliance with TripMind data integrity standards, fictional business names "
            "and synthetic coordinates are never fabricated. Verified regional dining advice is provided instead."
        )
    else:
        # Match each restaurant against verified OSM records
        valid_restaurants = []
        for r in result.get("featured_restaurants", []):
            matched = _find_matching_osm_poi(r.get("name"), r.get("lat"), r.get("lon"), pois)
            if matched:
                r["is_verified_osm"] = True
                r["lat"] = matched["lat"]
                r["lon"] = matched["lon"]
                r["osm_verified_name"] = matched["name"]
                valid_restaurants.append(r)

        # Preserve legitimate OSM food records if LLM hallucinated establishments
        if not valid_restaurants:
            food_pois = [p for p in pois if p.get("category") == "food" or "restaurant" in p.get("type", "") or "cafe" in p.get("type", "")]
            backup_food = food_pois if food_pois else pois[:4]
            for p in backup_food[:4]:
                valid_restaurants.append({
                    "name": p["name"],
                    "cuisine": p.get("cuisine") or "Regional Cuisine",
                    "description": p.get("description") or f"Authentic local establishment in {destination}",
                    "price_range": "$$",
                    "best_for": "lunch|dinner",
                    "lat": p["lat"],
                    "lon": p["lon"],
                    "opening_hours": p.get("opening_hours") or "Standard local hours",
                    "recommendation_reason": "Verified OpenStreetMap establishment in destination area",
                    "is_verified_osm": True,
                })
        result["featured_restaurants"] = valid_restaurants

        # Match each attraction against verified OSM records
        valid_attractions = []
        for a in result.get("top_attractions", []):
            matched = _find_matching_osm_poi(a.get("name"), a.get("lat"), a.get("lon"), pois)
            if matched:
                a["is_verified_osm"] = True
                a["lat"] = matched["lat"]
                a["lon"] = matched["lon"]
                a["osm_verified_name"] = matched["name"]
                valid_attractions.append(a)

        # Preserve legitimate OSM attraction records if LLM hallucinated attractions
        if not valid_attractions:
            attr_pois = [p for p in pois if p.get("category") != "food" or "tourism" in p.get("type", "")]
            backup_attr = attr_pois if attr_pois else pois[:4]
            for p in backup_attr[:4]:
                valid_attractions.append({
                    "name": p["name"],
                    "type": p.get("type", "attraction"),
                    "description": p.get("description") or f"Points of interest in {destination}",
                    "lat": p["lat"],
                    "lon": p["lon"],
                    "estimated_time_hours": 2,
                    "best_time_to_visit": "morning",
                    "crowd_level": "moderate",
                    "is_verified_osm": True,
                })
        result["top_attractions"] = valid_attractions

        result["is_live_data"] = True
        result["data_source"] = "OpenStreetMap / Overpass API (Live)"
        result["api_status_message"] = None

    result["raw_osm_pois"] = pois[:20]
    result["coordinates"] = coordinates
    result["poi_count_retrieved"] = len(pois)
    result["agent"] = "local_discovery"

    # Transparency metadata block
    errors = []
    if not has_live_pois:
        errors.append("OpenStreetMap Overpass POI query returned 0 records")
    if llm_meta["is_fallback"] and llm_meta.get("error"):
        errors.append(llm_meta["error"])

    data_sources = []
    if has_live_pois:
        data_sources.append("OpenStreetMap / Overpass API")
        if not llm_meta["is_fallback"]:
            llm_label = "Google Gemini 3.5 Flash Lite" if llm_meta.get("provider_used") == "gemini" else "OpenAI GPT-4o-mini"
            data_sources.append(llm_label)
        source_type = "live_api"
    else:
        data_sources.append("Curated Regional Travel Knowledge Base")
        source_type = "curated_knowledge"

    if coordinates:
        data_sources.append("Nominatim Geocoding")

    result["metadata"] = {
        "agent_name": "local_discovery",
        "display_name": "Local Discovery Agent",
        "responsibility": "Finding authentic local dining and cultural POIs via OpenStreetMap",
        "source_type": source_type,
        "data_sources": data_sources,
        "is_fallback": (not has_live_pois) or llm_meta["is_fallback"],
        "errors": errors,
    }

    return result
