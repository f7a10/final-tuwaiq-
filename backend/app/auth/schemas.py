# ==========================================
# Pydantic Schemas for Authentication
# ==========================================

from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    account_type: str = "personal"  # personal, office


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    account_type: str
    is_active: bool
    plans_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserListResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    plansCount: int
    status: str

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    task_id: str
    title: str
    original_image_url: str | None
    analyzed_image_url: str | None
    status: str
    compliance_status: str | None
    compliance_score: float | None
    rooms_count: int
    violations_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
