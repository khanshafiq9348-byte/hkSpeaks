from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, generate_uuid, utc_now

class BulkImageBatch(Base):
    __tablename__ = 'bulk_image_batches'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, default='Untitled Batch')
    status: Mapped[str] = mapped_column(String(50), default='queued', index=True)  # queued, processing, completed, failed, partial
    total_prompts: Mapped[int] = mapped_column(Integer, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    aspect_ratio: Mapped[str] = mapped_column(String(20), default='16:9')
    resolution: Mapped[str] = mapped_column(String(20), default='1080p')
    style_preset: Mapped[str] = mapped_column(String(50), default='cinematic')
    zip_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    zip_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    zip_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped['User'] = relationship('User')
    items: Mapped[List['BulkImageItem']] = relationship('BulkImageItem', back_populates='batch', cascade='all, delete-orphan', order_by='BulkImageItem.prompt_index')

class BulkImageItem(Base):
    __tablename__ = 'bulk_image_items'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey('bulk_image_batches.id', ondelete='CASCADE'), index=True)
    prompt_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='pending', index=True)  # pending, generating, completed, failed
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped['BulkImageBatch'] = relationship('BulkImageBatch', back_populates='items')
