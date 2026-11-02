"""
FastAPI Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.api import trip_routes, agent_routes

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="TripMind AI",
    description="Multi-Agent Intelligent Travel Planning Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(trip_routes.router)
app.include_router(agent_routes.router)


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "TripMind AI Backend",
        "version": "1.0.0",
        "ai_provider": settings.AI_PROVIDER,
    }


@app.get("/")
async def root():
    return {"message": "TripMind AI Backend — visit /docs for API documentation"}
