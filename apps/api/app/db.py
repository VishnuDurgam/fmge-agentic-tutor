import json
import sqlite3
from contextlib import contextmanager

from .config import CONTENT_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, subject TEXT, topic TEXT, stem TEXT,
  options TEXT, answer INTEGER, explanation TEXT, source TEXT,
  reviewed INTEGER DEFAULT 0, owner TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, learner TEXT, question_id TEXT,
  subject TEXT, topic TEXT, correct INTEGER, ts TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT, learner TEXT, front TEXT, back TEXT,
  subject TEXT, ease REAL DEFAULT 2.5, interval INTEGER DEFAULT 0,
  reps INTEGER DEFAULT 0, due TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS mocks (
  id TEXT PRIMARY KEY, learner TEXT, preset TEXT, started INTEGER, duration_s INTEGER,
  status TEXT DEFAULT 'in_progress', score INTEGER
);
CREATE TABLE IF NOT EXISTS mock_items (
  mock_id TEXT, pos INTEGER, question_id TEXT, choice INTEGER, PRIMARY KEY (mock_id, pos)
);
CREATE TABLE IF NOT EXISTS docs (
  id TEXT PRIMARY KEY, learner TEXT, name TEXT, kind TEXT, status TEXT DEFAULT 'processing',
  pages_done INTEGER DEFAULT 0, pages_total INTEGER DEFAULT 0, error TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT, learner TEXT, source TEXT, title TEXT, text TEXT
);
CREATE INDEX IF NOT EXISTS idx_uc_learner ON user_chunks(learner);
CREATE TABLE IF NOT EXISTS served (
  learner TEXT, question_id TEXT, perm TEXT, PRIMARY KEY (learner, question_id)
);
CREATE TABLE IF NOT EXISTS profiles (
  learner TEXT PRIMARY KEY, exam_date TEXT, hours_per_day REAL DEFAULT 4
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        try:  # older databases created before per-user questions existed
            c.execute("ALTER TABLE questions ADD COLUMN owner TEXT")
        except sqlite3.OperationalError:
            pass
        seed_dir = CONTENT_DIR / "seed"
        for f in sorted(seed_dir.glob("*.json")) if seed_dir.exists() else []:
            for q in json.loads(f.read_text()):
                c.execute(
                    "INSERT OR IGNORE INTO questions (id, subject, topic, stem, options, answer, explanation, source, reviewed) VALUES (?,?,?,?,?,?,?,?,?)",
                    (q["id"], q["subject"], q["topic"], q["stem"],
                     json.dumps(q["options"]), q["answer"], q["explanation"],
                     q.get("source", "original"), int(q.get("reviewed", 0))),
                )
