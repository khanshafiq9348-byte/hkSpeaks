import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_api_key_lifecycle(client: AsyncClient):
    # Log in as creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create API key
    create_res = await client.post("/v1/api-keys", json={"name": "Production Bot Key"}, headers=user_headers)
    assert create_res.status_code == 200
    key_data = create_res.json()
    assert "raw_key" in key_data
    raw_key = key_data["raw_key"]
    assert raw_key.startswith("hk_live_")
    key_id = key_data["id"]

    # 2. Use API key directly in Authorization header
    api_headers = {"Authorization": f"Bearer {raw_key}"}
    me_res = await client.get("/v1/auth/me", headers=api_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "creator@hkspeaks.ai"

    # 3. Revoke API key
    revoke_res = await client.delete(f"/v1/api-keys/{key_id}", headers=user_headers)
    assert revoke_res.status_code == 200

    # 4. Attempt to use revoked API key
    revoked_req = await client.get("/v1/auth/me", headers=api_headers)
    assert revoked_req.status_code == 401
    assert revoked_req.json()["error"]["code"] == "AUTH_REQUIRED"
