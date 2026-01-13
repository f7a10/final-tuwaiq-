# CAD Compliance RAG – Integration Guide

This guide explains how to integrate **CAD Compliance RAG**
with backend and frontend systems.

---

## 0. Setup

1) Create a virtual environment

```python
python -m venv .venv
``` 

2) Activate it

```python
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Windows (cmd)
.\.venv\Scripts\activate.bat
# macOS / Linux
source .venv/bin/activate
```

3) Upgrade pip (recommended)

```python
python -m pip install --upgrade pip
```

4) Install requirements

```python
pip install -r requirements.txt
```

---

## 1. What This Module Provides

CAD Compliance RAG is a **logic-only compliance engine** that:

- Evaluates architectural units and rooms against SBC rules
- Retrieves textual evidence from official regulations
- Returns structured JSON suitable for frontend display

It does **NOT** handle:
- Databases
- File storage
- OCR
- PDF parsing

---

## 2. Required Files

Ensure the following file exists before running:
data/kb/kb_all_chunks.jsonl

This file contains the pre-built knowledge base used for evidence retrieval.

---

## 3. Main Entry Point

Import the compliance engine using:

```python
from src.analyze_plan import analyze_plan
```

---

## 4. Input Format (Example)

```python
rooms = [
  {
    "id": 1,
    "type": "Bedroom",
    "metrics": {
      "area_sqm": 12,
      "min_dimension_m": 3
    }
  },
  {
    "id": 2,
    "type": "Bathroom",
    "metrics": {
      "area_sqm": 2.5,
      "min_dimension_m": 1.2
    },
    "ventilation": {
      "has_window": False
    }
  }
]
```

---

## 5. Running an Analysis

```python
result = analyze_plan(
    project_id="demo_project",
    asset_id="unit_01",
    rooms=rooms
)
```

---

## 6. Output Structure

The result is a JSON-compatible dictionary:

```python
{
  "project_id": "demo_project",
  "asset_id": "unit_01",
  "summary": {
    "rooms_total": 2,
    "violations_total": 1,
    "warnings_total": 0,
    "skipped_missing_data": 0
  },
  "violations": [
    {
      "rule_id": "...",
      "room_id": 2,
      "room_type": "Bathroom",
      "rule_sentence": "يجب توفر نافذة لدورة المياه...",
      "ref": {
        "doc": "SBC1101",
        "section": "دورات المياه",
        "page": 45
      }
    }
  ],
  "warnings": []
}
```

---

## 7. Design Philosophy

- Deterministic rule evaluation

- Explainable evidence (no LLM hallucination)

---

End of document.