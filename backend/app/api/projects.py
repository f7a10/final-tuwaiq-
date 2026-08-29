# ==========================================
# Projects API Routes - Enhanced with AI Layout
# ==========================================

import os
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.app.models.database import get_db, User, Project
from backend.app.auth.dependencies import require_auth
from backend.app.config import UPLOAD_DIR
from backend.app.services.dxf_service import DxfService

router = APIRouter(prefix="/api", tags=["projects"])

# Initialize Services
dxf_service = DxfService()


@router.get("/projects/me")
async def get_my_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    search: str = None,
    status_filter: str = None,  # all, compliant, non_compliant
    skip: int = 0,
    limit: int = 50
):
    """Get projects for the currently logged-in user."""
    query = db.query(Project).filter(Project.owner_id == current_user.id)
    
    # Apply search filter
    if search:
        query = query.filter(Project.title.ilike(f"%{search}%"))
    
    # Apply status filter
    if status_filter and status_filter != "all":
        if status_filter == "compliant":
            query = query.filter(Project.compliance_status == "compliant")
        elif status_filter == "non_compliant":
            query = query.filter(Project.compliance_status == "non_compliant")
    
    # Get total count
    total = query.count()
    
    # Order by newest first and paginate
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "projects": [
            {
                "id": p.id,
                "task_id": p.task_id,
                "title": p.title,
                "original_image_url": p.original_image_url,
                "analyzed_image_url": p.analyzed_image_url,
                "status": p.status,
                "compliance_status": p.compliance_status,
                "compliance_score": p.compliance_score,
                "rooms_count": p.rooms_count,
                "violations_count": p.violations_count,
                "analysis_error_code": p.analysis_error_code,
                "analysis_error_message": p.analysis_error_message,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in projects
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get a specific project by ID."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    return {
        "id": project.id,
        "task_id": project.task_id,
        "title": project.title,
        "original_image_url": project.original_image_url,
        "analyzed_image_url": project.analyzed_image_url,
        "status": project.status,
        "compliance_status": project.compliance_status,
        "compliance_score": project.compliance_score,
        "rooms_count": project.rooms_count,
        "violations_count": project.violations_count,
        "analysis_error_code": project.analysis_error_code,
        "analysis_error_message": project.analysis_error_message,
        "rooms_data": json.loads(project.rooms_data) if project.rooms_data else [],
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None
    }


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    db.delete(project)
    db.commit()
    
    # Update user's plans count
    user.plans_count = db.query(Project).filter(
        Project.owner_id == user.id, 
        Project.status == "completed"
    ).count()
    db.commit()
    
    return {"message": "تم حذف المشروع بنجاح"}


@router.get("/download/{task_id}")
async def download_image(task_id: str):
    """Download the analyzed image."""
    # Try analyzed image first
    analyzed_path = f"{UPLOAD_DIR}/{task_id}_analyzed.jpg"
    if os.path.exists(analyzed_path):
        return FileResponse(
            analyzed_path, 
            media_type="application/octet-stream", 
            filename=f"Emad_Analysis_{task_id}.jpg"
        )
    
    # Fallback to original upload
    for ext in ["png", "jpg", "jpeg", "pdf"]:
        file_path = f"{UPLOAD_DIR}/{task_id}.{ext}"
        if os.path.exists(file_path):
            return FileResponse(
                file_path, 
                media_type="application/octet-stream", 
                filename=f"Emad_Plan_{task_id}.{ext}"
            )
    
    return JSONResponse({"error": "Image not found"}, status_code=404)


@router.get("/projects/dxf/{task_id}")
async def get_project_dxf_by_task(
    task_id: str,
    mode: Literal["original"] = "original",
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Export the detected layout by task ID without automated corrections."""
    project = db.query(Project).filter(
        Project.task_id == task_id,
        Project.owner_id == user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    rooms_data = json.loads(project.rooms_data) if project.rooms_data else []
    if not rooms_data:
        raise HTTPException(status_code=400, detail="لا توجد بيانات غرف متاحة")

    filename = f"{project.task_id}_original.dxf"
    output_path = os.path.join(UPLOAD_DIR, filename)
    try:
        dxf_service.generate_dxf(rooms_data, output_path, use_fixes=False)
    except Exception as error:
        raise HTTPException(status_code=500, detail="فشل إنشاء ملف DXF") from error

    return FileResponse(
        output_path,
        media_type="application/dxf",
        filename=f"Emad_original_{project.task_id}.dxf",
    )

@router.get("/projects/{project_id}/dxf")
async def get_project_dxf(
    project_id: int,
    mode: Literal["original"] = "original",
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Export the detected layout without applying automated corrections."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    rooms_data = json.loads(project.rooms_data) if project.rooms_data else []
    if not rooms_data:
        raise HTTPException(status_code=400, detail="لا توجد بيانات غرف متاحة لهذا المشروع")

    filename = f"{project.task_id}_original.dxf"
    output_path = os.path.join(UPLOAD_DIR, filename)
    try:
        dxf_service.generate_dxf(rooms_data, output_path, use_fixes=False)
    except Exception as error:
        raise HTTPException(status_code=500, detail="فشل إنشاء ملف DXF") from error

    return FileResponse(
        output_path,
        media_type="application/dxf",
        filename=f"Emad_original_{project.task_id}.dxf",
    )
