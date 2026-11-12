"""Import MedMCQA (Indian AIIMS / NEET PG MCQs) from a local JSON-lines file.

Get the data from https://medmcqa.github.io or the Hugging Face dataset 'openlifescienceai/medmcqa'
(train.json is JSON lines with: question, opa, opb, opc, opd, cop, exp, subject_name, topic_name).
Licensing is mixed (code MIT, dataset card Apache-2.0, some pages say CC BY-NC-SA, and the questions
come from public exams), so keep this project non-commercial and credit MedMCQA (Pal et al., 2022).

Usage: python -m app.import_medmcqa path/to/train.json [--max 5000]
Also writes the explanations to content/raw/medmcqa/ so the tutor can retrieve them for clinical subjects.
"""
import json
import sys
from pathlib import Path

from .config import CONTENT_DIR, SUBJECTS
from .db import conn, init_db

SUBJECT_MAP = {
    "Gynaecology & Obstetrics": "Obstetrics and Gynaecology", "Social & Preventive Medicine": "Community Medicine",
    "Pediatrics": "Paediatrics", "Skin": "Dermatology", "Anaesthesia": "Anaesthesia", "Radiology": "Radiology",
    "Forensic Medicine": "Forensic Medicine", "Orthopaedics": "Orthopaedics",
}
ATTRIBUTION = "MedMCQA (Pal et al., 2022; AIIMS/NEET PG)"


def map_subject(name: str | None):
    name = (name or "").strip()
    name = SUBJECT_MAP.get(name, name)
    return name if name in SUBJECTS else None  # drops Dental/Unknown etc.


def load(path: Path, limit: int):
    n = 0
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            subj = map_subject(r.get("subject_name"))
            opts = [r.get("opa"), r.get("opb"), r.get("opc"), r.get("opd")]
            cop = r.get("cop")
            if not subj or not all(opts) or cop not in (0, 1, 2, 3) or not r.get("question"):
                continue
            yield {"id": "mm-" + str(r["id"]), "subject": subj, "topic": r.get("topic_name") or subj,
                   "stem": r["question"].strip(), "options": [o.strip() for o in opts], "answer": cop,
                   "explanation": (r.get("exp") or "No explanation provided in the source dataset.").strip()}
            n += 1
            if n >= limit:
                return


def main(path: str, limit: int = 5000):
    init_db()
    out_dir = CONTENT_DIR / "raw" / "medmcqa"
    out_dir.mkdir(parents=True, exist_ok=True)
    notes = {}
    count = 0
    with conn() as c:
        for q in load(Path(path), limit):
            c.execute("INSERT OR IGNORE INTO questions VALUES (?,?,?,?,?,?,?,?,0)",
                      (q["id"], q["subject"], q["topic"], q["stem"], json.dumps(q["options"]),
                       q["answer"], q["explanation"], ATTRIBUTION))
            if not q["explanation"].startswith("No explanation"):
                notes.setdefault(q["subject"], []).append(
                    f"Q: {q['stem']} Answer: {q['options'][q['answer']]}. Explanation: {q['explanation']}")
            count += 1
    for subj, lines in notes.items():
        (out_dir / f"{subj.replace(' ', '_')}.md").write_text(
            f"source: {ATTRIBUTION}\ntitle: {subj} solved questions\n\n" + "\n\n".join(lines) + "\n")
    print(f"Imported {count} questions; wrote explanations for {sum(map(len, notes.values()))} to {out_dir}. Run: python -m app.ingest")


if __name__ == "__main__":
    args = sys.argv[1:]
    lim = int(args[args.index("--max") + 1]) if "--max" in args else 5000
    main(args[0], lim)
