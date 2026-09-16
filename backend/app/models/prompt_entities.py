from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, generate_uuid, utc_now

class AudioPromptProject(Base):
    __tablename__ = 'audio_prompt_projects'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False, default='Untitled Audio Project')
    audio_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    audio_url: Mapped[str] = mapped_column(String(512), nullable=False)
    total_duration: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default='uploaded', index=True)  # uploaded, transcribing, generating, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_scenes: Mapped[int] = mapped_column(Integer, default=0)
    style_preset: Mapped[str] = mapped_column(String(50), default='cinematic')
    settings_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped['User'] = relationship('User')
    scenes: Mapped[List['PromptScene']] = relationship('PromptScene', back_populates='project', cascade='all, delete-orphan', order_by='PromptScene.scene_index')

class PromptScene(Base):
    __tablename__ = 'prompt_scenes'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('audio_prompt_projects.id', ondelete='CASCADE'), index=True)
    scene_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, default='')
    image_prompt: Mapped[str] = mapped_column(Text, default='')
    negative_prompt: Mapped[str] = mapped_column(Text, default='')
    aspect_ratio: Mapped[str] = mapped_column(String(20), default='16:9')
    keywords_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped['AudioPromptProject'] = relationship('AudioPromptProject', back_populates='scenes')
