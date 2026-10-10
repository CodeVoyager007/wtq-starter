"""Check the results and build the one-shot submission ZIP (guide section 7)."""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from . import csv_io
from .schema import LEVEL1_FIELDS

MAX_ZIP_BYTES = 15 * 1024 * 1024
SKIP_DIRS = {".git", ".venv", "node_modules", ".next", "__pycache__", ".pytest_cache", ".ruff_cache",
             "output", "test", ".claude"}
SKIP_FILES = {".env", ".DS_Store"}
SKIP_SUFFIXES = {".zip", ".pyc"}
BILL_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SECRET_PATTERNS = [
    re.compile(p) for p in (r"AIza[0-9A-Za-z_\-]{30,}", r"sk-[A-Za-z0-9_\-]{20,}", r"sk-ant-[A-Za-z0-9_\-]{20,}")
]


def check_outputs(out_dir: Path, template_dir: Path) -> list[str]:
    """Every rule from guide 7.1-7.2 that we can check mechanically."""
    problems: list[str] = []
    for name, value_col in (("level1.csv", "json"), ("level2.csv", "answer")):
        out_path, tpl_path = out_dir / name, template_dir / name
        if not out_path.exists():
            problems.append(f"{name}: missing in {out_dir}")
            continue
        out_cols, out_rows = csv_io.read(out_path)
        tpl_cols, tpl_rows = csv_io.read(tpl_path) if tpl_path.exists() else (out_cols, out_rows)
        if out_cols != tpl_cols:
            problems.append(f"{name}: columns {out_cols} differ from template {tpl_cols}")
        if len(out_rows) != len(tpl_rows):
            problems.append(f"{name}: {len(out_rows)} rows, template has {len(tpl_rows)}")
        for i, (out, tpl) in enumerate(zip(out_rows, tpl_rows, strict=False), start=2):  # counts checked above
            for col in tpl_cols:
                if col != value_col and out.get(col) != tpl.get(col):
                    problems.append(f"{name} line {i}: {col} changed from {tpl.get(col)!r}")
            value = (out.get(value_col) or "").strip()
            if not value:
                problems.append(f"{name} line {i}: empty {value_col}")
            elif value_col == "json":
                problems += _check_level1_json(i, value)
    return problems


def _check_level1_json(line: int, value: str) -> list[str]:
    if "\n" in value:
        return [f"level1.csv line {line}: JSON spans several lines"]
    try:
        bill = json.loads(value)
    except json.JSONDecodeError as exc:
        return [f"level1.csv line {line}: invalid JSON ({exc})"]
    missing = [f for f in LEVEL1_FIELDS if f not in bill]
    return [f"level1.csv line {line}: missing fields {missing}"] if missing else []


def _source_files(repo_root: Path, include_cache: bool):
    for path in sorted(repo_root.rglob("*")):
        rel = path.relative_to(repo_root)
        parts = set(rel.parts)
        if path.is_dir() or parts & SKIP_DIRS or path.name in SKIP_FILES or path.suffix in SKIP_SUFFIXES:
            continue
        if ".cache" in parts and not include_cache:
            continue
        if "data" in parts and path.suffix.lower() in BILL_IMAGE_SUFFIXES:
            continue  # training bills are not our code
        yield path, rel


def find_secrets(files) -> list[str]:
    hits = []
    for path, rel in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(p.search(text) for p in SECRET_PATTERNS):
            hits.append(str(rel))
    return hits


def build_zip(repo_root: Path, out_dir: Path, zip_path: Path, include_cache: bool, demo: Path | None) -> int:
    files = list(_source_files(repo_root, include_cache))
    secrets = find_secrets(files)
    if secrets:
        raise RuntimeError(f"possible API keys found, not packaging: {secrets}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("level1.csv", "level2.csv"):
            zf.write(out_dir / name, f"output/{name}")
        for path, rel in files:
            zf.write(path, f"source/{rel.as_posix()}")
        if demo:
            zf.write(demo, f"demo/demo{demo.suffix.lower()}")
    size = zip_path.stat().st_size
    if size > MAX_ZIP_BYTES:
        raise RuntimeError(f"ZIP is {size / 1e6:.1f} MB, over the 15 MB limit")
    return size
