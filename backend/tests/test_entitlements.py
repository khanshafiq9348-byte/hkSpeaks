import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_free_user_blocked_from_premium_voice(client: AsyncClient):
    # 1. Sign up new free user
    signup_data = {
        "email": "free_tier_user@example.com",
        "password": "Password123!",
        "display_name": "Free User"
    }
    signup_res = await client.post("/v1/auth/signup", json=signup_data)
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Find a premium voice
    voices_res = await client.get("/v1/voices", headers=headers)
    voices = voices_res.json()
    premium_voice = next((v for v in voices if v["tier"] in ["premium", "ultra"]), None)
    assert premium_voice is not None, "At least one premium voice should exist"

    # 3. Attempt generation with premium voice
    gen_payload = {
        "text": "This is an attempt to use a premium voice on a free plan.",
        "voice_id": premium_voice["id"],
        "format": "mp3"
    }
    res = await client.post("/v1/text-to-speech", json=gen_payload, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PREMIUM_REQUIRED"

@pytest.mark.asyncio
async def test_creator_user_can_use_premium_voice(client: AsyncClient):
    # Log in as demo creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Find premium voice
    voices_res = await client.get("/v1/voices", headers=headers)
    premium_voice = next((v for v in voices_res.json() if v["tier"] == "premium"), None)
    assert premium_voice is not None

    # Generate
    gen_payload = {
        "text": "Hello world from the creator plan.",
        "voice_id": premium_voice["id"],
        "format": "mp3"
    }
    res = await client.post("/v1/text-to-speech", json=gen_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["queued", "processing", "completed"]
