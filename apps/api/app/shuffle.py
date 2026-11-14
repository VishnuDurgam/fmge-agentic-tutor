"""Shuffle answer options so the same question does not always show the answer in the same place."""
import json
import random
import re

_FIXED = re.compile(r"\b(above|both|neither|none of|all of)\b|^\s*\(?[a-d]\)?\s+(and|&)\s|\b(a|b|c|d)\s+(and|&)\s+(a|b|c|d)\b", re.I)


def perm(seed: str | None, options: list[str]) -> list[int]:
    """Return p so that shuffled[i] = options[p[i]]. Options like 'All of the above' keep their order."""
    n = len(options)
    p = list(range(n))
    if any(_FIXED.search(o or "") for o in options):
        return p
    (random.Random(seed) if seed is not None else random).shuffle(p)
    return p


def apply(options: list[str], p: list[int]) -> list[str]:
    return [options[i] for i in p]


def to_shuffled(orig_index: int | None, p: list[int]):
    return None if orig_index is None else p.index(orig_index)


def to_original(shuffled_index: int | None, p: list[int]):
    return None if shuffled_index is None else p[shuffled_index]


def dump(p):
    return json.dumps(p)
