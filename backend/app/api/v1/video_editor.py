import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from PIL import Image
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.entities import User
from app.models.video_entities import (
    VideoProject, VideoAsset, Voiceover, TranscriptSegment,
    Scene, ImageAnalysis, TimelineClip, TimelineTransition, TimelineEffect,
    RenderJob, RenderOutput
)
from app.schemas.video_api import (
    VideoProjectCreate, VideoProjectUpdate, VideoProjectSummaryResponse,
    VideoProjectDetailResponse, VideoAssetResponse, VoiceoverResponse,
    SceneResponse, TimelineClipResponse, TimelineTransitionResponse,
    TimelineUpdateRequest, RenderSubmitRequest, RenderJobResponse, RenderOutputResponse
)
from app.security.auth import get_current_user, get_current_user_or_default
from app.services.storage import storage_service
from app.video.engine import documentary_engine
from app.workers.video_processor import video_render_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video-editor", tags=["AI Video Editor"])

@router.post("/projects", response_model=VideoProjectSummaryResponse)
async def create_project(
    data: VideoProjectCreate,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    project = VideoProject(
        user_id=current_user.id,
        title=data.title,
        description=data.description or "",
        aspect_ratio=data.aspect_ratio,
        resolution=data.resolution,
        fps=data.fps,
        status="draft"
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return VideoProjectSummaryResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        aspect_ratio=project.aspect_ratio,
        resolution=project.resolution,
        fps=project.fps,
        total_duration=project.total_duration,
        assets_count=0,
        scenes_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.get("/projects", response_model=List[VideoProjectSummaryResponse])
async def list_projects(
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject)
        .where((VideoProject.user_id == current_user.id) | (VideoProject.user_id == "default_user"))
        .options(
            selectinload(VideoProject.assets),
            selectinload(VideoProject.scenes)
        )
        .order_by(desc(VideoProject.created_at))
    )
    projects = res.scalars().all()
    out = []
    for p in projects:
        thumbnail = None
        for a in p.assets:
            if a.asset_type == "image":
                thumbnail = a.url
                break
        out.append(
            VideoProjectSummaryResponse(
                id=p.id,
                title=p.title,
                description=p.description,
                status=p.status,
                aspect_ratio=p.aspect_ratio,
                resolution=p.resolution,
                fps=p.fps,
                total_duration=p.total_duration,
                assets_count=len(p.assets),
                scenes_count=len(p.scenes),
                thumbnail_url=thumbnail,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
        )
    return out

@router.get("/projects/{project_id}", response_model=VideoProjectDetailResponse)
async def get_project_details(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(
            selectinload(VideoProject.assets),
            selectinload(VideoProject.voiceover),
            selectinload(VideoProject.scenes).selectinload(Scene.primary_asset),
            selectinload(VideoProject.timeline_clips).selectinload(TimelineClip.asset),
            selectinload(VideoProject.transitions),
            selectinload(VideoProject.render_outputs),
            selectinload(VideoProject.render_jobs)
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Documentary project not found.")

    latest_job = None
    if project.render_jobs:
        sorted_jobs = sorted(project.render_jobs, key=lambda j: j.created_at, reverse=True)
        latest_job = sorted_jobs[0]

    return VideoProjectDetailResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        aspect_ratio=project.aspect_ratio,
        resolution=project.resolution,
        fps=project.fps,
        total_duration=project.total_duration,
        assets=[VideoAssetResponse.model_validate(a) for a in project.assets],
        voiceover=VoiceoverResponse.model_validate(project.voiceover) if project.voiceover else None,
        scenes=[
            SceneResponse(
                id=s.id,
                project_id=s.project_id,
                scene_index=s.scene_index,
                title=s.title,
                narrative_text=s.narrative_text,
                start_time=s.start_time,
                end_time=s.end_time,
                duration=s.duration,
                primary_asset_id=s.primary_asset_id,
                primary_asset=VideoAssetResponse.model_validate(s.primary_asset) if s.primary_asset else None
            ) for s in project.scenes
        ],
        timeline_clips=[
            TimelineClipResponse(
                id=c.id,
                project_id=c.project_id,
                scene_id=c.scene_id,
                asset_id=c.asset_id,
                track_index=c.track_index,
                clip_index=c.clip_index,
                start_time=c.start_time,
                end_time=c.end_time,
                duration=c.duration,
                motion_type=c.motion_type,
                scale_factor=c.scale_factor,
                framing=c.framing,
                asset=VideoAssetResponse.model_validate(c.asset) if c.asset else None
            ) for c in project.timeline_clips
        ],
        transitions=[TimelineTransitionResponse.model_validate(t) for t in project.transitions],
        render_outputs=[RenderOutputResponse.model_validate(o) for o in project.render_outputs],
        latest_render=RenderJobResponse.model_validate(latest_job) if latest_job else None,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.put("/projects/{project_id}", response_model=VideoProjectSummaryResponse)
async def update_project(
    project_id: str,
    data: VideoProjectUpdate,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if data.title is not None:
        project.title = data.title
    if data.description is not None:
        project.description = data.description
    if data.aspect_ratio is not None:
        project.aspect_ratio = data.aspect_ratio
    if data.resolution is not None:
        project.resolution = data.resolution
    if data.fps is not None:
        project.fps = data.fps

    await db.commit()
    await db.refresh(project)
    return VideoProjectSummaryResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        aspect_ratio=project.aspect_ratio,
        resolution=project.resolution,
        fps=project.fps,
        total_duration=project.total_duration,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    await db.delete(project)
    await db.commit()
    return {"status": "deleted", "id": project_id}

@router.post("/projects/{project_id}/assets", response_model=List[VideoAssetResponse])
async def upload_assets(
    project_id: str,
    files: List[UploadFile] = File(...),
    asset_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    created_assets = []
    base_time = datetime.now(timezone.utc)
    for idx, file in enumerate(files):
        file_bytes = await file.read()
        filename = file.filename or "uploaded_asset"
        ext = os.path.splitext(filename)[1].lower()

        # Determine asset type if not provided
        determined_type = asset_type
        if not determined_type:
            if ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]:
                determined_type = "voiceover"
            else:
                determined_type = "image"

        storage_key = f"users/{current_user.id}/video_projects/{project.id}/assets/{uuid.uuid4().hex[:12]}_{filename}"
        mime_type = file.content_type or ("audio/mpeg" if ext == ".mp3" else "image/jpeg")

        url = await storage_service.upload_audio(storage_key, file_bytes, mime_type)
        if url.startswith("/v1/storage"):
            url = f"http://localhost:8000{url}"

        asset_time = base_time + timedelta(milliseconds=idx * 10)
        asset = VideoAsset(
            project_id=project.id,
            user_id=current_user.id,
            asset_type=determined_type,
            filename=filename,
            storage_key=storage_key,
            url=url,
            file_size=len(file_bytes),
            mime_type=mime_type,
            created_at=asset_time
        )
        db.add(asset)
        await db.flush()

        local_path = storage_service.get_local_path(storage_key)

        if determined_type == "image" and local_path:
            w, h = 1920, 1080
            try:
                with Image.open(local_path) as img:
                    w, h = img.size
            except Exception:
                pass
            asset.width = w
            asset.height = h

        elif determined_type == "voiceover" and local_path:
            probe = documentary_engine.probe_audio(local_path)
            asset.duration = probe["duration"]
            project.total_duration = probe["duration"]

            # Replace or set voiceover
            vo_res = await db.execute(select(Voiceover).where(Voiceover.project_id == project.id))
            existing_vo = vo_res.scalar_one_or_none()
            if existing_vo:
                existing_vo.asset_id = asset.id
                existing_vo.filename = filename
                existing_vo.storage_key = storage_key
                existing_vo.url = url
                existing_vo.duration = probe["duration"]
                existing_vo.sample_rate = probe["sample_rate"]
                existing_vo.channels = probe["channels"]
            else:
                new_vo = Voiceover(
                    project_id=project.id,
                    asset_id=asset.id,
                    filename=filename,
                    storage_key=storage_key,
                    url=url,
                    duration=probe["duration"],
                    sample_rate=probe["sample_rate"],
                    channels=probe["channels"],
                    status="ready"
                )
                db.add(new_vo)

        created_assets.append(asset)

    await db.commit()
    for a in created_assets:
        await db.refresh(a)

    return [VideoAssetResponse.model_validate(a) for a in created_assets]

@router.delete("/projects/{project_id}/assets/{asset_id}")
async def delete_asset(
    project_id: str,
    asset_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoAsset).where(
            VideoAsset.id == asset_id,
            VideoAsset.project_id == project_id
        )
    )
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    await db.delete(asset)
    await db.commit()
    return {"status": "deleted", "id": asset_id}

@router.post("/projects/{project_id}/generate", response_model=VideoProjectDetailResponse)
async def generate_documentary_timeline(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    """
    Automated Documentary Director:
    1. Probes & segments voiceover audio sentence-by-sentence
    2. Strictly preserves uploaded images in EXACT upload order:
       Image 1 -> Sentence 1
       Image 2 -> Sentence 2
       Image 3 -> Sentence 3
       Image 4 -> Sentence 4
       ...etc.
    3. ONLY adjusts TIMELINE timestamps and durations according to voiceover
    4. Applies cinematic Ken Burns motion & transitions
    """
    res = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(
            selectinload(VideoProject.assets),
            selectinload(VideoProject.voiceover),
            selectinload(VideoProject.scenes),
            selectinload(VideoProject.timeline_clips),
            selectinload(VideoProject.transitions)
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.voiceover:
        raise HTTPException(status_code=400, detail="Voiceover audio is required before generating documentary.")

    image_assets = [a for a in project.assets if a.asset_type == "image"]
    if not image_assets:
        raise HTTPException(status_code=400, detail="At least one image asset is required to generate a documentary.")

    # CRITICAL: Preserve EXACT upload order
    image_assets.sort(key=lambda a: a.created_at)

    vo_path = storage_service.get_local_path(project.voiceover.storage_key)
    if not vo_path or not os.path.exists(vo_path):
        raise HTTPException(status_code=404, detail="Voiceover audio file is missing on storage.")

    # 1. Analyze voiceover duration
    probe = documentary_engine.probe_audio(vo_path)
    total_dur = probe["duration"]
    project.total_duration = total_dur
    project.voiceover.duration = total_dur

    # 2. Segment voiceover sentence-by-sentence strictly matching sequential images
    segments = documentary_engine.segment_audio_for_sequential_images(
        audio_path=vo_path,
        total_duration=total_dur,
        num_images=len(image_assets),
        script_text=project.description or ""
    )

    # 3. Clear old scenes, clips, and transitions
    for c in list(project.timeline_clips):
        await db.delete(c)
    for s in list(project.scenes):
        await db.delete(s)
    for t in list(project.transitions):
        await db.delete(t)
    await db.flush()

    # 4. Build sequential image dictionaries in EXACT order
    img_dicts = []
    for a in image_assets:
        img_dicts.append({
            "id": a.id,
            "filename": a.filename,
            "url": a.url,
            "tags": [],
            "aspect_ratio": round((a.width or 1920) / max(1, a.height or 1080), 3),
            "dominant_colors": ["#1e293b", "#0f172a"],
            "width": a.width or 1920,
            "height": a.height or 1080,
            "description": a.filename
        })

    timeline_data = documentary_engine.generate_timeline(total_dur, segments, img_dicts)

    # 5. Save Scenes & Clips
    scene_map = {}
    new_scenes = []
    for s_dict in timeline_data["scenes"]:
        sc = Scene(
            project_id=project.id,
            scene_index=s_dict["scene_index"],
            title=s_dict["title"],
            narrative_text=s_dict["narrative_text"],
            start_time=s_dict["start_time"],
            end_time=s_dict["end_time"],
            duration=s_dict["duration"],
            primary_asset_id=s_dict["primary_asset_id"]
        )
        db.add(sc)
        await db.flush()
        scene_map[s_dict["id"]] = sc.id
        new_scenes.append(sc)

    clip_id_map = {}
    new_clips = []
    for c_dict in timeline_data["timeline_clips"]:
        assigned_scene_id = scene_map.get(c_dict["scene_id"])
        clip = TimelineClip(
            project_id=project.id,
            scene_id=assigned_scene_id,
            asset_id=c_dict["asset_id"],
            track_index=0,
            clip_index=c_dict["clip_index"],
            start_time=c_dict["start_time"],
            end_time=c_dict["end_time"],
            duration=c_dict["duration"],
            motion_type=c_dict["motion_type"],
            scale_factor=1.15,
            framing="cover"
        )
        db.add(clip)
        await db.flush()
        clip_id_map[c_dict["id"]] = clip.id
        new_clips.append(clip)

        eff = TimelineEffect(
            clip=clip,
            effect_type="cinematic_grade",
            intensity=0.5
        )
        db.add(eff)

    new_transitions = []
    for t_dict in timeline_data["transitions"]:
        from_id = clip_id_map.get(t_dict["from_clip_id"])
        to_id = clip_id_map.get(t_dict["to_clip_id"])
        tr = TimelineTransition(
            project_id=project.id,
            from_clip_id=from_id,
            to_clip_id=to_id,
            transition_type=t_dict["transition_type"],
            duration=t_dict["duration"],
            offset_time=t_dict["offset_time"]
        )
        db.add(tr)
        new_transitions.append(tr)

    project.scenes = new_scenes
    project.timeline_clips = new_clips
    project.transitions = new_transitions
    project.status = "ready"
    await db.commit()

    return await get_project_details(project_id, current_user, db)

@router.put("/projects/{project_id}/timeline", response_model=VideoProjectDetailResponse)
async def update_timeline(
    project_id: str,
    payload: TimelineUpdateRequest,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(selectinload(VideoProject.timeline_clips))
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Update clips in place
    clip_map = {c.id: c for c in project.timeline_clips}
    for item in payload.clips:
        if item.id in clip_map:
            c = clip_map[item.id]
            c.asset_id = item.asset_id
            c.start_time = item.start_time
            c.end_time = item.end_time
            c.duration = item.duration
            c.motion_type = item.motion_type
            c.scale_factor = item.scale_factor
            c.framing = item.framing

    await db.commit()
    return await get_project_details(project_id, current_user, db)

@router.post("/projects/{project_id}/render", response_model=RenderJobResponse)
async def submit_render_job(
    project_id: str,
    payload: Optional[RenderSubmitRequest] = None,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(
            selectinload(VideoProject.voiceover),
            selectinload(VideoProject.timeline_clips)
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.voiceover:
        raise HTTPException(status_code=400, detail="Voiceover is required.")
    if not project.timeline_clips:
        raise HTTPException(status_code=400, detail="Timeline must be generated before rendering.")

    chosen_ar = payload.aspect_ratio if (payload and payload.aspect_ratio) else project.aspect_ratio
    chosen_res = payload.resolution if (payload and payload.resolution) else project.resolution
    chosen_fps = payload.fps if (payload and payload.fps) else project.fps

    job = RenderJob(
        project_id=project.id,
        user_id=current_user.id,
        status="queued",
        progress=0.0,
        current_step="Queued for rendering...",
        resolution=chosen_res,
        aspect_ratio=chosen_ar,
        fps=chosen_fps
    )
    db.add(job)
    project.status = "rendering"
    await db.commit()
    await db.refresh(job)

    # Enqueue to background worker
    await video_render_queue.enqueue(job.id)

    return RenderJobResponse.model_validate(job)

@router.get("/renders/{job_id}", response_model=RenderJobResponse)
async def get_render_job(
    job_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(RenderJob).where(RenderJob.id == job_id)
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found.")
    return RenderJobResponse.model_validate(job)

@router.get("/projects/{project_id}/renders", response_model=List[RenderOutputResponse])
async def list_project_renders(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(RenderOutput)
        .join(VideoProject)
        .where(RenderOutput.project_id == project_id, VideoProject.user_id == current_user.id)
        .order_by(desc(RenderOutput.created_at))
    )
    outputs = res.scalars().all()
    return [RenderOutputResponse.model_validate(o) for o in outputs]
