"""Settings, read once from environment variables (backend/.env locally)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# The only models the competition allows (participant guide, section 9.1).
# Anything else is a disqualification, so we refuse to start instead of calling it.
ALLOWED_MODELS = {
    "google": {"gemini-3.5-flash-lite", "gemini-3.1-flash-lite"},
    "anthropic": {"claude-haiku-4-5"},
    "openai": {"gpt-4.1-mini", "gpt-5-mini"},
}

BACKEND_DIR = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    pass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    api_keys: list[str] = field(default_factory=list)
    requests_per_minute: int = 12
    cache_dir: Path = BACKEND_DIR / ".cache"
    mock: bool = False

    def check(self) -> None:
        """Fail fast on anything that would waste a run or break the rules."""
        allowed = ALLOWED_MODELS.get(self.provider)
        if allowed is None:
            raise ConfigError(f"MODEL_PROVIDER '{self.provider}' is not supported. Use one of {sorted(ALLOWED_MODELS)}.")
        if self.model not in allowed:
            raise ConfigError(f"MODEL_NAME '{self.model}' is not on the allowed list for {self.provider}: {sorted(allowed)}.")
        if self.provider != "google":
            raise ConfigError("Only the google provider is implemented. Set MODEL_PROVIDER=google.")
        if not self.mock and not self.api_keys:
            raise ConfigError("No API key. Put API_KEY=... in backend/.env (see .env.example).")


def load() -> Settings:
    keys = [k for k in (_env("API_KEY"), _env("API_KEY_BACKUP")) if k]
    return Settings(
        provider=_env("MODEL_PROVIDER", "google").lower(),
        model=_env("MODEL_NAME", "gemini-3.5-flash-lite"),
        api_keys=keys,
        requests_per_minute=int(_env("REQUESTS_PER_MINUTE", "12")),
        cache_dir=BACKEND_DIR / (_env("CACHE_DIR") or ".cache"),  # relative paths are under backend/
        mock=_env("LLM_MOCK") == "1",
    )
