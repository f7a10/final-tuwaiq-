# ==========================================
# Backend App Configuration
# ==========================================

import os

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API Keys
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "NmjqLgZyvnjZhiNJJXqH")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "emad-super-secret-key-change-in-production-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Scale Configuration
DEFAULT_SCALE = 100.0  # pixels per meter
WINDOW_PADDING = 25

# Upload Directory (relative to project root)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Database (relative to project root)
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'emad.db')}"

