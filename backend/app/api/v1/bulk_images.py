import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.models.entities import User
from app.models.bulk_image_entities import BulkImageBatch, BulkImageItem
from app.security.auth import get_current_user, get_current_user_or_default
from app.workers.bulk_image_processor import bulk_image_queue
from app.core.errors import AppException, ErrorCode

router = APIRouter(prefix="/bulk-images", tags=["Bulk Image Generator"])

@router.post("/batches")
async def create_bulk_batch(
    body: dict,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    prompts: List[str] = body.get("prompts", [])
    if not prompts or not isinstance(prompts, list):
        raise AppException(status_code=400, error_code=ErrorCode.VALIDATION_ERROR, message="A list of prompts is required.")

    # Clean and filter non-empty prompts
    valid_prompts = [p.strip() for p in prompts if isinstance(p, str) and p.strip()]
    if len(valid_prompts) == 0:
        raise AppException(status_code=400, error_code=ErrorCode.VALIDATION_ERROR, message="At least 1 valid prompt is required.")

    name = body.get("name", "Bulk Generation Batch").strip() or f"Batch of {len(valid_prompts)} images"
    aspect_ratio = body.get("aspect_ratio", "16:9")
    resolution = body.get("resolution", "1080p")
    style_preset = body.get("style_preset", "cinematic")

    batch = BulkImageBatch(
        user_id=current_user.id,
        name=name,
        total_prompts=len(valid_prompts),
        completed_count=0,
        failed_count=0,
        progress_pct=0.0,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        style_preset=style_preset,
        status="queued"
    )
    db.add(batch)
    await db.flush()

    # Create items (supports 1,000+ items seamlessly)
    for idx, p_text in enumerate(valid_prompts, start=1):
        item = BulkImageItem(
            batch_id=batch.id,
            prompt_index=idx,
            prompt_text=p_text,
            seed=(idx * 1337 + 42) % 1000000,
            status="pending"
        )
        db.add(item)

    await db.commit()
    await db.refresh(batch)

    # Enqueue background job
    await bulk_image_queue.enqueue(batch.id)

    return {
        "id": batch.id,
        "name": batch.name,
        "title": batch.name,
        "total_prompts": batch.total_prompts,
        "total_count": batch.total_prompts,
        "completed_count": 0,
        "failed_count": 0,
        "status": batch.status,
        "aspect_ratio": batch.aspect_ratio,
        "resolution": batch.resolution,
        "style_preset": batch.style_preset,
        "message": f"Successfully queued batch of {batch.total_prompts} images for generation."
    }

@router.get("/batches")
async def list_bulk_batches(
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(BulkImageBatch)
        .where(BulkImageBatch.user_id == current_user.id)
        .order_by(BulkImageBatch.created_at.desc())
    )
    batches = res.scalars().all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "title": b.name,
            "status": b.status,
            "total_prompts": b.total_prompts,
            "total_count": b.total_prompts,
            "completed_count": b.completed_count,
            "failed_count": b.failed_count,
            "progress_pct": b.progress_pct,
            "aspect_ratio": b.aspect_ratio,
            "resolution": b.resolution,
            "zip_url": b.zip_url,
            "created_at": b.created_at.isoformat() if b.created_at else None
        }
        for b in batches
    ]

@router.get("/batches/{batch_id}")
async def get_bulk_batch(
    batch_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(60, ge=1, le=500),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(BulkImageBatch).where(
            BulkImageBatch.id == batch_id,
            BulkImageBatch.user_id == current_user.id
        )
    )
    batch = res.scalar_one_or_none()
    if not batch:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Batch not found.")

    query = select(BulkImageItem).where(BulkImageItem.batch_id == batch_id)
    if status_filter:
        query = query.where(BulkImageItem.status == status_filter)
    query = query.order_by(BulkImageItem.prompt_index).offset((page - 1) * page_size).limit(page_size)

    items_res = await db.execute(query)
    items = items_res.scalars().all()

    return {
        "id": batch.id,
        "name": batch.name,
        "title": batch.name,
        "status": batch.status,
        "total_prompts": batch.total_prompts,
        "total_count": batch.total_prompts,
        "completed_count": batch.completed_count,
        "failed_count": batch.failed_count,
        "progress_pct": batch.progress_pct,
        "aspect_ratio": batch.aspect_ratio,
        "resolution": batch.resolution,
        "style_preset": batch.style_preset,
        "zip_url": batch.zip_url,
        "zip_size_bytes": batch.zip_size_bytes,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": it.id,
                "item_index": it.prompt_index,
                "prompt_index": it.prompt_index,
                "prompt": it.prompt_text,
                "prompt_text": it.prompt_text,
                "status": it.status,
                "image_url": it.image_url,
                "seed": it.seed,
                "error_message": it.error_message
            }
            for it in items
        ]
    }

@router.post("/batches/{batch_id}/retry")
async def retry_failed_batch_items(
    batch_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(BulkImageBatch).where(
            BulkImageBatch.id == batch_id,
            BulkImageBatch.user_id == current_user.id
        )
    )
    batch = res.scalar_one_or_none()
    if not batch:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Batch not found.")

    # Reset failed items to pending
    items_res = await db.execute(
        select(BulkImageItem).where(
            BulkImageItem.batch_id == batch_id,
            BulkImageItem.status == "failed"
        )
    )
    failed_items = items_res.scalars().all()
    for it in failed_items:
        it.status = "pending"
        it.retry_count += 1
        it.error_message = None

    batch.status = "queued"
    await db.commit()

    await bulk_image_queue.enqueue(batch.id)
    return {"status": "retrying", "retried_count": len(failed_items)}

@router.get("/batches/{batch_id}/download-zip")
@router.get("/batches/{batch_id}/zip")
async def download_batch_zip(
    batch_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(BulkImageBatch).where(
            BulkImageBatch.id == batch_id,
            BulkImageBatch.user_id == current_user.id
        )
    )
    batch = res.scalar_one_or_none()
    if not batch or not batch.zip_storage_key or not os.path.exists(batch.zip_storage_key):
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="ZIP archive not found or not yet generated.")

    return FileResponse(
        path=batch.zip_storage_key,
        media_type="application/zip",
        filename=f"{batch.name.replace(' ', '_')}_{batch.id[:8]}.zip"
    )

@router.delete("/batches/{batch_id}")
async def delete_bulk_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(BulkImageBatch).where(
            BulkImageBatch.id == batch_id,
            BulkImageBatch.user_id == current_user.id
        )
    )
    batch = res.scalar_one_or_none()
    if not batch:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Batch not found.")

    await db.delete(batch)
    await db.commit()
    return {"status": "deleted"}
