"""Batch run: bills folder + CSV templates -> completed level1.csv and level2.csv."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from . import csv_io, extract, imaging
from .answer import answer_bill
from .llm import Client, LLMError

log = logging.getLogger(__name__)


def run(client: Client, bills_dir: Path, csv_dir: Path, out_dir: Path, levels: set[int] = frozenset({1, 2})) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    l1_cols, l1_rows = csv_io.read(csv_dir / "level1.csv")
    l2_path = csv_dir / "level2.csv"
    l2_cols, l2_rows = csv_io.read(l2_path) if l2_path.exists() else (csv_io.LEVEL2_COLUMNS, [])

    bill_ids = list(dict.fromkeys([r["bill_id"].strip() for r in l1_rows] + [r["bill_id"].strip() for r in l2_rows]))
    results: dict[str, extract.Extraction] = {}
    images = {}
    for i, bill_id in enumerate(bill_ids, 1):
        log.info("[%d/%d] reading %s", i, len(bill_ids), bill_id)
        path = imaging.find_bill(bills_dir, bill_id)
        if path is None:
            results[bill_id] = extract.failed(bill_id, f"image not found in {bills_dir}")
            log.error("%s: image not found", bill_id)
            continue
        try:
            images[bill_id] = imaging.load(path)
            results[bill_id] = extract.extract_bill(client, bill_id, images[bill_id])
        except (LLMError, OSError, ValueError) as exc:
            log.error("%s: extraction failed: %s", bill_id, exc)
            results[bill_id] = extract.failed(bill_id, str(exc))

    if 1 in levels:
        for row in l1_rows:
            row["json"] = csv_io.one_line_json(results[row["bill_id"].strip()].level1)
        csv_io.write(out_dir / "level1.csv", l1_cols, l1_rows)

    if 2 in levels and l2_rows:
        for bill_id in bill_ids:
            bill_rows = [r for r in l2_rows if r["bill_id"].strip() == bill_id]
            if not bill_rows:
                continue
            log.info("answering %d questions for %s", len(bill_rows), bill_id)
            questions = [(r["question_id"].strip(), r["question"]) for r in bill_rows]
            answers = answer_bill(client, bill_id, images.get(bill_id), results[bill_id].facts, questions)
            for row in bill_rows:
                row["answer"] = answers[row["question_id"].strip()]
        csv_io.write(out_dir / "level2.csv", l2_cols, l2_rows)

    report = {
        bill_id: {k: v for k, v in asdict(r).items() if k in ("issues", "repaired", "error")}
        for bill_id, r in results.items()
    }
    (out_dir / "run_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
