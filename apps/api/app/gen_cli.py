"""Batch-generate draft questions from the library: python -m app.gen_cli [topic] [count]"""
import sys

from .agents import generate
from .db import init_db

if __name__ == "__main__":
    init_db()
    topic = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else None
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 10
    made = generate.questions(topic, n)
    print(f"Generated {len(made)} draft questions (unreviewed)")
    for m in made:
        print("-", m["subject"], "|", m["stem"][:80], "|", m["source"])
