"""Level 1: one bill image -> checked Level 1 JSON plus facts for Level 2.

Flow: extract (1 model call) -> normalize -> validate -> repair once if checks fail.
The version with fewer failed checks wins; ties keep the first reading.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from . import normalize, prompts, validate
from .llm import Client, Image
from .schema import FACTS_SCHEMA

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
    level1 = normalize.to_level1(raw, bill_id)
    issues = validate.check(level1)
    if not issues:
        return Extraction(bill_id, level1, normalize.clean_facts(raw, bill_id))

    log.info("%s: %d check(s) failed, asking the model to re-read: %s", bill_id, len(issues), issues)
    repaired_raw = client.generate_json(
        system=prompts.EXTRACT_SYSTEM, prompt=prompts.repair_prompt(provider, raw, issues),
        image=image, schema=FACTS_SCHEMA, tag=f"{bill_id}.repair",
    )
    repaired = normalize.to_level1(repaired_raw, bill_id)
    repaired_issues = validate.check(repaired)
    if len(repaired_issues) < len(issues):
        return Extraction(bill_id, repaired, normalize.clean_facts(repaired_raw, bill_id), repaired_issues, True)
    return Extraction(bill_id, level1, normalize.clean_facts(raw, bill_id), issues)


def failed(bill_id: str, error: str) -> Extraction:
    """All-null result so the CSV cell is never empty; the error is logged."""
    level1 = normalize.to_level1(None, bill_id)
    return Extraction(bill_id, level1, normalize.clean_facts(None, bill_id), error=error)
