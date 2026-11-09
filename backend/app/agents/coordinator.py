"""
Travel Coordinator Agent — Central Orchestrator
Manages all specialized agents, handles execution, collects results, and synthesizes the final plan.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.trip import Trip, AgentStatus
from app.services.llm_service import llm_service
from app.agents import (
    destination_agent,
    weather_agent,
    local_discovery_agent,
    budget_agent,
    itinerary_agent,
)

SYSTEM_PROMPT = """You are the Travel Coordinator Agent for TripMind AI.
Your role is to synthesize outputs from multiple specialized agents into a cohesive, 
comprehensive travel plan. Identify conflicts, fill gaps, and create a unified narrative.
Always prioritize accuracy over completeness — clearly mark any uncertain information.
Respond with structured JSON only."""

SYNTHESIS_PROMPT = """Synthesize the outputs from all specialized travel agents into a final, 
comprehensive travel plan.

User Preferences:
{preferences}

Agent Outputs Summary:
- Destination Research: {has_destination}
- Weather Intelligence: {has_weather}
- Local Discovery: {has_local}
- Budget Management: {has_budget}
- Itinerary Planning: {has_itinerary}

Create a final coordinated travel plan as JSON:
{{
  "trip_title": "Descriptive trip title",
  "executive_summary": "3-4 sentence summary of the complete trip",
  "destination_name": "Full destination name",
  "trip_highlights": ["Highlight 1", "Highlight 2", "Highlight 3", "Highlight 4", "Highlight 5"],
  "key_recommendations": [
    {{
      "category": "accommodation|transport|food|activity|safety",
      "recommendation": "Specific recommendation",
      "priority": "must|should|nice_to_have"
    }}
  ],
  "conflicts_identified": [
    {{
      "type": "weather|budget|time",
      "description": "Conflict description",
      "resolution": "How it was resolved"
    }}
  ],
  "data_quality": {{
    "agents_successful": {agents_successful},
    "agents_failed": {agents_failed},
    "missing_data": ["List of data that couldn't be retrieved"],
    "confidence_level": "high|medium|low"
  }},
  "travel_readiness_checklist": [
    {{
      "item": "Checklist item",
      "category": "documents|health|money|clothing|booking",
      "priority": "essential|recommended|optional"
    }}
  ],
  "final_tips": [
    "Final practical tip for the traveler"
  ]
}}"""


AGENT_CONFIGS = [
    {
        "name": "destination_research",
        "display_name": "Destination Research Agent",
        "description": "Researching destination, attractions, and activities",
        "module": destination_agent,
    },
    {
        "name": "weather_intelligence",
        "display_name": "Weather Intelligence Agent",
        "description": "Fetching real weather forecasts from Open-Meteo",
        "module": weather_agent,
    },
    {
        "name": "local_discovery",
        "display_name": "Local Discovery Agent",
        "description": "Finding restaurants and attractions via OpenStreetMap",
        "module": local_discovery_agent,
    },
    {
        "name": "budget_management",
        "display_name": "Budget Management Agent",
        "description": "Calculating costs and currency conversions",
        "module": budget_agent,
    },
]


async def _update_agent_status(
    trip_id: str,
    agent_name: str,
    status: str,
    message: str = "",
    result: dict = None,
):
    """Update agent status in database using an isolated short-lived session."""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result_obj = await db.execute(
            select(AgentStatus).where(
                AgentStatus.trip_id == trip_id,
                AgentStatus.agent_name == agent_name,
            )
        )
        agent_status = result_obj.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if agent_status:
            agent_status.status = status
            agent_status.message = message
            if status == "running" and not agent_status.started_at:
                agent_status.started_at = now
            if status in ("completed", "failed"):
                agent_status.completed_at = now
            if result is not None:
                agent_status.result_json = json.dumps(result)
        else:
            agent_status = AgentStatus(
                trip_id=trip_id,
                agent_name=agent_name,
                status=status,
                message=message,
                result_json=json.dumps(result or {}),
                started_at=now if status == "running" else None,
                completed_at=now if status in ("completed", "failed") else None,
            )
            db.add(agent_status)

        await db.commit()


async def _run_agent_safe(
    config: dict,
    preferences: dict,
    trip_id: str,
    extra_kwargs: dict = None,
) -> Dict[str, Any]:
    """Run a single agent with error handling, timing, and status updates."""
    name = config["name"]
    start_time = datetime.now(timezone.utc)
    try:
        await _update_agent_status(trip_id, name, "running", config["description"])

        kwargs = {"preferences": preferences}
        if extra_kwargs:
            kwargs.update(extra_kwargs)

        if name == "itinerary_planning":
            result = await config["module"].run(preferences=preferences, **extra_kwargs or {})
        else:
            result = await config["module"].run(preferences)

        duration = round((datetime.now(timezone.utc) - start_time).total_seconds(), 2)
        if isinstance(result, dict) and "metadata" in result:
            result["metadata"]["execution_duration_sec"] = duration

        await _update_agent_status(trip_id, name, "completed", "Completed successfully", result)
        return result
    except Exception as e:
        duration = round((datetime.now(timezone.utc) - start_time).total_seconds(), 2)
        error_msg = f"Agent failed: {str(e)}"
        error_result = {
            "error": error_msg,
            "agent": name,
            "metadata": {
                "agent_name": name,
                "display_name": config.get("display_name", name),
                "responsibility": config.get("description", ""),
                "source_type": "failed",
                "data_sources": [],
                "is_fallback": True,
                "execution_duration_sec": duration,
                "errors": [error_msg],
            }
        }
        await _update_agent_status(trip_id, name, "failed", error_msg, error_result)
        return error_result


async def orchestrate(
    preferences: Dict[str, Any],
    trip_id: str,
    db: AsyncSession = None,
) -> Dict[str, Any]:
    """
    Main orchestration workflow:
    1. Initialize all agent statuses as 'waiting'
    2. Run first 4 agents concurrently
    3. Run itinerary agent with other agents' outputs
    4. Coordinator synthesizes everything
    5. Save final result to DB
    """
    # Step 1: Initialize all agent statuses
    all_agent_names = [c["name"] for c in AGENT_CONFIGS] + ["itinerary_planning", "travel_coordinator"]
    for name in all_agent_names:
        await _update_agent_status(trip_id, name, "waiting", "Waiting to start")

    # Step 2: Run first 4 agents concurrently
    await _update_agent_status(trip_id, "travel_coordinator", "running", "Orchestrating agent execution")

    tasks = [
        _run_agent_safe(config, preferences, trip_id)
        for config in AGENT_CONFIGS
    ]
    results_list = await asyncio.gather(*tasks, return_exceptions=False)

    # Collect results
    agent_outputs = {}
    for config, result in zip(AGENT_CONFIGS, results_list):
        agent_outputs[config["name"]] = result

    # Step 3: Run itinerary agent with other agents' outputs
    itin_start = datetime.now(timezone.utc)
    await _update_agent_status(trip_id, "itinerary_planning", "running", "Creating day-by-day itinerary")
    try:
        itinerary_result = await itinerary_agent.run(
            preferences=preferences,
            agent_outputs=agent_outputs,
        )
        itin_dur = round((datetime.now(timezone.utc) - itin_start).total_seconds(), 2)
        if isinstance(itinerary_result, dict) and "metadata" in itinerary_result:
            itinerary_result["metadata"]["execution_duration_sec"] = itin_dur

        await _update_agent_status(trip_id, "itinerary_planning", "completed", "Itinerary created", itinerary_result)
        agent_outputs["itinerary_planning"] = itinerary_result
    except Exception as e:
        itin_dur = round((datetime.now(timezone.utc) - itin_start).total_seconds(), 2)
        error_msg = f"Itinerary agent failed: {str(e)}"
        itinerary_result = {
            "error": error_msg,
            "metadata": {
                "agent_name": "itinerary_planning",
                "display_name": "Itinerary Planning Agent",
                "responsibility": "Creating your day-by-day itinerary",
                "source_type": "failed",
                "data_sources": [],
                "is_fallback": True,
                "execution_duration_sec": itin_dur,
                "errors": [error_msg],
            }
        }
        await _update_agent_status(trip_id, "itinerary_planning", "failed", error_msg, itinerary_result)
        agent_outputs["itinerary_planning"] = itinerary_result

    # Step 4: Coordinator synthesizes
    coord_start = datetime.now(timezone.utc)
    await _update_agent_status(trip_id, "travel_coordinator", "running", "Synthesizing final travel plan")

    subagents_successful = sum(1 for v in agent_outputs.values() if "error" not in v)
    total_agents_successful = subagents_successful + 1  # Including coordinator
    agents_failed = len(agent_outputs) - subagents_successful

    has_map = {k: "error" not in v for k, v in agent_outputs.items()}

    synthesis_prompt = SYNTHESIS_PROMPT.format(
        preferences=json.dumps(preferences, indent=2),
        has_destination=has_map.get("destination_research", False),
        has_weather=has_map.get("weather_intelligence", False),
        has_local=has_map.get("local_discovery", False),
        has_budget=has_map.get("budget_management", False),
        has_itinerary=has_map.get("itinerary_planning", False),
        agents_successful=total_agents_successful,
        agents_failed=agents_failed,
    )

    try:
        coordinator_result, coord_meta = await llm_service.generate_json_with_provenance(synthesis_prompt, SYSTEM_PROMPT)
    except Exception as e:
        coord_meta = {"provider_used": "fallback", "is_fallback": True, "error": str(e)}
        coordinator_result = {
            "trip_title": f"Trip to {preferences.get('destination', 'Unknown')}",
            "executive_summary": f"Your trip plan has been generated. Note: Final synthesis encountered an issue: {str(e)}",
            "trip_highlights": [],
            "key_recommendations": [],
            "data_quality": {
                "agents_successful": total_agents_successful,
                "agents_failed": agents_failed,
                "confidence_level": "low",
            },
        }

    # Ensure data_quality counts coordinator as 6th agent
    if "data_quality" in coordinator_result:
        coordinator_result["data_quality"]["agents_successful"] = total_agents_successful
        coordinator_result["data_quality"]["agents_failed"] = agents_failed

    coord_dur = round((datetime.now(timezone.utc) - coord_start).total_seconds(), 2)

    is_fallback = coord_meta["is_fallback"]
    errors = [coord_meta["error"]] if (is_fallback and coord_meta.get("error")) else []
    if not is_fallback:
        llm_label = "Google Gemini 3.5 Flash Lite" if coord_meta.get("provider_used") == "gemini" else "OpenAI GPT-4o-mini"
        data_sources = [llm_label, "Multi-Agent Synthesis"]
        source_type = "llm"
    else:
        data_sources = ["Multi-Agent Coordination Engine (Fallback)"]
        source_type = "fallback"

    coordinator_result["metadata"] = {
        "agent_name": "travel_coordinator",
        "display_name": "Travel Coordinator Agent",
        "responsibility": "Orchestrating agents, resolving conflicts, and synthesizing complete travel plan",
        "source_type": source_type,
        "data_sources": data_sources,
        "is_fallback": is_fallback,
        "execution_duration_sec": coord_dur,
        "errors": errors,
    }

    await _update_agent_status(trip_id, "travel_coordinator", "completed", "Travel plan synthesized", coordinator_result)

    # Step 5: Assemble final plan
    final_plan = {
        "coordinator": coordinator_result,
        "destination_research": agent_outputs.get("destination_research", {}),
        "weather_intelligence": agent_outputs.get("weather_intelligence", {}),
        "local_discovery": agent_outputs.get("local_discovery", {}),
        "budget_management": agent_outputs.get("budget_management", {}),
        "itinerary_planning": agent_outputs.get("itinerary_planning", {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preferences": preferences,
    }

    return final_plan
