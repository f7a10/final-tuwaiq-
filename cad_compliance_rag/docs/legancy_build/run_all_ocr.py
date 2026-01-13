"""
Documentation only.
Example batch OCR execution.
"""

from pathlib import Path
from .ocr_mistral import run_ocr


def main() -> None:
    run_ocr(
        pdf_path="data/src/sbc1101.pdf",
        out_md="data/ocr/sbc1101_ocr.md",
    )

    run_ocr(
        pdf_path="data/src/اشتراطات إنشاء المباني السكنية.pdf",
        out_md="data/ocr/res_requirements_ocr.md",
    )


if __name__ == "__main__":
    main()
