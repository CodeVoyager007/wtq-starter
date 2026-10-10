"""Level 2: answer every question for one bill in a single model call.

The model writes the reasoning and the calculation expressions; calc.py computes the
numbers. If one answer's calculations fail, that answer is retried once on its own.
"""
from __future__ import annotations

import logging

from . import calc, prompts
from .llm import Client, Image, LLMError

log = logging.getLogger(__name__)

UNAVAILABLE = "I could not read enough of this bill to answer this question reliably."


def answer_bill(client: Client, bill_id: str, image: Image | None, facts: dict,
                questions: list[tuple[str, str]]) -> dict[str, str]:
    """Return {question_id: answer text} for every question; never an empty string."""
    answers: dict[str, str] = {}
    try:
        reply = client.generate_json(
            system=prompts.ANSWER_SYSTEM, prompt=prompts.answer_prompt(facts, questions),
            image=image, schema=prompts.ANSWER_SCHEMA, tag=f"{bill_id}.answers",
        )
        for item in reply.get("answers") or []:
            text = _render(item)
            if text:
                answers[str(item.get("question_id", "")).strip()] = text
    except LLMError as exc:
        log.error("%s: batch answer call failed: %s", bill_id, exc)

    for qid, question in questions:
        if qid not in answers:
            answers[qid] = _answer_one(client, bill_id, image, facts, qid, question)
    return answers


def _answer_one(client: Client, bill_id: str, image: Image | None, facts: dict, qid: str, question: str) -> str:
    try:
        reply = client.generate_json(
            system=prompts.ANSWER_SYSTEM, prompt=prompts.answer_prompt(facts, [(qid, question)]),
            image=image, schema=prompts.ANSWER_SCHEMA, tag=f"{bill_id}.{qid}",
        )
        for item in reply.get("answers") or []:
            text = _render(item)
            if text:
                return text
    except LLMError as exc:
        log.error("%s %s: answer call failed: %s", bill_id, qid, exc)
    return UNAVAILABLE


def _render(item: dict) -> str | None:
    template = str(item.get("answer") or "").strip()
    if not template:
        return None
    calcs = {c.get("name"): c.get("expression") for c in item.get("calcs") or [] if c.get("name")}
    try:
        return calc.render(template, calcs)
    except calc.CalcError as exc:
        log.warning("answer %s: calculation failed (%s)", item.get("question_id"), exc)
        return None
