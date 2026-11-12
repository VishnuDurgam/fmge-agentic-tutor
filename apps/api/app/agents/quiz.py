"""Adaptive question selection: weight weak topics, avoid recent repeats, explain on demand."""
import json
import random

from .. import llm
from ..db import conn


def topic_stats(learner: str):
    with conn() as c:
        rows = c.execute(
            "SELECT subject, topic, COUNT(*) n, SUM(correct) ok FROM attempts "
            "WHERE learner=? GROUP BY subject, topic", (learner,)).fetchall()
    return [{"subject": r["subject"], "topic": r["topic"], "attempts": r["n"],
             "accuracy": round(r["ok"] / r["n"], 2)} for r in rows]


def next_question(learner: str, subject: str | None = None):
    with conn() as c:
        qs = c.execute("SELECT * FROM questions" + (" WHERE subject=?" if subject else ""),
                       (subject,) if subject else ()).fetchall()
        recent = {r["question_id"] for r in c.execute(
            "SELECT question_id FROM attempts WHERE learner=? ORDER BY id DESC LIMIT 20", (learner,))}
    if not qs:
        return None
    acc = {(s["subject"], s["topic"]): s["accuracy"] for s in topic_stats(learner)}
    pool = [q for q in qs if q["id"] not in recent] or list(qs)
    # unseen topics get weight 1.0, weak topics up to 1.0, strong topics down to 0.2
    weights = [max(0.2, 1.0 - acc.get((q["subject"], q["topic"]), 0.0) * 0.8) if (q["subject"], q["topic"]) in acc else 1.0
               for q in pool]
    q = random.choices(pool, weights=weights, k=1)[0]
    return _public(q)


def _public(q):
    return {"id": q["id"], "subject": q["subject"], "topic": q["topic"], "stem": q["stem"],
            "options": json.loads(q["options"]), "reviewed": bool(q["reviewed"])}


def submit(learner: str, question_id: str, choice: int):
    with conn() as c:
        q = c.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not q:
            return None
        ok = int(choice == q["answer"])
        c.execute("INSERT INTO attempts (learner, question_id, subject, topic, correct) VALUES (?,?,?,?,?)",
                  (learner, question_id, q["subject"], q["topic"], ok))
    opts = json.loads(q["options"])
    extra = ""
    if not ok and llm.available():
        extra = llm.complete(
            "You are an FMGE tutor. In 3 sentences explain why the chosen option is wrong and the key to remember.",
            f"Q: {q['stem']}\nOptions: {opts}\nCorrect: {opts[q['answer']]}\nChosen: {opts[choice]}")
    return {"correct": bool(ok), "answer": q["answer"], "explanation": q["explanation"],
            "ai_feedback": extra, "reviewed": bool(q["reviewed"]), "source": q["source"]}
