"""Every module returns the SAME shape, so the frontend can render any result without changes.

kind:    "text" | "table" | "metrics" | "chart" (just a label, the UI shows whatever is filled in)
table:   {"columns": [...], "rows": [[...], ...], "truncated": bool}
chart:   {"type": "bar", "labels": [...], "values": [...], "label": "what the numbers mean"}
metrics: {"accuracy": 0.91, ...}
"""


def result(
    kind: str = "text",
    title: str = "",
    text: str = "",
    table: dict | None = None,
    metrics: dict | None = None,
    chart: dict | None = None,
    code: str | None = None,
    sources: list | None = None,
    meta: dict | None = None,
) -> dict:
    return {
        "ok": True,
        "kind": kind,
        "title": title,
        "text": text,
        "table": table,
        "metrics": metrics,
        "chart": chart,
        "code": code,
        "sources": sources or [],
        "meta": meta or {},
    }
