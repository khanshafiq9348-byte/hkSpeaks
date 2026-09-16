from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, generate_uuid, utc_now

class VideoProject(Base):
    __tablename__ = 'video_projects'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False, default='Untitled Documentary')
    description: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(50), default='draft', index=True)  # draft, processing, ready, rendering, completed, failed
    aspect_ratio: Mapped[str] = mapped_column(String(20), default='16:9')  # 16:9, 9:16, 1:1
    resolution: Mapped[str] = mapped_column(String(20), default='1080p')  # 720p, 1080p, 4k
    fps: Mapped[int] = mapped_column(Integer, default=30)
    total_duration: Mapped[float] = mapped_column(Float, default=0.0)
    settings_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped['User'] = relationship('User')
    assets: Mapped[List['VideoAsset']] = relationship('VideoAsset', back_populates='project', cascade='all, delete-orphan')
    voiceover: Mapped[Optional['Voiceover']] = relationship('Voiceover', back_populates='project', uselist=False, cascade='all, delete-orphan')
    scenes: Mapped[List['Scene']] = relationship('Scene', back_populates='project', cascade='all, delete-orphan', order_by='Scene.scene_index')
    timeline_clips: Mapped[List['TimelineClip']] = relationship('TimelineClip', back_populates='project', cascade='all, delete-orphan', order_by='TimelineClip.clip_index')
    transitions: Mapped[List['TimelineTransition']] = relationship('TimelineTransition', back_populates='project', cascade='all, delete-orphan')
    render_jobs: Mapped[List['RenderJob']] = relationship('RenderJob', back_populates='project', cascade='all, delete-orphan')
    render_outputs: Mapped[List['RenderOutput']] = relationship('RenderOutput', back_populates='project', cascade='all, delete-orphan')

class VideoAsset(Base):
    __tablename__ = 'video_assets'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), index=True)
    asset_type: Mapped[str] = mapped_column(String(20), index=True)  # image, voiceover
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), default='application/octet-stream')
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='assets')
    image_analysis: Mapped[Optional['ImageAnalysis']] = relationship('ImageAnalysis', back_populates='asset', uselist=False, cascade='all, delete-orphan')

class Voiceover(Base):
    __tablename__ = 'voiceovers'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), unique=True, index=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_assets.id', ondelete='CASCADE'), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_rate: Mapped[int] = mapped_column(Integer, default=44100)
    channels: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(50), default='ready')  # uploaded, analyzing, ready, failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='voiceover')
    asset: Mapped['VideoAsset'] = relationship('VideoAsset')
    transcript_segments: Mapped[List['TranscriptSegment']] = relationship('TranscriptSegment', back_populates='voiceover', cascade='all, delete-orphan', order_by='TranscriptSegment.segment_index')

class TranscriptSegment(Base):
    __tablename__ = 'transcript_segments'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    voiceover_id: Mapped[str] = mapped_column(String(36), ForeignKey('voiceovers.id', ondelete='CASCADE'), index=True)
    segment_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default='')
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    keywords_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    voiceover: Mapped['Voiceover'] = relationship('Voiceover', back_populates='transcript_segments')

class ImageAnalysis(Base):
    __tablename__ = 'image_analyses'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_assets.id', ondelete='CASCADE'), unique=True, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    tags_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default='')
    dominant_colors_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    aspect_ratio: Mapped[float] = mapped_column(Float, default=1.777)
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    asset: Mapped['VideoAsset'] = relationship('VideoAsset', back_populates='image_analysis')

class Scene(Base):
    __tablename__ = 'scenes'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    scene_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(150), default='Scene')
    narrative_text: Mapped[str] = mapped_column(Text, default='')
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    primary_asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('video_assets.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='scenes')
    primary_asset: Mapped[Optional['VideoAsset']] = relationship('VideoAsset')
    timeline_clips: Mapped[List['TimelineClip']] = relationship('TimelineClip', back_populates='scene')

class TimelineClip(Base):
    __tablename__ = 'timeline_clips'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    scene_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True, index=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_assets.id', ondelete='CASCADE'), index=True)
    track_index: Mapped[int] = mapped_column(Integer, default=0)
    clip_index: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    motion_type: Mapped[str] = mapped_column(String(50), default='pan_zoom')  # pan_zoom, zoom_in, zoom_out, pan_left, pan_right, ken_burns, static
    scale_factor: Mapped[float] = mapped_column(Float, default=1.15)
    framing: Mapped[str] = mapped_column(String(50), default='cover')  # cover, contain, fill
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='timeline_clips')
    scene: Mapped[Optional['Scene']] = relationship('Scene', back_populates='timeline_clips')
    asset: Mapped['VideoAsset'] = relationship('VideoAsset')
    effects: Mapped[List['TimelineEffect']] = relationship('TimelineEffect', back_populates='clip', cascade='all, delete-orphan')

class TimelineTransition(Base):
    __tablename__ = 'timeline_transitions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    from_clip_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    to_clip_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    transition_type: Mapped[str] = mapped_column(String(50), default='crossfade')  # crossfade, fade_black, dissolve, cut
    duration: Mapped[float] = mapped_column(Float, default=0.5)
    offset_time: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='transitions')

class TimelineEffect(Base):
    __tablename__ = 'timeline_effects'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    clip_id: Mapped[str] = mapped_column(String(36), ForeignKey('timeline_clips.id', ondelete='CASCADE'), index=True)
    effect_type: Mapped[str] = mapped_column(String(50), default='cinematic_grade')  # cinematic_grade, vignette, film_grain, none
    intensity: Mapped[float] = mapped_column(Float, default=0.5)
    parameters_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    clip: Mapped['TimelineClip'] = relationship('TimelineClip', back_populates='effects')

class RenderJob(Base):
    __tablename__ = 'render_jobs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(50), default='queued', index=True)  # queued, analyzing, transcribing, matching_images, building_timeline, rendering, completed, failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_step: Mapped[str] = mapped_column(String(100), default='Queued')
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[str] = mapped_column(String(20), default='1080p')
    aspect_ratio: Mapped[str] = mapped_column(String(20), default='16:9')
    fps: Mapped[int] = mapped_column(Integer, default=30)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='render_jobs')
    output: Mapped[Optional['RenderOutput']] = relationship('RenderOutput', back_populates='render_job', uselist=False, cascade='all, delete-orphan')

class RenderOutput(Base):
    __tablename__ = 'render_outputs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('video_projects.id', ondelete='CASCADE'), index=True)
    render_job_id: Mapped[str] = mapped_column(String(36), ForeignKey('render_jobs.id', ondelete='CASCADE'), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    download_url: Mapped[str] = mapped_column(String(512), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    format: Mapped[str] = mapped_column(String(20), default='mp4')
    codec: Mapped[str] = mapped_column(String(20), default='h264')
    resolution: Mapped[str] = mapped_column(String(20), default='1920x1080')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['VideoProject'] = relationship('VideoProject', back_populates='render_outputs')
    render_job: Mapped['RenderJob'] = relationship('RenderJob', back_populates='output')
