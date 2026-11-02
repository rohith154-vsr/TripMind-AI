"""
Maps Service — uses OpenStreetMap Nominatim for geocoding and
Overpass API for POI (points of interest) discovery.
"""
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from app.config import get_settings

settings = get_settings()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "TripMind-AI/1.0 (portfolio project)"}


async def geocode(location: str) -> Optional[Dict[str, Any]]:
    """Return lat, lon, display_name for a location."""
    params = {"q": location, "format": "json", "limit": 1, "addressdetails": 1}
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if data:
            item = data[0]
            address = item.get("address", {})
            return {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "display_name": item.get("display_name", location),
                "country": address.get("country", ""),
                "city": address.get("city") or address.get("town") or address.get("village") or "",
                "osm_id": item.get("osm_id"),
            }
    return None


async def find_pois(lat: float, lon: float, radius_m: int = 5000, categories: List[str] = None) -> List[Dict[str, Any]]:
    """
    Find points of interest around a location using Overpass API.
    Categories: restaurants, tourism, historic, entertainment
    """
    if categories is None:
        categories = ["tourism", "amenity=restaurant", "historic", "leisure"]

    queries = []
    for cat in categories:
        if "=" in cat:
            k, v = cat.split("=", 1)
            queries.append(f'node["{k}"="{v}"](around:{radius_m},{lat},{lon});')
            queries.append(f'way["{k}"="{v}"](around:{radius_m},{lat},{lon});')
        else:
            queries.append(f'node["{cat}"](around:{radius_m},{lat},{lon});')
            queries.append(f'way["{cat}"](around:{radius_m},{lat},{lon});')

    overpass_query = f"""
    [out:json][timeout:25];
    (
      {''.join(queries)}
    );
    out body center 50;
    """
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(OVERPASS_URL, data={"data": overpass_query})
        resp.raise_for_status()
        raw = resp.json()

    pois = []
    for el in raw.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        # Get coordinates
        if el["type"] == "node":
            plat, plon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            plat, plon = center.get("lat"), center.get("lon")

        category = _categorize(tags)
        pois.append({
            "name": name,
            "lat": plat,
            "lon": plon,
            "category": category,
            "type": tags.get("tourism") or tags.get("amenity") or tags.get("historic") or tags.get("leisure") or "point_of_interest",
            "cuisine": tags.get("cuisine"),
            "opening_hours": tags.get("opening_hours"),
            "website": tags.get("website"),
            "description": tags.get("description") or tags.get("wikipedia"),
        })

    return pois[:40]  # Limit to 40 POIs


def _categorize(tags: dict) -> str:
    if tags.get("amenity") in ["restaurant", "cafe", "bar", "fast_food", "food_court"]:
        return "food"
    if tags.get("tourism") in ["attraction", "museum", "viewpoint", "gallery", "zoo", "theme_park"]:
        return "attraction"
    if tags.get("historic"):
        return "historic"
    if tags.get("leisure") in ["park", "nature_reserve", "beach_resort", "stadium"]:
        return "leisure"
    return "other"
