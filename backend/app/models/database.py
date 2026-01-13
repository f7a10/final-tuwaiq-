# ==========================================
# Database Models - SQLAlchemy + SQLite
# ==========================================

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from backend.app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# -------------------------------------------------
# User Model
# -------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="customer")  # customer, office, admin
    account_type = Column(String(50), default="personal")  # personal, office
    is_active = Column(Boolean, default=True)
    plans_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to projects
    projects = relationship("Project", back_populates="owner", lazy="dynamic")


# -------------------------------------------------
# Project Model (Floor Plan Analysis)
# -------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Project Info
    title = Column(String(255), default="مخطط بدون عنوان")
    description = Column(Text, nullable=True)
    
    # Image URLs
    original_image_url = Column(String(500), nullable=True)
    analyzed_image_url = Column(String(500), nullable=True)
    
    # Analysis Results
    status = Column(String(50), default="processing")  # processing, completed, failed
    compliance_status = Column(String(50), nullable=True)  # compliant, non_compliant
    compliance_score = Column(Float, nullable=True)
    rooms_count = Column(Integer, default=0)
    compliant_rooms = Column(Integer, default=0)
    violations_count = Column(Integer, default=0)
    
    # JSON data for detailed results
    rooms_data = Column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship to user
    owner = relationship("User", back_populates="projects")


# -------------------------------------------------
# Database Initialization
# -------------------------------------------------
def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully.")


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database when module is imported
init_db()
