"""Safe arithmetic for Level 2. The model writes expressions, Python computes them.

Allowed: numbers, + - * / // % **, comparisons, and/or/not, x if c else y, list
literals, indexing, list/generator comprehensions over lists, the functions below,
and names of earlier calculations. Attributes, imports and other calls are rejected.
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
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}
_COMPARE = {
    ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
}
_MAX_ITEMS = 1000
_MAX_EXPRESSION_CHARS = 2000


def _flatten(args):
    if len(args) == 1 and isinstance(args[0], list):
        return args[0]
    return list(args)


def _avg(*args):
    values = _flatten(args)
    return sum(values) / len(values)


_FUNCTIONS = {
    "sum": lambda *a: sum(_flatten(a)),
    "avg": _avg,
    "mean": _avg,
    "median": lambda *a: statistics.median(_flatten(a)),
    "min": lambda *a: min(_flatten(a)),
    "max": lambda *a: max(_flatten(a)),
    "count": lambda *a: len(_flatten(a)),
    "len": lambda *a: len(_flatten(a)),
    "count_above": lambda values, limit: sum(1 for v in values if v > limit),
    "count_below": lambda values, limit: sum(1 for v in values if v < limit),
    "abs": abs,
    "round": round,
    "sorted": lambda values: sorted(values),
}


class CalcError(ValueError):
    pass


def evaluate(expression: str, names: dict | None = None, allow_list: bool = False):
    if len(str(expression)) > _MAX_EXPRESSION_CHARS:
        raise CalcError("expression too long")
    try:
        value = _eval(ast.parse(str(expression).strip(), mode="eval").body, dict(names or {}))
    except CalcError:
        raise
    except Exception as exc:  # syntax error, division by zero, overflow, bad index
        raise CalcError(f"cannot evaluate {expression!r}: {exc}") from exc
    if isinstance(value, bool):
        return int(value)
    if allow_list and isinstance(value, list):
        return value
    if not isinstance(value, (int, float)):
        raise CalcError(f"{expression!r} is not a single number")
    return value


def _eval(node, env: dict):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise CalcError(f"unknown name {node.id!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left, env), _eval(node.right, env)
        if isinstance(left, list) or isinstance(right, list):
            raise CalcError("arithmetic on lists is not allowed")
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise CalcError("exponent too large")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand, env))
    if isinstance(node, ast.Compare) and all(type(op) in _COMPARE for op in node.ops):
        left = _eval(node.left, env)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = _eval(comparator, env)
            if not _COMPARE[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, env) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.IfExp):
        return _eval(node.body, env) if _eval(node.test, env) else _eval(node.orelse, env)
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, env) for e in node.elts]
    if isinstance(node, ast.Subscript):
        container, index = _eval(node.value, env), _eval(node.slice, env)
        if not isinstance(container, list) or not isinstance(index, int):
            raise CalcError("only list[integer] indexing is allowed")
        return container[index]
    if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
        return _comprehension(node, env)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS \
            and not node.keywords:
        return _FUNCTIONS[node.func.id](*[_eval(a, env) for a in node.args])
    raise CalcError(f"not allowed in a calculation: {type(node).__name__}")


def _comprehension(node, env: dict) -> list:
    if len(node.generators) != 1 or node.generators[0].is_async:
        raise CalcError("only one 'for' per comprehension")
    gen = node.generators[0]
    items = _eval(gen.iter, env)
    if not isinstance(items, list) or len(items) > _MAX_ITEMS:
        raise CalcError("comprehensions must loop over a list")
    out = []
    for item in items:
        scope = dict(env)
        _bind(gen.target, item, scope)
        if all(_eval(cond, scope) for cond in gen.ifs):
            out.append(_eval(node.elt, scope))
    return out


def _bind(target, value, scope: dict) -> None:
    if isinstance(target, ast.Name):
        scope[target.id] = value
    elif isinstance(target, ast.Tuple) and isinstance(value, list) and len(target.elts) == len(value):
        for t, v in zip(target.elts, value, strict=True):
            _bind(t, v, scope)
    else:
        raise CalcError("unsupported loop variable")


def evaluate_all(calcs: dict[str, str]) -> dict:
    """Evaluate in order; later calculations may use the names of earlier ones.
    A calculation may be a list (e.g. a usage history) that later ones aggregate."""
    values: dict = {}
    for name, expression in (calcs or {}).items():
        values[name] = evaluate(expression, values, allow_list=True)
    return values


def format_number(value: float, decimals: int = 2) -> str:
    """1234.5 -> '1,234.50', 3 -> '3', 16.6055 -> '16.61'."""
    rounded = round(value, decimals)
    if float(rounded).is_integer():
        return f"{int(rounded):,}"
    return f"{rounded:,.{decimals}f}"


_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::(\d))?\}")


def render(template: str, calcs: dict[str, str]) -> str:
    """Fill {name} or {name:1} placeholders with computed values (decimals after the colon)."""
    values = evaluate_all(calcs)

    def fill(match):
        name, decimals = match.group(1), match.group(2)
        if name not in values:
            raise CalcError(f"placeholder {{{name}}} has no calculation")
        if isinstance(values[name], list):
            raise CalcError(f"placeholder {{{name}}} is a list, not a number")
        return format_number(values[name], int(decimals) if decimals else 2)

    return _PLACEHOLDER.sub(fill, template)
