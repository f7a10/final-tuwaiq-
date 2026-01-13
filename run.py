#!/usr/bin/env python3
# ==========================================
# Emad (عماد) - AI Floor Plan Auditor
# Entry Point Script
# ==========================================

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now run the app
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🏗️  Emad (عماد) - AI Floor Plan Auditor")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8005)
