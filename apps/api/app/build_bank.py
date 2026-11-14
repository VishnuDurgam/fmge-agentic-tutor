"""Write questions from the open textbooks and save them into content/seed/generated.json.

Run by the GitHub Action in .github/workflows/question-bank.yml (free), or by hand:
    cd apps/api && python -m app.build_bank 60
The app loads every file in content/seed/ at start-up, so questions saved here survive server restarts.
Only open-licence books are used here. Questions made from private workbooks stay in the app, per user.
"""
import json
import sys

from .agents import generate
from .config import CONTENT_DIR
from .db import conn, init_db

OUT = CONTENT_DIR / "seed" / "generated.json"


def main(count: int = 60, per_call: int = 6) -> int:
    init_db()
    made = 0
    error = ""
    while made < count:
        try:
            got = generate.questions(None, min(per_call, count - made))["made"]
        except Exception as e:  # noqa: BLE001  (quota used up: keep what we have)
            error = str(e)[:300]
            break
        if not got:
            break
        made += len(got)
        print(f"made {made}/{count}", flush=True)
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    seen = {q["id"] for q in existing}
    with conn() as c:
        rows = c.execute("SELECT * FROM questions WHERE id LIKE 'gen-%' AND owner IS NULL").fetchall()
    for r in rows:
        if r["id"] not in seen:
            existing.append({"id": r["id"], "subject": r["subject"], "topic": r["topic"], "stem": r["stem"],
                             "options": json.loads(r["options"]), "answer": r["answer"],
                             "explanation": r["explanation"], "source": r["source"], "reviewed": 0})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(existing, indent=1, ensure_ascii=False) + "\n")
    print(f"saved {len(existing)} generated questions in total" + (f"; stopped early: {error}" if error else ""))
    return made


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
