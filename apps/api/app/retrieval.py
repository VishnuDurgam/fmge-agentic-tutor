"""BM25 retrieval over ingested chunks (content/chunks.jsonl). No embedding key needed."""
import json
import re
from contextvars import ContextVar
from functools import lru_cache

from rank_bm25 import BM25Okapi

from .config import CONTENT_DIR


# True only for requests that sent the correct private-notes code (set in main.py)
unlocked: ContextVar[bool] = ContextVar("unlocked", default=False)


def visible(chunks):
    return chunks if unlocked.get() else [c for c in chunks if not c.get("private")]


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


def search(query: str, k: int = 4, source: str | None = None):
    chunks, bm = _index()
    if not bm:
        return []
    q = set(_tok(query))
    scores = bm.get_scores(list(q))
    # BM25 idf can go <= 0 on tiny corpora, so gate on token overlap instead of score sign
    ok = unlocked.get()
    hits = [i for i in range(len(chunks)) if (ok or not chunks[i].get("private")) and q & set(_tok(chunks[i]["text"])) and (not source or chunks[i]["source"] == source)]
    top = sorted(hits, key=lambda i: scores[i], reverse=True)[:k]
    return [chunks[i] | {"score": float(scores[i])} for i in top]


def search_all(query: str, k: int = 4, learner: str | None = None, source: str | None = None):
    """Search the shared library plus this person's own uploads (uploads first)."""
    from . import library
    own = library.search_user(learner, query, k, source) if learner else []
    shared = [] if (source and own) else search(query, k, source)
    return (own[: max(1, (k + 1) // 2)] + shared)[:k] if own else shared
