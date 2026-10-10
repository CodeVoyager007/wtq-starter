"""Inputs a judge might try: broken files, odd templates, bad model output, abuse of the web API."""
import json

import pytest
from fastapi.testclient import TestClient
from test_bill_decoder import DATA, TRUTH_0008, _mock_model, settings

from bill_decoder import calc, csv_io, normalize, package, pipeline
from bill_decoder.llm import Client


def _run(tmp_path, bills_dir, templates, model=_mock_model):
    csv_dir, out_dir = tmp_path / "csv", tmp_path / "out" / "nested"
    csv_dir.mkdir()
    for name, text in templates.items():
        (csv_dir / name).write_text(text, encoding="utf-8", newline="")
    report = pipeline.run(Client(settings(tmp_path), mock=model), bills_dir, csv_dir, out_dir)
    return csv_dir, out_dir, report


# ------------------------------------------------------------------ pipeline inputs

def test_corrupt_image_still_gives_a_valid_row(tmp_path):
    bills = tmp_path / "bills"
    bills.mkdir()
    (bills / "KESC_0001.png").write_bytes(b"this is not an image")
    templates = {"level1.csv": "bill_id,json\nKESC_0001,\n",
                 "level2.csv": "bill_id,question_id,question,answer\nKESC_0001,Q1,Any tax?,\n"}
    csv_dir, out_dir, report = _run(tmp_path, bills, templates, model=lambda p: '{"answers": []}')
    assert package.check_outputs(out_dir, csv_dir) == []
    assert report["KESC_0001"]["error"]


def test_template_with_bom_crlf_and_spaces_is_kept_exactly(tmp_path):
    template = "﻿bill_id,json\r\nKESC_0008 ,\r\n"
    csv_dir, out_dir, _ = _run(tmp_path, DATA / "bills", {"level1.csv": template})
    _, rows = csv_io.read(out_dir / "level1.csv")
    assert rows[0]["bill_id"] == "KESC_0008 "  # never change bill_id
    assert json.loads(rows[0]["json"]) == TRUTH_0008


def test_level2_template_missing_is_fine(tmp_path):
    csv_dir, out_dir, _ = _run(tmp_path, DATA / "bills", {"level1.csv": "bill_id,json\nKESC_0008,\n"})
    assert (out_dir / "level1.csv").exists() and not (out_dir / "level2.csv").exists()


def test_question_with_commas_quotes_and_newlines_round_trips(tmp_path):
    question = 'He said "why, exactly?"\nAnd 2nd line'
    rows = [{"bill_id": "KESC_0008", "question_id": "Q1", "question": question, "answer": ""}]
    (tmp_path / "csv").mkdir()
    csv_io.write(tmp_path / "csv" / "level2.csv", csv_io.LEVEL2_COLUMNS, rows)
    csv_io.write(tmp_path / "csv" / "level1.csv", csv_io.LEVEL1_COLUMNS, [{"bill_id": "KESC_0008", "json": ""}])
    out_dir = tmp_path / "out"
    pipeline.run(Client(settings(tmp_path), mock=_mock_model), DATA / "bills", tmp_path / "csv", out_dir)
    _, out = csv_io.read(out_dir / "level2.csv")
    assert out[0]["question"] == question and out[0]["answer"]
    assert package.check_outputs(out_dir, tmp_path / "csv") == []


@pytest.mark.parametrize("reply", ["not json at all", "[1, 2, 3]", '{"answers": oops}', "```json\n{broken\n```", '{"charges": "oops", "taxes": [1, null]}', "{}"])
def test_garbage_model_output_never_breaks_the_csv(tmp_path, reply):
    templates = {"level1.csv": "bill_id,json\nKESC_0008,\n",
                 "level2.csv": "bill_id,question_id,question,answer\nKESC_0008,Q1,Any tax?,\n"}
    csv_dir, out_dir, _ = _run(tmp_path, DATA / "bills", templates, model=lambda p: reply)
    assert package.check_outputs(out_dir, csv_dir) == []


# ------------------------------------------------------------------ normalisation oddities

@pytest.mark.parametrize("text,expected", [
    ("1,23,456", 123456), ("Rs.-0.53", -0.53), ("  3,430  ", 3430), ("PKR 1,054.00", 1054), ("12.5 kW", 12.5),
])
def test_amount_formats(text, expected):
    assert normalize.parse_amount(text) == expected


@pytest.mark.parametrize("text,expected", [("2026/04/21", "2026-04-21"), ("21.04.2026", "2026-04-21"),
                                           ("21-APR-26", "2026-04-21"), ("not a date", None)])
def test_date_formats(text, expected):
    assert normalize.parse_date(text) == expected


# ------------------------------------------------------------------ calculator abuse

@pytest.mark.parametrize("expr", ["(" * 500 + "1" + ")" * 500, "1+" * 1500 + "1",
                                  "max([x for x in [1, 2]] * 10 ** 8)", "__builtins__", "lambda: 1"])
def test_calc_survives_hostile_expressions(expr):
    with pytest.raises(calc.CalcError):
        calc.evaluate(expr)


# ------------------------------------------------------------------ web API abuse

@pytest.fixture
def web(tmp_path, monkeypatch):
    from app import bills, config
    from app.main import app

    monkeypatch.setattr(bills, "_client", Client(settings(tmp_path), mock=_mock_model))
    monkeypatch.setattr(bills, "_limiter", bills._RateLimiter(3))
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 2 * 1024 * 1024)
    return TestClient(app)


def _upload(web, data, name="KESC_0008.png"):
    return web.post("/api/bill", files={"file": (name, data, "image/png")}, data={"provider": "auto"})


def test_api_rejects_bad_uploads(web):
    assert _upload(web, b"").status_code == 400
    assert _upload(web, b"plain text, not an image").status_code == 400
    assert _upload(web, b"x" * (3 * 1024 * 1024)).status_code == 413


def test_api_rate_limits_one_client(web):
    image = (DATA / "bills" / "KESC_0008.png").read_bytes()
    codes = [_upload(web, image).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_api_reports_busy_when_all_slots_are_taken(web, monkeypatch):
    import threading

    from app import bills, config
    monkeypatch.setattr(bills, "_decode_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(config, "DECODE_WAIT_SECONDS", 0.01)
    bills._decode_slots.acquire()
    try:
        assert _upload(web, (DATA / "bills" / "KESC_0008.png").read_bytes()).status_code == 429
    finally:
        bills._decode_slots.release()


def test_api_questions_are_validated(web):
    assert web.post("/api/bill/ask", json={"token": "guess", "question": "hi"}).status_code == 404
    assert web.post("/api/bill/ask", json={"token": "t", "question": "x" * 501}).status_code == 422
    assert web.post("/api/bill/ask", json={"token": "t", "question": ""}).status_code == 422


def test_api_file_names_cannot_escape(web):
    image = (DATA / "bills" / "KESC_0008.png").read_bytes()
    res = _upload(web, image, name="../../etc/KESC_0008.png")
    assert res.status_code == 200 and res.json()["bill_id"] == "KESC_0008"


def test_check_fails_when_templates_are_missing(tmp_path):
    out = tmp_path / "out"
    csv_io.make_templates(["KESC_1"], [("Q1", "q")], out)
    problems = package.check_outputs(out, tmp_path / "no-such-folder")
    assert len(problems) == 2 and all("template not found" in p for p in problems)
