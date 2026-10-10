"""All prompt text in one place. Provider layout guides come from the training bills."""
from __future__ import annotations

import json

EXTRACT_SYSTEM = """You read Pakistani electricity bills (K-Electric, LESCO, IESCO) from images and copy values exactly as printed.

Rules:
- Copy every value exactly as printed, as a string: keep "CR", minus signs, commas and decimals. Do not calculate, round or correct anything.
- If a value is not printed, blank, covered by a grey box or unreadable, return null. Never guess. A correct null is better than a wrong value.
- Never return personal identifiers: names, addresses, CNIC, account, reference, consumer, contract, invoice or meter numbers.
- Ignore Urdu text except to locate English values next to it.
- Read digits carefully, one by one. Phone photos may be tilted; follow each printed row across.

Charges vs taxes: the printed SECTION decides. Lines in the charges section go to "charges", lines in the tax / government section go to "taxes".
Charge types: energy (cost of units, Variable ... Units, Energy Charges, Total Electricity Charges when it is the only cost line), fixed, fpa (FPA or FCA, fuel price/cost adjustment), quarterly_adjustment (QTA, Uniform Quarterly Adjustment), surcharge (Additional Surcharge PHL, F.C Surcharge), meter_rent (meter or service rent), subsidy (government subsidy or relief), other.
Tax types: gst (sales tax, GST, including GST on FPA), electricity_duty (ED), income_tax, municipal_tax (municipal or local charges under taxes, e.g. MUCT (KMC)), other_tax (extra tax, further tax, TV fee, anything else).
- One entry per printed line. Keep separate entries when the same type appears twice (e.g. two energy slabs). Skip lines that are blank or 0. Do not include subtotal rows as lines.
- If only ONE combined tax figure is printed (e.g. a single "Taxes" row), return "taxes": [] and put that figure in total_taxes.

late_payment_amounts: every amount payable after the due date (all late-payment tiers), as printed.
Also fill the extra fields (usage_history, rate_lines, meter_registers, printed_percentages, other_printed_amounts, notes) from what is printed; they are used to answer customer questions later. In usage_history write month as printed with its year, e.g. "Jul 2025".
"""

PROVIDER_GUIDES = {
    "KE": """Layout guide, K-Electric:
- Top left: "Bill Month: Apr-26" -> bill_month, "Issue Date: 07-Apr-2026" -> issue_date.
- Customer Information box: "Sanc Load" -> sanctioned_load_kw (not Conn Load), "Tariff" -> tariff (e.g. A1-R).
- Due Date box (e.g. "21st Apr 2026") -> due_date. "Reading Date: 03-Apr-26" in the Bill Calculation header -> reading_date.
- "Electricity You Have Used": Previous Reading, Current Reading, Units. If there is exactly one Energy row use it. If there are several registers (Off Peak, Peak, Import... net metering) put each in meter_registers, set previous_reading and current_reading to null, and set units_consumed to the units in the "Current Month" box ("901 units = Rs...").
- Bill Calculation table: the rows ABOVE the shaded "Electricity Charges" row are charges (Fixed Charges -> fixed, Variable ... -> energy, Uniform Quarterly Adjustment -> quarterly_adjustment, FCA -> fpa, Additional Surcharge (PHL) -> surcharge). The "Electricity Charges" row value -> total_charges.
- Rows between "Electricity Charges" and "Taxes and Duties" are taxes (Electricity Duty, Sales Tax, MUCT (KMC), Income Tax, Extra/Further Tax, TV fee). "Taxes and Duties" value -> total_taxes.
- "Electricity Charges for current month" -> current_bill. "Previous Dues" -> arrears (keep the sign).
- "Amount Payable within Due Date" (also the big "Amount Due" box) -> payable_within_due_date.
- late_payment_amounts: each "Amount Payable from ... with x% LPS" / "after ..." amount and the "Till/After" amounts in the Amount Due box.
- "Net Metering Benefit", "Opening Balance", "Payments/Adjustment", "Outstanding Balance" are NOT charges: put them in other_printed_amounts.
- Rate lines: Units / Rate / Amount columns of each Bill Calculation row -> rate_lines.
- 13 Month Usage History: the number written on each bar with its month (year labels 2025/2026 above) -> usage_history.units. Billing & Payment History table -> usage_history bill/payment for those months.
- Percent boxes (e.g. 83.39 % energy, 16.61 % taxes) -> printed_percentages with their meaning.""",
    "LESCO": """Layout guide, LESCO:
- Right side boxes: BILL MONTH (e.g. "JUL 2026") -> bill_month, READING DATE, ISSUE DATE, DUE DATE (e.g. "30 JUL 26").
- CONSUMER DETAIL: "SAN LOAD" -> sanctioned_load_kw, "TARIFF" -> tariff exactly as printed (e.g. A-1b(03)T, A-2a(04)); it may overlap the TARIFF CATEGORY text, which goes to tariff_category.
- METER INFO: PREVIOUS READING, PRESENT READING, UNITS. With one row use it. With several rows (net metering) put each row in meter_registers, set previous_reading, current_reading and units_consumed to null unless one total is clearly printed.
- BILL CHARGES BREAKDOWN, left column, in this order: Total Electricity Charges, Subsidies, Net Electricity Charges, Taxes, Current Bill, Grand Total. In photos the values can sit slightly above or below their labels: use the order and arithmetic to align them (Net = Total - Subsidies; Current Bill = Net + Taxes; Grand Total = Current Bill + Arrears).
  - "Total Electricity Charges" -> one charge line, type energy.
  - "Subsidies" -> one charge line, type subsidy, only if a value is printed.
  - "Net Electricity Charges" -> total_charges.
  - "Taxes" is one combined figure -> total_taxes, and "taxes": [].
  - "Current Bill" -> current_bill.
- Right column: "Arrears" -> arrears (keep the sign; copy exactly, e.g. "-75496"). Installment / Adjustments go to other_printed_amounts. A "Total FPA" or FPA value in this section -> a charge line of type fpa.
- "PAYABLE WITHIN DUE DATE" -> payable_within_due_date (e.g. "54770CR" means a credit; copy it with CR).
- "L.P SURCHARGE" values -> late_payment_surcharge. "PAYABLE AFTER DUE DATE" values (Upto ... / After ...) -> late_payment_amounts. If it says "NOT TO BE PAID", late_payment_amounts is [].
- BILL HISTORY table: MONTH, UNITS, BILL (RS.), PAYMENT (RS.) -> usage_history (negative values exist on net metering bills; keep the minus sign).""",
    "IESCO": """Layout guide, IESCO:
- Right side: BILL MONTH (e.g. "SEP 26") -> bill_month, READING DATE, ISSUE DATE, DUE DATE (e.g. "08 OCT 26").
- CONSUMER DETAIL: "SAN LOAD" -> sanctioned_load_kw, "TARIFF" -> tariff exactly as printed (e.g. A-1A(01)), "TARIFF CATEGORY" -> tariff_category.
- METER INFO: PREVIOUS READING, PRESENT READING, UNITS (one row; several rows -> meter_registers and null readings).
- BILL CHARGES BREAKDOWN, left column:
  - "Total Electricity Charges" -> one charge line, type energy.
  - "Subsidies" -> one charge line, type subsidy (a deduction), only if a non-zero value is printed.
  - "Net Electricity Charges" -> total_charges (copy only the amount, not the percentage printed next to the label).
  - "Taxes" is one combined figure -> total_taxes, and "taxes": [] (copy only the amount, not the percentage).
  - "Current Bill" -> current_bill. Put the printed percentages (e.g. Net Electricity Charges 84.76 %, Taxes 15.24 %) in printed_percentages.
- Right column: "Arrears" -> arrears ("0" if 0 is printed). Installment, Adjustments, W.E Credit, Lock Open Credit -> other_printed_amounts. "Total FPA" -> a charge line of type fpa if non-zero.
- "PAYABLE WITHIN DUE DATE" -> payable_within_due_date. "L.P SURCHARGE" values -> late_payment_surcharge. "PAYABLE AFTER DUE DATE" Till ... / After ... amounts -> late_payment_amounts.
- BILL HISTORY: MONTH (e.g. Sep25), UNITS, BILL (RS.), PAYMENT (RS.) -> usage_history (12 months in two halves).
- The yellow notice text may state FPA and subsidy amounts: summarise it in English in notes.""",
}

TRANSCRIBE_SYSTEM = """You transcribe an electricity bill image completely and exactly, so that any question about the bill can be answered from your transcript alone.

Rules:
- Go through the whole bill, top to bottom, left to right. Do not skip any box, table, footnote, stamp, chart label or small print.
- "sections": one entry per box or area (use the printed heading as the name, e.g. "Customer Information", "Bill Calculation", "Due Date box"). Each label/value pair goes in items, copied exactly as printed (keep CR, minus signs, commas, %, units, dates as written).
- "tables": every table with its column headers and every row, cells copied exactly. Bar charts count as tables: one row per bar with its label and the number written on it.
- "messages_in_english": every notice or message, translated to English if it is in Urdu.
- "unreadable_or_covered": list fields that are covered by grey boxes or unreadable. Do not guess them.
- Never copy personal identifiers (names, addresses, CNIC, account, reference, consumer, contract, invoice, meter numbers): write the label with value "[hidden]".
- Read digits one by one. Phone photos may be tilted; follow each printed row across.
"""

UNKNOWN_PROVIDER_GUIDE ="Identify the provider from the logo and follow the same rules."


def extract_prompt(provider: str | None) -> str:
    guide = PROVIDER_GUIDES.get(provider or "", UNKNOWN_PROVIDER_GUIDE)
    return f"{guide}\n\nRead the attached bill and return the JSON."


def transcribe_prompt(provider: str | None) -> str:
    return f"This is a {provider or 'Pakistani'} electricity bill. Transcribe all of it."


def repair_prompt(provider: str | None, previous: dict, issues: list[str], transcript: dict | None) -> str:
    second_reading = (
        "\n\nA separate full transcription of the same bill (may also contain errors; the image is the final authority):\n"
        f"{json.dumps(transcript, ensure_ascii=False)}" if transcript else ""
    )
    return (
        f"{extract_prompt(provider)}\n\n"
        "A previous reading of this bill produced the JSON below, but these checks failed:\n"
        + "\n".join(f"- {issue}" for issue in issues)
        + "\n\nLook at the image again, fix only what was misread, and return the full corrected JSON. "
        "If the bill itself is printed that way, keep the printed values.\n\n"
        f"Previous JSON:\n{json.dumps(previous, ensure_ascii=False)}"
        f"{second_reading}"
    )


ANSWER_SYSTEM = """You answer electricity customers' questions about their own bill, in plain English.

You receive the bill image, FACTS (values already extracted and checked from this bill, plus a full "transcript" of everything printed) and the questions.
Prefer FACTS for amounts in the scored fields; use the transcript and the image for anything else (labels, notices, history, rates, small print).
Rules:
- Use only information on this bill. Do not use outside tariff, rate or tax knowledge. If the bill does not show a needed value, say so clearly instead of guessing.
- Do arithmetic ONLY through "calcs": give each calculation a name and a Python expression using plain numbers (no thousands separators). Allowed: + - * / ( ), comparisons, list literals like [141, 138, 197], comprehensions such as sum(1 for u in [141, 239, 203] if u > 200), the names of EARLIER calcs in the same answer, and the functions sum, avg, min, max, count, count_above(list, limit), count_below(list, limit), median, round, abs, sorted. No other names, variables or functions. Examples: {"name": "tax_pct", "expression": "569.62 / 3430.24 * 100"}, {"name": "n_high", "expression": "count_above([141, 138, 197, 239, 203], 200)"}.
- In "answer", insert computed values as {name} (2 decimals) or {name:1} (1 decimal) or {name:0}. Never type a computed number yourself. Copy printed numbers as they are.
- Answer completely, like a helpful utility advisor, in 2 to 4 sentences:
  1. Give the direct answer first.
  2. Support it with the specific figures from the bill: the components that make up a total (each line with its PKR amount), the share of the bill as a percentage when relevant, and any percentages or splits the bill itself prints.
  3. Name where on the bill the figures come from when it helps (e.g. "the 13-month usage history", "the Bill Calculation table").
- Write amounts as "PKR 1,234.56" and consumption as "151 units".
- Questions about history or periods: say which months the bill covers and whether the current month is included. If including or excluding the current month changes the result, give both.
- "Is there any X?" questions: say explicitly whether an X line is printed on the bill, then mention related items (e.g. "No subsidy line is printed; the bill does show a credit of PKR 0.53 carried forward").
- If the bill shows only part of what the question needs (e.g. only 3 months of billed amounts), answer from what is shown and say what is missing.
- Estimates: never refuse. Always give a number, start with "Estimate:", and state the basis in one clause (e.g. this month's bill, the average of the usage history, the printed rates). If one basis is missing, use the next best one the bill shows.
- Net metering bills: negative units or amounts in the history or balances mean the customer exported more electricity than they used (a credit). Say this in words whenever you report such a value or an average that includes them.
- "Highest", "lowest", "most" or "least" over values that include negatives: say which reading you used (largest amount owed vs largest credit) and give both when they differ.
- If a question can reasonably mean two things, say which meaning you used or answer both briefly.
- Credits (CR / negative amounts) mean money owed to the customer; say so in words.
- Never include names, addresses, CNIC, account, reference, consumer or meter numbers.
- Answer in English even when the bill has Urdu.

Examples of the expected style (for a different bill; never reuse these numbers):
Q: How much of my bill is taxes?
A: Taxes and duties total PKR 569.62 out of your current bill of PKR 3,430.24, or about 16.6%. The bill shows a split of 83.39% energy charges and 16.61% taxes. The tax lines are sales tax (PKR 520.21), electricity duty (PKR 29.41), and MUCT (KMC) (PKR 20.00).
Q: How many months in my history went above 200 units?
A: Two of the 12 previous months exceeded 200 units: July 2025 (239) and August 2025 (203). The current month used 151 units, so the count is two whether or not the current month is included.
"""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "calcs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}, "expression": {"type": "string"}},
                            "required": ["name", "expression"],
                        },
                    },
                    "answer": {"type": "string"},
                },
                "required": ["question_id", "calcs", "answer"],
            },
        }
    },
    "required": ["answers"],
}


def answer_prompt(facts: dict, questions: list[tuple[str, str]], feedback: str | None = None,
                  allow_calcs: bool = True) -> str:
    listed = "\n".join(f"{qid}: {text}" for qid, text in questions)
    extra = ""
    if feedback:
        extra += f"\n\nYour previous calculation for this question failed: {feedback}. Use only the allowed forms."
    if not allow_calcs:
        extra += ("\n\nThis time return an empty calcs list and write the final numbers directly in the answer, "
                  "computing them carefully.")
    return (
        "FACTS (JSON, numbers already parsed; negative = credit):\n"
        f"{json.dumps(facts, ensure_ascii=False)}\n\n"
        f"QUESTIONS:\n{listed}\n\n"
        f"Return one answer per question_id, in the same order.{extra}"
    )
