"""One place that talks to the LLM.

Order of attempts: Gemini primary key -> Gemini backup key -> optional fallback provider.
Every AI module calls generate() or generate_json(), so swapping models is a one-file change.
"""
import json
import re
import time

import httpx

from . import config


class LLMError(Exception):
    pass


def _gemini(prompt: str, system: str | None, json_mode: bool, temperature: float, key: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    resp = client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt, config=cfg)
    return resp.text or ""


def _fallback(prompt: str, system: str | None, json_mode: bool, temperature: float) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {"model": config.FALLBACK_MODEL, "messages": messages, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(
        f"{config.FALLBACK_BASE_URL.rstrip('/')}/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {config.FALLBACK_API_KEY}"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def generate(
    prompt: str,
    system: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.2,
    mock: str | None = None,
) -> str:
    """Return the model's text. `mock` is what you get back when LLM_MOCK=1."""
    if config.mock_mode():
        return mock if mock is not None else "[mock] " + prompt[:80].replace("\n", " ")

    if not config.GEMINI_KEYS and not config.has_fallback():
        raise LLMError("No API key found. Add GEMINI_API_KEY to backend/.env and restart the server.")

    errors: list[str] = []
    for key in config.GEMINI_KEYS:
        for attempt in range(2):
            try:
                return _gemini(prompt, system, json_mode, temperature, key)
            except Exception as e:  # rate limit, network, bad key...
                errors.append(f"gemini(...{key[-4:]}): {str(e)[:160]}")
                time.sleep(1.5 * (attempt + 1))

    if config.has_fallback():
        try:
            return _fallback(prompt, system, json_mode, temperature)
        except Exception as e:
            errors.append(f"fallback: {str(e)[:160]}")

    raise LLMError(" | ".join(errors[-3:]))


def parse_json(text: str):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}|\[.*\]", t, flags=re.S)
        if m:
            return json.loads(m.group(0))
        raise


def generate_json(prompt: str, system: str | None = None, temperature: float = 0.1, mock=None):
    """Ask for JSON and parse it. Retries once if the model returns broken JSON."""
    mock_text = json.dumps(mock) if mock is not None and not isinstance(mock, str) else mock
    text = generate(prompt, system=system, json_mode=True, temperature=temperature, mock=mock_text)
    try:
        return parse_json(text)
    except Exception:
        text = generate(
            prompt + "\n\nYour last answer was not valid JSON. Return valid JSON only, no extra text.",
            system=system,
            json_mode=True,
            temperature=0,
            mock=mock_text,
        )
        return parse_json(text)
