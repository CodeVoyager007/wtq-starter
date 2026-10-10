"""Safe arithmetic for Level 2. The model writes expressions, Python computes them.

Allowed: numbers, + - * / // % **, parentheses, unary minus, list literals and the
functions below. Anything else (names, attributes, calls to other functions) is rejected.
"""
from __future__ import annotations

import ast
import operator
import re
import statistics

_BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _avg(*args):
    values = _flatten(args)
    return sum(values) / len(values)


def _flatten(args):
    if len(args) == 1 and isinstance(args[0], list):
        return args[0]
    return list(args)


_FUNCTIONS = {
    "sum": lambda *a: sum(_flatten(a)),
    "avg": _avg,
    "mean": _avg,
    "median": lambda *a: statistics.median(_flatten(a)),
    "min": lambda *a: min(_flatten(a)),
    "max": lambda *a: max(_flatten(a)),
    "count": lambda *a: len(_flatten(a)),
    "abs": abs,
    "round": round,
}


class CalcError(ValueError):
    pass


def evaluate(expression: str) -> float:
    try:
        value = _eval(ast.parse(str(expression), mode="eval").body)
    except CalcError:
        raise
    except Exception as exc:  # syntax error, division by zero, overflow
        raise CalcError(f"cannot evaluate {expression!r}: {exc}") from exc
    if isinstance(value, list):
        raise CalcError(f"{expression!r} is a list, not a number")
    return value


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise CalcError("exponent too large")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e) for e in node.elts]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS and not node.keywords:
        return _FUNCTIONS[node.func.id](*[_eval(a) for a in node.args])
    raise CalcError(f"not allowed in a calculation: {ast.dump(node)[:60]}")


def format_number(value: float, decimals: int = 2) -> str:
    """1234.5 -> '1,234.50', 3 -> '3', 16.6055 -> '16.61'."""
    rounded = round(value, decimals)
    if float(rounded).is_integer():
        return f"{int(rounded):,}"
    return f"{rounded:,.{decimals}f}"


_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::(\d))?\}")


def render(template: str, calcs: dict[str, str]) -> str:
    """Fill {name} or {name:1} placeholders with computed values (decimals after the colon)."""
    values = {name: evaluate(expr) for name, expr in (calcs or {}).items()}

    def fill(match):
        name, decimals = match.group(1), match.group(2)
        if name not in values:
            raise CalcError(f"placeholder {{{name}}} has no calculation")
        return format_number(values[name], int(decimals) if decimals else 2)

    return _PLACEHOLDER.sub(fill, template)
