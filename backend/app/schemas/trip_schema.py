from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date


class TripPreferences(BaseModel):
    origin: str = Field(..., min_length=2, max_length=200)
    destination: str = Field(..., min_length=2, max_length=200)
    departure_date: str = Field(...)
    return_date: str = Field(...)
    num_travelers: int = Field(default=1, ge=1, le=50)
    budget: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=5)
    travel_style: str = Field(default="Adventure")
    interests: List[str] = Field(default_factory=list)

    @field_validator("travel_style")
    @classmethod
    def validate_style(cls, v):
        allowed = ["Adventure", "Relaxation", "Luxury", "Budget", "Cultural"]
        if v not in allowed:
            raise ValueError(f"travel_style must be one of {allowed}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        return v.upper()


class TripGenerateRequest(BaseModel):
    preferences: TripPreferences


class TripResponse(BaseModel):
    id: str
    title: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    num_travelers: int
    budget: float
    currency: str
    travel_style: str
    interests: List[str]
    status: str
    created_at: Optional[str] = None


class AgentStatusResponse(BaseModel):
    trip_id: str
    agent_name: str
    status: str
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
