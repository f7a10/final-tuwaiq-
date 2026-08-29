# ==========================================
# Emad (عماد) - AI Floor Plan Auditor Backend
# Main FastAPI Application
# ==========================================

import os
import uuid
import json
import shutil
import cv2
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

# Import from organized modules
from backend.app.config import UPLOAD_DIR, PROJECT_ROOT
from backend.app.models.database import get_db, User, Project, SessionLocal, init_db
from backend.app.auth.dependencies import require_auth
from backend.app.services.smart_architect import AnalysisPipelineError, SmartArchitect

# Import API routers
from backend.app.api import auth as auth_router
from backend.app.api import projects as projects_router
from backend.app.api import chat as chat_router
from backend.app.api import editor as editor_router

# -------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------
app = FastAPI(title="Emad - عماد", description="AI Floor Plan Auditor")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload Directory
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize SmartArchitect globally
architect = SmartArchitect()

# In-Memory Results Store
analysis_results = {}

ANALYSIS_ERROR_MESSAGES = {
    "local_model_missing": "ملف النموذج المحلي لتحليل المخططات غير مثبت. أكمل إعداد النموذج المحلي ثم أعد المحاولة.",
    "local_model_load_failed": "تعذر تحميل النموذج المحلي لتحليل المخططات. أعد إعداد النموذج ثم حاول مجددًا.",
    "local_detection_failed": "تعذر على النموذج المحلي تحليل هذا المخطط. لم تُصدر نتيجة للمخطط.",
    "wall_detection_empty": "لم يتمكن النموذج المحلي من اكتشاف شبكة جدران قابلة للتحليل.",
    "detector_provider_invalid": "إعداد مزود تحليل المخططات غير صالح. راجع إعدادات التشغيل ثم أعد المحاولة.",
    "roboflow_api_key_missing": "خدمة التحليل الخارجية مختارة لكنها غير مهيأة. راجع إعدادات التشغيل.",
    "roboflow_inference_path_missing": "تعذر تجهيز الملف لخدمة التحليل الخارجية. لم تُصدر نتيجة للمخطط.",
    "provider_credit_exhausted": "نفد رصيد خدمة تحليل المخططات. أضف رصيدًا أو ارفع حد الاستخدام ثم أعد المحاولة.",
    "structure_detection_failed": "تعذر إكمال اكتشاف الجدران والفتحات. لم تُصدر نتيجة للمخطط.",
    "room_detection_failed": "تعذر الاتصال بخدمة اكتشاف الغرف. لم تُصدر نتيجة للمخطط.",
    "room_detection_empty": "لم يتمكن النظام من اكتشاف غرف قابلة للتحليل في الملف المرفوع.",
    "compliance_failed": "تعذر إكمال فحص المتطلبات. لم تُحسب درجة امتثال للمخطط.",
    "analysis_failed": "تعذر إكمال التحليل. لم تُصدر نتيجة أو درجة امتثال.",
}


def analysis_error_details(error: Exception) -> tuple[str, str]:
    code = str(error) if isinstance(error, AnalysisPipelineError) else "analysis_failed"
    if code not in ANALYSIS_ERROR_MESSAGES:
        code = "analysis_failed"
    return code, ANALYSIS_ERROR_MESSAGES[code]


# -------------------------------------------------
# Include API Routers
# -------------------------------------------------
app.include_router(auth_router.router)
app.include_router(projects_router.router)
app.include_router(chat_router.router)
app.include_router(editor_router.router)


# -------------------------------------------------
# Background Processing Task
# -------------------------------------------------
def process_floor_plan(task_id: str, file_path: str, settings: dict, base_url: str, owner_id: int = None):
    """Background task to analyze floor plan and save annotated image."""
    print(f"Starting analysis for task: {task_id}")
    
    # Get DB session for background task
    db = SessionLocal()
    
    try:
        # Run the full analysis (with task_id for CAD Compliance RAG)
        result_data, annotated_image = architect.analyze(file_path, task_id=task_id)
        
        analyzed_url = None
        original_url = f"{base_url}/uploads/{os.path.basename(file_path)}"
        
        if annotated_image is not None:
            # Save annotated image
            output_filename = f"{task_id}_analyzed.jpg"
            output_path = os.path.join(UPLOAD_DIR, output_filename)
            cv2.imwrite(output_path, annotated_image)
            print(f"Saved annotated image: {output_path}")
            
            analyzed_url = f"{base_url}/uploads/{output_filename}"
            result_data["imageUrl"] = analyzed_url
            result_data["id"] = task_id
        else:
            result_data["imageUrl"] = original_url
            result_data["id"] = task_id
        
        # Calculate compliance
        rooms = result_data.get("rooms", [])
        rooms_count = len(rooms)
        compliant_rooms = sum(1 for r in rooms if r.get("isCompliant", False))
        violations = rooms_count - compliant_rooms
        score = result_data.get("score", 0)
        compliance_status = "compliant" if score >= 80 else "non_compliant"
        
        # Update Project in database
        project = db.query(Project).filter(Project.task_id == task_id).first()
        if project:
            project.status = "completed"
            project.analysis_error_code = None
            project.analysis_error_message = None
            project.analyzed_image_url = analyzed_url
            project.compliance_status = compliance_status
            project.compliance_score = score
            project.rooms_count = rooms_count
            project.compliant_rooms = compliant_rooms
            project.violations_count = violations
            project.rooms_data = json.dumps(rooms)
            project.completed_at = datetime.utcnow()
            db.commit()
            
            # Update user's plans count
            if project.owner_id:
                user = db.query(User).filter(User.id == project.owner_id).first()
                if user:
                    user.plans_count = db.query(Project).filter(Project.owner_id == user.id, Project.status == "completed").count()
                    db.commit()
        
        # Store completed result in memory
        analysis_results[task_id] = {
            "status": "completed",
            "result": result_data
        }
        
    except Exception as e:
        error_code, error_message = analysis_error_details(e)
        print(f"Analysis failed: {error_code}")
        
        # Update project status to failed
        project = db.query(Project).filter(Project.task_id == task_id).first()
        if project:
            project.status = "failed"
            project.analysis_error_code = error_code
            project.analysis_error_message = error_message
            project.compliance_status = None
            project.compliance_score = None
            project.rooms_count = 0
            project.compliant_rooms = 0
            project.violations_count = 0
            project.rooms_data = None
            db.commit()
        
        analysis_results[task_id] = {
            "status": "failed",
            "error_code": error_code,
            "error": error_message,
        }
    finally:
        db.close()
    
    print(f"Task {task_id} complete!")


# -------------------------------------------------
# Upload API Endpoint
# -------------------------------------------------
@app.post("/api/upload")
async def upload_plan(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    settings: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Upload floor plan and start analysis. Requires authentication."""
    task_id = str(uuid.uuid4())
    file_extension = file.filename.split(".")[-1]
    file_path = f"{UPLOAD_DIR}/{task_id}.{file_extension}"
    
    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Parse settings
    settings_dict = json.loads(settings)
    
    # Get base URL for image URLs
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/uploads/{task_id}.{file_extension}"
    
    # Get owner_id from authenticated user
    owner_id = current_user.id
    
    # Create project in database
    project = Project(
        task_id=task_id,
        owner_id=owner_id,
        title=settings_dict.get("title", file.filename or "مخطط بدون عنوان"),
        original_image_url=image_url,
        status="processing"
    )
    db.add(project)
    db.commit()
    
    # Initialize result entry in memory
    analysis_results[task_id] = {"status": "processing", "progress": 0}
    
    # Add background task
    background_tasks.add_task(process_floor_plan, task_id, file_path, settings_dict, base_url, owner_id)
    
    return {
        "status": "processing_started",
        "task_id": task_id,
        "image_url": image_url,
        "project_id": project.id,
        "message": "تم رفع الملف بنجاح. جاري التحليل..."
    }


# -------------------------------------------------
# Static Files & SPA Serving
# -------------------------------------------------
# Dist and assets paths
DIST_DIR = os.path.join(PROJECT_ROOT, "frontend", "dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

# Mount assets first
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Mount uploads directory for serving images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve Vue.js SPA."""
    if full_path.startswith("api"):
        return JSONResponse({"error": "API route not found"}, status_code=404)
    
    file_path = os.path.join(DIST_DIR, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return "Frontend build not found. Run 'cd frontend && npm run build'"


# -------------------------------------------------
# Main Entry Point
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Emad - AI Floor Plan Auditor")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8005)
