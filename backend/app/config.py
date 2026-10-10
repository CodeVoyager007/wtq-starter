"""All settings come from environment variables (backend/.env locally, dashboard on Render)."""
import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# Same settings as the bill_decoder pipeline (MODEL_NAME, API_KEY, API_KEY_BACKUP).
# Only competition-allowed models: anything else is refused before any call.
from bill_decoder.config import ALLOWED_MODELS  # noqa: E402

GEMINI_KEYS = [k for k in (env("API_KEY"), env("API_KEY_BACKUP")) if k]
GEMINI_MODEL = env("MODEL_NAME", "gemini-3.5-flash-lite")
if GEMINI_MODEL not in ALLOWED_MODELS["google"]:
    raise RuntimeError(f"MODEL_NAME '{GEMINI_MODEL}' is not an allowed model: {sorted(ALLOWED_MODELS['google'])}")

# Comma separated list of allowed frontend origins (Vercel previews are allowed by regex in main.py).
FRONTEND_ORIGINS = [
    o.strip() for o in env("FRONTEND_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]


def mock_mode() -> bool:
    """LLM_MOCK=1 makes every LLM call return a canned answer. For tests and UI work with no key."""
    return env("LLM_MOCK") == "1"
