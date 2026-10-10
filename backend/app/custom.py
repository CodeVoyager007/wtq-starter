"""=====================  EDIT THIS FILE ON EVENT DAY  =====================

The frontend "Run" button sends everything here (POST /api/run -> run()).
The four built-in modes already work on any dataset. When the real challenge is announced:

  1. Try the built-in mode that fits best (analyze / docs / extract / predict).
  2. If you need something special, write it in solve_challenge() and use mode "custom".

Always return the shape from app/schema.py (result(...)), and the UI will show it automatically.
"""
from . import llm, store
from .modules import csv_analyst, extraction, ml_stub, rag
from .schema import result


def solve_challenge(text: str, df, options: dict) -> dict:
    """--- YOUR CODE HERE --- (mode: custom)

    text:    what the user typed in the input box
    df:      the uploaded table as a pandas DataFrame (or None)
    options: extra settings from the UI (labels, fields, column, target)
    """
    answer = llm.generate(
        "You are a helpful assistant for this challenge. Replace this prompt with your own.\n\n" + text,
        mock="[mock] Replace solve_challenge() in backend/app/custom.py with your own logic.",
    )
    return result("text", title="Custom result", text=answer)


def run(payload: dict) -> dict:
    mode = payload.get("mode", "analyze")
    text = (payload.get("input") or "").strip()
    options = payload.get("options") or {}
    dataset_id = payload.get("dataset_id")

    if mode == "analyze":
        if not text:
            raise ValueError("Type a question about your data.")
        return csv_analyst.ask(store.get_df(dataset_id), text)

    if mode == "docs":
        if not text:
            raise ValueError("Type a question about your documents.")
        return rag.answer(text)

    if mode in ("extract", "classify"):
        fields = [f.strip() for f in (options.get("fields") or "").split(",") if f.strip()] or None
        labels = [l.strip() for l in (options.get("labels") or "").split(",") if l.strip()] or None
        column = (options.get("column") or "").strip()
        if column:  # run on a text column of the uploaded table
            return extraction.run_column(store.get_df(dataset_id), column, mode, fields, labels)
        if not text:
            raise ValueError("Paste some text (or enter a text column name to run on your table).")
        return extraction.run_text(text, mode, fields, labels)

    if mode == "predict":
        target = (options.get("target") or text).strip()
        if not target:
            raise ValueError("Enter the column you want to predict.")
        return ml_stub.train(store.get_df(dataset_id), target)

    if mode == "custom":
        df = store.DATASETS[dataset_id]["df"] if dataset_id in store.DATASETS else None
        return solve_challenge(text, df, options)

    raise ValueError(f"Unknown mode '{mode}'")
