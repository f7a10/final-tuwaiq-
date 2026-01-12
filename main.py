# ==========================================
# Emad (عماد) - AI Floor Plan Auditor Backend
# Integrated with SmartArchitect Analysis
# ==========================================

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel as PydanticBaseModel
import uuid
import json
import shutil
import os
import cv2
import base64
import numpy as np
from PIL import Image
import sys
from openai import OpenAI
from inference_sdk import InferenceHTTPClient

# Database & Auth imports
from models import get_db, User, Project, init_db, SessionLocal
from auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserListResponse,
    ProjectResponse, ProjectListResponse,
    hash_password, verify_password, create_access_token,
    require_auth, require_admin, get_current_user
)
from datetime import datetime

# Import Saudi Building Code compliance checker
import google.generativeai as genai
from sbc_rag_sys.src.rag_query import query_sbc
import os
# Configure Gemini
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
elif os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# -------------------------------------------------
# ⚙️ Configuration (Keys from your working script)
# -------------------------------------------------
ROBOFLOW_API_KEY = "NmjqLgZyvnjZhiNJJXqH"
OPENROUTER_API_KEY = "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"

DEFAULT_SCALE = 100.0  # pixels per meter
WINDOW_PADDING = 25

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
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# 🧠 SmartArchitect Class (Full Integration)
# -------------------------------------------------
def calculate_dynamic_scale(structure_predictions, default_scale=100.0):
    """Calculate pixels per meter based on detected door widths."""
    doors = []
    for item in structure_predictions:
        if "door" in item['class'].lower() and "double" not in item['class'].lower():
            doors.append(item['width'])
    if not doors:
        return default_scale
    avg_door_pixel_width = sum(doors) / len(doors)
    # Standard door width is ~0.9m
    return avg_door_pixel_width / 0.9


class SmartArchitect:
    """Full analysis class for floor plan processing."""
    
    def __init__(self):
        print("🚀 Initializing SmartArchitect...")
        self.ai = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        self.rf = InferenceHTTPClient(
            api_url="https://detect.roboflow.com",
            api_key=ROBOFLOW_API_KEY
        )
        print("✓ SmartArchitect initialized successfully.")

    def encode_image(self, cv2_img):
        """Convert OpenCV image to base64 for LLM."""
        _, buffer = cv2.imencode('.jpg', cv2_img)
        return base64.b64encode(buffer).decode('utf-8')

    def identify_room_type(self, room_crop):
        """Use Grok Vision (OpenRouter) to identify room type from cropped image."""
        try:
            # Encode image to base64 with proper data URI
            _, buffer = cv2.imencode('.jpg', room_crop)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            image_data_uri = f"data:image/jpeg;base64,{base64_image}"
            
            # OpenRouter client (OpenAI-compatible)
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY
            )
            
            # Vision models to try (Grok first, then fallbacks)
            vision_models = [
                "x-ai/grok-2-vision-1212",      # Latest Grok Vision
                "x-ai/grok-vision-beta",         # Grok Vision Beta
                "openai/gpt-4o-mini",            # Fallback: GPT-4o Mini
                "google/gemini-flash-1.5"        # Fallback: Gemini Flash
            ]
            
            prompt = """Look at this floor plan room image. What type of room is this?

Choose ONE from this list:
- Bedroom
- Kitchen  
- Bathroom
- Living Room
- Dining Room
- Majlis
- Open Plan Kitchen/Living
- Unknown

Reply with ONLY the room type name, nothing else."""

            for model_id in vision_models:
                try:
                    print(f"    🤖 Trying VLM: {model_id}...")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_data_uri
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=50
                    )
                    
                    result = response.choices[0].message.content.strip()
                    print(f"    ✓ {model_id} Identified: {result}")
                    
                    # Normalize result
                    valid_types = ["Bedroom", "Kitchen", "Bathroom", "Living Room", 
                                   "Dining Room", "Majlis", "Open Plan Kitchen/Living"]
                                   
                    for vt in valid_types:
                        if vt.lower() in result.lower():
                            return vt
                    
                    return result if len(result) < 30 else "Unknown"
                    
                except Exception as model_error:
                    print(f"    ⚠️ {model_id} Error: {model_error}")
                    continue  # Try next model
            
            # All models failed
            print("    ❌ All VLM models failed")
            return "Unknown"
            
        except Exception as e:
            print(f"❌ Room identification error: {e}")
            return "Unknown"

    def analyze(self, image_path: str, pixels_per_meter: float = None):
        """
        Full analysis pipeline:
        1. Detect structures (walls, doors, windows)
        2. Detect rooms
        3. Identify room types with LLM
        4. Calculate metrics
        5. Draw bounding boxes
        6. Return annotated image and data
        """
        print(f"📐 Analyzing: {image_path}")
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "Could not load image"}, None
        
        visual_result = img.copy()
        h, w = img.shape[:2]
        
        # Step 1: Detect structures (doors, windows, walls)
        print("🔍 Detecting structures (doors, windows)...")
        try:
            structure_result = self.rf.infer(image_path, model_id="cubicasa5k-2-qpmsa/6")
            structure_predictions = structure_result.get('predictions', [])
        except Exception as e:
            print(f"⚠️ Structure detection failed: {e}")
            structure_predictions = []
        
        # Step 2: Calculate dynamic scale
        if pixels_per_meter is None:
            pixels_per_meter = calculate_dynamic_scale(structure_predictions, DEFAULT_SCALE)
        print(f"📏 Scale: {pixels_per_meter:.2f} px/m")
        
        # Step 3: Detect rooms
        print("🏠 Detecting rooms...")
        try:
            room_result = self.rf.infer(image_path, model_id="room-detection-6nzte/1")
            room_predictions = room_result.get('predictions', [])
        except Exception as e:
            print(f"⚠️ Room detection failed: {e}")
            room_predictions = []
        
        rooms_data = []
        
        # Step 4: Process each detected room
        for i, room in enumerate(room_predictions):
            x_center = room['x']
            y_center = room['y']
            room_w = room['width']
            room_h = room['height']
            
            # Calculate bounding box
            x1 = int(x_center - room_w / 2)
            y1 = int(y_center - room_h / 2)
            x2 = int(x_center + room_w / 2)
            y2 = int(y_center + room_h / 2)
            
            # Ensure bounds are within image
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # Crop room for LLM identification
            room_crop = img[y1:y2, x1:x2]
            if room_crop.size == 0:
                continue
            
            # Identify room type using LLM
            room_type = self.identify_room_type(room_crop)
            print(f"  🏷️ Room {i+1}: {room_type}")
            
            # Calculate metrics
            area_px = room_w * room_h
            area_m2 = area_px / (pixels_per_meter ** 2)
            min_dim_m = min(room_w, room_h) / pixels_per_meter
            
            # Check compliance using Saudi Building Code (SBC 1101)
            # Check compliance using Saudi Building Code (SBC 1101) - RAG Integration
            sbc_result = query_sbc(room_type, area_m2, min_dim_m)
            is_compliant = sbc_result["is_compliant"]
            rag_reason = sbc_result["reason"]
            code_reference = "SBC 1101" # Fixed reference
            violations = sbc_result.get("violations", [])
            
            # Draw bounding box
            color = (0, 255, 0) if is_compliant else (0, 0, 255)  # Green or Red
            cv2.rectangle(visual_result, (x1, y1), (x2, y2), color, 3)
            
            # Draw label background
            label = f"{room_type} ({area_m2:.1f}m²)"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            (label_w, label_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(visual_result, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            cv2.putText(visual_result, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            # Store room data
            rooms_data.append({
                "id": f"room_{i+1}",
                "type": room_type,
                "metrics": {
                    "area": round(area_m2, 2),
                    "minDim": round(min_dim_m, 2)
                },
                "isCompliant": is_compliant,
                "ragReason": rag_reason,
                "box": {
                    "x": round(x1 / w, 4),
                    "y": round(y1 / h, 4),
                    "w": round((x2 - x1) / w, 4),
                    "h": round((y2 - y1) / h, 4)
                }
            })
        
        # Draw structures (doors, windows) in blue
        for item in structure_predictions:
            x1 = int(item['x'] - item['width'] / 2)
            y1 = int(item['y'] - item['height'] / 2)
            x2 = int(item['x'] + item['width'] / 2)
            y2 = int(item['y'] + item['height'] / 2)
            cv2.rectangle(visual_result, (x1, y1), (x2, y2), (255, 128, 0), 2)  # Blue-ish for structures
        
        # Calculate overall score
        total_rooms = len(rooms_data)
        compliant_rooms = sum(1 for r in rooms_data if r['isCompliant'])
        score = round((compliant_rooms / total_rooms * 100) if total_rooms > 0 else 0)
        
        result = {
            "rooms": rooms_data,
            "score": score,
            "status": "Compliant" if score == 100 else "Non-Compliant",
            "total_rooms": total_rooms,
            "compliant_rooms": compliant_rooms
        }
        
        print(f"✅ Analysis complete: {compliant_rooms}/{total_rooms} rooms compliant ({score}%)")
        return result, visual_result


# Initialize SmartArchitect globally
architect = SmartArchitect()

# -------------------------------------------------
# 📦 In-Memory Results Store
# -------------------------------------------------
analysis_results = {}

# -------------------------------------------------
# ⚡ Background Processing Task
# -------------------------------------------------
def process_floor_plan(task_id: str, file_path: str, settings: dict, base_url: str, owner_id: int = None):
    """Background task to analyze floor plan and save annotated image."""
    print(f"🚀 Starting analysis for task: {task_id}")
    
    # Get DB session for background task
    db = SessionLocal()
    
    try:
        # Run the full analysis
        result_data, annotated_image = architect.analyze(file_path)
        
        analyzed_url = None
        original_url = f"{base_url}/uploads/{os.path.basename(file_path)}"
        
        if annotated_image is not None:
            # Save annotated image
            output_filename = f"{task_id}_analyzed.jpg"
            output_path = os.path.join(UPLOAD_DIR, output_filename)
            cv2.imwrite(output_path, annotated_image)
            print(f"💾 Saved annotated image: {output_path}")
            
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
        print(f"❌ Analysis failed: {e}")
        
        # Update project status to failed
        project = db.query(Project).filter(Project.task_id == task_id).first()
        if project:
            project.status = "failed"
            db.commit()
        
        analysis_results[task_id] = {
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()
    
    print(f"✅ Task {task_id} complete!")

# -------------------------------------------------
# 🌐 API Endpoints
# -------------------------------------------------
@app.post("/api/upload")
async def upload_plan(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    settings: str = Form(...),
    db: Session = Depends(get_db)
):
    """Upload floor plan and start analysis. (Open Access for Debugging)"""
    current_user = None  # TEMPORARY: Open access mode
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
    
    # Get owner_id if user is logged in
    owner_id = current_user.id if current_user else None
    
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


@app.get("/api/analysis/{task_id}")
async def get_analysis(task_id: str):
    """Get analysis status and results."""
    result = analysis_results.get(task_id)
    if not result:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return result


@app.get("/api/download/{task_id}")
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


# -------------------------------------------------
# � Chat API Endpoint (Saudi Building Code AI)
# -------------------------------------------------
class ChatRequest(PydanticBaseModel):
    message: str
    task_id: str = None

class ChatResponse(PydanticBaseModel):
    reply: str
    
@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """Chat with AI about Saudi Building Code."""
    try:
        print(f"💬 Chat request: {request.message[:50]}...")
        
        # Create OpenRouter client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # System prompt for Saudi Building Code expert
        system_prompt = """أنت "عماد"، مساعد ذكاء اصطناعي متخصص في كود البناء السعودي السكني (SBC 1101).

مهمتك:
- الإجابة عن أسئلة المستخدمين حول متطلبات كود البناء
- شرح أسباب المخالفات في المخططات
- تقديم حلول ومقترحات لتصحيح المخالفات

قواعد مهمة تعرفها:
- غرف النوم: الحد الأدنى 9 م²، أقل بُعد 2.7 م
- المطابخ: الحد الأدنى 4.5 م²، أقل بُعد 1.8 م
- دورات المياه: الحد الأدنى 2.5 م²، أقل بُعد 1.2 م
- غرف المعيشة: الحد الأدنى 12 م²، أقل بُعد 3.0 م
- المجلس: الحد الأدنى 14 م²، أقل بُعد 3.0 م
- غرفة الطعام: الحد الأدنى 10 م²، أقل بُعد 3.0 م
- الغرف المسكونة تحتاج نوافذ للتهوية والإضاءة الطبيعية

أجب باللغة العربية بشكل موجز ومفيد."""

        # Try multiple models
        models = ["x-ai/grok-2-1212", "openai/gpt-4o-mini", "google/gemini-flash-1.5"]
        
        for model_id in models:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.message}
                    ],
                    max_tokens=500
                )
                
                reply = response.choices[0].message.content.strip()
                print(f"✓ Chat reply from {model_id}: {reply[:50]}...")
                return {"reply": reply}
                
            except Exception as model_error:
                print(f"⚠️ Chat {model_id} Error: {model_error}")
                continue
        
        # All models failed - return fallback
        return {"reply": "عذراً، لم أتمكن من معالجة طلبك الآن. يرجى المحاولة مرة أخرى."}
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {"reply": f"حدث خطأ: {str(e)}"}


# -------------------------------------------------
# �📁 Projects API Endpoints
# -------------------------------------------------
@app.get("/api/projects/me")
async def get_my_projects(
    db: Session = Depends(get_db),
    search: str = None,
    status_filter: str = None,  # all, compliant, non_compliant
    skip: int = 0,
    limit: int = 50
):
    """Get projects (Open access for debugging - returns all projects)."""
    query = db.query(Project)  # TEMPORARY: Return all projects without auth
    
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


@app.get("/api/projects/{project_id}")
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


@app.delete("/api/projects/{project_id}")
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


# -------------------------------------------------
# 🔐 Authentication API Endpoints
# -------------------------------------------------
@app.post("/api/register", response_model=dict)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="البريد الإلكتروني مسجل مسبقاً"
            )
        


        # Create new user
        new_user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            account_type=user_data.account_type,
            role="customer"  # Default role
        )

    
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "تم إنشاء الحساب بنجاح",
            "user_id": new_user.id
        }
    except Exception as e:
        print(f"Register Error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )


@app.post("/api/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token."""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == credentials.email).first()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="البريد الإلكتروني أو كلمة المرور غير صحيحة"
            )
        
        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="البريد الإلكتروني أو كلمة المرور غير صحيحة"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="الحساب محظور. تواصل مع الدعم الفني"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                account_type=user.account_type,
                is_active=user.is_active,
                plans_count=user.plans_count,
                created_at=user.created_at
            )
        )
    except Exception as e:
        print(f"Login Error: {str(e)}")
        # If it's already HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )


@app.get("/api/users", response_model=list[UserListResponse])
async def get_all_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users (Admin only)."""
    users = db.query(User).all()
    
    return [
        UserListResponse(
            id=u.id,
            name=u.full_name,
            email=u.email,
            role=u.role,
            plansCount=u.plans_count,
            status="active" if u.is_active else "banned"
        )
        for u in users
    ]


@app.get("/api/me")
async def get_current_user_info(user: User = Depends(require_auth)):
    """Get current logged-in user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        account_type=user.account_type,
        is_active=user.is_active,
        plans_count=user.plans_count,
        created_at=user.created_at
    )


@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="لا يمكن حذف حساب مدير")
    
    db.delete(user)
    db.commit()
    
    return {"message": "تم حذف المستخدم بنجاح"}


# -------------------------------------------------
# 📁 Static Files & SPA Serving
# -------------------------------------------------
# Mount assets first
if os.path.exists("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

# Mount uploads directory for serving images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve Vue.js SPA."""
    if full_path.startswith("api"):
        return JSONResponse({"error": "API route not found"}, status_code=404)
    
    file_path = os.path.join("dist", full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    if os.path.exists("dist/index.html"):
        return FileResponse("dist/index.html")
    
    return "Frontend build not found. Run 'npm run build'"


# -------------------------------------------------
# 🚀 Main Entry Point
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🏗️  Emad (عماد) - AI Floor Plan Auditor")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8005)