"""Deterministic clean-up of what the model read. No LLM calls here.

The model copies printed text; this module applies the guide's rules (section 5.2-5.4):
numbers in PKR without labels or commas, CR means negative, dates as YYYY-MM-DD,
types from the allowed lists, blank and zero lines skipped, highest late amount.
"""
from __future__ import annotations

import re
from datetime import datetime

from .schema import CHARGE_TYPES, LEVEL1_FIELDS, TAX_TYPES, empty_level1

_FILE_PREFIX_TO_PROVIDER = {"KESC": "KE", "KE": "KE", "LESCO": "LESCO", "IESCO": "IESCO"}
_BLANK = {"", "-", "--", "n/a", "na", "null", "none", "nil", "not to be paid", "not printed", "unreadable"}


def provider_from_bill_id(bill_id: str) -> str | None:
    prefix = re.split(r"[_\-\s]", bill_id.strip(), maxsplit=1)[0].upper()
    return _FILE_PREFIX_TO_PROVIDER.get(prefix)


# ---------------------------------------------------------------- numbers

def parse_amount(value) -> int | float | None:
    """'Rs. 19,964' -> 19964, '38209CR' -> -38209, '(12.5)' -> -12.5, '39411 / 2' -> 39411."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _tidy(float(value))
    text = str(value).strip()
    if text.lower() in _BLANK:
        return None
    upper = text.upper()
    negative = bool(re.search(r"\bCR\b|CR$", upper)) or (upper.startswith("(") and upper.endswith(")"))
    cleaned = re.sub(r"(?i)rs\.?|pkr|kwh|kw|units?", "", text).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    number = float(match.group(0))
    if negative:
        number = -abs(number)
    return _tidy(number)


def _tidy(number: float) -> int | float:
    number = round(number, 2)
    return int(number) if number.is_integer() else number


# ---------------------------------------------------------------- dates

_DATE_FORMATS = ("%Y-%m-%d", "%Y %m %d", "%d %b %Y", "%d %B %Y", "%d %b %y", "%d %B %y", "%d %m %Y", "%d %m %y")
_MONTH_FORMATS = ("%Y-%m", "%b %Y", "%B %Y", "%b %y", "%B %y", "%m %Y", "%m %y")


def _date_tokens(text: str) -> str:
    text = re.sub(r"(?i)(\d)(st|nd|rd|th)\b", r"\1", text.strip())
    text = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", text)  # "Sep25" -> "Sep 25"
    return re.sub(r"[\s/\-.,]+", " ", text).strip()


def parse_date(value) -> str | None:
    """'21st Apr 2026', '07-Apr-2026', '17 JUL 26', '14/09/26' -> 'YYYY-MM-DD'."""
    if not value or str(value).strip().lower() in _BLANK:
        return None
    raw = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw if _valid(raw, "%Y-%m-%d") else None
    tokens = _date_tokens(raw).title()
    for fmt in _DATE_FORMATS[1:]:
        try:
            return datetime.strptime(tokens, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_month(value) -> str | None:
    """'Apr-26', 'JUL 2026', '2026-04' -> 'YYYY-MM'."""
    if not value or str(value).strip().lower() in _BLANK:
        return None
    raw = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        return raw if _valid(raw, "%Y-%m") else None
    tokens = _date_tokens(raw).title()
    for fmt in _MONTH_FORMATS[1:]:
        try:
            return datetime.strptime(tokens, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return None


def _valid(text: str, fmt: str) -> bool:
    try:
        datetime.strptime(text, fmt)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- line types

_CHARGE_KEYWORDS = (
    ("subsidy", ("subsid", "relief")),
    ("fpa", ("fpa", "fca", "fuel")),
    ("quarterly_adjustment", ("quarterly", "qta")),
    ("surcharge", ("surcharge", "phl")),
    ("meter_rent", ("meter rent", "service rent", "rent")),
    ("fixed", ("fixed",)),
    ("energy", ("variable", "energy", "cost of electricity", "electricity charges", "units", "peak")),
)
_TAX_KEYWORDS = (
    ("gst", ("gst", "sales tax")),
    ("electricity_duty", ("electricity duty", "e.duty", "e. duty", " ed")),
    ("income_tax", ("income tax",)),
    ("municipal_tax", ("municipal", "muct", "kmc", "local")),
)
_TAX_ALIASES = {"ed": "electricity_duty", "sales_tax": "gst", "salestax": "gst"}
_CHARGE_ALIASES = {"fca": "fpa", "qta": "quarterly_adjustment", "uqa": "quarterly_adjustment", "phl": "surcharge"}
_COMBINED_TAX_LABELS = {
    "taxes", "tax", "total taxes", "taxes and duties", "govt taxes", "government taxes", "govt. taxes",
}


def _slug(text) -> str:
    return re.sub(r"[^a-z]+", "_", str(text or "").lower()).strip("_")


def charge_type(model_type, label) -> str:
    slug = _slug(model_type)
    slug = _CHARGE_ALIASES.get(slug, slug)
    if slug in CHARGE_TYPES:
        return slug
    lowered = f" {model_type or ''} {label or ''}".lower()
    for kind, words in _CHARGE_KEYWORDS:
        if any(w in lowered for w in words):
            return kind
    return "other"


def tax_type(model_type, label) -> str:
    slug = _slug(model_type)
    slug = _TAX_ALIASES.get(slug, slug)
    if slug in TAX_TYPES:
        return slug
    lowered = f" {model_type or ''} {label or ''}".lower()
    for kind, words in _TAX_KEYWORDS:
        if any(w in lowered for w in words):
            return kind
    return "other_tax"


def _lines(raw_lines, classify) -> list[dict]:
    """Typed, signed lines. Blank and zero lines are skipped (guide 5.3)."""
    out = []
    for line in raw_lines or []:
        if not isinstance(line, dict):
            continue
        amount = parse_amount(line.get("amount"))
        if amount is None or amount == 0:
            continue
        kind = classify(line.get("type"), line.get("label"))
        if kind == "subsidy":
            amount = -abs(amount)
        out.append({"type": kind, "amount": amount, "label": str(line.get("label") or "")})
    return out


def _drop_subtotal_line(lines: list[dict], total) -> list[dict]:
    """If the model copied the subtotal as a line next to its parts, drop it."""
    if total is None or len(lines) < 3:
        return lines
    for i, line in enumerate(lines):
        rest = lines[:i] + lines[i + 1:]
        if abs(line["amount"] - total) <= 1 and abs(sum(other["amount"] for other in rest) - total) <= 1:
            return rest
    return lines


# ---------------------------------------------------------------- level 1

def to_level1(raw: dict | None, bill_id: str) -> dict:
    """Model output (printed strings) -> the exact scored Level 1 object."""
    provider = provider_from_bill_id(bill_id)
    bill = empty_level1(provider)
    if not raw:
        return bill

    tariff = raw.get("tariff")
    bill["tariff"] = re.sub(r"\s+", "", str(tariff)) if tariff and str(tariff).strip().lower() not in _BLANK else None
    bill["sanctioned_load_kw"] = parse_amount(raw.get("sanctioned_load_kw"))
    bill["bill_month"] = parse_month(raw.get("bill_month"))
    for name in ("reading_date", "issue_date", "due_date"):
        bill[name] = parse_date(raw.get(name))
    for name in ("previous_reading", "current_reading", "units_consumed", "total_charges",
                 "total_taxes", "current_bill", "arrears", "payable_within_due_date"):
        bill[name] = parse_amount(raw.get(name))

    charges = _drop_subtotal_line(_lines(raw.get("charges"), charge_type), bill["total_charges"])
    taxes = _lines(raw.get("taxes"), tax_type)
    if len(taxes) == 1 and taxes[0]["label"].strip().lower().rstrip(":") in _COMBINED_TAX_LABELS:
        # Only a combined figure is printed: guide 5.3 says [] plus total_taxes.
        if bill["total_taxes"] is None:
            bill["total_taxes"] = taxes[0]["amount"]
        taxes = []
    taxes = _drop_subtotal_line(taxes, bill["total_taxes"])
    bill["charges"] = [{"type": c["type"], "amount": c["amount"]} for c in charges]
    bill["taxes"] = [{"type": t["type"], "amount": t["amount"]} for t in taxes]

    late = [a for a in (parse_amount(v) for v in raw.get("late_payment_amounts") or []) if a is not None]
    bill["payable_after_due_date"] = max(late) if late else None

    assert tuple(bill) == LEVEL1_FIELDS
    return bill


# ---------------------------------------------------------------- level 2 facts

def clean_facts(raw: dict | None, bill_id: str) -> dict:
    """Level 1 plus parsed extras, the grounded context for Level 2 answers."""
    raw = raw or {}
    facts = {"bill_id": bill_id, **to_level1(raw, bill_id)}
    facts["tariff_category"] = raw.get("tariff_category")
    facts["net_metering"] = raw.get("net_metering")
    facts["meter_registers"] = [
        {"name": r.get("name"), "previous": parse_amount(r.get("previous")),
         "current": parse_amount(r.get("current")), "units": parse_amount(r.get("units"))}
        for r in raw.get("meter_registers") or [] if isinstance(r, dict)
    ]
    facts["late_payment_amounts"] = [parse_amount(v) for v in raw.get("late_payment_amounts") or []]
    facts["late_payment_surcharge"] = [parse_amount(v) for v in raw.get("late_payment_surcharge") or []]
    facts["usage_history"] = [
        {"month": parse_month(h.get("month")) or h.get("month"), "printed_month": h.get("month"),
         "units": parse_amount(h.get("units")),
         "bill": parse_amount(h.get("bill")), "payment": parse_amount(h.get("payment"))}
        for h in raw.get("usage_history") or [] if isinstance(h, dict)
    ]
    facts["rate_lines"] = [
        {"label": r.get("label"), "units": parse_amount(r.get("units")),
         "rate": parse_amount(r.get("rate")), "amount": parse_amount(r.get("amount"))}
        for r in raw.get("rate_lines") or [] if isinstance(r, dict)
    ]
    facts["charge_lines"] = _lines(raw.get("charges"), charge_type)
    facts["tax_lines"] = _lines(raw.get("taxes"), tax_type)
    facts["printed_percentages"] = raw.get("printed_percentages") or []
    facts["other_printed_amounts"] = [
        {"label": o.get("label"), "amount": parse_amount(o.get("amount"))}
        for o in raw.get("other_printed_amounts") or [] if isinstance(o, dict)
    ]
    facts["notes"] = raw.get("notes") or []
    return facts
