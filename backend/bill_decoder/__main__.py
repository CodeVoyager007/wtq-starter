"""Command line entry point: `uv run python -m bill_decoder <command> ...`

  run        bills + CSV templates -> output/level1.csv, output/level2.csv
  templates  build blank templates from a bills folder (for training runs)
  eval       score a level1.csv against truth JSON files
  check      validate output CSVs against the templates
  package    validate, then build the submission ZIP
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import config, csv_io, evaluate, imaging, package, pipeline
from .llm import Client

REPO_ROOT = config.BACKEND_DIR.parent


def _cmd_run(args) -> int:
    client = Client(config.load())
    levels = {int(x) for x in args.levels.split(",")}
    report = pipeline.run(client, Path(args.bills), Path(args.csv), Path(args.out), levels)
    flagged = {b: r for b, r in report.items() if r["issues"] or r["error"]}
    print(f"Done: {len(report)} bills, {len(flagged)} with open checks or errors. Output in {args.out}")
    for bill_id, r in flagged.items():
        print(f"  {bill_id}: {r['error'] or '; '.join(r['issues'])}")
    return 0


def _cmd_templates(args) -> int:
    bills = sorted(p.stem for p in Path(args.bills).iterdir() if p.suffix.lower() in imaging.IMAGE_SUFFIXES)
    questions = []
    if args.questions:
        lines = [l.strip() for l in Path(args.questions).read_text(encoding="utf-8").splitlines() if l.strip()]
        questions = [(f"Q{i}", q) for i, q in enumerate(lines, 1)]
    csv_io.make_templates(bills, questions, Path(args.csv))
    print(f"Templates for {len(bills)} bills and {len(questions)} questions written to {args.csv}")
    return 0


def _cmd_eval(args) -> int:
    print(json.dumps(evaluate.score(Path(args.pred), Path(args.truth)), indent=2, ensure_ascii=False))
    return 0


def _cmd_check(args) -> int:
    problems = package.check_outputs(Path(args.out), Path(args.csv))
    for p in problems:
        print("PROBLEM:", p)
    print("Outputs are valid." if not problems else f"{len(problems)} problem(s).")
    return 1 if problems else 0


def _cmd_package(args) -> int:
    if _cmd_check(args):
        return 1
    size = package.build_zip(REPO_ROOT, Path(args.out), Path(args.zip), args.include_cache,
                             Path(args.demo) if args.demo else None)
    print(f"Wrote {args.zip} ({size / 1e6:.2f} MB). Open it and look before you upload.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="bill_decoder", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="extract and answer")
    p.add_argument("--bills", required=True, help="folder with bill images")
    p.add_argument("--csv", required=True, help="folder with level1.csv and level2.csv templates")
    p.add_argument("--out", default="output", help="where to write the completed CSVs")
    p.add_argument("--levels", default="1,2", help="1, 2 or 1,2")
    p.set_defaults(func=_cmd_run)

    p = sub.add_parser("templates", help="blank templates for a training folder")
    p.add_argument("--bills", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--questions", help="text file, one question per line")
    p.set_defaults(func=_cmd_templates)

    p = sub.add_parser("eval", help="score level1.csv against truth files")
    p.add_argument("--pred", required=True)
    p.add_argument("--truth", required=True)
    p.set_defaults(func=_cmd_eval)

    for name, func in (("check", _cmd_check), ("package", _cmd_package)):
        p = sub.add_parser(name)
        p.add_argument("--out", default="output")
        p.add_argument("--csv", required=True, help="the official template folder")
        if name == "package":
            p.add_argument("--zip", default="submission.zip")
            p.add_argument("--demo", help="optional demo video (.mp4/.mov/.webm)")
            p.add_argument("--include-cache", action="store_true",
                           help="ship cached model responses so a rerun reproduces the same answers")
        p.set_defaults(func=func)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for noisy in ("httpx", "google_genai", "google.genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        return args.func(args)
    except (config.ConfigError, RuntimeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
