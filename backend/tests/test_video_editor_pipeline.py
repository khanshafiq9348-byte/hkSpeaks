import os
import io
import wave
import struct
import asyncio
import pytest
from PIL import Image
from httpx import AsyncClient

def generate_test_wav_bytes(duration_sec: float = 3.0) -> bytes:
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        num_samples = int(duration_sec * 16000)
        samples = bytearray()
        for _ in range(num_samples):
            samples.extend(struct.pack("<h", 0))
        wav_file.writeframes(samples)
    return wav_io.getvalue()

def generate_test_image_bytes(color=(50, 100, 200), size=(640, 360)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()

@pytest.mark.asyncio
async def test_video_editor_documentary_lifecycle(client: AsyncClient):
    # 1. Login creator
    login_res = await client.post("/v1/auth/login", json={
        "email": "creator@hkspeaks.ai",
        "password": "CreatorPass123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Documentary Project
    create_res = await client.post("/v1/video-editor/projects", headers=headers, json={
        "title": "Ancient Civilizations Documentary",
        "description": "Exploration of lost empires and historical monuments.",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "fps": 30
    })
    assert create_res.status_code == 200
    project = create_res.json()
    project_id = project["id"]
    assert project["title"] == "Ancient Civilizations Documentary"
    assert project["aspect_ratio"] == "16:9"

    # 3. Upload Media Assets (3 images + 1 voiceover)
    img1 = generate_test_image_bytes(color=(120, 40, 40), size=(640, 360))
    img2 = generate_test_image_bytes(color=(40, 120, 40), size=(640, 360))
    img3 = generate_test_image_bytes(color=(40, 40, 120), size=(640, 360))
    audio_wav = generate_test_wav_bytes(duration_sec=4.0)

    upload_res = await client.post(
        f"/v1/video-editor/projects/{project_id}/assets",
        headers=headers,
        files=[
            ("files", ("pyramid.jpg", img1, "image/jpeg")),
            ("files", ("temple.jpg", img2, "image/jpeg")),
            ("files", ("monument.jpg", img3, "image/jpeg")),
            ("files", ("narration.wav", audio_wav, "audio/wav"))
        ]
    )
    assert upload_res.status_code == 200
    assets = upload_res.json()
    assert len(assets) == 4

    # 4. Generate Documentary Timeline Automatically
    gen_res = await client.post(f"/v1/video-editor/projects/{project_id}/generate", headers=headers)
    assert gen_res.status_code == 200
    doc_detail = gen_res.json()
    assert len(doc_detail["scenes"]) >= 1
    assert len(doc_detail["timeline_clips"]) >= 1
    assert doc_detail["total_duration"] > 0.0

    # Verify dynamic durations and Ken Burns motion
    for clip in doc_detail["timeline_clips"]:
        assert clip["duration"] > 0.0
        assert clip["motion_type"] in ["zoom_in", "zoom_out", "pan_left", "pan_right", "ken_burns", "pan_zoom", "static"]

    # 5. Timeline manual edit: update clip motion
    first_clip = doc_detail["timeline_clips"][0]
    update_res = await client.put(
        f"/v1/video-editor/projects/{project_id}/timeline",
        headers=headers,
        json={
            "clips": [{
                "id": first_clip["id"],
                "asset_id": first_clip["asset_id"],
                "start_time": first_clip["start_time"],
                "end_time": first_clip["end_time"],
                "duration": first_clip["duration"],
                "motion_type": "ken_burns",
                "scale_factor": 1.2,
                "framing": "cover"
            }]
        }
    )
    assert update_res.status_code == 200
    updated_detail = update_res.json()
    updated_clip = [c for c in updated_detail["timeline_clips"] if c["id"] == first_clip["id"]][0]
    assert updated_clip["motion_type"] == "ken_burns"

    # 6. Submit Render Job with FFmpeg
    render_submit = await client.post(f"/v1/video-editor/projects/{project_id}/render", headers=headers)
    assert render_submit.status_code == 200
    job = render_submit.json()
    assert job["status"] in ["queued", "rendering", "completed"]
    job_id = job["id"]

    # Poll render completion
    completed = False
    for _ in range(30):
        await asyncio.sleep(1.0)
        poll_res = await client.get(f"/v1/video-editor/renders/{job_id}", headers=headers)
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            completed = True
            break
        elif poll_data["status"] == "failed":
            pytest.fail(f"Render failed: {poll_data.get('error_message')}")

    assert completed, "Video rendering timed out"

    # 7. Check Render Outputs
    renders_res = await client.get(f"/v1/video-editor/projects/{project_id}/renders", headers=headers)
    assert renders_res.status_code == 200
    outputs = renders_res.json()
    assert len(outputs) >= 1
    out_video = outputs[0]
    assert out_video["format"] == "mp4"
    assert out_video["file_size"] > 0
    assert out_video["download_url"]
