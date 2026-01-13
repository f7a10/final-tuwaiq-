"""
Documentation only.
This script shows how the Markdown OCR output was chunked into a KB (JSONL).
Not used in runtime.
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


PAGE_RE = re.compile(
    r"(?:^|\n)\s*(?:Page|PAGE|الصفحة)\s*[:\-]?\s*(\d+)\s*(?:\n|$)",
    re.IGNORECASE,
)

MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
SBC_HEADING_RE = re.compile(r"^(\d{3}(?:[-–—]\d+)*)\s+(.+)$")

MIN_BLOCK_LEN = 20
MIN_CHUNK_LEN = 20


def normalize_arabic(text: str) -> str:
    """Light Arabic normalization for search/indexing."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub("[إأآٱ]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ؤ", "و", text)
    text = re.sub("ئ", "ي", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("[ًٌٍَُِّْـ]", "", text)
    return text


def md_to_chunks(
    md_text: str,
    *,
    doc_id: str,
    source: str,
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> List[Dict[str, Any]]:
    """
    Convert a Markdown document into overlapping text chunks.
    Headings (Markdown or SBC-style numeric headings) define sections.
    """
    chunks: List[Dict[str, Any]] = []
    chunk_id = 0
    current_page: Optional[int] = None

    blocks: List[Dict[str, Any]] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []
    block_page: Optional[int] = None

    for raw_line in md_text.splitlines():
        stripped = raw_line.strip()

        m_page = PAGE_RE.search(raw_line)
        if m_page:
            current_page = int(m_page.group(1))

        if not stripped:
            if current_lines:
                current_lines.append(raw_line)
            continue

        m_md = MD_HEADING_RE.match(stripped)
        m_sbc = SBC_HEADING_RE.match(stripped)

        if m_md or m_sbc:
            if current_lines:
                block_text = "\n".join(current_lines).strip()
                if len(block_text) >= MIN_BLOCK_LEN:
                    blocks.append(
                        {
                            "title": current_title,
                            "text": block_text,
                            "page": block_page,
                        }
                    )
                current_lines = []

            current_title = m_md.group(2).strip() if m_md else m_sbc.group(2).strip()
            block_page = current_page
            current_lines.append(raw_line)
        else:
            if not current_lines:
                block_page = current_page
            current_lines.append(raw_line)

    if current_lines:
        block_text = "\n".join(current_lines).strip()
        if len(block_text) >= MIN_BLOCK_LEN:
            blocks.append(
                {
                    "title": current_title,
                    "text": block_text,
                    "page": block_page,
                }
            )

    for blk in blocks:
        text = re.sub(r"```.*?```", "", blk["text"], flags=re.DOTALL).strip()
        if len(text) < MIN_BLOCK_LEN:
            continue

        section = blk["title"] or text.splitlines()[0][:160]
        page = blk["page"]

        if len(text) <= max_chars:
            if len(text) >= MIN_CHUNK_LEN:
                chunks.append(
                    {
                        "doc_id": doc_id,
                        "source": source,
                        "chunk_id": chunk_id,
                        "page": page,
                        "section": section,
                        "text": text,
                        "text_norm": normalize_arabic(text),
                    }
                )
                chunk_id += 1
            continue

        start = 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            piece = text[start:end].strip()
            if len(piece) >= MIN_CHUNK_LEN:
                chunks.append(
                    {
                        "doc_id": doc_id,
                        "source": source,
                        "chunk_id": chunk_id,
                        "page": page,
                        "section": section,
                        "text": piece,
                        "text_norm": normalize_arabic(piece),
                    }
                )
                chunk_id += 1

            if end == len(text):
                break
            start = max(0, end - overlap_chars)

    return chunks


def build_kb_from_md(
    md_path: str,
    out_jsonl_path: str,
    *,
    doc_id: str,
    source: str,
) -> Dict[str, Any]:
    """Build a JSONL knowledge base from a Markdown file."""
    md = Path(md_path).read_text(encoding="utf-8")
    chunks = md_to_chunks(md, doc_id=doc_id, source=source)

    out_path = Path(out_jsonl_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    return {"chunks": len(chunks), "out_path": str(out_path)}
