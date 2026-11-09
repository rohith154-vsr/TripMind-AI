"""
FastAPI Main Application Entry Point
"""
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.config import get_settings
from app.database import init_db, AsyncSessionLocal
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

# CORS configuration
cors_kwargs = {
    "allow_origins": settings.cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

# If wildcard is present in origins, disable allow_credentials to avoid browser CORS errors
if "*" in settings.cors_origins_list:
    cors_kwargs["allow_credentials"] = False

# Support regex matching for preview deployments (e.g. Vercel preview URLs) if configured
if settings.CORS_ORIGIN_REGEX and settings.CORS_ORIGIN_REGEX.strip():
    cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX.strip()

app.add_middleware(
    CORSMiddleware,
    **cors_kwargs,
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


@app.get("/api/health/db")
async def health_db():
    """Database connectivity health check. Executes a live SELECT 1 probe."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
            },
        )


@app.get("/")
async def root():
    return {"message": "TripMind AI Backend — visit /docs for API documentation"}
