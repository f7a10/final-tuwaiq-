# CAD Compliance RAG – Knowledge Base Build Method

This document describes **how the knowledge base (KB) was created**, for documentation
and traceability purposes only.

⚠️ **Important**
- The runtime system does **NOT** execute OCR or KB building.
- All files under `docs/legacy_build/` are **documentation only**.
- The application consumes **pre-built JSONL files** from `data/kb/`.

---

## 1. Source Documents

The knowledge base is derived from official Saudi Building Code (SBC) documents:

- **SBC1101** – General building requirements
- **Residential Building Requirements** (اشتراطات إنشاء المباني السكنية)

Original PDFs are stored outside runtime usage:

data/src/
├─ sbc1101.pdf
└─ اشتراطات إنشاء المباني السكنية.pdf

---

## 2. OCR Step (Offline)

OCR was performed using **Mistral OCR** to convert PDF documents into Markdown.

- Tool: `mistral-ocr-latest`
- Output format: Markdown (`.md`)
- Purpose: Preserve structure (headings, sections, paragraphs)

Generated outputs:
data/ocr/
├─ sbc1101_ocr.md
└─ res_requirements_ocr.md


> See: `docs/legacy_build/ocr_mistral.py`

---

## 3. Markdown Chunking Strategy

Each OCR Markdown file is converted into **semantic chunks** using the following rules:

### Section Detection
A new section is detected when:
- A Markdown heading appears (`#`, `##`, `###`)
- OR a numeric SBC-style heading appears:
  - `301 التطبيق`
  - `301-1 التطبيق`
  - `306-3-1 يجب توصيل أدوات السباكة`

### Chunking Rules
- Maximum chunk size: **~1200 characters**
- Overlap between chunks: **~150 characters**
- Very short blocks are discarded
- Code blocks are removed
- Each chunk stores:
  - `doc_id`
  - `section`
  - `page`
  - `text`
  - `text_norm` (light Arabic normalization)

> See: `docs/legacy_build/kb_build_from_md.py`

---

## 4. Knowledge Base Outputs

Chunked content is saved in **JSONL** format:

data/kb/
├─ sbc1101_chunks.jsonl
├─ res_requirements_chunks.jsonl
└─ kb_all_chunks.jsonl


`kb_all_chunks.jsonl` is a simple concatenation of all document chunks and is the
**default KB file used at runtime**.

---

## 5. Runtime Usage

At runtime:
- No OCR is executed
- No chunking is executed
- No PDFs are parsed

The system directly loads:
data/kb/kb_all_chunks.jsonl

This file is used by the retrieval layer (BM25-based keyword search)
to support compliance evidence lookup.

---

## 6. Rationale

This separation ensures:
- Fast runtime performance
- Deterministic evidence retrieval
- Clear auditability of compliance sources
- Clean integration with backend and frontend systems

---
End of document.
