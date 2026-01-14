# ==========================================
# Projects API Routes - Enhanced with AI Layout
# ==========================================

import os
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.app.models.database import get_db, User, Project
from backend.app.auth.dependencies import require_auth
from backend.app.config import UPLOAD_DIR
from backend.app.services.dxf_service import DxfService
from backend.app.services.ai_layout_service import AILayoutService

router = APIRouter(prefix="/api", tags=["projects"])

# Initialize Services
dxf_service = DxfService()
ai_layout_service = AILayoutService()


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


from pydantic import BaseModel
from typing import Optional

class GenerateLayoutRequest(BaseModel):
    rooms: list[dict]  # [{ "type": "Bedroom", "width": 4, "length": 5 }]
    validate: bool = True  # Whether to validate and auto-correct dimensions


class ValidateRoomRequest(BaseModel):
    type: str
    width: float
    length: float


@router.get("/projects/dxf/{task_id}")
async def get_project_dxf_by_task(
    task_id: str,
    mode: str = "original",
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Download DXF by Task ID (UUID)."""
    project = db.query(Project).filter(
        Project.task_id == task_id,
        Project.owner_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
        
    # Redirect to the main function logic or duplicate it briefly
    rooms_data = json.loads(project.rooms_data) if project.rooms_data else []
    
    if not rooms_data:
        raise HTTPException(status_code=400, detail="لا توجد بيانات غرف متاحة")
        
    filename = f"{project.task_id}_{mode}.dxf"
    output_path = os.path.join(UPLOAD_DIR, filename)
    use_fixes = (mode == "corrected")
    
    try:
        dxf_service.generate_dxf(rooms_data, output_path, use_fixes=use_fixes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل إنشاء ملف DXF: {e}")
        
    return FileResponse(
        output_path, 
        media_type="application/dxf", 
        filename=f"Emad_{mode}_{project.task_id}.dxf"
    )

@router.get("/projects/{project_id}/dxf")
async def get_project_dxf(
    project_id: int,
    mode: str = "original", # "original" or "corrected"
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate and download DXF for a project.
    Mode: 
    - 'original': Exports the layout as detected from the image.
    - 'corrected': Exports the layout with auto-applied fixes for compliance.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
        
    rooms_data = json.loads(project.rooms_data) if project.rooms_data else []
    
    if not rooms_data:
        raise HTTPException(status_code=400, detail="لا توجد بيانات غرف متاحة لهذا المشروع")
        
    filename = f"{project.task_id}_{mode}.dxf"
    output_path = os.path.join(UPLOAD_DIR, filename)
    
    use_fixes = (mode == "corrected")
    
    # Generate DXF
    try:
        dxf_service.generate_dxf(rooms_data, output_path, use_fixes=use_fixes)
    except Exception as e:
        print(f"DXF Generation Error: {e}")
        raise HTTPException(status_code=500, detail=f"فشل إنشاء ملف DXF: {e}")
        
    return FileResponse(
        output_path, 
        media_type="application/dxf", 
        filename=f"Emad_{mode}_{project.task_id}.dxf"
    )


@router.post("/validate-room")
async def validate_room(request: ValidateRoomRequest):
    """
    Validate a single room against SBC requirements using RAG.
    Returns compliance status and recommendations.
    """
    try:
        room_data = {
            "type": request.type,
            "width": request.width,
            "length": request.length
        }
        
        result = ai_layout_service.validate_room(room_data)
        return result
        
    except Exception as e:
        print(f"Room validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-correct")
async def smart_correct_room(request: ValidateRoomRequest):
    """
    Use LLM + RAG to provide intelligent correction suggestions for a room.
    Returns AI-generated recommendations with optimal dimensions.
    """
    try:
        result = ai_layout_service.get_smart_correction(
            room_type=request.type,
            current_width=request.width,
            current_length=request.length
        )
        return result
        
    except Exception as e:
        print(f"Smart correction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-dxf")
async def generate_dxf_from_text(
    request: GenerateLayoutRequest,
    user: User = Depends(require_auth)
):
    """
    Generate a new DXF layout from text requirements.
    Uses AI Layout Service for intelligent placement and validation.
    Input: List of room specs [{"type": "Bedroom", "width": 4, "length": 5}]
    """
    import uuid
    task_id = f"gen_{uuid.uuid4()}"
    filename = f"{task_id}.dxf"
    output_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        # Use AI Layout Service for smart planning
        layout_plan = ai_layout_service.plan_layout(request.rooms, validate=request.validate)
        
        # Generate DXF with validation results
        dxf_service.generate_custom_dxf(
            layout_plan["rooms"], 
            output_path,
            validation_results=layout_plan.get("validation_results")
        )
        
    except Exception as e:
        print(f"DXF generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    return FileResponse(
        output_path,
        media_type="application/dxf",
        filename="Emad_Generated_Layout.dxf"
    )
