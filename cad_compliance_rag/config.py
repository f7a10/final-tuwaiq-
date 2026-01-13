# config.py
from __future__ import annotations
from pathlib import Path

PROJECT_NAME = "CAD Compliance RAG"

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
KB_DIR = DATA_DIR / "kb"
OCR_DIR = DATA_DIR / "ocr"

KB_ALL_PATH = str(KB_DIR / "kb_all_chunks.jsonl")
KB_SBC1101_PATH = str(KB_DIR / "sbc1101_chunks.jsonl")
KB_RES_REQ_PATH = str(KB_DIR / "res_requirements_chunks.jsonl")

DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.1
