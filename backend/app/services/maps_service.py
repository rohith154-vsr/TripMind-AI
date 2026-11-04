"""
Maps Service — uses OpenStreetMap Nominatim for geocoding and
Overpass API for POI (points of interest) discovery with multi-server failover,
in-memory caching, strict validation, and zero synthetic POI generation.
"""
import time
import httpx
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from app.config import get_settings

settings = get_settings()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {
    "User-Agent": "TripMind-AI/1.0 (portfolio project; travel-planner)",
    "Content-Type": "application/x-www-form-urlencoded",
}

# In-memory caches to respect OSM fair-use policies and accelerate responses
_GEOCODE_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}
_POI_CACHE: Dict[Tuple[float, float, int], Tuple[List[Dict[str, Any]], float]] = {}
CACHE_TTL = 86400  # 24 hours


async def geocode(location: str) -> Optional[Dict[str, Any]]:
    """
    Return lat, lon, display_name for a location.
    Caches geocoding results to adhere to Nominatim's 1-request/second usage policy.
    """
    cleaned_loc = location.strip().lower()
    now = time.time()

    if cleaned_loc in _GEOCODE_CACHE:
        cached_data, timestamp = _GEOCODE_CACHE[cleaned_loc]
        if now - timestamp < CACHE_TTL:
            return cached_data

    params = {"q": location, "format": "json", "limit": 1, "addressdetails": 1}
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.get(NOMINATIM_URL, params=params, headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    item = data[0]
                    address = item.get("address", {})
                    lat_val = float(item["lat"])
                    lon_val = float(item["lon"])
                    result = {
                        "lat": lat_val,
                        "lon": lon_val,
                        "display_name": item.get("display_name", location),
                        "country": address.get("country", ""),
                        "city": address.get("city") or address.get("town") or address.get("village") or "",
                        "osm_id": item.get("osm_id"),
                        "is_live_geocoded": True,
                    }
                    _GEOCODE_CACHE[cleaned_loc] = (result, now)
                    return result
    except Exception:
        pass

    return None


async def find_pois(lat: float, lon: float, radius_m: int = 5000, categories: List[str] = None) -> List[Dict[str, Any]]:
    """
    Find authentic points of interest around a location using Overpass API with server failover.
    Ensures every returned item has verified real coordinates and names from OpenStreetMap.
    """
    if abs(lat) < 0.0001 and abs(lon) < 0.0001:
        # Invalid coordinates guard
        return []

    cache_key = (round(lat, 3), round(lon, 3), radius_m)
    now = time.time()
    if cache_key in _POI_CACHE:
        cached_pois, timestamp = _POI_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return cached_pois

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
    [out:json][timeout:15];
    (
      {''.join(queries)}
    );
    out body center 40;
    """

    raw_elements = []
    for server_url in OVERPASS_SERVERS:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(server_url, data={"data": overpass_query}, headers=HEADERS)
                if resp.status_code == 200:
                    raw = resp.json()
                    raw_elements = raw.get("elements", [])
                    if raw_elements:
                        break
        except Exception:
            continue

    pois = []
    for el in raw_elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or not name.strip():
            continue

        # Get coordinates
        if el.get("type") == "node":
            plat, plon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            plat, plon = center.get("lat"), center.get("lon")

        if plat is None or plon is None:
            continue
        try:
            plat_f = float(plat)
            plon_f = float(plon)
            if abs(plat_f) < 0.0001 and abs(plon_f) < 0.0001:
                continue
        except (ValueError, TypeError):
            continue

        category = _categorize(tags)
        pois.append({
            "name": name.strip(),
            "lat": plat_f,
            "lon": plon_f,
            "category": category,
            "type": tags.get("tourism") or tags.get("amenity") or tags.get("historic") or tags.get("leisure") or "point_of_interest",
            "cuisine": tags.get("cuisine"),
            "opening_hours": tags.get("opening_hours"),
            "website": tags.get("website"),
            "description": tags.get("description") or tags.get("wikipedia"),
            "is_verified_osm": True,
            "osm_source": "OpenStreetMap / Overpass API",
        })

    if pois:
        _POI_CACHE[cache_key] = (pois[:40], now)

    return pois[:40]


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
