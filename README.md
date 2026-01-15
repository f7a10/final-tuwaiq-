# Emad (عماد) - AI Floor Plan Auditor

## Overview

Emad is an advanced AI-powered architectural auditing system designed to verify residential floor plans against the Saudi Building Code (SBC 1101). The system utilizes computer vision for room detection and Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG) to provide real-time compliance feedback and interactive consultation.

## Features

- **Automated Floor Plan Analysis**: Uses machine learning to segment rooms, identify types, and calculate dimensions.
- **SBC 1101 Compliance Checking**: Automatically verifies room areas and dimensions against Saudi Building Code requirements.
- **Intelligent RAG Assistant**: A specialized chatbot capable of answering engineering questions by retrieving evidence directly from the SBC 1101 text.
- **Interactive Dashboard**: A modern, responsive web interface supporting Arabic RTL layouts.
- **Reporting**: Generates visual compliance reports highlighting violations and offering corrective suggestions.

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (Application Data), ChromaDB (Vector Embeddings)
- **AI/ML**: 
  - PyTorch / Ultralytics (Vision Models)
  - LangChain / RAG (Context Retrieval)
  - OpenAI / Grok API (LLM Integration)

### Frontend
- **Framework**: Vue.js 3
- **State Management**: Pinia
- **Styling**: Tailwind CSS
- **Routing**: Vue Router

## Project Structure

```
FinalProjectTQ/
├── backend/                    # Core Application Logic
│   ├── app/
│   │   ├── api/               # REST API Endpoints
│   │   ├── services/          # AI & Business Logic
│   │   ├── models/            # Database Schema
│   │   └── main.py            # Application Entry Point
│   └── scripts/               # Utility Scripts
│
├── frontend/                   # Web Interface
│   ├── src/
│   │   ├── components/        # Vue Components
│   │   ├── views/             # Page Views
│   │   └── stores/            # State Management
│
├── sbc_rag_sys/               # Retrieval-Augmented Generation Module
└── uploads/                   # Temporary File Storage
```

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Backend Setup

Navigate to the project root and create a virtual environment:

```bash
python -m venv .venv
# Activate: 
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 2. Frontend Setup

Navigate to the frontend directory:

```bash
cd frontend
npm install
```

### 3. Environment Configuration

Create a `.env` file in the root directory containing your API keys:

```ini
OPENAI_API_KEY=your_key_here
ROBOFLOW_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

## Running the Application

### Start the Backend Server

From the project root:

```bash
python -m backend.app.main
```
The API will be available at `http://localhost:8005`.

### Start the Frontend Client

From the frontend directory:

```bash
npm run dev
```
The interface will be available at `http://localhost:5173` (or the port specified by Vite).

## API Documentation

The backend provides interactive documentation via Swagger UI. Once the server is running, navigate to:
`http://localhost:8005/docs`

### Key Endpoints
- `POST /api/upload`: Upload and analyze a floor plan image.
- `GET /api/analysis/{task_id}`: Retrieve analysis results.
- `POST /api/chat`: Query the AI consultant regarding building codes.

## License

Copyright 2026 Emad - AI Floor Plan Auditor. All Rights Reserved.
