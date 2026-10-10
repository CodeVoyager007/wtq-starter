"""Consistency checks on a Level 1 bill. Each failure is a plain sentence the
repair prompt can show the model. Tolerance matches the scorer (±1)."""
from __future__ import annotations

TOLERANCE = 1.0


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
