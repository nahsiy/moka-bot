from fractions import Fraction

import pytest

from moka.counting_expression import evaluate_expression


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1", 1),
        ("0001", 1),
        ("2 + 3", 5),
        ("3×2", 6),
        ("3x2", 6),
        ("3X2", 6),
        ("8÷2", 4),
        ("8:2", 4),
        ("(10−2)/2", 4),
        ("2^3", 8),
        ("2^3^2", 512),
        ("-2^2", -4),
        ("(-2)^2", 4),
        ("+2", 2),
        ("(1/3)*3", 1),
        ("1/2", Fraction(1, 2)),
        ("1000000000000", 10**12),
    ],
)
def test_exact_counting_arithmetic(text, expected):
    assert evaluate_expression(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "bonjour",
        "1.0",
        "1/0",
        "0^(-1)",
        "2^21",
        "2^(1/2)",
        "2^2^20",
        "1000000000001",
        "1000000000000*1000000000000",
        "1/(1000000000000*2)",
        "(2+3",
        "2+3)",
        "1//2",
        "2**3",
        "1%2",
        "True",
        "__import__('os').system('false')",
        "(1).__class__",
        "[1]",
        "1 if 1 else 0",
        "١",
        "1" * 61,
        " " * 241,
    ],
)
def test_invalid_and_unbounded_expressions_are_refused(text):
    assert evaluate_expression(text) is None
