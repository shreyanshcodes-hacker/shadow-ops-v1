import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    # Defensive headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert "X-Request-Id" in response.headers


@pytest.mark.asyncio
async def test_request_id_tracing(client: AsyncClient):
    custom_request_id = "test-req-12345"
    response = await client.get("/api/v1/health", headers={"X-Request-Id": custom_request_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id") == custom_request_id


@pytest.mark.asyncio
async def test_cors_preflight(client: AsyncClient):
    # Allowed origin
    res = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
