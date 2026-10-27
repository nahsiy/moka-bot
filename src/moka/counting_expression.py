"""Arithmétique bornée pour le counting, sans eval ni exécution de code."""

from __future__ import annotations

import ast
import re
from fractions import Fraction

MAX_VALUE = 10**12
_TRANSLATION = str.maketrans({"×": "*", "x": "*", "X": "*", "÷": "/", ":": "/", "−": "-"})


def evaluate_expression(text: str) -> Fraction | None:
    """Valeur exacte, ou None pour une syntaxe invalide/hors limites."""
    if len(text) > 240:
        return None
    source = "".join(text.split()).translate(_TRANSLATION)
    if not source or len(source) > 60 or not re.fullmatch(r"[0-9+*/^()\-]+", source):
        return None
    # '^' est la notation des puissances du jeu ; '**' écrit directement est refusé.
    if "**" in source or "//" in source:
        return None
    source = re.sub(r"[0-9]+", lambda match: str(int(match[0])), source)

    def bounded(value):
        if abs(value.numerator) > MAX_VALUE or value.denominator > MAX_VALUE:
            raise ValueError("Calcul hors limites")
        return value

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return bounded(Fraction(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return bounded(left + right)
            if isinstance(node.op, ast.Sub):
                return bounded(left - right)
            if isinstance(node.op, ast.Mult):
                return bounded(left * right)
            if isinstance(node.op, ast.Div):
                return bounded(left / right)
            if isinstance(node.op, ast.Pow) and right.denominator == 1 and 0 <= right <= 20:
                return bounded(left ** int(right))
        raise ValueError("Expression non autorisée")

    try:
        return visit(ast.parse(source.replace("^", "**"), mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError, RecursionError):
        return None
