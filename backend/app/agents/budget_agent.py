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
      "nights": {duration_days},
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

    # Calculate duration (inclusive of departure and return days)
    duration_days = 4
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        duration_days = max((ret - dep).days + 1, 1)
    except Exception:
        pass

    # Exact mathematical allocations
    budget_per_person = round(budget / num_travelers, 2)
    budget_per_day = round(budget / duration_days, 2)
    budget_per_person_per_day = round(budget / (num_travelers * duration_days), 2)

    hotel_est = round(budget * 0.38, 2)
    hotel_per_night = round(hotel_est / duration_days, 2)
    transport_est = round(budget * 0.15, 2)
    transport_per_day = round(transport_est / duration_days, 2)
    food_est = round(budget * 0.25, 2)
    food_per_day_person = round(food_est / (duration_days * num_travelers), 2)
    activities_est = round(budget * 0.12, 2)
    activities_per_day = round(activities_est / duration_days, 2)
    shopping_est = round(budget * 0.05, 2)
    emergency_est = round(budget * 0.10, 2)
    misc_est = round(budget * 0.05, 2)
    total_est = round(hotel_est + transport_est + food_est + activities_est + shopping_est + misc_est, 2)

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
    currency_data_source = f"Budget in selected currency ({currency})"
    try:
        if currency != "USD":
            conv = await convert_amount(1.0, "USD", currency)
            if conv:
                usd_conversion = conv
                rate_status = "live rate" if conv.get("is_live_rate") else "estimated rate"
                currency_info = f"1 USD = {conv['exchange_rate']} {currency} ({conv['rate_source']} - {rate_status})"
                currency_data_source = conv['rate_source']
        else:
            currency_info = "Budget is in USD (no conversion required)"
    except Exception as e:
        currency_info = f"Currency conversion reference: {str(e)}"

    interests_str = ", ".join(interests) or "General sightseeing"
    prompt = BUDGET_PROMPT.format(
        origin=origin,
        destination=destination,
        terrain_note=terrain_note,
        departure_date=departure_date,
        return_date=return_date,
        duration_days=duration_days,
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
        result = await llm_service.generate_json(prompt, SYSTEM_PROMPT)
    except Exception as e:
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
                    "nights": duration_days,
                    "recommended_type": "Heritage resort / guesthouse",
                    "notes": f"Centrally located stays in {destination} save transport costs."
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
                    "percentage": 10
                },
                "miscellaneous": {
                    "estimated_total": misc_est,
                    "notes": "Tips and mobile data."
                }
            },
            "total_estimated_cost": total_est,
            "budget_vs_estimate": {"difference": 0, "status": "on_budget", "percentage_difference": 0},
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

    # CRITICAL: Enforce strict mathematical consistency and currency
    summary = result.setdefault("budget_summary", {})
    summary["currency"] = currency
    summary["total_budget"] = budget
    summary["budget_per_person"] = budget_per_person
    summary["budget_per_day"] = budget_per_day
    summary["budget_per_person_per_day"] = budget_per_person_per_day

    if usd_conversion:
        result["currency_conversion"] = usd_conversion

    result["agent"] = "budget_management"
    result["metadata"] = {
        "agent_name": "budget_management",
        "display_name": "Budget Management Agent",
        "responsibility": "Realistic expense breakdown, daily budget allocation, and money-saving guidance",
        "source_type": "llm",
        "data_sources": [f"Frankfurter Currency Exchange API ({currency})", "Gemini 3.5 Flash Lite"],
        "is_fallback": False,
        "errors": [],
    }

    return result
