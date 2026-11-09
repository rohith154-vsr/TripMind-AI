import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "TripMind AI Backend" in data["service"]

@pytest.mark.asyncio
async def test_trip_list_endpoint():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/trips")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_generate_and_status_flow(sample_preferences):
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"preferences": sample_preferences}
        gen_res = await client.post("/api/trips/generate", json=payload)
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        trip_id = gen_data["trip_id"]
        assert trip_id is not None

        # Check agent status
        status_res = await client.get(f"/api/agents/status/{trip_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["trip_id"] == trip_id
        assert len(status_data["agents"]) == 6

        # Check trip details
        trip_res = await client.get(f"/api/trips/{trip_id}")
        assert trip_res.status_code == 200
        assert trip_res.json()["destination"] == sample_preferences["destination"]


