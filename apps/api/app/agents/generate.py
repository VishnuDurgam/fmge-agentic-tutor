"""Learn from the library, then write exam-style questions and flashcards grounded in the passages."""
import hashlib
import json
import random

from .. import llm, retrieval
from ..config import SUBJECTS
from ..db import conn
from . import flashcards

QSYS = (
    "You write FMGE-style single-best-answer MCQs for MBBS graduates. Use ONLY facts stated in the "
    "passage. Reply with ONLY a JSON list. Each item: {\"subject\": one of %s, \"topic\": short string, "
    "\"stem\": string, \"options\": [4 strings], \"answer\": index 0-3, \"explanation\": 1-3 sentences "
    "with the key point to remember}. Make distractors plausible; no 'all of the above'."
) % SUBJECTS


def _json_list(raw: str):
    try:
        return json.loads(raw[raw.index("["): raw.rindex("]") + 1])
    except ValueError:
        return []


def _valid(q) -> bool:
    return (isinstance(q, dict) and isinstance(q.get("options"), list) and len(q["options"]) == 4
            and isinstance(q.get("answer"), int) and 0 <= q["answer"] < 4 and q.get("stem") and q.get("explanation"))


def passages(topic: str | None, k: int):
    if topic:
        return retrieval.search(topic, k=k)
    chunks, _ = retrieval._index()
    return random.sample(chunks, min(k, len(chunks))) if chunks else []


def questions(topic: str | None = None, n: int = 5):
    """Generate up to n MCQs from library passages and store them as unreviewed drafts."""
    if not llm.available():
        return []
    made = []
    for p in passages(topic, max(1, n)):
        if len(made) >= n:
            break
        raw = llm.complete(QSYS, f"Passage ({p['source']} / {p.get('title','')}):\n{p['text']}\n\nWrite 1 MCQ.", 900)
        for q in _json_list(raw)[:1]:
            if not _valid(q):
                continue
            qid = "gen-" + hashlib.sha1(q["stem"].encode()).hexdigest()[:10]
            subject = q.get("subject") if q.get("subject") in SUBJECTS else "Anatomy"
            src = f"{p['source']} / {p.get('title','')}".strip(" /")
            with conn() as c:
                c.execute("INSERT OR IGNORE INTO questions VALUES (?,?,?,?,?,?,?,?,0)",
                          (qid, subject, q.get("topic", p.get("title", "")), q["stem"],
                           json.dumps(q["options"]), q["answer"], q["explanation"], src))
            made.append({"id": qid, "subject": subject, "stem": q["stem"], "source": src})
    return made


def cards(learner: str, topic: str, n: int = 5):
    if not llm.available():
        return []
    ctx = "\n\n".join(f"{p['text']}" for p in passages(topic, 3))
    raw = llm.complete(
        "Make FMGE flashcards from the passages only. Reply ONLY with a JSON list of {\"front\":..., \"back\":...}; one fact per card.",
        f"Topic: {topic}\nPassages:\n{ctx or '(none)'}\nMake {n} cards.", 1200)
    out = []
    for x in _json_list(raw)[:n]:
        if isinstance(x, dict) and x.get("front") and x.get("back"):
            out.append({"id": flashcards.add_card(learner, x["front"], x["back"], ""), **x})
    return out
