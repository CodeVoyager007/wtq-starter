"""Web server settings, from environment variables (backend/.env). Model settings live in bill_decoder.config."""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


FRONTEND_ORIGINS = [o.strip() for o in _env("FRONTEND_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

MAX_UPLOAD_BYTES = int(_env("MAX_UPLOAD_MB", "10")) * 1024 * 1024
MAX_QUESTION_CHARS = 500
# The model allows ~15 requests/min on the free tier and a decode uses 2-3, so a few at a time is the real limit.
MAX_CONCURRENT_DECODES = int(_env("MAX_CONCURRENT_DECODES", "3"))
DECODE_WAIT_SECONDS = 20  # how long a request waits for a free slot before getting "busy"
DECODES_PER_IP_PER_MINUTE = int(_env("DECODES_PER_IP_PER_MINUTE", "5"))
MAX_STORED_BILLS = 100  # decoded bills kept in memory for follow-up questions (oldest dropped first)
