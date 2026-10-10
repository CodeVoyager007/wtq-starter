"""Profile ANY table: shape, column types, missing values, quick stats. Also used as the first thing to run on the day."""
import math

import numpy as np
import pandas as pd


def py(v):
    """Turn numpy/pandas values into plain JSON-safe Python values."""
    if v is None:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(v, (pd.Timestamp, pd.Timedelta)):
        return str(v)
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v if isinstance(v, (int, str)) else str(v)


def to_table(df: pd.DataFrame, limit: int = 200) -> dict:
    part = df.head(limit)
    rows = [[py(v) for v in row] for row in part.itertuples(index=False, name=None)]
    return {"columns": [str(c) for c in part.columns], "rows": rows, "truncated": len(df) > limit}


def profile_dataframe(df: pd.DataFrame) -> dict:
    cols = []
    for c in df.columns:
        s = df[c]
        info = {
            "name": str(c),
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "unique": int(s.nunique(dropna=True)),
            "sample": [py(v) for v in s.dropna().head(3).tolist()],
        }
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and s.notna().any():
            info.update(min=py(s.min()), max=py(s.max()), mean=py(round(float(s.mean()), 3)))
        cols.append(info)
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_info": cols,
        "preview": to_table(df.head(8)),
    }


def schema_text(df: pd.DataFrame) -> str:
    """Short plain-text schema to paste into prompts."""
    p = profile_dataframe(df)
    lines = [f"{p['rows']} rows, {p['columns']} columns"]
    for c in p["column_info"]:
        extra = f", missing={c['missing']}, unique={c['unique']}, e.g. {c['sample']}"
        if "min" in c:
            extra += f", min={c['min']}, max={c['max']}, mean={c['mean']}"
        lines.append(f"- {c['name']} ({c['dtype']}){extra}")
    return "\n".join(lines)
