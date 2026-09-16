from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.entities import User, Project, ProjectDocument
from app.schemas.api import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectDocumentCreate, ProjectDocumentUpdate, ProjectDocumentResponse
)
from app.security.auth import get_current_user
from app.core.errors import AppException, ErrorCode

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project)
        .where(Project.owner_user_id == current_user.id)
        .options(selectinload(Project.documents))
        .order_by(Project.updated_at.desc())
    )
    return result.scalars().all()

@router.post("", response_model=ProjectResponse)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = Project(
        owner_user_id=current_user.id,
        name=body.name,
        description=body.description or ""
    )
    db.add(project)
    await db.flush()

    # Create default document
    initial_doc = ProjectDocument(
        project_id=project.id,
        title="Chapter 1 / Section 1",
        content="Welcome to your new audio project. Start typing or paste your script here."
    )
    db.add(initial_doc)
    await db.commit()

    # Reload with documents
    res = await db.execute(
        select(Project).where(Project.id == project.id).options(selectinload(Project.documents))
    )
    return res.scalar_one()

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.documents))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    if project.owner_user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.documents))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    if project.owner_user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description

    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Project not found.")

    if project.owner_user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted successfully."}

@router.post("/{project_id}/documents", response_model=ProjectDocumentResponse)
async def create_document(
    project_id: str,
    body: ProjectDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.owner_user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    doc = ProjectDocument(
        project_id=project_id,
        title=body.title,
        content=body.content,
        language=body.language,
        voice_id=body.voice_id,
        settings_json=body.settings_json or {}
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc

@router.put("/{project_id}/documents/{doc_id}", response_model=ProjectDocumentResponse)
async def update_document(
    project_id: str,
    doc_id: str,
    body: ProjectDocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.owner_user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    d_res = await db.execute(select(ProjectDocument).where(ProjectDocument.id == doc_id, ProjectDocument.project_id == project_id))
    doc = d_res.scalar_one_or_none()
    if not doc:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Document not found.")

    if body.title is not None:
        doc.title = body.title
    if body.content is not None:
        doc.content = body.content
    if body.language is not None:
        doc.language = body.language
    if body.voice_id is not None:
        doc.voice_id = body.voice_id
    if body.settings_json is not None:
        doc.settings_json = body.settings_json

    doc.version += 1
    await db.commit()
    await db.refresh(doc)
    return doc

@router.delete("/{project_id}/documents/{doc_id}")
async def delete_document(
    project_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.owner_user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    d_res = await db.execute(select(ProjectDocument).where(ProjectDocument.id == doc_id, ProjectDocument.project_id == project_id))
    doc = d_res.scalar_one_or_none()
    if not doc:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Document not found.")

    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted successfully."}
