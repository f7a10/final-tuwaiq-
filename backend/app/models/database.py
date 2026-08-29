# ==========================================
# Database Models - SQLAlchemy + SQLite
# ==========================================

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, UniqueConstraint
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
    analysis_error_code = Column(String(100), nullable=True)
    analysis_error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship to user
    owner = relationship("User", back_populates="projects")


# -------------------------------------------------
# Persistent Editor State
# -------------------------------------------------
class EditorRevision(Base):
    __tablename__ = "editor_revisions"
    __table_args__ = (
        UniqueConstraint("project_id", "revision_number", name="uq_editor_revision_number"),
        UniqueConstraint("project_id", "revision_hash", name="uq_editor_revision_hash"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False)
    revision_hash = Column(String(64), nullable=False)
    parent_revision_id = Column(Integer, ForeignKey("editor_revisions.id"), nullable=True)
    geometry_json = Column(Text, nullable=False)
    operation_json = Column(Text, nullable=True)
    label_ar = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EditorSession(Base):
    __tablename__ = "editor_sessions"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True, index=True)
    current_revision_id = Column(Integer, ForeignKey("editor_revisions.id"), nullable=False)
    redo_stack_json = Column(Text, nullable=False, default="[]")
    scale_confidence = Column(Float, nullable=False)
    geometry_confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EditorPreview(Base):
    __tablename__ = "editor_previews"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    base_revision_id = Column(Integer, ForeignKey("editor_revisions.id"), nullable=False)
    geometry_json = Column(Text, nullable=False)
    operation_json = Column(Text, nullable=False)
    label_ar = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# -------------------------------------------------
# Database Initialization
# -------------------------------------------------
def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        from sqlalchemy import inspect, text

        columns = {column["name"] for column in inspect(engine).get_columns("projects")}
        additions = {
            "analysis_error_code": "VARCHAR(100)",
            "analysis_error_message": "TEXT",
        }
        with engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE projects ADD COLUMN {name} {sql_type}"))
    print("Database initialized successfully.")


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database when module is imported
init_db()
