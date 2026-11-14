"""Timed mock exams in the FMGE format: 4-option MCQs, +1 per correct answer, no negative marking,
pass at 50%. Explanations are only revealed after submission (practice mode shows them instantly)."""
import json
import random
import time
import uuid

from .. import shuffle
from ..db import conn

PART_A = ["Anatomy", "Physiology", "Biochemistry", "Pathology", "Microbiology", "Pharmacology",
          "Forensic Medicine", "Community Medicine"]
PART_B = ["Medicine", "Surgery", "Obstetrics and Gynaecology", "Paediatrics", "Ophthalmology", "ENT",
          "Orthopaedics", "Dermatology", "Psychiatry", "Anaesthesia", "Radiology"]
# preset -> (questions, minutes, subjects). Real FMGE: 2 parts x 150 questions x 150 minutes.
PRESETS = {
    "part_a": (150, 150, PART_A),
    "part_b": (150, 150, PART_B),
    "section": (50, 50, PART_A + PART_B),
    "quick": (20, 20, PART_A + PART_B),
    "my_material": (20, 20, None),  # questions made from the learner's own uploads
}
GRACE_S = 5


def _pick(n, subjects, learner=None):
    with conn() as c:
        if subjects is None:  # "my material": only the learner's own questions
            rows = c.execute("SELECT id, subject FROM questions WHERE owner=?", (learner,)).fetchall()
        else:
            rows = c.execute("SELECT id, subject FROM questions WHERE owner IS NULL OR owner=?", (learner,)).fetchall()
    by = {}
    for r in rows:
        if subjects is None or r["subject"] in subjects:
            by.setdefault(r["subject"], []).append(r["id"])
    for v in by.values():
        random.shuffle(v)
    chosen = []
    while len(chosen) < n and any(by.values()):  # round-robin so subjects are mixed evenly
        for s in list(by):
            if by[s] and len(chosen) < n:
                chosen.append(by[s].pop())
    random.shuffle(chosen)
    return chosen


def start(learner, preset="quick"):
    n, minutes, subjects = PRESETS[preset]
    ids = _pick(n, subjects, learner)
    if not ids:
        return None
    mid = uuid.uuid4().hex[:12]
    duration = max(60, round(minutes * 60 * len(ids) / n))  # keep the real pace of one minute per question
    with conn() as c:
        c.execute("INSERT INTO mocks (id, learner, preset, started, duration_s) VALUES (?,?,?,?,?)",
                  (mid, learner, preset, int(time.time()), duration))
        c.executemany("INSERT INTO mock_items (mock_id, pos, question_id) VALUES (?,?,?)",
                      [(mid, i + 1, q) for i, q in enumerate(ids)])
    out = view(learner, mid)
    out["requested"] = n
    return out


def _mock(c, learner, mid):
    m = c.execute("SELECT * FROM mocks WHERE id=? AND learner=?", (mid, learner)).fetchone()
    return m


def view(learner, mid):
    """Exam in progress: questions without answers, saved choices, seconds left."""
    with conn() as c:
        m = _mock(c, learner, mid)
        if not m:
            return None
        left = max(0, m["started"] + m["duration_s"] - int(time.time()))
        if m["status"] == "in_progress" and left == 0:
            _grade(c, m)
            m = _mock(c, learner, mid)
        items = c.execute(
            "SELECT i.pos, i.choice, q.id, q.subject, q.stem, q.options FROM mock_items i "
            "JOIN questions q ON q.id=i.question_id WHERE i.mock_id=? ORDER BY i.pos", (mid,)).fetchall()
    return {"id": mid, "preset": m["preset"], "status": m["status"], "seconds_left": left,
            "total": len(items),
            "questions": [_view_q(mid, r) for r in items]}


def _view_q(mid, r):
    opts = json.loads(r["options"])
    p = _perm(mid, r["id"], opts)
    return {"pos": r["pos"], "id": r["id"], "subject": r["subject"], "stem": r["stem"],
            "options": shuffle.apply(opts, p), "choice": shuffle.to_shuffled(r["choice"], p)}


def answer(learner, mid, question_id, choice):
    with conn() as c:
        m = _mock(c, learner, mid)
        if not m:
            return "missing"
        if m["status"] != "in_progress" or time.time() > m["started"] + m["duration_s"] + GRACE_S:
            return "closed"
        q = c.execute("SELECT options FROM questions WHERE id=?", (question_id,)).fetchone()
        if q and choice is not None:
            opts = json.loads(q["options"])
            if not 0 <= choice < len(opts):
                return "missing"
            choice = shuffle.to_original(choice, _perm(mid, question_id, opts))  # stored as the original index
        c.execute("UPDATE mock_items SET choice=? WHERE mock_id=? AND question_id=?", (choice, mid, question_id))
    return "ok"


def _grade(c, m):
    rows = c.execute("SELECT i.choice, q.answer, q.subject FROM mock_items i JOIN questions q "
                     "ON q.id=i.question_id WHERE i.mock_id=?", (m["id"],)).fetchall()
    score = sum(1 for r in rows if r["choice"] == r["answer"])
    c.execute("UPDATE mocks SET status='submitted', score=? WHERE id=?", (score, m["id"]))
    for r in c.execute("SELECT i.choice, q.* FROM mock_items i JOIN questions q ON q.id=i.question_id "
                       "WHERE i.mock_id=? AND i.choice IS NOT NULL", (m["id"],)).fetchall():
        c.execute("INSERT INTO attempts (learner, question_id, subject, topic, correct) VALUES (?,?,?,?,?)",
                  (m["learner"], r["id"], r["subject"], r["topic"], int(r["choice"] == r["answer"])))


def submit(learner, mid):
    with conn() as c:
        m = _mock(c, learner, mid)
        if not m:
            return None
        if m["status"] == "in_progress":
            _grade(c, m)
    return result(learner, mid)


def result(learner, mid):
    with conn() as c:
        m = _mock(c, learner, mid)
        if not m:
            return None
        if m["status"] == "in_progress":
            return {"status": "in_progress"}
        items = c.execute(
            "SELECT i.pos, i.choice, q.* FROM mock_items i JOIN questions q ON q.id=i.question_id "
            "WHERE i.mock_id=? ORDER BY i.pos", (mid,)).fetchall()
    total = len(items)
    subj = {}
    for r in items:
        s = subj.setdefault(r["subject"], {"correct": 0, "total": 0})
        s["total"] += 1
        s["correct"] += int(r["choice"] == r["answer"])
    return {
        "status": "submitted", "score": m["score"], "total": total,
        "answered": sum(1 for r in items if r["choice"] is not None),
        "percent": round(100 * m["score"] / total, 1) if total else 0,
        "pass_mark": (total + 1) // 2, "passed": m["score"] >= (total + 1) // 2,
        "by_subject": [{"subject": k, **v} for k, v in sorted(subj.items())],
        "review": [_review_item(mid, r) for r in items],
    }


def _review_item(mid, r):
    opts = json.loads(r["options"])
    p = _perm(mid, r["id"], opts)
    return {"pos": r["pos"], "stem": r["stem"], "options": shuffle.apply(opts, p),
            "chosen": shuffle.to_shuffled(r["choice"], p), "answer": shuffle.to_shuffled(r["answer"], p),
            "explanation": r["explanation"], "source": r["source"], "reviewed": bool(r["reviewed"])}


def history(learner):
    with conn() as c:
        rows = c.execute("SELECT id, preset, started, status, score FROM mocks WHERE learner=? "
                         "ORDER BY started DESC LIMIT 20", (learner,)).fetchall()
    return [dict(r) for r in rows]


def _perm(mid, qid, options):
    return shuffle.perm(f"{mid}:{qid}", options)  # same order every time this exam is opened
