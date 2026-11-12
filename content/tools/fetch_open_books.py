"""Download open-licence textbooks (OpenStax, CC BY 4.0) from GitHub and convert to plain text.

Usage: python content/tools/fetch_open_books.py [workdir]
Writes content/raw/openstax-<book>/<module>.md with 'source:' and 'title:' header lines.
Then run: cd apps/api && python -m app.ingest
Add more books by appending to BOOKS (only legally reusable ones).
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOKS = {
    "anatomy-physiology": ("osbooks-anatomy-physiology", "OpenStax Anatomy and Physiology 2e (CC BY 4.0)"),
    "microbiology": ("osbooks-microbiology", "OpenStax Microbiology (CC BY 4.0)"),
}
SKIP = {"figure", "table", "media", "equation", "metadata", "glossary", "exercise", "solution"}


def strip(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(el) -> str:
    parts = []

    def walk(e):
        t = strip(e.tag)
        if t in SKIP:
            return
        if t in {"para", "title", "item"} and e is not el:
            parts.append("\n")
        if e.text:
            parts.append(e.text)
        for ch in e:
            walk(ch)
            if ch.tail:
                parts.append(ch.tail)

    walk(el)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", "".join(parts))).strip()


def convert(book_key: str, repo: str, label: str, work: Path):
    dest = work / repo
    if not dest.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"https://github.com/openstax/{repo}", str(dest)], check=True)
    out = ROOT / "content" / "raw" / f"openstax-{book_key}"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for mod in sorted((dest / "modules").glob("m*/index.cnxml")):
        root = ET.parse(mod).getroot()
        title_el = root.find("{*}title")
        title = (title_el.text or "").strip() if title_el is not None else mod.parent.name
        content = root.find("{*}content")
        body = text_of(content) if content is not None else ""
        if len(body) < 400:
            continue
        (out / f"{mod.parent.name}.md").write_text(f"source: {label}\ntitle: {title}\n\n{body}\n")
        n += 1
    print(f"{book_key}: {n} sections")


if __name__ == "__main__":
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/open_books")
    work.mkdir(parents=True, exist_ok=True)
    for k, (repo, label) in BOOKS.items():
        convert(k, repo, label, work)
