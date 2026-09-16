import pytest
import io
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_cloned_voice_id_trace_and_no_silent_fallback(client: AsyncClient):
    # 1. Log in as creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create audio sample for clone
    dummy_wav = io.BytesIO()
    import wave
    with wave.open(dummy_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 24000 * 3)
    dummy_wav.seek(0)

    # 3. Create cloned voice
    files = {"audio_file": ("sample.wav", dummy_wav.getvalue(), "audio/wav")}
    data = {
        "name": "Audit Cloned Voice",
        "gender": "female",
        "language": "en",
        "description": "Trace audit test clone",
        "consent_confirmed": "true",
        "rights_confirmed": "true"
    }
    clone_res = await client.post("/v1/voices/clone", data=data, files=files, headers=headers)
    assert clone_res.status_code == 200
    cloned_voice = clone_res.json()
    cloned_voice_id = cloned_voice["id"]
    assert cloned_voice["tier"] == "custom"
    assert cloned_voice["name"] == "Audit Cloned Voice"
    assert cloned_voice.get("model") is not None
    assert "neural" in cloned_voice["model"].lower()

    # 4. Generate TTS with the cloned voice ID
    gen_res = await client.post("/v1/text-to-speech", json={
        "text": "This is an audit test ensuring the exact cloned voice ID is preserved throughout the pipeline.",
        "voice_id": cloned_voice_id,
        "format": "mp3"
    }, headers=headers)
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    gen_id = gen_data["id"]
    assert gen_data["voice_name"] == "Audit Cloned Voice"

    # Wait for completion
    for _ in range(20):
        await asyncio.sleep(0.5)
        check = (await client.get(f"/v1/generations/{gen_id}", headers=headers)).json()
        if check["status"] == "completed":
            assert check["actual_audio_seconds"] > 0
            assert check["audio_url"] is not None
            assert check["voice_name"] == "Audit Cloned Voice"
            break
    else:
        pytest.fail("Cloned voice generation did not complete in time")

    # 5. Verify standard voice generation uses the exact voice ID
    voices = (await client.get("/v1/voices", headers=headers)).json()
    david_voice = next(v for v in voices if "david" in v["name"].lower())
    std_res = await client.post("/v1/text-to-speech", json={
        "text": "Testing standard voice DavidAuthoritative Broadcaster.",
        "voice_id": david_voice["id"],
        "format": "mp3"
    }, headers=headers)
    assert std_res.status_code == 200
    std_gen = std_res.json()
    assert std_gen["voice_name"] == david_voice["name"]

    # 6. Verify non-existent voice ID is rejected with 404 (NEVER silently fall back)
    fake_res = await client.post("/v1/text-to-speech", json={
        "text": "Testing fake voice should never fall back silently.",
        "voice_id": "00000000-0000-0000-0000-000000000000",
        "format": "mp3"
    }, headers=headers)
    assert fake_res.status_code == 404
    assert fake_res.json()["error"]["code"] == "VOICE_NOT_FOUND"
