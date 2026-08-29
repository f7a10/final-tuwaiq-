# ==========================================
# Backend App Configuration
# ==========================================

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


def load_project_environment(project_root):
    """Load project-local settings without replacing process-level secrets."""
    return load_dotenv(Path(project_root) / ".env", override=False)


def _unique_csv(value):
    return tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_project_environment(PROJECT_ROOT)

# API Keys
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
FLOOR_PLAN_DETECTOR = os.getenv("FLOOR_PLAN_DETECTOR", "local").strip().lower()
LOCAL_FLOORPLAN_MODEL_PATH = os.getenv(
    "LOCAL_FLOORPLAN_MODEL_PATH",
    os.path.join(PROJECT_ROOT, "models", "cubicasa5k-structure.safetensors"),
)
LOCAL_FLOORPLAN_MAX_DIMENSION = int(os.getenv("LOCAL_FLOORPLAN_MAX_DIMENSION", "512"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_VISION_MODEL = os.getenv(
    "OPENROUTER_VISION_MODEL",
    "google/gemini-2.5-flash",
)
OPENROUTER_PLANNING_MODEL = os.getenv(
    "OPENROUTER_PLANNING_MODEL",
    "openai/gpt-4.1-mini",
)
OPENROUTER_ASSISTANT_MODEL = os.getenv(
    "OPENROUTER_ASSISTANT_MODEL",
    "google/gemini-2.5-flash",
)
OPENROUTER_FALLBACK_MODELS = _unique_csv(
    os.getenv("OPENROUTER_FALLBACK_MODELS", "openai/gpt-4.1-mini")
)

# JWT Configuration
_configured_jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
JWT_SECRET_IS_EPHEMERAL = not bool(_configured_jwt_secret)
JWT_SECRET_KEY = _configured_jwt_secret or secrets.token_urlsafe(48)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Scale Configuration
DEFAULT_SCALE = 100.0  # pixels per meter
WINDOW_PADDING = 25

# Upload Directory (relative to project root)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Database (relative to project root)
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'emad.db')}"

