"""Pattern 4: a quick classic ML baseline (thin on purpose).

Trains a random forest on any table and reports honest metrics + which columns mattered.
If you are short on time on the day, the LLM patterns are faster. Use this when the task is clearly prediction.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ..schema import result
from .profiler import py, to_table


def train(df: pd.DataFrame, target: str) -> dict:
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found. Columns: {', '.join(map(str, df.columns))}")

    d = df.dropna(subset=[target]).copy()
    if len(d) < 30:
        raise ValueError("Need at least 30 rows with a value in the target column.")

    y = d[target]
    X = d.drop(columns=[target])

    # Turn date-like text columns into month + weekday numbers (raw dates would be noise).
    for c in [c for c in X.columns if X[c].dtype == object]:
        try:
            parsed = pd.to_datetime(X[c], errors="coerce", format="mixed")
        except (TypeError, ValueError):
            continue
        if parsed.notna().mean() >= 0.9:
            X[f"{c}_month"] = parsed.dt.month
            X[f"{c}_weekday"] = parsed.dt.dayofweek
            X = X.drop(columns=[c])

    # Drop id-like / free-text columns (almost every value is different).
    dropped = [c for c in X.columns if X[c].dtype == object and X[c].nunique() / len(X) > 0.5]
    X = X.drop(columns=dropped)
    if X.shape[1] == 0:
        raise ValueError("No usable feature columns left after removing id/text columns.")

    is_classification = (not pd.api.types.is_numeric_dtype(y)) or y.nunique() <= 10
    if is_classification:
        y = y.astype(str)

    num_cols = X.select_dtypes(include="number").columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]
    pre = ColumnTransformer(
        [
            ("num", SimpleImputer(strategy="median"), num_cols),
            (
                "cat",
                Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore"))]),
                cat_cols,
            ),
        ]
    )
    model = (
        RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
        if is_classification
        else RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1)
    )
    pipe = Pipeline([("pre", pre), ("model", model)])

    stratify = y if is_classification and y.value_counts().min() >= 2 else None
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)

    if is_classification:
        metrics = {
            "task": "classification",
            "accuracy": round(float(accuracy_score(y_te, pred)), 3),
            "f1_weighted": round(float(f1_score(y_te, pred, average="weighted")), 3),
            "baseline_accuracy": round(float(y_te.value_counts(normalize=True).max()), 3),
        }
    else:
        metrics = {
            "task": "regression",
            "r2": round(float(r2_score(y_te, pred)), 3),
            "mae": round(float(mean_absolute_error(y_te, pred)), 3),
        }
    metrics["train_rows"] = int(len(X_tr))
    metrics["test_rows"] = int(len(X_te))

    names = pipe.named_steps["pre"].get_feature_names_out()
    imp = pipe.named_steps["model"].feature_importances_
    top = sorted(zip(names, imp), key=lambda t: t[1], reverse=True)[:10]
    imp_df = pd.DataFrame({"feature": [n.split("__", 1)[-1] for n, _ in top], "importance": [round(float(v), 4) for _, v in top]})

    note = f"Ignored id/text columns: {', '.join(dropped)}." if dropped else ""
    return result(
        "metrics",
        title=f"Quick model to predict '{target}'",
        text=("Compare accuracy with the baseline (always guessing the most common answer). " if is_classification else "") + note,
        metrics={k: py(v) for k, v in metrics.items()},
        table=to_table(imp_df),
        chart={"type": "bar", "labels": imp_df["feature"].tolist(), "values": imp_df["importance"].tolist(), "label": "feature importance"},
    )
