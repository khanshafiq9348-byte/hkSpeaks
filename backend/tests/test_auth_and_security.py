import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_signup_and_login(client: AsyncClient):
    # 1. Sign up new user
    signup_data = {
        "email": "testuser@example.com",
        "password": "Password123!",
        "display_name": "Test User"
    }
    res = await client.post("/v1/auth/signup", json=signup_data)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "access_token" in body
    assert body["user"]["email"] == "testuser@example.com"
    token = body["access_token"]

    # 2. Get profile with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testuser@example.com"

    # 3. Log in with credentials
    login_data = {
        "email": "testuser@example.com",
        "password": "Password123!"
    }
    login_res = await client.post("/v1/auth/login", json=login_data)
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

@pytest.mark.asyncio
async def test_unauthorized_access_rejected(client: AsyncClient):
    # No auth header
    res = await client.get("/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"

@pytest.mark.asyncio
async def test_invalid_credentials_rejected(client: AsyncClient):
    login_data = {
        "email": "creator@hkspeaks.ai",
        "password": "WrongPassword!"
    }
    res = await client.post("/v1/auth/login", json=login_data)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"
