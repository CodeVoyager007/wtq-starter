"""Pattern 3: turn messy text into structured data (extract fields or classify) using prompts, no training."""
import pandas as pd

from .. import llm
from ..schema import result
from .profiler import py, to_table

DEFAULT_FIELDS = ["summary", "people", "organizations", "locations", "dates", "key_points"]

EXTRACT_PROMPT = """Extract the following fields from the text. Use null when a field is not present.
Fields: {fields}

Text:
\"\"\"{text}\"\"\"

Return JSON with exactly these keys."""

CLASSIFY_PROMPT = """Classify the text into exactly one of these labels: {labels}

Text:
\"\"\"{text}\"\"\"

Return JSON: {{"label": "<one label>", "confidence": <0 to 1>, "reason": "one short sentence"}}"""


def extract_one(text: str, fields: list[str]) -> dict:
    mock = {f: "mock" for f in fields}
    out = llm.generate_json(EXTRACT_PROMPT.format(fields=", ".join(fields), text=text[:6000]), mock=mock)
    return {f: py(out.get(f)) if not isinstance(out.get(f), (list, dict)) else str(out.get(f)) for f in fields}


def classify_one(text: str, labels: list[str]) -> dict:
    mock = {"label": labels[0], "confidence": 0.9, "reason": "mock"}
    out = llm.generate_json(CLASSIFY_PROMPT.format(labels=", ".join(labels), text=text[:6000]), mock=mock)
    label = out.get("label")
    if label not in labels:  # keep results clean if the model invents a label
        label = next((l for l in labels if str(label).lower() == l.lower()), "unknown")
    return {"label": label, "confidence": py(out.get("confidence")), "reason": out.get("reason", "")}


def run_text(text: str, mode: str = "extract", fields: list[str] | None = None, labels: list[str] | None = None) -> dict:
    if mode == "classify":
        if not labels:
            raise ValueError("Add at least one label to classify with (comma separated).")
        out = classify_one(text, labels)
        return result("metrics", title="Classification", text=out["reason"], metrics={"label": out["label"], "confidence": out["confidence"]})
    fields = fields or DEFAULT_FIELDS
    out = extract_one(text, fields)
    table = {"columns": ["field", "value"], "rows": [[k, v] for k, v in out.items()], "truncated": False}
    return result("table", title="Extracted fields", table=table)


def run_column(df: pd.DataFrame, column: str, mode: str, fields=None, labels=None, limit: int = 10) -> dict:
    """Run on the first `limit` rows of a text column (keeps you under rate limits while testing)."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found. Columns: {', '.join(map(str, df.columns))}")
    rows = []
    for text in df[column].astype(str).head(limit):
        if mode == "classify":
            if not labels:
                raise ValueError("Add at least one label to classify with (comma separated).")
            o = classify_one(text, labels)
            rows.append({"text": text[:120], "label": o["label"], "confidence": o["confidence"]})
        else:
            o = extract_one(text, fields or DEFAULT_FIELDS)
            rows.append({"text": text[:120], **o})
    out_df = pd.DataFrame(rows)
    chart = None
    if mode == "classify" and not out_df.empty:
        counts = out_df["label"].value_counts()
        chart = {"type": "bar", "labels": counts.index.tolist(), "values": [float(v) for v in counts.values], "label": "rows per label"}
    return result("table", title=f"{mode.title()} on '{column}' (first {limit} rows)", table=to_table(out_df), chart=chart)
