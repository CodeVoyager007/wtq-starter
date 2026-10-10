"""Level 2: answer every question for one bill in a single model call.

The model writes the reasoning and the calculation expressions; calc.py computes the
numbers. An answer whose calculation fails is retried on its own with the error shown
to the model; as a last resort it is asked to answer without calculations.
"""
from __future__ import annotations

import logging

from . import calc, prompts
from .llm import Client, Image, LLMError

log = logging.getLogger(__name__)

UNAVAILABLE = "This bill does not give enough readable information to answer this question reliably."


def answer_bill(client: Client, bill_id: str, image: Image | None, facts: dict,
                questions: list[tuple[str, str]]) -> dict[str, str]:
    """Return {question_id: answer text} for every question; never an empty string."""
    answers: dict[str, str] = {}
    failures: dict[str, str] = {}
    try:
        reply = client.generate_json(
            system=prompts.ANSWER_SYSTEM, prompt=prompts.answer_prompt(facts, questions),
            image=image, schema=prompts.ANSWER_SCHEMA, tag=f"{bill_id}.answers",
        )
        for item in reply.get("answers") or []:
            qid = str(item.get("question_id", "")).strip()
            text, error = _render(item)
            if text:
                answers[qid] = text
            elif error:
                failures[qid] = error
    except LLMError as exc:
        log.error("%s: batch answer call failed: %s", bill_id, exc)

    for qid, question in questions:
        if qid not in answers:
            answers[qid] = _answer_one(client, bill_id, image, facts, qid, question, failures.get(qid))
    return answers


def _answer_one(client: Client, bill_id: str, image: Image | None, facts: dict,
                qid: str, question: str, error: str | None) -> str:
    attempts = (("retry", error), ("direct", None))
    for mode, feedback in attempts:
        try:
            reply = client.generate_json(
                system=prompts.ANSWER_SYSTEM,
                prompt=prompts.answer_prompt(facts, [(qid, question)], feedback=feedback, allow_calcs=mode == "retry"),
                image=image, schema=prompts.ANSWER_SCHEMA, tag=f"{bill_id}.{qid}.{mode}",
            )
        except LLMError as exc:
            log.error("%s %s: answer call failed: %s", bill_id, qid, exc)
            continue
        for item in reply.get("answers") or []:
            text, error = _render(item)
            if text:
                return text
            feedback = error
    return UNAVAILABLE


def _render(item: dict) -> tuple[str | None, str | None]:
    """(answer text, None) on success, (None, error message) when a calculation fails."""
    template = str(item.get("answer") or "").strip()
    if not template:
        return None, None
    calcs = {c.get("name"): c.get("expression") for c in item.get("calcs") or [] if c.get("name")}
    try:
        return calc.render(template, calcs), None
    except calc.CalcError as exc:
        log.warning("answer %s: calculation failed (%s)", item.get("question_id"), exc)
        return None, str(exc)
