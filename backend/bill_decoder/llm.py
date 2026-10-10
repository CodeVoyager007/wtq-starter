"""The only module that talks to the model.

- Allow-list guard (config.Settings.check) before the first call.
- Deterministic settings: temperature 0, fixed seed, top_k 1.
- Disk cache keyed by everything that affects the answer, so a rerun gives the same
  output and spends no quota.
- Client-side rate limit plus retry with backoff; rotates to the backup key on 429.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import Settings

log = logging.getLogger(__name__)

SEED = 7
MAX_ATTEMPTS = 6


class LLMError(Exception):
    pass


@dataclass
class Image:
    data: bytes
    mime_type: str


class _RateLimiter:
    def __init__(self, per_minute: int):
        self.interval = 60.0 / max(per_minute, 1)
        self.next_slot = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = self.next_slot - now
            self.next_slot = max(now, self.next_slot) + self.interval
        if delay > 0:
            time.sleep(delay)


class Client:
    def __init__(self, settings: Settings, mock: Callable[[str], str] | None = None):
        settings.check()
        self.settings = settings
        self.mock = mock
        self.limiter = _RateLimiter(settings.requests_per_minute)
        self.cache_dir = Path(settings.cache_dir) / settings.model
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._key_index = 0
        self._sdk = None

    # ------------------------------------------------------------ public

    def generate_json(self, *, system: str, prompt: str, image: Image | None, schema: dict, tag: str) -> dict:
        """One structured call. `tag` names the cache file (e.g. 'KESC_0008.extract')."""
        key = self._cache_key(system, prompt, image, schema)
        path = self.cache_dir / f"{tag}.{key[:16]}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["parsed"]

        text = self.mock(prompt) if self.settings.mock and self.mock else self._call(system, prompt, image, schema)
        parsed = _parse_json(text)
        path.write_text(json.dumps({"model": self.settings.model, "raw": text, "parsed": parsed},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        return parsed

    # ------------------------------------------------------------ internals

    def _cache_key(self, system: str, prompt: str, image: Image | None, schema: dict) -> str:
        h = hashlib.sha256()
        for part in (self.settings.model, system, prompt, json.dumps(schema, sort_keys=True), str(SEED)):
            h.update(part.encode("utf-8"))
            h.update(b"\0")
        if image:
            h.update(hashlib.sha256(image.data).digest())
        return h.hexdigest()

    def _call(self, system: str, prompt: str, image: Image | None, schema: dict) -> str:
        if self.settings.mock:
            raise LLMError("LLM_MOCK=1 but no mock response was supplied for this call.")
        from google.genai import types

        contents = [prompt]
        if image:
            contents = [types.Part.from_bytes(data=image.data, mime_type=image.mime_type), prompt]
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            top_k=1,
            seed=SEED,
            response_mime_type="application/json",
            response_schema=schema,
        )

        last_error = None
        for attempt in range(MAX_ATTEMPTS):
            self.limiter.wait()
            try:
                response = self._client().models.generate_content(
                    model=self.settings.model, contents=contents, config=config
                )
                if response.text:
                    return response.text
                last_error = LLMError("empty response")
            except Exception as exc:  # SDK raises several error types; classify by message
                last_error = exc
                message = str(exc)
                if any(code in message for code in ("400", "INVALID_ARGUMENT", "401", "403", "PERMISSION_DENIED", "404", "NOT_FOUND")):
                    raise LLMError(f"request rejected: {message[:300]}") from exc
                if "429" in message or "RESOURCE_EXHAUSTED" in message:
                    self._rotate_key()
            backoff = min(2 ** (attempt + 1), 40)
            log.warning("model call failed (attempt %d/%d): %s; retrying in %ss",
                        attempt + 1, MAX_ATTEMPTS, str(last_error)[:160], backoff)
            time.sleep(backoff)
        raise LLMError(f"model call failed after {MAX_ATTEMPTS} attempts: {str(last_error)[:300]}")

    def _client(self):
        if self._sdk is None:
            from google import genai

            self._sdk = genai.Client(api_key=self.settings.api_keys[self._key_index])
        return self._sdk

    def _rotate_key(self) -> None:
        if len(self.settings.api_keys) > 1:
            self._key_index = (self._key_index + 1) % len(self.settings.api_keys)
            self._sdk = None
            log.warning("rate limited, switching to API key #%d", self._key_index + 1)


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned[cleaned.find("{"):]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMError(f"model did not return JSON: {text[:200]}")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise LLMError("model returned JSON that is not an object")
    return value
