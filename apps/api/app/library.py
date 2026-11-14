"""Per-user study library: upload PDFs, images or text, or import a link. Scanned pages are read with OCR.

Everything a person adds is stored under their learner id and is only searched for them. It never
appears in anyone else's tutor answers, question bank or mock exams.
"""
import io
import ipaddress
import os
import re
import socket
import threading
import uuid
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import httpx
from rank_bm25 import BM25Okapi

from .db import conn
from .ingest import chunk

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "150"))
RUN_SYNC = False  # tests set this so processing finishes before the request returns
_tok = lambda t: re.findall(r"[a-z0-9]+", t.lower())  # noqa: E731


# ---------- jobs ----------
def new_doc(learner: str, name: str, kind: str) -> str:
    did = uuid.uuid4().hex[:12]
    with conn() as c:
        c.execute("INSERT INTO docs (id, learner, name, kind) VALUES (?,?,?,?)", (did, learner, name, kind))
    return did


def _set(did, **kw):
    with conn() as c:
        c.execute(f"UPDATE docs SET {', '.join(k + '=?' for k in kw)} WHERE id=?", (*kw.values(), did))


def _store(did, learner, name, title, text):
    rows = [(did, learner, name, title, t) for t in chunk(text)]
    if rows:
        with conn() as c:
            c.executemany("INSERT INTO user_chunks (doc_id, learner, source, title, text) VALUES (?,?,?,?,?)", rows)
    return len(rows)


def run(fn, *args):
    if RUN_SYNC:
        fn(*args)
    else:
        threading.Thread(target=fn, args=args, daemon=True).start()


def _ocr_image(data: bytes) -> str:
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(io.BytesIO(data))).strip()


def process_pdf(path: str, learner: str, did: str, name: str):
    try:
        import pymupdf
        doc = pymupdf.open(path)
        _set(did, pages_total=len(doc))
        stored = 0
        for i, page in enumerate(doc):
            text = page.get_text().strip()  # embedded text layer first, OCR only for scanned pages
            if len(text) < 40:
                text = _ocr_image(page.get_pixmap(dpi=150).tobytes("png"))
            if text:
                stored += _store(did, learner, name, f"{name}, page {i + 1}", text)
            if (i + 1) % 5 == 0 or i + 1 == len(doc):
                _set(did, pages_done=i + 1)
        _set(did, status="ready" if stored else "error", error=None if stored else "No readable text found in this file")
    except Exception as e:  # noqa: BLE001
        _set(did, status="error", error=_friendly(e))
    finally:
        _cleanup(path)


def process_image(path: str, learner: str, did: str, name: str):
    try:
        text = _ocr_image(open(path, "rb").read())
        n = _store(did, learner, name, name, text)
        _set(did, status="ready" if n else "error", pages_done=1, pages_total=1, error=None if n else "No readable text found in this image")
    except Exception as e:  # noqa: BLE001
        _set(did, status="error", error=_friendly(e))
    finally:
        _cleanup(path)


def process_text(text: str, learner: str, did: str, name: str):
    n = _store(did, learner, name, name, text)
    _set(did, status="ready" if n else "error", pages_done=1, pages_total=1, error=None if n else "The file is empty")


def _friendly(e: Exception) -> str:
    if "tesseract" in str(e).lower():
        return "The OCR engine (Tesseract) is not installed on the server, so scanned pages cannot be read"
    return str(e)[:200]


def _cleanup(path):
    try:
        os.remove(path)
    except OSError:
        pass


def ingest_bytes(learner: str, filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()
    did = new_doc(learner, filename, ext.lstrip(".") or "file")
    if ext in {".txt", ".md"}:
        run(process_text, data.decode("utf-8", "ignore"), learner, did, filename)
    elif ext in {".png", ".jpg", ".jpeg", ".webp"} or ext == ".pdf":
        path = f"/tmp/fmge-{did}{ext}"
        with open(path, "wb") as f:
            f.write(data)
        run(process_pdf if ext == ".pdf" else process_image, path, learner, did, filename)
    else:
        _set(did, status="error", error="Unsupported file type. Use PDF, PNG, JPG, TXT or MD.")
    return did


# ---------- links ----------
class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "noscript"} and self.skip:
            self.skip -= 1
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3", "tr"}:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", "".join(p.out))).strip()


def normalize_link(url: str) -> str:
    """Turn a Google Drive 'share' link into a direct download link."""
    u = urlparse(url)
    if u.netloc.endswith("drive.google.com"):
        m = re.search(r"/file/d/([\w-]+)", u.path) or None
        fid = m.group(1) if m else (parse_qs(u.query).get("id") or [None])[0]
        if fid:
            return f"https://drive.google.com/uc?export=download&id={fid}"
    return url


def _check_public(url: str):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("Only http and https links are supported")
    for info in socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80)):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("That address is not allowed")


def fetch(url: str, limit_mb: int = MAX_UPLOAD_MB):
    """Download a public link. Redirects are followed manually so each hop is checked."""
    url = normalize_link(url)
    for _ in range(5):
        _check_public(url)
        with httpx.stream("GET", url, timeout=60, follow_redirects=False, headers={"User-Agent": "FMGE-Tutor/1.0"}) as r:
            if r.is_redirect:
                url = str(httpx.URL(url).join(r.headers["location"]))
                continue
            r.raise_for_status()
            buf = bytearray()
            for part in r.iter_bytes():
                buf += part
                if len(buf) > limit_mb * 1024 * 1024:
                    raise ValueError(f"File is larger than {limit_mb} MB")
            return bytes(buf), r.headers.get("content-type", ""), url
    raise ValueError("Too many redirects")


def ingest_link(learner: str, url: str) -> str:
    did = new_doc(learner, url[:120], "link")

    def job():
        try:
            data, ctype, final = fetch(url)
            name = os.path.basename(urlparse(final).path) or urlparse(final).netloc
            _set(did, name=name[:120])
            if data[:4] == b"%PDF" or "pdf" in ctype:
                path = f"/tmp/fmge-{did}.pdf"
                open(path, "wb").write(data)
                process_pdf(path, learner, did, name)
            elif ctype.startswith("image/"):
                path = f"/tmp/fmge-{did}.img"
                open(path, "wb").write(data)
                process_image(path, learner, did, name)
            else:
                if "drive.google.com" in final or "accounts.google.com" in final:
                    raise ValueError("Google Drive blocked the download. Set sharing to 'Anyone with the link' or upload the file directly")
                process_text(html_to_text(data.decode("utf-8", "ignore")), learner, did, name)
        except Exception as e:  # noqa: BLE001
            _set(did, status="error", error=_friendly(e))

    run(job)
    return did


# ---------- listing, deleting, searching ----------
def list_docs(learner: str):
    with conn() as c:
        rows = c.execute("SELECT id, name, kind, status, pages_done, pages_total, error, created FROM docs "
                         "WHERE learner=? ORDER BY created DESC", (learner,)).fetchall()
    return [dict(r) for r in rows]


def delete_doc(learner: str, did: str) -> bool:
    with conn() as c:
        d = c.execute("SELECT id FROM docs WHERE id=? AND learner=?", (did, learner)).fetchone()
        if not d:
            return False
        c.execute("DELETE FROM user_chunks WHERE doc_id=?", (did,))
        c.execute("DELETE FROM docs WHERE id=?", (did,))
    return True


_cache: dict = {}


def _index(learner: str):
    with conn() as c:
        sig = c.execute("SELECT COUNT(*) n, COALESCE(MAX(id),0) m FROM user_chunks WHERE learner=?", (learner,)).fetchone()
        key = (sig["n"], sig["m"])
        if _cache.get(learner, (None,))[0] == key:
            return _cache[learner][1], _cache[learner][2]
        rows = c.execute("SELECT source, title, text FROM user_chunks WHERE learner=?", (learner,)).fetchall()
    chunks = [dict(r, owner=learner) for r in rows]
    bm = BM25Okapi([_tok(x["text"]) for x in chunks]) if chunks else None
    _cache[learner] = (key, chunks, bm)
    return chunks, bm


def search_user(learner: str, query: str, k: int = 4, source: str | None = None):
    chunks, bm = _index(learner)
    if not bm:
        return []
    q = set(_tok(query))
    scores = bm.get_scores(list(q))
    hits = [i for i, c in enumerate(chunks) if q & set(_tok(c["text"])) and (not source or c["source"] == source)]
    return [chunks[i] | {"score": float(scores[i])} for i in sorted(hits, key=lambda i: scores[i], reverse=True)[:k]]


def sample_user(learner: str, source: str | None, k: int):
    import random
    chunks, _ = _index(learner)
    pool = [c for c in chunks if not source or c["source"] == source]
    return random.sample(pool, min(k, len(pool)))


def source_names(learner: str):
    with conn() as c:
        return [r["name"] for r in c.execute("SELECT name FROM docs WHERE learner=? AND status='ready'", (learner,))]
