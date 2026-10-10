"""Tiny in-memory store. Fine for a one-day demo (it resets when the server restarts)."""
import uuid

import pandas as pd

DATASETS: dict[str, dict] = {}


def add_dataset(name: str, df: pd.DataFrame) -> str:
    dataset_id = uuid.uuid4().hex[:8]
    DATASETS[dataset_id] = {"name": name, "df": df}
    return dataset_id


def get_df(dataset_id: str | None) -> pd.DataFrame:
    if not dataset_id or dataset_id not in DATASETS:
        raise ValueError("No dataset loaded. Upload a file first (or click 'Load sample data').")
    return DATASETS[dataset_id]["df"]
