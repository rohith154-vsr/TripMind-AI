"""
Destination Research Agent
Researches the destination, identifies attractions, and recommends places based on user preferences.
Enforces strict geographical accuracy, destination classification, and zero fake venue fabrication.
"""
from typing import Dict, Any
from app.services.llm_service import llm_service
from app.services.maps_service import geocode
from app.services.knowledge_base import classify_destination

SYSTEM_PROMPT = """You are the Destination Research Agent for TripMind AI, a specialized travel intelligence system.
Your role is to research travel destinations thoroughly and provide accurate, geographically authentic information.
CRITICAL INTEGRITY RULES:
1. Accurately identify the destination's country, state, region, and terrain (hill station, coastal, metropolitan, etc.).
2. Never assume metropolitan infrastructure (subways, metro, trams) for hill stations, small towns, or rural destinations.
3. Tailor transportation (e.g. mountain railways, local taxis, auto-rickshaws) and regional food culture to the real location.
4. Always respond with structured JSON. Never fabricate fake attractions or coordinates.
5. If you are unsure of specific facts, provide verified regional guidance instead of inventing place names."""

AGENT_PROMPT_TEMPLATE = """Research the travel destination for a trip with these preferences:

- Origin: {origin}
- Destination: {destination}
- Geographic Context: {geo_context}
- Travel Style: {travel_style}
- Interests: {interests}
- Number of Travelers: {num_travelers}
- Travel Dates: {departure_date} to {return_date}

Provide a comprehensive destination research report as JSON with this exact structure:
{{
  "destination_overview": {{
    "name": "Full destination name",
    "country": "Accurate country name",
    "region": "Accurate region/state/district",
    "description": "2-3 paragraph overview capturing the authentic geography, terrain, and culture",
    "best_time_to_visit": "When is the best time to visit",
    "language": "Primary language spoken",
    "currency": "Local currency name and code",
    "timezone": "Timezone info",
    "climate_summary": "Brief climate description for the travel period"
  }},
  "top_attractions": [
    {{
      "name": "Real attraction name",
      "type": "museum|park|landmark|beach|temple|garden|viewpoint|lake|market",
      "description": "2-3 sentence description",
      "why_visit": "Why this matches the traveler's interests",
      "estimated_duration_hours": 2,
      "admission_fee": 50,
      "admission_fee_currency": "INR",
      "admission_fee_usd": 1,
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
      "name": "Neighborhood or quarter name",
      "character": "Brief character description",
      "best_for": "What it's best for"
    }}
  ],
  "cultural_tips": ["tip1", "tip2", "tip3"],
  "safety_info": "General safety information for the destination",
  "getting_around": "Realistic transportation options suited to the actual terrain",
  "must_try_foods": ["food1", "food2", "food3"],
  "research_confidence": "high|medium|low",
  "data_notes": "Any caveats or notes about the information provided"
}}

Include at least 6 real attractions and 4 activities tailored to {travel_style} travelers interested in {interests}.
Focus strictly on genuine, well-known places. Do not invent places or fabricate European templates for non-European destinations."""


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Execute destination research for the given preferences."""
    destination = preferences["destination"]

    # 1. Geocode destination to obtain country, state, region
    geo_data = None
    geo_context = "International"
    try:
        geo_data = await geocode(destination)
        if geo_data:
            geo_context = f"{geo_data.get('city') or destination}, {geo_data.get('state') or geo_data.get('county') or ''}, {geo_data.get('country', '')}".strip(", ")
    except Exception as e:
        geo_data = {"error": str(e)}

    # 2. Check destination classification
    classification = classify_destination(destination, geo_data)
    if classification["is_curated"]:
        curated_info = classification["data"]
        geo_context = f"{curated_info['name']}, {curated_info['region']}, {curated_info['country']} ({curated_info.get('geography_type', '')})"

    # 3. Build prompt
    interests_str = ", ".join(preferences.get("interests", [])) or "General sightseeing"
    prompt = AGENT_PROMPT_TEMPLATE.format(
        origin=preferences["origin"],
        destination=destination,
        geo_context=geo_context,
        travel_style=preferences.get("travel_style", "Adventure"),
        interests=interests_str,
        num_travelers=preferences.get("num_travelers", 1),
        departure_date=preferences.get("departure_date", ""),
        return_date=preferences.get("return_date", ""),
    )

    result, llm_meta = await llm_service.generate_json_with_provenance(prompt, SYSTEM_PROMPT)

    # Attach coordinates
    if geo_data and "error" not in geo_data:
        result["coordinates"] = {
            "lat": geo_data["lat"],
            "lon": geo_data["lon"],
            "display_name": geo_data["display_name"],
        }
    else:
        result["coordinates"] = None

    is_curated = classification["is_curated"]
    is_fallback = llm_meta["is_fallback"]

    errors = []
    if geo_data and "error" in geo_data:
        errors.append(geo_data["error"])
    if is_fallback and llm_meta.get("error"):
        errors.append(llm_meta["error"])

    data_sources = ["Nominatim Geocoding"]
    if is_fallback:
        source_type = "curated_knowledge" if is_curated else "fallback"
        if is_curated:
            data_sources.append("Curated Regional Travel Knowledge Base")
        else:
            data_sources.append("Curated Regional Travel Intelligence (Fallback Engine)")
    else:
        source_type = "llm"
        llm_label = "Google Gemini 3.5 Flash Lite" if llm_meta.get("provider_used") == "gemini" else "OpenAI GPT-4o-mini"
        data_sources.append(llm_label)

    result["metadata"] = {
        "agent_name": "destination_research",
        "display_name": "Destination Research Agent",
        "responsibility": "Destination research, attraction analysis, and regional cultural orientation",
        "source_type": source_type,
        "data_sources": data_sources,
        "is_fallback": is_fallback,
        "errors": errors,
    }

    result["agent"] = "destination_research"
    return result
