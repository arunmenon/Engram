"""The value language of pack projection rules (domain/pack_expressions.py)."""

from __future__ import annotations

import hashlib

import pytest

from context_graph.domain.pack_expressions import (
    ExpressionError,
    Scope,
    compile_value,
    evaluate,
    is_expression,
)

SCOPE = Scope(
    payload={
        "repo": "acme/app",
        "title": 'Revert "retry"',
        "body": "This reverts #12.\nReviewers: Ann <a@x>, Bo <b@x>\nFixes PAY-7 and PAY-8",
        "subject": "fix(refund): retry (#41)",
        "status": "Won't Do",
        "entries": [{"pr_number": 1, "section": "added"}, {"pr_number": 2}],
        "nested": {"deep": {"value": 3}},
    },
    event={"occurred_at": "2026-10-04T10:00:00Z", "global_position": "5-0"},
)


def _eval(text: str) -> object:
    return evaluate(compile_value(text), SCOPE)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("$.repo", "acme/app"),
        ("$.nested.deep.value", 3),
        ("$.missing.field", None),
        ("$event.global_position", "5-0"),
        ("$.entries[*].pr_number", [1, 2]),
        ("$.entries[*].section", ["added", None]),
        ("$.title + ' ' + $.repo", 'Revert "retry" acme/app'),
        ("$.missing + $.alsomissing", None),
        ("regex($.subject, '\\(#(\\d+)\\)$')", "41"),
        ("regex($.subject, '^\\w+')", "fix"),
        ("regex($.missing, 'x')", None),
        ("regex_all($.body, '([A-Z]+-\\d+)')", ["PAY-7", "PAY-8"]),
        ("each(regex_all($.body, '(?im)^reviewers?:\\s*(.+)$'))", ["Ann <a@x>", "Bo <b@x>"]),
        ("match($.subject, '(?i)^FIX')", True),
        ("match($.missing, 'x')", False),
        ("map($.status, {'To Do': open, 'Won''t Do': cancelled})", "cancelled"),
        ("map($.repo, {'To Do': open})", None),
        ("each($.repo)", ["acme/app"]),
    ],
)
def test_evaluation(expression: str, expected: object) -> None:
    assert _eval(expression) == expected


def test_sha256() -> None:
    assert _eval("sha256($.repo)") == hashlib.sha256(b"acme/app").hexdigest()


def test_constants_are_not_expressions() -> None:
    for constant in ("jira", "declared", "approved"):
        assert not is_expression(constant)
        assert _eval(constant) == constant
    assert evaluate(compile_value(1.0), SCOPE) == 1.0
    assert evaluate(compile_value(True), SCOPE) is True


@pytest.mark.parametrize(
    "bad",
    [
        "nosuchfn($.x)",
        "regex($.x)",
        "regex($.x, $.y)",
        "regex($.x, '(unclosed')",
        "map($.x, 'not a table')",
        "$.",
        "$[*]",
        "regex($.x, 'a'",
        "$.x +",
        "sha256('unterminated)",
    ],
)
def test_invalid_expressions(bad: str) -> None:
    with pytest.raises(ExpressionError):
        compile_value(bad)
