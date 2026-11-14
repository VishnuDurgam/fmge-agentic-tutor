"""Turn your own notes (PDF, photos, text) in content/notes/ into text the app can learn from.

Output: content/raw/notes/<name>.md with 'source:' and 'title:' header lines. Typed pages are read directly,
scanned or handwritten-looking pages go through OCR (Tesseract). Files already converted are skipped.
Run by .github/workflows/ocr-notes.yml, or by hand: python content/tools/ocr_notes.py [notes_dir] [out_dir]
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMG = {".png", ".jpg", ".jpeg", ".webp"}


def ocr(data: bytes) -> str:
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(io.BytesIO(data))).strip()


def pdf_text(path: Path) -> list[str]:
    import pymupdf
    pages = []
    for i, page in enumerate(pymupdf.open(path)):
        t = page.get_text().strip()
        if len(t) < 40:
            t = ocr(page.get_pixmap(dpi=150).tobytes("png"))
        pages.append(t)
        if (i + 1) % 10 == 0:
            print(f"  {path.name}: {i + 1} pages", flush=True)
    return pages


def convert(src: Path, out: Path) -> bool:
    ext = src.suffix.lower()
    if ext == ".pdf":
        pages = pdf_text(src)
    elif ext in IMG:
        pages = [ocr(src.read_bytes())]
    elif ext in {".txt", ".md"}:
        pages = [src.read_text(errors="ignore")]
    else:
        return False
    body = "\n\n".join(f"Page {i + 1}\n{t}" for i, t in enumerate(pages) if t.strip())
    if not body:
        print(f"  no readable text in {src.name}")
        return False
    out.write_text(f"source: Notes: {src.stem}\ntitle: {src.stem}\n\n{body}\n")
    return True


def main(notes: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    done = 0
    for src in sorted(p for p in notes.rglob("*") if p.is_file()):
        out = out_dir / (src.stem + ".md")
        if out.exists():
            continue
        print("reading", src.name, flush=True)
        done += convert(src, out)
    print(f"converted {done} file(s)")
    return done


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]) if a else ROOT / "content" / "notes", Path(a[1]) if len(a) > 1 else ROOT / "content" / "raw" / "notes")
