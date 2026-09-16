import os
import uuid
import csv
import json
import io
import subprocess
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.models.entities import User
from app.models.prompt_entities import AudioPromptProject, PromptScene
from app.security.auth import get_current_user, get_current_user_or_default
from app.services.storage import storage_service
from app.services.prompt_engine import PromptEngine
from app.workers.prompt_processor import prompt_queue
from app.core.errors import AppException, ErrorCode

router = APIRouter(prefix="/image-prompts", tags=["AI Image Prompt Studio"])

def get_audio_duration_seconds(audio_path: str) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return round(float(res.stdout.strip()), 2)
    except Exception:
        return 15.0

@router.post("/upload")
async def upload_audio_for_prompts(
    title: Optional[str] = Form(None),
    style_preset: str = Form("cinematic"),
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    if not audio_file.filename:
        raise AppException(status_code=400, error_code=ErrorCode.VALIDATION_ERROR, message="Audio file is required.")

    file_bytes = await audio_file.read()
    if len(file_bytes) == 0:
        raise AppException(status_code=400, error_code=ErrorCode.VALIDATION_ERROR, message="Audio file cannot be empty.")

    clean_filename = f"{uuid.uuid4().hex[:8]}_{audio_file.filename}"
    storage_key, public_url = await storage_service.save_file(
        file_bytes=file_bytes,
        filename=clean_filename,
        user_id=current_user.id,
        category="prompt_audio",
        mime_type=audio_file.content_type or "audio/mpeg"
    )

    duration = get_audio_duration_seconds(storage_key)
    proj_title = title.strip() if title and title.strip() else audio_file.filename.rsplit(".", 1)[0]

    project = AudioPromptProject(
        user_id=current_user.id,
        title=proj_title,
        audio_filename=audio_file.filename,
        audio_storage_key=storage_key,
        audio_url=public_url,
        total_duration=duration,
        status="uploaded",
        style_preset=style_preset
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Enqueue background processing
    await prompt_queue.enqueue(project.id)

    return {
        "id": project.id,
        "title": project.title,
        "audio_url": project.audio_url,
        "total_duration": project.total_duration,
        "status": project.status,
        "style_preset": project.style_preset,
        "message": "Audio uploaded successfully. Transcription and prompt generation started."
    }

@router.post("/generate")
async def generate_image_prompts(
    script: str = Form(...),
    visual_style_prompt: Optional[str] = Form(""),
    title: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Image Prompt Generator:
    1. SCRIPT (required)
    2. IMAGE VISUAL STYLE PROMPT (customizable style prompt)
    3. AUDIO / VOICEOVER upload (optional)
    When audio is provided: analyzes actual audio, extracts accurate sentence-level timestamps,
    matches script with spoken audio, and generates prompts reflecting both script and timeline.
    When audio is not provided: generates sentence-level prompts normally with natural pacing.
    """
    clean_script = PromptEngine.extract_clean_script(str(script or ""))
    if not clean_script:
        clean_script = str(script or "").strip()
    if not clean_script:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Script text is required."
        )

    clean_style = PromptEngine.extract_clean_style(str(visual_style_prompt or ""))
    proj_title = str(title or "").strip() or "Image Prompt Project"

    audio_storage_key = ""
    audio_url = ""
    audio_filename = ""
    total_dur = 0.0
    scenes_data: List[dict] = []

    # 1. If optional audio is provided, analyze audio and align script
    if audio_file and audio_file.filename:
        file_bytes = await audio_file.read()
        if len(file_bytes) > 0:
            clean_filename = f"{uuid.uuid4().hex[:8]}_{audio_file.filename}"
            audio_storage_key, audio_url = await storage_service.save_file(
                file_bytes=file_bytes,
                filename=clean_filename,
                user_id=current_user.id,
                category="prompt_audio",
                mime_type=audio_file.content_type or "audio/mpeg"
            )
            audio_filename = audio_file.filename
            total_dur = get_audio_duration_seconds(audio_storage_key)
            scenes_data = PromptEngine.analyze_audio_and_align_script(
                audio_path=audio_storage_key,
                script_text=clean_script,
                visual_style_prompt=clean_style,
                total_duration=total_dur
            )

    # 2. If audio is not provided, generate from script sentence structure
    if not audio_url:
        scenes_data = PromptEngine.generate_from_script_and_style(
            script_text=clean_script,
            visual_style_prompt=clean_style
        )
        audio_filename = "script_narration.txt"
        total_dur = scenes_data[-1]["end_time"] if scenes_data else 10.0

    # 3. Create Project & Scenes in DB
    project = AudioPromptProject(
        user_id=current_user.id,
        title=proj_title,
        audio_filename=audio_filename,
        audio_storage_key=audio_storage_key,
        audio_url=audio_url,
        total_duration=total_dur,
        total_scenes=len(scenes_data),
        status="completed",
        style_preset="custom",
        settings_json={
            "visual_style_prompt": clean_style,
            "has_audio": bool(audio_url),
            "script": clean_script
        }
    )
    db.add(project)
    await db.flush()

    for sdata in scenes_data:
        scene = PromptScene(
            project_id=project.id,
            scene_index=sdata["scene_index"],
            start_time=sdata["start_time"],
            end_time=sdata["end_time"],
            duration=sdata["duration"],
            transcript_text=sdata["sentence"],
            image_prompt=sdata["image_prompt"],
            negative_prompt=sdata.get("negative_prompt", "blurry, low quality, distorted, extra limbs, bad anatomy, watermark, signature, text overlay"),
            aspect_ratio=sdata.get("aspect_ratio", "16:9")
        )
        db.add(scene)

    await db.commit()
    await db.refresh(project)

    return {
        "id": project.id,
        "title": project.title,
        "audio_url": project.audio_url,
        "has_audio": bool(project.audio_url),
        "total_duration": project.total_duration,
        "scenes_count": len(scenes_data),
        "total_scenes": len(scenes_data),
        "visual_style_prompt": clean_style,
        "scenes": scenes_data
    }

@router.post("/generate-script")
async def generate_prompts_from_script(
    body: dict,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    raw_script = str(body.get("script_text") or body.get("script") or "")
    script_text = PromptEngine.extract_clean_script(raw_script) or raw_script.strip()
    if not script_text:
        raise AppException(status_code=400, error_code=ErrorCode.VALIDATION_ERROR, message="Script/Narration text is required.")

    raw_style = str(
        body.get("visual_style_prompt") or
        body.get("style_prompt") or
        body.get("style_preset") or
        body.get("style") or
        ""
    )
    visual_style_prompt = PromptEngine.extract_clean_style(raw_style)
    title = str(body.get("title", "")).strip() or "Script Prompt Project"

    scenes_data = PromptEngine.generate_from_script_and_style(
        script_text=script_text,
        visual_style_prompt=visual_style_prompt
    )
    total_dur = scenes_data[-1]["end_time"] if scenes_data else 10.0

    project = AudioPromptProject(
        user_id=current_user.id,
        title=title,
        audio_filename="script_narration.txt",
        audio_storage_key="",
        audio_url="",
        total_duration=total_dur,
        total_scenes=len(scenes_data),
        status="completed",
        style_preset="custom",
        settings_json={
            "visual_style_prompt": visual_style_prompt,
            "has_audio": False,
            "script": script_text
        }
    )
    db.add(project)
    await db.flush()

    for sdata in scenes_data:
        scene = PromptScene(
            project_id=project.id,
            scene_index=sdata["scene_index"],
            start_time=sdata["start_time"],
            end_time=sdata["end_time"],
            duration=sdata["duration"],
            transcript_text=sdata["sentence"],
            image_prompt=sdata["image_prompt"],
            negative_prompt=sdata.get("negative_prompt", "blurry, low quality, distorted, extra limbs, bad anatomy, watermark, signature, text overlay"),
            aspect_ratio=sdata.get("aspect_ratio", "16:9")
        )
        db.add(scene)

    await db.commit()
    await db.refresh(project)

    return {
        "id": project.id,
        "title": project.title,
        "audio_url": "",
        "has_audio": False,
        "total_duration": project.total_duration,
        "audio_duration": project.total_duration,
        "status": "completed",
        "scenes_count": len(scenes_data),
        "total_scenes": len(scenes_data),
        "visual_style_prompt": visual_style_prompt,
        "scenes": scenes_data
    }

@router.get("/projects")
async def list_prompt_projects(
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AudioPromptProject)
        .where(AudioPromptProject.user_id == current_user.id)
        .order_by(AudioPromptProject.created_at.desc())
    )
    projects = res.scalars().all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "audio_filename": p.audio_filename,
            "audio_url": p.audio_url,
            "total_duration": p.total_duration,
            "status": p.status,
            "total_scenes": p.total_scenes,
            "style_preset": p.style_preset,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in projects
    ]

@router.get("/projects/{project_id}")
async def get_prompt_project(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AudioPromptProject).where(
            AudioPromptProject.id == project_id,
            AudioPromptProject.user_id == current_user.id
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Prompt project not found.")

    scenes_res = await db.execute(
        select(PromptScene)
        .where(PromptScene.project_id == project_id)
        .order_by(PromptScene.scene_index)
    )
    scenes = scenes_res.scalars().all()

    return {
        "id": project.id,
        "title": project.title,
        "audio_filename": project.audio_filename,
        "audio_url": project.audio_url,
        "total_duration": project.total_duration,
        "audio_duration": project.total_duration,
        "status": project.status,
        "error_message": project.error_message,
        "total_scenes": project.total_scenes,
        "scenes_count": project.total_scenes,
        "style_preset": project.style_preset,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "scenes": [
            {
                "id": s.id,
                "scene_index": s.scene_index,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.duration,
                "transcript": s.transcript_text,
                "transcript_text": s.transcript_text,
                "image_prompt": s.image_prompt,
                "negative_prompt": s.negative_prompt,
                "aspect_ratio": s.aspect_ratio
            }
            for s in scenes
        ]
    }

@router.patch("/projects/{project_id}/scenes/{scene_id}")
async def update_prompt_scene(
    project_id: str,
    scene_id: str,
    body: dict,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    proj_res = await db.execute(
        select(AudioPromptProject).where(
            AudioPromptProject.id == project_id,
            AudioPromptProject.user_id == current_user.id
        )
    )
    if not proj_res.scalar_one_or_none():
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    scene_res = await db.execute(
        select(PromptScene).where(PromptScene.id == scene_id, PromptScene.project_id == project_id)
    )
    scene = scene_res.scalar_one_or_none()
    if not scene:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Scene not found.")

    if "image_prompt" in body:
        scene.image_prompt = str(body["image_prompt"]).strip()
    if "transcript_text" in body:
        scene.transcript_text = str(body["transcript_text"]).strip()
    if "negative_prompt" in body:
        scene.negative_prompt = str(body["negative_prompt"]).strip()

    await db.commit()
    return {"status": "ok", "scene_id": scene.id, "image_prompt": scene.image_prompt}

@router.post("/projects/{project_id}/regenerate")
async def regenerate_prompts(
    project_id: str,
    body: dict,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AudioPromptProject).where(
            AudioPromptProject.id == project_id,
            AudioPromptProject.user_id == current_user.id
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    if "style_preset" in body:
        project.style_preset = str(body["style_preset"])

    project.status = "uploaded"
    await db.commit()
    await prompt_queue.enqueue(project.id)

    return {"status": "queued", "message": "Regenerating prompts with style preset: " + project.style_preset}

@router.get("/projects/{project_id}/export")
async def export_prompts(
    project_id: str,
    format: str = Query("txt", regex="^(txt|csv|json)$"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AudioPromptProject).where(
            AudioPromptProject.id == project_id,
            AudioPromptProject.user_id == current_user.id
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    scenes_res = await db.execute(
        select(PromptScene)
        .where(PromptScene.project_id == project_id)
        .order_by(PromptScene.scene_index)
    )
    scenes = scenes_res.scalars().all()

    if format == "json":
        data = [
            {
                "scene": s.scene_index,
                "start": s.start_time,
                "end": s.end_time,
                "duration": s.duration,
                "transcript": s.transcript_text,
                "image_prompt": s.image_prompt,
                "negative_prompt": s.negative_prompt,
                "aspect_ratio": s.aspect_ratio
            }
            for s in scenes
        ]
        content = json.dumps(data, indent=2)
        return Response(content=content, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="prompts_{project.id[:8]}.json"'})

    elif format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Scene", "Start", "End", "Duration", "Transcript", "Image Prompt", "Negative Prompt"])
        for s in scenes:
            writer.writerow([s.scene_index, s.start_time, s.end_time, s.duration, s.transcript_text, s.image_prompt, s.negative_prompt])
        return Response(content=out.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="prompts_{project.id[:8]}.csv"'})

    else:
        # plain TXT (one prompt per line, clean for Bulk Generator)
        lines = [s.image_prompt for s in scenes]
        content = "\n".join(lines)
        return Response(content=content, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="prompts_{project.id[:8]}.txt"'})

@router.delete("/projects/{project_id}")
async def delete_prompt_project(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AudioPromptProject).where(
            AudioPromptProject.id == project_id,
            AudioPromptProject.user_id == current_user.id
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    await db.delete(project)
    await db.commit()
    return {"status": "deleted"}
