import json
import zipfile
from pathlib import Path

import pytest

from bill_decoder import calc, csv_io, evaluate, normalize, package, pipeline, validate
from bill_decoder.config import ConfigError, Settings
from bill_decoder.llm import Client
from bill_decoder.schema import LEVEL1_FIELDS

DATA = Path(__file__).resolve().parent.parent / "data" / "train"
TRUTH_0008 = json.loads((DATA / "truth" / "KESC_0008.json").read_text())

# What the model is asked to return for KESC_0008: printed strings, not clean numbers.
RAW_0008 = {
    "tariff": "A1-R", "sanctioned_load_kw": "3", "bill_month": "Apr-26", "reading_date": "03-Apr-26",
    "issue_date": "07-Apr-2026", "due_date": "21st Apr 2026", "previous_reading": "8819",
    "current_reading": "8970", "units_consumed": "151",
    "charges": [
        {"label": "Fixed Charges", "type": "fixed", "amount": "900.00"},
        {"label": "Variable Upto 100 Units (Protected)", "type": "energy", "amount": "1,054.00"},
        {"label": "Variable Upto 200 Units (Protected)", "type": "energy", "amount": "663.51"},
        {"label": "Uniform Quarterly Adjustment", "type": "quarterly_adjustment", "amount": "52.91"},
        {"label": "FCA :Feb-26", "type": "FCA", "amount": "125.27"},
        {"label": "Additional Surcharge (PHL)", "type": "surcharge", "amount": "64.93"},
    ],
    "total_charges": "2,860.62",
    "taxes": [
        {"label": "Electricity Duty", "type": "ED", "amount": "29.41"},
        {"label": "Sales Tax u/s 3(1)*", "type": "gst", "amount": "520.21"},
        {"label": "MUCT (KMC)", "type": "municipal_tax", "amount": "20.00"},
    ],
    "total_taxes": "569.62", "current_bill": "3,430.24", "arrears": "Rs. -0.53",
    "payable_within_due_date": "Rs. 3,430", "late_payment_amounts": ["3,574", "3,716"],
    "usage_history": [{"month": "Jul 2025", "units": "239"}, {"month": "Aug 2025", "units": "203"}],
}


def settings(tmp_path, **kw):
    return Settings(provider="google", model="gemini-3.5-flash-lite", api_keys=[],
                    requests_per_minute=6000, cache_dir=tmp_path / "cache", mock=True, **kw)


# ------------------------------------------------------------------ normalize

@pytest.mark.parametrize("text,expected", [
    ("Rs. 19,964", 19964), ("38209CR", -38209), ("54770CR", -54770), ("-0.53", -0.53),
    ("(12.50)", -12.5), ("39411 / 2", 39411), ("0", 0), ("NOT TO BE PAID", None), ("", None),
    (None, None), ("1,054.00", 1054), (3, 3), ("Rs.286.06", 286.06),
])
def test_parse_amount(text, expected):
    assert normalize.parse_amount(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("22nd Sep 2026", "2026-09-22"), ("21st Apr 2026", "2026-04-21"), ("07-Apr-2026", "2026-04-07"),
    ("03-Apr-26", "2026-04-03"), ("17 JUL 26", "2026-07-17"), ("14/09/26", "2026-09-14"),
    ("2026-04-21", "2026-04-21"), ("31 Feb 2026", None), ("", None),
])
def test_parse_date(text, expected):
    assert normalize.parse_date(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("MAR 2026", "2026-03"), ("Apr-26", "2026-04"), ("JUL 2026", "2026-07"), ("SEP 26", "2026-09"),
    ("2026-04", "2026-04"),
])
def test_parse_month(text, expected):
    assert normalize.parse_month(text) == expected


def test_provider_comes_from_file_name():
    assert normalize.provider_from_bill_id("KESC_0002") == "KE"
    assert normalize.provider_from_bill_id("LESCO_0008") == "LESCO"
    assert normalize.provider_from_bill_id("IESCO_0004") == "IESCO"


def test_kesc_0008_matches_the_official_answer():
    assert normalize.to_level1(RAW_0008, "KESC_0008") == TRUTH_0008


def test_level1_always_has_every_field_in_order():
    bill = normalize.to_level1(None, "LESCO_0001")
    assert tuple(bill) == LEVEL1_FIELDS
    assert bill["provider"] == "LESCO" and bill["charges"] == [] and bill["taxes"] == []


def test_combined_tax_goes_to_total_and_subsidy_is_negative():
    raw = {"charges": [{"label": "Total Electricity Charges", "type": "energy", "amount": "6102"},
                       {"label": "Subsidies", "type": "subsidy", "amount": "3332"},
                       {"label": "Installment", "type": "other", "amount": "0"}],
           "taxes": [{"label": "Taxes", "type": "other_tax", "amount": "498"}],
           "total_taxes": None, "late_payment_amounts": ["3,674", "3,812"]}
    bill = normalize.to_level1(raw, "IESCO_0004")
    assert bill["charges"] == [{"type": "energy", "amount": 6102}, {"type": "subsidy", "amount": -3332}]
    assert bill["taxes"] == [] and bill["total_taxes"] == 498
    assert bill["payable_after_due_date"] == 3812


def test_subtotal_copied_as_a_line_is_dropped():
    raw = {"total_charges": "300", "charges": [
        {"label": "Fixed", "type": "fixed", "amount": "100"}, {"label": "Variable", "type": "energy", "amount": "200"},
        {"label": "Electricity Charges", "type": "energy", "amount": "300"}]}
    assert [c["amount"] for c in normalize.to_level1(raw, "KESC_1")["charges"]] == [100, 200]


def test_unknown_types_map_to_allowed_values():
    assert normalize.charge_type("Fuel Charges Adjustment", "") == "fpa"
    assert normalize.charge_type("weird", "Meter Rent") == "meter_rent"
    assert normalize.charge_type("weird", "something") == "other"
    assert normalize.tax_type("TV fee", "TV fee") == "other_tax"
    assert normalize.tax_type("", "Electricity Duty") == "electricity_duty"


# ------------------------------------------------------------------ validate

def test_official_bill_passes_all_checks():
    assert validate.check(TRUTH_0008) == []


def test_checks_catch_misread_values():
    bad = dict(TRUTH_0008, units_consumed=115, total_taxes=596.62)
    issues = validate.check(bad)
    assert any("units_consumed" in i for i in issues)
    assert any("total_taxes" in i for i in issues)


def test_all_hand_read_truth_files_are_consistent():
    for path in (DATA / "truth").glob("*.json"):
        assert validate.check(json.loads(path.read_text())) == [], path.name


# ------------------------------------------------------------------ calc

def test_calc_evaluates_safe_arithmetic():
    assert calc.evaluate("569.62 / 3430.24 * 100") == pytest.approx(16.6058, abs=1e-3)
    assert calc.evaluate("avg([141, 138, 197])") == pytest.approx(158.667, abs=1e-3)
    assert calc.evaluate("count([239, 203])") == 2


@pytest.mark.parametrize("expr", ["__import__('os')", "open('x')", "(1).real", "a + 1", "9 ** 9999"])
def test_calc_rejects_anything_else(expr):
    with pytest.raises(calc.CalcError):
        calc.evaluate(expr)


def test_render_fills_placeholders():
    text = calc.render("Taxes are {pct:1}% of PKR {bill}.", {"pct": "569.62/3430.24*100", "bill": "3430.24"})
    assert text == "Taxes are 16.6% of PKR 3,430.24."


# ------------------------------------------------------------------ end to end with a mock model

def _mock_model(prompt: str) -> str:
    if "QUESTIONS:" in prompt:
        return json.dumps({"answers": [
            {"question_id": "Q1", "calcs": [{"name": "pct", "expression": "569.62 / 3430.24 * 100"}],
             "answer": "Taxes are PKR 569.62, about {pct:1}% of the PKR 3,430.24 bill."},
            {"question_id": "Q2", "calcs": [{"name": "n", "expression": "count([239, 203])"}],
             "answer": "{n:0} months were above 200 units."},
        ]})
    return json.dumps(RAW_0008)


def test_pipeline_end_to_end(tmp_path):
    csv_dir, out_dir = tmp_path / "csv", tmp_path / "out"
    csv_io.make_templates(["KESC_0008"], [("Q1", "How much is tax?"), ("Q2", "Months above 200?")], csv_dir)
    client = Client(settings(tmp_path), mock=_mock_model)

    pipeline.run(client, DATA / "bills", csv_dir, out_dir)

    _, l1 = csv_io.read(out_dir / "level1.csv")
    assert json.loads(l1[0]["json"]) == TRUTH_0008
    _, l2 = csv_io.read(out_dir / "level2.csv")
    assert l2[0]["answer"] == "Taxes are PKR 569.62, about 16.6% of the PKR 3,430.24 bill."
    assert l2[1]["answer"] == "2 months were above 200 units."
    assert package.check_outputs(out_dir, csv_dir) == []
    assert evaluate.score(out_dir / "level1.csv", DATA / "truth")["accuracy"] == 1.0


def test_missing_image_still_writes_a_valid_row(tmp_path):
    csv_dir, out_dir = tmp_path / "csv", tmp_path / "out"
    csv_io.make_templates(["KESC_9999"], [("Q1", "Anything?")], csv_dir)
    client = Client(settings(tmp_path), mock=lambda p: json.dumps({"answers": []}))
    pipeline.run(client, DATA / "bills", csv_dir, out_dir)
    assert package.check_outputs(out_dir, csv_dir) == []


def test_level1_csv_quotes_json_like_the_guide(tmp_path):
    path = tmp_path / "level1.csv"
    csv_io.write(path, csv_io.LEVEL1_COLUMNS, [{"bill_id": "KESC_0008", "json": csv_io.one_line_json({"provider": "KE"})}])
    assert path.read_text().splitlines()[1] == 'KESC_0008,"{""provider"":""KE""}"'


def test_check_outputs_flags_empty_and_changed_cells(tmp_path):
    tpl, out = tmp_path / "tpl", tmp_path / "out"
    csv_io.make_templates(["KESC_1"], [("Q1", "q")], tpl)
    csv_io.write(out / "level1.csv", csv_io.LEVEL1_COLUMNS, [{"bill_id": "KESC_1", "json": ""}])
    csv_io.write(out / "level2.csv", csv_io.LEVEL2_COLUMNS,
                 [{"bill_id": "KESC_1", "question_id": "Q1", "question": "changed", "answer": "a"}])
    problems = package.check_outputs(out, tpl)
    assert any("empty json" in p for p in problems) and any("question changed" in p for p in problems)


def test_zip_layout_and_secret_guard(tmp_path):
    repo, out = tmp_path / "repo", tmp_path / "out"
    (repo / "backend").mkdir(parents=True)
    (repo / "README.md").write_text("# readme")
    (repo / "backend" / ".env").write_text("API_KEY=real")
    out.mkdir()
    for name in ("level1.csv", "level2.csv"):
        (out / name).write_text("bill_id\n")
    zip_path = tmp_path / "s.zip"
    package.build_zip(repo, out, zip_path, include_cache=False, demo=None)
    names = set(zipfile.ZipFile(zip_path).namelist())
    assert {"output/level1.csv", "output/level2.csv", "source/README.md"} <= names
    assert "source/backend/.env" not in names

    (repo / "leak.py").write_text('KEY = "AIza' + "x" * 35 + '"')
    with pytest.raises(RuntimeError, match="API keys"):
        package.build_zip(repo, out, zip_path, include_cache=False, demo=None)


# ------------------------------------------------------------------ config guard

def test_disallowed_model_is_refused(tmp_path):
    with pytest.raises(ConfigError):
        Settings(provider="google", model="gemini-2.5-flash", api_keys=["k"]).check()
    with pytest.raises(ConfigError):
        Settings(provider="google", model="gemini-3.5-flash-lite", api_keys=[]).check()
    Settings(provider="google", model="gemini-3.1-flash-lite", api_keys=["k"]).check()
