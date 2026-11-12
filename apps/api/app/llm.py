"""Thin LLM wrapper. Falls back to an offline stub so the app and tests run without a key."""
from .config import ANTHROPIC_API_KEY, MODEL

_client = None


def available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def complete(system: str, user: str, max_tokens: int = 900) -> str:
    global _client
    if not available():
        return "[offline mode: set ANTHROPIC_API_KEY for AI answers]\n\n" + user[:600]
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = _client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "text", None))
