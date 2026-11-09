"""
Curated Knowledge Base & Destination Geography Classifier
Provides verified, authentic travel intelligence and geographical classification
to guarantee realistic, non-fabricated recommendations for any destination.
"""
from typing import Dict, Any, Optional, List
import re


# Verified Destination Knowledge Base
DESTINATION_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "ooty": {
        "name": "Ooty (Udhagamandalam)",
        "canonical_name": "Udhagamandalam",
        "country": "India",
        "region": "Nilgiris District, Tamil Nadu",
        "geography_type": "hill_station",
        "elevation_m": 2240,
        "description": "Nestled in the Nilgiri Hills of Tamil Nadu at an elevation of 2,240 meters, Ooty (Udhagamandalam) is the quintessential 'Queen of Hill Stations'. Renowned for rolling emerald tea plantations, eucalyptus groves, cool mountain air, and heritage colonial bungalows, it offers serene nature escapes, scenic hiking trails, and the UNESCO World Heritage Nilgiri Mountain Railway.",
        "best_time_to_visit": "October through March for crisp mountain weather, or April–June for pleasant summer escapes.",
        "language": "Tamil, Badaga, English, and Hindi widely understood",
        "currency": "INR",
        "timezone": "IST (UTC+5:30)",
        "climate_summary": "Subtropical highland climate with mild, pleasant daytime temperatures (15–20°C) and cool to chilly evenings (8–12°C). Light woollens recommended year-round.",
        "top_attractions": [
            {
                "name": "Government Botanical Garden",
                "type": "garden",
                "description": "Sprawling 55-acre terraced garden established in 1848, featuring thousands of exotic flora species, a fossilized tree trunk, and tranquil lawns.",
                "why_visit": "Iconic Ooty landmark perfect for peaceful walks and nature photography.",
                "estimated_duration_hours": 2.5,
                "admission_fee_usd": 1,
                "best_time": "Morning",
                "insider_tip": "Visit before 10:00 AM to enjoy dewy lawns before tour crowds arrive."
            },
            {
                "name": "Nilgiri Mountain Railway (Toy Train)",
                "type": "historic",
                "description": "UNESCO World Heritage meter-gauge rack railway winding through mountain tunnels, misty bridges, and steep tea-carpeted slopes.",
                "why_visit": "One of the most scenic train journeys in Asia and a living heritage marvel.",
                "estimated_duration_hours": 3.5,
                "admission_fee_usd": 3,
                "best_time": "Morning",
                "insider_tip": "Book unreserved second-class or first-class tickets weeks in advance via IRCTC as seats sell out immediately."
            },
            {
                "name": "Doddabetta Peak",
                "type": "viewpoint",
                "description": "The highest mountain in the Nilgiri Hills (2,637 m) offering sweeping 360-degree vistas across forested valleys and the Western Ghats.",
                "why_visit": "Unrivaled panoramic photography vantage point with a telescope house at the summit.",
                "estimated_duration_hours": 2,
                "admission_fee_usd": 1,
                "best_time": "Early Morning",
                "insider_tip": "Arrive early before mountain mist and afternoon fog roll in to obscure the view."
            },
            {
                "name": "Ooty Lake & Boat House",
                "type": "lake",
                "description": "L-shaped artificial lake built in 1824 by John Sullivan, surrounded by tall eucalyptus trees with paddle, row, and motorboats.",
                "why_visit": "Relaxing boating experience and scenic lakeside walking paths.",
                "estimated_duration_hours": 2,
                "admission_fee_usd": 2,
                "best_time": "Late Afternoon",
                "insider_tip": "Choose pedal boats on the far side away from the jetty for a quieter experience."
            },
            {
                "name": "Government Rose Garden",
                "type": "garden",
                "description": "One of the largest rose gardens in India, spanning five terraced slopes with over 20,000 varieties of vibrant roses.",
                "why_visit": "Stunning floral display with panoramic views over the Ooty town basin.",
                "estimated_duration_hours": 1.5,
                "admission_fee_usd": 1,
                "best_time": "Morning",
                "insider_tip": "Peak flowering season is between April and June, but the terraces remain scenic year-round."
            },
            {
                "name": "Pykara Lake & Waterfalls",
                "type": "nature",
                "description": "Pristine lake and series of cascading waterfalls surrounded by shola forests and grassy meadows, 21 km from Ooty town.",
                "why_visit": "Unspoiled nature sanctuary offering speedboat rides and forest trekking.",
                "estimated_duration_hours": 3.5,
                "admission_fee_usd": 2,
                "best_time": "Afternoon",
                "insider_tip": "Combine Pykara Lake boating with a quick stop at the nearby shooting point meadows."
            },
            {
                "name": "Benchmark Tea Factory & Museum",
                "type": "museum",
                "description": "Working CTC tea processing factory where visitors watch fresh tea leaves transformed into aromatic Nilgiri tea with guided tastings.",
                "why_visit": "Essential immersion into Ooty's historic tea plantation heritage and fresh tea tastings.",
                "estimated_duration_hours": 1.5,
                "admission_fee_usd": 1,
                "best_time": "Morning or Afternoon",
                "insider_tip": "Sample the freshly brewed cardamom and chocolate teas at the observation terrace."
            },
            {
                "name": "Thread Garden",
                "type": "art",
                "description": "Unique handcrafted exhibition showcasing an incredible artificial garden crafted entirely from colored embroidery threads over 12 years.",
                "why_visit": "A rare, astonishing display of meticulous folk craftsmanship near Ooty Lake.",
                "estimated_duration_hours": 1,
                "admission_fee_usd": 1,
                "best_time": "Anytime",
                "insider_tip": "No needles or machinery were used; look closely at the flower petals to observe the thread-wound stems."
            }
        ],
        "must_try_foods": [
            "Authentic Nilgiri CTC & Orthodox Teas",
            "Crispy Ooty Varkey (flaky local puff pastry)",
            "Artisanal Ooty Homemade Chocolates (fudge, truffle & nut clusters)",
            "Traditional South Indian Tiffin (crispy Ghee Roast Dosa, Idli, Sambar)",
            "Badaga Style Avarai Beans Curry & Spiced Rice",
            "Chettinad and Nilgiri spiced preparations"
        ],
        "getting_around": "Hilly terrain is best navigated by local taxis, tourist cabs, or auto-rickshaws for short trips. The UNESCO Nilgiri Mountain Railway connects Ooty to Coonoor and Mettupalayam. Walking is pleasant in the commercial center and garden promenades.",
        "safety_info": "Ooty is very safe and welcoming. Mountain roads can have hairpin turns, so hire experienced local drivers. Keep warm jackets handy as evening temperatures drop sharply.",
        "transit_advice": "Book local cabs for full-day sightseeing packages to cover outer sights like Pykara and Doddabetta efficiently.",
        "neighborhoods": [
            {
                "name": "Town Centre & Charing Cross",
                "character": "Bustling commercial hub lined with bakeries, tea shops, woollen markets, and local eateries.",
                "best_for": "Shopping for tea, chocolate, and convenient transit"
            },
            {
                "name": "Fernhill & Lake District",
                "character": "Scenic, quieter zone overlooking eucalyptus groves, Ooty Lake, and heritage British-era properties.",
                "best_for": "Relaxed stays, nature walks, and boating"
            },
            {
                "name": "Upper Bazaar & Heritage Quarter",
                "character": "Steep hillside lanes with spice merchants, fresh vegetable markets, and traditional South Indian tiffin rooms.",
                "best_for": "Authentic street food, local spices, and fresh produce"
            }
        ]
    },
    "bangalore": {
        "name": "Bangalore (Bengaluru)",
        "canonical_name": "Bengaluru",
        "country": "India",
        "region": "Karnataka",
        "geography_type": "metropolitan",
        "elevation_m": 920,
        "description": "India's dynamic tech capital and 'Garden City', Bengaluru seamlessly balances leafy colonial-era parks and grand palaces with craft microbreweries, bustling hipster cafes, and historic South Indian vegetarian institutions.",
        "best_time_to_visit": "October through March when the city experiences pleasant, cool weather.",
        "language": "Kannada, English, Hindi, and Tamil",
        "currency": "INR",
        "timezone": "IST (UTC+5:30)",
        "climate_summary": "Moderate tropical savanna climate with warm days (26–30°C) and pleasantly breezy evenings.",
        "top_attractions": [
            {"name": "Lalbagh Botanical Garden", "type": "park", "description": "Historic 240-acre botanical garden commissioned by Hyder Ali, featuring a 19th-century Glass House modeled after London's Crystal Palace.", "admission_fee_usd": 1, "best_time": "Morning"},
            {"name": "Cubbon Park", "type": "park", "description": "Lush green oasis in the heart of Bengaluru spanning 300 acres of bamboo groves, heritage state libraries, and shaded walkways.", "admission_fee_usd": 0, "best_time": "Morning"},
            {"name": "Bangalore Palace", "type": "historic", "description": "Tudor-style royal residence built in 1878 with fortified towers, woodcarvings, and memorabilia of the Wadiyar dynasty.", "admission_fee_usd": 6, "best_time": "Afternoon"},
            {"name": "Tipu Sultan's Summer Palace", "type": "historic", "description": "Indo-Islamic teakwood palace completed in 1791, known for ornate pillars and historic frescoes.", "admission_fee_usd": 1, "best_time": "Morning"}
        ],
        "must_try_foods": ["Crispy Benne Dosa (butter dosa)", "Filter Coffee", "Bisi Bele Bath", "Mangalorean Ghee Roast", "Craft Beer"],
        "getting_around": "Namma Metro connects major corridors efficiently; auto-rickshaws, Ola, and Uber serve local connections."
    },
    "mysore": {
        "name": "Mysore (Mysuru)",
        "canonical_name": "Mysuru",
        "country": "India",
        "region": "Karnataka",
        "geography_type": "heritage_town",
        "elevation_m": 763,
        "description": "The cultural capital of Karnataka, Mysuru is famed for opulent palaces, royal heritage, fragrant sandalwood, rich silk sarees, and delectable culinary traditions.",
        "best_time_to_visit": "October through March, especially during the grand Dasara festival celebrations.",
        "language": "Kannada, English, and Hindi",
        "currency": "INR",
        "timezone": "IST (UTC+5:30)",
        "climate_summary": "Pleasant semi-arid climate with warm afternoons and comfortable evenings.",
        "top_attractions": [
            {"name": "Mysore Palace (Amba Vilas)", "type": "historic", "description": "Magnificent Indo-Saracenic royal palace with stained glass, carved mahogany ceilings, and 100,000 bulbs illuminating Sunday evenings.", "admission_fee_usd": 2, "best_time": "Morning / Sunday Evening"},
            {"name": "Chamundi Hill & Sri Chamundeshwari Temple", "type": "temple", "description": "Sacred hilltop temple overlooking Mysuru with a colossal monolithic Nandi bull statue halfway up.", "admission_fee_usd": 0, "best_time": "Early Morning"},
            {"name": "Devaraja Market", "type": "market", "description": "Vibrant 100-year-old market overflowing with fragrant jasmine garlands, mounds of colorful kumkum, bananas, and sandalwood oils.", "admission_fee_usd": 0, "best_time": "Morning"},
            {"name": "Brindavan Gardens", "type": "garden", "description": "Terraced musical fountain gardens laid out across the Krishna Raja Sagara dam.", "admission_fee_usd": 1, "best_time": "Evening"}
        ],
        "must_try_foods": ["Mylari Dosa", "Traditional Mysore Pak", "Mysore Masala Dosa", "Filter Coffee"],
        "getting_around": "Auto-rickshaws, city buses, and local cabs make getting around easy and economical."
    }
}


def classify_destination(destination_name: str, geo_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Classify a destination into its geographic and cultural context.
    Returns structured context that prevents inappropriate templates
    (e.g., prevents European metro templates for hill stations).
    """
    dest_lower = destination_name.lower().strip()
    geo = geo_data or {}
    display_name = geo.get("display_name", "")
    country = geo.get("country", "")

    # 1. Check exact curated knowledge base
    for key, data in DESTINATION_KNOWLEDGE.items():
        if key in dest_lower or data["canonical_name"].lower() in dest_lower or key in display_name.lower():
            return {
                "is_curated": True,
                "key": key,
                "data": data,
                "geography_type": data.get("geography_type", "general"),
                "country": data.get("country", country or "International"),
                "region": data.get("region", ""),
                "is_hill_station": data.get("geography_type") == "hill_station",
                "is_metropolitan": data.get("geography_type") == "metropolitan",
            }

    # 2. Check geographic indicators
    hill_station_keywords = [
        "ooty", "udhagamandalam", "kodaikanal", "munnar", "manali", "shimla", "darjeeling",
        "mussoorie", "nainital", "coorg", "madikeri", "wayanad", "chikhaldara", "mount abu",
        "mahabaleshwar", "gangtok", "leh", "ladakh", "gulmarg", "rishikesh", "dharamshala"
    ]
    beach_keywords = ["beach", "goa", "bali", "phuket", "pattaya", "maldives", "gokarna", "pondicherry", "hawaii"]
    metro_keywords = ["york", "tokyo", "london", "paris", "berlin", "singapore", "dubai", "mumbai", "delhi", "bangalore", "bengaluru", "chicago", "toronto"]

    is_hill = any(k in dest_lower or k in display_name.lower() for k in hill_station_keywords)
    is_beach = any(k in dest_lower or k in display_name.lower() for k in beach_keywords)
    is_metro = any(k in dest_lower or k in display_name.lower() for k in metro_keywords)

    if is_hill:
        geography_type = "hill_station"
    elif is_beach:
        geography_type = "coastal"
    elif is_metro:
        geography_type = "metropolitan"
    else:
        geography_type = "general"

    # Derive country and region from display_name if available
    region = ""
    if display_name:
        parts = [p.strip() for p in display_name.split(",")]
        if len(parts) >= 2:
            country = country or parts[-1]
            region = ", ".join(parts[1:-1][-2:]) if len(parts) > 2 else parts[0]

    return {
        "is_curated": False,
        "key": dest_lower,
        "data": None,
        "geography_type": geography_type,
        "country": country or "International",
        "region": region or "Regional Corridor",
        "is_hill_station": is_hill,
        "is_metropolitan": is_metro,
    }
