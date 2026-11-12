"""Study planner: allocates days across subjects by weakness and standard FMGE weightage."""
from datetime import date

from ..config import SUBJECTS
from ..db import conn
from .quiz import topic_stats

# Rough relative weight (higher = more questions / more commonly high-yield). Tune with real PYQ data.
BASE_WEIGHT = {s: 1.0 for s in SUBJECTS}
BASE_WEIGHT.update({"Medicine": 2.0, "Surgery": 2.0, "Obstetrics and Gynaecology": 2.0,
                    "Community Medicine": 1.8, "Pathology": 1.6, "Pharmacology": 1.6,
                    "Microbiology": 1.5, "Paediatrics": 1.4, "Physiology": 1.3,
                    "Anatomy": 1.3, "Biochemistry": 1.2})


def set_profile(learner, exam_date, hours_per_day):
    with conn() as c:
        c.execute("INSERT INTO profiles VALUES (?,?,?) ON CONFLICT(learner) DO UPDATE SET "
                  "exam_date=excluded.exam_date, hours_per_day=excluded.hours_per_day",
                  (learner, exam_date, hours_per_day))


def build_plan(learner, today=None):
    today = today or date.today()
    with conn() as c:
        p = c.execute("SELECT * FROM profiles WHERE learner=?", (learner,)).fetchone()
    if not p:
        return None
    days_left = (date.fromisoformat(p["exam_date"]) - today).days
    if days_left <= 0:
        return {"days_left": days_left, "plan": [], "note": "Exam date has passed. Update your exam date."}
    revision_days = min(14, days_left // 5)
    study_days = max(days_left - revision_days, 1)

    acc = {}
    for s in topic_stats(learner):
        a = acc.setdefault(s["subject"], [0, 0])
        a[0] += s["accuracy"] * s["attempts"]
        a[1] += s["attempts"]
    weights = {}
    for s in SUBJECTS:
        weakness = 1.0 + (1.0 - acc[s][0] / acc[s][1]) if s in acc and acc[s][1] >= 5 else 1.0
        weights[s] = BASE_WEIGHT[s] * weakness
    total = sum(weights.values())
    plan = [{"subject": s, "days": max(1, round(study_days * w / total)),
             "hours": round(max(1, round(study_days * w / total)) * p["hours_per_day"], 1)}
            for s, w in sorted(weights.items(), key=lambda x: -x[1])]
    return {"days_left": days_left, "study_days": study_days, "revision_days": revision_days,
            "hours_per_day": p["hours_per_day"], "plan": plan,
            "daily_routine": ["60% new topic + notes", "25% Q-bank on that subject",
                              "15% flashcard reviews (spaced repetition)"]}
