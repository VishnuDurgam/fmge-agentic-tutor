"""SM-2 spaced repetition plus AI card generation from a topic or pasted notes."""
from datetime import date, timedelta

from ..db import conn


def sm2(ease: float, interval: int, reps: int, quality: int):
    """quality 0-5. Returns (ease, interval, reps)."""
    if quality < 3:
        return max(1.3, ease - 0.2), 1, 0
    ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    reps += 1
    interval = 1 if reps == 1 else 6 if reps == 2 else round(interval * ease)
    return ease, interval, reps


def add_card(learner, front, back, subject=""):
    with conn() as c:
        cur = c.execute("INSERT INTO cards (learner, front, back, subject) VALUES (?,?,?,?)",
                        (learner, front, back, subject))
        return cur.lastrowid


def due(learner, limit=20):
    with conn() as c:
        rows = c.execute("SELECT * FROM cards WHERE learner=? AND due<=date('now') ORDER BY due LIMIT ?",
                         (learner, limit)).fetchall()
    return [dict(r) for r in rows]


def review(learner, card_id, quality):
    with conn() as c:
        r = c.execute("SELECT * FROM cards WHERE id=? AND learner=?", (card_id, learner)).fetchone()
        if not r:
            return None
        ease, interval, reps = sm2(r["ease"], r["interval"], r["reps"], quality)
        nxt = (date.today() + timedelta(days=interval)).isoformat()
        c.execute("UPDATE cards SET ease=?, interval=?, reps=?, due=? WHERE id=?",
                  (ease, interval, reps, nxt, card_id))
    return {"next_due": nxt, "interval": interval}
