import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "test"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_database_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health/database")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["database_connected"] is True
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "ShadowOps" in data["service"]
    assert data["tagline"] == "Your AI Security Team. Always Watching."


@pytest.mark.asyncio
async def test_liveness_and_readiness_probes(client: AsyncClient):
    # Liveness probe
    live_res = await client.get("/api/v1/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "healthy"

    # Readiness probe
    ready_res = await client.get("/api/v1/health/ready")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()
    assert ready_data["status"] == "ready"
    assert ready_data["database"]["connected"] is True
    assert "scanner" in ready_data
    assert "outbox_backlog" in ready_data
