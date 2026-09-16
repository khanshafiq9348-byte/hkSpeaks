import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_storage_head_and_range_requests(client: AsyncClient):
    # First, generate audio as creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    voices = (await client.get("/v1/voices", headers=headers)).json()
    voice = voices[0]

    gen_res = await client.post("/v1/text-to-speech", json={
        "text": "Audio test for streaming range headers and head requests.",
        "voice_id": voice["id"],
        "format": "mp3"
    }, headers=headers)
    assert gen_res.status_code == 200
    gen_id = gen_res.json()["id"]

    # Wait for completion
    import asyncio
    audio_path = None
    for _ in range(20):
        await asyncio.sleep(0.5)
        check = (await client.get(f"/v1/generations/{gen_id}", headers=headers)).json()
        if check["status"] == "completed" and check.get("audio_url"):
            # Extract path from URL e.g. /v1/storage/...
            url = check["audio_url"]
            audio_path = url[url.index("/v1/storage"):]
            break

    assert audio_path is not None, "Generation should complete with audio_path"

    # Test HEAD request on audio URL
    head_res = await client.head(audio_path)
    assert head_res.status_code == 200
    assert "content-length" in head_res.headers
    assert head_res.headers.get("accept-ranges") == "bytes"

    # Test Range request on audio URL
    range_headers = {"Range": "bytes=0-500"}
    range_res = await client.get(audio_path, headers=range_headers)
    assert range_res.status_code in [200, 206]
    assert len(range_res.content) > 0

@pytest.mark.asyncio
async def test_delete_generation_from_history(client: AsyncClient):
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    voices = (await client.get("/v1/voices", headers=headers)).json()
    voice = voices[0]

    gen_res = await client.post("/v1/text-to-speech", json={
        "text": "Temporary generation to be deleted.",
        "voice_id": voice["id"],
        "format": "mp3"
    }, headers=headers)
    gen_id = gen_res.json()["id"]

    # Delete generation
    del_res = await client.delete(f"/v1/generations/{gen_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure it's deleted
    get_res = await client.get(f"/v1/generations/{gen_id}", headers=headers)
    assert get_res.status_code == 404

@pytest.mark.asyncio
async def test_clear_all_generations(client: AsyncClient):
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Clear all
    clear_res = await client.delete("/v1/generations", headers=headers)
    assert clear_res.status_code == 200
    assert "deleted_count" in clear_res.json()

    # Verify history is empty
    history_res = await client.get("/v1/generations", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()["items"]) == 0

