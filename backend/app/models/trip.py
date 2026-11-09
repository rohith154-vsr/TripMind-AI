import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, Float
from sqlalchemy.sql import func
from app.database import Base


def _format_dt(dt) -> Optional[str]:
    """Format datetime as strict ISO 8601 UTC string ending in 'Z'."""
    if not dt:
        return None
    if isinstance(dt, str):
        s = dt.strip()
        if s.endswith("+00:00"):
            return s[:-6] + "Z"
        if not s.endswith("Z") and not ("+" in s[10:] or "-" in s[10:]):
            return s.replace(" ", "T") + "Z"
        return s
    if dt.tzinfo is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    departure_date = Column(String(20), nullable=False)
    return_date = Column(String(20), nullable=False)
    num_travelers = Column(Integer, default=1)
    budget = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    travel_style = Column(String(50), default="")
    interests = Column(Text, default="[]")  # JSON array
    preferences_json = Column(Text, default="{}")  # Full preferences JSON
    result_json = Column(Text, default="{}")  # Full result JSON
    status = Column(String(20), default="pending")  # pending | running | completed | failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date,
            "return_date": self.return_date,
            "num_travelers": self.num_travelers,
            "budget": self.budget,
            "currency": self.currency,
            "travel_style": self.travel_style,
            "interests": json.loads(self.interests or "[]"),
            "preferences": json.loads(self.preferences_json or "{}"),
            "result": json.loads(self.result_json or "{}"),
            "status": self.status,
            "error_message": self.error_message,
            "created_at": _format_dt(self.created_at),
            "updated_at": _format_dt(self.updated_at),
        }


class AgentStatus(Base):
    __tablename__ = "agent_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), default="waiting")  # waiting | running | completed | failed
    message = Column(Text, nullable=True)
    result_json = Column(Text, default="{}")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "message": self.message,
            "result": json.loads(self.result_json or "{}"),
            "started_at": _format_dt(self.started_at),
            "completed_at": _format_dt(self.completed_at),
        }
