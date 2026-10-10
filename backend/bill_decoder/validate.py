"""Consistency checks on a Level 1 bill. Each failure is a plain sentence the
repair prompt can show the model. Tolerance matches the scorer (±1)."""
from __future__ import annotations

import re

TOLERANCE = 1.0
_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_MIN_TRANSCRIPT_NUMBERS = 20  # below this the transcription itself probably failed


def _close(a, b) -> bool:
    return abs(a - b) <= TOLERANCE


def check(bill: dict) -> list[str]:
    issues: list[str] = []
    prev, cur, units = bill.get("previous_reading"), bill.get("current_reading"), bill.get("units_consumed")
    if None not in (prev, cur, units) and cur >= prev and not _close(cur - prev, units):
        issues.append(
            f"current_reading ({cur}) - previous_reading ({prev}) = {round(cur - prev, 2)}, "
            f"but units_consumed is {units}. Re-read the meter readings and units."
        )

    charges, total_charges = bill.get("charges") or [], bill.get("total_charges")
    if charges and total_charges is not None:
        total = sum(c["amount"] for c in charges)
        without_fpa = sum(c["amount"] for c in charges if c["type"] != "fpa")
        if not (_close(total, total_charges) or _close(without_fpa, total_charges)):
            issues.append(
                f"charges add up to {round(total, 2)} but total_charges is {total_charges}. "
                "Check for a missed, duplicated or misread charge line."
            )

    taxes, total_taxes = bill.get("taxes") or [], bill.get("total_taxes")
    if taxes and total_taxes is not None and not _close(sum(t["amount"] for t in taxes), total_taxes):
        issues.append(
            f"taxes add up to {round(sum(t['amount'] for t in taxes), 2)} but total_taxes is {total_taxes}. "
            "Check for a missed or misread tax line."
        )

    current = bill.get("current_bill")
    if None not in (total_charges, total_taxes, current) and not _close(total_charges + total_taxes, current):
        issues.append(
            f"total_charges ({total_charges}) + total_taxes ({total_taxes}) = "
            f"{round(total_charges + total_taxes, 2)}, but current_bill is {current}. Re-check these three values."
        )

    within, after = bill.get("payable_within_due_date"), bill.get("payable_after_due_date")
    if None not in (within, after) and after < within - TOLERANCE:
        issues.append(
            f"payable_after_due_date ({after}) is lower than payable_within_due_date ({within}). "
            "Re-check both amounts."
        )

    arrears = bill.get("arrears")
    if bill.get("provider") == "LESCO" and None not in (current, arrears, within) \
            and not _close(current + arrears, within):
        issues.append(
            f"current_bill ({current}) + arrears ({arrears}) = {round(current + arrears, 2)}, "
            f"but payable_within_due_date is {within}. Values in the charges breakdown may be misaligned."
        )

    issue, due = bill.get("issue_date"), bill.get("due_date")
    if issue and due and issue > due:
        issues.append(f"issue_date ({issue}) is after due_date ({due}). Re-check both dates.")

    month = bill.get("bill_month")
    if month and due and due[:7] < month:
        issues.append(f"due_date ({due}) is before bill_month ({month}). Re-check the dates.")
    return issues


def _strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, str):
        yield value


def transcript_numbers(transcript: dict | None) -> set[float]:
    """Every number printed anywhere in the transcript, as absolute values (CR/minus ignored)."""
    numbers = set()
    for text in _strings(transcript or {}):
        for token in _NUMBER.findall(text):
            try:
                numbers.add(abs(round(float(token.replace(",", "")), 2)))
            except ValueError:
                continue
    return numbers


def cross_check(bill: dict, transcript: dict | None) -> list[str]:
    """Flag extracted amounts that the independent full transcription never saw."""
    printed = transcript_numbers(transcript)
    if len(printed) < _MIN_TRANSCRIPT_NUMBERS:
        return []
    values = [(name, bill.get(name)) for name in (
        "sanctioned_load_kw", "previous_reading", "current_reading", "units_consumed", "total_charges",
        "total_taxes", "current_bill", "arrears", "payable_within_due_date", "payable_after_due_date")]
    values += [(f"charges[{i}] ({c['type']})", c["amount"]) for i, c in enumerate(bill.get("charges") or [])]
    values += [(f"taxes[{i}] ({t['type']})", t["amount"]) for i, t in enumerate(bill.get("taxes") or [])]
    missing = [
        f"{name} = {value}" for name, value in values
        if value not in (None, 0) and not any(abs(abs(value) - p) <= 0.011 for p in printed)
    ]
    if not missing:
        return []
    return [f"These extracted values do not appear anywhere in an independent transcription of the bill, "
            f"so they may be misread: {', '.join(missing)}."]
