"""A safe calculator: arithmetic only, no code is ever executed."""
from __future__ import annotations

import ast
import math
import operator as op
import re

_BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow}
_UN = {ast.UAdd: op.pos, ast.USub: op.neg}
_FUN = {"sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max, "floor": math.floor, "ceil": math.ceil}
_CONST = {"pi": math.pi, "e": math.e}
LOOKS_LIKE_MATH = re.compile(r"^[\d\s+\-*/().,%^xX×÷]+$")


class CalcError(Exception):
    pass


def _eval(n):
    if isinstance(n, ast.Expression):
        return _eval(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return n.value
    if isinstance(n, ast.Name) and n.id in _CONST:
        return _CONST[n.id]
    if isinstance(n, ast.UnaryOp) and type(n.op) in _UN:
        return _UN[type(n.op)](_eval(n.operand))
    if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
        a, b = _eval(n.left), _eval(n.right)
        if isinstance(n.op, ast.Pow) and (abs(b) > 1000 or abs(a) > 1e9):
            raise CalcError("That power is too large.")
        return _BIN[type(n.op)](a, b)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUN and not n.keywords and len(n.args) <= 4:
        return _FUN[n.func.id](*[_eval(a) for a in n.args])
    raise CalcError("I can only do simple arithmetic.")


def normalize(expr: str) -> str:
    e = expr.strip().rstrip("=?").lower()
    e = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", r"(\1/100*\2)", e)      # "15% of 200"
    e = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", e)
    e = e.replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", "")
    e = re.sub(r"(?<=[\d)])\s*x\s*(?=[\d(])", "*", e)
    return e


def calculate(expr: str) -> str:
    e = normalize(expr)
    if not e or len(e) > 200:
        raise CalcError("Send me something like /calc 15% of 240.")
    try:
        value = _eval(ast.parse(e, mode="eval"))
    except CalcError:
        raise
    except ZeroDivisionError:
        raise CalcError("You can't divide by zero.")
    except (SyntaxError, ValueError, OverflowError, TypeError):
        raise CalcError("I couldn't work that out. Try something like 12*(3+4).")
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CalcError("That result is not a number.")
        value = round(value, 10)
        if value == int(value) and abs(value) < 1e15:
            value = int(value)
    return f"{value:,}" if isinstance(value, int) and abs(value) >= 10000 else str(value)
