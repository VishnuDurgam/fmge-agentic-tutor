"""Batch-generate draft questions from the library: python -m app.gen_cli [topic] [count] [--source "Source label"]"""
import sys

from .agents import generate
from .db import init_db

if __name__ == "__main__":
    init_db()
    args = sys.argv[1:]
    source = args[args.index("--source") + 1] if "--source" in args else None
    if "--source" in args:
        del args[args.index("--source"):args.index("--source") + 2]
    topic = args[0] if args and not args[0].isdigit() else None
    n = int(args[-1]) if args and args[-1].isdigit() else 10
    out = generate.questions(topic, n, source)
    made = out["made"]
    if out["skipped_private"]:
        print(f"Skipped {out['skipped_private']} private passages: set OLLAMA_MODEL to use a local model")
    print(f"Generated {len(made)} draft questions (unreviewed)")
    for m in made:
        print("-", m["subject"], "|", m["stem"][:80], "|", m["source"])
