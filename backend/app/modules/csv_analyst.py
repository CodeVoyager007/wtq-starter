"""Pattern 1: ask questions about a table in plain English.

The LLM writes pandas code, we run it on the data, and return the answer + the code (judges like seeing the code).

SAFETY NOTE: the checks below (an AST filter + limited builtins) stop accidents and silly prompts.
They are NOT a real sandbox. Use this only on your own laptop for the demo, never on a public server with private data.
"""
import ast
import builtins

import numpy as np
import pandas as pd

from .. import llm
from ..schema import result
from .profiler import schema_text, to_table

# `import pandas as pd` is harmless, and AI models love to write it, so a short list of modules is allowed.
ALLOWED_IMPORTS = {"pandas", "numpy", "math", "re", "datetime", "statistics", "collections", "itertools"}
BLOCKED_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "delattr", "globals",
    "locals", "vars", "input", "breakpoint", "exit", "quit", "help", "dir", "memoryview",
}
BLOCKED_ATTRS = {
    # file and network access
    "read_csv", "read_excel", "read_json", "read_parquet", "read_pickle", "read_sql", "read_table",
    "read_html", "read_clipboard", "to_csv", "to_excel", "to_json", "to_pickle", "to_parquet",
    "to_sql", "to_clipboard", "to_feather", "to_hdf", "savetxt", "loadtxt", "fromfile", "tofile",
    # ways to reach the operating system through module attributes
    "os", "sys", "subprocess", "system", "popen", "importlib", "builtins", "ctypes", "shutil", "socket", "pickle",
}
ALLOWED_BUILTINS = {
    n: getattr(builtins, n)
    for n in (
        "len range min max sum sorted round abs list dict set str int float bool tuple "
        "enumerate zip any all map filter reversed isinstance format pow divmod"
    ).split()
}

PROMPT = """You are a careful data analyst. A pandas DataFrame named df is already loaded.
Also available: pd (pandas) and np (numpy), so you do not need to import them. Do not read or write files.

Table schema:
{schema}

Question: {question}

Write pandas code that answers the question and stores the answer in a variable named result
(a DataFrame, a Series, or a single value). Keep the result small and readable (sort and limit if needed).
Return JSON: {{"code": "python code as one string", "explanation": "one or two plain sentences"}}"""

MOCK = {
    "code": "result = df.select_dtypes('number').describe().reset_index()",
    "explanation": "Mock answer: summary statistics of the numeric columns.",
}


def _check(code: str) -> None:
    """Reject code that imports unusual modules, touches files, or pokes at Python internals."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in the generated code: {e.msg} (line {e.lineno})")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    raise ValueError(f"Blocked import: {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                raise ValueError(f"Blocked import: {node.module}")
            for a in node.names:
                if a.name.startswith("_") or a.name in BLOCKED_ATTRS:
                    raise ValueError(f"Blocked import name: {a.name}")
        elif isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"Blocked name: {node.id}")
        elif isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in BLOCKED_ATTRS):
            raise ValueError(f"Blocked attribute: {node.attr}")


def _run(code: str, df: pd.DataFrame):
    _check(code)
    safe_builtins = dict(ALLOWED_BUILTINS)
    # Python and pandas themselves use __import__ behind the scenes (for example Timestamp.strftime).
    # Leaving it out causes "KeyError: '__import__'". The AST check above already stops the generated
    # code from importing anything unusual or calling __import__ itself.
    safe_builtins["__import__"] = builtins.__import__
    env = {"__builtins__": safe_builtins, "df": df.copy(), "pd": pd, "np": np}
    exec(code, env)  # noqa: S102
    if "result" not in env:
        raise ValueError("The code did not set a variable named result")
    return env["result"]


def _format(res, question: str, code: str, explanation: str) -> dict:
    if isinstance(res, pd.Series):
        res = res.reset_index()
        res.columns = [str(c) for c in res.columns]
    if isinstance(res, pd.DataFrame):
        table = to_table(res)
        chart = None
        if res.shape[1] == 2 and 1 < len(res) <= 30 and pd.api.types.is_numeric_dtype(res.iloc[:, 1]):
            chart = {
                "type": "bar",
                "labels": [str(v) for v in res.iloc[:, 0].tolist()],
                "values": [float(v) for v in res.iloc[:, 1].fillna(0).tolist()],
                "label": str(res.columns[1]),
            }
        return result("table", title=question, text=explanation, table=table, chart=chart, code=code)
    return result("text", title=question, text=f"{explanation}\n\nAnswer: {res}", code=code)


def ask(df: pd.DataFrame, question: str) -> dict:
    prompt = PROMPT.format(schema=schema_text(df), question=question)
    out = llm.generate_json(prompt, mock=MOCK)
    code = out.get("code", "")
    explanation = out.get("explanation", "")
    try:
        res = _run(code, df)
    except Exception as first_error:
        # One repair round: show the model its own error.
        fix_prompt = (
            prompt
            + f"\n\nYour previous code:\n{code}\n\nIt failed with: {type(first_error).__name__}: {first_error}\n"
            "Fix it. Return the same JSON format."
        )
        out = llm.generate_json(fix_prompt, mock=MOCK)
        code = out.get("code", "")
        explanation = out.get("explanation", "")
        try:
            res = _run(code, df)
        except Exception as second_error:
            # A friendly message in the UI instead of a server crash.
            raise ValueError(
                f"The AI's code failed twice ({type(second_error).__name__}: {str(second_error)[:150]}). "
                "Try asking in a different way, for example name the exact columns you mean."
            )
    return _format(res, question, code, explanation)
