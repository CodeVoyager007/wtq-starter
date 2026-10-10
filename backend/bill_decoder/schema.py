"""Data shapes.

LEVEL1_FIELDS is the exact scored schema (participant guide, section 5.1), in order.
FACTS_SCHEMA is what we ask the model to read: Level 1 plus the extra facts Level 2
questions need (history, rates, late payment amounts). Amounts are requested as the
printed strings ("54770CR", "Rs. 3,430") so sign and format handling stays in code.
"""
from __future__ import annotations

PROVIDERS = ("KE", "LESCO", "IESCO")

CHARGE_TYPES = ("energy", "fixed", "fpa", "quarterly_adjustment", "surcharge", "meter_rent", "subsidy", "other")
TAX_TYPES = ("gst", "electricity_duty", "income_tax", "municipal_tax", "other_tax")

LEVEL1_FIELDS = (
    "provider", "tariff", "sanctioned_load_kw",
    "bill_month", "reading_date", "issue_date", "due_date",
    "previous_reading", "current_reading", "units_consumed",
    "charges", "total_charges", "taxes", "total_taxes",
    "current_bill", "arrears", "payable_within_due_date", "payable_after_due_date",
)
NUMBER_FIELDS = (
    "sanctioned_load_kw", "previous_reading", "current_reading", "units_consumed",
    "total_charges", "total_taxes", "current_bill", "arrears",
    "payable_within_due_date", "payable_after_due_date",
)
DATE_FIELDS = ("reading_date", "issue_date", "due_date")
TEXT_FIELDS = ("provider", "tariff", "bill_month", *DATE_FIELDS)


def empty_level1(provider: str | None = None) -> dict:
    bill = {name: None for name in LEVEL1_FIELDS}
    bill["provider"] = provider
    bill["charges"] = []
    bill["taxes"] = []
    return bill


# JSON schema for Gemini structured output. Everything is a nullable string so the
# model copies what it sees; normalize.py turns it into numbers and dates.
_S = {"type": "string", "nullable": True}
_LINE = {
    "type": "object",
    "properties": {"label": {"type": "string"}, "type": {"type": "string"}, "amount": {"type": "string"}},
    "required": ["label", "type", "amount"],
}

FACTS_SCHEMA = {
    "type": "object",
    "properties": {
        "tariff": _S,
        "sanctioned_load_kw": _S,
        "bill_month": _S,
        "reading_date": _S,
        "issue_date": _S,
        "due_date": _S,
        "previous_reading": _S,
        "current_reading": _S,
        "units_consumed": _S,
        "charges": {"type": "array", "items": _LINE},
        "total_charges": _S,
        "taxes": {"type": "array", "items": _LINE},
        "total_taxes": _S,
        "current_bill": _S,
        "arrears": _S,
        "payable_within_due_date": _S,
        "late_payment_amounts": {"type": "array", "items": {"type": "string"}},
        # Extra facts for Level 2 (not scored directly).
        "tariff_category": _S,
        "net_metering": {"type": "boolean", "nullable": True},
        "meter_registers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": _S, "previous": _S, "current": _S, "units": _S},
            },
        },
        "late_payment_surcharge": {"type": "array", "items": {"type": "string"}},
        "usage_history": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"month": {"type": "string"}, "units": _S, "bill": _S, "payment": _S},
                "required": ["month"],
            },
        },
        "rate_lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "units": _S, "rate": _S, "amount": _S},
                "required": ["label"],
            },
        },
        "printed_percentages": {"type": "array", "items": {"type": "string"}},
        "other_printed_amounts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "amount": {"type": "string"}},
                "required": ["label", "amount"],
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["charges", "taxes", "late_payment_amounts"],
}

# Full transcription: everything printed, so Level 2 can answer any question and
# Level 1 numbers can be cross-checked against an independent reading.
TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                            "required": ["label", "value"],
                        },
                    },
                },
                "required": ["name", "items"],
            },
        },
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "columns": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                },
                "required": ["name", "columns", "rows"],
            },
        },
        "messages_in_english": {"type": "array", "items": {"type": "string"}},
        "unreadable_or_covered": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sections", "tables", "messages_in_english"],
}
