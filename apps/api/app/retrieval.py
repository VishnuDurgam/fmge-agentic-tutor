"""BM25 retrieval over ingested chunks (content/chunks.jsonl). No embedding key needed."""
import json
import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from .config import CONTENT_DIR


def _tok(t: str):
    return re.findall(r"[a-z0-9]+", t.lower())


@lru_cache(maxsize=1)
def _index():
    path = CONTENT_DIR / "chunks.jsonl"
    chunks = []
    if path.exists():
        chunks = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if not chunks:
        return [], None
    return chunks, BM25Okapi([_tok(c["text"]) for c in chunks])


def reload():
    _index.cache_clear()


def search(query: str, k: int = 4):
    chunks, bm = _index()
    if not bm:
        return []
    q = set(_tok(query))
    scores = bm.get_scores(list(q))
    # BM25 idf can go <= 0 on tiny corpora, so gate on token overlap instead of score sign
    hits = [i for i in range(len(chunks)) if q & set(_tok(chunks[i]["text"]))]
    top = sorted(hits, key=lambda i: scores[i], reverse=True)[:k]
    return [chunks[i] | {"score": float(scores[i])} for i in top]
