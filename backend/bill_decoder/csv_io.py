"""CSV templates in, completed CSVs out. Row order and columns never change (guide 7.2)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

LEVEL1_COLUMNS = ["bill_id", "json"]
LEVEL2_COLUMNS = ["bill_id", "question_id", "question", "answer"]


def read(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writeheader()
        writer.writerows({c: row.get(c, "") for c in columns} for row in rows)


def one_line_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def make_templates(bill_ids: list[str], questions: list[tuple[str, str]], csv_dir: Path) -> None:
    """Build blank level1/level2 templates (same shape as the official ones) for training runs."""
    write(csv_dir / "level1.csv", LEVEL1_COLUMNS, [{"bill_id": b, "json": ""} for b in bill_ids])
    write(csv_dir / "level2.csv", LEVEL2_COLUMNS, [
        {"bill_id": b, "question_id": qid, "question": q, "answer": ""} for b in bill_ids for qid, q in questions
    ])
