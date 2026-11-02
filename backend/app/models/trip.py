import json
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float
from sqlalchemy.sql import func
from app.database import Base


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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
