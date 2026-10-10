"""Score a level1.csv against hand-checked truth JSON files, like the judges do:
text and dates exact, numbers within ±1, null counts as a value."""
from __future__ import annotations

import json
from pathlib import Path

from . import csv_io
from .schema import LEVEL1_FIELDS, NUMBER_FIELDS

TOLERANCE = 1.0


def _same(a, b, numeric: bool) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if numeric:
        try:
            return abs(float(a) - float(b)) <= TOLERANCE
        except (TypeError, ValueError):
            return False
    return str(a) == str(b)


def _same_lines(pred: list, truth: list) -> bool:
    if len(pred or []) != len(truth or []):
        return False
    remaining = list(truth)
    for line in pred:
        match = next((t for t in remaining if t["type"] == line.get("type")
                      and _same(line.get("amount"), t["amount"], True)), None)
        if match is None:
            return False
        remaining.remove(match)
    return True


def score(pred_csv: Path, truth_dir: Path) -> dict:
    _, rows = csv_io.read(pred_csv)
    per_bill, per_field = {}, {f: [0, 0] for f in LEVEL1_FIELDS}
    for row in rows:
        truth_path = truth_dir / f"{row['bill_id']}.json"
        if not truth_path.exists():
            continue
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        pred = json.loads(row["json"])
        wrong = []
        for field in LEVEL1_FIELDS:
            if field not in truth:
                continue
            if field in ("charges", "taxes"):
                ok = _same_lines(pred.get(field), truth[field])
            else:
                ok = _same(pred.get(field), truth[field], field in NUMBER_FIELDS)
            per_field[field][0] += ok
            per_field[field][1] += 1
            if not ok:
                wrong.append({"field": field, "predicted": pred.get(field), "expected": truth[field]})
        per_bill[row["bill_id"]] = wrong
    correct = sum(c for c, _ in per_field.values())
    total = sum(t for _, t in per_field.values())
    return {"accuracy": round(correct / total, 4) if total else None, "correct": correct, "total": total,
            "wrong_by_bill": per_bill,
            "by_field": {f: f"{c}/{t}" for f, (c, t) in per_field.items() if t}}
