"""
Trip API Routes — handles trip generation, retrieval, deletion.
"""
import json
import uuid
import asyncio
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.trip import Trip, AgentStatus
from app.schemas.trip_schema import TripGenerateRequest, TripResponse
from app.agents import coordinator

router = APIRouter(prefix="/api/trips", tags=["trips"])


async def _run_orchestration(trip_id: str, preferences: dict, db_session_factory=None):
    """Background task to run the full agent orchestration with clean isolated sessions."""
    from app.database import AsyncSessionLocal
    
    # 1. Mark as running
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if not trip:
            return
        trip.status = "running"
        await db.commit()

    # 2. Run orchestration without holding a long session
    try:
        final_plan = await coordinator.orchestrate(preferences, trip_id)

        # 3. Save completed result
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Trip).where(Trip.id == trip_id))
            trip = result.scalar_one_or_none()
            if trip:
                trip.status = "completed"
                trip.result_json = json.dumps(final_plan)
                coord = final_plan.get("coordinator", {})
                trip.title = coord.get("trip_title", trip.title)
                await db.commit()

    except Exception as e:
        # 4. Mark as failed if anything went wrong
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Trip).where(Trip.id == trip_id))
            trip = result.scalar_one_or_none()
            if trip:
                trip.status = "failed"
                trip.error_message = str(e)
                await db.commit()


@router.post("/generate")
async def generate_trip(
    request: TripGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new travel plan using multi-agent orchestration."""
    prefs = request.preferences

    trip_id = str(uuid.uuid4())
    title = f"Trip to {prefs.destination}"

    trip = Trip(
        id=trip_id,
        title=title,
        origin=prefs.origin,
        destination=prefs.destination,
        departure_date=prefs.departure_date,
        return_date=prefs.return_date,
        num_travelers=prefs.num_travelers,
        budget=prefs.budget,
        currency=prefs.currency,
        travel_style=prefs.travel_style,
        interests=json.dumps(prefs.interests),
        preferences_json=json.dumps(prefs.model_dump()),
        status="pending",
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    # Kick off background orchestration
    preferences_dict = prefs.model_dump()
    background_tasks.add_task(_run_orchestration, trip_id, preferences_dict, None)

    return {
        "trip_id": trip_id,
        "status": "pending",
        "message": "Trip generation started. Poll /api/agents/status/{trip_id} for progress.",
    }


@router.get("")
async def list_trips(db: AsyncSession = Depends(get_db)):
    """Return all saved trips."""
    result = await db.execute(select(Trip).order_by(Trip.created_at.desc()))
    trips = result.scalars().all()
    return [t.to_dict() for t in trips]


@router.get("/{trip_id}")
async def get_trip(trip_id: str, db: AsyncSession = Depends(get_db)):
    """Return a specific trip by ID."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip.to_dict()


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a trip and its agent statuses."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    await db.execute(delete(AgentStatus).where(AgentStatus.trip_id == trip_id))
    await db.delete(trip)
    await db.commit()
    return {"message": "Trip deleted successfully", "trip_id": trip_id}
