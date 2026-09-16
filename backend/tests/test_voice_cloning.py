import pytest
import io
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_voice_cloning_requires_auth(client: AsyncClient):
    # No auth header
    files = {"audio_file": ("test.mp3", b"dummy audio content here", "audio/mpeg")}
    data = {
        "name": "Unauthorized Voice",
        "consent_confirmed": "true",
        "rights_confirmed": "true"
    }
    res = await client.post("/v1/voices/clone", data=data, files=files)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"

@pytest.mark.asyncio
async def test_voice_cloning_requires_consent(client: AsyncClient):
    # Log in as creator (has cloning entitlement)
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate a small valid wav
    import wave, struct
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        # 2 seconds of audio
        samples = bytearray()
        for i in range(32000):
            samples.extend(struct.pack('<h', 0))
        wav_file.writeframes(samples)
    audio_bytes = wav_io.getvalue()

    # Attempt cloning without consent
    files = {"audio_file": ("audio [vocals].wav", audio_bytes, "audio/wav")}
    data = {
        "name": "No Consent Voice",
        "consent_confirmed": "false",
        "rights_confirmed": "false"
    }
    res = await client.post("/v1/voices/clone", data=data, files=files, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "CLONE_NOT_AUTHORIZED"

@pytest.mark.asyncio
async def test_voice_cloning_success_with_special_filename(client: AsyncClient):
    # Log in as creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create dummy audio
    import wave, struct
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

    # Clone with brackets and spaces in filename (similar to user screenshot)
    files = {"audio_file": ("audio [vocals].wav", audio_bytes, "audio/wav")}
    data = {
        "name": "My Custom Voice Clone",
        "description": "Custom tested voice",
        "consent_confirmed": "true",
        "rights_confirmed": "true"
    }
    res = await client.post("/v1/voices/clone", data=data, files=files, headers=headers)
    assert res.status_code == 200, res.text
    v = res.json()
    assert v["name"] == "My Custom Voice Clone"
    assert v["tier"] == "custom"
    assert v["is_public"] is False
