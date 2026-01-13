"""
Documentation only.
This script shows how PDFs were converted to Markdown using Mistral OCR.
Not used in runtime.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from mistralai import Mistral

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

MODEL_NAME = "mistral-ocr-latest"
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("MISTRAL_API_KEY is not set")

client = Mistral(api_key=API_KEY)


def run_ocr(pdf_path: str, out_md: str) -> None:
    """Run OCR on a PDF file and save the output as Markdown."""
    with open(pdf_path, "rb") as f:
        uploaded = client.files.upload(
            file={"file_name": Path(pdf_path).name, "content": f},
            purpose="ocr",
        )

    res = client.ocr.process(
        model=MODEL_NAME,
        document={"type": "file", "file_id": uploaded.id},
    )

    md_text = "\n\n".join(p.markdown for p in res.pages)
    Path(out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(out_md).write_text(md_text, encoding="utf-8")
