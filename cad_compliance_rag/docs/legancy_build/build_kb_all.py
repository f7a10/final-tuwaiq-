"""
Documentation only.
Build individual KB files and concatenate them into a single JSONL.
"""

from pathlib import Path
from .kb_build_from_md import build_kb_from_md


def _concat_jsonl(out_path: str, inputs: list[str]) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as w:
        for p in inputs:
            with open(p, "r", encoding="utf-8") as r:
                for line in r:
                    if line.strip():
                        w.write(line)


def main() -> None:
    out1 = "data/kb/sbc1101_chunks.jsonl"
    out2 = "data/kb/res_requirements_chunks.jsonl"

    build_kb_from_md(
        md_path="data/ocr/sbc1101_ocr.md",
        out_jsonl_path=out1,
        doc_id="SBC1101",
        source="SBC1101_MISTRAL_OCR",
    )

    build_kb_from_md(
        md_path="data/ocr/res_requirements_ocr.md",
        out_jsonl_path=out2,
        doc_id="RES_REQUIREMENTS",
        source="RES_REQUIREMENTS_MISTRAL_OCR",
    )

    _concat_jsonl(
        "data/kb/kb_all_chunks.jsonl",
        [out1, out2],
    )


if __name__ == "__main__":
    main()
