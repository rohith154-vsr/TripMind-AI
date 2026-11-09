"""
Budget Management Agent
Calculates trip costs, breaks down expenses, and provides cost-saving tips.
Maintains strict currency consistency, eliminates improper USD assumptions,
and enforces mathematical accuracy across total, daily, and per-person allocations.
"""
from typing import Dict, Any
from app.services.llm_service import llm_service
from app.services.currency_service import convert_amount
from app.services.knowledge_base import classify_destination

SYSTEM_PROMPT = """You are the Budget Management Agent for TripMind AI.
Your role is to provide realistic travel cost estimates, expense breakdowns, and money-saving tips.
Base your estimates on real-world travel costs in the specified local currency.
STRICT CURRENCY RULES:
1. Always use the requested currency. NEVER prepend '$' or assume USD unless the currency is USD.
2. Maintain strict mathematical consistency: total budget / duration = daily budget.
3. Tailor accommodation and transport advice to the destination's geography.
4. Respond with structured JSON only."""

BUDGET_PROMPT = """Analyze the travel budget for this trip and provide a comprehensive cost breakdown.

Trip Details:
- Origin: {origin}
- Destination: {destination} ({terrain_note})
- Departure: {departure_date}
- Return: {return_date}
- Duration: {duration_days} days (inclusive)
- Number of Travelers: {num_travelers}
- Total Budget: {budget} {currency}
- Budget per person: {budget_per_person} {currency}
- Expected Daily Budget: {budget_per_day} {currency}/day
- Expected Per-Person Daily Budget: {budget_per_person_per_day} {currency}/day/person
- Travel Style: {travel_style}
- Interests: {interests}

Currency Information:
{currency_info}

CRITICAL INSTRUCTIONS:
- All amounts in your response must be in {currency}.
- Do NOT use '$' unless currency is USD.
- Ensure expense breakdown categories sum approximately to the total budget ({budget} {currency}).

Provide a detailed budget analysis as JSON with this exact structure:
{{
  "budget_summary": {{
    "total_budget": {budget},
    "currency": "{currency}",
    "budget_per_person": {budget_per_person},
    "budget_per_day": {budget_per_day},
    "budget_per_person_per_day": {budget_per_person_per_day},
    "budget_category": "budget|mid-range|comfortable|luxury",
    "feasibility": "comfortable|tight|very_tight|generous",
    "feasibility_explanation": "Why this budget is feasible or not in {currency}"
  }},
  "expense_breakdown": {{
    "accommodation": {{
      "estimated_total": {hotel_est},
      "per_night": {hotel_per_night},
      "nights": {accommodation_nights},
      "recommended_type": "guesthouse|boutique resort|3-star hotel|homestay",
      "notes": "Accommodation recommendations tailored to {destination}"
    }},
    "flights": {{
      "estimated_total": 0,
      "per_person": 0,
      "notes": "Regional transit advice"
    }},
    "local_transport": {{
      "estimated_total": {transport_est},
      "per_day": {transport_per_day},
      "recommended_options": ["Option 1", "Option 2"]
    }},
    "food": {{
      "estimated_total": {food_est},
      "per_day_per_person": {food_per_day_person},
      "breakdown": {{
        "breakfast": {food_breakfast},
        "lunch": {food_lunch},
        "dinner": {food_dinner},
        "snacks": {food_snacks}
      }},
      "notes": "Food budget tips for regional dishes in {destination}"
    }},
    "activities_attractions": {{
      "estimated_total": {activities_est},
      "per_day": {activities_per_day},
      "notes": "Entry passes, boat rentals, and viewpoint admissions"
    }},
    "shopping_souvenirs": {{
      "estimated_total": {shopping_est},
      "notes": "Regional specialties and artisan crafts"
    }},
    "emergency_buffer": {{
      "recommended_amount": {emergency_est},
      "percentage": 10
    }},
    "miscellaneous": {{
      "estimated_total": {misc_est},
      "notes": "Tips, entry fees, mobile data, etc."
    }}
  }},
  "total_estimated_cost": {total_est},
  "budget_vs_estimate": {{
    "difference": 0,
    "status": "on_budget",
    "percentage_difference": 0
  }},
  "cost_saving_tips": [
    {{
      "tip": "Specific money-saving tip",
      "potential_savings": "Estimated savings amount in {currency}",
      "category": "accommodation|food|transport|activities"
    }}
  ],
  "splurge_recommendations": [
    {{
      "item": "Memorable experience to splurge on",
      "reason": "Why it's worth it",
      "estimated_cost": 0
    }}
  ],
  "daily_budget_guide": {{
    "budget_day": {budget_day_guide},
    "comfortable_day": {budget_per_day},
    "splurge_day": {splurge_day_guide}
  }},
  "currency_notes": "Important local payment customs (cash vs UPI vs card)",
  "financial_tips": ["Card vs cash advice in {currency}"]
}}"""


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate budget breakdown with real currency conversion."""
    from datetime import datetime

    origin = preferences["origin"]
    destination = preferences["destination"]
    departure_date = preferences.get("departure_date", "")
    return_date = preferences.get("return_date", "")
    num_travelers = max(preferences.get("num_travelers", 1), 1)
    budget = float(preferences.get("budget", 15000))
    currency = preferences.get("currency", "INR").upper()
    travel_style = preferences.get("travel_style", "Adventure")
    interests = preferences.get("interests", [])

    # Calculate duration (inclusive of departure and return days) and accommodation nights
    duration_days = 4
    accommodation_nights = 3
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d").date()
        ret = datetime.strptime(return_date, "%Y-%m-%d").date()
        duration_days = max((ret - dep).days + 1, 1)
        accommodation_nights = max((ret - dep).days, 0)
    except Exception:
        pass

    # Exact mathematical allocations
    budget_per_person = round(budget / num_travelers, 2)
    budget_per_day = round(budget / duration_days, 2)
    budget_per_person_per_day = round(budget / (num_travelers * duration_days), 2)

    if accommodation_nights > 0:
        hotel_est = round(budget * 0.38, 2)
        hotel_per_night = round(hotel_est / accommodation_nights, 2)
        food_est = round(budget * 0.24, 2)
        transport_est = round(budget * 0.14, 2)
        activities_est = round(budget * 0.10, 2)
        shopping_est = round(budget * 0.04, 2)
        emergency_est = round(budget * 0.10, 2)
    else:
        # Single-day trip (no overnight accommodation)
        hotel_est = 0.0
        hotel_per_night = 0.0
        food_est = round(budget * 0.40, 2)
        transport_est = round(budget * 0.25, 2)
        activities_est = round(budget * 0.20, 2)
        shopping_est = round(budget * 0.05, 2)
        emergency_est = round(budget * 0.10, 2)

    # Enforce that all allocations sum EXACTLY to total budget (inclusive of emergency reserve)
    current_sum = round(hotel_est + transport_est + food_est + activities_est + shopping_est + emergency_est, 2)
    diff = round(budget - current_sum, 2)
    emergency_est = round(emergency_est + diff, 2)
    total_est = round(hotel_est + transport_est + food_est + activities_est + shopping_est + emergency_est, 2)

    transport_per_day = round(transport_est / duration_days, 2)
    food_per_day_person = round(food_est / (duration_days * num_travelers), 2)
    activities_per_day = round(activities_est / duration_days, 2)
    misc_est = emergency_est

    food_breakfast = round(food_per_day_person * 0.15, 2)
    food_lunch = round(food_per_day_person * 0.35, 2)
    food_dinner = round(food_per_day_person * 0.40, 2)
    food_snacks = round(food_per_day_person * 0.10, 2)

    budget_day_guide = round(budget_per_day * 0.75, 2)
    splurge_day_guide = round(budget_per_day * 1.35, 2)

    classification = classify_destination(destination)
    terrain_note = "Highland Hill Station" if classification["is_hill_station"] else "Metropolitan / Urban" if classification["is_metropolitan"] else "Regional Destination"

    # Currency conversion info
    currency_info = ""
    usd_conversion = None
    currency_error = None
    try:
        if currency != "USD":
            conv = await convert_amount(1.0, "USD", currency)
            if conv and conv.get("exchange_rate") is not None:
                usd_conversion = conv
                rate_status = "live rate" if conv.get("is_live_rate") else "estimated rate"
                currency_info = f"1 USD = {conv['exchange_rate']} {currency} ({conv['rate_source']} - {rate_status})"
            else:
                currency_info = f"Currency conversion reference unavailable; all amounts calculated in native {currency}."
    except Exception as e:
        currency_error = str(e)
        currency_info = f"Currency conversion reference: {currency_error}"

    interests_str = ", ".join(interests) or "General sightseeing"
    prompt = BUDGET_PROMPT.format(
        origin=origin,
        destination=destination,
        terrain_note=terrain_note,
        departure_date=departure_date,
        return_date=return_date,
        duration_days=duration_days,
        accommodation_nights=accommodation_nights,
        num_travelers=num_travelers,
        budget=budget,
        currency=currency,
        budget_per_person=budget_per_person,
        budget_per_day=budget_per_day,
        budget_per_person_per_day=budget_per_person_per_day,
        travel_style=travel_style,
        interests=interests_str,
        currency_info=currency_info,
        hotel_est=hotel_est,
        hotel_per_night=hotel_per_night,
        transport_est=transport_est,
        transport_per_day=transport_per_day,
        food_est=food_est,
        food_per_day_person=food_per_day_person,
        food_breakfast=food_breakfast,
        food_lunch=food_lunch,
        food_dinner=food_dinner,
        food_snacks=food_snacks,
        activities_est=activities_est,
        activities_per_day=activities_per_day,
        shopping_est=shopping_est,
        emergency_est=emergency_est,
        misc_est=misc_est,
        total_est=total_est,
        budget_day_guide=budget_day_guide,
        splurge_day_guide=splurge_day_guide,
    )

    try:
        result, llm_meta = await llm_service.generate_json_with_provenance(prompt, SYSTEM_PROMPT)
    except Exception as e:
        llm_meta = {"provider_used": "fallback", "is_fallback": True, "error": str(e)}
        result = {
            "budget_summary": {
                "total_budget": budget,
                "currency": currency,
                "budget_per_person": budget_per_person,
                "budget_per_day": budget_per_day,
                "budget_per_person_per_day": budget_per_person_per_day,
                "budget_category": "comfortable",
                "feasibility": "comfortable",
                "feasibility_explanation": f"Budget of {currency} {budget:,.0f} ({currency} {budget_per_day:,.0f}/day) is comfortable for {destination}.",
            },
            "expense_breakdown": {
                "accommodation": {
                    "estimated_total": hotel_est,
                    "per_night": hotel_per_night,
                    "nights": accommodation_nights,
                    "recommended_type": "Heritage resort / guesthouse" if accommodation_nights > 0 else "None (Single-Day Trip)",
                    "notes": f"Centrally located stays in {destination} save transport costs." if accommodation_nights > 0 else "No accommodation required for single-day itinerary."
                },
                "local_transport": {
                    "estimated_total": transport_est,
                    "per_day": transport_per_day,
                    "recommended_options": ["Local Tourist Taxis", "Auto-rickshaws", "Scenic Walking"] if classification["is_hill_station"] else ["Local Taxis", "Public Transit", "Walking"]
                },
                "food": {
                    "estimated_total": food_est,
                    "per_day_per_person": food_per_day_person,
                    "notes": "Enjoy fresh regional dining at authentic local restaurants."
                },
                "activities_attractions": {
                    "estimated_total": activities_est,
                    "per_day": activities_per_day,
                    "notes": "Entry fees for botanical gardens and viewpoints."
                },
                "shopping_souvenirs": {
                    "estimated_total": shopping_est,
                    "notes": "Local tea, homemade chocolates, and spices."
                },
                "emergency_buffer": {
                    "recommended_amount": emergency_est,
                    "percentage": 10,
                    "is_included_in_total": True
                },
                "miscellaneous": {
                    "estimated_total": 0.0,
                    "notes": "Covered within emergency reserve and daily allowances."
                }
            },
            "total_estimated_cost": total_est,
            "budget_vs_estimate": {"difference": 0.0, "status": "on_budget", "percentage_difference": 0.0},
            "cost_saving_tips": [
                {
                    "tip": "Book a full-day tourist taxi package rather than negotiating multiple individual one-way fares.",
                    "potential_savings": f"Save ~20% in {currency}",
                    "category": "transport"
                }
            ],
            "splurge_recommendations": [],
            "daily_budget_guide": {
                "budget_day": budget_day_guide,
                "comfortable_day": budget_per_day,
                "splurge_day": splurge_day_guide
            },
            "currency_notes": f"All amounts in {currency}.",
            "financial_tips": ["UPI payments and cash are widely accepted."]
        }

    # CRITICAL: Enforce strict mathematical consistency, nights vs days, and emergency reserve inclusion
    summary = result.setdefault("budget_summary", {})
    summary["currency"] = currency
    summary["total_budget"] = budget
    summary["budget_per_person"] = budget_per_person
    summary["budget_per_day"] = budget_per_day
    summary["budget_per_person_per_day"] = budget_per_person_per_day

    eb = result.setdefault("expense_breakdown", {})
    eb.setdefault("accommodation", {})["estimated_total"] = hotel_est
    eb["accommodation"]["per_night"] = hotel_per_night
    eb["accommodation"]["nights"] = accommodation_nights
    eb.setdefault("local_transport", {})["estimated_total"] = transport_est
    eb["local_transport"]["per_day"] = transport_per_day
    eb.setdefault("food", {})["estimated_total"] = food_est
    eb["food"]["per_day_person"] = food_per_day_person
    eb.setdefault("activities_attractions", {})["estimated_total"] = activities_est
    eb["activities_attractions"]["per_day"] = activities_per_day
    eb.setdefault("shopping_souvenirs", {})["estimated_total"] = shopping_est
    eb.setdefault("emergency_buffer", {})["recommended_amount"] = emergency_est
    eb["emergency_buffer"]["percentage"] = 10
    eb["emergency_buffer"]["is_included_in_total"] = True
    if "miscellaneous" in eb:
        eb["miscellaneous"]["estimated_total"] = 0.0

    result["total_estimated_cost"] = total_est
    result["budget_vs_estimate"] = {"difference": 0.0, "status": "on_budget", "percentage_difference": 0.0}

    if usd_conversion:
        result["currency_conversion"] = usd_conversion

    result["agent"] = "budget_management"

    # Truthful provenance metadata
    data_sources = []
    if currency != "USD" and usd_conversion:
        data_sources.append(usd_conversion.get("rate_source", f"Frankfurter Currency Exchange API ({currency})"))
    elif currency == "USD":
        data_sources.append("Standard USD Reference (No Conversion Required)")
    else:
        data_sources.append(f"Standard Currency Baseline ({currency})")

    if not llm_meta["is_fallback"]:
        llm_label = "Google Gemini 3.5 Flash Lite" if llm_meta.get("provider_used") == "gemini" else "OpenAI GPT-4o-mini"
        data_sources.append(llm_label)
        source_type = "hybrid" if (usd_conversion and usd_conversion.get("is_live_rate")) else "llm"
        is_fallback = False
    else:
        data_sources.append("Curated Regional Budget Model (Fallback)")
        source_type = "live_api" if (usd_conversion and usd_conversion.get("is_live_rate")) else "curated_knowledge"
        is_fallback = True

    errors = []
    if currency_error:
        errors.append(currency_error)
    if llm_meta["is_fallback"] and llm_meta.get("error"):
        errors.append(llm_meta["error"])

    result["metadata"] = {
        "agent_name": "budget_management",
        "display_name": "Budget Management Agent",
        "responsibility": "Realistic expense breakdown, daily budget allocation, and money-saving guidance",
        "source_type": source_type,
        "data_sources": data_sources,
        "is_fallback": is_fallback,
        "errors": errors,
    }

    return result
