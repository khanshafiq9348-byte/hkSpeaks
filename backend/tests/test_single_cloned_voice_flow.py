import pytest
import asyncio
import wave
import struct
import io
from httpx import AsyncClient

def generate_test_wav_bytes(duration_sec: float = 2.0) -> bytes:
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        num_samples = int(duration_sec * 16000)
        samples = bytearray()
        for _ in range(num_samples):
            samples.extend(struct.pack('<h', 0))
        wav_file.writeframes(samples)
    return wav_io.getvalue()

@pytest.mark.asyncio
async def test_single_cloned_voice_lifecycle_and_replacement(client: AsyncClient):
    # 1. Login as creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial user-clone status
    status_res = await client.get("/v1/voices/user-clone", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["can_clone"] is True
    assert status_data["max_clones"] == 1

    # 3. Upload first voice sample
    audio1 = generate_test_wav_bytes(2.0)
    clone1_res = await client.post(
        "/v1/voices/clone",
        headers=headers,
        data={"name": "First Uploaded Voice", "gender": "female", "consent_confirmed": "true", "rights_confirmed": "true"},
        files={"audio_file": ("sample1.wav", audio1, "audio/wav")}
    )
    assert clone1_res.status_code == 200
    v1 = clone1_res.json()
    assert v1["name"] == "First Uploaded Voice"
    assert v1["tier"] == "custom"
    v1_id = v1["id"]

    # Verify user-clone status has 1 of 1 saved
    status_res1 = await client.get("/v1/voices/user-clone", headers=headers)
    assert status_res1.json()["saved_count"] == 1
    assert status_res1.json()["voice"]["name"] == "First Uploaded Voice"

    # 4. Upload second voice sample -> MUST REPLACE/UPDATE PREVIOUS CLONE (1 of 1 saved)
    audio2 = generate_test_wav_bytes(2.5)
    clone2_res = await client.post(
        "/v1/voices/clone",
        headers=headers,
        data={"name": "Replaced Voice Clone", "gender": "female", "consent_confirmed": "true", "rights_confirmed": "true"},
        files={"audio_file": ("sample2.wav", audio2, "audio/wav")}
    )
    assert clone2_res.status_code == 200
    v2 = clone2_res.json()
    assert v2["name"] == "Replaced Voice Clone"
    assert v2["tier"] == "custom"

    # Check that user STILL has exactly 1 active cloned voice!
    status_res2 = await client.get("/v1/voices/user-clone", headers=headers)
    assert status_res2.json()["saved_count"] == 1
    assert status_res2.json()["voice"]["name"] == "Replaced Voice Clone"

    # 5. Generate TTS with the exact single cloned voice
    active_clone = status_res2.json()["voice"]
    gen_res = await client.post("/v1/text-to-speech", headers=headers, json={
        "text": "Testing single cloned voice flow with guaranteed voice ID routing.",
        "voice_id": active_clone["id"],
        "format": "mp3"
    })
    assert gen_res.status_code == 200
    gen_id = gen_res.json()["id"]

    # Poll for completion
    completed = False
    for _ in range(25):
        await asyncio.sleep(0.5)
        poll = await client.get(f"/v1/generations/{gen_id}", headers=headers)
        data = poll.json()
        if data["status"] == "completed":
            assert data["voice_id"] == active_clone["id"]
            assert data["model"] == active_clone["model"]
            assert data["audio_url"] is not None
            completed = True
            break
        elif data["status"] == "failed":
            pytest.fail(f"Generation failed: {data.get('error_message')}")

    assert completed, "Cloned voice generation timed out"

    # 6. Delete the cloned voice -> returns to 0 of 1 saved
    del_res = await client.delete(f"/v1/voices/{active_clone['id']}", headers=headers)
    assert del_res.status_code == 200

    status_res3 = await client.get("/v1/voices/user-clone", headers=headers)
    assert status_res3.json()["saved_count"] == 0
    assert status_res3.json()["voice"] is None

    # 7. Verify standard catalog voice TTS also works (Sarah)
    catalog_res = await client.get("/v1/voices", headers=headers)
    sarah = [v for v in catalog_res.json() if "sarah" in v["slug"].lower()][0]

    std_gen_res = await client.post("/v1/text-to-speech", headers=headers, json={
        "text": "Standard catalog voice generation remains unaffected.",
        "voice_id": sarah["id"],
        "format": "mp3"
    })
    assert std_gen_res.status_code == 200
    std_id = std_gen_res.json()["id"]

    for _ in range(25):
        await asyncio.sleep(0.5)
        poll = await client.get(f"/v1/generations/{std_id}", headers=headers)
        if poll.json()["status"] == "completed":
            assert poll.json()["voice_id"] == sarah["id"]
            break
    else:
        pytest.fail("Standard voice generation timed out")

@pytest.mark.asyncio
async def test_voice_types_and_source_filtering(client: AsyncClient):
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload a clone
    audio = generate_test_wav_bytes(1.5)
    clone_res = await client.post(
        "/v1/voices/clone",
        headers=headers,
        data={"name": "Type Test Clone", "gender": "male", "consent_confirmed": "true", "rights_confirmed": "true"},
        files={"audio_file": ("test_clone.wav", audio, "audio/wav")}
    )
    assert clone_res.status_code == 200
    clone_data = clone_res.json()
    assert clone_data["voice_type"] == "clone"

    # Query all voices
    all_voices_res = await client.get("/v1/voices", headers=headers)
    assert all_voices_res.status_code == 200
    all_voices = all_voices_res.json()
    assert any(v["voice_type"] == "clone" for v in all_voices)
    assert any(v["voice_type"] == "library" for v in all_voices)

    # Query strictly Voice Library
    lib_res = await client.get("/v1/voices?voice_type=library", headers=headers)
    assert lib_res.status_code == 200
    lib_voices = lib_res.json()
    assert len(lib_voices) > 0
    assert all(v["voice_type"] == "library" for v in lib_voices)
    assert not any(v["tier"] == "custom" for v in lib_voices)

    # Query strictly Your Clone
    clone_query_res = await client.get("/v1/voices?voice_type=clone", headers=headers)
    assert clone_query_res.status_code == 200
    clones = clone_query_res.json()
    assert len(clones) == 1
    assert clones[0]["voice_type"] == "clone"
    assert clones[0]["id"] == clone_data["id"]
