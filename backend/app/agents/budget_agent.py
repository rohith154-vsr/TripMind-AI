"""
Budget Management Agent
Calculates trip costs, breaks down expenses, and provides cost-saving tips.
Uses Frankfurter API for real currency conversion.
"""
from typing import Dict, Any
from app.services.llm_service import llm_service
from app.services.currency_service import convert_amount

SYSTEM_PROMPT = """You are the Budget Management Agent for TripMind AI.
Your role is to provide realistic travel cost estimates, expense breakdowns, and money-saving tips.
Base your estimates on real-world travel costs. Be honest about uncertainty.
Respond with structured JSON only. Never use placeholder values."""

BUDGET_PROMPT = """Analyze the travel budget for this trip and provide a comprehensive cost breakdown.

Trip Details:
- Origin: {origin}
- Destination: {destination}
- Departure: {departure_date}
- Return: {return_date}
- Duration: {duration_days} days
- Number of Travelers: {num_travelers}
- Total Budget: {budget} {currency}
- Budget per person: {budget_per_person} {currency}
- Travel Style: {travel_style}
- Interests: {interests}

Currency Information:
{currency_info}

Provide a detailed budget analysis as JSON with this exact structure:
{{
  "budget_summary": {{
    "total_budget": {budget},
    "currency": "{currency}",
    "budget_per_person": {budget_per_person},
    "budget_per_day": 0,
    "budget_per_person_per_day": 0,
    "budget_category": "budget|mid-range|comfortable|luxury",
    "feasibility": "comfortable|tight|very_tight|generous",
    "feasibility_explanation": "Why this budget is feasible or not"
  }},
  "expense_breakdown": {{
    "accommodation": {{
      "estimated_total": 0,
      "per_night": 0,
      "nights": {duration_days},
      "recommended_type": "hostel|guesthouse|3-star hotel|4-star hotel|5-star hotel",
      "notes": "Accommodation recommendations"
    }},
    "flights": {{
      "estimated_total": 0,
      "per_person": 0,
      "notes": "Flight cost estimate and tips"
    }},
    "local_transport": {{
      "estimated_total": 0,
      "per_day": 0,
      "recommended_options": ["Option 1", "Option 2"]
    }},
    "food": {{
      "estimated_total": 0,
      "per_day_per_person": 0,
      "breakdown": {{
        "breakfast": 0,
        "lunch": 0,
        "dinner": 0,
        "snacks": 0
      }},
      "notes": "Food budget tips"
    }},
    "activities_attractions": {{
      "estimated_total": 0,
      "per_day": 0,
      "notes": "Activity cost estimates"
    }},
    "shopping_souvenirs": {{
      "estimated_total": 0,
      "notes": "Shopping budget"
    }},
    "emergency_buffer": {{
      "recommended_amount": 0,
      "percentage": 10
    }},
    "miscellaneous": {{
      "estimated_total": 0,
      "notes": "Tips, entry fees, sim card, etc."
    }}
  }},
  "total_estimated_cost": 0,
  "budget_vs_estimate": {{
    "difference": 0,
    "status": "under_budget|over_budget|on_budget",
    "percentage_difference": 0
  }},
  "cost_saving_tips": [
    {{
      "tip": "Specific money-saving tip",
      "potential_savings": "Estimated savings amount",
      "category": "accommodation|food|transport|activities"
    }}
  ],
  "splurge_recommendations": [
    {{
      "item": "What to splurge on",
      "reason": "Why it's worth it",
      "estimated_cost": 0
    }}
  ],
  "daily_budget_guide": {{
    "budget_day": 0,
    "comfortable_day": 0,
    "splurge_day": 0
  }},
  "currency_notes": "Any important currency exchange info",
  "financial_tips": ["Travel insurance recommendation", "Card vs cash advice"]
}}

All amounts should be in {currency}. Be realistic based on actual costs in {destination}."""


async def run(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate budget breakdown with real currency conversion."""
    from datetime import datetime

    origin = preferences["origin"]
    destination = preferences["destination"]
    departure_date = preferences.get("departure_date", "")
    return_date = preferences.get("return_date", "")
    num_travelers = preferences.get("num_travelers", 1)
    budget = preferences.get("budget", 1000)
    currency = preferences.get("currency", "USD").upper()
    travel_style = preferences.get("travel_style", "Adventure")
    interests = preferences.get("interests", [])

    # Calculate duration
    duration_days = 7
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
        duration_days = max((ret - dep).days, 1)
    except Exception:
        pass

    budget_per_person = round(budget / max(num_travelers, 1), 2)

    # Get real currency info
    currency_info = ""
    usd_conversion = None
    try:
        if currency != "USD":
            conv = await convert_amount(1.0, "USD", currency)
            if conv:
                usd_conversion = conv
                currency_info = f"1 USD = {conv['exchange_rate']} {currency} (live rate from Frankfurter API)"
        else:
            currency_info = "Budget is in USD"
    except Exception as e:
        currency_info = f"Currency conversion unavailable: {str(e)}"

    interests_str = ", ".join(interests) or "General sightseeing"
    prompt = BUDGET_PROMPT.format(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        duration_days=duration_days,
        num_travelers=num_travelers,
        budget=budget,
        budget_per_person=budget_per_person,
        currency=currency,
        travel_style=travel_style,
        interests=interests_str,
        currency_info=currency_info,
    )

    try:
        result = await llm_service.generate_json(prompt, SYSTEM_PROMPT)
    except Exception as e:
        result = {
            "budget_summary": {
                "total_budget": budget,
                "currency": currency,
                "budget_per_person": budget_per_person,
                "feasibility": "unknown",
                "feasibility_explanation": f"Budget analysis unavailable: {str(e)}",
            },
            "expense_breakdown": {},
            "cost_saving_tips": [],
        }

    result["currency_conversion"] = usd_conversion
    result["trip_duration_days"] = duration_days
    result["agent"] = "budget_management"
    return result
