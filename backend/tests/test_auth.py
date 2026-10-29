import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_me_without_token(client: AsyncClient):
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_auth_me_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer invalid.malformed.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_with_valid_token(client: AsyncClient, auth_headers_owner):
    response = await client.get("/api/v1/me", headers=auth_headers_owner)
    assert response.status_code == 200
    data = response.json()
    assert data["firebase_uid"] == "owner-user-123"
    assert "email" in data
    assert "id" in data
    assert data["role"] == "user"
