"""Level 1: one bill image -> checked Level 1 JSON plus facts for Level 2.

Flow: extract (1 call) + full transcription (1 call, independent second reading)
-> normalize -> arithmetic checks + cross-check against the transcript
-> repair once (with the transcript as evidence) if anything fails.
The version with fewer failed checks wins; ties keep the first reading.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from . import normalize, prompts, validate
from .llm import Client, Image, LLMError
from .schema import FACTS_SCHEMA, TRANSCRIPT_SCHEMA

log = logging.getLogger(__name__)


@dataclass
class Extraction:
    bill_id: str
    level1: dict
    facts: dict
    issues: list[str] = field(default_factory=list)
    repaired: bool = False
    error: str | None = None


def extract_bill(client: Client, bill_id: str, image: Image) -> Extraction:
    provider = normalize.provider_from_bill_id(bill_id)
    raw = client.generate_json(
        system=prompts.EXTRACT_SYSTEM, prompt=prompts.extract_prompt(provider),
        image=image, schema=FACTS_SCHEMA, tag=f"{bill_id}.extract",
    )
    transcript = transcribe(client, bill_id, provider, image)

    def checked(reading: dict) -> tuple[dict, list[str]]:
        level1 = normalize.to_level1(reading, bill_id)
        return level1, validate.check(level1) + validate.cross_check(level1, transcript)

    def result(reading: dict, level1: dict, issues: list[str], repaired: bool = False) -> Extraction:
        facts = normalize.clean_facts(reading, bill_id)
        facts["transcript"] = transcript
        return Extraction(bill_id, level1, facts, issues, repaired)

    level1, issues = checked(raw)
    if not issues:
        return result(raw, level1, issues)

    log.info("%s: %d check(s) failed, asking the model to re-read: %s", bill_id, len(issues), issues)
    repaired_raw = client.generate_json(
        system=prompts.EXTRACT_SYSTEM, prompt=prompts.repair_prompt(provider, raw, issues, transcript),
        image=image, schema=FACTS_SCHEMA, tag=f"{bill_id}.repair",
    )
    repaired, repaired_issues = checked(repaired_raw)
    if len(repaired_issues) < len(issues):
        return result(repaired_raw, repaired, repaired_issues, repaired=True)
    return result(raw, level1, issues)


def transcribe(client: Client, bill_id: str, provider: str | None, image: Image) -> dict | None:
    """Full independent reading of the bill. Optional: extraction still works without it."""
    try:
        return client.generate_json(
            system=prompts.TRANSCRIBE_SYSTEM, prompt=prompts.transcribe_prompt(provider),
            image=image, schema=TRANSCRIPT_SCHEMA, tag=f"{bill_id}.transcript",
        )
    except LLMError as exc:
        log.warning("%s: transcription failed, continuing without it: %s", bill_id, exc)
        return None


def failed(bill_id: str, error: str) -> Extraction:
    """All-null result so the CSV cell is never empty; the error is logged."""
    level1 = normalize.to_level1(None, bill_id)
    return Extraction(bill_id, level1, normalize.clean_facts(None, bill_id), error=error)
