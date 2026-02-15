"""
软著材料 API
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..copyright_service import run_copyright_generation
from ..database import get_db
from ..deps import get_current_user, get_copyright_project_for_user
from ..models import (
    CopyrightJob,
    CopyrightJobResponse,
    CopyrightProject,
    CopyrightProjectCreateRequest,
    CopyrightProjectRequirementsRequest,
    CopyrightProjectResponse,
    CopyrightProjectUpdateRequest,
    User,
)
from ..utils.paths import COPYRIGHT_ZIPS_DIR


router = APIRouter(prefix="/api/copyright", tags=["软著材料"])


def _sanitize_generation_mode(value: Optional[str]) -> str:
    if value and value.lower() in {"fast", "full"}:
        return value.lower()
    return "fast"


def _get_latest_job(db: Session, project_id: int) -> Optional[CopyrightJob]:
    return (
        db.query(CopyrightJob)
        .filter(CopyrightJob.project_id == project_id)
        .order_by(CopyrightJob.created_at.desc())
        .first()
    )


def _serialize_project(
    project: CopyrightProject,
    latest_job: Optional[CopyrightJob] = None,
) -> CopyrightProjectResponse:
    response = CopyrightProjectResponse.model_validate(project, from_attributes=True)
    if latest_job:
        response.latest_job = CopyrightJobResponse.model_validate(latest_job, from_attributes=True)
    return response


@router.post("/projects")
def create_project(
    payload: CopyrightProjectCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = CopyrightProject(
        user_id=user.id,
        name=payload.name,
        domain=payload.domain,
        system_name=payload.system_name,
        software_abbr=payload.software_abbr,
        description=payload.description,
        output_type=payload.output_type or "zip",
        generation_mode=_sanitize_generation_mode(payload.generation_mode),
        include_sourcecode=True if payload.include_sourcecode is None else payload.include_sourcecode,
        include_ui_desc=True if payload.include_ui_desc is None else payload.include_ui_desc,
        include_tech_desc=True if payload.include_tech_desc is None else payload.include_tech_desc,
        requirements_text=payload.requirements_text,
        ui_description=payload.ui_description,
        tech_description=payload.tech_description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _serialize_project(project)


@router.get("/projects")
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(CopyrightProject)
        .filter(CopyrightProject.user_id == user.id)
        .order_by(CopyrightProject.created_at.desc())
        .all()
    )
    results: List[CopyrightProjectResponse] = []
    for project in projects:
        latest_job = _get_latest_job(db, project.id)
        results.append(_serialize_project(project, latest_job))
    return {"projects": results}


@router.get("/projects/{project_id}")
def get_project_detail(
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    db: Session = Depends(get_db),
):
    latest_job = _get_latest_job(db, project.id)
    return _serialize_project(project, latest_job)


@router.put("/projects/{project_id}")
def update_project(
    payload: CopyrightProjectUpdateRequest,
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    if "generation_mode" in data:
        data["generation_mode"] = _sanitize_generation_mode(data["generation_mode"])
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    latest_job = _get_latest_job(db, project.id)
    return _serialize_project(project, latest_job)


@router.post("/projects/{project_id}/requirements")
def update_project_requirements(
    payload: CopyrightProjectRequirementsRequest,
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    latest_job = _get_latest_job(db, project.id)
    return _serialize_project(project, latest_job)


@router.get("/projects/{project_id}/jobs/latest")
async def get_latest_job(
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    wait: int = Query(0, description="长轮询等待秒数"),
    since: Optional[str] = Query(None, description="上次更新时间（ISO 格式）"),
    db: Session = Depends(get_db),
):
    job = _get_latest_job(db, project.id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到生成任务")
    if not since or wait <= 0:
        return CopyrightJobResponse.model_validate(job, from_attributes=True)

    try:
        since_time = datetime.fromisoformat(since)
    except Exception:
        return CopyrightJobResponse.model_validate(job, from_attributes=True)

    wait_seconds = max(0, min(wait, 25))
    elapsed = 0
    while elapsed < wait_seconds:
        if job.updated_at and job.updated_at > since_time:
            break
        if job.status in ("completed", "failed"):
            break
        await asyncio.sleep(1)
        elapsed += 1
        job = _get_latest_job(db, project.id)
        if not job:
            break

    return CopyrightJobResponse.model_validate(job, from_attributes=True)


@router.get("/projects/{project_id}/download")
def download_zip(
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    db: Session = Depends(get_db),
):
    job = _get_latest_job(db, project.id)
    if not job or not job.output_zip_path:
        raise HTTPException(status_code=404, detail="尚未生成可下载的 ZIP")
    path = Path(job.output_zip_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="ZIP 文件不存在")
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.post("/projects/{project_id}/generate")
async def generate_project(
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = CopyrightJob(
        project_id=project.id,
        status="queued",
        stage="preparing",
        message="已进入队列，等待开始生成...",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    asyncio.create_task(run_copyright_generation(job.id, project.id, user.id))

    return CopyrightJobResponse.model_validate(job, from_attributes=True)


@router.get("/projects/{project_id}/generate/stream")
async def generate_project_stream(
    project: CopyrightProject = Depends(get_copyright_project_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = CopyrightJob(
        project_id=project.id,
        status="queued",
        stage="preparing",
        message="已进入队列，等待开始生成...",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    asyncio.create_task(run_copyright_generation(job.id, project.id, user.id))
    return CopyrightJobResponse.model_validate(job, from_attributes=True)
