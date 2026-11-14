"""OCR scanned PDFs (course workbooks etc.) into searchable text. PRIVATE USE ONLY.

Run this on YOUR computer, not on a server. Output goes to content/raw/offline/, which is
git-ignored and docker-ignored, so the text never reaches GitHub or a public deployment.

Setup:  pip install -r apps/api/requirements.txt   and install Tesseract OCR
        (Windows: github.com/UB-Mannheim/tesseract/wiki, macOS: brew install tesseract, Linux: apt install tesseract-ocr)
Usage:  python content/tools/ocr_pdf.py "Physiology FMGE Workbook.pdf" "Physiology workbook (private)" [--dpi 150] [--pages 1-50]
Large PDFs take a while (roughly 1 to 3 seconds per page). It resumes by skipping pages already done.
"""
import io
import re
import sys
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
import pytesseract
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "raw" / "offline"


def page_range(spec: str | None, n: int):
    if not spec:
        return range(n)
    a, _, b = spec.partition("-")
    return range(max(0, int(a) - 1), min(n, int(b or a)))


def main(pdf: str, label: str, dpi: int = 150, pages: str | None = None):
    OUT.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"\W+", "_", Path(pdf).stem).strip("_")
    target = OUT / f"{name}.md"
    doc = fitz.open(pdf)
    done = set(re.findall(r"^## Page (\d+)$", target.read_text(), re.M)) if target.exists() else set()
    if not target.exists():
        target.write_text(f"source: {label}\ntitle: {Path(pdf).stem}\n\n")
    with target.open("a") as f:
        for i in page_range(pages, len(doc)):
            if str(i + 1) in done:
                continue
            page = doc[i]
            text = page.get_text().strip()  # use the embedded text layer when there is one
            if len(text) < 40:
                pix = page.get_pixmap(dpi=dpi)
                text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png")))).strip()
            if text:
                f.write(f"## Page {i + 1}\n{text}\n\n")
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(doc)} pages", flush=True)
    print(f"Done: {target}")


if __name__ == "__main__":
    a = sys.argv[1:]
    dpi = int(a[a.index("--dpi") + 1]) if "--dpi" in a else 150
    pg = a[a.index("--pages") + 1] if "--pages" in a else None
    main(a[0], a[1] if len(a) > 1 and not a[1].startswith("--") else "Private PDF", dpi, pg)
