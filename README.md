# عماد (Emad) - AI Floor Plan Auditor

![Emad Logo](https://via.placeholder.com/150?text=عماد)

An AI-powered floor plan auditor that checks architectural drawings for compliance with the Saudi Building Code (SBC 1101).

## 🏗️ Project Structure

```
FinalProjectTQ/
├── backend/                    # Python FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Configuration settings
│   │   ├── api/               # API route modules
│   │   │   ├── auth.py        # Auth endpoints (login, register)
│   │   │   ├── projects.py    # Project CRUD endpoints
│   │   │   └── chat.py        # AI chat endpoints
│   │   ├── auth/              # Authentication utilities
│   │   │   ├── utils.py       # Password hashing, JWT
│   │   │   ├── dependencies.py # FastAPI auth dependencies
│   │   │   └── schemas.py     # Pydantic models
│   │   ├── models/            # Database models
│   │   │   └── database.py    # SQLAlchemy models
│   │   └── services/          # Business logic services
│   │       ├── smart_architect.py  # ML analysis
│   │       └── llm_service.py      # LLM integration
│   ├── scripts/
│   │   └── build_saudi_db.py  # Database setup scripts
│   └── requirements.txt
│
├── frontend/                   # Vue.js Frontend
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── style.css
│   │   ├── assets/            # Static files
│   │   ├── components/        # Reusable components
│   │   │   ├── ui/            # UI components
│   │   │   └── layout/        # Layout components
│   │   ├── views/             # Page components
│   │   │   ├── HomeView.vue
│   │   │   ├── DashboardView.vue
│   │   │   ├── HistoryView.vue
│   │   │   ├── ProfileView.vue
│   │   │   ├── auth/
│   │   │   │   ├── LoginView.vue
│   │   │   │   └── RegisterView.vue
│   │   │   └── admin/
│   │   │       └── AdminDashboardView.vue
│   │   ├── stores/            # Pinia stores
│   │   │   ├── auth.js
│   │   │   └── analysis.js
│   │   └── router/
│   │       └── index.js
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── sbc_rag_sys/               # Saudi Building Code RAG System
├── saudi_sbc_db/              # ChromaDB vector database
├── uploads/                   # Uploaded floor plans
├── dist/                      # Production build output
├── emad.db                    # SQLite database
│
├── main.py                    # Legacy entry point (still works)
├── auth.py                    # Legacy auth module
├── models.py                  # Legacy models
└── README.md                  # This file
```

## 🚀 Quick Start

### Backend (from root directory - legacy mode)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

### Backend (new modular structure)
```bash
# From project root
python -m backend.app.main
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Development
npm run build    # Production build
```

## 🔑 Features

- **AI Floor Plan Analysis**: Detects rooms and checks compliance with SBC 1101
- **User Authentication**: JWT-based login/register with per-user project history
- **Real-time Chat**: AI assistant for building code questions
- **Responsive UI**: Modern Arabic RTL interface

## 🎨 Color Scheme

| Color | Hex | Usage |
|-------|-----|-------|
| Primary | `#0F766E` | Buttons, headers |
| Secondary | `#334155` | Text |
| Accent | `#F59E0B` | Highlights |

## 📝 API Endpoints

### Authentication
- `POST /api/register` - Create account
- `POST /api/login` - Login
- `GET /api/me` - Get current user

### Projects
- `POST /api/upload` - Upload floor plan
- `GET /api/projects/me` - Get user's projects
- `GET /api/projects/{id}` - Get project details
- `DELETE /api/projects/{id}` - Delete project

### Analysis
- `GET /api/analysis/{task_id}` - Get analysis status
- `POST /api/chat` - Chat with AI

## 📄 License

© 2026 Emad (عماد) - All rights reserved.
