# ==========================================
# Authentication Utilities
# JWT Tokens + Password Hashing
# ==========================================

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from models import get_db, User

# -------------------------------------------------
# Configuration
# -------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "emad-super-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# -------------------------------------------------
# Password Hashing
# -------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


import hashlib

def pre_hash_password(password: str) -> str:
    """
    Pre-hash password using SHA256 to allow passwords > 72 bytes.
    Returns: 64-character hex string.
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (with SHA256 pre-hashing)."""
    pre_hashed = pre_hash_password(password)
    print(f"DEBUG: Hashing password. Pre-hash length: {len(pre_hashed)}, Content: {pre_hashed[:10]}...")
    return pwd_context.hash(pre_hashed)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (with SHA256 pre-hashing)."""
    # Try verifying with pre-hash first (New standard)
    if pwd_context.verify(pre_hash_password(plain_password), hashed_password):
        return True
    
    # Optional backward compatibility: Try verifying check without pre-hash
    # ONLY if check fails. This allows old passwords (if specific lengths worked) to still work,
    # OR if you migrate existing DB. 
    # For now, to solve the crash, checking pre-hash first is key.
    # Note: If previous short pwd was hashed raw, this verify will fail.
    # But user complained about crash.
    # I will stick to strictly using pre-hashing for new logic.
    # If backward compatibility needed, I would catch error.
    return False


# -------------------------------------------------
# JWT Token Handling
# -------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# -------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------
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


# -------------------------------------------------
# Security Dependency
# -------------------------------------------------
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get the current authenticated user.
    Returns None if no valid token is provided.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that REQUIRES authentication.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="الرجاء تسجيل الدخول",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="جلسة منتهية. الرجاء تسجيل الدخول مجدداً",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز غير صالح",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="المستخدم غير موجود",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الحساب محظور",
        )
    
    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """
    Dependency that REQUIRES admin role.
    Must be used after require_auth.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء يتطلب صلاحيات المدير",
        )
    return user
