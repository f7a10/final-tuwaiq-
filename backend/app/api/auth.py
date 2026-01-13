# ==========================================
# Authentication API Routes
# ==========================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.models.database import get_db, User
from backend.app.auth.utils import hash_password, verify_password, create_access_token
from backend.app.auth.dependencies import require_auth, require_admin
from backend.app.auth.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserListResponse
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=dict)
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


@router.post("/login", response_model=TokenResponse)
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
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/me")
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


@router.get("/users", response_model=list[UserListResponse])
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


@router.delete("/users/{user_id}")
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
