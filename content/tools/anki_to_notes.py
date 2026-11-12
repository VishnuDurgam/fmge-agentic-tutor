"""Convert an Anki .apkg deck into a text file the tutor can search. PRIVATE USE ONLY.

Output goes to content/raw/local-private/, which is git-ignored and docker-ignored so the deck is never
committed or deployed. Only use decks whose owners allow it.
Usage: python content/tools/anki_to_notes.py "deck.apkg" "Source label"
Needs: pip install zstandard
"""
import html
import io
import re
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "raw" / "local-private"


def clean(s: str) -> str:
    s = re.sub(r"<img[^>]*>", " [image] ", s)
    s = re.sub(r"<br\s*/?>|</div>|</p>", "\n", s)
    return re.sub(r"\n{2,}", "\n", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def notes(apkg: Path):
    z = zipfile.ZipFile(apkg)
    if "collection.anki21b" in z.namelist():
        import zstandard
        data = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(z.read("collection.anki21b"))).read()
    else:
        data = z.read("collection.anki21" if "collection.anki21" in z.namelist() else "collection.anki2")
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        f.write(data)
        f.flush()
        for (flds,) in sqlite3.connect(f.name).execute("select flds from notes"):
            yield [clean(x) for x in flds.split("\x1f")]


def main(apkg: str, label: str):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [f"Q: {f[0]}\nA: {' | '.join(x for x in f[1:] if x)}" for f in notes(Path(apkg)) if f and f[0]]
    name = re.sub(r"\W+", "_", Path(apkg).stem).strip("_")
    (OUT / f"{name}.md").write_text(f"source: {label}\ntitle: {Path(apkg).stem}\n\n" + "\n\n".join(rows) + "\n")
    print(f"{len(rows)} cards -> {OUT / (name + '.md')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Private deck")
