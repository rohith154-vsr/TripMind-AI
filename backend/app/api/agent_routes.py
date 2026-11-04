"""
Agent Status Routes — SSE streaming + polling for live agent execution status.
"""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.trip import Trip, AgentStatus

router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENT_DISPLAY_INFO = {
    "destination_research": {
        "display_name": "Destination Research Agent",
        "icon": "MapPin",
        "description": "Researching destination attractions and activities",
    },
    "weather_intelligence": {
        "display_name": "Weather Intelligence Agent",
        "icon": "Cloud",
        "description": "Fetching real-time weather forecasts",
    },
    "local_discovery": {
        "display_name": "Local Discovery Agent",
        "icon": "Search",
        "description": "Finding restaurants and local attractions",
    },
    "budget_management": {
        "display_name": "Budget Management Agent",
        "icon": "DollarSign",
        "description": "Calculating costs and currency conversions",
    },
    "itinerary_planning": {
        "display_name": "Itinerary Planning Agent",
        "icon": "Calendar",
        "description": "Creating your day-by-day itinerary",
    },
    "travel_coordinator": {
        "display_name": "Travel Coordinator Agent",
        "icon": "Compass",
        "description": "Orchestrating agents and synthesizing your travel plan",
    },
}


@router.get("/status/{trip_id}")
async def get_agent_statuses(trip_id: str, db: AsyncSession = Depends(get_db)):
    """Get the execution status of all agents for a trip."""
    # Check trip exists
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Get agent statuses
    result = await db.execute(
        select(AgentStatus).where(AgentStatus.trip_id == trip_id)
    )
    statuses = result.scalars().all()

    status_map = {s.agent_name: s.to_dict() for s in statuses}

    # Build response with all 6 agents
    agents = []
    for agent_name, info in AGENT_DISPLAY_INFO.items():
        status_data = status_map.get(agent_name, {
            "status": "waiting",
            "message": "Waiting to start",
            "started_at": None,
            "completed_at": None,
            "result": {},
        })
        res_dict = status_data.get("result") or {}
        meta = res_dict.get("metadata") or {}

        # Compute duration if available
        duration = meta.get("execution_duration_sec")
        if duration is None and status_data.get("started_at") and status_data.get("completed_at"):
            try:
                from datetime import datetime
                s_time = datetime.fromisoformat(status_data["started_at"])
                e_time = datetime.fromisoformat(status_data["completed_at"])
                duration = round((e_time - s_time).total_seconds(), 2)
            except Exception:
                duration = None

        errors = meta.get("errors", [])
        if status_data.get("status") == "failed" and status_data.get("message"):
            if status_data["message"] not in errors:
                errors.append(status_data["message"])

        agents.append({
            **info,
            "agent_name": agent_name,
            "responsibility": meta.get("responsibility", info.get("description", "")),
            "status": status_data.get("status", "waiting"),
            "message": status_data.get("message", ""),
            "source_type": meta.get("source_type", "pending" if status_data.get("status") != "completed" else "llm"),
            "data_sources": meta.get("data_sources", []),
            "is_fallback": meta.get("is_fallback", False),
            "duration_seconds": duration,
            "errors": errors,
            "started_at": status_data.get("started_at"),
            "completed_at": status_data.get("completed_at"),
        })

    return {
        "trip_id": trip_id,
        "trip_status": trip.status,
        "agents": agents,
    }


@router.get("/stream/{trip_id}")
async def stream_agent_status(trip_id: str):
    """SSE endpoint for live agent status updates."""
    from app.database import AsyncSessionLocal

    async def event_generator():
        """Generate SSE events for agent status updates."""
        previous_statuses = {}
        max_polls = 120  # 2 minutes max (1 poll/second)
        polls = 0

        while polls < max_polls:
            async with AsyncSessionLocal() as session:
                # Get trip status
                trip_result = await session.execute(select(Trip).where(Trip.id == trip_id))
                trip = trip_result.scalar_one_or_none()
                if not trip:
                    yield f"data: {json.dumps({'error': 'Trip not found'})}\n\n"
                    break

                # Get agent statuses
                result = await session.execute(
                    select(AgentStatus).where(AgentStatus.trip_id == trip_id)
                )
                statuses = result.scalars().all()
                status_map = {s.agent_name: s.to_dict() for s in statuses}

                # Check for changes
                changed = False
                for name, data in status_map.items():
                    if previous_statuses.get(name) != data.get("status"):
                        changed = True
                        previous_statuses[name] = data.get("status")

                if changed or polls == 0:
                    agents = []
                    for agent_name, info in AGENT_DISPLAY_INFO.items():
                        status_data = status_map.get(agent_name, {
                            "status": "waiting",
                            "message": "Waiting to start",
                            "started_at": None,
                            "completed_at": None,
                            "result": {},
                        })
                        res_dict = status_data.get("result") or {}
                        meta = res_dict.get("metadata") or {}

                        duration = meta.get("execution_duration_sec")
                        if duration is None and status_data.get("started_at") and status_data.get("completed_at"):
                            try:
                                from datetime import datetime
                                s_time = datetime.fromisoformat(status_data["started_at"])
                                e_time = datetime.fromisoformat(status_data["completed_at"])
                                duration = round((e_time - s_time).total_seconds(), 2)
                            except Exception:
                                duration = None

                        errors = meta.get("errors", [])
                        if status_data.get("status") == "failed" and status_data.get("message"):
                            if status_data["message"] not in errors:
                                errors.append(status_data["message"])

                        agents.append({
                            **info,
                            "agent_name": agent_name,
                            "responsibility": meta.get("responsibility", info.get("description", "")),
                            "status": status_data.get("status", "waiting"),
                            "message": status_data.get("message", ""),
                            "source_type": meta.get("source_type", "pending" if status_data.get("status") != "completed" else "llm"),
                            "data_sources": meta.get("data_sources", []),
                            "is_fallback": meta.get("is_fallback", False),
                            "duration_seconds": duration,
                            "errors": errors,
                            "started_at": status_data.get("started_at"),
                            "completed_at": status_data.get("completed_at"),
                        })

                    payload = {
                        "trip_id": trip_id,
                        "trip_status": trip.status,
                        "agents": agents,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                # Stop if trip is done
                if trip.status in ("completed", "failed"):
                    break

            await asyncio.sleep(1)
            polls += 1

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
