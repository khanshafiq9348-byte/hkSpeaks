import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_cloned_voice_routing_and_fallback_prohibition(client: AsyncClient):
    # 1. Login as creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Clone a new voice with valid in-memory WAV audio
    import wave, struct, io
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        samples = bytearray()
        for i in range(32000):
            samples.extend(struct.pack('<h', 0))
        wav_file.writeframes(samples)
    audio_bytes = wav_io.getvalue()

    clone_res = await client.post(
        "/v1/voices/clone",
        headers=headers,
        data={
            "name": "Strict Identity Clone",
            "gender": "female",
            "consent_confirmed": "true",
            "rights_confirmed": "true"
        },
        files={"audio_file": ("sample.wav", audio_bytes, "audio/wav")}
    )
    assert clone_res.status_code == 200, f"Clone failed: {clone_res.text}"
    cloned_voice = clone_res.json()
    cloned_id = cloned_voice["id"]
    assigned_model = cloned_voice["model"]

    assert cloned_id is not None
    assert assigned_model is not None
    assert "neural" in assigned_model.lower()

    # 3. Generate TTS using the exact cloned voice ID
    gen_res = await client.post("/v1/text-to-speech", headers=headers, json={
        "text": "Testing strict voice identity routing for custom voice clone.",
        "voice_id": cloned_id,
        "format": "mp3"
    })
    assert gen_res.status_code == 200, f"TTS request failed: {gen_res.text}"
    gen_id = gen_res.json()["id"]

    # Poll for completion
    completed = False
    for _ in range(25):
        await asyncio.sleep(0.5)
        poll_res = await client.get(f"/v1/generations/{gen_id}", headers=headers)
        data = poll_res.json()
        if data["status"] == "completed":
            assert data["voice_id"] == cloned_id
            assert data["model"] == assigned_model
            assert data["audio_url"] is not None
            completed = True
            break
        elif data["status"] == "failed":
            pytest.fail(f"Generation failed unexpectedly: {data.get('error_message')}")

    assert completed, "TTS generation timed out"

    # 4. STRICT FALLBACK PROHIBITION TEST:
    # If the neural engine is unavailable for the cloned voice, the system MUST fail
    # and NEVER fallback to another voice or default SAPI engine.
    from app.providers.mock import MockTTSProvider

    async def mock_failing_synth(self, request, voice_name):
        # Simulate neural service outage
        return None

    with patch.object(MockTTSProvider, "_synthesize_edge_tts", mock_failing_synth):
        fail_gen_res = await client.post("/v1/text-to-speech", headers=headers, json={
            "text": "This request must fail instead of using a default AI voice.",
            "voice_id": cloned_id,
            "format": "mp3"
        })
        assert fail_gen_res.status_code == 200
        fail_gen_id = fail_gen_res.json()["id"]

        # Poll status — MUST transition to 'failed' and NOT 'completed'
        failed_cleanly = False
        for _ in range(20):
            await asyncio.sleep(0.5)
            f_poll = await client.get(f"/v1/generations/{fail_gen_id}", headers=headers)
            f_data = f_poll.json()
            if f_data["status"] == "failed":
                assert f_data["error_code"] in ["PROVIDER_UNAVAILABLE", "GENERATION_FAILED"]
                failed_cleanly = True
                break
            elif f_data["status"] == "completed":
                pytest.fail("VIOLATION: Cloned voice silently fell back to a default voice instead of returning an error!")

        assert failed_cleanly, "Failed cloned voice generation did not record failed status"
