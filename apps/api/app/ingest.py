"""Ingest PDFs / text / markdown from content/raw into content/chunks.jsonl for retrieval.

Usage: python -m app.ingest [path ...]   (defaults to everything in content/raw)
Only ingest material you have the right to use (see content/SOURCES.md).
"""
import json
import sys
from pathlib import Path

from .config import CONTENT_DIR


def read(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    return path.read_text(errors="ignore")


def chunk(text: str, size=900, overlap=150):
    text = " ".join(text.split())
    i = 0
    while i < len(text):
        yield text[i:i + size]
        i += size - overlap


def main(paths):
    files = [Path(p) for p in paths] or [p for p in (CONTENT_DIR / "raw").rglob("*") if p.is_file()]
    out = CONTENT_DIR / "chunks.jsonl"
    n = 0
    with out.open("w") as f:
        for p in files:
            if p.suffix.lower() not in {".pdf", ".txt", ".md"}:
                continue
            for c in chunk(read(p)):
                f.write(json.dumps({"source": p.name, "text": c}) + "\n")
                n += 1
    print(f"Wrote {n} chunks from {len(files)} files to {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
