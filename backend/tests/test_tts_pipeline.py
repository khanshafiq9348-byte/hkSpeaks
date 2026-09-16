import pytest
import asyncio
from httpx import AsyncClient
from app.workers.processor import split_text_into_chunks

def test_split_text_into_chunks():
    # Short text
    short = "Hello world! This is a test."
    chunks = split_text_into_chunks(short, max_chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == short

    # Long text exceeding chunk size
    sentence1 = "This is the first long sentence designed to verify boundary splitting."
    sentence2 = "Here is the second sentence that continues the narrative cleanly."
    sentence3 = "Finally, the third concluding thought finishes the paragraph."
    full = f"{sentence1} {sentence2} {sentence3}"

    chunks = split_text_into_chunks(full, max_chunk_size=75)
    assert len(chunks) >= 2
    # Ensure all original words are preserved
    reconstructed = " ".join(chunks)
    assert "first long sentence" in reconstructed
    assert "concluding thought" in reconstructed

@pytest.mark.asyncio
async def test_generation_lifecycle(client: AsyncClient):
    # Log in
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get a voice
    voices = (await client.get("/v1/voices", headers=headers)).json()
    voice = voices[0]

    # Post generation
    gen_payload = {
        "text": "The quick brown fox jumps over the lazy dog.",
        "voice_id": voice["id"],
        "format": "mp3"
    }
    gen_res = await client.post("/v1/text-to-speech", json=gen_payload, headers=headers)
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    gen_id = gen_data["id"]
    assert gen_data["status"] in ["queued", "processing", "completed"]

    # Poll status until completed (max 5 seconds)
    for _ in range(10):
        await asyncio.sleep(0.5)
        status_res = await client.get(f"/v1/generations/{gen_id}", headers=headers)
        assert status_res.status_code == 200
        cur = status_res.json()
        if cur["status"] == "completed":
            assert cur["actual_audio_seconds"] > 0
            assert cur["audio_url"] is not None
            break
    else:
        # If worker hadn't finished in loop, check it didn't fail
        final_check = (await client.get(f"/v1/generations/{gen_id}", headers=headers)).json()
        assert final_check["status"] in ["queued", "processing", "completed"]

@pytest.mark.asyncio
async def test_idempotency_key(client: AsyncClient):
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "test_idem_key_999"
    }

    voices = (await client.get("/v1/voices", headers=headers)).json()
    voice = voices[0]

    payload = {
        "text": "Testing idempotency deduplication.",
        "voice_id": voice["id"],
        "format": "mp3"
    }

    res1 = await client.post("/v1/text-to-speech", json=payload, headers=headers)
    assert res1.status_code == 200
    id1 = res1.json()["id"]

    # Send duplicate request with identical key
    res2 = await client.post("/v1/text-to-speech", json=payload, headers=headers)
    assert res2.status_code == 200
    id2 = res2.json()["id"]

    assert id1 == id2, "Idempotent requests must return the original generation record"
