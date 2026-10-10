"""All settings come from environment variables (backend/.env locally, dashboard on Render)."""
import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# Gemini keys are tried in order: primary first, then the backup key.
GEMINI_KEYS = [k for k in (env("GEMINI_API_KEY"), env("GEMINI_API_KEY_BACKUP")) if k]
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")

# Optional last-resort provider (any OpenAI-compatible API: Groq, OpenRouter, ...).
FALLBACK_BASE_URL = env("FALLBACK_BASE_URL")  # e.g. https://api.groq.com/openai/v1
FALLBACK_API_KEY = env("FALLBACK_API_KEY")
FALLBACK_MODEL = env("FALLBACK_MODEL")  # e.g. llama-3.3-70b-versatile

# Comma separated list of allowed frontend origins (Vercel previews are allowed by regex in main.py).
FRONTEND_ORIGINS = [
    o.strip() for o in env("FRONTEND_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]


def mock_mode() -> bool:
    """LLM_MOCK=1 makes every LLM call return a canned answer. For tests and UI work with no key."""
    return env("LLM_MOCK") == "1"


def has_fallback() -> bool:
    return bool(FALLBACK_BASE_URL and FALLBACK_API_KEY and FALLBACK_MODEL)
