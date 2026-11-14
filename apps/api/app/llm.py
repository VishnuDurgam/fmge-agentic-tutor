"""LLM wrapper with a fallback chain across free-tier providers (OpenAI-compatible APIs).

Set any of GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY (all have free tiers, no card).
ANTHROPIC_API_KEY is optional and paid. Models are overridable with env vars because free-tier
model lists change often. Without any key the app runs in offline mode.
"""
import os

import httpx

PROVIDERS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
               os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY",
             os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
                   os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")),
}
LOCAL = "ollama"  # optional: a model running on your own computer
ORDER = [p.strip() for p in os.getenv("LLM_PROVIDERS", "ollama,gemini,groq,openrouter,anthropic").split(",") if p.strip()]


def _active():
    out = []
    for p in ORDER:
        if p == LOCAL and os.getenv("OLLAMA_MODEL"):
            out.append(p)
        elif (p == "anthropic" and os.getenv("ANTHROPIC_API_KEY")) or (p in PROVIDERS and os.getenv(PROVIDERS[p][1])):
            out.append(p)
    return out


def available() -> bool:
    return bool(_active())


def _openai_compat(provider, system, user, max_tokens):
    base, key_env, model = PROVIDERS[provider]
    r = httpx.post(f"{base}/chat/completions", timeout=60,
                   headers={"Authorization": f"Bearer {os.environ[key_env]}"},
                   json={"model": model, "max_tokens": max_tokens,
                         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    if r.status_code >= 400:
        raise RuntimeError(f"{provider} returned {r.status_code}: {r.text[:240]}")
    return r.json()["choices"][0]["message"]["content"] or ""


def _ollama(system, user, max_tokens):
    base = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
    r = httpx.post(f"{base}/chat/completions", timeout=300,
                   json={"model": os.environ["OLLAMA_MODEL"], "max_tokens": max_tokens,
                         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"] or ""


def _anthropic(system, user, max_tokens):
    import anthropic
    msg = anthropic.Anthropic().messages.create(
        model=os.getenv("FMGE_MODEL", "claude-sonnet-5-5"), max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in msg.content if getattr(b, "text", None))


def complete(system: str, user: str, max_tokens: int = 900) -> str:
    providers = _active()
    if not providers:
        return "[offline mode: add a free GEMINI_API_KEY or GROQ_API_KEY for AI answers]\n\n" + user[:600]
    last = None
    for p in providers:  # fall through to the next free tier when one is rate limited
        try:
            if p == "anthropic":
                return _anthropic(system, user, max_tokens)
            return _ollama(system, user, max_tokens) if p == LOCAL else _openai_compat(p, system, user, max_tokens)
        except Exception as e:  # noqa: BLE001
            last = f"{p}: {e}" if p not in str(e) else e
    raise RuntimeError(f"All LLM providers failed: {last}")
